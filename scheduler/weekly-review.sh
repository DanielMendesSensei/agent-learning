#!/usr/bin/env bash
# weekly-review.sh: one firing of the task-observer weekly review, for any engine.
#
#   weekly-review.sh [full|probe]
#
#   full   the review in scheduled autonomous mode (what the timer fires).
#   probe  proves the access grant: the engine writes one file in the workspace
#          from inside this same context and does nothing else.
#
# Environment:
#   AGENT_LEARNING_HOME    workspace root (default ~/.agent-learning)
#   AGENT_LEARNING_ENGINE  claude | codex (default claude)
#   AGENT_LEARNING_MODEL   optional model for the engine
#
# Isolation: claude runs with no user settings, hooks or MCP servers, in its
# bash sandbox (writes only under the workspace, no network for commands).
# Every Bash call is approved by a PreToolUse hook, because in dontAsk mode a
# command the sandbox would run but the classifier wants to ask about (a
# $(date) substitution, say) is denied; the sandbox, not the prompt, is the
# barrier, and allowUnsandboxedCommands=false removes the escape hatch. File
# tools stay limited to the workspace by the Edit rule. task-observer comes in
# through scheduler/claude-plugin, since user skills load with user settings.
# codex runs with --ignore-user-config (no user plugins, MCP servers or hooks;
# auth.json still applies) and -s workspace-write rooted at the workspace,
# which also keeps the network off. The wrapper, not
# the engine, commits the workspace, so commits carry no agent attribution.
set -uo pipefail
shopt -u patsub_replacement 2>/dev/null || true

mode="${1:-full}"
case "$mode" in full|probe) ;; *) echo "uso: $0 [full|probe]" >&2; exit 2 ;; esac

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(dirname "$here")"
ws="${AGENT_LEARNING_HOME:-$HOME/.agent-learning}"
engine="${AGENT_LEARNING_ENGINE:-claude}"
model="${AGENT_LEARNING_MODEL:-}"
state="${XDG_STATE_HOME:-$HOME/.local/state}/agent-learning"
obs="$ws/skill-observations"
export PATH="$HOME/.local/bin:$PATH" SERENA_GATE_OFF=1

mkdir -p "$state/review-logs"
log="$state/review-logs/$(date '+%Y%m%d-%H%M%S')-$mode-$engine.log"
exec > >(tee -a "$log") 2>&1

notify() {
    command -v notify-send >/dev/null 2>&1 && notify-send -a agent-learning "Revisão semanal" "$1" || true
}
finish() { echo "$1"; notify "$1"; exit "$2"; }

exec 9>"$state/review.lock"
flock -n 9 || finish "outra revisão já está rodando; esta saiu sem fazer nada" 0

echo "agent-learning weekly-review: mode=$mode engine=$engine workspace=$ws"
ls "$obs" >/dev/null 2>&1 || finish "revisão pulada: workspace $ws fora do ar ou ausente" 1

case "$engine" in
    claude|codex) command -v "$engine" >/dev/null 2>&1 || finish "revisão pulada: $engine não está no PATH" 1 ;;
    gemini) finish "gemini não roda agendado: no modo headless ele não tem sandbox de escrita; use claude ou codex aqui e rode a revisão no Gemini em sessão interativa" 2 ;;
    *) finish "motor desconhecido: $engine (use claude ou codex)" 2 ;;
esac

commit() {   # commit only the workspace's own folders, never -A
    git -C "$ws" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
    local paths=() p
    for p in skill-observations skill-updates knowledge; do [ -e "$ws/$p" ] && paths+=("$p"); done
    git -C "$ws" add -- "${paths[@]}"
    git -C "$ws" diff --cached --quiet && return 0
    git -C "$ws" -c commit.gpgsign=false commit -q -m "$1" && echo "workspace: commit \"$1\""
}

