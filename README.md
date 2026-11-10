# Left Undone para Herdr

Plugin local e skill para acompanhar tarefas e promessas abertas de **uma
conversa Codex ou Claude** em um painel terminal à direita. Python 3.10+,
Linux, Herdr 0.9.1+; sem dependências Python externas.

## Usar

No Herdr, invoque a ação **Left Undone:
abrir pendências**, ou peça ao Codex/Claude para usar a skill
`left-undone-herdr`. A seleção mostra conversas com identidade verificável.

```sh
left-undone                 # abre pelo repo da pasta atual
left-undone open --repo .   # equivalente, também aceita outra pasta
./left-undone list
./left-undone open          # seletor global, todos os repos
# Para uma conversa identificada na listagem:
./left-undone open --pane PANE --session UUID
```

O comando curto é instalado em `~/.local/bin/left-undone`. Execute dentro do
Herdr, no repo da conversa: uma sessão ativa verificável abre diretamente;
várias mostram um seletor com agente, pane, UUID, conta e número de pendências.
As opções aparecem no próprio terminal onde você executou o comando; Enter ou
Abrir escolhe a conversa, Esc volta ao shell. Não abre popup. Quando invocado
por uma ferramenta do agente sem terminal interativo, o seletor abre em um
split normal dentro do Herdr.
O filtro usa a pasta inicial registrada na conversa e a raiz Git, inclusive
quando executado em subpastas. Symlinks são resolvidos; worktrees permanecem
separados. Em projetos sem Git, a correspondência é pela pasta exata.
Se só houver conversas salvas sem sessão ativa, o comando orienta retomá-las.
Retome a mesma conversa para recuperar sua lista; uma sessão nova tem outra lista.
O filtro não junta tarefas nem altera a validação do destinatário.

O painel aceita mouse: clique em uma tarefa para selecionar e use os botões
Enviar/Concluir. Exportar, Importar, páginas e Fechar também são clicáveis.
A roda do mouse troca páginas. Os textos quebram conforme a largura; tarefas
que excedem a altura continuam na página seguinte. Os atalhos abaixo continuam ativos.

A seleção explícita abre o painel à direita, mantendo o foco anterior.
Aberturas repetidas reencontram o mesmo painel. Para interagir, foque o painel
pelos controles normais do Herdr.

| Tecla | Ação |
|---|---|
| a–z | Selecionar/desselecionar item da página |
| 1 | Enviar selecionados à conversa vinculada; mantém pendências |
| 2 | Marcar selecionados como concluídos |
| 3 | Exportar pendências em Markdown |
| 4 | Importar o último export desta sessão |
| ← / → | Trocar página |
| Esc | Fechar painel e parar coleta |

Os itens indicam origem **TAREFA**, **PROMESSA** ou **IMPORTADO**. A seleção
persiste ao trocar página e fechar o painel. Itens enviados só saem quando
concluídos pelo agente/analisador ou baixados manualmente.

## Instalar / remover

```sh
python3 install.py
# Para remover os links do plugin, preservando o estado:
herdr plugin unlink left-undone
```

O instalador liga este diretório no Herdr e cria links da skill em
`~/.agents/skills/left-undone-herdr` e `~/.claude/skills/left-undone-herdr`,
mais o comando `~/.local/bin/left-undone` (essa pasta deve estar no PATH).
Não sobrescreve comandos/skills diferentes, não reinicia servidor e não instala em
outras máquinas. Para retirar a skill, remova somente esses links simbólicos.
O diretório antigo `things-undone-herdr` é um symlink para este projeto,
preservando referências da sessão que iniciou o trabalho.

## Estado e importação

Estado local em `~/.local/state/left-undone-herdr/` (ou XDG_STATE_HOME).
`LEFT_UNDONE_STATE_DIR` permite outro diretório. SQLite usa WAL; cada sessão
é isolada por agente + diretório da conta + UUID. Arquivos são privados ao
usuário. Fechar o painel preserva pendências, seleção e posição da coleta.

Exportação: `exports/<chave-da-sessão>/latest.md`, com cabeçalho `# Left undone`
e linhas `- [ ] texto`, compatíveis com o plugin original. Importação aceita
`-` ou `*`, ignora `[x]`/`[X]`, elimina duplicados e preserva baixas manuais.

