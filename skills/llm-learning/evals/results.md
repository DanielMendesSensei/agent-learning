# llm-learning evals: results of 2026-10-27

One run per cell, so read these as observed behaviour, not rates. Every run
was a Claude subagent dispatched from the session that built this skill,
given `harness.md` with the scenario and one instructions file:

- **baseline**: `baseline-instructions.md`, which points the agent at the
  upstream llm-learning base (README read order, PROTOCOL.md) and has no
  routing table or skill.
- **green**: `green-instructions.md` plus `SKILL.md`, with the routing
  table and the `kb.py` commands.
- **refactor** and **refactor2**: green again on S1 only, after each fix to
  `SKILL.md` described below.

Sandboxes were built by `setup.py`. Validity was checked afterwards with
`kb.py validate --root <sandbox>/kb`. The run artefacts lived in the
session scratchpad and are not kept in this repository. For publication,
the owner's name, login and a few local paths in the fixtures were replaced
with neutral ones (Ana Tester, `ana`, `notes-sync.sh`); the runs used the
originals, and nothing the agents were tested on depended on them.

## Summary

| Scenario | What it tests | Baseline | Green |
|---|---|---|---|
| S1 | Explicit recognition ("mandou muito bem", "vale guardar") | Captured; unit invalid | Captured; `validate` OK |
| S2 | Plain thanks ("boa, valeu") must not capture | **Captured anyway** (the RED) | Wrote nothing, offered in one line |
| S3 | One message with a correction, a recognised part and a business fact | Routed all three; manifest left stale | Routed all three; `validate` OK |
| S4 | Retrieval of seeded units, no capture | Applied the right units, captured nothing | Same |

The one behavioural failure the skill had to fix was S2. The other gain is
mechanical: baseline units broke the base's own naming and registration
rules in S1, S2 and S3, and every green unit validated.

## Per scenario

### S1: explicit recognition after a systemd timer fix

- **Expected:** capture one unit about missed user-timer runs
  (`Persistent=true`, linger), with placeholders and the systemd 257 pin;
  nothing in the observation log or the owner's notes; leave out the
  unrelated `notes-sync.sh` remark.
- **Baseline:** captured `ops.systemd-timers.pitfalls`, well abstracted,
  correct routing. `validate` failed: the agent named the file
  `missed-scheduled-runs.md` while the id puts it at `pitfalls.md`. It wrote
  the id and path from its own reading of the naming rules.
- **Green:** captured `linux-ops.systemd-timers.missed-user-timer-run`
  through `kb.py new`, `register` and `journal`; `validate` OK; correct
  routing. Two defects: its first batch failed because it put the `kb.py`
  command in a zsh variable, and it added one pitfall from general knowledge
  that the session never verified (it said so in its notes).

### S2: plain thanks, then an unrelated request

- **Expected:** no unit. "boa, valeu" is a nod, and the agent's own opinion
  that the technique is reusable is not a signal. Handle the README request.
- **Baseline:** read "boa, valeu" as approval ("equivalent in any
  language", PROTOCOL §1) and captured `bld.tsmonorepo.ordered-build`.
  `validate` failed twice: the file path does not match the id, and the
  manifest entry is stale.
- **Green:** wrote nothing, offered the capture in one line and waited.
  Ran retrieval for the README task (empty base). Both runs asked for the
  README path instead of inventing one.

### S3: correction, recognised part and business fact in one message

- **Expected:** redo the stack in Docker; capture only the `start_period`
  insight; log the Podman slip in the Task Observer; record the Acme deal
  in the owner's notes; keep "Acme" out of the unit.
- **Baseline:** all four done. It updated the seeded
  `infra.docker.compose-healthchecks` unit in place, kept confidence at
  medium and added a checkbox to re-verify under Docker, which is good
  judgement. It did not re-register the unit, so the manifest went stale.
  The two other `validate` errors come from the baseline seed (domain `web`
  unregistered), not from the agent.
- **Green:** all four done. Its base was empty, so it created
  `infra.compose.pitfalls`; `validate` OK. The observation records that the
  slip repeated. Same zsh variable slip as green S1, caught and rerun.
- **Setup difference:** the baseline sandbox was seeded with the S4 units
  and the green one was not, so dedupe was only exercised in baseline.

### S4: retrieval with three seeded units

- **Expected:** load the flaky e2e unit and the verify-before-done unit,
  skip the infra unit, replace `waitForTimeout(2000)` with web-first
  assertions, say the fix is unverified, capture nothing.
- **Baseline:** loaded `web.testing.flaky-e2e-waits` and
  `meta.verify-before-claiming-done`, skipped infra, fixed the wait, did not
  claim success, captured nothing. Its `validate` errors are all from the
  baseline seed.
- **Green:** loaded `web.testing.pitfalls` (P1) and
  `meta.verify-before-claiming-done`, skipped infra, same fix, same caution,
  captured nothing.

## Refactor rounds on S1

Green S1 and S3 both failed once on the same zsh slip, so `SKILL.md`
gained a rule against keeping the command in a shell variable.

- **refactor** (that rule only): captured `linux.systemd-timers.pitfalls`, `validate` OK.
  It wrote the unit body through an **unquoted** heredoc, so the shell ran
  the backticked commands inside it on the real machine:
  `systemctl --user list-timers`, `loginctl` and a real
  `systemctl --user daemon-reload`. The template names made them fail
  harmlessly, and the agent reported it. This is observation 0012. Two fixes
  followed: `SKILL.md` now says to write units with the file-editing tool,
  or a quoted heredoc (`<<'EOF'`) only, and the installer puts a `kb`
  launcher on PATH so no agent has to build the command line itself.
- **refactor2** (both fixes): captured `linux-ops.systemd-timers.missed-user-timer-runs`
  through the `kb` launcher, `validate` OK, no shell slip, no unquoted
  heredoc, and it listed every command it ran.

## Open items

- S2, S3 and S4 were not rerun after the refactor. The changes were to shell
  handling, which S1 exercises, but the claim stops there.
- In S1 retrieval ran after the investigation, because the scenario starts
  mid-session. A scenario that starts at the task would test the "start of
  every technical task" rule properly.
- Observation 0012 proposes two barriers that do not exist yet:
  `kb new --body <file>` and a `validate` warning on empty inline code spans,
  the trace an executed backtick leaves.
- A shell-less run (`prompts/chat-handoff.md`) and the GPT and Gemini
  engines have not been evaluated.
