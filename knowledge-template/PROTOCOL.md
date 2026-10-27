---
id: root.protocol
kind: protocol
title: Capture, retrieval and maintenance protocol
summary: Deterministic rules an LLM follows to store and reuse high-level learnings.
updated: 2026-10-04
---

# Protocol

## 1. Capture trigger
CAPTURE := owner ({owner} := manifest.yaml#owner) explicitly signals recognition of {work} as high-level (praise, approval, "save this learning", equivalent in any language).
- MUST run §2 in the same session, before ending the turn.
- NEVER capture without the signal (no self-assessed "great work" entries).
- MAY propose a capture when {work} clearly exceeds baseline; wait for owner confirmation.

## 2. Capture pipeline
1. **Extract** — list [insight] from {work}: decisions that mattered, methods that produced the result, failures diagnosed + root cause, version-pinned facts verified at runtime.
2. **Filter** — keep {insight} only if (transferable ∨ costly_to_rediscover) ∧ verified. Drop narration, project trivia, anything derivable from source code or official docs in < 1 lookup.
3. **Abstract** — replace every concrete domain noun with a typed placeholder (`{agent_class}`, `[zone]`, `<number>`). Keep concrete values ONLY for version pins, numeric tunings with stated scale, and API identifiers.
4. **Classify** — choose `kind` (schema/vocabulary.yaml#kinds) and `domain`; meta-level method → `meta-skills/`.
5. **Dedupe** — search `manifest.yaml` by tags/triggers. Overlap → UPDATE existing unit (§5), never duplicate.
6. **Write** — copy `templates/{kind}.md`, fill every section, satisfy `schema/knowledge-unit.schema.yaml`.
7. **Register** — add/modify entry in `manifest.yaml`; update `domains/{domain}/_domain.md`.
8. **Journal** — append event to `journal/recognitions.yaml`.
9. **Report** — tell owner: units created/updated + paths (≤ 5 lines).

## 3. Retrieval (every task)
1. At task start, match {current_task} against `manifest.yaml` → `triggers`, `tags`, `domain`.
2. Load matched units (highest `confidence` first, max {k}=5 unless task is broad).
3. Apply `Procedure` + respect `Invariants`; check `Pitfalls` before acting.
4. If a unit is wrong/outdated in practice → fix it (§5) and note in journal.

## 4. Quality bar (all MUST hold)
- [ ] Every claim is verified (runtime, test, measurement) or marked `confidence: low`.
- [ ] Zero concrete examples outside allowed exceptions (§2.3).
- [ ] Each section is scannable: bullets, tables, formulas; no prose paragraphs > 3 lines.
- [ ] `triggers` are phrased as task conditions an LLM can match.
- [ ] Version-sensitive facts carry `version_pins` and date.
- [ ] Unit is self-contained; cross-refs via `@{unit_id}`.

## 5. Update / merge / deprecate
- UPDATE := edit in place, bump `updated`, append to `changelog` in frontmatter.
- MERGE := fold smaller unit into larger; move old file to `archive/`; set `superseded_by`.
- DEPRECATE := move to `archive/`, set `status: deprecated`, keep manifest entry with `status`.
- NEVER delete history; archive instead.

## 6. Naming
- id := `{domain_short}.{topic}.{slug}` (lowercase, dot-separated).
- file := `{slug}.md` inside `domains/{domain}/{topic}/` or `meta-skills/`.
- New domain := create `domains/{domain}/_domain.md` from `templates/domain.md` + add to `schema/vocabulary.yaml#domains`.
