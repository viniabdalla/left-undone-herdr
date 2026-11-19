# Automatic project curation

Automatically apply clear additions and updates. Skip equivalent tasks and preserve conflicting items without prompting, while continuing with other additions. Curation edits lists without executing tasks.

Reuse the existing authenticated accounts, models, SQLite database and incremental reader. The curator receives the final reply, recent request and compact project items, including promises from other sessions as read-only context. Shared tasks and checklists and the session's own promises can be updated or completed with textual evidence. Native tasks and promises from other sessions are read-only. Skip conflicts individually.

Structured actions add an item with project or session scope, update it, complete it, merge an owned duplicate into an existing item, or declare conflicting IDs. Archive merged duplicates and record their destination. Preserve manual closures. Absence from a snapshot does not complete a task.

A per-project lock serializes collector reviews. UI writes remain responsive. If the list changes during analysis, discard the stale answer and retry the event with fresh state. Apply actions, processed events and change logs transactionally. Advance the cursor only on success.

The heartbeat reads files. Only new replies and actual list changes trigger model calls. Use compact text and omit full logs. Fail explicitly when the item budget is exceeded to avoid silently analyzing an incomplete list. Keep gpt-6-luna/low and Haiku/low. Disable tools and treat instructions embedded in data as data.

The UI keeps its list and mouse controls and summarizes changes in the status line. The `items` command displays the list without opening the picker. A history command shows applied changes. Session/project filters, cross-PC synchronization and automatic /new handling are outside this change.

Validate two sessions, semantic duplicates, distinct tasks, additions alongside conflicts, evidence requirements, protection of foreign targets, incomplete snapshots, concurrent completion/import, event replay and reopening. Check that model failure preserves the cursor and idle polling incurs no model cost. Run a real-model test.
