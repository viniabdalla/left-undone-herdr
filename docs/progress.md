# Left Undone — implementation of the approved plan

The plan paired a Herdr plugin and skill with Python, curses and SQLite. It called for per-session tasks and promises, Claude Haiku and Codex gpt-6-luna low, a right-hand panel, letters and keys 1/2/3/4, incremental collection, sending through a verified binding, additive import and live tests.

1. State and adapters.
2. Analyzers.
3. Herdr binding and panel.
4. Packaging and skill.
5. Tests and review.

The project started empty. Implementation went directly into the new left-undone-herdr directory, with a symlink under the old name to preserve the active session. There was no base repository or worktree to isolate. Sending requires a Herdr-identified session. Inherited context and focus are insufficient. The Linux process verifies the account only. Operational task: 9a097abf-870c-465a-b6ab-97f406c1b100.

Implemented state, adapters, analyzers, binding, curses UI, manifest, shared Codex/Claude skill and a local installer that preserves conflicting files. Initially 14 tests passed. Live Codex Luna returned done=[1,2], add=[Add retry tests.]. Live Claude returned API 429 usage_limit_reached. Claude histories can be symlinked across accounts, so account identity always comes from the verified process.

Independent review by gpt-6-astra identified four failures: an orphan collector after SIGTERM/SIGHUP, a stale binding after resuming the same UUID, unreliable deduplication by persisted PID, and native completion blocking reopening. All four regression tests failed before their fixes. Afterward 20 tests passed, including real signal termination in a PTY. Fixes added signal cleanup, full binding comparison, deduplication using the panel's foreground process and environment with a startup window, and distinct manual tombstones and native completion.

A disposable live Codex session detected a promise to write a poem. Pressing a and 1 in the panel sent it exclusively to lu-demo. The agent replied with the poem and the analyzer removed the fulfilled promise, leaving zero open items. Reopening passed. Focus stayed in the original pane and no server restarted. Herdr 0.9.1 lacks atomic compare-and-send by UUID. The implementation checks session, terminal, foreground PID, starttime, account and history immediately before sending. A documented native TOCTOU window remains.

Extended verification passed 21 tests. An additional guard prevents inheriting API credentials from another account in the calling process. The skill passed quick_validate and the modules compiled. Closing the panel externally stopped its collector. Two concurrent opens produced one panel. The demo panes were closed. Live Claude validation was initially partial due to account quota.

On 2026-11-10, tropico-2 completed the live Claude cycle with Haiku. The promise was detected, sent through the UI, fulfilled and automatically removed (dismissed=0). Evidence is in docs/verification.md.
