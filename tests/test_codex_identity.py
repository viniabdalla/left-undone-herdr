import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from left_undone import codex_identity as ci
from left_undone.runtime import Binding, verify as VERIFY

# Full UUIDs shaped like Codex 0.167 UUIDv7 ids; titles show 8-4-4-4-5 + "...".
A = '01a1c6d9-7870-78a2-a755-e75580bcd10b'
B = '01a1c6da-1640-7cf0-9a94-b1071e5efa9b'
SAME_PREFIX = '01a1c6d9-7870-78a2-a755-e7558ffffff0'  # same visible prefix as A
OVERRIDE = ['codex', '-m', 'gpt-6-luna', '-c', 'tui.terminal_title=["thread-id"]']


def title(session):
    return session[:29] + '...'


class Fixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name);self.account = self.root / 'codex';self.account.mkdir()
        env = patch.dict(os.environ, {'LEFT_UNDONE_STATE_DIR': str(self.root / 'state')})
        env.start();self.addCleanup(env.stop)
        self.argv = list(OVERRIDE);self.start = time.time() + 60
        for target, value in [('command_line', lambda pid: self.argv), ('started_at', lambda pid: self.start),
                              ('MANAGED', str(self.root / 'managed.toml'))]:
            p = patch.object(ci, target, value);p.start();self.addCleanup(p.stop)
        self.proc = {'pid': 10, 'started': '123', 'account': str(self.account)}

    def live(self, shown, native):
        return {'pane_id': 'w1:p1', 'terminal_id': 'term1', 'terminal_title': shown,
                'agent_session': {'kind': 'id', 'value': native} if native else None}

    def session(self, shown, native, proc=None):
        return ci.confirmed_session(self.live(shown, native), proc or self.proc, lambda pid, started: True)


class TitleProofTests(Fixture):
    def test_name_or_label_with_old_prefix_is_not_native_thread_id(self):
        # Exactly the old UUID prefix in the title, but produced by thread-title.
        for items in ('["thread-title"]', '["project-name"]', '["thread-title","project-name"]'):
            self.argv = ['codex', '-c', 'tui.terminal_title=' + items]
            with self.assertRaises(ci.Unverifiable):self.session(title(A), A)

    def test_current_config_file_does_not_prove_what_the_running_tui_loaded(self):
        # TUI started without override; config.toml now says thread-id.
        self.argv = ['codex', '--ignore-user-config']
        (self.account / 'config.toml').write_text('[tui]\nterminal_title = ["thread-id"]\n')
        with self.assertRaises(ci.Unverifiable):self.session(title(A), A)

    def test_title_with_several_uuids_is_refused(self):
        self.argv = ['codex', '-c', 'tui.terminal_title=["thread-id","thread-title"]']
        with self.assertRaises(ci.Unverifiable):self.session(title(A) + ' | ' + title(B), A)
        self.argv = list(OVERRIDE)
        for shown in (title(A) + ' | ' + title(B), title(A) + ' ' + title(A), 'x ' + title(A), title(A) + ' x'):
            with self.assertRaises(ci.Unverifiable):self.session(shown, A)

    def test_short_prefix_is_not_enough(self):
        for shown in (A[:8] + '...', A[:23] + '...', A[:28] + '...'):
            with self.assertRaises(ci.Unverifiable):self.session(shown, A)
        self.assertEqual(self.session(title(A), A), A)
        self.assertEqual(self.session(A, A), A)

    def test_any_config_write_after_start_blocks_even_if_field_removed(self):
        # Review sequence: /title switches to thread-title (saved after start),
        # then config is rewritten without terminal_title while the runtime
        # title stays editable. The current file must not re-enable the proof.
        config = self.account / 'config.toml'
        self.assertEqual(self.session(title(A), A), A)
        self.start = time.time() - 30
        for content in ('[tui]\nterminal_title = ["thread-title"]\n', 'model = "unrelated change"\n',
                        '[tui]\nterminal_title = ["thread-id"]\n', '[profiles.x.tui]\nterminal_title = ["thread-title"]\n'):
            config.write_text(content)
            with self.assertRaises(ci.Unverifiable):self.session(title(A), A)
        config.unlink()
        self.assertEqual(self.session(title(A), A), A)
        config.write_text('model = "written before start"\n')
        self.start = config.stat().st_mtime + 30
        self.assertEqual(self.session(title(A), A), A)

    def test_managed_config_or_ambiguous_overrides_block(self):
        (self.root / 'managed.toml').write_text('[tui]\nterminal_title = ["thread-id"]\n')
        with self.assertRaises(ci.Unverifiable):self.session(title(A), A)
        (self.root / 'managed.toml').unlink()
        for extra in (['-c', 'tui={terminal_title=["thread-title"]}'], ['-c', 'tui."terminal_title"=["x"]'],
                      ['--config=tui.terminal_title.0="thread-title"']):
            self.argv = OVERRIDE + extra
            with self.assertRaises(ci.Unverifiable):self.session(title(A), A)
        self.argv = ['codex', '--config=tui.terminal_title=["thread-title"]', '-c', 'tui.terminal_title=["thread-id"]']
        self.assertEqual(self.session(title(A), A), A)
        self.argv = OVERRIDE + ['-c', 'tui.terminal_title=["thread-title"]']
        with self.assertRaises(ci.Unverifiable):self.session(title(A), A)


