# agent-learning

English: [README.md](README.md)

Junta duas ferramentas de aprendizado contínuo para agentes de código e as
liga em qualquer IA da sua máquina: Claude Code, Codex (GPT), Gemini CLI e,
por texto, qualquer outra.

- **Task Observer** aprende com o que deu errado. Cada correção sua, regra
  quebrada ou lacuna de skill vira uma observação, e uma revisão semanal
  transforma as observações em skills melhores.
- **llm-learning** guarda o que deu certo. Quando você reconhece um trabalho
  técnico ("mandou muito bem, guarda isso"), o agente grava uma unidade de
  conhecimento e a recupera na próxima tarefa parecida.

As duas leem e escrevem no mesmo lugar, `~/.agent-learning`, fora da pasta
de qualquer agente. Por isso o que o Claude aprende numa sessão o Codex usa
na seguinte, e o contrário também.

Ele junta dois projetos que já existiam:
[Task Observer](https://github.com/rebelytics/one-skill-to-rule-them-all), de
Eoghan Henn, e [llm-learning](https://github.com/Jonhvmp/llm-learning), de
Jonh. Este repositório acrescenta o instalador, os adaptadores de cada agente,
o agendador da revisão semanal e o comando `kb`.

O guia de uso está em [PLAYBOOK.pt-BR.md](PLAYBOOK.pt-BR.md). Origem e licenças dos
componentes, em [NOTICE.pt-BR.md](NOTICE.pt-BR.md).

## Requisitos

- Linux com units de usuário do systemd, para a revisão agendada. Fora dele,
  a revisão roda por qualquer agendador (veja o playbook).
- Python 3, só a biblioteca padrão.
- git e `flock`.
- Pelo menos um entre Claude Code, Codex e Gemini CLI.

## Instalar

```bash
python3 install.py --dry-run
```

```bash
python3 install.py
```

O primeiro mostra o que vai mudar sem gravar nada. O segundo aplica. Rodar
de novo é seguro: o que já está certo aparece como "em dia". Antes de mexer
num arquivo, o instalador guarda uma cópia em
`~/.local/state/agent-learning/backups/<data-hora>/`.

Depois da instalação, faltam dois passos que só você pode dar:

1. **Codex:** abra o Codex, rode `/hooks` e aprove o hook `SessionStart` do
   agent-learning. Sem isso ele não lembra o protocolo no começo da sessão.
2. **Gemini CLI:** o Gemini só roda hooks em pasta confiável. Confie, pelo
   próprio Gemini, nas pastas onde quer o lembrete.

Opções úteis: `--no-schedule` (sem revisão agendada), `--review-engine codex`
(a revisão agendada roda no Codex), `--review-calendar 'Fri *-*-* 17:00:00'`,
`--uninstall` e `--selftest`.

## Configuração pessoal

O bloco de instruções cita duas coisas que são suas: o dono, cujo elogio
conta como reconhecimento, e o destino dos fatos de negócio. As duas vêm de
`~/.config/agent-learning/install.json` (ou
`$XDG_CONFIG_HOME/agent-learning/install.json`), que fica fora do
repositório:

```json
{
  "owner": "Ana",
  "notes": "Notion | o servidor MCP do Notion"
}
```

`notes` segue o formato `destino | ferramenta`. Sem o arquivo, o dono é o seu
`git config user.name` e os fatos de negócio vão para as suas notas pessoais,
pela ferramenta que as suas outras instruções indicarem. `--owner` e
`--notes` passam por cima do arquivo numa execução.

## O que tem aqui

| Pasta | Conteúdo |
|---|---|
| `skills/task-observer/` | Task Observer v3.8.1, sem alterações |
| `skills/llm-learning/` | A skill que embrulha a base do llm-learning, o comando `kb` e os evals |
| `knowledge-template/` | O esqueleto da base do llm-learning (README, PROTOCOL, schema, templates) |
| `adapters/` | O bloco de instruções que vai para CLAUDE.md, AGENTS.md e GEMINI.md, e o hook de início de sessão |
| `scheduler/` | A revisão semanal: script, prompts, units do systemd e o plugin que expõe a skill ao Claude agendado |
| `prompts/` | Textos para colar, como o repasse de um chat sem shell |
| `install.py` | Instala, atualiza, desinstala e se testa |

## Onde ficam os dados

| Caminho | O quê |
|---|---|
| `~/.agent-learning/skill-observations/` | Log de observações, princípios transversais, marcadores da revisão |
| `~/.agent-learning/skill-updates/` | Skills revisadas esperando você instalar |
| `~/.agent-learning/knowledge/` | A base do llm-learning |
| `~/.local/state/agent-learning/review-logs/` | Um log por execução da revisão agendada |

`~/.agent-learning` é um repositório git. Quem faz os commits é o script da
revisão, com caminhos explícitos, sem assinatura de agente.

## Licença

O código próprio está sob a licença MIT ([LICENSE](LICENSE)). O Task
Observer, em `skills/task-observer/`, mantém a licença CC BY 4.0, e o
esqueleto do llm-learning em `knowledge-template/` entra com a permissão do
autor. Detalhes em [NOTICE.pt-BR.md](NOTICE.pt-BR.md).
