# Left Undone Herdr

Left Undone is a Linux terminal plugin that collects open tasks from Codex and Claude and displays them beside the linked conversation. Use Python 3.10 or newer and Herdr 0.9.1 or newer.

Run the full test suite with `python3 -m unittest discover -s tests -q`. Use temporary state and disposable sessions for integration tests.

`install.py` links this checkout and its skills. `uninstall.py` removes links owned by this checkout. Keep persisted tasks under the configured local state directory across installations and removals.

Validate the account, process and conversation before routing a message. Project scope controls task visibility. The conversation binding controls the recipient. See the README for known session identity limitations.

Keep raw terminal captures and machine-specific evidence under the ignored `docs/evidence/` directory.
