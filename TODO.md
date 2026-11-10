---
status: ativo
area: omarchy
prioridade: media
resumo: Painel de tarefas e promessas por conversa no Herdr
atualizado: 2026-11-10
---

# TODO — Left Undone Herdr

## Próximo
- [ ] Ao enviar com o agente ocupado, perguntar se deseja colocar os itens na fila do harness
- [ ] Acompanhar a conversa visível e corrigir UUID antigo após /new ou /resume no Codex antes da primeira resposta; revalidar troca/retomada (falha reproduzida ao vivo)

## Bloqueado
- [ ] Eliminar janela entre verificação e envio — depende de envio condicionado ao UUID na API Herdr

## Feito
- [x] 2026-11-10 Orientar o LLM a manter o termo técnico junto da tarefa em linguagem simples, sem explicação completa
- [x] 2026-11-10 Adicionar botão Coletar agora e tecla 5, com pedidos agrupados ao coletor ativo e retomada imediata após erro
- [x] 2026-11-10 Curadoria automática do projeto com evidência, duplicatas semânticas, conflitos preservados e histórico de alterações
- [x] 2026-11-10 Planejar e implementar tarefas/checklists persistentes por projeto; promessas privadas e seleção independente
- [x] 2026-11-10 Recuperar conversas Codex sem UUID nativo com recover --marker, cruzando histórico, painel visível e processo
- [x] 2026-11-10 Distribuir versão Git no omarchy2 e Omarchy novo por SSH; 53 testes em cada máquina; tropico-1 excluída a pedido
- [x] 2026-11-10 Inicializar Git e criar repositório privado viniabdalla/left-undone-herdr
- [x] 2026-11-10 Executar validação Codex ao vivo: retomada preserva itens/seleção/baixas, mas transição mantém UUID antigo até primeira resposta; correção permanece pendente
- [x] 2026-11-10 Instalar atalho left-undone por repo com seletor no próprio terminal
- [x] 2026-11-10 Mouse: seleção, ações, páginas e fechamento clicáveis; texto completo ajustado à largura
- [x] 2026-11-10 Claude ao vivo: promessa detectada, enviada pelo painel, cumprida e concluída automaticamente
- [x] 2026-11-10 Instalar plugin e skill na tropico-2
- [x] 2026-11-10 Recuperar contexto do app-server por UUID nativo e processo verificado
- [x] 2026-11-10 Criar checklist próprio do projeto
