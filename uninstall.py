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
            print(f"Removido {path}")
    print("Desinstalação concluída. As pendências e o checkout foram preservados.")


if __name__ == "__main__":
    raise SystemExit(run(uninstall))
