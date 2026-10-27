# Repasse de um chat sem shell

English: [chat-handoff.md](chat-handoff.md)

Serve para quando o trabalho reconhecido aconteceu numa IA que não roda
comandos: ChatGPT na web, Claude.ai, Gemini no navegador, um chat da
empresa. Ela não tem como gravar na base. Então o trabalho vira texto ali e
outra sessão, com shell, registra.

São duas etapas, cada uma com um texto para colar.

## Etapa 1: no chat sem shell

Cole isto logo depois do elogio ("mandou muito bem, guarda isso"):

```text
Não temos shell aqui, então prepare o aprendizado para eu registrar em outra
sessão. Responda com um único bloco de código, sem nada fora dele, neste
formato:

KIND: playbook | pattern | pitfall-set | reference | meta-skill
DOMAIN: <domínio curto em inglês, minúsculo, ex. linux-ops>
TOPIC: <tópico curto em inglês, minúsculo, ex. systemd-timers>
TITLE: <título em inglês>
SUMMARY: <uma frase em inglês: o que é e quando usar>
TRIGGER: <condição de tarefa em inglês, com {placeholders}>
TRIGGER: <repita a linha para cada gatilho>
TAG: <uma palavra; repita a linha para cada tag>
PIN: <pacote=versão; uma por linha; omita se não houver>
CONFIDENCE: high | medium | low
EVIDENCE: owner-recognized
EVIDENCE: runtime-verified   (só se rodou e foi conferido nesta conversa)
OWNER SAID: <minhas palavras de reconhecimento, literais>
BODY:
<o corpo da unidade em inglês, em seções curtas: Context, Procedure ou
Pitfalls, Invariants, Verification>

Regras:
- Só entra o que foi verificado nesta conversa. Palpite de conhecimento
  geral fica fora do bloco, ou entra com CONFIDENCE: low.
- Troque nomes de projeto, cliente e produto por {placeholders}. Mantenha
  versões e números ajustados.
- Se a mesma mensagem minha trouxe uma correção ou um fato de negócio, não
  misture: liste isso depois do bloco, em uma linha cada, marcado
  CORREÇÃO ou NEGÓCIO.
```

Copie o bloco que ela devolver.

## Etapa 2: numa sessão com shell

Abra uma sessão de qualquer agente que rode comandos nesta máquina (Claude
Code, Codex, Gemini CLI) e cole:

```text
Registre na base llm-learning o aprendizado abaixo, que veio de um chat sem
shell. Carregue a skill llm-learning e siga o pipeline de captura dela, com
estas regras:

1. Rode `kb index` e veja se alguma unidade já cobre o assunto. Se cobrir,
   atualize aquele arquivo em vez de criar outro.
2. Senão, crie com `kb new`, levando cada campo do bloco para a opção de mesmo
   nome (--kind, --domain, --topic, --title, --summary, --trigger, --tag,
   --pin, --confidence, --evidence). Se o domínio for novo, acrescente
   --scope com uma frase sobre ele. Use o caminho que o comando imprimir.
3. Escreva o BODY no arquivo com a ferramenta de edição, nunca com heredoc
   sem aspas.
4. `kb register <caminho>`, depois `kb journal --signal "<OWNER SAID>"
   --summary "<SUMMARY>" --created <id>` (ou --updated, se atualizou).
5. `kb validate` precisa imprimir OK. Se der erro, corrija e rode de novo.
6. Responda em até 5 linhas: id, caminho e o gatilho que vai trazer a
   unidade de volta.

Linhas marcadas CORREÇÃO vão para o Task Observer, criadas pelo
new-observation.sh. Linhas marcadas NEGÓCIO vão para as minhas notas. Nenhuma
das duas entra na base.

<cole aqui o bloco da etapa 1>
```

## Por que não colar o corpo direto num arquivo

O `kb new` é quem decide o id e o caminho, e o `kb register` é quem mantém o
manifest em dia. Nos evals, as unidades escritas à mão quebraram essas duas
regras (`skills/llm-learning/evals/results.md`). Por isso o repasse sempre
passa por uma sessão que rode o `kb`.

## Observações do Task Observer sem shell

Uma correção num chat sem shell segue o modo de documento de repasse do
próprio Task Observer (`skills/task-observer/references/environments.md`,
seção "Handoff-doc mode"). Ele já define o formato e como a sessão seguinte
analisa o que chegou.
