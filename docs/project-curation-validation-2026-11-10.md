# Automatic curation validation

The approved implementation automatically applies new items and updates while preserving conflicts and avoiding duplicates. The curator edits the list without executing work. Project sharing and private promises retain their existing behavior.

86 local tests passed, along with compileall and diff --check. Coverage included evidence, project changes, concurrent completion/import, ABA, repeated events, model failure without cursor loss, old history, incomplete review, larger checklists, per-session caching without idle polling, hidden foreign promises and protection for other sessions' tasks.

Live Codex gpt-6-luna/low with synthetic data in an isolated SQLite database:

- Merged “Implementar interação com mouse” (“Implement mouse interaction”) into “Adicionar suporte ao mouse” (“Add mouse support”).
- Completed keyboard navigation using the supplied verbatim evidence.
- Added CSV export as a project task visible in the second session.
- Preserved a conflicting SQLite decision and the other session's parser work.
- Received no further model call on a repeat with no new information.

Independent review found four issues, all fixed and covered by tests. Other sessions' private promises could hide visible work, a global cache could block the owner's review, historical completions could affect new tasks, and the five-addition budget was too small for checklists. A skill-consumption test confirmed second-session instructions, automatic completion of imported tasks and delivery limits.

A consistent backup precedes activation in the live panel. Raw evidence and temporary data stay outside Git. The stale recipient after /new and /resume remains a separate issue.

Limits are the last 12,000 characters of the response and 4,000 of requests, 500 context items and 50 actions per category. A response flagged incomplete leaves the event unconsumed. Semantic deduplication depends on model judgment. History records changes and deterministic checks protect ownership, versions, dates, textual evidence and manual closures.
