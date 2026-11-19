# Persistent project lists

The user approved sharing tasks and checklists by project while keeping specific promises in their originating conversation. The panel should follow the visible conversation. The user prioritized the shared list ahead of fixing the `/new` and `/resume` transition.

Each project combines tasks from its Codex and Claude sessions. Completion in one panel applies to all panels. Selection for sending is private to the conversation. Tasks survive panel closure, process restarts and new sessions. New imports belong to the project. Native tasks retain their source session so one session's snapshot cannot close another session's tasks. The current session cannot analyze, display or close another session's promises.

Reuse SQLite and preserve existing IDs and history by adding a session-to-project association and a shared view. Moving all rows to a new key would erase the provenance collectors need. Using Markdown as primary storage would lose transactions and manual closures.

The default project is the Git root of the conversation's verifiable initial working directory, or the exact directory outside Git. Worktrees are separate. `--project` explicitly associates a conversation started elsewhere and takes precedence over inference. Projects without verifiable history keep session state. Lists are local to each machine at this stage.

The UI keeps mouse and keyboard controls and identifies the project. Export writes the visible list. Import creates shared tasks. Choosing a recipient still requires verified identity. Automatic conversation switching and atomic delivery remain separate work on the stale native UUID issue.

Validate two sessions and agents in the same project, a separate isolated project, private promises, independent selection, shared completion, deduplicated imports, persistent closures, independent snapshots, legacy data and reopening.
