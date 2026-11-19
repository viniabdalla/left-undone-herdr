---
name: left-undone-herdr
description: Open or find a Left Undone panel in Herdr to track tasks and promises from a Codex or Claude conversation, or import and export open items.
---

# Left Undone for Herdr

Use this skill when someone asks for the open tasks panel in Herdr. It requires Linux, Python 3.10 or newer, Herdr 0.9.1 or newer, and a linked local `left-undone` plugin.

Resolve `scripts/left-undone` relative to this SKILL.md. The wrapper uses the plugin implementation and shares its collector.

## Choose a conversation

The installer also places `left-undone` in `~/.local/bin`. With no arguments, it always opens the global picker of verifiable Herdr conversations, regardless of the current directory or how many sessions are available. The picker shows titles, IDs, accounts and open item counts. In a terminal it stays open until the user makes a choice or presses Esc. Agent tools without a TTY open it in a regular Herdr split.

Use `left-undone open --repo <directory>` to explicitly filter by project. A single verifiable match opens directly. `left-undone open` uses the global picker. The filter uses the session history’s initial directory, resolved to the Git root, or the exact directory outside Git. Worktrees remain separate. Saved conversations without a live session must be resumed in the agent.

The directory determines the project exchange file and filters candidates. Opening or sending requires the UUID, account and process. When the user requests the current conversation, use its verified binding even if the tool runs in a different project.

1. Run `python3 scripts/left-undone list`. The result lists verifiable panes, session UUIDs, accounts and transcripts, and explains unavailable sessions.
2. Once the requested conversation is unambiguous, run `scripts/left-undone open --pane <pane> --session <UUID>`. Otherwise, run `scripts/left-undone open` and let the user choose. Visual focus, the working directory and an inherited `HERDR_PANE_ID` are insufficient to identify the recipient. Do not substitute another conversation.
3. A new panel opens in a right-hand split and preserves the existing focus. Reopening an existing panel focuses it even in another tab. Its collector reads only the bound conversation’s transcript.

## Project lists

Each session owns its tasks, promises, selections and history. A new conversation starts empty. Reopening the same session restores its local list.

By default the project is the Git root of the verified starting directory, or that exact directory outside Git. If the conversation started elsewhere and the user identifies its project, link it explicitly. The association persists.

```sh
python3 scripts/left-undone open --pane PANE --session UUID --project /path/to/project
```

Never use `--project` to guess a recipient. Change another conversation’s association only with evidence that it belongs to the project. Project sharing does not resolve a stale native UUID after `/new` or `/resume`.

## Panel controls

Click any line of a task or press its letter to toggle selection. Send and Complete show the selection count. The mouse wheel, arrow keys and page buttons change pages. Long text wraps to the panel width and tall items continue onto the next page. Export, Import and Close are clickable. In the conversation picker, click a row and then Open.

- **1** sends the selected items to the linked conversation. They remain open.
- **2** asks for confirmation before marking items complete. Press `1` or click Confirm to complete the displayed selection. Press `2`, click Cancel, or press Esc to return to the same selection and page. Editing, completing or deselecting an item during confirmation invalidates the request. Automatic curation operates independently.
- **3** merges open items and published closures into the chosen project’s `.left-undone/tasks.md`. **4** opens a chooser. Select individual tasks and confirm to import them, or press Esc to cancel.
- **5** requests an immediate round from the active collector, including during the retry delay after an error. Repeated requests are combined and wait for any analysis already in progress. The collector still verifies the session and skips previously processed events. Automatic collection continues.
- **6** switches between newest first and oldest first. **7** toggles read-only session history. **8** chooses the project for Export and Import. These changes return to the first page and preserve selections. The header always identifies the verified recipient.
- **9** switches the interface between English and Portuguese and saves the choice locally.
- **Esc** closes the panel. State and selections are saved.

Project panels group highlighted titles and descriptions under **For the agent** and **For you**. Other projects’ and conversations’ private promises stay hidden. History shows documented closure reasons or “Closed” for ambiguous records. Known dates appear beside items, with a single notice for missing historical dates. Never invent a date or a reason for closure.

If Codex is busy, press `1` or click Queue to use `codex queue` for the verified account and UUID. Press `2`, click Cancel, or press Esc to return to the same selection and page. Confirmation revalidates the items and recipient. A queued request leaves the current turn running and the selected items open. Failures preserve selections and trigger no automatic resend. Check the native queue before retrying an uncertain delivery. Claude queuing is unavailable in this version. The panel explains the limitation and keeps the selection.

## Import, export and curation

Use `export --file <file>` or `import --file <file>` with `--binding <path.binding.json>` to choose a file. Find the binding in `~/.local/state/left-undone-herdr/` or the configured state directory. Match the session UUID inside the JSON. File modification time cannot identify the session. Use `items --binding` to inspect the list. Import adds open items, skips checked entries and preserves manual completions.

Analyzers use the verified account’s authenticated CLI. Claude uses Haiku and Codex uses gpt-6-luna at low effort. With a project, the analyzer receives the final reply, recent requests and a compact list of this session’s items. Keep the configured model and input bounds. Authentication, limit and JSON failures appear in the panel and preserve the list.

