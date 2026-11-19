# Project lists and identity recovery

The user approved shared tasks by project and private promises by conversation, giving this priority over automatically tracking the visible recipient.

## Verified

- All 69 tests, compileall and git diff --check passed.
- `recover --marker` identified the live conversation using history, recent commentary, the visible pane and foreground PID, and confirmed the native hook.
- Two live Codex panels in distinct sessions displayed the same six tasks. Selecting one in the second panel left it unselected in the first. This test sent no prompt.
- Existing data survived. A consistent SQLite backup preceded activation.
- Automated tests covered Codex/Claude sessions, a separate project, private promises, shared completion, repeated imports, private selection, reopening, independent snapshots and persistent explicit association.
- Independent review helped reproduce and fix late discovery overwriting an explicit project, a private promise blocking a shared import and a concurrent selection resurfacing after completion.
- A skill-consumption test showed the agent using recover --marker, declining to declare /new automatically safe, and explicitly associating the correct project.

## Limits

Lists are local to each machine. The Herdr integration may still report a stale UUID before the first interaction after /new or /resume. Sharing tasks and recovering an individual registration do not provide automatic detection. Sending still uses the Herdr API without an atomic UUID precondition.

Live text captures from both panes, the backup and structured result are in the Git-ignored `docs/evidence/`. A desktop capture lacked Herdr and was discarded. Visual verification used the rendered panes and PTY tests.
