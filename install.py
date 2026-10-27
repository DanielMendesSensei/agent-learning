#!/usr/bin/env python3
"""install.py: wire agent-learning (task-observer + llm-learning) into every agent.

    python3 install.py [--dry-run] [--home DIR] [--owner NAME] [--projects DIR]
    python3 install.py --uninstall [--dry-run] [--home DIR]
    python3 install.py --selftest

What it does, each step idempotent (a second run reports "em dia"):

  skills      links skills/task-observer and skills/llm-learning into
              ~/.claude/skills (Claude Code) and ~/.agents/skills (Codex and
              Gemini CLI read it). A real directory already there is adopted
              only when identical to the repo copy; anything else is refused.
  kb          links ~/.local/bin/kb to the llm-learning helper.
  instructions  renders adapters/instructions-block.md into CLAUDE.md,
              ~/.codex/AGENTS.md (or AGENTS.override.md) and ~/.gemini/GEMINI.md,
              between <!-- agent-learning:inicio --> and <!-- agent-learning:fim -->,
              and removes the older hand-written task-observer section.
  hooks       a SessionStart hook running adapters/session-start.sh in Claude
              Code (settings.json), Codex (config.toml) and Gemini CLI
              (settings.json). Trust is never written: Codex asks in /hooks,
              Gemini runs hooks only in trusted folders.
  workspace   moves ~/.claude/skill-observations and ~/.claude/skill-updates to
              ~/.agent-learning, leaves skill-observations/MOVED.md at the old
              root, and creates the llm-learning base at ~/.agent-learning/knowledge.
  schedule    renders scheduler/systemd/ into ~/.config/systemd/user, enables
              weekly-skill-review.timer (the weekly review, run by
              scheduler/weekly-review.sh with claude or codex), and writes
              skill-observations/scheduler-registered.txt only after
              list-timers shows the timer. Skipped with --no-schedule or
              without systemctl.

Every file is copied to ~/.local/state/agent-learning/backups/<timestamp>/
before its first change. Nothing is deleted: replaced directories and the old
hook script are moved there too. --uninstall removes links, blocks and hooks,
and leaves the workspace and the base alone.
"""
from __future__ import annotations

import argparse
import contextlib
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent
VERSION = "0.1.0"
SKILLS = ("task-observer", "llm-learning")
HOOK_SCRIPT = REPO / "adapters" / "session-start.sh"
TEMPLATE = REPO / "adapters" / "instructions-block.md"
KB_PY = REPO / "skills" / "llm-learning" / "scripts" / "kb.py"

BLOCK_RE = re.compile(r"<!-- agent-learning:inicio[^>]*-->.*?<!-- agent-learning:fim -->\n?", re.S)
LEGACY_RE = re.compile(r"^# Task Observer: bloco de ativação\n.*?<!-- task-observer:fim -->\n?", re.S | re.M)
TOML_RE = re.compile(r"^# agent-learning:inicio[^\n]*\n.*?^# agent-learning:fim[^\n]*\n?", re.S | re.M)
LEGACY_HOOK = "task-observer-session-start.sh"
HOOK_MARK = "adapters/session-start.sh"
CODEX_AGENTS_LIMIT = 32 * 1024
IGNORE = {"__pycache__", ".DS_Store"}
SCHED = REPO / "scheduler"
TIMER = "weekly-skill-review.timer"
SERVICE = "weekly-skill-review@.service"
CALENDAR = "Mon *-*-* 10:00:00"
ENGINES = ("claude", "codex")
NOTES_DEFAULT = "notas pessoais | a ferramenta que as outras instruções indicarem"
CONFIG_KEYS = ("owner", "notes")


