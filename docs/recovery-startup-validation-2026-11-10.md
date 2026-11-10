# Falha de abertura na segunda sessão

O teste manual do usuário produziu UUID/processo ausente e falha em recover.
O screenshot mostra o token de commentary quebrado entre duas linhas.
Inspeção posterior confirmou UUID real no histórico, marca recente de assistant
commentary, processo Codex foreground e pane correspondente. A mesma marca,
ainda dentro da validade, recuperou o registro e permitiu abrir o painel da
sessão criada pelo usuário. Nenhuma sessão adicional foi criada.

O erro original não registrava a etapa que falhou. Não é possível afirmar se
na primeira tentativa faltava persistência do histórico ou renderização do
viewport; a tentativa posterior prova que as evidências ficaram disponíveis.

Correção: descoberta sem candidatos tolera atraso curto de publicação, com nova
verificação completa. Marcas completas podem atravessar quebras físicas de linha;
caracteres não são corrigidos nem prefixos aceitos. Dois candidatos recusam sem
esperar que um desapareça. Registro/hook e confirmação final não são repetidos.
Erros agora distinguem processo, histórico, commentary recente e viewport.

94 testes aprovados, incluindo histórico publicado após a primeira leitura,
token quebrado, token incorreto, ambiguidade e falhas de registro. Conferência
real comparou IDs/textos compartilhados entre a sessão original e a nova sessão.

Na mesma conferência foi encontrada uma falsa pendência criada a partir do guia
de testes do assistente: o exemplo Teste LU-1350. O histórico de curadoria provou
que veio da resposta “como eu testo?”, não de um pedido real para construir a
tela. Essa entrada foi arquivada com backup e registro `dismiss-example`.
Blocos cercados por fences na resposta do assistente agora ficam fora da evidência
de tarefas; pedidos reais do usuário continuam disponíveis, inclusive checklists.
O prompt distingue exemplos, mensagens sugeridas e instruções de teste de trabalho
efetivamente solicitado. Há testes de regressão para exemplo e pedido real.
O teste com modelo real retornou zero ações para o guia original e manteve adição,
conclusão, deduplicação e preservação de conflitos no cenário de trabalho real.
Uma rodada intermediária não consolidou a duplicata; a instrução de reconciliar
itens existentes foi esclarecida antes da rodada aprovada. Julgamento semântico
continua dependendo do modelo, não é uma garantia determinística.