dash_check() {   # dashes in lines this run added to the workspace's own prose
    git -C "$ws" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
    git -C "$ws" add -N -- skill-observations knowledge 2>/dev/null
    git -C "$ws" diff -U0 --no-color -- 'skill-observations/*.md' 'skill-observations/*.txt' \
        'knowledge/*.md' 'knowledge/*.yaml' | python3 -c '
import sys
f, bad = None, {}
for line in sys.stdin:
    if line.startswith("+++ "):
        f = line[6:].rstrip("\n") if line.startswith("+++ b/") else None
    elif line.startswith("+") and f and ("\u2014" in line or "\u2013" in line):
        bad[f] = bad.get(f, 0) + 1
for k, v in sorted(bad.items()):
    print(f"{k}: {v}")
'
}

today="$(date '+%F')"
commit "estado antes da $([ "$mode" = probe ] && echo sonda || echo revisão) de $today"

template="$here/review-prompt.md"
[ "$mode" = probe ] && template="$here/probe-prompt.md"
prompt="$(<"$template")"
prompt="${prompt//'{{WORKSPACE}}'/$ws}"
prompt="${prompt//'{{ENGINE}}'/$engine}"
prompt="${prompt//'{{SKILL_DIR}}'/$repo/skills/task-observer}"

limit=7200
[ "$mode" = probe ] && limit=600
started="$(date '+%s')"

run_claude() {
    local settings="$state/claude-review-settings.json"
    python3 - "$ws" "$settings" <<'PY'
import json, sys
ws, out = sys.argv[1], sys.argv[2]
allow_bash = json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse", "permissionDecision": "allow",
    "permissionDecisionReason": "scheduled review: Bash runs inside the sandbox"}})
json.dump({
    "sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False},
    "permissions": {"allow": ["Read", "Glob", "Grep", "Skill", f"Edit(/{ws}/**)"],
                    "deny": ["WebFetch", "WebSearch"]},
    "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": "printf '%s' '" + allow_bash + "'"}]}]},
    "env": {"SERENA_GATE_OFF": "1"},
}, open(out, "w"), indent=2)
PY
    local args=(-p "$prompt" --setting-sources project --settings "$settings" --strict-mcp-config
                --plugin-dir "$here/claude-plugin" --permission-mode dontAsk --add-dir "$ws"
                --no-session-persistence)
    [ -n "$model" ] && args+=(--model "$model")
    (cd "$ws" && timeout "$limit" claude "${args[@]}" </dev/null)
}

run_codex() {
    local args=(exec --ignore-user-config -C "$ws" -s workspace-write --skip-git-repo-check --ephemeral)
    [ -n "$model" ] && args+=(-m "$model")
    timeout "$limit" codex "${args[@]}" "$prompt" </dev/null
}

echo "----- $engine -----"
"run_$engine"
rc=$?
echo "----- fim ($engine saiu com $rc) -----"

if [ "$mode" = probe ]; then
    marker="$obs/scheduler-probe.txt"
    if [ -f "$marker" ] && [ "$(stat -c %Y "$marker")" -ge "$started" ]; then
        msg="sonda ok: $engine gravou $(cat "$marker") no workspace"
        code=0
    else
        msg="sonda FALHOU: $engine não gravou $marker (veja $log)"
        code=1
    fi
else
    marker="$(head -n1 "$obs/review-started.txt" 2>/dev/null)"
    d="${marker#completed }"
    if [ "$marker" != "$d" ] && [ -s "$obs/reviews/$d/REVIEW.md" ]; then
        msg="revisão $d concluída: $obs/reviews/$d/REVIEW.md"
        code=0
    else
        msg="disparou em $today e não registrou revisão (marcador: ${marker:-ausente}; veja $log)"
        code=1
    fi
fi

dashes="$(dash_check)"
[ -n "$dashes" ] && { echo "travessões em linhas novas:"; echo "$dashes"; msg="$msg; ATENÇÃO: travessões em $(echo "$dashes" | wc -l) arquivo(s), veja o log"; }
commit "$([ "$mode" = probe ] && echo "sonda do agendador" || echo "revisão semanal") de $today ($engine, saída $rc)"
finish "$msg" "$code"
