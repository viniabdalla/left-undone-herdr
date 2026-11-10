# Validação da curadoria automática

Implementação aprovada para aplicar automaticamente novidades e atualizações,
preservando conflitos e evitando duplicatas. Nenhuma tarefa é executada pelo
curador. Compartilhamento de projeto e promessas privadas continuam intactos.

Verificação local: 86 testes aprovados, compileall e diff --check limpos.
Testes cobrem evidência, alterações de projeto, conclusão/importação concorrente,
ABA, repetição de evento, falha do modelo sem perda do cursor, histórico antigo,
revisão incompleta, checklists maiores, cache por sessão sem polling ocioso,
promessas alheias invisíveis e proteção de tarefas de outra sessão.

Modelo real Codex gpt-6-luna/low, com dados sintéticos em SQLite isolado:
- consolidou “Implementar interação com mouse” em “Adicionar suporte ao mouse”;
- concluiu navegação por teclado com a evidência literal apresentada;
- acrescentou exportação CSV como tarefa de projeto, visível na segunda sessão;
- preservou decisão SQLite em conflito e trabalho de parser da outra sessão;
- repetição sem novidade não chamou o modelo novamente.

Revisão independente encontrou quatro problemas, todos corrigidos e cobertos:
promessas privadas alheias escondendo trabalho visível; cache global impedindo
revisão pelo dono; conclusões históricas atingindo tarefas novas; orçamento antigo
de cinco adições insuficiente para checklists. Teste de consumo da skill confirmou
instruções de segunda sessão, conclusão automática de importados e limites de envio.

Backup consistente precede ativação no painel real. Evidências brutas e dados
temporários permanecem fora do Git. A falha de destinatário obsoleto após /new e
/resume continua separada; este trabalho não a declara resolvida.

Limites explícitos: últimos 12 mil caracteres da resposta e 4 mil dos pedidos;
500 itens de contexto e 50 ações por categoria. Resposta declarada incompleta
não consome o evento. A deduplicação semântica depende do julgamento do modelo;
histórico preserva as alterações, enquanto as verificações determinísticas
protegem propriedade, versões, datas, evidência textual e baixas manuais.
