"""Repository discovery is a UI filter, never a substitute for session verification."""
import json
import os
import sqlite3
import subprocess
from pathlib import Path
from .runtime import Binding


def project_root(directory):
    path=Path(directory).expanduser().resolve()
    if not path.is_dir():return path
    # Inherited Git overrides must not turn every session into the caller's repo.
    env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    result=subprocess.run(['git','-C',str(path),'rev-parse','--show-toplevel'],
                          capture_output=True,text=True,env=env,timeout=5)
    return Path(result.stdout.strip()).resolve() if result.returncode==0 else path


def session_project(binding):
    """Use the initial cwd recorded for this exact transcript/session."""
    try:
        with Path(binding.history).open() as stream:
            # Bound reads, including malformed/very large transcript records.
            remaining=4*1024*1024
            for _ in range(1000):
                line=stream.readline(remaining+1)
                remaining-=len(line)
                if not line or remaining<0:break
                try:row=json.loads(line)
                except ValueError:continue
                if not isinstance(row,dict):continue
                if binding.kind=='codex':
                    if row.get('type')!='session_meta':continue
                    meta=row.get('payload')
                    if not isinstance(meta,dict) or meta.get('id')!=binding.session:continue
                else:
                    if row.get('sessionId')!=binding.session:continue
                    meta=row
                cwd=meta.get('cwd')
                if isinstance(cwd,str) and Path(cwd).is_absolute():return project_root(cwd)
    except (OSError,ValueError,TypeError,subprocess.TimeoutExpired):pass
    return None


def repository_sessions(bindings,repository):
    root=project_root(repository)
    return [b for b in bindings if session_project(b)==root]


def saved_sessions(state,repository):
    result=[]
    for file in Path(state).glob('*.binding.json'):
        try:result.append(Binding(**json.loads(file.read_text())))
        except (OSError,ValueError,TypeError):continue
    return repository_sessions(result,repository)


def pending_counts(state,bindings):
    counts={b.key:0 for b in bindings}
    file=Path(state)/'state.db'
    if not file.exists():return counts
    try:
        conn=sqlite3.connect(file.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        try:
            for key in counts:
                counts[key]=conn.execute("SELECT count(*) FROM items WHERE session=? AND status='open'",(key,)).fetchone()[0]
        finally:conn.close()
    except sqlite3.Error:return {key:None for key in counts}
    return counts
