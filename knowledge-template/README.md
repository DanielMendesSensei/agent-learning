---
id: root.readme
kind: reference
title: LLM Learning Base — entry point
summary: Persistent, structured, AI-native store of high-level learnings captured from validated LLM work.
updated: 2026-10-04
---

# LLM Learning Base

## Purpose
Store {learning} extracted from {work} that the owner explicitly recognized as high-level, in a form any LLM can retrieve, load and reuse with minimal tokens and zero ambiguity.

## Read order (MUST)
1. `manifest.yaml` → registry of every knowledge unit (id, path, triggers, confidence).
2. `PROTOCOL.md` → capture, retrieval, update and quality rules.
3. `schema/vocabulary.yaml` → placeholder grammar used in every unit.
4. Load only units whose `triggers` match {current_task}. NEVER bulk-load the tree.

## Layout
| Path | Role |
|---|---|
| `manifest.yaml` | Machine-readable index. Single source of truth for discovery. |
| `PROTOCOL.md` | Operating rules for LLMs (capture → refine → register → retrieve). |
| `schema/` | Unit frontmatter schema + controlled vocabulary + placeholder grammar. |
| `templates/` | Skeletons per unit kind. Copy, never edit in place. |
| `domains/{domain}/{topic}/` | Domain knowledge units (patterns, playbooks, pitfalls). |
| `domains/{domain}/_domain.md` | Domain map: scope, units, prerequisites, open gaps. |
| `meta-skills/` | Cross-domain cognitive/operational methods (how to work, not what to build). |
| `journal/recognitions.yaml` | Append-only log of recognition events → units produced. |
| `inbox/` | Raw captures awaiting refinement into units. |
| `archive/` | Superseded/deprecated units (kept for provenance). |

## Format decisions
- Units := Markdown + YAML frontmatter → headings chunk cleanly for retrieval; frontmatter enables filtering without reading bodies.
- Registries/schemas := YAML → lowest token cost for structured data, supports comments.
- Content := abstract placeholders (`{x}`, `[x]`, `(a | b)`) instead of concrete examples → patterns transfer across domains.
- Normative keywords := MUST / SHOULD / MAY / NEVER (RFC 2119 semantics).
- Language := English only.
