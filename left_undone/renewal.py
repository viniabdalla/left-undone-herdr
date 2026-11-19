"""Hand off a Codex or Claude conversation to a verified successor in a new tab."""
import fcntl
import json
import os
import re
import secrets
import shlex
import subprocess
import time
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path
from uuid import UUID

from . import runtime
from .app import atomic_json
from .exchange import export_snapshot, import_selected, open_exchange_ids
from .language import tr
from .projects import project_store
from .repository import project_root, session_project
from .runtime import Binding


class ConfirmationRequired(RuntimeError):
    pass


def final_texts(history, offset):
    """Final assistant replies after offset, for Codex and Claude transcripts."""
    with Path(history).open('rb') as stream:
        stream.seek(offset)
        for line in stream:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            payload = row.get('payload', {})
            if row.get('type') == 'event_msg' and payload.get('type') == 'task_complete':
                yield payload.get('last_agent_message') or ''
            elif row.get('type') == 'assistant' and not row.get('isSidechain'):
                message = row.get('message') or {}
                if message.get('stop_reason') == 'end_turn':
                    yield ''.join(part.get('text','') for part in message.get('content') or []
                                  if isinstance(part, dict) and part.get('type') == 'text')


def receipt(history, offset, marker):
    for reply in final_texts(history, offset):
        for text in reply.splitlines():
            text = text.strip().strip('`*')
            if text.startswith(marker+' ') and text[len(marker):].strip():
                return text[len(marker):].strip()
    return ''


def find_skill(binding, project, word='handoff'):
    """Name of an installed skill about `word` for this agent, if any."""
    home = Path.home()
    if binding.kind == 'claude':
        roots = [Path(project)/'.claude/skills', Path(binding.account)/'skills', home/'.claude/skills']
    else:
        roots = [Path(project)/'.agents/skills', Path(project)/'.codex/skills', Path(binding.account)/'skills',
                 home/'.agents/skills', home/'.codex/skills']
    for root in roots:
        try:
            names = sorted(entry.name for entry in root.iterdir() if (entry/'SKILL.md').is_file())
        except OSError:
            continue
        for name in names:
            if word in name.lower():
                return name
    return None


def skill_hint(binding, project, word='handoff'):
    name = find_skill(binding, project, word)
    return f' Use the `{name}` skill.' if name else ''


def account_env(kind, account):
    """Herdr --env options and `env -u` names that keep the successor on the source account.

    Claude reads ~/.claude.json only while CLAUDE_CONFIG_DIR is unset. Setting it to the
    default ~/.claude switches to ~/.claude/.claude.json, with other folder trust and MCP
    servers, so the default account launches with the variable removed instead."""
    name = 'CODEX_HOME' if kind == 'codex' else 'CLAUDE_CONFIG_DIR'
    default = Path.home()/('.codex' if kind == 'codex' else '.claude')
    if kind == 'claude' and Path(account).resolve() == default.resolve():
        return [], ['-u', name]
    return ['--env', f'{name}={account}'], []


def completed_init(history):
    """Require a completed native /init turn before delivering the handoff."""
    initializing = False
    with Path(history).open('rb') as stream:
        for line in stream:
            if not line.endswith(b'\n'):
                break
            row = json.loads(line)
            p = row.get('payload', {})
            if row.get('type') == 'event_msg':
                if p.get('type') == 'task_started':
                    initializing = False
                if p.get('type') == 'task_complete' and initializing and p.get('last_agent_message'):
                    return True
            if row.get('type') == 'response_item' and p.get('role') == 'user':
                if any(part.get('text', '').startswith('Generate a file named AGENTS.md')
                       for part in p.get('content', []) if isinstance(part, dict)):
                    initializing = True
    return False


def claude_init_done(history):
    """A /init command followed by a finished assistant reply in a Claude transcript."""
    started = False
    with Path(history).open('rb') as stream:
        for line in stream:
            if not line.endswith(b'\n'):
                break
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get('type') == 'user' and '<command-name>/init</command-name>' in json.dumps(row.get('message')):
                started = True
            elif (started and row.get('type') == 'assistant' and not row.get('isSidechain')
                  and (row.get('message') or {}).get('stop_reason') == 'end_turn'):
                return True
    return False