class Ctx:
    def __init__(self, home: Path, env: dict, *, dry: bool, owner: str, projects: Path,
                 out=print, engine: str = "claude", calendar: str = CALENDAR, schedule: bool = True,
                 notes: str = NOTES_DEFAULT):
        self.home = home
        self.notes = notes
        self.env = env
        self.dry = dry
        self.owner = owner
        self.projects = projects
        self.out = out
        self.engine = engine
        self.calendar = calendar
        self.schedule = schedule
        self.problems: list[str] = []
        self.changes = 0
        self.stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.claude = Path(env.get("CLAUDE_CONFIG_DIR") or home / ".claude")
        self.codex = Path(env.get("CODEX_HOME") or home / ".codex")
        self.gemini = home / ".gemini"
        self.root = Path(env.get("AGENT_LEARNING_HOME") or home / ".agent-learning")
        self.backups = home / ".local" / "state" / "agent-learning" / "backups" / self.stamp

    # -- reporting
    def ok(self, msg: str) -> None:
        self.out(f"  em dia   {msg}")

    def did(self, msg: str) -> None:
        self.changes += 1
        self.out(f"  {'faria' if self.dry else 'feito'}    {msg}")

    def bad(self, msg: str) -> None:
        self.problems.append(msg)
        self.out(f"  PROBLEMA {msg}")

    def short(self, p: Path) -> str:
        with contextlib.suppress(ValueError):
            return "~/" + str(p.relative_to(self.home))
        return str(p)

    # -- file operations (no-ops in a dry run)
    def _backup_path(self, p: Path) -> Path:
        with contextlib.suppress(ValueError):
            return self.backups / p.relative_to(self.home)
        return self.backups / "_abs" / str(p).lstrip("/")

    def backup_copy(self, p: Path) -> None:
        """Copy a file before its first change in this run."""
        if self.dry or not p.exists():
            return
        dst = self._backup_path(p)
        if dst.exists():
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(os.path.realpath(p), dst)

    def backup_move(self, p: Path) -> Path:
        """Move a file, directory or link out of the way, into the backup."""
        dst = self._backup_path(p)
        if not self.dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dst))
        return dst

    def write(self, p: Path, text: str) -> None:
        if self.dry:
            return
        self.backup_copy(p)
        real = Path(os.path.realpath(p))
        real.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=real.parent, prefix=f".{real.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            if real.exists():
                shutil.copymode(real, tmp)
            else:
                os.chmod(tmp, 0o644)
            os.replace(tmp, real)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp)
            raise

    def symlink(self, src: Path, dst: Path) -> None:
        if not self.dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src, target_is_directory=src.is_dir())


# ---------------------------------------------------------------- helpers

def same_tree(a: Path, b: Path) -> bool:
    """True when two directories hold the same files with the same bytes."""
    def files(root: Path) -> set[str]:
        out = set()
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORE]
            for f in filenames:
                if f not in IGNORE and not f.endswith(".pyc"):
                    out.add(str(Path(dirpath, f).relative_to(root)))
        return out
    fa, fb = files(a), files(b)
    return fa == fb and all(filecmp.cmp(a / f, b / f, shallow=False) for f in fa)


def points_into_repo(p: Path) -> bool:
    if not p.is_symlink():
        return False
    target = Path(os.path.realpath(p))
    return target == REPO or REPO in target.parents


def hook_command(agent: str) -> str:
    s = str(HOOK_SCRIPT)
    return f"[ ! -f '{s}' ] || bash '{s}' --agent {agent}"


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def dump_json(d: dict, original: str) -> str:
    ascii_only = bool(original) and all(ord(c) < 128 for c in original)
    return json.dumps(d, indent=2, ensure_ascii=ascii_only) + "\n"


def drop_hooks(groups: list, predicate) -> list:
    """Remove matching hook entries; drop a group only when that emptied it."""
    kept = []
    for g in groups:
        if isinstance(g, dict) and isinstance(g.get("hooks"), list):
            before = g["hooks"]
            after = [h for h in before if not (isinstance(h, dict) and predicate(h))]
            if not after and before:
                continue
            if len(after) != len(before):
                g = {**g, "hooks": after}
        kept.append(g)
    return kept


def is_ours(h: dict) -> bool:
    cmd = str(h.get("command", ""))
    return HOOK_MARK in cmd and str(REPO) in cmd or h.get("name") == "agent-learning"


def is_legacy(h: dict) -> bool:
    return LEGACY_HOOK in str(h.get("command", ""))


# ---------------------------------------------------------------- steps

def skill_dirs(c: Ctx) -> list[Path]:
    dirs = []
    if c.claude.is_dir():
        dirs.append(c.claude / "skills")
    if c.codex.is_dir() or c.gemini.is_dir():
        dirs.append(c.home / ".agents" / "skills")
    return dirs


def link(c: Ctx, src: Path, dst: Path) -> None:
    label = f"{c.short(dst)} -> {c.short(src)}"
    if dst.is_symlink():
        if Path(os.path.realpath(dst)) == src.resolve():
            return c.ok(label)
        return c.bad(f"{c.short(dst)} já aponta para {os.readlink(dst)}; nada feito")
    if dst.is_dir():
        if not same_tree(dst, src):
            return c.bad(f"{c.short(dst)} é um diretório diferente do repositório; nada feito "
                         f"(compare: diff -r '{dst}' '{src}')")
        moved = c.backup_move(dst)
        c.symlink(src, dst)
        return c.did(f"{label} (cópia idêntica movida para {c.short(moved)})")
    if dst.exists():
        return c.bad(f"{c.short(dst)} já existe e não é link nem diretório; nada feito")
    c.symlink(src, dst)
    c.did(label)


def step_skills(c: Ctx) -> None:
    for d in skill_dirs(c):
        for name in SKILLS:
            link(c, REPO / "skills" / name, d / name)


def step_kb(c: Ctx) -> None:
    bindir = c.home / ".local" / "bin"
    link(c, KB_PY, bindir / "kb")
    if str(bindir) not in c.env.get("PATH", "").split(os.pathsep):
        c.out(f"  aviso    {c.short(bindir)} não está no PATH: o comando kb não vai resolver")


