---
status: ativo
area: omarchy
prioridade: media
resumo: Herdr panel for tracking tasks and promises by conversation
atualizado: 2026-11-18
---

# TODO — Left Undone for Herdr

## In progress

- [ ] Review the partial protection for Codex after `/new` and `/resume` (commit `95f5e79` on branch `fix/codex-active-thread` in worktree `../left-undone-herdr-codex-title`).
- [ ] Make the promise auditor show user-owned tasks in sessions without a project. This is Dev's first Hermes assignment, following `~/Projects/dev-hermes-setup/docs/orquestracao.md`.

## Next

- [ ] Place the previous and next page buttons beside the current page number at the top of the panel.
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

## Blocked

- [ ] Close the gap between verification and sending. This requires a Herdr API that can condition delivery on the UUID.

## Done

- [x] 2026-11-18 Added a dedicated handoff confirmation screen and switched successor launch to a new Herdr tab. Verified the screen and disposable tab creation.
- [x] 2026-11-16 Added project panels with highlighted titles, separate groups for the agent and the user, history, and unobtrusive dates.
- [x] 2026-11-16 Made the short command open the global picker and focus an existing panel when reopened.
- [x] 2026-11-16 Added creation dates and newest-first or oldest-first sorting while preserving selections.
- [x] 2026-11-11 Updated tropico-2, omarchy2 and the new Omarchy installation to `70b61a3` with `git pull` and `install.py`. Tests passed on all three.
- [x] 2026-11-11 Added commands and architecture notes to CLAUDE.md covering identity, collection, curation and storage.
- [x] 2026-11-11 Made the curator split lists into individual tasks, omit redundant umbrella tasks and mark user-owned tasks with `VOCÊ`.
- [x] 2026-11-10 Added Herdr pane titles alongside IDs in the conversation picker.
- [x] 2026-11-10 Added confirmation for manual completion. Canceling preserves the selection and page.
- [x] 2026-11-10 Added confirmation before queuing selected items for busy Codex sessions. Canceling preserves the selection and page. Claude queuing was unavailable in this version.