def status_session(screen):
    matches = re.findall(r'^\s*Session:\s+([a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})[ \t]*$', screen, re.M)
    return matches[-1] if len(set(matches)) == 1 else None


def read_screen(binding):
    return subprocess.run([os.environ.get('HERDR_BIN_PATH','herdr'), 'pane','read',
                           binding.pane,'--source','visible'], check=True, capture_output=True,
                          text=True, timeout=5).stdout


def same_terminal(binding, project):
    live = runtime.herdr('agent','get',binding.pane)['agent']
    info = runtime.herdr('pane','process-info','--pane',binding.pane)['process_info']
    proc = runtime.process_info(binding.pid)
    if (not proc or any(proc[k] != getattr(binding,k) for k in ('account','started','pane','kind'))
            or binding.pid not in [p['pid'] for p in info['foreground_processes']]
            or any(live.get(k) != v for k,v in [('pane_id',binding.pane),('terminal_id',binding.terminal),
                                                  ('workspace_id',binding.workspace),('agent',binding.kind)])
            or project_root(live.get('foreground_cwd') or '/') != Path(project)):
        raise RuntimeError('Agent terminal or worktree changed')
    return live


def wait(check, seconds, message):
    deadline = time.monotonic()+seconds
    while True:
        value = check()
        if value:
            return value
        if time.monotonic() >= deadline:
            raise RuntimeError(message)
        time.sleep(.4)


def identified(binding, project, expected=None, previous=None):
    # /status comes from the interactive client itself. Herdr can retain the old
    # session UUID after /new. Never route the handoff using that stale value.
    live = same_terminal(binding, project)
    if live.get('agent_status') not in ('idle','done'):
        raise RuntimeError('Wait for the agent to finish in the linked pane')
    if binding.kind == 'claude':
        # Claude has no /status probe; Herdr's native hook reports the session.
        sid = (live.get('agent_session') or {}).get('value')
        if not sid or (live.get('agent_session') or {}).get('kind') != 'id':
            raise RuntimeError('Herdr has not identified the Claude session yet')
        if expected and sid != expected:
            raise RuntimeError(tr('Panel linked to a different conversation.'))
        if previous and sid == previous:
            return None
        return sid
    probe_at = 0

    def check():
        nonlocal probe_at
        now = time.monotonic()
        if now >= probe_at:
            live = same_terminal(binding, project)
            if live.get('agent_status') not in ('idle','done'):
                return None
            runtime.herdr('agent','prompt',binding.pane,'/status')
            probe_at = now + 4
            time.sleep(.3)
        sid = status_session(read_screen(binding))
        if expected and sid and sid != expected:
            raise RuntimeError(tr('Panel linked to a different conversation.'))
        if sid and sid != previous:
            same_terminal(binding, project)
            return sid
    return wait(check, 24, 'Could not verify the active Codex UUID via /status')


def journal(root, binding):
    return root/(binding.key+'.renewal.json')


def pending_confirmation(root, binding, store, cancel=None):
    path = journal(root,binding)
    if not path.exists():
        return None
    with (root/(binding.key+'.renewal.lock')).open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return None
        if not path.exists():
            return None
        job = json.loads(path.read_text())
        if job.get('stage') != 'confirm':
            return None
        if cancel == job['approval']:
            path.unlink()
            return None
        selection = [[i['id'],i['text']] for i in store.items()]
        if selection != job['selection']:
            job.update(selection=selection,approval=secrets.token_hex(12))
            atomic_json(path,job)
        return job


def confirmed_successor(root, binding, pane, live=None):
    """Follow the verified successor while the monitor stays in its own pane."""
    current = binding
    seen = set()
    live_sid = (pane.get('agent_session') or {}).get('value')
    while current.key not in seen:
        seen.add(current.key)
        path = journal(root,current)
        if not path.exists():
            break
        job = json.loads(path.read_text())
        if job['stage'] != 'complete':
            break
        new = Binding(**job['binding'])
        if job.get('pane') == new.pane and job.get('terminal') == new.terminal and live is not None:
            peer = live.get(new.pane,{})
            if new.workspace != current.workspace or new.account != current.account:
                break
            current = new
            live_sid = ((peer.get('agent_session') or {}).get('value')
                        if peer.get('terminal_id') == new.terminal else None)
            continue
        if current.session == live_sid:
            break
        if (new.terminal, new.pid, new.started, new.account, new.pane) != (
                current.terminal, current.pid, current.started, current.account, current.pane):
            break
        current = new
    return current if current.session == live_sid else binding


