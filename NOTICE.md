# Origins and licences

Português: [NOTICE.pt-BR.md](NOTICE.pt-BR.md)

This repository combines two third-party projects with original code. Each
part keeps its own licence.

## Task Observer

- **Origin:** the `task-observer` skill v3.8.1, by Eoghan Henn and
  contributors, from
  [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all)
  (commit `ba696b2`).
- **Licence:** Creative Commons Attribution 4.0 (CC BY 4.0). The text is in
  `skills/task-observer/LICENSE`.
- **Where it is:** `skills/task-observer/`, identical to the upstream skill at
  that commit. The only added file is `INSTALL-SOURCE.txt`, which records
  where the copy came from. The upstream repository's own top-level files
  (its README, contributing guide and so on) are not included.
- **What changed:** only the activation block, copied into
  `adapters/instructions-block.md`. Its paths became placeholders that the
  installer fills in, and its dashes became commas, colons or parentheses to
  match this repository's house style (no em or en dashes). The rest is the
  template's text, word for word.

CC BY 4.0 allows copying, adapting and redistributing, commercial use
included, as long as you give credit and say what changed. This section does
both.

## llm-learning

- **Origin:** [Jonhvmp/llm-learning](https://github.com/Jonhvmp/llm-learning),
  by Jonh (commit `a2337b2`).
- **Permission:** the upstream repository has no licence file. Its author
  allowed forking it and publishing this repository on 2026-10-27. Until a
  licence file exists upstream, ask the author before reusing
  `knowledge-template/` outside this project.
- **Where it is:** `knowledge-template/` is the skeleton of the llm-learning
  base (README, PROTOCOL, schema and templates), copied unchanged.
  `skills/llm-learning/` is original code that follows that format and
  protocol.

## Original code

`install.py`, `adapters/`, `scheduler/`, `prompts/` and `skills/llm-learning/`
(SKILL.md, `scripts/kb.py` and `evals/`) are by Daniel Mendes, under the MIT
licence in [LICENSE](LICENSE).

## Punctuation in third-party text

The Task Observer files and the llm-learning skeleton keep their original
punctuation, dashes included. They are someone else's text, and editing them
would break the byte-for-byte comparison on an update. The house style
applies to what was written here.
