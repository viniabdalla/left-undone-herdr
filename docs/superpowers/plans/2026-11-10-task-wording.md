# Task wording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the technical term alongside a short task that is easy to understand.

**Architecture:** Edit the two existing analyzer prompts used by the Codex and Claude CLIs. Preserve validation and the JSON schema.

**Tech Stack:** Python, structured prompts, existing authenticated CLIs.

**Spec:** docs/superpowers/specs/2026-11-10-task-wording-design.md

## Global Constraints

Preserve models, text limits, scope, evidence and completion criteria.

## Review Focus

Keep distinct requirements, avoid inventing terms or turning examples into tasks, preserve evidence verbatim and avoid rewriting old lists purely for style.

### Task 1: Guide and verify real responses

- [x] Edit only the text instructions in runtime.py and curation.py.
- [x] Exercise both prompts with a real model and review the generated text and actions.
- [x] Run the existing suite, compileall and diff --check.
- [x] Document the behavior, complete the task and record the result.

Result: docs/task-wording-validation-2026-11-10.md.
