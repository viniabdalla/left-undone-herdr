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


def binding_project(binding,state=None):
    if state is not None and (Path(state)/'state.db').exists():
        conn=None
        try:
            conn=sqlite3.connect((Path(state)/'state.db').resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
            row=conn.execute('SELECT project FROM project_sessions WHERE session=?',(binding.key,)).fetchone()
            if row:return Path(row[0])
        except sqlite3.Error:pass
        finally:
            if conn is not None:conn.close()
    return session_project(binding)


def repository_sessions(bindings,repository,state=None):
    root=project_root(repository)
    return [b for b in bindings if binding_project(b,state)==root]


def saved_sessions(state,repository):
    result=[]
    for file in Path(state).glob('*.binding.json'):
        try:result.append(Binding(**json.loads(file.read_text())))
        except (OSError,ValueError,TypeError):continue
    return repository_sessions(result,repository,state)


def pending_counts(state,bindings):
    from .projects import project_store
    counts={b.key:0 for b in bindings}
    file=Path(state)/'state.db'
    if not file.exists():return counts
    try:
        views=[]
        try:
            for binding in bindings:views.append((binding.key,project_store(state,binding)))
            for key,view in views:counts[key]=len(view.items())
        finally:
            for _,view in views:view.close()
    except sqlite3.Error:return {key:None for key in counts}
    return counts
