# Playbook: Task Observer and llm-learning day to day

Português: [PLAYBOOK.pt-BR.md](PLAYBOOK.pt-BR.md)

## The idea in one minute

Every session with an agent produces two kinds of learning, and each has its
owner.

- **What went wrong goes to Task Observer.** You corrected the agent, it
  broke a written rule, a skill did not cover a case. That becomes an
  observation in the log. Once a week the review reads the observations and
  prepares better versions of the skills and instructions.
- **What went right goes to llm-learning.** You praised a piece of technical
  work and asked to keep it. That becomes a knowledge unit, short and free of
  project names, which comes back by itself on the next similar task.

Both live in `~/.agent-learning`, which every agent reads. It does not matter
that the mistake happened in Claude and the win in Codex: it all lands in
the same place.

## Where each thing goes

| What happened | Goes to | Who writes it |
|---|---|---|
| You recognised a piece of technical work ("great work", "save this", "mandou muito bem", "guarda isso") | llm-learning | the `llm-learning` skill, through the `kb` command |
| You corrected the agent, it broke a rule, a skill showed a gap | Task Observer | `new-observation.sh` |
| A business fact: client, deal, amount, date, person | your notes | whatever the `notes` setting names (see the README) |
| One of your working preferences | the agent's own memory | the agent |

One message can go to several places. For example:

> You were supposed to open a PR, not commit to main. But the retry with
> backoff came out great, save this. Oh, and Beta renewed until March.

That produces an observation (the correction), a unit (the retry) and a
business note (the renewal).

## What to say to the agent

| You want to | Say | What happens |
|---|---|---|
| Keep a win | "save this", "worth keeping", "great work" | The agent writes the unit in the same reply and shows the id, path and trigger |
| Just say thanks | "nice", "thanks", "ok", "it works", "perfect" | Nothing is written. At most it offers to keep it, in one line |
| Keep only one part | "the healthcheck part came out great, save this" | Only that part becomes a unit |
| Correct it | Say what was wrong, in your own words | It becomes an observation. No need to ask |
| Run the review now | "run the weekly review" | The agent loads Task Observer and follows the review procedure |

The skill lists these signals in Portuguese and English, and any language
works the same way. The praise is the trigger. The agent does not write a
unit because it thinks the work was good: that is exactly the mistake the
evals caught (see `skills/llm-learning/evals/results.md`).

## A typical session

1. **Start.** The session-start hook reminds the agent of the Task Observer
   protocol and says how many observations are open. If the review is
   overdue, the agent offers to run it, once. You can ignore it.
2. **Technical task.** The agent runs `kb index`, loads up to 5 units that
   match the task and cites the ids it used.
3. **You correct something.** The agent creates the observation in the same
   turn, without stopping the work.
4. **You praise something.** The agent writes the unit and runs
   `kb validate` before replying.
5. **End of the task.** The agent lists the observations written during the
   session, read from the log, not from memory.

## The weekly review

It runs by itself every Monday at 10:00 (with up to 15 minutes of random
delay). If the computer is off or asleep at that time, it runs as soon as
the computer comes back.

What it does:

- reads the open observations and groups the ones about the same thing;
- applies the simple changes to copies of the skills, in
  `~/.agent-learning/skill-updates/`. Nothing takes effect until you install
  it;
- leaves to you what is your call: a new skill, a removal or a large
  restructure, an uncertain item, observations that conflict;
- writes the report to
  `~/.agent-learning/skill-observations/reviews/<date>/REVIEW.md`;
- commits to the workspace repository and sends a desktop notification.

Afterwards, read `REVIEW.md` and `skill-updates/PENDING.md`. In the next
interactive session the agent says how many updates are waiting for review.
Ask it to review them and install the ones you approve.

### Running it by hand

Test access without running the review:

```bash
systemctl --user start weekly-skill-review@probe.service
```

Run the full review now:

```bash
systemctl --user start weekly-skill-review@full.service
```

See when the next run is:

```bash
systemctl --user list-timers weekly-skill-review.timer
```

Find the most recent logs:

```bash
ls -t ~/.local/state/agent-learning/review-logs/ | head -n 3
```

### Notification messages

The script writes its notifications in Portuguese. What each one means:

| Message | Meaning |
|---|---|
| `revisão <data> concluída` | It worked. The report path comes with it |
| `sonda ok` | The agent managed to write to the workspace from inside the unit |
| `revisão pulada: workspace ... fora do ar` | `~/.agent-learning` does not exist or could not be opened |
| `disparou em ... e não registrou revisão` | The agent ran and did not finish. Check the log |
| `ATENÇÃO: travessões em ...` | The review wrote a dash in some text. Fix it before installing |
| `outra revisão já está rodando` | Two runs at the same time. The second one left without doing anything |

### How it stays isolated