class Python310FallbackTests(Fixture):
    """Python 3.10 has no tomllib; parsing must stay conservative."""
    def setUp(self):
        super().setUp()
        p = patch.object(ci, 'tomllib', None);p.start();self.addCleanup(p.stop)

    def test_json_compatible_override_still_proves_and_others_block(self):
        self.assertEqual(self.session(title(A), A), A)
        self.argv = ['codex', '-c', "tui.terminal_title=['thread-id']"]
        with self.assertRaises(ci.Unverifiable):self.session(title(A), A)
        self.argv = ['codex', '-c', 'tui.terminal_title=["thread-title"]']
        with self.assertRaises(ci.Unverifiable):self.session(title(A), A)

    def test_managed_config_mentioning_title_blocks_without_parser(self):
        (self.root / 'managed.toml').write_text('[tui]\nterminal_title = ["thread-id"]\n')
        with self.assertRaises(ci.Unverifiable):self.session(title(A), A)
        (self.root / 'managed.toml').write_text('model = "x"\n')
        self.assertEqual(self.session(title(A), A), A)


class SwitchTests(Fixture):
    def test_new_before_first_turn_blocks_old_binding(self):
        self.assertEqual(self.session(title(A), A), A)
        # /new: Codex shows B at once, Herdr still reports A.
        with self.assertRaises(ci.Unverifiable):self.session(title(B), A)

    def test_resume_previously_confirmed_conversation_without_new_turn(self):
        self.assertEqual(self.session(title(A), A), A)
        self.assertEqual(self.session(title(B), B), B)
        # /resume A: Herdr still says B; A was confirmed in this same process.
        self.assertEqual(self.session(title(A), B), A)
        self.assertEqual(self.session(title(B), A), B)

    def test_confirmation_is_scoped_to_process_pane_and_terminal(self):
        self.assertEqual(self.session(title(A), A), A)
        self.assertEqual(self.session(title(B), B), B)
        for proc, live in [({**self.proc, 'pid': 11}, {}), ({**self.proc, 'started': '999'}, {}),
                           (self.proc, {'pane_id': 'w1:p2'}), (self.proc, {'terminal_id': 'term2'})]:
            data = {**self.live(title(A), B), **live}
            with self.assertRaises(ci.Unverifiable):ci.confirmed_session(data, proc, lambda pid, started: True)

    def test_dead_process_confirmations_are_pruned(self):
        self.assertEqual(self.session(title(A), A), A)
        with self.assertRaises(ci.Unverifiable):
            ci.confirmed_session(self.live(title(A), B), self.proc, lambda pid, started: False)

    def test_two_confirmed_sessions_with_the_same_visible_prefix_are_ambiguous(self):
        self.assertEqual(self.session(title(A), A), A)
        # Native branch: the second UUID is recorded but already ambiguous.
        with self.assertRaises(ci.Unverifiable):self.session(title(SAME_PREFIX), SAME_PREFIX)
        # From then on, both branches: native matching the prefix, or stale/missing.
        for native in (A, SAME_PREFIX, B, None):
            with self.assertRaises(ci.Unverifiable):self.session(title(A), native)

    def test_prefix_never_resolves_an_unconfirmed_history(self):
        # A history file for A exists, but A was never confirmed in this process.
        (self.account / 'sessions').mkdir()
        (self.account / 'sessions' / f'rollout-x-{A}.jsonl').write_text(json.dumps({'type': 'session_meta', 'payload': {'id': A}}) + '\n')
        self.assertEqual(self.session(title(B), B), B)
        with self.assertRaises(ci.Unverifiable):self.session(title(A), B)
        with self.assertRaises(ci.Unverifiable):self.session(title(A), None)

    def test_missing_native_report_blocks(self):
        with self.assertRaises(ci.Unverifiable):self.session(title(A), None)