def instruction_files(c: Ctx) -> list[tuple[str, Path]]:
    out = []
    if c.claude.is_dir():
        out.append(("Claude Code", c.claude / "CLAUDE.md"))
    if c.codex.is_dir():
        override = c.codex / "AGENTS.override.md"
        out.append(("Codex", override if override.exists() else c.codex / "AGENTS.md"))
    if c.gemini.is_dir():
        out.append(("Gemini CLI", c.gemini / "GEMINI.md"))
    return out


def render_block(c: Ctx) -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    for key, val in (("{{REPO}}", REPO), ("{{ROOT}}", c.root), ("{{PROJECTS}}", c.projects),
                     ("{{OWNER}}", c.owner), ("{{NOTES}}", c.notes)):
        text = text.replace(key, str(val))
    left = re.findall(r"\{\{[A-Z]+\}\}", text)
    if left:
        raise SystemExit(f"instructions-block.md: placeholder sem valor: {left[0]}")
    return text.rstrip("\n")


def cut(text: str, rx: re.Pattern) -> str:
    """Remove every match of rx, joining the two sides with one blank line."""
    while (m := rx.search(text)):
        head, tail = text[:m.start()].rstrip("\n"), text[m.end():].lstrip("\n")
        text = head + "\n\n" + tail if head and tail else (head + "\n" if head else tail)
    return text


def apply_block(text: str, block: str | None) -> str:
    """Remove the legacy section and our block; append the block when given."""
    new = cut(text, LEGACY_RE)
    if block is not None and BLOCK_RE.search(new):
        return BLOCK_RE.sub(lambda _m: block + "\n", new, count=1)
    new = cut(new, BLOCK_RE).rstrip("\n")
    if block is None:
        return new + "\n" if new else ""
    return (new + "\n\n" if new else "") + block + "\n"


def step_instructions(c: Ctx, *, remove: bool = False) -> None:
    block = None if remove else render_block(c)
    for agent, p in instruction_files(c):
        text = read(p)
        new = apply_block(text, block)
        if new == text:
            c.ok(f"{c.short(p)} ({agent})")
            continue
        if agent == "Codex" and len(new.encode()) > CODEX_AGENTS_LIMIT:
            c.bad(f"{c.short(p)} passaria de 32 KiB ({len(new.encode())} bytes) e o Codex "
                  "corta o excedente; nada feito")
            continue
        legacy = " e seção antiga do task-observer removida" if LEGACY_RE.search(text) else ""
        c.write(p, new)
        c.did(f"{c.short(p)} ({agent}): bloco {'removido' if remove else 'gravado'}{legacy}")


def edit_json_hooks(c: Ctx, p: Path, agent: str, group: dict | None) -> None:
    original = read(p)
    try:
        d = json.loads(original) if original.strip() else {}
    except json.JSONDecodeError as e:
        return c.bad(f"{c.short(p)} não é JSON válido ({e}); nada feito")
    hooks = d.get("hooks", {})
    if not isinstance(hooks, dict) or not isinstance(hooks.get("SessionStart", []), list):
        return c.bad(f"{c.short(p)}: 'hooks' fora do formato esperado; nada feito")
    groups = drop_hooks(list(hooks.get("SessionStart", [])), lambda h: is_ours(h) or is_legacy(h))
    if group is not None:
        groups.append(group)
    new_hooks = {**hooks, "SessionStart": groups} if groups else {
        k: v for k, v in hooks.items() if k != "SessionStart"}
    new = {**d, "hooks": new_hooks} if new_hooks or "hooks" in d else d
    if new == d:
        return c.ok(f"{c.short(p)} ({agent}): hook SessionStart")
    text = dump_json(new, original)
    json.loads(text)
    c.write(p, text)
    c.did(f"{c.short(p)} ({agent}): hook SessionStart {'removido' if group is None else 'gravado'}")


def step_claude_hooks(c: Ctx, *, remove: bool = False) -> None:
    if not c.claude.is_dir():
        return
    group = None if remove else {"hooks": [
        {"type": "command", "command": hook_command("claude"), "timeout": 10}]}
    edit_json_hooks(c, c.claude / "settings.json", "Claude Code", group)
    old = c.claude / "hooks" / LEGACY_HOOK
    if not remove and (old.exists() or old.is_symlink()):
        moved = c.backup_move(old)
        c.did(f"{c.short(old)} movido para {c.short(moved)}")


def codex_block() -> str:
    cmd = json.dumps(hook_command("codex"))
    return (f"# agent-learning:inicio v{VERSION} (gerado por {REPO}/install.py; aprove em /hooks)\n"
            "[[hooks.SessionStart]]\n"
            'matcher = "startup|resume|clear|compact"\n\n'
            "[[hooks.SessionStart.hooks]]\n"
            'type = "command"\n'
            f"command = {cmd}\n"
            "timeout = 10\n"
            "# agent-learning:fim\n")


