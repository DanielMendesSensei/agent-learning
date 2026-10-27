---
id: {domain_short}.{topic}.{slug}
kind: playbook
domain: {domain}
title: {title}
summary: {what_it_achieves} when {condition}
triggers: ["{task_condition}"]
tags: [{tag}]
confidence: (high | medium | low)
evidence: [{evidence_type}]
version_pins: {{package}: "{version}"}
prerequisites: [@{unit_id}]
related: [@{unit_id}]
status: active
created: {yyyy-mm-dd}
updated: {yyyy-mm-dd}
changelog: []
---

# {title}

## Context
- Applies when: {condition}
- Does not apply when: {anti_condition}

## Outcome
{measurable_end_state}

## Procedure
1. {step} → {observable_result}
2. ...

## Parameters
| Parameter | Value/Range | Scale/Unit | Rationale |
|---|---|---|---|
| {param} | {value} | <unit> | {why} |

## Invariants
- MUST {invariant}
- NEVER {forbidden}

## Pitfalls
- {symptom} ⇐ {root_cause} → {fix}

## Verification
- [ ] {check} → {pass_criterion}

## Related
- @{unit_id} — {relation}