```sh
./left-undone export --binding CAMINHO.binding.json --file pendencias.md
./left-undone import --binding CAMINHO.binding.json --file pendencias.md
./left-undone items --binding CAMINHO.binding.json
```

Confira o UUID dentro do arquivo `.binding.json` para escolher a sessão.

## Coleta e modelos

- Codex: eventos `task_complete` e chamadas bem-sucedidas de `update_plan`.
- Claude: respostas `end_turn`, `TodoWrite`, `TaskCreate` e `TaskUpdate` após
  resultado da ferramenta; ignora sidechains.
- Leitura incremental de JSONL, sem consumir linhas ainda incompletas;
  eventos processados e cursor são gravados na mesma transação.
- O analisador recebe só resposta final (até 12 mil caracteres finais) e
  promessas abertas. JSON validado estritamente; até cinco novas promessas.
- Codex usa **gpt-6-luna / low**. Claude usa **Haiku / low**. Ambos usam os
  CLIs autenticados da conta verificada, sem persistir sessões de análise,
  sem contexto de projeto e sem hooks/MCP herdados.
- Os modelos decidem promessas cumpridas/abandonadas; perguntas, obrigações
  do usuário e descrições de trabalho já feito devem ser excluídas.
- Falha de autenticação, cota, timeout ou JSON mantém a lista e o cursor;
  o painel mostra erro e tenta novamente em 30 segundos. Fechar interrompe.
- Ao abrir pela primeira vez, percorre o histórico existente: conversas
  longas podem exigir várias chamadas de análise. Fechar interrompe o custo.

## Identidade e limites

**Falha reproduzida em 2026-11-10 (Codex 0.167.0 / integração Herdr v8):** após
`/new` ou `/resume`, o Herdr pode continuar anunciando o UUID anterior até a
primeira interação da conversa escolhida. Nesse intervalo, até a verificação
imediata do Left Undone pode aceitar o vínculo antigo e enviar à conversa errada.
Reabrir o painel antes dessa interação não resolve. Até a correção, após trocar
de conversa, envie primeiro uma mensagem diretamente ao Codex, aguarde a resposta
e só então reabra o Left Undone. Evidências em
`docs/evidence/codex-session-lifecycle/`; a validação completa continua reprovada.

O plugin confere sessão anunciada pelo Herdr, terminal, processo foreground,
PID/starttime, conta e histórico estruturado. Não deduz destinatário por foco
visual, cwd ou ambiente herdado. Sessão ausente/ambígua fica indisponível;
uma primeira resposta do agente pode ser necessária para o Herdr identificar
seu UUID. A listagem explica panes indisponíveis.

A conta vem do processo autenticado; instalações que compartilham históricos
por symlink são suportadas. Mudanças de sessão/conta bloqueiam envio e coleta.
Para retomar o mesmo UUID em outro processo, abra novamente: o painel próprio
é substituído com o novo vínculo, mantendo o estado salvo.

**Limite do Herdr 0.9.1:** `agent prompt` não oferece precondição atômica por
UUID. Todas as verificações são feitas imediatamente antes do envio, mas
resta uma pequena janela entre validação e envio se outra ação trocar o
agente nesse instante. Não há repetição automática de envio após erro.

Este adaptador foi conferido contra os formatos locais de novembro/2026.
Claude com `stop_reason=null` em todos os registros finais exige adaptar o
coletor; o formato instalado registra `end_turn`. Processos não Linux/remotos
não são suportados nesta versão.

## Verificação

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q left_undone
```

Veja [evidências de verificação](docs/verification.md). A API de plugins foi
conferida no schema do binário instalado e na
[documentação oficial do Herdr](https://herdr.dev/tui/docs/plugins/).
A referência funcional foi o `left-undone` 0.1.0 original de adam-mods,
inspecionado na etapa anterior com REA e nesta implementação pelo código.

As capturas brutas em `docs/evidence/` ficam somente nas máquinas de validação
e não são versionadas: incluem identificadores de sessões e caminhos locais.
Os relatórios de verificação e os testes acompanham o código no Git.