def step_codex_hooks(c: Ctx, *, remove: bool = False) -> None:
    if not c.codex.is_dir():
        return
    try:
        import tomllib
    except ModuleNotFoundError:
        return c.bad("Python sem tomllib (precisa de 3.11+); hook do Codex não gravado")
    p = c.codex / "config.toml"
    text = read(p)
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        return c.bad(f"{c.short(p)} não é TOML válido ({e}); nada feito")
    new = cut(text, TOML_RE).rstrip("\n")
    if not remove:
        new = (new + "\n\n" if new else "") + codex_block()
    elif new:
        new += "\n"
    if new == text:
        return c.ok(f"{c.short(p)} (Codex): hook SessionStart")
    try:
        parsed = tomllib.loads(new)
    except tomllib.TOMLDecodeError as e:
        return c.bad(f"{c.short(p)}: o bloco novo quebraria o TOML ({e}); nada feito")
    cmds = [h.get("command") for g in parsed.get("hooks", {}).get("SessionStart", [])
            for h in g.get("hooks", [])]
    if not remove and hook_command("codex") not in cmds:
        return c.bad(f"{c.short(p)}: hook não aparece depois de gravado; nada feito")
    c.write(p, new)
    c.did(f"{c.short(p)} (Codex): hook SessionStart {'removido' if remove else 'gravado'}")


def step_gemini_hooks(c: Ctx, *, remove: bool = False) -> None:
    if not c.gemini.is_dir():
        return
    group = None if remove else {"matcher": "startup", "hooks": [
        {"type": "command", "command": hook_command("gemini"), "name": "agent-learning",
         "timeout": 5000}]}
    edit_json_hooks(c, c.gemini / "settings.json", "Gemini CLI", group)


def has_content(d: Path, ignore: tuple[str, ...] = ()) -> bool:
    return d.is_dir() and any(x.name not in ignore for x in d.iterdir())


def step_workspace(c: Ctx) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    old_obs, new_obs = c.claude / "skill-observations", c.root / "skill-observations"
    if old_obs.resolve() == new_obs.resolve():
        c.ok(f"workspace já em {c.short(c.root)}")
    elif has_content(old_obs, ("MOVED.md",)):
        if has_content(new_obs):
            c.bad(f"{c.short(old_obs)} e {c.short(new_obs)} têm dados: duas raízes. Consolide à mão "
                  "(task-observer, references/environments.md); nada movido")
        else:
            if not c.dry:
                new_obs.mkdir(parents=True, exist_ok=True)
                for child in sorted(old_obs.iterdir()):
                    if child.name != "MOVED.md":
                        shutil.move(str(child), str(new_obs / child.name))
                (old_obs / "MOVED.md").write_text(
                    f"Movido para {c.root} em {today}\n\n"
                    f"O agent-learning ({REPO}/install.py) re-ancorou o workspace do task-observer "
                    f"de {c.claude} para {c.root}, onde Claude Code, Codex e Gemini leem o mesmo log. "
                    "Os hooks e os arquivos de instruções foram re-apontados na mesma execução.\n",
                    encoding="utf-8")
            c.did(f"{c.short(old_obs)} movido para {c.short(new_obs)} (MOVED.md deixado na raiz antiga)")
    elif new_obs.is_dir():
        c.ok(f"{c.short(new_obs)}")
    else:
        c.out(f"  aviso    nenhum workspace ainda; a primeira sessão cria {c.short(new_obs)}")

    old_up, new_up = c.claude / "skill-updates", c.root / "skill-updates"
    if old_up.resolve() != new_up.resolve() and has_content(old_up):
        if has_content(new_up):
            c.bad(f"{c.short(old_up)} e {c.short(new_up)} têm itens em staging; nada movido")
        else:
            if not c.dry:
                new_up.parent.mkdir(parents=True, exist_ok=True)
                with contextlib.suppress(FileNotFoundError):
                    new_up.rmdir()
                shutil.move(str(old_up), str(new_up))
            c.did(f"{c.short(old_up)} movido para {c.short(new_up)}")

    kb = c.root / "knowledge"
    if (kb / "manifest.yaml").exists():
        c.ok(f"base llm-learning em {c.short(kb)}")
    elif has_content(kb):
        c.bad(f"{c.short(kb)} existe sem manifest.yaml; nada feito")
    else:
        if not c.dry:
            r = subprocess.run([sys.executable, str(KB_PY), "init", str(kb), "--owner", c.owner],
                               capture_output=True, text=True)
            if r.returncode != 0:
                return c.bad(f"kb.py init falhou:\n{r.stdout}{r.stderr}")
        c.did(f"base llm-learning criada em {c.short(kb)} (dono: {c.owner})")