The curator adds and updates items, completes tasks with evidence and consolidates duplicates. Conflicts preserve the affected item without prompting, while independent changes continue. Omission alone cannot establish completion. Idle polling checks for changes without invoking a model. Inspect recent changes or items without opening another panel.

```sh
python3 scripts/left-undone changes --binding PATH.binding.json
python3 scripts/left-undone items --binding PATH.binding.json
```

## Session identity and recovery

If Herdr cannot identify the session, explain why. If needed, check the native integrations with `herdr integration` and ask the user to identify the conversation. Never invent a UUID, run `report-agent-session` with an ID inferred from the working directory, or restart the server to recover identity.

Herdr 0.9.1 validates delivery through `agent prompt` without an atomic UUID precondition. Left Undone verifies the recipient immediately before sending. Do not retry automatically after a timeout or ambiguous error.

A live test on 2026-11-10 with Codex 0.167.0 and integration v8 confirmed that Herdr can announce the old UUID after `/new` or `/resume` until the chosen conversation’s first interaction. When switching conversations, send a message directly to Codex and wait for its reply before opening or sending through Left Undone. Reopening early or running curation does not correct the recipient. Full switch and resume validation remains open.

### Codex app-server without Herdr context

An absent `HERDR_ENV` can mean the app-server ran a tool without the terminal environment. The wrapper recovers context when `CODEX_THREAD_ID` matches exactly one native Herdr session and a verifiable interactive Codex process. Run `list` before asking the user to reopen the conversation.

For an unregistered session, check `herdr integration status`. Installing the Codex integration with `herdr integration install codex` is part of an authorized plugin installation. Keep Herdr and Codex running.

An already-open conversation may need initial registration.

1. Generate a fresh marker with `python3 -c 'import uuid; print("LU-"+uuid.uuid4().hex)'`.
2. Post the marker in a commentary message. Immediately run `python3 scripts/left-undone recover --marker <marker>`, substituting the full generated value (`LU-` and 32 hexadecimal digits). Never reuse an example.
3. Recovery requires a real `CODEX_THREAD_ID`, a commentary marker in the account’s transcript from the past five minutes, the same marker **visible** in exactly one pane, and matching foreground PID and environment. It invokes the native hook and checks the registration without sending prompts.
4. Open the returned pane and UUID and check `list` again. If the marker has scrolled offscreen, post a fresh marker and retry. On ambiguity or a mismatch, stop before registering manually or sending anything.

Recovery applies to the current session only. Titles, directories and focus cannot establish bindings, and later `/new` or `/resume` switches still require the checks above. Leave the generic skill embedded in the Herdr binary intact.

## When the user asks for an existing checklist

Open the panel and import a Markdown file with a `- [ ]` entry for each item still open. Exclude installation if it has already finished. Match the binding’s UUID to the requested conversation and verify the result with `items --binding`.

Project imports can be curated automatically or completed manually with key `2`. Confirm actions in the history before reporting that the model recognized completion. Check the rendered panel with `herdr pane read` and a capture before reporting readiness.

If the plugin is missing on this machine and installation is authorized, run `python3 install.py` from the local project. Keep the skill, wrapper and implementation together.


## Dispatch a sub-agent

Select one task and click **Dispatch Sub-Agent** (key 0). The parent agent reviews its own conversation for relevant context. If a decision is missing, use the supplied question callback and ask the user before opening a tab. Otherwise choose both the model and effort, then use the supplied dispatch command with a self-contained brief on stdin. It returns the tab, pane and worktree. New Codex workers start with approvals and sandboxing disabled. New Claude workers start in the `bypassPermissions` mode. The worker uses the report command in its initial prompt to send its summary, verification and outstanding work back to the panel. Report blocked when user input is needed. Press R in the original panel to read dispatch reports.

Use **Review** (uppercase V) to check the selected tasks, or all open tasks if none are selected. A small model checks for delivery, closes completed tasks and sends the remaining work to the linked main session. The report shows the result of each handoff. **Collect** (5) requests the usual incremental collection.

## Renew a Codex session or dispatch a plan

Press **H** in a Codex project panel to export its open tasks and request a local handoff. Update TODO.md using the worktree’s instructions and preserve its consumer’s format. Evaluate commit and push using the repository policy and the user’s authorization. Return the saved handoff reference on the requested receipt line. The panel opens a successor in a split, runs /init, verifies the successor, restores the handoff and imports the exported tasks in the same Left Undone panel. Close the old Codex pane only when the panel confirms the new connection. When the active thread and displayed list differ, H asks for explicit confirmation before carrying the displayed tasks. If a step needs attention, answer in the linked conversation and use H to continue the pending transition.

For a planning dispatch, select one item and press **P**. Prepare a planning-only brief for the native Codex or Claude planner. Read the proposal with **R**. Selecting **0** on that item starts a separate execution dispatch and includes the proposed plan for review by the parent.
