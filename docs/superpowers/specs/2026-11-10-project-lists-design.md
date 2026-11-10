# Listas persistentes por projeto

Comportamento aprovado pelo usuário: tarefas/checklists compartilhados por
projeto; promessas específicas pertencem à conversa de origem. O painel deverá
acompanhar a conversa visível. A lista compartilhada é a primeira etapa,
priorizada pelo usuário antes de corrigir a transição `/new`/`/resume`.

Cada projeto reúne tarefas de suas sessões Codex e Claude. Concluir em um painel
conclui para todos; selecionar para enviar é privado à conversa. Fechar painéis,
reiniciar processos ou criar outra sessão não perde as tarefas. Importações novas
pertencem ao projeto; tarefas nativas mantêm a sessão de origem para um snapshot
de uma sessão não encerrar tarefas de outra. Promessas de outra sessão não são
analisadas, mostradas nem encerradas pela sessão atual.

Decisão de implementação: reutilizar SQLite e preservar IDs/históricos existentes,
adicionando associação sessão→projeto e uma visão compartilhada. Migrar todas as
linhas para uma nova chave apagaria a proveniência necessária aos coletores;
arquivos Markdown como estado principal perderiam transações e baixas manuais.

Projeto padrão é a raiz Git do cwd inicial verificável da conversa (sem Git,
pasta exata; worktrees separados). `--project` permite associar explicitamente
uma conversa que começou em outra pasta. Associação explícita prevalece sobre
inferência. Projetos sem histórico verificável continuam com estado de sessão.
Listas são locais à máquina nesta etapa; não há sincronização entre PCs.

UI mantém mouse/teclas e indica o projeto. Exportar representa a lista visível;
importar cria tarefas compartilhadas. A seleção do destinatário continua exigindo
identidade verificada. Esta etapa não declara resolvido o UUID nativo obsoleto:
troca automática da conversa e envio atômico permanecem trabalho separado.

Validação: duas sessões/agentes no mesmo projeto, outro projeto isolado, promessas
privadas, seleção independente, conclusão compartilhada, importação deduplicada,
baixas persistentes, snapshots independentes, dados legados e reabertura.