def systemctl(c: Ctx, *args: str) -> subprocess.CompletedProcess | None:
    exe = shutil.which(c.env.get("AGENT_LEARNING_SYSTEMCTL", "systemctl"), path=c.env.get("PATH"))
    if not exe:
        return None
    return subprocess.run([exe, "--user", *args], capture_output=True, text=True, env=c.env)


def unit_dir(c: Ctx) -> Path:
    return Path(c.env.get("XDG_CONFIG_HOME") or c.home / ".config") / "systemd" / "user"


def render_units(c: Ctx) -> dict[Path, str]:
    subs = {"{{SCRIPT}}": str(SCHED / "weekly-review.sh"), "{{ROOT}}": str(c.root),
            "{{ENGINE}}": c.engine, "{{CALENDAR}}": c.calendar}
    units = {}
    for name in (SERVICE, TIMER):
        text = read(SCHED / "systemd" / name)
        for k, v in subs.items():
            text = text.replace(k, v)
        units[unit_dir(c) / name] = text
    return units


def marker_text(c: Ctx, day: str) -> str:
    """scheduler-registered.txt: the date first, then the workspace the task reads."""
    return (f"{day}\n"
            f"workspace: {c.root}\n"
            f"task: weekly-skill-review (systemd --user {TIMER}, fires weekly-skill-review@full.service)\n"
            f"schedule: {c.calendar}, Persistent=true\n"
            f"engine: {c.engine}\n"
            f"prompt: {SCHED / 'review-prompt.md'}\n"
            f"logs: {c.home / '.local' / 'state' / 'agent-learning' / 'review-logs'}\n")


def step_schedule(c: Ctx, *, remove: bool = False) -> None:
    marker = c.root / "skill-observations" / "scheduler-registered.txt"
    units = render_units(c)
    if remove:
        present = [p for p in units if p.exists()]
        if present:
            if not c.dry:
                systemctl(c, "disable", "--now", TIMER)
                for p in present:
                    c.backup_move(p)
                systemctl(c, "daemon-reload")
            c.did(f"{TIMER} desligado e unidades removidas")
        if marker.exists():
            c.backup_move(marker)
            c.did(f"{c.short(marker)} removido (sem agendador, a oferta de revisão volta)")
        return
    if not c.schedule:
        return c.out("  aviso    agendamento pulado (--no-schedule)")
    if systemctl(c, "--version") is None:
        return c.out("  aviso    sem systemctl: agende scheduler/weekly-review.sh no agendador da máquina (PLAYBOOK.md)")
    changed = False
    for p, text in units.items():
        if read(p) == text:
            c.ok(c.short(p))
        else:
            c.write(p, text)
            c.did(c.short(p))
            changed = True
    if changed and not c.dry:
        systemctl(c, "daemon-reload")
    on = (systemctl(c, "is-enabled", TIMER).stdout.strip() == "enabled"
          and systemctl(c, "is-active", TIMER).stdout.strip() == "active")
    if on:
        c.ok(f"{TIMER} ativo ({c.calendar}, motor {c.engine})")
    else:
        if not c.dry:
            r = systemctl(c, "enable", "--now", TIMER)
            if r.returncode != 0:
                return c.bad(f"systemctl --user enable --now {TIMER} falhou: {r.stderr.strip()}")
        c.did(f"{TIMER} ligado ({c.calendar}, motor {c.engine})")
        c.out("  próximo  prove o acesso: systemctl --user start weekly-skill-review@probe.service")
    if c.dry:
        return
    r = systemctl(c, "list-timers", "--all", "--no-legend", TIMER)
    if TIMER not in r.stdout:
        return c.bad(f"{TIMER} não aparece em list-timers; {c.short(marker)} não gravado")
    if not marker.parent.is_dir():
        return c.out(f"  aviso    {c.short(marker.parent)} ainda não existe; marcador fica para a próxima instalação")
    old = read(marker)
    if old and old.split("\n", 1)[1:] == marker_text(c, "").split("\n", 1)[1:]:
        c.ok(c.short(marker))
    else:
        c.write(marker, marker_text(c, datetime.now().strftime("%Y-%m-%d")))
        c.did(f"{c.short(marker)} (timer listado, workspace {c.root})")


def step_unlink(c: Ctx) -> None:
    targets = [d / n for d in skill_dirs(c) for n in SKILLS] + [c.home / ".local" / "bin" / "kb"]
    for t in targets:
        if points_into_repo(t):
            if not c.dry:
                t.unlink()
            c.did(f"link {c.short(t)} removido")
        elif t.exists() or t.is_symlink():
            c.out(f"  aviso    {c.short(t)} não é link deste repositório; deixado como está")


# ---------------------------------------------------------------- entry points

