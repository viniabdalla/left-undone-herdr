# Mouse Controls Implementation Plan

Goal: Make the existing Herdr checklist and picker operable by mouse, with complete wrapped task text.
Architecture: A pure layout module produces displayed lines and exact hit regions; the curses view routes mouse and keyboard through the existing store/actions. No dependencies or binding changes.
Spec: docs/superpowers/specs/2026-11-10-mouse-controls-design.md
Execution: inline; approved by the user's checklist execution request and reinforced by their narrow-pane screenshot.

## Constraints and review focus
- Existing session checks, send behavior, persistence and keyboard shortcuts stay intact.
- No Git repository exists here: work in the authorized project folder, save the old UI for recovery, do not initialize an unrelated repo/worktree.
- Long rows may continue onto later pages; every character must remain reachable.
- Mouse release activates only the same target pressed; drags, blank space, right clicks and resize must not send.
- Narrow/short terminals, Unicode cell width, conditional action buttons and background changes must preserve correct targets.

## Task 1 — layout and event routing
- [x] Add failing tests for wrapping, page continuation, hit bounds, press/release, resize, disabled/blank actions and picker.
- [x] Add left_undone/ui_layout.py and integrate with ui.py without changing the store or binding.
- [x] Pass new tests and the existing suite.

## Task 2 — real terminal validation and rollout
- [x] Exercise real SGR mouse input and resize in a PTY and a disposable Herdr panel; inspect persisted selection and visible text.
- [x] Review independently, fix supported issues and recheck.
- [x] Update docs/skill, deploy both machines, reopen only this conversation's panel preserving its state and mark this task complete.

## Ledger
- Baseline: 25 tests passed previously; current implementation has no mouse handling and truncates task lines.
- Ruling: preserve the existing project without Git; initializing Git is a separate pending user task.

- Validation: 40 tests passed, including real ncurses SGR click/send-once/resize. Actual Herdr panel accepted wrapped-row selection, completion and wheel events. Independent review found three issues; each was reproduced, fixed, regression-tested and re-reviewed cleanly.
