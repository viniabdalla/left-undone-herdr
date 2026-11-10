# Project Lists Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation.

**Goal:** Preserve tasks across sessions of the same project, with private promises.
**Architecture:** Add a project/session registry and ProjectStore view over existing
SQLite rows. Keep session collectors and source IDs unchanged.
**Tech Stack:** Python 3.10+, standard library, SQLite WAL, curses, Herdr 0.9.1+.
**Spec:** ../specs/2026-11-10-project-lists-design.md

## Global constraints
- No external Python dependencies; no data deletion or implicit cross-PC sync.
- Project paths filter task scope, never prove a message recipient.
- Native `/new`/`/resume` identity bug remains explicit and unchecked as complete.

## Review focus
- A snapshot from A must not close B's native tasks.
- Legacy selections and manual tombstones must survive reopening.
- One viewer's selection must not cause another viewer to send its tasks.
- Missing history must not merge unrelated sessions.
- Explicit project association must survive future automatic discovery.

## Tasks
1. Add failing `tests/test_projects.py` for sharing, isolation, promises, import
   deduplication, completion, selection, snapshots, legacy persistence and mappings.
   Implement `left_undone/projects.py`: `ProjectStore(path, session, project)`;
   `project_store(root, binding, project=None)` resolves/persists associations.
2. Integrate project views into panel, CLI items/import/export and picker counts;
   leave collectors session-scoped. Add explicit `open --project PATH` association.
   Test CLI associations and shared counts; run existing PTY/mouse tests.
3. Document scope and limitations, review changes, run full unittest suite,
   inspect live panel, commit/push and update available machines. Keep the two
   lifecycle issues visibly pending where not actually fixed.

Verification: `python3 -m unittest discover -s tests -v` and compileall.

## Resultado

Etapas 1–3 implementadas e verificadas: 69 testes, revisão independente e dois
painéis reais com tarefas compartilhadas/seleção independente. Correções da
revisão têm regressões: associação explícita preservada, importação apesar de
promessa privada igual e conclusão concorrente sem ressuscitar seleção.
Recuperação de registro validada ao vivo; mudança automática de conversa segue
pendente conforme prioridade combinada. Coletores continuam por sessão.
