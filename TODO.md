---
status: ativo
area: omarchy
prioridade: media
resumo: Herdr panel for tracking tasks and promises by conversation
atualizado: 2026-11-19
---

# TODO — Left Undone for Herdr

## In progress

- [ ] Review the partial protection for Codex after `/new` and `/resume` (commit `95f5e79` on branch `fix/codex-active-thread` in worktree `../left-undone-herdr-codex-title`).
- [ ] Make the promise auditor show user-owned tasks in sessions without a project. This is Dev's first Hermes assignment, following `~/Projects/dev-hermes-setup/docs/orquestracao.md`.

## Next

- [ ] On macOS, identify the Herdr fields that distinguish two disposable conversations and verify their values before and after `/resume`.
- [ ] On macOS, test Open Here and Send in both disposable conversations, including after `/resume`, and record the actual recipients.
- [ ] Adapt the panel, file locking and helper-process shutdown for native Windows.
- [ ] Check whether the previously stuck session was relaunched with the requested permission mode.
- [ ] Verify that each dispatch opens in its own tab and that one monitor below the panel gathers only that conversation's dispatches.
- [ ] Verify the dispatch monitor's per-agent tab, pane, availability, delivery and token usage, plus the footer total and progress bar. The exported reference is 500,000 tokens; the user deferred the cap decision.
- [ ] Idea for later: let the Ideas button tell the curator to keep the selected item as an idea. Agent promises stay in the pending list.
- [ ] Reprocess the two NAS replies from `nas-tropico` with the new curator and archive the old generic task.
- [ ] Require evidence of completion. The curator closed “check SATA errors” when the error count went up.
- [ ] Track the visible Codex conversation and correct a stale UUID after `/new` or `/resume` before the first reply. Repeat the live switch and resume checks that exposed this failure.
- [ ] Exclude Claude's automatic compaction summaries (`isCompactSummary`) from user requests during curation. Check `isMeta` and Codex system messages as well.
- [ ] Run a real dispatch of 2 tasks (Separate and Together) in a disposable conversation and check tabs, reports and completion.
- [ ] Run H live in a disposable Claude conversation and in a disposable Codex one; check /init detection, restore and task import.
- [ ] Apply the plug-and-play prompt idea (short prompt, skill named only if installed) to the other buttons that prompt the agent.
- [ ] Watch real use of the new picker and `open --current` from Codex (app-server tools may not descend from the TUI process; fallback is `CODEX_THREAD_ID`).

## Blocked

- [ ] Close the gap between verification and sending. This requires a Herdr API that can condition delivery on the UUID.

## Done

- [x] 2026-11-19 Dispatch request prompt now gives ready-to-run commands, valid model/effort values per CLI (weakest for execution, strongest for planning), a brief checklist and a Herdr/Left Undone command reference.
- [x] 2026-11-19 Handoff (H) is universal for Codex and Claude: one short plug-and-play prompt that names an installed handoff skill only when found. Unit-tested; live run pending.
- [x] 2026-11-19 Agents monitor shows context used (e.g. 273k / 1M · 27%) with abbreviated totals; [B] sets the Claude context window (automatic by default). Agents button moved to the top row.
- [x] 2026-11-19 Dispatch accepts several tasks (separate tabs or together in one), page buttons and Close moved to the top, Close asks to export, and M opens the agents monitor below. Verified live except a real multi-tab dispatch.
- [x] 2026-11-19 Picker shows only the current Herdr workspace in two-line blocks; from Herdr the panel opens in the picker pane and offers selective import of repo tasks; the skill uses `open --current`. Verified live.
- [x] 2026-11-19 Opening a panel whose old copy sits in another tab now closes it and reopens beside the conversation. Verified live and with a regression test.
- [x] 2026-11-18 Added a dedicated handoff confirmation screen and switched successor launch to a new Herdr tab. Verified the screen and disposable tab creation.
- [x] 2026-11-16 Added project panels with highlighted titles, separate groups for the agent and the user, history, and unobtrusive dates.
- [x] 2026-11-16 Made the short command open the global picker and focus an existing panel when reopened.
- [x] 2026-11-16 Added creation dates and newest-first or oldest-first sorting while preserving selections.
