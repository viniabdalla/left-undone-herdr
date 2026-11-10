---
status: ativo
area: omarchy
prioridade: media
resumo: Painel de tarefas e promessas por conversa no Herdr
atualizado: 2026-11-10
---

# TODO — Left Undone Herdr

## Em andamento
- [ ] Revisar a proteção parcial do Codex após /new e /resume (branch fix/codex-active-thread no worktree ../left-undone-herdr-codex-title, sem commit)

## Próximo
- [ ] Acompanhar a conversa visível e corrigir UUID antigo após /new ou /resume no Codex antes da primeira resposta; revalidar troca/retomada (falha reproduzida ao vivo)
- [ ] Curadoria / resumo de compactação do Claude: não tratar o resumo automático (isCompactSummary) como pedido do usuário; conferir isMeta e textos de sistema do Codex

## Bloqueado
- [ ] Eliminar janela entre verificação e envio — depende de envio condicionado ao UUID na API Herdr

## Feito
- [x] 2026-11-10 Seletor de conversas mostra os títulos dos painéis do Herdr junto dos IDs
- [x] 2026-11-10 Exigir confirmação antes de concluir manualmente; cancelar preserva seleção e página
- [x] 2026-11-10 Codex ocupado: perguntar antes de colocar os selecionados na fila nativa; cancelar preserva seleção e página (fila Claude indisponível nesta versão)
- [x] 2026-11-10 Orientar o LLM a manter o termo técnico junto da tarefa em linguagem simples, sem explicação completa
- [x] 2026-11-10 Adicionar botão Coletar agora e tecla 5, com pedidos agrupados ao coletor ativo e retomada imediata após erro
- [x] 2026-11-10 Curadoria automática do projeto com evidência, duplicatas semânticas, conflitos preservados e histórico de alterações
- [x] 2026-11-10 Planejar e implementar tarefas/checklists persistentes por projeto; promessas privadas e seleção independente
- [x] 2026-11-10 Recuperar conversas Codex sem UUID nativo com recover --marker, cruzando histórico, painel visível e processo
- [x] 2026-11-10 Distribuir versão Git no omarchy2 e Omarchy novo por SSH; 53 testes em cada máquina; tropico-1 excluída a pedido
- [x] 2026-11-10 Inicializar Git e criar repositório privado viniabdalla/left-undone-herdr
