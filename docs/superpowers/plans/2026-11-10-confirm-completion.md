# Confirm completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Request confirmation before any manual completion in the panel.

**Architecture:** DoneOffer freezes the selection. The shared queue modal accepts confirmation or cancellation. confirm_done validates the snapshot and applies Store.done inside a transaction. Preserve models and curation rules.

**Tech Stack:** Python, curses, SQLite, unittest and PTY.

**Spec:** docs/superpowers/specs/2026-11-10-confirm-completion-design.md

## Global Constraints

Cancellation preserves page and selection. Keep automatic completion rules. Confirm only the items presented and block invisible confirmation.

## Review Focus

Check empty selection, new selections or text changes during confirmation, the same modal opened by mouse and key 2, Esc returning to the panel and resizing to a small window.

### Task 1: Manual confirmation

- [x] Write regression tests and observe failures before implementation.
- [x] Add DoneOffer/confirm_done and share the confirmation layout.
- [x] Update completion tests for explicit confirmation and exercise cancellation, confirmation and resizing in real curses.
- [x] Run the suite, review, document, reload the panel and record the result.

Result: docs/confirm-completion-validation-2026-11-10.md.
