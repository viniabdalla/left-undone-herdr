#!/usr/bin/env python3
"""Install local links, without replacing existing unrelated skills."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parent
source=root/'skills/left-undone-herdr'
command=Path.home()/'.local/bin/left-undone'
executable=source/'scripts/left-undone'
if (command.exists() or command.is_symlink()) and command.resolve()!=executable.resolve():
    raise SystemExit(f'Conflito: {command}; nada será sobrescrito')
for parent in [Path.home()/'.agents/skills',Path.home()/'.claude/skills']:
    target=parent/source.name
    if target.exists() or target.is_symlink():
        if target.resolve()!=source:raise SystemExit(f'Conflito: {target}; nada será sobrescrito')
subprocess.run(['herdr','plugin','link',str(root)],check=True)
for parent in [Path.home()/'.agents/skills',Path.home()/'.claude/skills']:
    parent.mkdir(parents=True,exist_ok=True)
    target=parent/source.name
    if not target.is_symlink():target.symlink_to(source,target_is_directory=True)
    print(target)
command.parent.mkdir(parents=True,exist_ok=True)
if not command.is_symlink():command.symlink_to(executable)
print(command)
