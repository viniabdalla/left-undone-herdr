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
A pasta só filtra candidatos: identidade para abrir/enviar continua por UUID,
conta e processo. Se o usuário pedir esta conversa, use o vínculo exato abaixo,
mesmo que o diretório de trabalho da ferramenta esteja em outro projeto.

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

Para arquivo escolhido: use `export` ou `import --file <arquivo>` junto com
`--binding <arquivo .binding.json>`. O arquivo de vínculo é criado em
`~/.local/state/left-undone-herdr/`; derive o correto pela sessão no JSON,
não pelo arquivo mais recente. `items --binding ...` mostra o estado.
Importação é aditiva, ignora `[x]` e não reabre baixas manuais.

Os analisadores usam o CLI autenticado da conta verificada: Claude Haiku,
Codex gpt-6-luna com esforço low. Só recebem a resposta final e as promessas
abertas. Não substitua por modelo maior nem reenvie a conversa inteira.
Falhas de login/limite/JSON aparecem no painel; não apagam a lista.

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
Uma conversa já aberta pode precisar de registro inicial: confirme o UUID
real de `CODEX_THREAD_ID` no histórico da conta; publique uma marca aleatória
em uma mensagem de commentary e confira essa marca tanto no histórico
como no conteúdo **visível** do painel. Confira também o PID foreground e
seu ambiente em `/proc/PID/environ`. Só com essas evidências concordantes,
execute o hook nativo `~/.codex/herdr-agent-state.sh session` com o ambiente
desse processo e o JSON SessionStart contendo o UUID e transcript_path reais.
Confira o UUID retornado por `herdr agent get` e rode `list` novamente.
Se houver divergência ou ambiguidade, não registre nem envie: solicite que
a pessoa identifique a conversa. Não use título, pasta ou foco como vínculo.
Não altere a skill genérica embutida no binário Herdr.

## Checklist solicitado pelo usuário

Quando a pessoa pedir o painel com pendências já levantadas, abra o painel
e importe um Markdown com `- [ ]` para cada item ainda aberto. Use o arquivo
`.binding.json` cujo UUID corresponde à conversa escolhida e confira com
`items --binding`. Instalação já concluída não entra como pendência.
Itens importados têm baixa manual pela tecla 2; não prometa que o analisador
vai concluir automaticamente esses itens. Verifique o painel renderizado
com `herdr pane read` e uma captura antes de anunciar que está pronto.

Se o plugin estiver ausente nesta máquina, use o projeto local e execute
`python3 install.py` após a instalação ter sido autorizada. Mantenha projeto
e skill juntos; não copie somente o SKILL.md sem seu wrapper/implementação.
