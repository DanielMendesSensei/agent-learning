---
id: {domain_short}.{topic}.{slug}
kind: pattern
domain: {domain}
title: {title}
summary: {solution} for {recurring_problem}
triggers: ["{task_condition}"]
tags: [{tag}]
confidence: (high | medium | low)
evidence: [{evidence_type}]
version_pins: {}
related: [@{unit_id}]
status: active
created: {yyyy-mm-dd}
updated: {yyyy-mm-dd}
changelog: []
---

# {title}

## Context
{forces_in_play}

## Problem
{recurring_problem}

## Solution
{core_idea}

## Structure
```
{component} → {component}
```

## Parameters
| Parameter | Value/Range | Rationale |
|---|---|---|

## Invariants
- MUST {invariant}

## Trade-offs
- (+) {benefit}
- (−) {cost}

## Related
- @{unit_id}
