# Painel legível — validação de 16/11/2026

Pedido aprovado: projeto escolhido, grupos IA/você, títulos destacados e descrições,
datas discretas, histórico e controles de ordem/projeto. Implementação no worktree
`left-undone-herdr-picker-dates`, preservando as alterações anteriores e o worktree
de identidade Codex. Nenhum commit/push ou reinício do Herdr.

## Evidência

139 testes passaram no worktree e na instalação. Testes novos observaram falhas
antes da implementação: isolamento de visões, histórico somente leitura, cards,
paginação e organização atômica. A revisão independente encontrou o risco de mover
tarefas nativas do coletor; o organizador agora recusa essas tarefas, além de
promessas privadas. A nova regressão falhou antes dessa proteção e passou depois.
Tarefas compartilhadas criadas pela curadoria e importações são o único escopo
permitido para a organização aplicada. Seleção de importações legadas é preservada.

O ensaio da organização usou estado descartável com os vinte registros revisados,
sem copiar a base inteira ou executar uma sessão real. Contagens esperadas foram
confirmadas. Prévia com quatro tarefas foi aberta no Herdr em estado temporário,
conferida e fechada. `compileall` e `git diff --check` passaram.

## Organização autorizada dos registros reais

Backup SQLite consistente em `docs/evidence/state-before-readable-panel-20261116.sqlite3`.
Plano com snapshots esperados em `docs/evidence/readable-panel-organization-plan-20261116.json`.
Binding e identidade foram revalidados; somente o painel desta conversa foi fechado.
Locks dos projetos e transação única protegeram a aplicação; qualquer alteração
concorrente no snapshot recusaria o lote inteiro. IDs/fontes foram preservados.
Antes/depois, evidência e motivo estão em `panel_organization`/`item_closures`.
Criações antigas foram recuperadas apenas quando o evento original foi encontrado.

A conversa foi associada ao worktree desta implementação, isolando as quatro
pendências de curadoria. Associação de nenhuma outra conversa foi alterada.
Projetos/listas: Left Undone quatro abertos, Atlas cinco e TaskBlade dois.
Outras listas antigas permanecem acessíveis pelo seletor; não foram reclassificadas
sem conferência. TaskBlade é um grupo de planejamento, sem presumir clone local.

Painel atual `w3:p1J`, vinculado a `w3:p2`, foi reaberto e conferido: quatro cards,
Para você zero, datas conhecidas, botões 6/7/8 e coletor ativo. Snapshots texto/ANSI
ignorados em `docs/evidence/readable-panel-current-20261116.*`.

## Limite

Esta entrega organiza a apresentação e os registros explicitamente revisados.
As quatro melhorias do motor de curadoria continuam pendentes nos cards. Não
alega que o modelo deixou de cometer erros semânticos ou que o Atlas foi ativado.
