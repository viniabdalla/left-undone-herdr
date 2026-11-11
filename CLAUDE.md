# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See also `AGENTS.md` (shared rules for all agents) and `README.md` (user-facing behavior, in Portuguese). User-facing strings, README and docs are written in Portuguese; keep that.

## What this is

Left Undone is a Herdr plugin (Linux, Python 3.10+, stdlib only, Herdr 0.9.1+) that watches one Codex or Claude conversation, uses an LLM to extract open tasks/promises from its transcript, and shows them in a curses panel split beside that conversation. Selected items can be sent back to the conversation as "You left this undone: …".

## Commands

```sh
python3 -m unittest discover -s tests -q                     # full suite
python3 -m unittest tests.test_curation.CurationTests.test_x  # single test (run from repo root)
python3 -m compileall -q left_undone
python3 install.py / python3 uninstall.py                    # link/unlink this checkout into Herdr, ~/.local/bin and skill dirs
./left-undone list                                           # verifiable sessions (JSON) + why others are unavailable
./left-undone items|changes --binding <state>/<key>.binding.json
```

Tests must use temporary state (`LEFT_UNDONE_STATE_DIR`) and disposable sessions. Never touch the real state dir `~/.local/state/left-undone-herdr/` in tests. Some tests (`*_pty.py`) drive the curses UI through a pseudo-terminal.

## Architecture

Entry: `left-undone` → `left_undone/app.py:main`. `herdr-plugin.toml` declares the `open` action and two plugin panes (`panel`, `picker`) that re-invoke the same script.

**Process model.** `open` resolves a `Binding`, writes `<key>.binding.json` and asks Herdr to open the `panel` pane beside the target pane. The panel (`ui.py`) spawns a separate `collect` process. The collector polls every ~3 s, or immediately when the panel writes `<key>.collect-request` (`collection_request.py`), and reports progress via `<key>.status.json`. Collector code is loaded once, so after changing collection or curation code, the panel must be closed and reopened (`herdr plugin pane close <pane>` then `open --pane --session`) for it to take effect.

**Identity (`runtime.py`).** A `Binding` is the verified tuple: agent kind, session UUID announced by Herdr, account dir (`CODEX_HOME`/`CLAUDE_CONFIG_DIR` read from the process's `/proc/<pid>/environ`), pane/terminal, foreground PID + starttime, and the resolved transcript path. `Binding.key` = sha256(kind, account, session) keys all per-conversation state. `verify()` re-checks all of it before every send and every collection round. Never infer the recipient from focus, cwd or inherited env. The panel stays bound to the conversation it was opened for, not the neighbouring/focused pane. `recovery.py` handles Codex sessions without a native UUID via a fresh `LU-<hex>` marker.

**Collection (`core.py`).** `Collector.poll` reads the JSONL transcript incrementally from a cursor (offset + inode identity), consuming only complete lines. Adapters turn rows into events: `CodexAdapter` (`task_complete`, `update_plan`) and `ClaudeAdapter` (assistant rows with `stop_reason=end_turn` and text; `TodoWrite`/`TaskCreate`/`TaskUpdate` after a successful tool_result; sidechains ignored). Claude writes one message across several rows (the first may have no text), so dedupe is by event id in the `processed` table. Item changes, the processed mark and the cursor commit in one transaction, so replays are idempotent. Already-processed turns are never re-analyzed.

**Two analysis modes.**
- *No project*: `runtime.RULES` audits each final reply into `{done, add}` promises scoped to the session (`Store`).
- *Project associated* (the normal case): `curation.Curator` replaces the promise auditor entirely. It gets the reply (fenced blocks stripped by `prose_evidence`), the recent user request and a compact snapshot of all project items, and returns `add/update/done/duplicate/conflicts`. `validate()` requires each action's `evidence` to be an exact substring of reply/request. Writes are guarded by a per-project file lock, item version fingerprints (stale results are discarded), `writable`/`canonical` flags (other sessions' items are context only), and per-item timestamps so old replies can't overwrite newer edits. Every applied change is logged in `curation_changes`. User-owned tasks are stored with the text prefix `VOCÊ · ` (`OWNERS` in `curation.py`); updates preserve the prefix.

The LLM call (`Analyzer`) runs the authenticated CLI of the verified account in a temp dir with tools, hooks, MCP, user config and session persistence disabled. Codex uses `codex exec` with `gpt-6-luna` and an output schema; Claude uses `claude -p --model haiku` with `--json-schema`. Both run at low effort by default. Prompt wording rules (technical label, then a plain-language action) live in the `RULES` strings and are shared between both modes.

**Storage (`projects.py`, `repository.py`).** A single SQLite (WAL) `state.db` holds everything. `items.session` is either a binding key (private promises/native tasks) or `project:<sha256(project path)>` (shared project tasks/imports). `project_sessions` maps binding keys to a project, defaulting to the Git toplevel of the transcript's initial cwd (worktrees separate, exact dir without Git). `ProjectStore.scope()` defines visibility: own items plus shared `task`/`import` items of sessions in the same project. Selection for shared items is per viewer (`project_selections`). State is local per machine, with no sync between PCs.

**Sending.** `send` requires `verify(ready=True)`. A busy Codex agent raises `AgentBusy` → `QueueOffer`, and the user can choose the native `codex queue --thread <uuid>` path (`queue_selected` re-validates the selection under `BEGIN IMMEDIATE`). Claude has no queue. Herdr 0.9.1 has no atomic compare-and-send, so never auto-retry a send.

## Known limits

- After `/new` or `/resume`, Codex/Herdr may announce the old UUID until the first reply (README "Identidade e limites"). This is still open in `TODO.md`.
- Keep raw terminal captures and machine-specific evidence in the git-ignored `docs/evidence/`. Validation write-ups go in `docs/*.md`.

## Repo conventions

`TODO.md` is the live to-do read by a widget. Update it in the same commit (Feito with date, Próximo/Bloqueado, `atualizado:`). Keep only the 10 latest items in Feito.
