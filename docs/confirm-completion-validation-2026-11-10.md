# Manual completion confirmation — 2026-11-10

Implemented for the Complete button and key 2.

- Opening the prompt leaves tasks open and shows the selected count with singular or plural wording. Key 1 or Confirm applies completion. Key 2, Cancel or Esc returns to the list on the same page with the selection intact.
- Opening freezes the IDs and text. Confirmation revalidates them inside a transaction. Any change in text, selection or state invalidates the entire request. New selections cannot enter an old confirmation. Shared projects use the correct viewer's selection and propagate completion to other panels.
- The queue modal layout is reused. When the window is too small to display the question, only cancellation is available. Queue behavior is preserved.
- Automatic curation keeps its completion rules and calls.

114 tests passed. Real curses in a PTY covered clicks and keys, cancellation by button/2/Esc, page preservation, single and multiple items, resizing to a small window and explicit confirmation before SQLite mutation. Existing curation tests, `compileall` and `git diff --check` passed.

Independent review found no functional issues. A test using letters on page 2 assumed that letters stayed fixed when buttons appeared. The existing layout reflows and remaps them. The test now clicks stable IDs after redraw, preserving product pagination.

The rasterized preview was checked at 40×24 with three items and 18×12 with one item. The local Git-ignored file is `docs/evidence/confirm-completion/confirmation.png`.
