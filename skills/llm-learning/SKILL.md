---
name: llm-learning
description: Use when the owner praises a piece of technical work or asks to keep it ("mandou muito bem", "excelente", "guarda isso", "vale guardar", "save this"), when starting a technical task that a past learning may already cover, or when a knowledge unit you loaded turns out wrong in practice.
license: "MIT. Wraps the knowledge-base layout of Jonhvmp/llm-learning, used with its author's permission; see NOTICE.md in the agent-learning repository."
metadata:
  author: Daniel Mendes
  source: https://github.com/DanielMendesSensei/agent-learning
  requires: "binary:python3>=3.9; python:pyyaml"
  version: 0.1.0
---

# llm-learning

A persistent base of technical know-how the owner recognised as high level.
The base's own `PROTOCOL.md` holds the format rules. This file adds the two
things agents got wrong without it: when a signal counts, and that ids and
paths come from `kb`, never from your own reading of the naming rules.

**Command:** `kb <command> ...`, installed on PATH by agent-learning. Where
`command -v kb` finds nothing, call `python3 <skill dir>/scripts/kb.py
<command> ...` written out in full each time. Never put the command in a
shell variable: zsh does not split it into words.

**Root:** `$AGENT_LEARNING_KB`, else `~/.agent-learning/knowledge`. When your
instructions name another root, put `--root <root>` after the command on
every call (`kb index --root <root>`).

## Retrieve, at the start of every technical task

1. Run `kb index` and match the task against each unit's triggers, tags
   and domain.
2. Read at most 5 matching units, highest confidence first. Check their
   Pitfalls before acting and keep their Invariants.
3. Name the ids you applied in your reply.
4. A unit that proves wrong in practice is fixed in place (PROTOCOL §5),
   then `kb register <path>`, `kb journal --signal "correction"
   --summary "<what was wrong>" --updated <id>` and `kb validate`.

## Capture: the owner's words decide, not your opinion of the work

| The owner says | You do |
|---|---|
| An explicit ask to keep it: "guarda isso", "vale guardar", "salva esse aprendizado", "registra isso", "save this" | Capture in this turn |
| Praise that rates the level: "excelente", "mandou muito bem", "nível alto", "brilhante", "great work" | Capture in this turn |
| Plain thanks or a nod: "boa", "valeu", "ok", "show", "beleza", "funcionou", "perfeito" on its own, 👍 | Write nothing. You may offer the capture in one line, then wait for a yes |
| Nothing, or only your own sense that it went well | Never capture |

Praise aimed at one part of the work covers that part only. The rest of the
same message may be a correction or a business fact, and those go elsewhere
(see Routing).

## Capture pipeline

1. Keep only what was verified in this work and is either transferable or
   costly to find again. A hunch from general knowledge goes in your reply,
   not in the unit. Replace project, client and product names with
   `{placeholders}`; keep version pins and tuned numbers.
2. Dedupe with `kb index`. If a unit already covers it, update that file
   instead of creating a second one.
3. Scaffold with `kb new --kind <kind> --domain <d> --topic <t>
   --title ... --summary ... --trigger "..." --confidence <c>
   --evidence owner-recognized [--evidence runtime-verified]`. Add
   `--scope "..."` when the domain is new. Use the path it prints.
4. Fill every section of that file and replace every template line. Write
   it with your file-editing tool. In a shell, use only a quoted heredoc
   (`<<'EOF'`): units hold backticks, and an unquoted heredoc runs them
   as commands on the owner's machine.
5. `kb register <path>`, then `kb journal --signal "<owner's words>"
   --summary "..." --created <id>`.
6. `kb validate` must print OK before you report. On an error, fix and
   run it again.
7. Report in at most 5 lines: id, path, and the trigger that will bring it
   back.

## Routing

This skill takes only recognised technical know-how. A correction, friction
or a broken rule goes to the Task Observer. A business fact (client, deal,
price, date) goes to the owner's notes. A working preference goes to your
own memory. One owner message can feed several of them; your instructions
file holds the full table.

## Without a shell

When you cannot run commands, draft the unit as text and give it to the
owner with the prompt in `prompts/chat-handoff.md` of the agent-learning
repository, so a session with a shell can file it.
