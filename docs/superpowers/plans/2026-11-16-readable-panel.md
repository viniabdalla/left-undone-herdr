# Painel legível — Implementation Plan

> **For agentic workers:** executar inline usando superpowers:executing-plans e testes antes da implementação.

**Goal:** painel claro por projeto e responsável, histórico e organização verificada dos itens existentes.
**Architecture:** ProjectStore oferece visões sem mudar a associação; catálogo de projetos permite navegação. Layout dos cards separado do seletor de conversas. Histórico usa os mesmos IDs e apresenta encerramentos com motivo quando comprovado.
**Tech Stack:** Python stdlib, SQLite, curses.
**Spec:** docs/superpowers/specs/2026-11-16-readable-panel-design.md

## Global Constraints

Preservar seleções por viewer, binding de envio, relógios da curadoria e histórico. Testes exclusivamente temporários. Nenhum reinício do Herdr ou commit/push.

## Review Focus

Visões de outros projetos nunca revelam promessas privadas; histórico não permite envio/conclusão; cards longos não perdem texto; painel estreito mantém controles; reorganização conserva IDs e registra motivos de baixa sem fingir entrega de duplicatas.

### Task 1: Visões de projeto e histórico
- [x] Testar catálogo, visão sem reassociação, isolamento e motivos de encerramento.
- [x] Implementar view_project, available_projects e history_items no ProjectStore. Testes passam.

### Task 2: Cards e navegação
- [x] Testar grupos, títulos, datas discretas, paginação e controles em tamanhos pequenos.
- [x] Implementar layout dos cards e navegação de projeto/histórico na UI. Atualizar testes PTY para alvos reais. Suite completa passa.

### Task 3: Aplicação e organização
- [x] Revisar diff e testar painel descartável no Herdr. Aplicar arquivos revisados preservando mudanças anteriores.
- [x] Backup real, conferir binding e itens contra evidências, locks de projetos, transação auditada para títulos/movimentação/baixas/datas.
- [x] Reabrir somente o painel desta conversa e conferir renderização. Documentar validação e registrar atividade.
