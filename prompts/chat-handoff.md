# Handoff from a chat with no shell

Português: [chat-handoff.pt-BR.md](chat-handoff.pt-BR.md)

Use this when the recognised work happened in an AI that cannot run
commands: ChatGPT on the web, Claude.ai, Gemini in the browser, a company
chat. It has no way to write to the base. So the work becomes text there,
and another session, one with a shell, records it.

There are two stages, each with a text to paste.

## Stage 1: in the chat with no shell

Paste this right after the praise ("great work, save this"):

```text
We have no shell here, so prepare the learning for me to record in another
session. Reply with a single code block and nothing outside it, in this
format:

KIND: playbook | pattern | pitfall-set | reference | meta-skill
DOMAIN: <short domain in English, lowercase, e.g. linux-ops>
TOPIC: <short topic in English, lowercase, e.g. systemd-timers>
TITLE: <title in English>
SUMMARY: <one sentence in English: what it is and when to use it>
TRIGGER: <task condition in English, with {placeholders}>
TRIGGER: <repeat the line for each trigger>
TAG: <one word; repeat the line for each tag>
PIN: <package=version; one per line; leave out if none>
CONFIDENCE: high | medium | low
EVIDENCE: owner-recognized
EVIDENCE: runtime-verified   (only if it ran and was checked in this conversation)
OWNER SAID: <my words of recognition, verbatim>
BODY:
<the unit body in English, in short sections: Context, Procedure or
Pitfalls, Invariants, Verification>

Rules:
- Only what was verified in this conversation goes in. A guess from general
  knowledge stays out of the block, or goes in with CONFIDENCE: low.
- Replace project, client and product names with {placeholders}. Keep
  versions and tuned numbers.
- If the same message of mine also carried a correction or a business fact,
  do not mix them in: list them after the block, one line each, marked
  CORRECTION or BUSINESS.
```

Copy the block it returns.

## Stage 2: in a session with a shell

Open a session of any agent that runs commands on this machine (Claude
Code, Codex, Gemini CLI) and paste:

```text
Record the learning below in the llm-learning base. It came from a chat with
no shell. Load the llm-learning skill and follow its capture pipeline, with
these rules:

1. Run `kb index` and check whether a unit already covers the subject. If
   one does, update that file instead of creating another.
2. Otherwise create it with `kb new`, mapping each field of the block to the
   option of the same name (--kind, --domain, --topic, --title, --summary,
   --trigger, --tag, --pin, --confidence, --evidence). If the domain is new,
   add --scope with one sentence about it. Use the path the command prints.
3. Write the BODY into the file with the file-editing tool, never with an
   unquoted heredoc.
4. `kb register <path>`, then `kb journal --signal "<OWNER SAID>"
   --summary "<SUMMARY>" --created <id>` (or --updated, if you updated one).
5. `kb validate` must print OK. If it fails, fix it and run it again.
6. Reply in at most 5 lines: id, path and the trigger that will bring the
   unit back.

Lines marked CORRECTION go to the Task Observer, created through
new-observation.sh. Lines marked BUSINESS go to my notes. Neither goes into
the base.

<paste the stage 1 block here>
```

## Why not paste the body straight into a file

`kb new` decides the id and the path, and `kb register` keeps the manifest
current. In the evals, hand-written units broke both rules
(`skills/llm-learning/evals/results.md`). That is why the handoff always goes
through a session that runs `kb`.

## Task Observer observations with no shell

A correction in a chat with no shell follows Task Observer's own handoff-doc
mode (`skills/task-observer/references/environments.md`, section
"Handoff-doc mode"). It already defines the format and how the next session
processes what arrives.
