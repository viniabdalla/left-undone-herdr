# Curadoria automática do projeto

Comportamento aprovado: aplicar automaticamente novidades e atualizações claras;
não duplicar tarefas equivalentes; preservar itens conflitantes sem perguntar;
continuar com as demais novidades. Curadoria altera listas, não executa tarefas.

Decisão de implementação: reutilizar modelos/contas autenticadas existentes,
SQLite e leitura incremental. O curador recebe a resposta final, o pedido recente
e itens compactos do projeto (incluindo promessas de outras sessões como contexto
somente leitura). Tarefas/checklists globais e promessas próprias podem receber
atualização/conclusão baseada em evidência textual. Tarefas nativas e promessas
de outras sessões são somente leitura. Conflitos são omitidos individualmente.

Ações estruturadas: adicionar com escopo projeto/sessão; atualizar; concluir;
consolidar duplicata própria em item existente; declarar IDs conflitantes.
Duplicatas consolidadas ficam arquivadas com registro do destino, não apagadas.
Baixas manuais não são reabertas. Ausência em snapshot não conclui tarefa.

Uma trava por projeto serializa os coletores durante revisão. Escritas da UI
continuam responsivas; se a fotografia da lista muda durante análise, a resposta
obsoleta não é aplicada e o evento é repetido com estado novo. Ações, eventos
processados e log de alterações são transacionais. Cursor só avança após sucesso.

Heartbeat lê arquivos; respostas novas e mudanças reais da lista disparam IA.
Não há chamada em polling ocioso. O contexto evita logs integrais, usa textos
compactos e falha de forma explícita se ultrapassar o orçamento de itens, sem
analisar silenciosamente uma lista incompleta. Mesmos modelos gpt-6-luna/low e
Haiku/low; sem ferramentas ou execução de instruções contidas nos dados.

Interface mantém lista/mouse e informa resumo das alterações no status. `items`
permite consultar a lista sem abrir seletor e um comando de histórico expõe o que
foi aplicado. Filtros sessão/projeto, sincronização entre PCs e /new automático
continuam fora desta mudança.

Validação: duas sessões; duplicata semântica; tarefa diferente preservada;
conflito não bloqueia novidade; evidência exigida; alvo estrangeiro protegido;
snapshot incompleto; concorrência com conclusão/importação; repetir evento/reabrir;
falha do modelo não perde cursor; nenhum custo em polling ocioso; teste com LLM real.
