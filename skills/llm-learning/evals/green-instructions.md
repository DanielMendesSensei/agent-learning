# Agent Learning: Task Observer e llm-learning

Carregar uma skill nesta simulação: ler o arquivo SKILL.md dela. A skill `llm-learning` está em {SANDBOX}/skills/llm-learning/SKILL.md. A base de conhecimento fica em {SANDBOX}/kb: passe `--root {SANDBOX}/kb` em toda chamada do `kb`.

## Para onde vai cada coisa

| O que aconteceu | Destino | Ferramenta |
|---|---|---|
| Ana reconheceu um trabalho técnico ("excelente", "mandou muito bem", "guarda isso", "vale guardar") | llm-learning | skill `llm-learning` (usa o comando `kb`) |
| Ana corrigiu você, você quebrou uma regra escrita, ou uma skill mostrou lacuna | Task Observer | `bash {SANDBOX}/obs/new-observation.sh <slug>`, que imprime o caminho de um arquivo novo; escreva nele a observação (frontmatter YAML: title, status: open, skill ou target_file, type; corpo: o que aconteceu, correção proposta) |
| Fato de negócio: cliente, acordo, valor, data, pessoa | notas pessoais | a nota certa em {SANDBOX}/sb, com data |
| Preferência de trabalho da Ana | memória do próprio agente | |

Uma mensagem pode alimentar vários destinos. "Era para abrir PR, não commitar na main; mas o retry com backoff ficou excelente, guarda isso. Ah, e a Beta renovou até março" gera uma observação (a correção), uma unidade (o retry) e uma nota (a renovação). "boa", "valeu", "ok" ou "funcionou" sozinhos não são reconhecimento: nada vai para o llm-learning.

## llm-learning

- No começo de toda tarefa técnica, carregue a skill `llm-learning` e faça a recuperação que ela descreve (no máximo 5 unidades).
- Quando aparecer o sinal da Ana, carregue a skill e grave na mesma resposta. Ids e caminhos saem do comando `kb`, e o `kb validate` precisa passar antes do relatório.

# Containers
Serviço local que a Ana vai usar roda em Docker Compose. Podman é só para banco de teste descartável.

# Idioma
Responda à Ana em português.
