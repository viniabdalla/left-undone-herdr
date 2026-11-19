# Repo Command Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task.

**Goal:** Open Left Undone from the current repository while keeping sessions separate.
**Architecture:** Discover sessions from history and Git roots. The CLI filters sessions and forwards them to the existing panel or picker.
**Tech Stack:** Python stdlib, Git, curses, SQLite, Herdr.
**Spec:** docs/superpowers/specs/2026-11-10-repo-command-design.md

## Global Constraints

Preserve existing keys and data. Keep UUID and process checks when opening and sending. Do not restart Herdr. The project had no Git repository, so use a local backup at /tmp/left-undone-repo-baseline in place of a worktree and commit. Inline implementation was authorized.

## Review Focus

Check subdirectories, symlinks, distinct checkouts, incorrect log UUIDs, a picker in a different working directory, closed sessions and a session change between selection and opening.

## Task 1: Discovery and command

- [x] Test with temporary Git repositories, Codex and Claude histories and real SQLite. Cover one, multiple and zero sessions, isolated counts and forwarding the filter to the split.
- [x] Run tests and verify that missing functionality causes failure.
- [x] Create left_undone/repository.py with project_root, session_project, repository_sessions, saved_sessions and pending_counts. Integrate app.py and ui.py.
- [x] Install the CLI link with a conflict check and update README and skill.
- [x] Run the full suite and independent review. Validate the real CLI and picker in Herdr.

## Ledger

The app passes bindings and counts to the picker. Repository discovery preserves Binding and Store. Git initialization remained a separate open task. The user requested in-terminal options without a popup. Use inline curses with a TTY and a regular split without one. Keep direct opening for a single session.

Task 1 completed with 53 tests. Final independent review found no blockers. The CLI was installed locally and the inline picker verified with a real PTY and Enter.
