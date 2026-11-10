# Mouse controls for Left Undone — proposed design

Status: approved by the user's execution request; wrapping reaffirmed by screenshot.

## Intent and reference
Use the checklist with the mouse, like the original Claude left-undone plugin.
REA inspected its five files; direct source inspection found item Button/onPress
handlers and conditional Send/Mark Done buttons. This is static evidence, not a
runtime mouse test of Claude's UI framework. Evidence: docs/evidence/rea-original-mouse-local.json.

## Approach
Extend the existing Python/curses panel with mouse events and clickable regions.
This preserves the Herdr split and current session binding. Replacing the terminal
panel with a web UI would change the requested interaction and installation;
there is no need for that here. Approved for implementation.

## Behavior
- Clicking an item row or checkbox toggles selection, just like its letter key.
  Selection alone neither sends nor completes the item.
- When at least one item is selected, show clickable Send N and Mark N Done
  buttons. Send uses the existing verified-session path and leaves items open;
  Mark Done performs the existing manual completion.
- Keep Export and Import buttons available. Import retains its existing additive behavior.
- Add clickable previous/next page and close controls; the mouse wheel changes pages.
- In the session chooser, clicking a row selects it; an Open button opens that session.
- Long text wraps to available width. Layout and click targets are recalculated on resize;
  clicks outside visible controls do nothing. No hidden/truncated action targets.
- Preserve letters, 1–4, arrows and Esc, session/account checks, collection and saved state.

## Validation
Exercise mouse selection, action hit areas, resize, wheel bounds and unchanged
keyboard paths with tests; verify real mouse event routing through Herdr using a
disposable panel before replacing the current panel. No duplicate send on press/release.
