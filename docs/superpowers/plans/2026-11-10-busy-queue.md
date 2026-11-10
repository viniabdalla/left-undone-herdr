# Busy agent queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Confirmar com o usuário antes de enfileirar pedidos para agente ocupado.

**Architecture:** Erro tipado de agente ocupado abre confirmação com seleção
congelada. Confirmar chama fila nativa Codex por UUID após revalidação; cancelar
retorna ao painel. Não altera o caminho de envio com agente livre.

**Tech Stack:** Python, curses, CLI Codex, unittest/PTY.

**Spec:** docs/superpowers/specs/2026-11-10-busy-queue-design.md

## Global Constraints

Preservar validação de identidade, lista e seleção ao cancelar/falhar. Sem
retry automático, sem --resume e sem alterar sessões reais em testes.

## Review Focus

Troca de sessão durante confirmação; seleção/texto mudados; falha ambígua do
CLI; confirmação em painel estreito; Claude sem API de fila.

### Task 1: Runtime e confirmação

- [x] Escrever testes de regressão que falhem antes da implementação.
- [x] Adicionar AgentBusy/QueueOffer, snapshot e queue_selected; native queue
  exige verificação nova e recibo do CLI com o UUID exato da conversa.
- [x] Adicionar confirmação modal curses (mouse, 1/2/Esc), sem aplicar outras
  ações enquanto estiver aberta; Claude mostra indisponibilidade.
- [x] Validar persistência real com CLI Codex em CODEX_HOME temporário, sem
  modelo, e testar UI curses em PTY; executar suíte completa.
- [x] Revisar, documentar, recarregar painel e registrar resultado.

Resultado: docs/busy-queue-validation-2026-11-10.md. Painel recarregado; pendência correspondente concluída.
