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
Uma sessão nova no mesmo projeto reencontra as tarefas compartilhadas. Promessas
continuam na conversa de origem. O projeto não substitui a validação do destinatário.

O painel aceita mouse: clique em uma tarefa para selecionar e use os botões
Enviar/Concluir. Exportar, Importar, páginas e Fechar também são clicáveis.
A roda do mouse troca páginas. Os textos quebram conforme a largura; tarefas
que excedem a altura continuam na página seguinte. Os atalhos abaixo continuam ativos.

Ao enviar para um Codex ocupado, o painel pergunta se deseja **Colocar na fila**
ou **Cancelar**. Na confirmação, `1` enfileira e `2` ou Esc cancela, mantendo a
seleção e a página. O pedido entra na fila nativa da conversa verificada, na
mesma conta, sem interromper o trabalho atual. O recibo confirma o recebimento
pela fila; as tarefas continuam abertas até conclusão. Se a seleção mudar ou
uma tarefa for concluída antes da confirmação, revise e envie novamente.
Durante a confirmação do envio, a gravação dos itens é serializada com o coletor.
Falhas não limpam a seleção nem repetem automaticamente o pedido. Se o resultado
for incerto, confira a fila do Codex antes de tentar outra vez.
A fila requer um CLI Codex que ofereça `codex queue`; no Claude, a fila não está
disponível nesta versão e o painel orienta aguardar o agente terminar.

Concluir pelo botão ou pela tecla `2` pede confirmação com a quantidade de
itens selecionados. Na pergunta, `1` ou **Confirmar** conclui os itens; `2`,
**Cancelar** ou Esc volta à lista preservando seleção e página. Se os itens
mudarem enquanto a pergunta estiver aberta, o pedido é recusado para revisão.
Isso só altera a conclusão manual; a curadoria automática continua funcionando.

A seleção explícita abre o painel à direita, mantendo o foco anterior.
Aberturas repetidas reencontram o mesmo painel. Para interagir, foque o painel
pelos controles normais do Herdr.

| Tecla | Ação |
|---|---|
| a–z | Selecionar/desselecionar item da página |
| 1 | Enviar selecionados à conversa vinculada; mantém pendências |
| 2 | Pedir confirmação para marcar selecionados como concluídos |
| 3 | Exportar pendências em Markdown |
| 4 | Importar o último export desta sessão |
| 5 | Coletar agora: solicitar uma rodada imediata ao coletor ativo |
| ← / → | Trocar página |
| Esc | Fechar painel e parar coleta |

Os itens indicam origem **TAREFA**, **PROMESSA** ou **IMPORTADO**. A seleção
persiste ao trocar página e fechar o painel. Itens enviados só saem quando
concluídos pelo agente/analisador ou baixados manualmente.

## Instalar / remover

```sh
git clone https://github.com/viniabdalla/left-undone-herdr.git
cd left-undone-herdr
python3 install.py
```

Para remover a instalação deste checkout:

```sh
python3 uninstall.py
```

O instalador liga este diretório no Herdr e cria links da skill em
`~/.agents/skills/left-undone-herdr` e `~/.claude/skills/left-undone-herdr`,
mais o comando `~/.local/bin/left-undone` (essa pasta deve estar no PATH).
O instalador verifica se o comando, as skills e o ID do plugin já pertencem a
outra instalação. O desinstalador remove os links deste checkout e preserva
as pendências, o diretório do projeto e as demais instalações.

## Estado e importação

Estado local em `~/.local/state/left-undone-herdr/` (ou XDG_STATE_HOME).
`LEFT_UNDONE_STATE_DIR` permite outro diretório. SQLite usa WAL. As tarefas
nativas e os checklists importados são compartilhados entre sessões do mesmo
projeto, inclusive Codex e Claude. Promessas, seleção para envio e posição da
coleta continuam por agente + conta + UUID. Concluir uma tarefa atualiza todos
os painéis do projeto. Fechar painéis e criar novas sessões preserva as tarefas.
Os dados são locais à máquina; esta versão não sincroniza listas entre PCs.

O projeto padrão vem da raiz Git da pasta inicial da conversa, com worktrees
separados. Sem Git, usa a pasta exata. Para uma conversa iniciada em outra pasta:

```sh
left-undone open --pane PANE --session UUID --project /caminho/do/projeto
```

A associação persiste. O cabeçalho mostra o projeto. Dados anteriores mantêm
IDs, origem e baixas manuais; nenhum histórico é apagado. Snapshots de tarefas
de uma sessão não encerram tarefas de outra. Sem histórico que identifique o
projeto, a lista continua restrita à sessão até associação explícita.

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

