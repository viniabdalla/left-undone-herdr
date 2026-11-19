# Verification — 2026-11-10, omarchy2

## Automated tests

`python3 -m unittest discover -s tests -v` ran 21 tests. All passed. Coverage included import/export, session isolation, JSON validation, partial lines, repeated turns, cursor recovery, analyzer failure and retry, Codex plans, Claude tasks, closing promises and accounts sharing a log. Tests also covered session, terminal and foreground PID changes, selection and sending, pagination, reopening after process replacement and slow startup.

The shutdown test uses a real PTY and subprocesses. SIGTERM to the UI must stop the collector. Four regressions from independent review failed before their fixes and passed afterward. The tests require no paid model calls.

## Live execution

- Herdr client/server 0.9.1, protocol 22, accepted the plugin link without warnings.
- The `open` action appeared in `herdr plugin action list`.
- The skill was installed for both agents and the wrapper was executable.
- With an authenticated CLI, Codex gpt-6-luna/low received a synthetic prompt covering completed work, an abandoned promise, a new promise, a question and a user obligation. It returned `done: [1,2]`, `add: ["Add retry tests."]`.
- In a disposable Codex conversation in pane w1P:p3, UUID 01a1c3d1-4222-7640-9a8f-1ffd68ecdd5e, the agent promised a poem. The collector detected one promise. The panel opened on the right and preserved the original focus.
- Pressing `a` and `1` in the panel sent the item to that conversation. The agent replied with a two-line poem and the analyzer closed the promise, leaving zero open items. Opening again with the panel active returned `reused: true`.
- Esc closed the panel. Reopening recovered state without repeating analysis.
- Closing the panel externally through plugin pane close stopped the real collector.
- Two simultaneous opens returned the same pane. One created it and the other reused it.
- Disposable panes were closed after the test. The original panes and focus were preserved.

## Initial quota block (resolved below)

Authenticated Claude Haiku returned `429 usage_limit_reached`, the account's five-hour limit. The full **live** Claude cycle could not run at that point. Actual history formats (assistant/end_turn and assistant/tool_use) were checked and the adapter had test coverage. A complete demonstration still required restored quota.

## API limitation

Herdr accepts no session precondition on `agent prompt`. A TOCTOU window exists between identity verification and delivery. The README and skill document this. The plugin rejects known inconsistencies and never retries sends.

## tropico-2 — context recovery on 2026-11-10

The Codex TUI had Herdr context, but tools run by the app-server did not. The missing native Codex integration was installed without restarting servers. A random commentary marker, actual history, visible pane content and the foreground PID confirmed the current conversation. The native hook registered its real UUID.

The wrapper now recovers the environment by exact native UUID. It queries the socket for each interactive Codex process and checks the foreground on the same server. Missing, inconsistent or duplicate matches prevent recovery. Independent review identified a socket change without revalidation. The fix and a regression test were included.

25 tests passed. The skill passed quick_validate. The plugin and skill were installed, and the checklist was imported and deduplicated. Reopening returned reused:true. The rendering was checked through herdr pane read and captured in docs/evidence/checklist-tropico-2.txt. The local graphical screen belonged to another desktop and provided no evidence for the remote panel.

Automatic conversation switching and resumption through the app-server still needed live validation and were not simulated in this ongoing conversation. The Claude test completed below. The API's atomic-send limitation remained.

## Live Claude — completed on 2026-11-10, tropico-2

Claude Code 2.1.319, Haiku 5.5/low, authenticated account. Native Claude integration v10 was installed without restarting the server. Disposable session 8831ff18-2100-40c6-8bfe-2a9d9b2bd98e had its agent in w3:p5 and its panel in w3:p6.

1. Claude promised to write a two-line poem when reminded.
2. The real collector and Haiku analyzer created a promise in the panel.
3. Keys a and 1 selected and sent the promise exclusively to Claude.
4. Claude received "You left this undone" and wrote the poem.
5. The analyzer closed the item automatically. Zero items remained open, status=done and dismissed=0. The test session had no manual closure.
6. The disposable panel and agent were closed and focus returned to the original checklist. The Claude validation item was manually removed from the main checklist.

Evidence is in docs/evidence/claude-live-before.txt, claude-live-conversation.txt, claude-live-after.txt and claude-live-state.json.

## Mouse and text wrapping — 2026-11-10

The curses UI uses a cell-based layout, hit areas for each line and SGR events. Long tasks wrap to the available width and continue across pages when taller than the panel. Buttons cover selection, sending, completion, export, import, pagination and closing. The wheel turns pages, and the conversation picker has an Open button. Keyboard controls remain available.

40 tests passed on tropico-2 and omarchy2. Real PTY/ncurses tests exercised a click on a continuation line, single delivery, resizing and keyboard completion. Independent review identified small-panel issues, selection hidden after picker resize, and a ZWJ issue. Tests reproduced each before its fix. Final review found no issues. The skill passed quick_validate.

In live Herdr, SGR events sent to a disposable panel verified selection on a continuation line, the Complete button and wheel movement in both directions. The test panel was closed. The original panel was reopened with the same list and selection and its former width restored to 48 columns. The new controls selected and completed the mouse-support task itself. Terminal evidence is in docs/evidence/mouse-herdr-*.txt and mouse-installed-*.txt. Validation used actual terminal events through Herdr and a PTY. It did not capture a physical mouse click on the remote graphical client.

## Repository shortcut and in-terminal picker — 2026-11-10

- All 53 tests passed with `python3 -m unittest discover -s tests -v`.
- New cases covered repositories, subdirectories and symlinks, distinct worktrees and inherited Git overrides, missing UUID or working directory, one/multiple/zero sessions, invalid saved data and isolated counts. Tests also covered the inline TTY picker, split without a TTY, idempotent installation and preservation of conflicts.
- `left-undone` was installed in ~/.local/bin. Running it in git-todo returned `{"reused": true, "pane": "w3:p8"}`. In left-undone-herdr it correctly reported no verifiable active session from that directory.
- The repository-filtered picker was checked in a temporary Herdr split and removed afterward. See `docs/evidence/repo-picker-live.txt`.
- After the user-requested correction, `TERM=xterm-256color left-undone open` in a real PTY displayed the picker in the calling terminal with agent, UUID and three open items. Enter reused the panel, exited with code 0 and restored the terminal.
- The manifest was updated for a split picker without popup-specific dimensions. Installed Herdr successfully validated `python3 install.py`.
- Visual validation used rendered terminal content. No graphical capture of the remote client was taken.
