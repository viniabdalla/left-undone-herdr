# Stale session identity investigation — 2026-11-10

**The failure reproduced again with /new and /resume. The fix remained pending.** This investigation changed no runtime or integration behavior.

## Comparison with the user's attempt

The user resumed the original conversation and opened Left Undone with the correct identifier. That output establishes the identity at that moment. It does not record the intermediate identifier, so it cannot establish a confirmed A → B switch before the return to A. Resuming A while Herdr still reports A can succeed even when the fault is present.

## Controlled reproduction

The test used Codex 0.167.0, Herdr integration v8, an existing account and one disposable panel in `/tmp`. The model was gpt-6-luna / low, as in the earlier reproduction. It produced only three short synthetic responses without tools. The test neither switched a user conversation nor registered a native binding manually.

1. After A's first response, Herdr reported A (`01a1c6bd-90f3-7fa3-be44-d06527f3e421`).
2. After `/new`, Codex displayed an empty conversation but Herdr still reported A.
3. Without a model message, `/status` in Codex reported B (`01a1c6be-3395-7121-91ed-3ae2c8ca10ba`). Herdr still reported A.
4. After B's first message, Herdr reported B.
5. With `/resume`, selecting A in the synthetic history displayed A in Codex. API queries after approximately 0.3, 2 and 5 seconds still reported B.
6. Without a model message, `/status` confirmed A while Herdr reported B.
7. `candidates()` and `verify(binding_B, ready=True)` accepted B's binding while A was active. **No message was sent through that binding.**
8. After a direct message in resumed session A, Herdr reported A again.
9. Only the disposable panel was closed. The live panel was preserved.

## Findings

The installed hook `~/.codex/herdr-agent-state.sh` publishes the identifier supplied by the SessionStart event. It does not independently observe visible conversation switches. In these tests, the API showed the updated registration only after a model interaction, although `/status` already identified the new conversation. This places the divergence between conversation selection in Codex and native registration in Herdr. Hook stdin was not instrumented, so the test could not distinguish delayed hook execution from delayed event delivery or application.

Left Undone verifies that registration, PID, terminal, account and history. Within the same process the stale values remain internally consistent, so it accepts the binding. Waiting longer and reopening the panel did not resolve the divergence. It is distinct from the short race between verification and sending.

A fix should obtain verifiable evidence of the conversation switch before using the binding, block collection and sending during uncertainty, and update the recipient after confirmation. Focus, title, directory, most recent history and the mere presence of a session file cannot establish which conversation is active.

## Evidence and limits

API output, `/status` screens, the accepted verification and identities are in the local, Git-ignored `docs/evidence/uuid-investigation-2026-11-10/`. Full screens contain account details and should remain unpublished. The usage screen opened briefly during command automation. It was closed and selection of A was explicitly confirmed in the picker and in `/status`. The findings use those confirmed states.

The investigation neither validated a fix nor closed the task. The exact source of the SessionStart delay still needed to be located before choosing between an integration fix and an additional identity source.
