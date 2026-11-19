import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

from left_undone import dispatch
from left_undone.core import Store
from left_undone.runtime import Binding


class DispatchFixture(unittest.TestCase):
    kind = 'codex'

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.parent = Binding(self.kind,'parent','account','w1:p1','term1','w1','history',1,'start')
        self.store = Store(self.root/'state.db',self.parent.key)
        self.addCleanup(self.store.close)
        self.store.add('task','Inspect README')
        self.store.toggle(self.store.items()[0]['id'])
        self.conn = self.store.conn
        dispatch.setup(self.conn)
        live = {'workspace_id':'w1','foreground_cwd':str(self.root)}
        verify = patch.object(dispatch,'verify',return_value=live)
        project = patch.object(dispatch,'project_root',return_value=self.root)
        project.start()
        self.addCleanup(project.stop)
        verify.start()
        self.addCleanup(verify.stop)
        with patch.object(dispatch,'send') as send:
            dispatch.request(self.store,self.parent,self.root)
        self.assertIn('choose the worker model AND reasoning effort',send.call_args.args[1])
        self.job = self.conn.execute('SELECT * FROM dispatches').fetchone()
        self.args = Namespace(ticket=self.job['ticket'],question=False,model='chosen-model',effort='high')

    def check_worker_launch(self, options, account_var):
        pane = dict(workspace_id='w1',tab_id='tab',pane_id='pane',cwd=str(self.root),terminal_id='term2')
        with patch.object(dispatch,'herdr',return_value={'tab':pane,'root_pane':pane}) as api, patch.object(dispatch.subprocess,'run') as run:
            result=dispatch.review(self.conn,self.root,self.args,'Check README')
            self.assertEqual(result['tab'],'tab')
            self.assertEqual(api.call_args.args[:6],('tab','create','--workspace','w1','--cwd',str(self.root)))
            with self.assertRaises(ValueError):
                dispatch.review(self.conn,self.root,self.args,'Duplicate')
            self.assertEqual(run.call_count,1)
        with patch.object(dispatch,'herdr',return_value={'pane':pane}), patch.object(Path,'cwd',return_value=self.root), \
             patch.dict(dispatch.os.environ,{'HERDR_PANE_ID':'pane'}), patch.object(dispatch.subprocess,'run') as run:
            dispatch.worker(self.conn,self.root,self.job['receipt'])
        argv=run.call_args.args[0]
        self.assertEqual(argv[:-1], [self.kind, '--model', 'chosen-model', *options, '--'])
        self.assertEqual(run.call_args.kwargs['env'][account_var], self.parent.account)
        self.assertIn(dispatch.callback(self.root, 'dispatch-report', self.job['receipt']), argv[-1])
        self.assertIn('Check README',argv[-1])
        self.assertEqual(run.call_args.kwargs['cwd'],str(self.root))
        self.assertEqual(dispatch.records(self.conn,self.parent.key)[0]['state'],'stopped')
        self.assertEqual(len(self.store.items()),1)


class ClaudeDispatchTests(DispatchFixture):
    kind = 'claude'

    def test_claude_worker_launch(self):
        self.check_worker_launch(['--effort', 'high', '--permission-mode', 'bypassPermissions'],
                                 'CLAUDE_CONFIG_DIR')


class DispatchTests(DispatchFixture):
    def test_codex_worker_launch(self):
        self.check_worker_launch(['-c', 'model_reasoning_effort="high"',
                                  '--dangerously-bypass-approvals-and-sandbox'], 'CODEX_HOME')

    def test_question_and_missing_effort_do_not_create_tabs(self):
        with patch.object(dispatch,'herdr') as api:
            self.args.question=True
            dispatch.review(self.conn,self.root,self.args,'Which file?')
            self.args.question=False
            self.args.effort=None
            with self.assertRaises(ValueError):
                dispatch.review(self.conn,self.root,self.args,'Read the file')
            api.assert_not_called()
        self.assertEqual(dispatch.records(self.conn,self.parent.key)[0]['summary'],'Which file?')
        self.assertEqual(dispatch.records(self.conn,'another session'),[])

    def test_worker_can_report_blocker_then_completion_only_to_origin(self):
        self.conn.execute("UPDATE dispatches SET state='running'")
        self.conn.commit()
        with self.assertRaises(ValueError):
            dispatch.report(self.conn,self.job['ticket'],'done','Wrong callback')
        dispatch.report(self.conn,self.job['receipt'],'blocked','Need approval')
        self.assertEqual(len(self.store.items()),1)
        dispatch.report(self.conn,self.job['receipt'],'done','Read and checked README')
        dispatch.report(self.conn,self.job['receipt'],'done','Read and checked README')
        self.assertEqual(self.store.items(),[])
        self.assertEqual(dispatch.records(self.conn,self.parent.key)[0]['summary'],'Read and checked README')

    def test_changed_task_blocks_launch_and_duplicate_click_creates_no_request(self):
        with patch.object(dispatch,'send') as send:
            with self.assertRaises(ValueError):
                dispatch.request(self.store,self.parent,self.root)
            send.assert_not_called()
        self.store.done([self.job['item']])
        with patch.object(dispatch,'herdr') as api, self.assertRaises(ValueError):
            dispatch.review(self.conn,self.root,self.args,'Brief')
        api.assert_not_called()