def ready_terminal(binding, project):
    live = same_terminal(binding,project)
    return live if live.get('agent_status') in ('idle','done') else None


def active_source(binding, project):
    sid = identified(binding,project)
    source = replace(binding,session=sid,history=str(runtime.resolve_history(binding.kind,binding.account,sid)))
    if session_project(source) != Path(project):
        raise ValueError('Active conversation is in a different worktree')
    return source


def allocated_pane(binding, job):
    """Recover the successor pane even if the coordinator stopped before saving its ID."""
    matches = []
    for pane in runtime.herdr('pane','list','--workspace',binding.workspace)['panes']:
        if pane['pane_id'] == binding.pane:
            continue
        if 'source_tab' in job and pane['tab_id'] == job['source_tab']:
            continue
        if job.get('tab') and pane['tab_id'] != job['tab']:
            continue
        info = runtime.herdr('pane','process-info','--pane',pane['pane_id'])['process_info']
        try:
            env = runtime.process_environment(info['shell_pid'])
        except (KeyError,OSError):
            continue
        if env.get('LEFT_UNDONE_HANDOFF') == job['token']:
            matches.append(pane)
    if len(matches) != 1:
        raise RuntimeError('Could not identify the successor pane. Check the panes before retrying.')
    return matches[0]


def split_binding(binding, job):
    for new in runtime.candidates()[0]:
        if (new.kind,new.account,new.workspace,new.pane,new.terminal) == (
                binding.kind,binding.account,binding.workspace,job['pane'],job['terminal']):
            if new.session in (binding.session,job['source']['session']):
                raise RuntimeError('Expected a fresh agent session')
            if runtime.process_environment(new.pid).get('LEFT_UNDONE_HANDOFF') != job['token']:
                raise RuntimeError('Unexpected process in the handoff pane')
            if session_project(new) != Path(job['project']):
                raise RuntimeError('Successor worktree differs from source')
            if runtime.verify(new).get('agent_status') in ('idle','done'):
                return new


