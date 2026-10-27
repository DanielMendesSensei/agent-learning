# agent-learning

Português: [README.pt-BR.md](README.pt-BR.md)

Two continuous-learning tools for coding agents, wired into every AI on your
machine: Claude Code, Codex (GPT), Gemini CLI and, through plain text, any
other.

- **Task Observer** learns from what went wrong. Every correction you make,
  every broken rule and every gap in a skill becomes an observation, and a
  weekly review turns the observations into better skills.
- **llm-learning** keeps what went right. When you recognise a piece of
  technical work ("great work, save this"), the agent writes a knowledge unit
  and brings it back on the next similar task.

Both read and write the same place, `~/.agent-learning`, outside any agent's
own folder. What Claude learns in one session, Codex uses in the next, and
the other way round.

It joins two existing projects:
[Task Observer](https://github.com/rebelytics/one-skill-to-rule-them-all), by
Eoghan Henn, and [llm-learning](https://github.com/Jonhvmp/llm-learning), by
Jonh. This repository adds the installer, the adapters for each agent, the
weekly scheduler and the `kb` command.

The usage guide is in [PLAYBOOK.md](PLAYBOOK.md). Where each component comes
from, and under which licence, is in [NOTICE.md](NOTICE.md).

## Requirements

- Linux with systemd user units, for the scheduled review. Elsewhere the
  review runs from any scheduler (see the playbook).
- Python 3, standard library only.
- git and `flock`.
- At least one of Claude Code, Codex or Gemini CLI.

## Install

```bash
python3 install.py --dry-run
```

```bash
python3 install.py
```

The first shows what would change and writes nothing. The second applies it.
Running it again is safe: whatever is already right shows up as "em dia"
(the installer speaks Portuguese; it means "up to date"). The
instructions block it writes is in Portuguese too, and agents follow it
whatever language you work in. Before touching a
file, the installer keeps a copy in
`~/.local/state/agent-learning/backups/<date-time>/`.

Two steps are left after the install, and only you can take them:

1. **Codex:** open Codex, run `/hooks` and approve the agent-learning
   `SessionStart` hook. Without it, Codex gets no protocol reminder at the
   start of a session.
2. **Gemini CLI:** Gemini runs hooks only in trusted folders. Trust, from
   Gemini itself, the folders where you want the reminder.

Useful options: `--no-schedule` (no scheduled review), `--review-engine codex`
(the scheduled review runs on Codex), `--review-calendar 'Fri *-*-* 17:00:00'`,
`--uninstall` and `--selftest`.

## Personal settings

The instructions block names two things that belong to you: the owner, whose
praise counts as recognition, and where business facts go. Both come from
`~/.config/agent-learning/install.json` (or
`$XDG_CONFIG_HOME/agent-learning/install.json`), which lives outside the
repository:

```json
{
  "owner": "Ana",
  "notes": "Notion | the Notion MCP server"
}
```

`notes` takes the form `destination | tool`. Without the file, the owner is
your `git config user.name` and business facts go to your personal notes,
through whatever tool your other instructions name. `--owner` and `--notes`
override the file for a single run.

## What is in here

| Folder | Contents |
|---|---|
| `skills/task-observer/` | Task Observer v3.8.1, unchanged |
| `skills/llm-learning/` | The skill that wraps the llm-learning base, the `kb` command and the evals |
| `knowledge-template/` | The llm-learning base skeleton (README, PROTOCOL, schema, templates) |
| `adapters/` | The instructions block for CLAUDE.md, AGENTS.md and GEMINI.md, and the session-start hook |
| `scheduler/` | The weekly review: script, prompts, systemd units and the plugin that hands the skill to the scheduled Claude |
| `prompts/` | Texts to paste, such as the handoff from a chat with no shell |
| `install.py` | Installs, updates, uninstalls and tests itself |

## Where the data lives

| Path | What |
|---|---|
| `~/.agent-learning/skill-observations/` | Observation log, cross-cutting principles, review markers |
| `~/.agent-learning/skill-updates/` | Reviewed skills waiting for you to install them |
| `~/.agent-learning/knowledge/` | The llm-learning base |
| `~/.local/state/agent-learning/review-logs/` | One log per scheduled review run |

`~/.agent-learning` is a git repository. The review script makes the
commits, with explicit paths and no agent attribution.

## Licence

The original code is under the MIT licence ([LICENSE](LICENSE)). Task
Observer, in `skills/task-observer/`, keeps its CC BY 4.0 licence, and the
llm-learning skeleton in `knowledge-template/` is included with its author's
permission. Details in [NOTICE.md](NOTICE.md).
