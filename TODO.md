---
status: ativo
area: omarchy
prioridade: media
resumo: Painel de tarefas e promessas por conversa no Herdr
atualizado: 2026-11-17
---

# TODO — Left Undone Herdr

## Em andamento
- [ ] Revisar a proteção parcial do Codex após /new e /resume (branch fix/codex-active-thread no worktree ../left-undone-herdr-codex-title, sem commit)
- [ ] Modo sem projeto: auditor de promessas ainda não mostra tarefas do usuário (VOCÊ) — primeiro trabalho do Dev (Hermes), conduzido pelo plano em ~/Projects/dev-hermes-setup/docs/orquestracao.md

## Próximo
- [ ] Reprocessar as 2 respostas do NAS (nas-tropico) com o curador novo e arquivar a tarefa genérica antiga
- [ ] Curador: não concluir tarefa sem prova de que foi feita (ex.: fechou "checar erros SATA" só porque os erros subiram)
- [ ] Acompanhar a conversa visível e corrigir UUID antigo após /new ou /resume no Codex antes da primeira resposta; revalidar troca/retomada (falha reproduzida ao vivo)
- [ ] Curadoria / resumo de compactação do Claude: não tratar o resumo automático (isCompactSummary) como pedido do usuário; conferir isMeta e textos de sistema do Codex

## Bloqueado
- [ ] Eliminar janela entre verificação e envio — depende de envio condicionado ao UUID na API Herdr

## Feito
- [x] 2026-11-16 Painel por projeto com títulos destacados, grupos IA/você, histórico e datas discretas
- [x] 2026-11-16 Comando curto abre seletor global; reencontrar painel existente dá foco a ele
- [x] 2026-11-16 Mostrar data de criação e alternar ordem por mais recentes/antigas no topo, preservando seleção
- [x] 2026-11-11 Atualizar tropico-2, omarchy2 e Omarchy novo para 70b61a3 (git pull + install.py; testes OK nas três)
- [x] 2026-11-11 Criar CLAUDE.md com comandos e arquitetura (identidade, coleta, curadoria, armazenamento)
- [x] 2026-11-11 Curador: separar listas de pendências em itens (sem tarefa guarda-chuva) e marcar tarefas do usuário com VOCÊ
- [x] 2026-11-10 Seletor de conversas mostra os títulos dos painéis do Herdr junto dos IDs
- [x] 2026-11-10 Exigir confirmação antes de concluir manualmente; cancelar preserva seleção e página
- [x] 2026-11-10 Codex ocupado: perguntar antes de colocar os selecionados na fila nativa; cancelar preserva seleção e página (fila Claude indisponível nesta versão)
- [x] 2026-11-10 Orientar o LLM a manter o termo técnico junto da tarefa em linguagem simples, sem explicação completa
