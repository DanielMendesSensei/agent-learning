# Origem e licenças

English: [NOTICE.md](NOTICE.md)

Este repositório junta dois projetos de terceiros com código próprio. Cada
parte mantém a sua licença.

## Task Observer

- **Origem:** skill `task-observer` v3.8.1, de Eoghan Henn e colaboradores,
  repositório
  [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all)
  (commit `ba696b2`).
- **Licença:** Creative Commons Attribution 4.0 (CC BY 4.0). O texto está em
  `skills/task-observer/LICENSE`.
- **Onde está:** `skills/task-observer/`, idêntico à skill original nesse
  commit. O único arquivo acrescentado é o `INSTALL-SOURCE.txt`, que registra
  de onde veio a cópia. Os arquivos da raiz do repositório original (README,
  guia de contribuição e afins) não vieram junto.
- **O que mudou:** só o bloco de ativação, copiado em
  `adapters/instructions-block.md`. Os caminhos viraram marcadores que o
  instalador preenche, e os travessões viraram vírgula, dois-pontos ou
  parênteses para seguir o estilo deste repositório (sem travessão nem
  meia-risca). O resto do texto é o do template, palavra por palavra.

A CC BY 4.0 permite copiar, adaptar e redistribuir, inclusive para uso
comercial, desde que se dê o crédito e se diga o que mudou. Esta seção cumpre
as duas coisas.

## llm-learning

- **Origem:** [Jonhvmp/llm-learning](https://github.com/Jonhvmp/llm-learning),
  de Jonh (commit `a2337b2`).
- **Permissão:** o repositório original não tem arquivo de licença. O autor
  autorizou o fork e a publicação deste repositório em 27/10/2026. Enquanto
  não houver licença lá, peça autorização ao autor antes de reaproveitar
  `knowledge-template/` fora deste projeto.
- **Onde está:** `knowledge-template/` é o esqueleto da base do llm-learning
  (README, PROTOCOL, schema e templates), copiado sem mudanças.
  `skills/llm-learning/` é código próprio que segue esse formato e esse
  protocolo.

## Código próprio

`install.py`, `adapters/`, `scheduler/`, `prompts/` e `skills/llm-learning/`
(SKILL.md, `scripts/kb.py` e `evals/`) são de Daniel Mendes, sob a licença MIT
do arquivo [LICENSE](LICENSE).

## Pontuação dos textos de terceiros

Os arquivos do Task Observer e do esqueleto do llm-learning mantêm a
pontuação original, travessões incluídos. Eles são texto de terceiros, e
mexer neles quebraria a comparação byte a byte numa atualização. O estilo da
casa vale para o que foi escrito aqui.
