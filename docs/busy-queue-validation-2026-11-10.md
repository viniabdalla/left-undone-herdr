# Busy-agent queue confirmation — 2026-11-10

Implemented for local Codex. This version of Claude lacks queue support. The partial UUID protection in the separate worktree was outside this change.

## Behavior

Sending to a verified agent in the `working` state prompts for confirmation. Key `1` or Queue invokes `codex queue --thread UUID --message TEXT` with the verified account. Key `2`, Cancel or Esc returns to the same page with the selection intact. Idle agents receive messages directly. Blocked or unknown states and invalid identities cannot offer queueing. Busy Claude reports that queueing is unavailable.

Sending freezes the selection and text. Confirmation revalidates both. A SQLite transaction serializes validation and queue acceptance against changes to the items. The CLI times out after 20 seconds, without automatic retries or `--resume`. Other list writes may wait during the external call. The Codex receipt must contain the exact binding UUID. Failure or an uncertain receipt preserves the selection. Success clears only the submitted selection and leaves the tasks open.

## Evidence

- The real Codex CLI with a temporary CODEX_HOME, synthetic rollout and no model wrote exactly one item to `queue_1.sqlite`. Its UUID and content matched, including literal shell metacharacters. No real conversation received a test message. This verified native queue persistence only.
- Real curses in a PTY exercised sending, confirmation and cancellation by mouse and keyboard. Esc canceled without closing the panel. Failure kept the selection, tasks stayed visible, cancellation preserved the page, and a tiny panel blocked invisible confirmation.
- Tests covered edits, completion and changed selection before confirmation, and concurrent updates during acceptance. Changed snapshots were never sent.
- Independent review identified a race between validation and submission and loss of pagination. Both regression tests failed before their fixes and passed afterward.
- 107 tests passed. `compileall` and `git diff --check` passed.
- The local, Git-ignored preview shows 40×24 and 18×12 layouts in `docs/evidence/busy-queue/confirmation.png`.

## Limits

The receipt confirms queue acceptance. Later model execution was unverified. The installed CLI must support `codex queue`. Identity validation uses the checks on this branch. The stale UUID during /new or /resume remains separate work. The new path targets the full binding UUID without simulating keys in a busy terminal.
