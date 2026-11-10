# Confirm completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Pedir confirmação antes de qualquer conclusão manual no painel.

**Architecture:** DoneOffer congela seleção; modal compartilhado com a fila
aceita confirmar/cancelar. confirm_done valida o snapshot e aplica Store.done
sob transação. Modelos e regras de curadoria não mudam.

**Tech Stack:** Python, curses, SQLite, unittest e PTY.

**Spec:** docs/superpowers/specs/2026-11-10-confirm-completion-design.md

## Global Constraints

Preservar seleção/página no cancelamento e regras de conclusão automática.
Confirmar somente itens apresentados; bloquear confirmação invisível.

## Review Focus

Seleção vazia; nova seleção ou alteração de texto durante modal; mouse e tecla
2 abrindo o mesmo modal; Esc sem fechar painel; redimensionamento pequeno.

### Task 1: Confirmação manual

- [x] Escrever e observar regressões antes de implementar.
- [x] Adicionar DoneOffer/confirm_done; compartilhar layout de confirmação.
- [x] Atualizar testes de conclusão para confirmação explícita e exercitar
  cancelar/confirmar/resize em curses real.
- [x] Rodar suíte, revisar, documentar, recarregar painel e registrar resultado.

Resultado: docs/confirm-completion-validation-2026-11-10.md.
