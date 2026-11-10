"""Explicit recovery using a fresh marker in the current assistant's commentary.

This repairs missing native registration; it does not prove that a pane stays on
the same thread after recovery, nor replace an atomic recipient-aware send API.
"""
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

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
        raise RuntimeError('O painel não corresponde ao processo Codex')
    foreground = runtime.raw_herdr('pane', 'process-info', '--pane', proc['pane'],
                                   env=context)['process_info']['foreground_processes']
    if proc['pid'] not in [item['pid'] for item in foreground]:
        raise RuntimeError('O processo não está em primeiro plano')
    result = subprocess.run([context.get('HERDR_BIN_PATH', 'herdr'), 'pane', 'read',
                             proc['pane'], '--source', 'visible', '--format', 'text'],
                            env=context, capture_output=True, text=True, timeout=20)
    if result.returncode or marker not in result.stdout:
        raise RuntimeError('A marca não está visível no painel')
    return live


def recover(marker):
    try:return _recover(marker)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError('Tempo esgotado ao recuperar o vínculo; confira o registro antes de tentar novamente') from error


def _recover(marker):
    if not re.fullmatch(r'LU-[0-9a-f]{32}', marker or ''):
        raise RuntimeError('Use uma marca nova LU- seguida de 32 dígitos hexadecimais na mensagem de commentary')
    session = os.environ.get('CODEX_THREAD_ID', '')
    if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', session):
        raise RuntimeError('CODEX_THREAD_ID atual ausente; execute pela conversa Codex')
    matches = []
    for proc in runtime.processes():
        if proc['kind'] != 'codex':continue
        try:
            env = runtime.process_environment(proc['pid'])
            if (env.get('HERDR_ENV') != '1' or not env.get('HERDR_SOCKET_PATH') or
                not proc['pane'] or env.get('HERDR_PANE_ID') != proc['pane']):continue
            history = runtime.resolve_history('codex', proc['account'], session)
            if not has_fresh_marker(history, marker):continue
            context = {k: v for k, v in os.environ.items() if not k.startswith('HERDR_')}
            context.update({k: v for k, v in env.items() if k.startswith('HERDR_')})
            live = check_pane(proc, context, marker)
            matches.append((proc, env, context, history, live))
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):continue
    if len(matches) != 1:
        raise RuntimeError('Marca/histórico/processo ausente ou ambíguo; publique uma marca nova visível nesta conversa e tente novamente')
    proc, env, context, history, live = matches[0]
    hook = Path(proc['account']) / 'herdr-agent-state.sh'
    if not hook.is_file():raise RuntimeError('Integração nativa ausente nesta conta; confira herdr integration status')
    # Recheck after discovery so a reused PID or pane cannot authorize a report.
    if runtime.process_info(proc['pid']) != proc:
        raise RuntimeError('Processo mudou durante a recuperação; nenhum registro realizado')
    fresh = check_pane(proc, context, marker)
    if fresh.get('terminal_id') != live.get('terminal_id'):
        raise RuntimeError('Terminal mudou durante a recuperação; nenhum registro realizado')
    hook_env = {**env, 'CODEX_THREAD_ID': session}
    result = subprocess.run(['/bin/sh', str(hook), 'session'], env=hook_env,
        input=json.dumps({'hook_event_name': 'SessionStart', 'session_id': session,
                          'transcript_path': str(history)}),
        capture_output=True, text=True, timeout=20)
    binding = runtime.Binding('codex', session, proc['account'], proc['pane'],
        live['terminal_id'], live['workspace_id'], str(history), proc['pid'], proc['started'])
    if result.returncode:raise RuntimeError('A integração nativa não concluiu a recuperação')
    reported = runtime.raw_herdr('agent', 'get', proc['pane'], env=context)['agent']
    runtime.verify_live(binding, reported)
    for key in list(os.environ):
        if key.startswith('HERDR_'):del os.environ[key]
    os.environ.update({k: v for k, v in context.items() if k.startswith('HERDR_')})
    return binding