class VerifyTests(Fixture):
    def verify(self, binding, shown, native, ready=True):
        from left_undone import runtime
        original = VERIFY  # unpatched, so send() tests can patch runtime.verify
        live = {**self.live(shown, native), 'agent': 'codex', 'agent_status': 'idle'}
        info = {'pid': 10, 'started': '123', 'kind': 'codex', 'pane': 'w1:p1', 'account': str(self.account)}
        def api(*args):
            if args[0] == 'agent':return {'agent': live}
            return {'process_info': {'foreground_processes': [{'pid': 10}]}}
        with patch.object(runtime, 'herdr', side_effect=api), patch.object(runtime, 'process_info', return_value=info), \
             patch.object(runtime, 'resolve_history', side_effect=lambda kind, account, session: Path('/h/' + session)):
            return original(binding, ready=ready)

    def binding(self, session):
        return Binding('codex', session, str(self.account), 'w1:p1', 'term1', 'w1', '/h/' + session, 10, '123')

    def test_verify_and_send_follow_the_active_thread_not_stale_herdr(self):
        from left_undone import runtime
        a, b = self.binding(A), self.binding(B)
        self.verify(a, title(A), A);self.verify(b, title(B), B)
        with self.assertRaises(RuntimeError):self.verify(a, title(B), A)      # /new, Herdr stale A
        with self.assertRaises(RuntimeError):self.verify(b, title(A), B)      # /resume A, Herdr stale B
        self.verify(a, title(A), B)                                            # A recognised
        sent = []
        with patch.object(runtime, 'verify', side_effect=lambda binding, ready: self.verify(binding, title(A), B)), \
             patch.object(runtime, 'herdr', side_effect=lambda *args: sent.append(args)):
            with self.assertRaises(RuntimeError):runtime.send(b, 'x')
            runtime.send(a, 'y')
        self.assertEqual(sent, [('agent', 'prompt', 'w1:p1', 'y')])

    def test_codex_without_title_proof_is_blocked_even_when_herdr_matches(self):
        self.argv = ['codex']
        with self.assertRaises(RuntimeError):self.verify(self.binding(A), title(A), A)

    def test_claude_keeps_native_session_check(self):
        from left_undone import runtime
        live = {'agent': 'claude', 'pane_id': 'w1:p1', 'terminal_id': 'term1', 'agent_session': {'kind': 'id', 'value': 's1'}}
        binding = Binding('claude', 's1', 'acc', 'w1:p1', 'term1', 'w1', 'h', 10, '1')
        runtime.verify_live(binding, live)
        with self.assertRaises(RuntimeError):runtime.verify_live(binding, {**live, 'agent_session': {'kind': 'id', 'value': 's2'}})


if __name__ == '__main__':
    unittest.main()
