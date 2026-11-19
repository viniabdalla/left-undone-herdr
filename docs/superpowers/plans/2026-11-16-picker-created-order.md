# Global Picker and Creation Order Implementation Plan

> **For agentic workers:** implement inline with superpowers:executing-plans and superpowers:test-driven-development.

**Goal:** Open the global picker with the short command. Show creation dates in the panel and allow sorting by them.
**Architecture:** Keep the existing query and identity logic. Store timestamps separately and sort only for display.
**Tech Stack:** Python 3.10+, SQLite, curses, stdlib.
**Spec:** docs/superpowers/specs/2026-11-16-picker-created-order-design.md

## Global Constraints

Use temporary state for tests. Preserve subsequent work on main and the partial identity worktree. Avoid commits, pushes and Herdr restarts. Preserve curation semantics.

## Review Focus

- Concurrent migration and unknown legacy timestamps must not invent dates.
- Replays, edits, repeated imports and completion preserve creation dates and cannot reopen items.
- Sort across sources. Keep selection by ID and pagination correct.
- Check local, missing and invalid dates, narrow panels and button clicks.
- Keep the picker global even with one conversation or an inherited filter. Reveal a reused panel.

### Task 1: Open globally

- [x] Update tests/test_repository.py so a command with no arguments shows all conversations, including the single-session and inherited-filter cases.
- [x] Observe failure in the repository suite before removing the implicit filter in app.main.
- [x] Add a focus test for reused panels in tests/test_runtime.py and implement it in app.open_panel.
- [x] Run the relevant tests. All pass.

### Task 2: Creation dates

- [x] Create tests/test_creation.py covering legacy migration, multiple connections, new imports and transcript timestamps for tasks, promises and curation. Preserve dates across edits and replay.
- [x] Observe failures. Implement item_creation and its trigger in core.Store. Join created_at in Store.items and ProjectStore.items. Propagate new event timestamps in core.Collector, Store.commit_line and curation.Curator.
- [x] Run creation/core/projects/curation tests. All pass.

### Task 3: Ordering and interface

- [x] Create tests/test_ordering.py and a PTY test for creation order across sources, unknown dates last, button/key 6 toggling with selection preserved, local dates and narrow width.
- [x] Observe failures. Implement sort_items in ui_layout, include the date in item text and add a top button. ui.panel retains the direction and selects using sorted visible items.
- [x] Update README, skill and TODO. Run the full suite, compileall and diff --check. Review and install verified files in the main checkout without a reset, merge or commit. Check the picker and panel with disposable data.
