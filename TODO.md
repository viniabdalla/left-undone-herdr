---
status: ativo
area: omarchy
prioridade: media
resumo: Painel de tarefas e promessas por conversa no Herdr
atualizado: 2026-11-10
---

# TODO — Left Undone Herdr

## Em andamento
- [ ] Revisão do Codex sobre fix/codex-active-thread (worktree ../left-undone-herdr-codex-title, sem commit)

## Próximo
- [ ] Ao enviar com o agente ocupado, perguntar se deseja colocar os itens na fila do harness
- [ ] Codex /new: reconhecer a conversa nova antes da primeira mensagem (hoje só bloqueia o vínculo antigo; falta UUID completo verificável)
- [ ] Codex /resume de conversa nunca confirmada no mesmo processo: reconhecer sem primeira mensagem
- [ ] Decidir com Vini como lançar Codex com -c 'tui.terminal_title=["thread-id"]' (sem isso painéis Codex ficam bloqueados) antes de mesclar fix/codex-active-thread

## Bloqueado
- [ ] Eliminar janela entre verificação e envio — depende de envio condicionado ao UUID na API Herdr

## Feito
- [x] 2026-11-10 Codex /new e /resume: bloquear vínculo antigo e reconhecer retomada já confirmada, provado pelo título nativo thread-id (parcial)
- [x] 2026-11-10 Orientar o LLM a manter o termo técnico junto da tarefa em linguagem simples, sem explicação completa
- [x] 2026-11-10 Adicionar botão Coletar agora e tecla 5, com pedidos agrupados ao coletor ativo e retomada imediata após erro
- [x] 2026-11-10 Curadoria automática do projeto com evidência, duplicatas semânticas, conflitos preservados e histórico de alterações
- [x] 2026-11-10 Planejar e implementar tarefas/checklists persistentes por projeto; promessas privadas e seleção independente
- [x] 2026-11-10 Recuperar conversas Codex sem UUID nativo com recover --marker, cruzando histórico, painel visível e processo
- [x] 2026-11-10 Distribuir versão Git no omarchy2 e Omarchy novo por SSH; 53 testes em cada máquina; tropico-1 excluída a pedido
- [x] 2026-11-10 Inicializar Git e criar repositório privado viniabdalla/left-undone-herdr
- [x] 2026-11-10 Executar validação Codex ao vivo: retomada preserva itens/seleção/baixas, mas transição mantém UUID antigo até primeira resposta; correção permanece pendente
- [x] 2026-11-10 Instalar atalho left-undone por repo com seletor no próprio terminal