class PlanningDispatchTests(DispatchFixture):
    def setUp(self):
        super().setUp()
        self.conn.execute("UPDATE dispatches SET state='stopped'")
        self.conn.commit()
        with patch.object(dispatch, 'send') as send:
            dispatch.request(self.store, self.parent, self.root, plan=True)
        self.assertIn('plan only', send.call_args.args[1])
        self.job = self.conn.execute('SELECT * FROM dispatches WHERE plan=1').fetchone()

    def test_plan_report_keeps_selection_and_next_execution_receives_plan(self):
        pane = dict(tab_id='tab', pane_id='pane', terminal_id='term2')
        with self.conn:
            self.conn.execute("UPDATE dispatches SET state='launch', tab='tab', pane='pane', terminal='term2' "
                              "WHERE plan=1")
        with patch.object(dispatch, 'herdr', return_value={'pane': pane}), \
                patch.object(Path, 'cwd', return_value=self.root), \
                patch.dict(dispatch.os.environ, {'HERDR_PANE_ID': 'pane'}), \
                patch.object(dispatch.dispatch_plan, 'run', return_value='1. Inspect README') as planner, \
                patch('builtins.print'):
            dispatch.worker(self.conn, self.root, self.job['receipt'])
        self.assertEqual(planner.call_args.args[0], 'codex')
        self.assertEqual(dispatch.records(self.conn, self.parent.key)[0]['state'], 'planned')
        self.assertTrue(self.store.items()[0]['selected'])
        with patch.object(dispatch, 'send') as send:
            dispatch.request(self.store, self.parent, self.root)
        self.assertIn('1. Inspect README', send.call_args.args[1])

    def test_completion_callback_cannot_execute_a_planning_ticket(self):
        with self.conn:
            self.conn.execute("UPDATE dispatches SET state='running' WHERE plan=1")
        with self.assertRaises(ValueError):
            dispatch.report(self.conn, self.job['receipt'], 'done', 'Accidental completion')
        self.store.done([self.job['item']])
        dispatch.report(self.conn, self.job['receipt'], 'planned', 'Late plan')
        self.assertEqual(dispatch.records(self.conn, self.parent.key)[0]['state'], 'stopped')

    def test_claude_question_without_native_plan_is_reported_as_failure(self):
        response = Mock(returncode=0, stdout=json.dumps({'result': 'Which runner should I use?'}))
        with patch.object(dispatch.dispatch_plan.subprocess, 'run', return_value=response) as cli, \
                self.assertRaisesRegex(RuntimeError, 'Which runner'):
            dispatch.dispatch_plan.run('claude', self.job, {}, Mock())
        argv = cli.call_args.args[0]
        self.assertEqual(argv[argv.index('--permission-mode') + 1], 'plan')
        self.assertFalse(list(self.root.glob('.left-undone-plan-*')))

    def test_codex_native_question_is_shown_in_tab_and_panel_before_plan(self):
        from io import StringIO

        events = [
            {'id': 1, 'result': {}}, {'id': 2, 'result': {'thread': {'id': 'thread'}}},
            {'id': 3, 'result': {'turn': {'id': 'turn'}}},
            {'id': 4, 'method': 'item/tool/requestUserInput', 'params': {'turnId': 'turn',
             'questions': [{'id': 'runner', 'question': 'Which runner?', 'options': []}]}},
            {'method': 'item/completed', 'params': {'turnId': 'turn', 'item': {'type': 'plan', 'text': 'Use pytest'}}},
            {'method': 'turn/completed', 'params': {'turn': {'id': 'turn', 'status': 'completed'}}},
        ]
        proc = Mock(stdout=StringIO('\n'.join(map(json.dumps, events))))
        env = {}
        question_status = Mock()
        with patch.object(dispatch.dispatch_plan.subprocess, 'Popen', return_value=proc), \
                patch('builtins.input', return_value='pytest'), patch('builtins.print'):
            plan = dispatch.dispatch_plan.run('codex', self.job, env, question_status)
        self.assertEqual(plan, 'Use pytest')
        self.assertEqual([c.args for c in question_status.call_args_list], [('Which runner?',), ('',)])
        messages = [json.loads(c.args[0]) for c in proc.stdin.write.call_args_list]
        turn = next(m for m in messages if m.get('method') == 'turn/start')
        self.assertEqual(turn['params']['collaborationMode']['mode'], 'plan')
        self.assertEqual(messages[-1]['result']['answers']['runner'], {'answers': ['pytest']})


