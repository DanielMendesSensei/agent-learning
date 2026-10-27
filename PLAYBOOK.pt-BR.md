# Playbook: Task Observer e llm-learning no dia a dia

English: [PLAYBOOK.md](PLAYBOOK.md)

## A ideia em um minuto

Toda sessão com um agente produz dois tipos de aprendizado, e cada um tem
seu dono.

- **O que deu errado vai para o Task Observer.** Você corrigiu o agente, ele
  quebrou uma regra escrita, uma skill não cobriu um caso. Isso vira uma
  observação no log. Uma vez por semana, a revisão lê as observações e
  prepara versões melhores das skills e das instruções.
- **O que deu certo vai para o llm-learning.** Você elogiou um trabalho
  técnico e pediu para guardar. Isso vira uma unidade de conhecimento, curta
  e sem nomes de projeto, que volta sozinha na próxima tarefa parecida.

Os dois moram em `~/.agent-learning`, que qualquer agente lê. Não importa se
o erro aconteceu no Claude e o acerto no Codex: tudo cai no mesmo lugar.

## Para onde vai cada coisa

| Aconteceu | Vai para | Quem grava |
|---|---|---|
| Você reconheceu um trabalho técnico ("excelente", "mandou muito bem", "guarda isso", "vale guardar") | llm-learning | skill `llm-learning`, pelo comando `kb` |
| Você corrigiu o agente, ele quebrou uma regra, uma skill mostrou lacuna | Task Observer | `new-observation.sh` |
| Fato de negócio: cliente, acordo, valor, data, pessoa | suas notas | o que a opção `notes` indicar (veja o README) |
| Preferência sua de trabalho | memória do próprio agente | o agente |

Uma mensagem pode ir para vários lugares. Por exemplo:

> Era para abrir PR, não commitar na main. Mas o retry com backoff ficou
> excelente, guarda isso. Ah, e a Beta renovou até março.

Isso gera uma observação (a correção), uma unidade (o retry) e uma nota de
negócio (a renovação).

## O que dizer ao agente

| Você quer | Diga | O que acontece |
|---|---|---|
| Guardar um acerto | "guarda isso", "vale guardar", "mandou muito bem" | O agente grava a unidade na mesma resposta e mostra id, caminho e gatilho |
| Só agradecer | "boa", "valeu", "ok", "funcionou", "perfeito" | Nada é gravado. No máximo ele oferece guardar, em uma linha |
| Guardar só uma parte | "a parte do healthcheck ficou excelente, guarda isso" | Só aquela parte vira unidade |
| Corrigir | Diga o que estava errado, do seu jeito | Vira observação. Não precisa pedir |
| Rodar a revisão agora | "roda a revisão semanal" | O agente carrega o Task Observer e segue o procedimento da revisão |

O elogio é o gatilho. O agente não grava porque achou que foi bom: isso é
justamente o erro que os evals pegaram (veja
`skills/llm-learning/evals/results.md`).

## Uma sessão típica

1. **Começo.** O hook de início de sessão lembra o agente do protocolo do
   Task Observer e diz quantas observações estão abertas. Se a revisão
   estiver atrasada, ele oferece rodar, uma vez. Você pode ignorar.
2. **Tarefa técnica.** O agente roda `kb index`, carrega até 5 unidades que
   batem com a tarefa e cita os ids que usou.
3. **Você corrige algo.** O agente cria a observação no mesmo turno, sem
   parar o trabalho.
4. **Você elogia.** O agente grava a unidade e roda `kb validate` antes de
   te responder.
5. **Fim da tarefa.** O agente lista as observações gravadas na sessão, lidas
   do log, não de memória.

## A revisão semanal

Roda sozinha toda segunda às 10:00 (com até 15 minutos de atraso aleatório).
Se o computador estiver desligado ou suspenso nessa hora, ela roda assim que
ele voltar.

O que ela faz:

- lê as observações abertas e agrupa as que falam da mesma coisa;
- aplica as mudanças simples em cópias das skills, em
  `~/.agent-learning/skill-updates/`. Nada fica valendo até você instalar;
- deixa para você o que é decisão sua: skill nova, remoção ou reestruturação
  grande, item incerto e observações em conflito;
- grava o relatório em
  `~/.agent-learning/skill-observations/reviews/<data>/REVIEW.md`;
- faz commit no repositório do workspace e manda uma notificação na área de
  trabalho.

Depois, leia o `REVIEW.md` e o `skill-updates/PENDING.md`. Na próxima sessão
interativa o agente avisa quantas atualizações esperam revisão. Peça para
revisar e instalar as que você aprovar.

### Rodar na mão

Testar o acesso sem fazer a revisão:

```bash
systemctl --user start weekly-skill-review@probe.service
```

Rodar a revisão completa agora:

```bash
systemctl --user start weekly-skill-review@full.service
```

Ver quando é a próxima:

```bash
systemctl --user list-timers weekly-skill-review.timer
```

Ler o log mais recente:

```bash
ls -t ~/.local/state/agent-learning/review-logs/ | head -n 3
```

### Mensagens da notificação

| Mensagem | Quer dizer |
|---|---|
| `revisão <data> concluída` | Deu certo. O caminho do relatório vem junto |
| `sonda ok` | O agente conseguiu gravar no workspace de dentro da unit |
| `revisão pulada: workspace ... fora do ar` | `~/.agent-learning` não existe ou não abriu |
| `disparou em ... e não registrou revisão` | O agente rodou e não terminou. Veja o log |
| `ATENÇÃO: travessões em ...` | A revisão escreveu travessão em algum texto. Corrija antes de instalar |
| `outra revisão já está rodando` | Duas execuções ao mesmo tempo. A segunda saiu sem fazer nada |

