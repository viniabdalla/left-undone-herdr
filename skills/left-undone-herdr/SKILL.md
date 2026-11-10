---
name: left-undone-herdr
description: Abrir ou reencontrar o painel Left Undone no Herdr para acompanhar tarefas e promessas de uma conversa Codex ou Claude, importar ou exportar pendências.
---

# Left Undone no Herdr

Use quando a pessoa pedir o painel de pendências no Herdr. Requer Linux,
Python 3.10+, Herdr 0.9.1+ e o plugin local `left-undone` vinculado.

O executável desta skill é `scripts/left-undone` (resolva relativo a este
SKILL.md). Ele usa a mesma implementação do plugin, sem criar outro coletor.

## Atalho pelo repo

O instalador também disponibiliza `left-undone` em `~/.local/bin`.
Sem argumentos, filtra pelo repo da pasta atual: uma sessão ativa verificável
abre diretamente, várias abrem o seletor do repo com contagens de pendências.
No terminal, o seletor ocupa o próprio terminal até escolher ou sair com Esc.
Invocado sem TTY pelas ferramentas do agente, abre em split no Herdr; nunca popup.
`left-undone open --repo <pasta>` permite indicar a pasta; `left-undone open`
continua abrindo o seletor global. Em subpastas usa raiz Git; sem Git usa pasta
exata; cada worktree é separado. A pasta inicial vem do histórico da sessão.
Conversas salvas sem sessão ativa precisam ser retomadas no agente.
A pasta define a lista compartilhada e filtra candidatos; identidade para abrir/enviar continua por UUID,
conta e processo. Se o usuário pedir esta conversa, use o vínculo exato abaixo,
mesmo que o diretório de trabalho da ferramenta esteja em outro projeto.

## Listas por projeto

Tarefas nativas e itens importados aparecem nas sessões do mesmo projeto;
promessas continuam privadas à conversa de origem. Concluir uma tarefa afeta
todos os painéis do projeto. Selecionar para enviar é privado à conversa.
O estado continua local à máquina e sobrevive a novas sessões.
Por padrão, o projeto é a raiz Git do cwd inicial verificado (ou pasta exata).
Se a conversa começou em outra pasta mas trata de um projeto identificado pelo
usuário, associe explicitamente com `python3 scripts/left-undone open --pane PANE
--session UUID --project /caminho/do/projeto`. Essa associação persiste. Nunca
use `--project` para adivinhar qual é o destinatário. Não altere a associação de
outras conversas sem evidência de que pertencem ao projeto.
Após trocar /new ou /resume, a atualização automática do destinatário ainda
está pendente: compartilhar a lista não corrige o UUID nativo obsoleto.

## Abrir uma conversa identificada

1. Rode `python3 scripts/left-undone list`. A saída identifica panes, UUIDs, conta e
   histórico verificáveis; também explica sessões indisponíveis.
2. Se a pessoa identificou a conversa e os dados permitem confirmar o destino,
   rode `scripts/left-undone open --pane <pane> --session <UUID>`.
   Sem correspondência inequívoca, rode `scripts/left-undone open`: abre uma
   seleção no Herdr. Não use foco visual, cwd ou HERDR_PANE_ID herdado como
   prova da identidade. Não escolha outra conversa silenciosamente.
3. A abertura cria um split à direita sem roubar foco, ou reencontra o painel
   existente. O painel lê apenas o histórico da conversa vinculada.

Clique na tarefa (qualquer linha) ou use a letra para selecionar. Botões
Enviar e Concluir aparecem com a contagem dos selecionados. A roda do mouse
e os botões < / > trocam páginas; Exportar, Importar e Fechar são clicáveis.
Textos quebram na largura do painel; tarefas muito altas continuam em outra página.
No seletor de conversas, clique na linha e depois em Abrir.

Letras selecionam itens. `1` envia os selecionados à conversa vinculada,
sem retirá-los da lista. `2` conclui. `3` exporta. `4` importa o último arquivo
exportado. Setas trocam páginas. Esc fecha; estado e seleção ficam salvos.

O botão **Coletar agora** e a tecla `5` solicitam uma rodada imediata ao
coletor existente, sem interromper a coleta automática. Pedidos repetidos são
agrupados; se houver análise em andamento, aguardam essa rodada terminar.
O pedido também interrompe a espera após erro, mantendo a validação da sessão.
A leitura permanece incremental: eventos já processados não são reanalisados.

Para arquivo escolhido: use `export` ou `import --file <arquivo>` junto com
`--binding <arquivo .binding.json>`. O arquivo de vínculo é criado em
`~/.local/state/left-undone-herdr/`; derive o correto pela sessão no JSON,
não pelo arquivo mais recente. `items --binding ...` mostra o estado.
Importação é aditiva, ignora `[x]` e não reabre baixas manuais.

