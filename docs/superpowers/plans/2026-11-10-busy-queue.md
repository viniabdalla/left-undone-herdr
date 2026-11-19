# Busy agent queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ask before queueing requests for a busy agent.

**Architecture:** A typed busy-agent error opens a confirmation with a frozen selection. Confirm invokes the native Codex queue by UUID after revalidation. Cancel returns to the panel. An idle agent receives messages as before.

**Tech Stack:** Python, curses, Codex CLI, unittest/PTY.

**Spec:** docs/superpowers/specs/2026-11-10-busy-queue-design.md

## Global Constraints

Preserve identity validation, the list and selection on cancellation or failure. Avoid automatic retries, --resume and changes to real sessions in tests.

## Review Focus

Cover session changes during confirmation, changed selections or text, ambiguous CLI failures, confirmation in a narrow panel and Claude's lack of a queue API.

### Task 1: Runtime and confirmation

- [x] Write regression tests that fail before implementation.
- [x] Add AgentBusy/QueueOffer, a snapshot and queue_selected. Require fresh verification and a CLI receipt containing the exact conversation UUID.
- [x] Add a curses confirmation modal with mouse and 1/2/Esc. Block other actions while open. Report unavailable queueing for Claude.
- [x] Verify real persistence through the Codex CLI with a temporary CODEX_HOME and no model. Test the curses UI in a PTY and run the full suite.
- [x] Review, document, reload the panel and record the result.

Result: docs/busy-queue-validation-2026-11-10.md. Reloaded the panel and completed the corresponding task.
