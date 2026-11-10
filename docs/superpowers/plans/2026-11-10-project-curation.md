# Project Curation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation.

**Goal:** Automatically curate project tasks with deduplication and conflict guards.
**Architecture:** New curation module handles compact snapshots, validated actions,
project locking and transactions. Existing collector gets an optional audit
callback; native task snapshots retain absent items in curated project mode.
**Tech Stack:** Python stdlib, SQLite, curses, current authenticated Codex/Claude CLIs.
**Spec:** ../specs/2026-11-10-project-curation-design.md

## Constraints and review focus
- Preserve manual tombstones, IDs, source sessions and per-session selection.
- No blind writes from stale snapshots or foreign-session task changes.
- All applied updates/completions need evidence from the triggering exchange.
- New task proposals must see the existing project list before insertion.
- No idle LLM calls or full-transcript prompts; repeated events are idempotent.

## Tasks
1. Write failing transaction/guard tests in tests/test_curation.py; implement
   Curator, CuratedStore and structured validation in left_undone/curation.py.
2. Extend Analyzer with configurable rules/schema/input while preserving defaults;
   add optional Collector audit callback and recent-user context. Integrate
   project lock and changed-list review in app.collect; expose changes history.
3. Test transcript-driven flow, no-op polling, failure/retry, evidence and races.
   Run a real-model fixture. Review independently and resolve substantive findings.
4. Update docs, back up state, restart owned panel, verify another session reads
   the project's list, commit/push and refresh available installations.

Run `python3 -m unittest discover -s tests -q`, compileall and git diff --check.

## Resultado

Etapas 1–3 concluídas: 86 testes, revisão independente com quatro correções,
teste real gpt-6-luna/low e teste de consumo da skill. Ativação local com backup
realizada; publicação e distribuição seguem a instalação existente.
