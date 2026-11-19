# Left Undone for Herdr

Left Undone tracks open tasks and promises from a Codex or Claude conversation in a terminal panel beside it. It includes a local Herdr plugin and an agent skill. It requires Linux, Python 3.10 or newer and Herdr 0.9.1 or newer, and uses only the Python standard library.

## Open a conversation

Run `left-undone` from any directory inside Herdr, choose **Left Undone: Open tasks** in Herdr, or ask Codex or Claude to use the `left-undone-herdr` skill.

```sh
left-undone                         # Open the global conversation picker
left-undone open --repo .           # Filter by project
./left-undone list                  # List sessions and identity checks
./left-undone open                  # Open the picker across all repositories
./left-undone open --pane PANE --session UUID
```

The short command always opens the global picker, even for a single verifiable conversation. Each entry shows the title, agent, pane, UUID, account and open item count. In an interactive terminal, press Enter or click **Open** to choose a conversation, or press Esc to return to the shell. Agent tools without an interactive terminal open the picker in a regular Herdr split. Choosing a conversation opens its panel on the right and leaves focus where it was. If the panel already exists, Herdr focuses it, even in another tab.

Use `--repo` to filter by the conversation’s recorded starting directory. The filter resolves symlinks and uses the Git root when run from a subdirectory. Each worktree is a separate project. Outside Git, the directory must match exactly. A single verifiable match opens directly. If only saved conversations match, resume one in the agent first. Each new conversation starts with its own empty list and can import selected project tasks. Promises belong to their original conversation, and sending always requires a verified recipient.

## Use the panel

Click any line of a task or press its letter to toggle selection. The Send and Complete buttons show how many items are selected. You can also click Export, Import, the page controls and Close. Scroll the mouse wheel to change pages. Text wraps to the panel width and long tasks continue on the next page.

| Key | Action |
|---|---|
| a–z | Toggle an item on the current page |
| 0 | Dispatch Sub-Agent for one selected task |
| P | Dispatch one selected task in native Plan Mode (Codex or Claude) |
| H | Prepare a handoff and start a new Codex session in a new tab |
| R | Read dispatch reports for this conversation |
| 1 | Send selected items to the linked conversation and keep them open |
| 2 | Review and confirm completion of selected items |
| 3 | Export this conversation’s open items and published closures to the project |
| 4 | Choose project tasks to import into this conversation |
| 5 | Ask the active collector to collect now |
| V | Check completion and send remaining work to the main session |
| 6 | Switch between newest first and oldest first |
| 7 | Switch between open items and conversation history |
| 8 | Choose the project for Export and Import |
| 9 | Switch between English and Portuguese and remember the choice |
| ← / → | Change page |
| Esc | Close the panel and stop collection |

The panel starts in English. Press **9** or click the language button to switch languages. Left Undone saves the preference locally for the next time you open it.

**Dispatch Sub-Agent.** Select one task and press `0`. The linked agent checks the context, asks for clarification if needed and chooses the worker model and reasoning effort. Its dispatch command opens a new tab in the same Herdr workspace and worktree and returns the tab and pane IDs. The worker starts with a standalone brief and the same CLI and account. New Codex workers start with approvals and sandboxing disabled. New Claude workers start in the `bypassPermissions` mode. Its prompt includes a callback to report changes, verification, and outstanding work. A blocked report keeps the task open. A completion report closes the original task if its text still matches. Press `R` in the original panel to read the reports, including after reopening. Answer worker questions in the tab identified in the report.

**Dispatch Plan.** Select one task and press `P`. The parent prepares a planning brief, and the worker uses its provider’s plan mode. Read the proposal with `R`. The task stays open. Press `0` on that task when you approve execution. The parent receives the proposed plan with the execution request.

**Review a dispatch.** In Agents, click **Review** beneath a task while the linked Main is idle, or select its button with Tab and press Enter. The Main checks the original request and evidence. **Done** or **Not done** and a short reason appear under that task and remain available when you reopen Agents. The review leaves the task list and worker report intact.

**Handoff and new session.** Press `H` with the source Codex idle. The panel verifies the active thread through `/status`. If the displayed list belongs to an older thread in that terminal, the panel asks whether to carry its tasks into the handoff. Click **Confirm handoff** or press Enter on the confirmation screen to approve the displayed list. The panel exports the tasks and asks the source to update TODO.md, evaluate commit and push under local rules, and save the handoff. After confirmation it opens a Codex successor in a new Herdr tab, in the same worktree and account. It runs /init, waits for the successor to confirm restoration, verifies the imported tasks, and binds the existing Left Undone panel to the successor. Close the old Codex pane when Left Undone displays the ready message. A paused transition retains its stage and successor pane for the next H. The monitor uses the verified successor as Main. The feature requires the English Session field in the Codex TUI’s /status output.

**Sending to busy Codex sessions.** Press `1` to queue the request or `2` or Esc to cancel and keep the current selection and page. Queuing requires a Codex CLI with `codex queue`. The request goes to the verified conversation’s native queue under the same account, and the current turn continues. A receipt acknowledges delivery to the queue. The tasks stay open until completed. Confirmation serializes item writes with the collector. If the selection changes or an item is completed, review the items and try again. After a failure the selection is preserved. Check the native queue before retrying an uncertain delivery. Claude has no queue in this version, so wait for the agent to finish.

