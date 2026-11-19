# Collect Now Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Request immediate collection with a button or key 5.

**Architecture:** A request file for each binding wakes the existing collector. The loop consumes the request before checking identity and collecting.

**Tech Stack:** Python, curses, unittest.

**Spec:** docs/superpowers/specs/2026-11-10-collect-now-design.md

## Global Constraints

Preserve automatic collection, identity checks and mutual exclusion. Keep the models and avoid reprocessing consumed events.

## Review Focus

Check repeated clicks, requests during collection, error backoff, collector shutdown and narrow layouts with items selected.

### Task 1: Button and on-demand collection

**Files:** `left_undone/ui.py`, `left_undone/ui_layout.py`, `left_undone/app.py`, new `left_undone/collection_request.py`, `tests/test_collection_request.py`, `tests/test_mouse_layout.py`.

**Interfaces:** `request_collection(worker, path)` checks that the process is active and records the request. `wait_for_collection(path, seconds)` interrupts the wait when a request arrives.

- [x] Write layout and integration tests with the real collector. Use deterministic fixtures only for Herdr verification and external analysis.
- [x] Observe failures before implementation.
- [x] Coalesce requests, interrupt waits and implement the button and key 5.
- [x] Run the full suite and the curses panel in a PTY. Update the README, skill and TODO.
- [x] Review the diff and record the operational result.

## Result

96 tests passed. compileall and git diff --check reported no errors. A real curses PTY verified the click and key 5. A rasterized 40×24 preview confirmed the layout. Independent review reported no findings. Operational history entry 13fc5939-9e0f-4a2e-baf3-e6f7b08c41eb was recorded and verified. An already open panel requires closing and reopening to load the update.
