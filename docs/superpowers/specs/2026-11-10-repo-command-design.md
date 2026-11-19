# Open by repository

On 2026-11-10 the user approved running `left-undone` in a repository to open its only active session or choose among several. Reuse an existing panel. Closed sessions retain data and must resume before opening a linked panel. Each session keeps its own list.

## Approaches

- Filter sessions by repository to preserve identity and individual lists. This was the chosen approach.
- An aggregated repository panel would require identifying and routing each task to its source.

## Implementation

Use the Python standard library with no dependencies. With no arguments, the command is equivalent to `open --repo .`.
Explicit `open` keeps the global picker. `--pane` with `--session` opens an exact binding.
The physical Git root identifies the checkout, keeping worktrees separate. Outside Git use the exact directory.
Read the working directory from history with a matching UUID. A directory cannot authorize delivery.
During implementation the user requested choices directly in the terminal without a popup.
With a TTY, run curses in the calling terminal. Otherwise open the picker in a Herdr split.
Pass an absolute path to the split in a dedicated variable because the split may start in the plugin directory.
The picker shows agent, pane, UUID, account and open-item count.
The installer links ~/.local/bin/left-undone and refuses a conflict with another executable.
Lists, collection, identity validation and mouse/keyboard actions keep their existing behavior.
