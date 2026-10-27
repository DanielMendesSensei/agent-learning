#!/usr/bin/env bash
# agent-learning SessionStart hook, shared by Claude Code, Codex and Gemini CLI.
#
#   bash session-start.sh --agent claude|codex|gemini|other
#
# Prints one JSON object on stdout:
#   {"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}
# The three CLIs read the same shape; Codex rejects unknown fields, so nothing
# else is printed. The context carries the task-observer activation reminder
# (template of task-observer v3.8.1, references/environments.md), the review
# state and the llm-learning base size. It never runs the review.
#
# Roots: AGENT_LEARNING_HOME (default ~/.agent-learning) for the task-observer
# workspace, AGENT_LEARNING_KB (default <root>/knowledge) for the base.
set -u

agent=other
while [ $# -gt 0 ]; do
  case "$1" in
    (--agent) agent="${2:-other}"; shift 2 ;;
    (--agent=*) agent="${1#--agent=}"; shift ;;
    (*) shift ;;
  esac
done

repo=$(cd "$(dirname "$0")/.." && pwd -P)
root="${AGENT_LEARNING_HOME:-$HOME/.agent-learning}"
kb="${AGENT_LEARNING_KB:-$root/knowledge}"
d="$root/skill-observations"

case "$agent" in
  (claude) load="invoke the task-observer skill (Skill tool)" ;;
  (gemini) load="activate the task-observer skill (activate_skill)" ;;
  (codex)  load="load the task-observer skill (by name, or by reading its SKILL.md)" ;;
  (*)      load="read $repo/skills/task-observer/SKILL.md" ;;
esac

if [ -d "$d/observation-log" ]; then
  open=$(find "$d/observation-log" -maxdepth 1 -name '*.md' -exec grep -l '^status: open$' {} + 2>/dev/null | wc -l | tr -d ' ')
  last=$(tr -d '\r' 2>/dev/null < "$d/last-review-date.txt"); last=${last:-never}   # a CRLF file must not carry \r into the JSON
  msg="Make the first tool call of this session one batched call: in it, list the task-observer workspace ($root) and $load; then run its Session Start Protocol. Observation files are created only by $repo/skills/task-observer/scripts/new-observation.sh, never by copying a header."
  msg="$msg $open open observations in $d; last review: $last."   # always, zero included: a mispinned path reads 0 too
  if [ "$open" -gt 0 ]; then
    cutoff=$(date -d '7 days ago' +%F 2>/dev/null || date -v-7d +%F)   # GNU, then BSD/macOS
    case "$last" in
      (never) msg="$msg Offer the review." ;;
      (*) [ "$(printf '%s\n%s\n' "$last" "$cutoff" | sort | head -1)" = "$last" ] && msg="$msg Offer the review." ;;
    esac
  fi
else
  msg="The task-observer workspace $d does not exist yet: this is a first run. In the first tool call, $load and run its Session Start Protocol, whose Workspace creation step creates it."
fi

if [ -f "$kb/manifest.yaml" ]; then
  units=$(grep -c -E '^[[:space:]]*-[[:space:]]*\{?[[:space:]]*id:' "$kb/manifest.yaml" 2>/dev/null); units=${units:-0}
  msg="$msg llm-learning: $units units in $kb. At the start of a technical task, load the llm-learning skill and run its retrieval; capture only on the owner's explicit recognition."
else
  msg="$msg llm-learning: no base at $kb (create it with: python3 $repo/skills/llm-learning/scripts/kb.py init $kb --owner NAME)."
fi

msg=$(printf '%s' "$msg" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr -d '\000-\037')   # JSON string: escape \ and ", drop control characters
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg"