def install(c: Ctx) -> int:
    c.out(f"agent-learning {VERSION}: {REPO}{'  (simulação)' if c.dry else ''}")
    for title, fn in (("skills", step_skills), ("kb", step_kb),
                      ("instruções", step_instructions), ("hooks", step_claude_hooks),
                      (None, step_codex_hooks), (None, step_gemini_hooks),
                      ("workspace", step_workspace), ("agendamento", step_schedule)):
        if title:
            c.out(title)
        fn(c)
    finish(c)
    return 1 if c.problems else 0


def uninstall(c: Ctx) -> int:
    c.out(f"agent-learning {VERSION}: desinstalação{'  (simulação)' if c.dry else ''}")
    step_unlink(c)
    step_instructions(c, remove=True)
    step_claude_hooks(c, remove=True)
    step_codex_hooks(c, remove=True)
    step_gemini_hooks(c, remove=True)
    step_schedule(c, remove=True)
    c.out(f"  aviso    workspace e base ficam em {c.short(c.root)}; nada apagado")
    finish(c)
    return 1 if c.problems else 0


def finish(c: Ctx) -> None:
    if c.changes and not c.dry and c.backups.exists():
        c.out(f"cópias de segurança: {c.short(c.backups)}")
    if c.changes and not c.dry and c.codex.is_dir():
        c.out("Codex: abra /hooks e aprove o hook novo do agent-learning (ele não roda antes disso).")
    if c.changes and not c.dry and c.gemini.is_dir():
        c.out("Gemini CLI: hooks só rodam em pasta confiável; a confiança é sua, o instalador não mexe nela.")
    if c.problems:
        c.out(f"{len(c.problems)} problema(s); o resto foi aplicado.")


def load_config(home: Path, env: dict) -> dict:
    """Per-machine values (owner, notes) kept out of the repository."""
    p = Path(env.get("XDG_CONFIG_HOME") or home / ".config") / "agent-learning" / "install.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{p}: JSON inválido ({e})")
    if not isinstance(data, dict):
        raise SystemExit(f"{p}: esperava um objeto JSON")
    return {k: str(data[k]) for k in CONFIG_KEYS if data.get(k)}


def git_name() -> str:
    with contextlib.suppress(Exception):
        r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
        if r.stdout.strip():
            return r.stdout.strip()
    return "owner"


# ---------------------------------------------------------------- selftest

