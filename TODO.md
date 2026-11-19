---
status: ativo
area: omarchy
prioridade: media
resumo: Herdr panel for tracking tasks and promises by conversation
atualizado: 2026-11-18
---

# TODO — Left Undone for Herdr

## In progress

- [ ] Review the partial protection for Codex after `/new` and `/resume` (uncommitted on branch `fix/codex-active-thread` in worktree `../left-undone-herdr-codex-title`).
- [ ] Make the promise auditor show user-owned tasks in sessions without a project. This is Dev's first Hermes assignment, following `~/Projects/dev-hermes-setup/docs/orquestracao.md`.

## Next

- [ ] Reprocess the two NAS replies from `nas-tropico` with the new curator and archive the old generic task.
- [ ] Require evidence of completion. The curator closed “check SATA errors” when the error count went up.
- [ ] Track the visible Codex conversation and correct a stale UUID after `/new` or `/resume` before the first reply. Repeat the live switch and resume checks that exposed this failure.
- [ ] Exclude Claude's automatic compaction summaries (`isCompactSummary`) from user requests during curation. Check `isMeta` and Codex system messages as well.

## Blocked

- [ ] Close the gap between verification and sending. This requires a Herdr API that can condition delivery on the UUID.

## Done

- [x] 2026-11-16 Added project panels with highlighted titles, separate groups for the agent and the user, history, and unobtrusive dates.
- [x] 2026-11-16 Made the short command open the global picker and focus an existing panel when reopened.
- [x] 2026-11-16 Added creation dates and newest-first or oldest-first sorting while preserving selections.
- [x] 2026-11-11 Updated tropico-2, omarchy2 and the new Omarchy installation to `70b61a3` with `git pull` and `install.py`. Tests passed on all three.
- [x] 2026-11-11 Added commands and architecture notes to CLAUDE.md covering identity, collection, curation and storage.
- [x] 2026-11-11 Made the curator split lists into individual tasks, omit redundant umbrella tasks and mark user-owned tasks with `VOCÊ`.
- [x] 2026-11-10 Added Herdr pane titles alongside IDs in the conversation picker.
- [x] 2026-11-10 Added confirmation for manual completion. Canceling preserves the selection and page.
- [x] 2026-11-10 Added confirmation before queuing selected items for busy Codex sessions. Canceling preserves the selection and page. Claude queuing was unavailable in this version.
- [x] 2026-11-10 Updated model instructions to pair technical terms with plain-language tasks and omit lengthy explanations.
