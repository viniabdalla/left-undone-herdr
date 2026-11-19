# Live validation of Codex session switching and resumption

**Session transitions failed. Persistence passed.** The test used Codex CLI/app-server 0.167.0 and Herdr Codex integration v8, with disposable sessions, synthetic tasks and separate SQLite state. It used no manual UUID registration and neither switched nor closed any real conversation.

## Passed

- Session A received its native UUID after its first response.
- Once B received its native UUID, verify(A) rejected the binding and collector A reported an error while retaining its items.
- After /resume A and the first response, the UUID returned to A and the panel was reused.
- The old binding was rejected after the test Codex process exited.
- After `codex resume <A>` in a new process and its first response, the PID changed, the old binding was rejected and the panel was replaced. Items, selection and manual closure persisted.
- With CODEX_THREAD_ID and no HERDR_* variables, context recovery found the right pane in the new process using live Herdr data.

## Failed — stale native UUID

1. Session A had UUID 01a1c597-3399-7851-9d20-f51931456fe1.
2. /new cleared the interface, but agent get still returned A.
3. verify(A, ready=True) accepted A even after enough time for the UI to change.
4. send(A, synthetic message LU-STALE-ROUTE-6e42) succeeded and the message reached new session B, 01a1c598-4d14-7b23-9182-b4812944a500.
5. Herdr reported B only after the interaction with B.
6. /resume A displayed A's history while the API still reported B. After a direct message to Codex, the API reported A again.

The API already exposed a stale identity before verification, beyond the short race between checking and sending. Native identity updates were observably delayed. The event or integration change needed further investigation. This validation made no runtime edits.

## Evidence

`docs/evidence/codex-session-lifecycle/` contains before/after API and terminal captures, the delivery result, actual messages separated by user and assistant role, and the persistence check after the PID change. Role-based checks avoided substring matches in injected memory referencing other sessions.

53 automated tests passed without detecting the stale native UUID. The test panels and collectors were closed. The user's new requests covering missing UUIDs, Collect now, commit/push and SSH distribution were added to the live panel and TODO for later implementation.