Os analisadores usam o CLI autenticado da conta verificada: Claude Haiku,
Codex gpt-6-luna com esforço low. No projeto, recebem resposta final, pedidos
recentes e itens compactos do projeto, incluindo outras sessões como contexto.
Não substitua por modelo maior nem reenvie a conversa inteira.
Falhas de login/limite/JSON aparecem no painel; não apagam a lista.

A curadoria aplica automaticamente adições, atualizações, conclusões com
evidência e consolidação de duplicatas. Conflitos preservam o item sem perguntar;
novidades diferentes continuam entrando. Tarefas nativas/promessas de outras
sessões não são alteradas. Não trate promessa privada alheia como substituta de
uma tarefa compartilhada. Nenhuma tarefa é concluída por simples omissão.
O heartbeat apenas verifica mudanças; não há chamada ao LLM em polling ocioso.
Use `python3 scripts/left-undone changes --binding ARQUIVO` para conferir o
histórico de alterações, e `items --binding` para listar sem abrir outro painel.
A curadoria não corrige o destinatário obsoleto após /new ou /resume.

Se a sessão não foi identificada pelo Herdr, explique a indisponibilidade.
Não invente UUID, não use report-agent-session com ID deduzido do cwd e
não reinicie o servidor. Se necessário, verifique as integrações nativas
com `herdr integration` e peça que o usuário identifique a conversa.

Limite do Herdr 0.9.1: o envio valida identidade imediatamente antes de
`agent prompt`, mas a API não oferece envio atômico condicionado ao UUID.
Não repita automaticamente um envio após timeout/erro ambíguo.

Falha ao vivo confirmada em 2026-11-10 com Codex 0.167.0/integração v8:
após /new ou /resume, o Herdr pode anunciar o UUID antigo até a primeira
interação da conversa escolhida. Reabrir o painel nesse intervalo não basta.
Quando houver troca de conversa, aguarde uma resposta a uma mensagem enviada
diretamente ao Codex antes de abrir/enviar pelo Left Undone. Não anuncie a
validação completa de troca/retomada como aprovada enquanto essa falha existir.


## Codex com app-server e contexto ausente

`HERDR_ENV` ausente no comando não prova que a interface está fora do Herdr:
o app-server pode executar ferramentas sem herdar o ambiente do terminal.
O wrapper recupera o contexto quando `CODEX_THREAD_ID` corresponde a exatamente
uma sessão nativa do Herdr e a um processo Codex interativo verificável.
Execute `list` antes de mandar a pessoa reabrir a conversa.

Se a sessão não estiver registrada, confira `herdr integration status`.
Instalar a integração Codex (`herdr integration install codex`) faz parte da
instalação autorizada do plugin; não reinicie o Herdr nem o Codex.
Uma conversa já aberta pode precisar de registro inicial. Gere uma marca nova
com `python3 -c 'import uuid; print("LU-"+uuid.uuid4().hex)'`, publique-a em uma
mensagem de commentary e execute logo em seguida
`python3 scripts/left-undone recover --marker LU-<32 dígitos hexadecimais>`.
Não reutilize uma marca de exemplo. O comando exige `CODEX_THREAD_ID` real,
marca de commentary no histórico da conta com até cinco minutos, a mesma marca
no conteúdo **visível** de exatamente um painel, PID foreground e ambiente
concordantes. Ele invoca o hook nativo e confere o registro. Não envia prompts.
Use o pane/UUID retornado para abrir e confira `list` novamente.
Se a marca saiu da tela, publique uma nova e tente a recuperação novamente.
Em divergência/ambiguidade, não improvise um registro manual nem envie.
Essa recuperação pontual não corrige futuras trocas /new ou /resume.
Não use título, pasta ou foco como vínculo.
Não altere a skill genérica embutida no binário Herdr.

## Checklist solicitado pelo usuário

Quando a pessoa pedir o painel com pendências já levantadas, abra o painel
e importe um Markdown com `- [ ]` para cada item ainda aberto. Use o arquivo
`.binding.json` cujo UUID corresponde à conversa escolhida e confira com
`items --binding`. Instalação já concluída não entra como pendência.
Itens importados no projeto têm curadoria automática e também podem ser
concluídos manualmente pela tecla 2. Confirme ações no histórico, não presuma
que o modelo reconheceu uma conclusão. Verifique o painel renderizado
com `herdr pane read` e uma captura antes de anunciar que está pronto.

Se o plugin estiver ausente nesta máquina, use o projeto local e execute
`python3 install.py` após a instalação ter sido autorizada. Mantenha projeto
e skill juntos; não copie somente o SKILL.md sem seu wrapper/implementação.
