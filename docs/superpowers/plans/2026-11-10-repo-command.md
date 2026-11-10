# Repo Command Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task.

**Goal:** Abrir Left Undone pelo repo atual sem misturar sessões.
**Architecture:** Módulo de descoberta por histórico e raiz Git; CLI filtra e encaminha ao painel/seletor existente.
**Tech Stack:** Python stdlib, Git, curses, SQLite, Herdr.
**Spec:** docs/superpowers/specs/2026-11-10-repo-command-design.md

## Global Constraints
Preservar chaves e dados existentes; abertura/envio continuam verificando UUID/processo.
Não reiniciar Herdr. Sem Git no projeto: backup local em /tmp/left-undone-repo-baseline em vez de worktree/commit.
Autorização de implementação já recebida; execução inline.

## Review Focus
Subpastas/symlinks e checkouts diferentes; UUID incorreto no log; seletor com cwd diferente;
sessões encerradas; mudança de sessão entre seleção e abertura.

## Task 1: Descoberta e comando
- [x] Criar testes com repos Git temporários, históricos Codex/Claude e SQLite real;
      cobrir uma/várias/zero sessões, contagens isoladas e encaminhamento de filtro ao split.
- [x] Executar testes e confirmar falhas pela funcionalidade ausente.
- [x] Criar left_undone/repository.py: project_root, session_project, repository_sessions,
      saved_sessions e pending_counts; integrar app.py e ui.py.
- [x] Instalar link CLI com verificação de conflito; atualizar README e skill.
- [x] Executar suíte completa e revisão independente; validar CLI e seletor reais no Herdr.

## Ledger
Pré-flight: app passa bindings/contagens ao picker; repository não muda Binding nem Store.
Ruling: manter projeto sem Git, conforme pendência separada já existente.
Steering: usuário pediu opções no terminal, sem popup. CLI interativo usa curses inline;
sem TTY usa split normal. Manter comportamento de abertura direta para sessão única.

Task 1: complete — 53 testes; revisão independente final sem achados bloqueantes;
CLI instalado localmente e seletor inline validado com PTY real + Enter.
