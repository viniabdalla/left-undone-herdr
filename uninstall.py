#!/usr/bin/env python3
"""Remove the links owned by this checkout while preserving task data."""

import subprocess

from install import PLUGIN_ID, links, owned_link, owns_plugin_link, run


def uninstall():
    if owns_plugin_link():
        subprocess.run(["herdr", "plugin", "unlink", PLUGIN_ID], check=True)
    for path, source in links().items():
        if owned_link(path, source):
            path.unlink()
            print(f"Removed {path}")
    print("Uninstalled. Your tasks and checkout have been preserved.")


if __name__ == "__main__":
    raise SystemExit(run(uninstall))