class TaskVerdictTests(DispatchFixture):
    def setUp(self):
        super().setUp()
        with self.conn:
            self.conn.execute("UPDATE dispatches SET state='running',brief='Check the documented command'")
        dispatch.report(self.conn, self.job['receipt'], 'blocked', 'Command is missing')
        self.row = dispatch.records(self.conn, self.parent.key)[0]

    def test_review_reaches_origin_and_preserves_original_report_and_item(self):
        from dataclasses import replace
        with patch.object(dispatch, 'send') as send:
            with self.assertRaises(ValueError):
                dispatch.request_verdict(self.conn, replace(self.parent, session='other'), self.root,
                                        self.row['dispatch_id'], 0)
            send.assert_not_called()
            dispatch.request_verdict(self.conn, self.parent, self.root, self.row['dispatch_id'], 0)
            with self.assertRaises(ValueError):
                dispatch.request_verdict(self.conn, self.parent, self.root, self.row['dispatch_id'], 0)
        send.assert_called_once()
        binding, prompt = send.call_args.args
        self.assertEqual(binding, self.parent)
        for value in ('Inspect README', 'Check the documented command', 'Command is missing', 'dispatch-verdict'):
            self.assertIn(value, prompt)
        token = self.conn.execute('SELECT token FROM dispatch_reviews').fetchone()[0]
        with patch.dict(dispatch.os.environ, {'HERDR_PANE_ID': self.parent.pane, 'CODEX_THREAD_ID': self.parent.session}):
            dispatch.save_verdict(self.conn, token, 'not-done', 'The command is missing.')
            dispatch.save_verdict(self.conn, token, 'not-done', 'The command is missing.')
        row = dispatch.records(self.conn, self.parent.key)[0]
        self.assertEqual((row['verdict'], row['reason'], row['summary']), ('not-done', 'The command is missing.', 'Command is missing'))
        self.assertEqual(len(self.store.items()), 1)
        self.assertFalse(dispatch.records(self.conn, 'other'))
        dispatch.report(self.conn, self.job['receipt'], 'done', 'Command added')
        self.assertIsNone(dispatch.records(self.conn, self.parent.key)[0]['verdict'])
        with self.assertRaises(ValueError):
            dispatch.save_verdict(self.conn, token, 'done', 'Obsolete callback')

    def test_busy_source_and_uncertain_retry_never_change_the_worker_report(self):
        from left_undone.runtime import AgentBusy
        args = self.conn, self.parent, self.root, self.row['dispatch_id']
        with patch.object(dispatch, 'verify', side_effect=AgentBusy('busy')), patch.object(dispatch, 'send') as send:
            with self.assertRaises(AgentBusy):
                dispatch.request_verdict(*args, 0)
            send.assert_not_called()
        with patch.object(dispatch, 'send', side_effect=RuntimeError('unconfirmed')):
            with self.assertRaisesRegex(RuntimeError, 'unconfirmed'):
                dispatch.request_verdict(*args, 0)
        pending = dispatch.records(self.conn,self.parent.key)[0]
        self.assertEqual(pending['reason'],'unconfirmed')
        old = self.conn.execute('SELECT token FROM dispatch_reviews').fetchone()[0]
        with patch.object(dispatch,'send'):
            dispatch.request_verdict(*args, pending['attempt'])
        new = self.conn.execute('SELECT token FROM dispatch_reviews').fetchone()[0]
        with self.assertRaises(ValueError):
            dispatch.save_verdict(self.conn,old,'done','Late result')
        with patch.dict(dispatch.os.environ,{'HERDR_PANE_ID':'different-pane'}), self.assertRaises(ValueError):
            dispatch.save_verdict(self.conn,new,'done','Wrong caller')
        with patch.dict(dispatch.os.environ,{'HERDR_PANE_ID':self.parent.pane,'CODEX_THREAD_ID':self.parent.session}):
            dispatch.save_verdict(self.conn,new,'done','The command is in the file.')
        self.assertEqual(dispatch.records(self.conn,self.parent.key)[0]['summary'], 'Command is missing')
