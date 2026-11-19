# Readable panel validation — 2026-11-16

The approved request covered the chosen project, AI/user groups, prominent titles and descriptions, understated dates, history and project/order controls. Implementation used the `left-undone-herdr-picker-dates` worktree and preserved previous changes and the Codex identity worktree. There was no commit, push or Herdr restart.

## Evidence

139 tests passed in the worktree and installation. New tests failed before implementation for view isolation, read-only history, cards, pagination and atomic reorganization. Independent review found that native collector tasks could be moved. The organizer now rejects those tasks as well as private promises. The regression failed before this guard and passed afterward. Only curated shared tasks and imports can be reorganized. Legacy imports keep their selections.

A rehearsal used disposable state containing the twenty reviewed records, without copying the entire database or running a real session. The counts matched expectations. A four-task preview was opened, checked and closed in Herdr with temporary state. `compileall` and `git diff --check` passed.

## Authorized reorganization of live records

The consistent SQLite backup is `docs/evidence/state-before-readable-panel-20261116.sqlite3`. The plan with expected snapshots is `docs/evidence/readable-panel-organization-plan-20261116.json`. Binding and identity were revalidated. Only this conversation's panel was closed. Project locks and a single transaction protected the changes. Any concurrent snapshot change would reject the entire batch. IDs and sources were preserved. Before/after records, evidence and reasons are in `panel_organization` and `item_closures`. Old creation dates were recovered only when the original event was found.

Only this conversation was associated with the implementation worktree, isolating the four open curation items. Left Undone had four open items, Atlas five and TaskBlade two. Other older lists remained accessible in the picker pending review before reclassification. TaskBlade was a planning group without an assumed local clone.

The current panel `w3:p1J`, bound to `w3:p2`, was reopened and checked. It showed four cards, zero items for the user, known dates, buttons 6/7/8 and an active collector. The Git-ignored text/ANSI snapshots are in `docs/evidence/readable-panel-current-20261116.*`.

## Limit

This delivery organized the presentation and the explicitly reviewed records. The four curation engine improvements remained open on the cards. The validation did not establish that semantic model errors had stopped or that Atlas had been activated.