### Como ela fica isolada

A revisão agendada roda o agente sem as suas configurações, hooks, MCPs e
plugins. No Claude, comandos só gravam dentro de `~/.agent-learning`, a rede
fica fechada e a skill chega por um plugin do próprio repositório. No Codex,
`--ignore-user-config` deixa de fora os plugins, MCPs e hooks, e o sandbox
`workspace-write` prende a escrita no workspace. Quem faz o commit é o
script, não o agente, então nenhum commit sai com assinatura de IA.

## Por agente

### Claude Code

Funciona sem passo extra. O bloco de instruções está no `~/.claude/CLAUDE.md`,
o hook no `~/.claude/settings.json` e as skills em `~/.claude/skills/`.

### Codex (GPT)

O bloco vai para o `~/.codex/AGENTS.md` e as skills ficam em
`~/.agents/skills/`, que o Codex lê. O hook de início de sessão precisa da
sua aprovação: abra o Codex e rode `/hooks`. O instalador nunca aprova por
você.

Para a revisão agendada rodar no Codex em vez do Claude:

```bash
python3 install.py --review-engine codex
```

Depois rode a sonda para provar que funciona. O motor padrão é o Claude.

### Gemini CLI

O bloco vai para o `~/.gemini/GEMINI.md` e as skills para `~/.agents/skills/`.
O Gemini só roda hooks em pastas que você marcou como confiáveis, e o
instalador não mexe nisso. Sem a pasta confiável, o bloco de instruções
continua valendo, só o lembrete do início de sessão não aparece.

O Gemini não roda a revisão agendada. No modo headless ele não tem sandbox
de escrita, e liberar tudo sem supervisão seria pior do que não rodar. Nele,
peça a revisão numa sessão interativa.

### Escolher o modelo

O script da revisão aceita `AGENT_LEARNING_MODEL`. Para fixar um modelo sem
que a próxima instalação apague a escolha, use um drop-in do systemd:

```bash
systemctl --user edit weekly-skill-review@.service
```

E escreva:

```ini
[Service]
Environment=AGENT_LEARNING_MODEL=<nome do modelo>
```

### Qualquer outra IA

- **Com shell e arquivo de instruções:** copie o bloco de
  `adapters/instructions-block.md` para o arquivo de instruções dela,
  trocando `{{REPO}}`, `{{ROOT}}` e `{{PROJECTS}}` pelos caminhos reais,
  `{{OWNER}}` pelo seu nome e `{{NOTES}}` pelo destino dos fatos de negócio. As
  skills são Markdown puro: basta ela ler `skills/<nome>/SKILL.md`.
- **Só chat, sem shell** (ChatGPT na web, Claude.ai, Gemini no navegador):
  use `prompts/chat-handoff.pt-BR.md`. A IA do chat prepara a unidade como texto e
  uma sessão com shell registra.

## O comando kb

| Comando | Para quê |
|---|---|
| `kb index` | Lista as unidades com gatilhos e confiança |
| `kb new --kind ... --domain ... --topic ... --title ... --summary ... --trigger ... --confidence ... --evidence ...` | Cria a unidade e imprime o caminho |
| `kb register <caminho>` | Atualiza o manifest a partir da unidade |
| `kb journal --signal "<suas palavras>" --summary ... --created <id>` | Registra o reconhecimento no diário |
| `kb validate` | Confere a base inteira. Precisa dar OK |

Cada comando aceita `--help`. Os tipos de unidade são `playbook`, `pattern`,
`pitfall-set`, `reference` e `meta-skill`.

## Manutenção

Ver o que uma instalação mudaria:

```bash
python3 install.py --dry-run
```

Atualizar depois de mexer no repositório (os links já apontam para cá, então
só o bloco de instruções e as units precisam de nova cópia):

```bash
python3 install.py
```

Rodar os testes do instalador num HOME falso:

```bash
python3 install.py --selftest
```

Desinstalar (tira links, blocos, hooks e o timer; mantém o workspace e a
base):

```bash
python3 install.py --uninstall
```

Os backups de cada arquivo alterado ficam em
`~/.local/state/agent-learning/backups/<data-hora>/`.

## Outros agendadores

O systemd é o caminho padrão no Linux porque recupera a execução perdida
com a máquina desligada. Fora dele, agende o mesmo script:

```text
scheduler/weekly-review.sh full
```

Com `AGENT_LEARNING_ENGINE` (claude ou codex) e, se quiser,
`AGENT_LEARNING_HOME` no ambiente.

- **cron:** não recupera execução perdida, e o PATH do cron é curto.
  Confira que `command -v claude` acha o binário no PATH que você passar.
- **launchd (macOS):** o script foi escrito e testado no Linux. No macOS ele
  precisa do `flock` e do `stat` e `timeout` do GNU coreutils.
- **Agendador de Tarefas (Windows):** rode pelo WSL, com
  `wsl.exe -e bash -lc "<caminho>/scheduler/weekly-review.sh full"`.

## Quando algo não funciona

| Sintoma | Onde olhar |
|---|---|
| O agente não carrega o Task Observer no começo | O bloco está no arquivo de instruções dele? `python3 install.py --dry-run` mostra |
| O Codex não mostra o lembrete | Aprovação pendente em `/hooks` |
| O Gemini não mostra o lembrete | A pasta não é confiável |
| `kb: command not found` | `~/.local/bin` fora do PATH. Use `python3 skills/llm-learning/scripts/kb.py` |
| `kb validate` falha | A mensagem diz o arquivo e o comando que conserta |
| A revisão não rodou | `systemctl --user list-timers` e o log mais recente |