The scheduled review runs the agent without your settings, hooks, MCP
servers or plugins. On Claude, commands can write only inside
`~/.agent-learning`, the network stays closed, and the skill comes in
through a plugin in this repository. On Codex, `--ignore-user-config` leaves
out plugins, MCP servers and hooks, and the `workspace-write` sandbox keeps
writes inside the workspace. The script makes the commit, not the agent, so
no commit carries an AI attribution.

## Per agent

### Claude Code

Works with no extra step. The instructions block is in `~/.claude/CLAUDE.md`,
the hook in `~/.claude/settings.json` and the skills in `~/.claude/skills/`.

### Codex (GPT)

The block goes into `~/.codex/AGENTS.md` and the skills sit in
`~/.agents/skills/`, which Codex reads. The session-start hook needs your
approval: open Codex and run `/hooks`. The installer never approves it for
you.

To run the scheduled review on Codex instead of Claude:

```bash
python3 install.py --review-engine codex
```

Then run the probe to prove it works. The default engine is Claude.

### Gemini CLI

The block goes into `~/.gemini/GEMINI.md` and the skills into
`~/.agents/skills/`. Gemini runs hooks only in folders you marked as
trusted, and the installer does not touch that. Without a trusted folder the
instructions block still applies; only the session-start reminder does not
show up.

Gemini does not run the scheduled review. In headless mode it has no write
sandbox, and opening everything up with no one watching would be worse than
not running it. On Gemini, ask for the review in an interactive session.

### Choosing the model

The review script accepts `AGENT_LEARNING_MODEL`. To pin a model without the
next install wiping the choice, use a systemd drop-in:

```bash
systemctl --user edit weekly-skill-review@.service
```

And write:

```ini
[Service]
Environment=AGENT_LEARNING_MODEL=<model name>
```

### Any other AI

- **With a shell and an instructions file:** copy the block from
  `adapters/instructions-block.md` into its instructions file, replacing
  `{{REPO}}`, `{{ROOT}}` and `{{PROJECTS}}` with the real paths, `{{OWNER}}`
  with your name and `{{NOTES}}` with where business facts go. The skills
  are plain Markdown: it only needs to read `skills/<name>/SKILL.md`.
- **Chat only, no shell** (ChatGPT on the web, Claude.ai, Gemini in the
  browser): use `prompts/chat-handoff.md`. The chat AI prepares the unit as
  text and a session with a shell records it.

## The kb command

| Command | What for |
|---|---|
| `kb index` | Lists the units with their triggers and confidence |
| `kb new --kind ... --domain ... --topic ... --title ... --summary ... --trigger ... --confidence ... --evidence ...` | Creates the unit and prints its path |
| `kb register <path>` | Updates the manifest from the unit |
| `kb journal --signal "<your words>" --summary ... --created <id>` | Records the recognition in the journal |
| `kb validate` | Checks the whole base. It must print OK |

Every command accepts `--help`. The unit kinds are `playbook`, `pattern`,
`pitfall-set`, `reference` and `meta-skill`.

## Maintenance

See what an install would change:

```bash
python3 install.py --dry-run
```

Update after changing the repository (the links already point here, so only
the instructions block and the units need a fresh copy):

```bash
python3 install.py
```

Run the installer's tests in a fake HOME:

```bash
python3 install.py --selftest
```

Uninstall (removes links, blocks, hooks and the timer; keeps the workspace
and the base):

```bash
python3 install.py --uninstall
```

The backup of every changed file is in
`~/.local/state/agent-learning/backups/<date-time>/`.

## Other schedulers

systemd is the default on Linux because it catches up on a run missed while
the machine was off. Elsewhere, schedule the same script:

```text
scheduler/weekly-review.sh full
```

With `AGENT_LEARNING_ENGINE` (claude or codex) and, if you want,
`AGENT_LEARNING_HOME` in the environment.

- **cron:** does not catch up on missed runs, and cron's PATH is short.
  Check that `command -v claude` finds the binary in the PATH you pass.
- **launchd (macOS):** the script was written and tested on Linux. On macOS
  it needs `flock`, plus `stat` and `timeout` from GNU coreutils.
- **Task Scheduler (Windows):** run it through WSL, with
  `wsl.exe -e bash -lc "<path>/scheduler/weekly-review.sh full"`.

## When something does not work

| Symptom | Where to look |
|---|---|
| The agent does not load Task Observer at the start | Is the block in its instructions file? `python3 install.py --dry-run` shows it |
| Codex shows no reminder | Approval pending in `/hooks` |
| Gemini shows no reminder | The folder is not trusted |
| `kb: command not found` | `~/.local/bin` is not on PATH. Use `python3 skills/llm-learning/scripts/kb.py` |
| `kb validate` fails | The message names the file and the command that fixes it |
| The review did not run | `systemctl --user list-timers` and the most recent log |
