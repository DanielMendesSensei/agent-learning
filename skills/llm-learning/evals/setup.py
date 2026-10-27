#!/usr/bin/env python3
"""Build a fresh eval sandbox and the prompt that drives it.

Usage:
    python3 setup.py <scenario: S1..S4> <dest-dir> <instructions: baseline|green>

Creates <dest-dir>/{kb,obs,sb,skills,...} and writes <dest-dir>.prompt.md, the
full text to hand to the agent under test. <dest-dir> must not exist.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
KB = SKILL / "scripts" / "kb.py"


def kb(*args: str) -> str:
    r = subprocess.run([sys.executable, str(KB), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"kb.py {' '.join(args[:2])} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def fill(path: str, body: str) -> None:
    """Keep kb.py's frontmatter, replace everything after it with body."""
    p = Path(path)
    text = p.read_text()
    end = text.index("\n---\n", 4) + 5
    p.write_text(text[:end] + "\n" + body.lstrip("\n"))


S4_UNITS = [
    (
        ["--kind", "pitfall-set", "--domain", "web", "--topic", "testing",
         "--scope", "browser and end-to-end testing of web apps",
         "--title", "flaky end-to-end test waits",
         "--summary", "failure modes and fixes when {browser_test} fails intermittently because of timing",
         "--trigger", "{e2e_test} fails intermittently in {ci}",
         "--trigger", "replacing fixed sleeps in {browser_test}",
         "--tag", "e2e", "--tag", "flaky", "--tag", "playwright", "--tag", "timing",
         "--confidence", "high", "--evidence", "runtime-verified", "--evidence", "owner-recognized",
         "--pin", "playwright=1.48"],
        """
# flaky end-to-end test waits pitfalls

## Context
{browser_test} that passes locally and fails in {ci} at random.

## Pitfalls
| ID | Symptom | Root cause | Fix | Pin |
|---|---|---|---|---|
| P1 | passes locally, times out in {ci} | fixed sleep shorter than {ci} render time | wait on {locator} state, never on time | playwright@1.48 |
| P2 | click lands on wrong element | {animation} still running | wait for animation end or disable animations in test config | |

## Related
- @meta.verify-before-claiming-done
""",
    ),
    (
        ["--kind", "playbook", "--domain", "infra", "--topic", "docker",
         "--scope", "containers and local service stacks",
         "--slug", "compose-healthchecks",
         "--title", "compose healthchecks before dependent services",
         "--summary", "start {service} only after {dependency} is healthy in docker compose",
         "--trigger", "{service} starts before {database} is ready in docker compose",
         "--tag", "docker", "--tag", "compose", "--tag", "healthcheck",
         "--confidence", "medium", "--evidence", "runtime-verified",
         "--pin", "docker-compose=2.29"],
        """
# compose healthchecks before dependent services

## Context
- Applies when: {service} crashes on boot because {dependency} is not accepting connections.
- Does not apply when: {dependency} is external.

## Outcome
{service} boots once, with no restart loop.

## Procedure
1. add healthcheck to {dependency} → status turns healthy
2. depends_on: {dependency}: condition: service_healthy → {service} waits

## Parameters
| Parameter | Value/Range | Scale/Unit | Rationale |
|---|---|---|---|
| interval | 5 | <s> | fast feedback |

## Invariants
- MUST use condition service_healthy, NEVER a sleep in entrypoint

## Pitfalls
- restart loop ⇐ depends_on without condition → add condition

## Verification
- [ ] docker compose up shows one start per service → pass

## Related
- none
""",
    ),
    (
        ["--kind", "meta-skill", "--slug", "verify-before-claiming-done",
         "--title", "verify before claiming done",
         "--summary", "run the check that proves {task} works before reporting it complete",
         "--trigger", "about to report {task} as complete",
         "--tag", "verification", "--confidence", "high", "--evidence", "owner-recognized"],
        """
# verify before claiming done

## Context
Any {task} whose result can be observed by running something.

## Principle
A result is reported only after the check that would show it failing has run and passed.

## Procedure
1. name the observable that proves {task} works
2. run it and read the output
3. report the output, not the expectation

## Signals
- Use when: about to write "done", "fixed" or "works"
- Stop/escalate when: the check cannot run here; say so instead of claiming

## Anti-patterns
- reporting from the diff alone → regressions reach the owner

## Related
- none
""",
    ),
]

LOGIN_SPEC = """import { test, expect } from '@playwright/test';

test('login redirects to dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('#email', 'qa@example.test');
  await page.fill('#password', 'qa-password');
  await page.click('button[type=submit]');
  await page.waitForTimeout(2000);
  expect(page.url()).toContain('/dashboard');
  expect(await page.locator('h1').textContent()).toBe('Dashboard');
});
"""

ACME_NOTE = "# Acme\n\n> Atualizado em: 2026-10-20\n\nCliente em negociação de piloto. Sem valor fechado.\n"


def build(scenario: str, dest: Path, mode: str) -> None:
    if dest.exists():
        raise SystemExit(f"{dest} exists; use a fresh directory")
    dest.mkdir(parents=True)
    kbroot = dest / "kb"
    kb("init", str(kbroot), "--owner", "Ana Tester")
    if scenario == "S4":
        for args, body in S4_UNITS:
            out = kb("new", "--root", str(kbroot), *args)
            rel = next(l.strip() for l in out.splitlines() if l.strip().endswith(".md") and (kbroot / l.strip()).is_file())
            path = str(kbroot / rel)
            fill(path, body)
            kb("register", "--root", str(kbroot), path)
        kb("validate", "--root", str(kbroot))
        (dest / "repo/tests/e2e").mkdir(parents=True)
        (dest / "repo/tests/e2e/login.spec.ts").write_text(LOGIN_SPEC)
    if scenario == "S3":
        (dest / "acme-app").mkdir()
    (dest / "obs/observation-log").mkdir(parents=True)
    shutil.copy(HERE / "new-observation-stub.sh", dest / "obs/new-observation.sh")
    (dest / "sb/Inbox").mkdir(parents=True)
    (dest / "sb/Inbox/Inbox.md").write_text("# Inbox\n")
    (dest / "sb/Projects/Acme").mkdir(parents=True)
    (dest / "sb/Projects/Acme/Acme.md").write_text(ACME_NOTE)
    if mode == "green":
        skill = dest / "skills/llm-learning"
        (skill / "scripts").mkdir(parents=True)
        shutil.copy(SKILL / "SKILL.md", skill / "SKILL.md")
        shutil.copy(KB, skill / "scripts/kb.py")

    instructions = (HERE / f"{mode}-instructions.md").read_text()
    scenario_text = (HERE / "scenarios" / f"{scenario}.md").read_text()
    prompt = (HERE / "harness.md").read_text()
    prompt = prompt.replace("{INSTRUCTIONS}", instructions.strip())
    prompt = prompt.replace("{SCENARIO}", scenario_text.strip())
    prompt = prompt.replace("{SANDBOX}", str(dest))
    Path(str(dest) + ".prompt.md").write_text(prompt)
    print(Path(str(dest) + ".prompt.md"))


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[3] not in ("baseline", "green"):
        raise SystemExit(__doc__)
    build(sys.argv[1], Path(sys.argv[2]).resolve(), sys.argv[3])