- As pendências escritas pelos analisadores usam o termo técnico como rótulo,
  seguido da tarefa em linguagem simples, sem explicação longa. Exemplo:
  “Codex /resume / UUID: reconhecer a conversa certa ao retomar.” Quando não
  houver termo técnico útil, basta a tarefa simples. Isso vale para textos
  novos ou atualizados pelo LLM; tarefas nativas e itens antigos não são
  reescritos apenas para mudar o estilo.
- O botão **Coletar agora** (tecla **5**) solicita uma rodada imediata,
  inclusive durante a espera após erro. O status mostra andamento e resultado.
  Pedidos repetidos são agrupados; durante uma análise, a solicitação aguarda
  a rodada atual. A coleta automática continua ativa e a leitura permanece
  incremental: respostas já processadas não são reanalisadas.
- Codex: eventos `task_complete` e chamadas bem-sucedidas de `update_plan`.
- Claude: respostas `end_turn`, `TodoWrite`, `TaskCreate` e `TaskUpdate` após
  resultado da ferramenta; ignora sidechains.
- Leitura incremental de JSONL, sem consumir linhas ainda incompletas.
  A curadoria grava alterações, histórico e evento processado na mesma transação;
  o cursor avança depois. Repetir um evento não reaplica suas alterações.
- Com projeto associado, o curador recebe resposta final (até 12 mil caracteres),
  pedidos recentes (até 4 mil) e itens compactos do projeto. Ele adiciona tarefas,
  atualiza descrições, conclui com evidência e consolida duplicatas semânticas.
  Conflitos preservam o item e não impedem outras novidades. Itens de outras sessões
  entram como contexto; tarefas nativas e promessas delas não são alteradas.
- Checklists importados também podem ser concluídos automaticamente com evidência.
  Ausência numa resposta ou num snapshot não prova conclusão. Baixas manuais são
  preservadas; respostas antigas não sobrescrevem tarefas criadas/editadas depois.
- Heartbeat de aproximadamente 3 segundos verifica novidades; IA só é chamada
  por resposta final nova ou mudança da lista. Revisões são serializadas por
  projeto e têm cache por sessão, sem chamadas em polling ocioso.
- JSON validado, evidência textual, proteção contra resultado obsoleto e histórico
  de ações. Até 50 ações por categoria e 500 itens de contexto; revisão incompleta
  ou acima do limite aparece como erro e mantém o evento para nova tentativa.
  Sem projeto identificado, permanece a análise antiga de promessas por sessão.
- Codex usa **gpt-6-luna / low**. Claude usa **Haiku / low**. Ambos usam os
  CLIs autenticados da conta verificada, sem persistir sessões de análise,
  sem carregar arquivos do repo e sem hooks/MCP herdados. A lista do projeto é
  enviada explicitamente como dados; o curador não executa tarefas.
- Exemplos de mensagens e roteiros de teste não representam trabalho solicitado.
  Blocos de código/exemplo da resposta do assistente não servem como evidência
  de tarefa; pedidos reais do usuário continuam disponíveis para a curadoria.
- Falha de autenticação, cota, timeout ou JSON mantém a lista e o cursor;
  o painel mostra erro e tenta novamente em 30 segundos. Fechar interrompe.
- Ao abrir pela primeira vez, percorre o histórico existente: conversas
  longas podem exigir várias chamadas de análise. Fechar interrompe o custo.

Para consultar a lista ou as últimas mudanças sem abrir outro painel:

```sh
left-undone items --binding CAMINHO.binding.json
left-undone changes --binding CAMINHO.binding.json
```

O status do painel informa quantas mudanças foram aplicadas e quantos itens foram
preservados. O histórico detalha sessão, evento, antes/depois e destino de duplicatas.

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

Para ferramentas Codex sem contexto Herdr ou conversas sem registro nativo,
a skill agora usa `left-undone recover --marker LU-<32 dígitos hexadecimais>`.
O agente publica uma marca nova em commentary; o comando cruza essa marca
recente com histórico, painel visível, conta e processo, registra pelo hook
nativo e verifica o resultado. Não envia mensagens nem reinicia processos.
Essa recuperação pontual não detecta automaticamente trocas futuras de conversa.
A recuperação aguarda brevemente a publicação da marca no histórico/terminal e
aceita a marca quebrada entre linhas pelo terminal. Ambiguidade continua sendo
recusada imediatamente. A espera ocorre somente antes de qualquer registro;
falhas do hook ou da confirmação não são repetidas automaticamente. Se falhar,
a mensagem identifica a etapa ausente (processo, histórico ou marca visível).

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