def selftest() -> int:
    fails = []

    def check(cond: bool, why: str) -> None:
        print(f"  {'ok ' if cond else 'FALHOU'} {why}")
        if not cond:
            fails.append(why)

    def snapshot(root: Path) -> dict:
        snap = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORE]
            for name in filenames + [d for d in dirnames if Path(dirpath, d).is_symlink()]:
                p = Path(dirpath, name)
                if ".local/state" in str(p):
                    continue
                snap[str(p.relative_to(root))] = (os.readlink(p) if p.is_symlink()
                                                  else p.read_bytes())
        return snap

    legacy = ("# Task Observer: bloco de ativação\n\nInstalado antes.\n\n"
              "<!-- task-observer:inicio -->\n```text\nvelho\n```\n<!-- task-observer:fim -->\n")
    with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as fakebin:
        home = Path(t)
        fake = Path(fakebin) / "systemctl"
        fake.write_text(
            '#!/bin/bash\nd="$(dirname "$0")"; echo "$*" >> "$d/calls.log"\ncase "$2" in\n'
            '  is-enabled) [ -f "$d/on" ] && echo enabled || { echo disabled; exit 1; } ;;\n'
            '  is-active) [ -f "$d/on" ] && echo active || { echo inactive; exit 3; } ;;\n'
            '  enable) touch "$d/on" ;;\n  disable) rm -f "$d/on" ;;\n'
            f'  list-timers) [ -f "$d/on" ] && echo "Mon 2026-11-02 10:00:00 -03 - - - {TIMER} x" ;;\n'
            'esac\nexit 0\n')
        fake.chmod(0o755)
        calls = Path(fakebin) / "calls.log"
        claude, codex, gemini = home / ".claude", home / ".codex", home / ".gemini"
        (claude / "hooks").mkdir(parents=True)
        (claude / "CLAUDE.md").write_text(
            "# Regras\n\n<!-- serena:inicio sha=000000000000 -->\nserena\n<!-- serena:fim -->\n\n"
            + legacy)
        (claude / "settings.json").write_text(json.dumps({"hooks": {"SessionStart": [
            {"hooks": [{"type": "command", "command": "outro.sh"}]},
            {"hooks": [{"type": "command", "command": f"{claude}/hooks/{LEGACY_HOOK}", "timeout": 10}]},
        ]}}, indent=2))
        (claude / "hooks" / LEGACY_HOOK).write_text("#!/bin/sh\n")
        shutil.copytree(REPO / "skills" / "task-observer", claude / "skills" / "task-observer")
        log = claude / "skill-observations" / "observation-log"
        log.mkdir(parents=True)
        (log / "0001-x.md").write_text("---\nid: 1\nstatus: open\n---\n")
        (claude / "skill-observations" / "last-review-date.txt").write_text("never\n")
        codex.mkdir()
        (codex / "AGENTS.md").write_text("# Regras do Codex\n")
        (codex / "config.toml").write_text(
            'model = "x"\n\n[[hooks.Stop]]\n[[hooks.Stop.hooks]]\ntype = "command"\n'
            'command = "stop.sh"\n\n[hooks.state]\nfoo = 1\n')
        gemini.mkdir()
        (gemini / "GEMINI.md").write_text("# Regras do Gemini\n")
        (gemini / "settings.json").write_text(json.dumps({"security": {"auth": "x"}}, indent=2))
        different = home / ".agents" / "skills" / "llm-learning"
        different.mkdir(parents=True)
        (different / "SKILL.md").write_text("outra\n")

        env = {"PATH": f"{home}/.local/bin:/usr/bin", "AGENT_LEARNING_SYSTEMCTL": str(fake)}
        quiet: list[str] = []
        mk = lambda dry=False: Ctx(home, env, dry=dry, owner="Ana Tester",
                                   projects=home / "projects", out=quiet.append)
        before = snapshot(home)
        c = mk(dry=True)
        install(c)
        check(snapshot(home) == before, "--dry-run não muda nenhum arquivo")
        check("enable --now" not in read(calls) and "daemon-reload" not in read(calls),
              "--dry-run não liga nem recarrega o systemd")

        c = mk()
        code = install(c)
        check(code == 1 and len(c.problems) == 1 and "diferente" in c.problems[0],
              "diretório diferente em ~/.agents/skills/llm-learning é recusado, e só ele")
        check(different.is_dir() and not different.is_symlink(), "o diretório recusado fica intacto")
        for d in (claude / "skills", home / ".agents" / "skills"):
            for n in SKILLS:
                if d / n == different:
                    continue
                check(points_into_repo(d / n), f"{(d / n).relative_to(home)} aponta para o repositório")
        check(points_into_repo(home / ".local" / "bin" / "kb"), "kb no PATH aponta para kb.py")
        md = (claude / "CLAUDE.md").read_text()
        check("task-observer:inicio" not in md and "velho" not in md, "seção antiga do CLAUDE.md removida")
        check(md.count("agent-learning:inicio") == 1 and "serena:fim" in md, "bloco gravado uma vez, serena preservado")
        check("{{" not in md and str(home / ".agent-learning") in md, "placeholders renderizados")
        check("Ana Tester reconheceu" in md and NOTES_DEFAULT in md, "dono e notas padrão no bloco")
        cfgdir = home / ".config" / "agent-learning"
        cfgdir.mkdir(parents=True)
        (cfgdir / "install.json").write_text(json.dumps({"owner": "Ana", "notes": "Vault | skill `x`", "y": 1}))
        check(load_config(home, {}) == {"owner": "Ana", "notes": "Vault | skill `x`"},
              "install.json local: lê dono e notas, ignora o resto")
        for p in (codex / "AGENTS.md", gemini / "GEMINI.md"):
            check(read(p).count("agent-learning:fim") == 1, f"bloco em {p.relative_to(home)}")
        s = json.loads((claude / "settings.json").read_text())
        cmds = [h["command"] for g in s["hooks"]["SessionStart"] for h in g["hooks"]]
        check(cmds == ["outro.sh", hook_command("claude")], "settings.json: hook antigo fora, novo dentro, outro mantido")
        check(not (claude / "hooks" / LEGACY_HOOK).exists(), "script do hook antigo saiu de ~/.claude/hooks")
        import tomllib
        tm = tomllib.loads((codex / "config.toml").read_text())
        check(tm["hooks"]["SessionStart"][0]["hooks"][0]["command"] == hook_command("codex")
              and tm["hooks"]["Stop"] and tm["hooks"]["state"]["foo"] == 1, "config.toml válido com o hook e o resto")
        g = json.loads((gemini / "settings.json").read_text())
        check(g["security"]["auth"] == "x" and g["hooks"]["SessionStart"][0]["hooks"][0]["name"] == "agent-learning",
              "settings.json do Gemini com o hook e o resto")
        root = home / ".agent-learning"
        check((root / "skill-observations" / "observation-log" / "0001-x.md").exists(), "log movido para a raiz nova")
        moved = claude / "skill-observations" / "MOVED.md"
        check(moved.exists() and str(root) in moved.read_text().splitlines()[0], "MOVED.md nomeia a raiz nova na primeira linha")
        r = subprocess.run([sys.executable, str(KB_PY), "validate", "--root", str(root / "knowledge")],
                           capture_output=True, text=True)
        check(r.returncode == 0, "base llm-learning criada e válida")
        check((c.backups / ".claude" / "CLAUDE.md").read_text().count("velho") == 1
              and (c.backups / ".claude" / "skills" / "task-observer" / "SKILL.md").exists()
              and (c.backups / ".claude" / "hooks" / LEGACY_HOOK).exists(), "cópias de segurança guardadas")
        r = subprocess.run(["bash", str(HOOK_SCRIPT), "--agent", "codex"], capture_output=True, text=True,
                           env={**os.environ, "HOME": str(home), "AGENT_LEARNING_HOME": str(root)})
        ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        check("1 open observations" in ctx and "units in" in ctx, "session-start.sh lê a raiz nova")
        units = home / ".config" / "systemd" / "user"
        svc, tmr = read(units / SERVICE), read(units / TIMER)
        check("{{" not in svc + tmr and str(SCHED / "weekly-review.sh") in svc
              and f"AGENT_LEARNING_HOME={root}" in svc and "Persistent=true" in tmr,
              "unidades do systemd renderizadas")
        log_calls = read(calls)
        check("enable --now" in log_calls and "daemon-reload" in log_calls, "timer recarregado e ligado")
        reg = read(root / "skill-observations" / "scheduler-registered.txt").splitlines()
        check(len(reg) > 1 and re.fullmatch(r"\d{4}-\d\d-\d\d", reg[0]) and reg[1] == f"workspace: {root}",
              "scheduler-registered.txt com a data e o caminho do workspace")

        shutil.rmtree(different)
        c = mk()
        install(c)
        check(not c.problems and points_into_repo(different), "segunda execução liga o que faltava")
        after = snapshot(home)
        c = mk()
        install(c)
        check(c.changes == 0 and snapshot(home) == after, "terceira execução não muda nada")

        c = mk()
        uninstall(c)
        md = (claude / "CLAUDE.md").read_text()
        check("agent-learning" not in md and "serena:fim" in md, "desinstalar tira o bloco e mantém o resto")
        check(not any(points_into_repo(d / n) for d in (claude / "skills", home / ".agents" / "skills") for n in SKILLS),
              "desinstalar tira os links")
        check("agent-learning" not in (codex / "config.toml").read_text()
              and tomllib.loads((codex / "config.toml").read_text())["hooks"]["Stop"], "desinstalar tira o hook do Codex")
        s = json.loads((claude / "settings.json").read_text())
        check([h["command"] for g in s["hooks"]["SessionStart"] for h in g["hooks"]] == ["outro.sh"],
              "desinstalar tira o hook do Claude")
        check("SessionStart" not in json.loads((gemini / "settings.json").read_text()).get("hooks", {}),
              "desinstalar tira o hook do Gemini")
        check((root / "skill-observations" / "observation-log" / "0001-x.md").exists(), "desinstalar não toca nos dados")
        check(not (units / TIMER).exists() and "disable --now" in read(calls)
              and not (root / "skill-observations" / "scheduler-registered.txt").exists(),
              "desinstalar desliga o timer e tira o marcador")
    print(f"{'OK' if not fails else 'FALHOU'}: {len(fails)} falha(s)")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="install.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="mostra o que faria, sem gravar")
    ap.add_argument("--uninstall", action="store_true", help="tira links, blocos e hooks")
    ap.add_argument("--selftest", action="store_true", help="roda os testes num HOME falso")
    ap.add_argument("--home", type=Path, default=Path.home())
    ap.add_argument("--owner", default=None,
                    help="nome do dono no bloco e na base (padrão: install.json, senão git user.name)")
    ap.add_argument("--notes", default=None,
                    help="destino dos fatos de negócio no bloco, como 'destino | ferramenta' (padrão: install.json)")
    ap.add_argument("--projects", type=Path, default=None,
                    help="pasta dos repositórios (padrão: ~/Documents/projects, senão ~)")
    ap.add_argument("--no-schedule", action="store_true", help="não liga a revisão semanal agendada")
    ap.add_argument("--review-engine", choices=ENGINES, default="claude",
                    help="quem roda a revisão agendada (padrão: claude)")
    ap.add_argument("--review-calendar", default=CALENDAR,
                    help=f"OnCalendar do timer (padrão: {CALENDAR!r})")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if "'" in str(REPO):
        raise SystemExit("o caminho do repositório não pode ter aspas simples")
    home = a.home.expanduser().resolve()
    projects = a.projects or (home / "Documents" / "projects")
    if not projects.is_dir():
        projects = home
    cfg = load_config(home, os.environ)
    c = Ctx(home, dict(os.environ), dry=a.dry_run, owner=a.owner or cfg.get("owner") or git_name(),
            projects=projects, engine=a.review_engine, calendar=a.review_calendar,
            schedule=not a.no_schedule, notes=a.notes or cfg.get("notes") or NOTES_DEFAULT)
    return uninstall(c) if a.uninstall else install(c)


if __name__ == "__main__":
    sys.exit(main())
