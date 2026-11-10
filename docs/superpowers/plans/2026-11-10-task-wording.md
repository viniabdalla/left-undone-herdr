# Task wording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Manter o técnico junto de uma tarefa curta e fácil de entender.

**Architecture:** Alterar os prompts existentes dos dois analisadores, usados
pelos CLIs Codex e Claude; preservar validação e esquema JSON.

**Tech Stack:** Python, prompts estruturados, CLIs autenticados existentes.

**Spec:** docs/superpowers/specs/2026-11-10-task-wording-design.md

## Global Constraints

Sem mudar modelo, limites de texto, escopo, evidência ou critérios de conclusão.

## Review Focus

Não inventar termos; preservar requisitos distintos; não transformar exemplos em
trabalho; não parafrasear evidence; não reescrever listas antigas só pelo estilo.

### Task 1: Orientar e conferir respostas reais

- [x] Editar somente as instruções de texto em runtime.py e curation.py.
- [x] Exercitar ambos os prompts com LLM real e revisar os textos/ações obtidos.
- [x] Executar suíte existente, compileall e diff --check.
- [x] Documentar o comportamento, concluir a pendência e registrar o resultado.

Resultado: docs/task-wording-validation-2026-11-10.md.