**Completing items.** Click Complete or press `2` to see the number of selected items. Press `1` or click **Confirm** to mark them complete. Press `2`, click **Cancel**, or press Esc to return to the same page and selection. Changes to the selected items invalidate the confirmation and require another review. Automatic curation can still complete tasks based on evidence.

**Project views.** The panel groups items under **For the agent** and **For you**, with a highlighted title, description and creation date when available. A single notice covers missing dates in older records. The project control (`8`) chooses the project used for exchange. The header identifies the conversation that will receive a send, and the plugin verifies it again before delivery. Private promises stay in their original conversation and project. Item selections belong to the conversation that selected those IDs.

History (`7`) gives a read-only view of closed items. A documented reason for closure appears beside the title. Older entries without a known reason show “Closed”. The default order is newest first. Changing the project, sort order or history view returns to the first page and preserves selections.

Newly collected items use the event date. Imports use the local import date. Older dates are recovered only from corroborating events. Explicit organization preserves IDs, sources, closures and history, recording before and after values and evidence in `panel_organization`. Automatic curation operates independently.

Without an associated project the panel shows the conversation’s own list, with source labels **TASK**, **PROMISE** and **IMPORTED**. Selections survive page changes and panel closure. Sent items stay on the list until the agent, analyzer or user marks them complete.

## Install or uninstall

```sh
git clone https://github.com/viniabdalla/left-undone-herdr.git
cd left-undone-herdr
python3 install.py
```

The installer links this checkout into Herdr, installs skill links at `~/.agents/skills/left-undone-herdr` and `~/.claude/skills/left-undone-herdr`, and creates `~/.local/bin/left-undone`. Include `~/.local/bin` in your PATH. The installer checks whether another installation owns the command, skills or plugin ID.

To remove this checkout’s links, run the following command. It preserves saved tasks, the checkout and other installations.

```sh
python3 uninstall.py
```

## Storage and import

State lives in `~/.local/state/left-undone-herdr/`, or under `XDG_STATE_HOME` when set. Set `LEFT_UNDONE_STATE_DIR` to override that directory. Left Undone stores items in SQLite using write-ahead logging. State is local to each machine.

Each Codex or Claude conversation owns its tasks and history. Reopening the same session restores its list. Two conversations on the same project can work independently and exchange selected tasks. Promises, send selections and the collection cursor belong to the combination of agent, account and session UUID.

The default project is the Git root of the conversation’s starting directory, or that exact directory outside Git. To associate a conversation that started elsewhere, use an explicit project path.

```sh
left-undone open --pane PANE --session UUID --project /path/to/project
```

The association persists and the panel header shows the project. Existing IDs, sources, manual completions and history are preserved. Each session’s native task snapshot applies only to its own tasks. If the transcript cannot identify a project, the list stays private to the session until explicitly associated.

Export merges the conversation’s open items into `.left-undone/tasks.md` in the chosen project. Import opens a chooser with nothing selected. Toggle individual tasks, then confirm to copy them into this conversation. Esc cancels. Importing twice skips existing copies. Completing a copy stays local until Export publishes its closure. An older session exporting later preserves that closure and other conversations’ exported tasks.

The CLI lists available tasks with their IDs. Repeat `--id` to import multiple choices. An explicit `--file` exchanges a standalone Markdown checklist.

```sh
./left-undone export --binding PATH.binding.json
./left-undone import --binding PATH.binding.json
./left-undone import --binding PATH.binding.json --id TASK_ID
./left-undone export --binding PATH.binding.json --file tasks.md
./left-undone import --binding PATH.binding.json --file tasks.md
./left-undone items --binding PATH.binding.json
```

## Collection and models

