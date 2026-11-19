"""Explicit recovery using a fresh marker in the current assistant's commentary.

This repairs missing native registration; it does not prove that a pane stays on
the same thread after recovery, nor replace an atomic recipient-aware send API.
"""
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from .language import tr

from . import runtime


def has_fresh_marker(history, marker):
    with Path(history).open('rb') as stream:
        offset = max(0, stream.seek(0, 2) - 4 * 1024 * 1024)
        stream.seek(offset)
        if offset:stream.readline()
        lines = stream.read().decode(errors='replace').splitlines()
    now = datetime.now(timezone.utc)
    for line in lines:
        try:
            row = json.loads(line)
            if not isinstance(row, dict):continue
            payload = row.get('payload', {})
            if not isinstance(payload, dict):continue
            if (row.get('type') != 'response_item' or payload.get('type') != 'message' or
                payload.get('role') != 'assistant' or
                payload.get('phase', payload.get('channel')) != 'commentary'):continue
            stamp = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
            age = (now - stamp).total_seconds()
            if not 0 <= age <= 300:continue
            content = payload.get('content', [])
            if not isinstance(content, list):continue
            if any(isinstance(part, dict) and part.get('type') == 'output_text' and
                   isinstance(part.get('text'), str) and marker in part['text']
                   for part in content):return True
        except (ValueError, KeyError, TypeError):continue
    return False


def check_pane(proc, context, marker):
    live = runtime.raw_herdr('agent', 'get', proc['pane'], env=context)['agent']
    if live.get('agent') != 'codex' or live.get('pane_id') != proc['pane']:
        raise RuntimeError(tr('Panel does not match the Codex process'))
    foreground = runtime.raw_herdr('pane', 'process-info', '--pane', proc['pane'],
                                   env=context)['process_info']['foreground_processes']
    if proc['pid'] not in [item['pid'] for item in foreground]:
        raise RuntimeError(tr('The process is not in the foreground'))
    result = subprocess.run([context.get('HERDR_BIN_PATH', 'herdr'), 'pane', 'read',
                             proc['pane'], '--source', 'visible', '--format', 'text'],
                            env=context, capture_output=True, text=True, timeout=20)
    # Herdr's visible snapshot preserves physical line breaks and indentation.
    # Join wrapped lines only; never accept a prefix or repair token characters.
    visible=re.sub(r'\r?\n[ \t]*','',result.stdout)
    if result.returncode or marker not in visible:
        raise RuntimeError(tr('The marker is not visible in the pane'))
    return live


class EvidencePending(RuntimeError):
    """Discovery has no candidate yet; no registration has been attempted."""


def recover(marker,wait_seconds=6):
    deadline=time.monotonic()+max(0,min(wait_seconds,6))
    while True:
        try:return _recover(marker)
        except EvidencePending as error:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise RuntimeError(str(error)) from None
            time.sleep(min(.25,remaining))
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(tr('Time out when recovering the link; check the record before trying again')) from error


def _recover(marker):
    if not re.fullmatch(r'LU-[0-9a-f]{32}', marker or ''):
        raise RuntimeError(tr('Use a fresh LU- marker followed by 32 hexadecimal digits in a commentary message'))
    session = os.environ.get('CODEX_THREAD_ID', '')
    if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', session):
        raise RuntimeError(tr('CODEX_THREAD_ID is missing. Run this from the Codex conversation.'))
    matches = [];checked=0;histories=0;recent=0;reasons=[]
    for proc in runtime.processes():
        if proc['kind'] != 'codex':continue
        try:
            env = runtime.process_environment(proc['pid'])
            if (env.get('HERDR_ENV') != '1' or not env.get('HERDR_SOCKET_PATH') or
                not proc['pane'] or env.get('HERDR_PANE_ID') != proc['pane']):continue
            checked+=1
            history = runtime.resolve_history('codex', proc['account'], session)
            histories+=1
            if not has_fresh_marker(history, marker):continue
            recent+=1
            context = {k: v for k, v in os.environ.items() if not k.startswith('HERDR_')}
            context.update({k: v for k, v in env.items() if k.startswith('HERDR_')})
            live = check_pane(proc, context, marker)
            matches.append((proc, env, context, history, live))
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            reasons.append(f"{proc['pane']}: {str(error)[:120]}")
    if len(matches)>1:
        raise RuntimeError(tr('Marker visible in multiple panes. Nothing registered. Post a fresh marker in this conversation.'))
    if not matches:
        stage=(tr('no Codex process with Herdr context') if not checked else
               tr('current UUID history not found') if not histories else
               tr('Marker not found in recent commentary') if not recent else
               tr('Marker and process could not be verified in the visible pane'))
        details='; '.join(dict.fromkeys(reasons)) if recent else ''
        raise EvidencePending(tr('Recovery: ')+stage+tr('. Post a fresh marker visible in this conversation.')+
                              (' '+details if details else ''))
    proc, env, context, history, live = matches[0]
    hook = Path(proc['account']) / 'herdr-agent-state.sh'
    if not hook.is_file():raise RuntimeError(tr('Native integration missing in this account; check out herdr integration status'))
    # Recheck after discovery so a reused PID or pane cannot authorize a report.
    if runtime.process_info(proc['pid']) != proc:
        raise RuntimeError(tr('Process changed during recovery. Nothing registered.'))
    fresh = check_pane(proc, context, marker)
    if fresh.get('terminal_id') != live.get('terminal_id'):
        raise RuntimeError(tr('Terminal changed during recovery. Nothing registered.'))
    hook_env = {**env, 'CODEX_THREAD_ID': session}
    result = subprocess.run(['/bin/sh', str(hook), 'session'], env=hook_env,
        input=json.dumps({'hook_event_name': 'SessionStart', 'session_id': session,
                          'transcript_path': str(history)}),
        capture_output=True, text=True, timeout=20)
    binding = runtime.Binding('codex', session, proc['account'], proc['pane'],
        live['terminal_id'], live['workspace_id'], str(history), proc['pid'], proc['started'])
    if result.returncode:raise RuntimeError(tr('Native integration did not complete recovery'))
    reported = runtime.raw_herdr('agent', 'get', proc['pane'], env=context)['agent']
    runtime.verify_live(binding, reported)
    for key in list(os.environ):
        if key.startswith('HERDR_'):del os.environ[key]
    os.environ.update({k: v for k, v in context.items() if k.startswith('HERDR_')})
    return binding
