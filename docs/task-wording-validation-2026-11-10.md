# Task wording validation — 2026-11-10

Only the promise and curation prompts shared by Codex and Claude changed. The approved format keeps the technical term alongside a short task in plain language.

The test used the real `Analyzer`, Codex gpt-6-luna / low and the account bound to the conversation. Test responses stayed outside project state. The first generic instruction still produced “corrigir UUID obsoleto” (“fix stale UUID”) and “enviar de forma atômica” (“send atomically”). The revision explicitly separated the technical label and the plain-language action.

The existing schemas validated these results after the adjustment. The Portuguese output is quoted verbatim alongside its English meaning:

- Promises: “Codex /resume / UUID: reconhecer a conversa certa ao retomar.” (“Codex /resume / UUID: recognize the right conversation when resuming.”)
- Curation: “API Herdr / envio atômico por UUID: garantir o envio à conversa certa mesmo se ela mudar durante o envio.” (“Herdr API / atomic delivery by UUID: send to the right conversation even if it changes during delivery.”)
- Terms absent from the prompt examples: “Debounce do botão: impedir que cliques repetidos iniciem várias coletas.” (“Button debounce: prevent repeated clicks from starting several collections.”) and “Cache por sessão: evitar analisar o mesmo texto mais de uma vez.” (“Per-session cache: avoid analyzing the same text more than once.”)
- A question and explanation about an API with no requested work produced no curation action.

96 existing tests, `compileall` and `git diff --check` passed. Independent prompt review found no issues. No tests were added solely to check instruction strings. Claude shares the prompts, but this test did not assess its wording live.

The panel for this conversation was reloaded to apply the prompts. The corresponding item was completed by exact ID, preserving the three previous items. Older and native tasks retained their wording.