- **What triggers collection.** The collector checks for changes about every three seconds. A new final reply or a change to the list can trigger analysis. Reviews run one at a time per conversation and use a per-session cache. Idle polling makes no model calls.
- **Collect now.** Press `5` to request an immediate round, including during the retry delay after an error. Repeated requests are combined. A request made during analysis waits for the current round. The status shows progress and results. Automatic collection continues, and previously processed replies are skipped.
- **Review.** Click Review or press uppercase `V` to check the selected tasks. With no selection, Review checks all open tasks in the linked conversation. The small analyzer checks final replies and dispatch summaries, closes evidenced deliveries and sends one message to the main session describing the remaining work. A working Codex session receives it through its native queue. The report shows each decision and delivery status. If Claude is busy, Review waits and rechecks the conversation and tasks before sending. The CLI command `left-undone review --binding PATH.binding.json` performs the same check and handoff and prints the report as JSON.
- **Transcript events.** For Codex, the collector reads `task_complete` events and successful `update_plan` calls. For Claude, it reads `end_turn` replies and `TodoWrite`, `TaskCreate` and `TaskUpdate` calls with successful tool results. Claude sidechains are skipped.
- **Completion checks.** After each final reply, the collector checks each eligible open task independently. For a task with several requirements, the small model identifies the numbered passage that supports each delivered part, using the full prose of the final reply. The preceding final reply can clarify references. Only passages from the current reply count as evidence. The collector closes the task only when every part has evidence. Blocked, partial and ambiguous items stay open. The history view shows the supporting quotations. When there are eligible open tasks, delivery assessment and list curation make separate calls and commit together. On upgrade the collector also checks up to six previously processed final replies from the last 8 MiB of its own transcript.
- **Incremental reads.** The collector consumes complete JSONL lines. Curation commits item changes, history and the processed-event record together before advancing the cursor. Replaying an event is safe.
- **Project curation.** The curator receives the final reply (up to 12,000 characters), recent requests (up to 4,000 characters) and a compact list of the current conversation’s items. It adds tasks, updates descriptions, completes items with evidence and consolidates semantic duplicates. A conflict preserves the affected item while independent changes proceed.
- **Evidence.** Imported checklist items can also be completed automatically when there is evidence. Omission from a reply or snapshot is insufficient. Manual completions are preserved, and older replies cannot overwrite items created or edited later. Example messages and test scripts do not establish a request. Code and example blocks in assistant replies are excluded as evidence, while genuine user requests remain available.
- **Validation.** The curator validates JSON, requires textual evidence, rejects stale results and logs actions. Limits are 50 actions per category and 500 context items. An incomplete or oversized review raises an error and keeps the event for retry. Sessions without an identified project use the original per-session promise auditor.
- **Models.** Codex uses **gpt-6-luna** and Claude uses **Haiku**, both at low effort. Each runs through the verified account’s authenticated CLI. Analysis sessions are ephemeral, with repository files, inherited hooks and MCP integrations excluded. The conversation’s list is passed explicitly as data. The curator records tasks without executing them.
- **Task wording.** For new or edited descriptions, the analyzer pairs a useful technical term with a plain-language action, for example “Codex /resume / UUID — identify the right conversation when resuming.” Where there is no useful term, the action alone is sufficient. Native tasks and older items keep their existing wording.
- **Retries and cost.** Authentication, quota, timeout or JSON failures preserve the list and cursor. The panel displays the error and retries after 30 seconds. Opening a conversation for the first time scans existing history, which can require multiple model calls. Closing the panel stops collection and further calls.

To inspect the list or recent changes from the command line, use the verified binding. The panel reports the number of changes applied and items preserved. The change history includes session, event, before and after values, and the retained item for each duplicate.

```sh
left-undone items --binding PATH.binding.json
left-undone changes --binding PATH.binding.json
```

## Identity and limitations

**After a Codex conversation switch, send a message directly to Codex, wait for its reply, then reopen Left Undone.** A live test on 2026-11-10 with Codex 0.167.0 and Herdr integration v8 reproduced a failure after `/new` or `/resume`. Herdr could announce the old UUID until the first interaction in the chosen conversation. During that interval, even an immediate verification can accept the old binding and send to the wrong conversation. Reopening the panel before that first interaction is insufficient. Full switch and resume validation is still failing. Local evidence is under `docs/evidence/codex-session-lifecycle/`.

The plugin checks Herdr’s announced session, terminal, foreground process, PID and start time, authenticated account and structured transcript. Visual focus, the working directory and inherited environment cannot establish the recipient. The session list explains unavailable panes, including missing or ambiguous identities. Herdr may need the agent’s first reply to identify its UUID.

For Codex tools missing Herdr context or conversations lacking native registration, the skill uses `left-undone recover --marker LU-<32 hex digits>`. The agent posts a fresh marker in commentary. Recovery matches it against recent transcript content, a visible pane, the account and the process, then registers through the native hook and verifies the result. It briefly waits for the marker to appear in the transcript and terminal, recognizes line-wrapped markers and rejects ambiguity immediately. Waiting occurs before registration. Hook and confirmation failures are reported without automatic retries. Errors identify whether the process, transcript or visible marker was missing. This one-time recovery sends no messages, restarts no processes and cannot detect future conversation switches.

The authenticated process identifies the account, including on installations that share transcripts through symlinks. A session or account change blocks sending and collection. To resume the same UUID under a new process, reopen the panel. Left Undone replaces its old panel with the new binding and retains saved state.

Herdr 0.9.1 provides no atomic UUID precondition for `agent prompt`. A small window remains between the final verification and delivery if another action switches the agent at that instant. Sends are never retried automatically after an error.

The adapter was checked against local transcript formats in November 2026. The tested Claude format records `end_turn`. An installation that writes `stop_reason=null` on every final record would require a collector change. This version supports local Linux processes only.

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q left_undone
```

The plugin API was checked against the installed binary’s schema and Herdr’s official documentation. The behavioral reference was adam-mods’ original `left-undone` 0.1.0, inspected with REA and by reading the code. [Verification report](docs/verification.md) · [Herdr plugin documentation](https://herdr.dev/tui/docs/plugins/)

Raw captures in `docs/evidence/` contain session identifiers and local paths and stay on the validation machines. Verification reports and tests are tracked in Git.
