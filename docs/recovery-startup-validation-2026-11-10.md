# Opening failure in the second session

The user's manual test reported a missing UUID/process and failed recovery. The screenshot shows the commentary token wrapped across two lines. Later inspection confirmed the real UUID in history, a recent assistant commentary marker, the foreground Codex process and the corresponding pane. The same marker, still valid, restored registration and opened the panel for the user's session. No additional session was created.

The original error did not identify the failing step. The first attempt may have preceded history persistence or viewport rendering. The later attempt establishes only that the evidence became available.

Discovery with no candidates now tolerates a short publication delay and repeats the full check. Complete markers may span physical line breaks. The check neither corrects characters nor accepts prefixes. Two candidates cause immediate rejection. Registration, the hook and final confirmation run once. Errors distinguish process, history, recent commentary and viewport failures.

94 tests passed, including history published after the first read, a wrapped token, an incorrect token, ambiguity and registration failures. A live check compared shared IDs and text between the original and new sessions.

The same check found a spurious task created from the assistant's testing guide, the example “Teste LU-1350” (“Test LU-1350”). Curation history traced it to the answer to “como eu testo?” (“how do I test it?”) rather than a request to build a screen. The entry was backed up and archived with a `dismiss-example` record.

Fenced blocks in assistant responses are now excluded from task evidence. Real user requests, including checklists, remain available. The prompt distinguishes examples, suggested messages and test instructions from requested work. Regression tests cover both the example and a real request. A live model returned zero actions for the original guide and preserved addition, completion, deduplication and conflicts in the real-work scenario. One intermediate run missed the duplicate. The instruction to reconcile existing items was clarified before the passing run. Semantic judgment remains model-dependent.
