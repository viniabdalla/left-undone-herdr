# Global picker and creation date validation

On 2026-11-16, implementation used worktree `left-undone-herdr-picker-dates` and branch `feat/picker-created-order` from main `0ae0c31`. The `left-undone-herdr-codex-title` worktree and its unique Codex identity commit were preserved.

## Checks

- Baseline before code changes: 117 tests passed.
- Reproduced the short-command failure and the focus failure on panel reuse.
- Creation tests failed before implementation. They cover source timestamps, editing, replay, old records, import, tombstones and multiple connections.
- A PTY test verified key 6, button clicks and selection across order changes, sending, queueing and confirmation. Disconnecting the order toggle makes the test fail.
- Final suite: `python3 -m unittest discover -s tests -q` passed 128 tests in both the worktree and installed checkout. `compileall` and `git diff --check` passed.
- Independent review found no code issues. A request to preserve two old TODO entries was assessed against the ten-entry limit in Done.
- A disposable Herdr panel with state in `/tmp` showed newest and oldest first, local dates and unknowns last. Git-ignored local snapshots: `docs/evidence/2026-11-16-creation-order-newest.txt` and `...-oldest.txt`.
- Running the installed command with no arguments from `/tmp` and temporary state opened the global picker with both requested conversations. Local snapshot: `docs/evidence/2026-11-16-global-picker.txt`. The test did not choose a conversation.
- The test panel and picker were closed and disposable state was removed.

## Local installation

Reviewed files were applied to the main checkout without commit, reset, merge or push. A consistent local SQLite backup in `docs/evidence/` preceded the panel update. Only the two open panels in this conversation were reloaded. Their rendered output confirmed the order button and dates. Herdr stayed active. Tests used disposable state and sessions. The final reload used the installed version.

## Limits

Older records without a verifiable date still show an unknown date. Neither IDs nor mutable timestamps were converted into creation dates. Markdown export preserves its format. Importing into another state creates a new local entry. The order preference lasts until the panel closes. Other open panels load the new interface when reopened. The four curation reliability improvements were outside this delivery.