def run(root, binding, confirm_source=None):
    if binding.kind not in ('codex','claude'):
        raise ValueError('Handoff requires a Codex or Claude session')
    agent = binding.kind.capitalize()
    path = journal(root,binding)
    with (root/(binding.key+'.renewal.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        job = json.loads(path.read_text()) if path.exists() else {}
        def save(stage, **values):
            job.update(values, stage=stage)
            atomic_json(path,job)

        if not job or job['stage'] == 'confirm':
            project = session_project(binding)
            if project is None:
                raise ValueError('Cannot verify the conversation worktree')
            source = active_source(binding,project)
            with closing(project_store(root,binding)) as store:
                if Path(store.project) != project:
                    raise ValueError('The linked project differs from the active worktree')
                selection = [[i['id'],i['text']] for i in store.items()]
                if (
                        not confirm_source or confirm_source != job.get('approval')
                        or source.session != job.get('active') or selection != job.get('selection')):
                    save('confirm',active=source.session,selection=selection,approval=secrets.token_hex(12))
                    raise ConfirmationRequired(f'Confirm handoff of {len(selection)} tasks')
                _, ids = export_snapshot(store,project)
            token = secrets.token_hex(12)
            identified(source,project,source.session)
            save('preparing',project=str(project),token=token,ids=ids,source=asdict(source),
                 offset=Path(source.history).stat().st_size)
            # Plug and play: the session follows its own local handoff procedure.
            runtime.herdr('agent','prompt',source.pane,
                f"""Do a handoff following this project's local settings.{skill_hint(source,project)} """
                f"""Open tasks are already exported to .left-undone/tasks.md. """
                f"""When done, end your reply with a line: READY-{token} <handoff reference>""")
        project = job['project']
        if job['stage'] == 'preparing':
            source = Binding(**job.get('source',asdict(binding)))
            ref = wait(lambda: receipt(source.history,job['offset'],'READY-'+job['token']),
                       300,'Handoff not confirmed. Check the conversation, then press H to continue.')
            live = wait(lambda: ready_terminal(source,project),30,'Wait for the agent to finish')
            identified(source,project,source.session)
            save('allocating',ref=ref,source=asdict(source),source_tab=live['tab_id'])
            pane = runtime.herdr('tab','create','--workspace',source.workspace,'--label','Handoff · '+agent,
                                 '--cwd',project,'--env','LEFT_UNDONE_HANDOFF='+job['token'],
                                 *account_env(binding.kind,source.account)[0],
                                 '--no-focus')['root_pane']
            save('launch',pane=pane['pane_id'],terminal=pane['terminal_id'],tab=pane['tab_id'])
        if job['stage'] == 'allocating':
            pane = allocated_pane(binding,job)
            save('launch',pane=pane['pane_id'],terminal=pane['terminal_id'],tab=pane['tab_id'])
        if job['stage'] == 'launch':
            pane = allocated_pane(binding,job)
            if (pane['pane_id'],pane['terminal_id']) != (job['pane'],job['terminal']) or pane.get('agent'):
                raise RuntimeError('Unexpected successor pane')
            save('starting')
            greeting = 'You are the successor in a Left Undone handoff. Reply only READY and wait for /init.'
            if binding.kind == 'codex':
                command = shlex.join(['env','-u','CODEX_THREAD_ID','codex','--no-daemon','-C',project,greeting])
            else:
                command = shlex.join(['env','-u','CLAUDECODE','-u','CLAUDE_CODE_ENTRYPOINT',
                                      *account_env(binding.kind,binding.account)[1],'claude',greeting])
            subprocess.run([os.environ.get('HERDR_BIN_PATH','herdr'),'pane','run',job['pane'],command],
                           check=True,capture_output=True,text=True,timeout=20)
        if job['stage'] == 'starting':
            new = wait(lambda: split_binding(binding,job),180,'Check the successor pane started, then press H.')
            identified(new,project,new.session)
            save('initializing',successor=new.session,binding=asdict(new))
            runtime.send(new,'/init')
        if job['stage'] == 'switching':
            sid = identified(binding,project,previous=binding.session)
            # Reject a user-initiated resume of an older thread on the same pane.
            uid = UUID(sid)
            if uid.version != 7 or (uid.int >> 80)/1000 < job['since']-1:
                raise ValueError('Codex did not open a fresh session')
            save('initializing',successor=sid)
            same_terminal(binding,project)
            runtime.herdr('agent','prompt',binding.pane,'/init')
            time.sleep(2)
        if job['stage'] == 'initializing':
            sid = job['successor']
            target = Binding(**job['binding']) if 'binding' in job else binding
            guide = 'AGENTS.md' if binding.kind == 'codex' else 'CLAUDE.md'
            def init_finished():
                if same_terminal(target,project).get('agent_status') not in ('idle','done'):
                    return False
                try:
                    history = runtime.resolve_history(binding.kind,binding.account,sid)
                except RuntimeError:
                    return False
                done = completed_init(history) if binding.kind == 'codex' else claude_init_done(history)
                return done and (Path(project)/guide).is_file()

            wait(init_finished,300,f'Finish /init in the {agent} pane, then press H')
            identified(target,project,sid)
            history = runtime.resolve_history(binding.kind,binding.account,sid)
            new = replace(target, session=sid, history=str(history))
            if session_project(new) != Path(project):
                raise ValueError('New session worktree differs from source')
            save('restoring',binding=asdict(new),offset=history.stat().st_size)
            prompt = (f"""Restore the handoff {job['ref']} following this project's local settings.{skill_hint(new,project)} """
                      f"""When done, end your reply with a line: RESTORED-{job['token']} OK""")
            live = same_terminal(new,project)
            if binding.kind == 'codex' and (live.get('agent_session') or {}).get('value') != sid:
                prompt += "\nUse the Left Undone skill's marker recovery to register this thread before confirming."
            runtime.herdr('agent','prompt',new.pane,prompt)
        if job['stage'] == 'restoring':
            new = Binding(**job['binding'])
            wait(lambda: receipt(new.history,job['offset'],'RESTORED-'+job['token']) == 'OK',300,
                 'Restoration not confirmed. Check the successor and press H to continue.')
            runtime.verify(new)
            with closing(project_store(root,new,project)) as store:
                import_selected(store,job['ids'],project)
                if set(job['ids']) - open_exchange_ids(store):
                    raise RuntimeError('Some exported tasks are missing. Keep the source pane open.')
            save('complete')
        return Binding(**job['binding'])
