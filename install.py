#!/usr/bin/env python3
"""Link this checkout into Herdr and install its command and agent skills."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGIN_ID = "left-undone"
SKILL = ROOT / "skills" / "left-undone-herdr"


def links():
    home = Path.home()
    return {
        home / ".local/bin/left-undone": SKILL / "scripts/left-undone",
        home / ".agents/skills" / SKILL.name: SKILL,
        home / ".claude/skills" / SKILL.name: SKILL,
    }


def owned_link(path, source):
    return path.is_symlink() and path.resolve() == source.resolve()


def owns_plugin_link():
    result = subprocess.run(
        ["herdr", "plugin", "list", "--plugin", PLUGIN_ID, "--json"],
        check=True, capture_output=True, text=True,
    )
    plugins = json.loads(result.stdout)["result"]["plugins"]
    for plugin in plugins:
        if plugin["plugin_id"] != PLUGIN_ID:
            continue
        local = plugin.get("source", {}).get("kind") == "local"
        if local and Path(plugin["plugin_root"]).resolve() == ROOT:
            return True
        raise RuntimeError(f"O plugin {PLUGIN_ID} pertence a outra instalação.")
    return False


def install():
    destinations = links()
    for path, source in destinations.items():
        if (path.exists() or path.is_symlink()) and not owned_link(path, source):
            raise RuntimeError(f"Conflito: {path}; nada será sobrescrito")
    already_linked = owns_plugin_link()
    created = []
    try:
        for path, source in destinations.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            if not owned_link(path, source):
                path.symlink_to(source, target_is_directory=source.is_dir())
                created.append((path, source))
        if not already_linked:
            subprocess.run(["herdr", "plugin", "link", str(ROOT)], check=True)
    except (OSError, subprocess.CalledProcessError):
        for path, source in reversed(created):
            if owned_link(path, source):
                path.unlink()
        raise
    for path in destinations:
        print(path)


def run(action):
    try:
        action()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Left Undone: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run(install))
