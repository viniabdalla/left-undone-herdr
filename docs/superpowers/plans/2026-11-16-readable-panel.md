# Readable Panel Implementation Plan

> **For agentic workers:** implement inline with superpowers:executing-plans and tests before implementation.

**Goal:** Make tasks readable by project and owner, expose history and verify the organization of existing items.
**Architecture:** ProjectStore provides views without changing the association. A project catalog supports navigation. Card layout is separate from the conversation picker. History retains IDs and shows reasons for closure when supported by evidence.
**Tech Stack:** Python stdlib, SQLite, curses.
**Spec:** docs/superpowers/specs/2026-11-16-readable-panel-design.md

## Global Constraints

Preserve per-viewer selections, the delivery binding, curation clocks and history. Use only temporary test state. Avoid Herdr restarts, commits and pushes.

## Review Focus

Other projects' views protect private promises. History disables sending and completion. Long cards preserve all text and narrow panels keep controls. Reorganization preserves IDs and records closure reasons, distinguishing duplicates from delivered work.

### Task 1: Project views and history

- [x] Test the catalog, views without reassociation, isolation and closure reasons.
- [x] Implement view_project, available_projects and history_items in ProjectStore. Tests pass.

### Task 2: Cards and navigation

- [x] Test groups, titles, understated dates, pagination and controls at small sizes.
- [x] Implement card layout and project/history navigation. Update PTY tests to use actual targets. The full suite passes.

### Task 3: Apply changes and organize existing items

- [x] Review the diff and test a disposable Herdr panel. Apply reviewed files while preserving earlier changes.
- [x] Back up live state, check the binding and items against evidence, acquire project locks and use an audited transaction for titles, moves, closures and dates.
- [x] Reopen only this conversation's panel and check its rendering. Document validation and record the activity.
