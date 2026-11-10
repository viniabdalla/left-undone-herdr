import os
import unittest
from unittest.mock import patch
from left_undone import runtime

class ContextTests(unittest.TestCase):
    def recover(self, sessions, foreground=True):
        procs=[{'pid':n+10,'pane':'w1:p1','kind':'codex'} for n in range(len(sessions))]
        def environ(pid):
            return {'HERDR_ENV':'1','HERDR_PANE_ID':'w1:p1','HERDR_SOCKET_PATH':'/socket'+str(pid)}
        def api(*args,env=None):
            pid=int(env['HERDR_SOCKET_PATH'].removeprefix('/socket'))
            if args[:2]==('agent','list'):
                return {'agents':[{'agent':'codex','pane_id':'w1:p1','agent_session':{'kind':'id','value':sessions[pid-10]}}]}
            return {'process_info':{'foreground_processes':[{'pid':pid if foreground else 999}]}}
        with patch.object(runtime,'raw_herdr',side_effect=api),patch.object(runtime,'processes',return_value=procs),patch.object(runtime,'process_environment',side_effect=environ):
            runtime.restore_context()

    def test_daemon_restores_exact_session_on_its_own_socket(self):
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'current'},clear=True):
            self.recover(['other','current'])
            self.assertEqual(os.environ['HERDR_SOCKET_PATH'],'/socket11')
            self.assertEqual(os.environ['HERDR_PANE_ID'],'w1:p1')

    def test_missing_wrong_or_duplicate_sessions_refuse(self):
        for ids in ([],['other'],['current','current']):
            with self.subTest(ids=ids),patch.dict(os.environ,{'CODEX_THREAD_ID':'current'},clear=True):
                with self.assertRaises(RuntimeError):self.recover(ids)
                self.assertNotIn('HERDR_ENV',os.environ)

    def test_stale_process_refuses(self):
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'current'},clear=True):
            with self.assertRaises(RuntimeError):self.recover(['current'],foreground=False)
            self.assertNotIn('HERDR_ENV',os.environ)

    def test_no_thread_refuses_without_querying_server(self):
        with patch.dict(os.environ,{},clear=True),patch.object(runtime,'raw_herdr') as api:
            with self.assertRaises(RuntimeError):runtime.restore_context()
            api.assert_not_called()
