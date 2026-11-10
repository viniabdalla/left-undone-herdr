"""Recovery must prove a fresh assistant marker, not trust inherited pane IDs."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from left_undone import runtime


class RecoveryTests(unittest.TestCase):
    def test_recovery_command_is_available_without_a_binding(self):
        result = subprocess.run([sys.executable, 'left-undone', 'recover', '--marker', 'bad'],
                                capture_output=True, text=True)
        self.assertNotIn('invalid choice', result.stderr)
        self.assertIn('marca', result.stderr.lower())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.session = '01a1c50d-e2e7-72d2-ab3b-c7cefaaa4e20'
        self.marker = 'LU-' + 'c' * 32
        self.history = self.root / 'sessions' / ('rollout-' + self.session + '.jsonl')
        self.history.parent.mkdir()
        self.write_history()

    def write_history(self, role='assistant', age=0):
        now = datetime.now(timezone.utc) - timedelta(seconds=age)
        self.history.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': self.session}}) + '\n' +
            json.dumps({'timestamp': now.isoformat(), 'type': 'response_item', 'payload': {
                'type': 'message', 'role': role, 'phase': 'commentary',
                'content': [{'type': 'output_text', 'text': self.marker}]}}) + '\n')

    def recover(self, visible=None, duplicate=False, foreground=10, changed_pid=False,
                changed_terminal=False, hook_effect=True, hook_timeout=False,
                wait=0, on_wait=None):
        proc = {'pid': 10, 'started': '100', 'kind': 'codex', 'pane': 'w1:p1', 'account': str(self.root)}
        procs = [proc]
        if duplicate:procs.append({**proc, 'pid': 11, 'pane': 'w1:p2'})
        def env(pid):
            return {'HERDR_ENV': '1', 'HERDR_PANE_ID': 'w1:p1' if pid == 10 else 'w1:p2',
                    'HERDR_SOCKET_PATH': '/fixture.sock'}
        live = {'agent': 'codex', 'pane_id': 'w1:p1', 'terminal_id': 'term1',
                'workspace_id': 'w1', 'agent_status': 'idle'}
        reads = 0
        def api(*args, env=None):
            nonlocal reads
            pane = env['HERDR_PANE_ID']
            if args[:2] == ('agent', 'get'):
                reads += 1
                if changed_terminal and reads > 1:live['terminal_id'] = 'replaced'
                return {'agent': {**live, 'pane_id': pane}}
            return {'process_info': {'foreground_processes': [{'pid': foreground if pane == 'w1:p1' else 11}]}}
        def run(argv, **kwargs):
            if argv[0] == 'herdr':return subprocess.CompletedProcess(argv, 0, self.marker if visible is None else visible, '')
            if hook_timeout:raise subprocess.TimeoutExpired(argv, 20)
            payload = json.loads(kwargs['input'])
            if hook_effect:live['agent_session'] = {'kind': 'id', 'value': payload['session_id']}
            return subprocess.CompletedProcess(argv, 0, '', '')
        hook = self.root / 'herdr-agent-state.sh'
        hook.write_text('# fixture native hook')
        with patch.dict(os.environ, {'CODEX_THREAD_ID': self.session}, clear=True), \
             patch.object(runtime, 'processes', return_value=procs), \
             patch.object(runtime, 'process_environment', side_effect=env), \
             patch.object(runtime, 'process_info', return_value={**proc, 'started': 'changed'} if changed_pid else proc), \
             patch.object(runtime, 'raw_herdr', side_effect=api), \
             patch('left_undone.recovery.time.sleep', side_effect=on_wait or (lambda _: None)), \
             patch('subprocess.run', side_effect=run):
            from left_undone.recovery import recover
            return recover(self.marker,wait_seconds=wait)

    def test_missing_native_uuid_recovers_from_exact_history_and_visible_marker(self):
        binding = self.recover()
        self.assertEqual((binding.session, binding.pane, binding.pid), (self.session, 'w1:p1', 10))
        self.assertEqual(binding.history, str(self.history))

    def test_missing_or_ambiguous_visible_evidence_refuses(self):
        for kwargs in ({'visible': 'another conversation'}, {'duplicate': True}, {'foreground': 999}):
            with self.subTest(kwargs=kwargs), self.assertRaises(RuntimeError):self.recover(**kwargs)

    def test_user_quotes_and_old_markers_do_not_establish_identity(self):
        for role, age in [('user', 0), ('assistant', 3600)]:
            self.write_history(role, age)
            with self.subTest(role=role), self.assertRaises(RuntimeError):self.recover()

    def test_malformed_records_do_not_hide_valid_fresh_commentary(self):
        self.history.write_text(self.history.read_text() + '\nnull\n{"type":"response_item","payload":null}\n')
        self.assertEqual(self.recover().session, self.session)

    def test_process_replacement_and_failed_registration_never_report_success(self):
        for kwargs in ({'changed_pid': True}, {'changed_terminal': True},
                       {'hook_effect': False}, {'hook_timeout': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(RuntimeError):self.recover(**kwargs)

    def test_visible_marker_survives_terminal_line_wrapping(self):
        text='Verificação: LU-\n  '+self.marker[3:19]+'\n    '+self.marker[19:]
        self.assertEqual(self.recover(visible=text).session,self.session)

    def test_recent_commentary_can_reach_transcript_after_first_read(self):
        self.history.write_text(json.dumps({'type':'session_meta','payload':{'id':self.session}})+'\n')
        self.assertEqual(self.recover(wait=.5,on_wait=lambda _:self.write_history()).session,self.session)

    def test_wrong_marker_characters_are_never_repaired(self):
        with self.assertRaises(RuntimeError):self.recover(visible=self.marker[:-1]+'d')

    def test_ambiguous_match_does_not_wait_for_one_candidate_to_disappear(self):
        def must_not_wait(_):raise AssertionError('Ambiguidade não pode ser resolvida esperando')
        with self.assertRaises(RuntimeError):self.recover(duplicate=True,wait=.5,on_wait=must_not_wait)
