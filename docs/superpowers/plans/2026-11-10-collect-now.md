# Coletar agora Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Solicitar coleta imediata por botão e tecla 5.

**Architecture:** Arquivo de solicitação por vínculo acorda o coletor existente;
o loop consome o pedido antes de verificar identidade e coletar.

**Tech Stack:** Python, curses, unittest.

**Spec:** docs/superpowers/specs/2026-11-10-collect-now-design.md

## Global Constraints

Preservar coleta automática, validação de identidade e exclusão mútua.
Não alterar modelos nem reprocessar eventos já consumidos.

## Review Focus

Cliques repetidos; pedido durante coleta; espera após erro; coletor encerrado;
layout estreito com itens selecionados.

### Task 1: Botão e coleta sob demanda

**Files:** `left_undone/ui.py`, `left_undone/ui_layout.py`,
`left_undone/app.py`, novo `left_undone/collection_request.py`,
`tests/test_collection_request.py`, `tests/test_mouse_layout.py`.

**Interfaces:** `request_collection(worker, path)` confirma processo ativo e
grava pedido; `wait_for_collection(path, seconds)` interrompe espera no pedido.

- [x] Escrever testes de layout e integração com coletor real, substituindo
  somente verificação Herdr/análise externa por fixtures determinísticas.
- [x] Observar falhas antes da implementação.
- [x] Implementar solicitação agrupada, espera interrompível e botão/tecla 5.
- [x] Rodar suíte completa e painel curses em PTY; atualizar README/skill/TODO.
- [x] Revisar diff e registrar resultado operacional.

## Resultado

96 testes passaram; compileall e git diff --check sem erros.
Clique/tecla 5 verificados em curses real via PTY. Layout conferido visualmente
em prévia rasterizada de 40×24. Revisão independente sem achados.
Histórico operacional registrado e verificado: 13fc5939-9e0f-4a2e-baf3-e6f7b08c41eb.
Painel já aberto requer fechar/reabrir para carregar o código atualizado.
