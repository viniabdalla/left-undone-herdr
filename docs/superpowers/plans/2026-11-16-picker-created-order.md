# Seletor global e ordem por criação — plano

> **For agentic workers:** executar inline com superpowers:executing-plans e superpowers:test-driven-development.

**Goal:** abrir o seletor global pelo comando curto e permitir ordenar/visualizar datas de criação no painel.
**Architecture:** manter consulta/identidade existentes; timestamps em tabela separada e ordenação só na apresentação.
**Tech Stack:** Python 3.10+, SQLite, curses, stdlib.
**Spec:** docs/superpowers/specs/2026-11-16-picker-created-order-design.md

## Global Constraints

Somente estado temporário em testes. Preservar main posterior e worktree de identidade parcial. Sem commit/push/reinício do Herdr. Sem modificar semântica de curadoria.

## Review Focus

- Migração concorrente e timestamps antigos desconhecidos não devem inventar datas.
- Replays, edições, importação repetida e conclusão não alteram criação nem reabrem itens.
- Ordem combina origens; seleções por ID e paginação permanecem corretas.
- Datas locais, ausentes e inválidas; painéis estreitos e clique no botão.
- Seletor com uma conversa ou ambiente com filtro herdado permanece global; reutilizar mostra o painel.

### Task 1: Abertura global
- [x] Alterar testes em tests/test_repository.py para comando sem argumentos mostrar todas as conversas, incluindo uma única e filtro herdado.
- [x] Rodar suite repository: observar falha antes de remover filtro implícito em app.main.
- [x] Adicionar teste em tests/test_runtime.py para foco no painel reutilizado; implementar em app.open_panel.
- [x] Rodar os testes relevantes: todos passam.

### Task 2: Datas de criação
- [x] Criar tests/test_creation.py: migração legada, múltiplas conexões, novas importações e timestamps de transcrição nas tarefas/promessas/curadoria; edição e replay preservam data.
- [x] Observar falhas; implementar item_creation e trigger em core.Store, juntar created_at em Store.items/ProjectStore.items, propagar timestamp de eventos novos em core.Collector/Store.commit_line e curation.Curator.
- [x] Rodar testes creation/core/projects/curation: todos passam.

### Task 3: Ordenação e interface
- [x] Criar tests/test_ordering.py e teste PTY: ordem por criação entre origens, desconhecidos ao final, botão/tecla 6 alterna e preserva seleção; datas locais e largura estreita.
- [x] Observar falhas; implementar sort_items em ui_layout, data no texto e botão no topo. ui.panel mantém direção e usa visible ordenado para seleção.
- [x] Atualizar README, skill e TODO. Rodar suíte inteira, compileall e diff --check. Revisar diff e instalar os arquivos verificados no checkout main sem reset, merge ou commit; conferir seletor/painel com dados descartáveis.
