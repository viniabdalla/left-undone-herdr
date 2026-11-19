import json
import tempfile
import unittest
from pathlib import Path

from left_undone import renewal
from left_undone.core import CodexAdapter, Store
from left_undone.exchange import export_project, export_snapshot, import_selected


class RenewalTests(unittest.TestCase):
    def test_visible_status_requires_one_complete_native_uuid(self):
        sid = '01a1f08a-b9ef-71c2-977e-4d0b0c22aba6'
        status = '/status\n  Directory:  /tmp/project\n  Session:    ' + sid
        self.assertEqual(renewal.status_session(status), sid)
        self.assertIsNone(renewal.status_session('› Session: '+sid))
        self.assertIsNone(renewal.status_session(status+'\n'+status.replace(sid,'abcd'+sid[4:])))

    def test_only_a_completed_turn_can_release_the_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = Path(tmp)/'history'
            row = dict(type='event_msg',payload=dict(type='task_complete',last_agent_message='Saved\nREADY-abc ref'))
            history.write_text(json.dumps(row)+'\n')
            offset = history.stat().st_size
            with history.open('a') as stream:
                stream.write(json.dumps(dict(type='event_msg',payload=dict(type='user_message',message='READY-abc fake')))+'\n')
            self.assertEqual(renewal.receipt(history,offset,'READY-abc'), '')
            with history.open('a') as stream:
                stream.write(json.dumps(row)+'\n')
            self.assertEqual(renewal.receipt(history,offset,'READY-abc'), 'ref')

    def test_only_exported_source_tasks_cross_the_boundary_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stores = [Store(root/'db', key) for key in ('A','B','C')]
            for db in stores:
                self.addCleanup(db.close)
            a,b,c = stores
            c.add('task','Other'); export_project(c,root)
            a.add('task','Mine')
            _, ids = export_snapshot(a,root)
            self.assertEqual(import_selected(b,ids,root),1)
            self.assertEqual(import_selected(b,ids,root),0)
            self.assertEqual([i['text'] for i in b.items()],['Mine'])

    def test_interrupted_init_does_not_count_as_a_completed_init(self):
        rows = [
            ('event_msg', dict(type='task_started')),
            ('response_item', dict(role='user',content=[dict(text='Generate a file named AGENTS.md for this repo.')])),
            ('event_msg', dict(type='turn_aborted')),
            ('event_msg', dict(type='task_started')),
            ('event_msg', dict(type='task_complete',last_agent_message='Unrelated turn.'))
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'log'
            def write(data):
                path.write_text(''.join(json.dumps(dict(type=t,payload=p))+'\n' for t,p in data))
            write(rows)
            self.assertFalse(renewal.completed_init(path))
            write(rows[:2]+rows[-1:])
            self.assertTrue(renewal.completed_init(path))

    def test_handoff_receipt_is_not_delivery_evidence_for_exported_tasks(self):
        token = '0123456789ab'*2
        for line in ('READY-'+token+' handoff.txt', 'RESTORED-'+token+' OK'):
            row = dict(type='event_msg',payload=dict(type='task_complete',
                       last_agent_message='Verified the unchecked item in TODO.md.\n'+line))
            self.assertEqual(CodexAdapter().feed(row, {}, 'test'), [])

    def test_monitor_follows_only_a_completed_chain_in_the_same_process(self):
        from dataclasses import asdict, replace
        from left_undone.runtime import Binding
        old = Binding('codex','old','account','pane','term','workspace','hist',42,'123')
        new = replace(old, session='new',history='newhist')
        live = {'agent_session':{'kind':'id','value':'new'}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = renewal.journal(root,old)
            for stage, target, expected in [('restoring',new,old),('complete',replace(new,pid=77),old),
                                             ('complete',new,new)]:
                path.write_text(json.dumps(dict(stage=stage,binding=asdict(target))))
                self.assertEqual(renewal.confirmed_successor(root,old,live),expected)

    def test_source_mismatch_stops_before_export_and_before_a_second_probe(self):
        from unittest.mock import Mock, patch
        current = '01a1f076-c9a9-7483-a438-0b586b496e1b'
        old = '01a1ef8a-9776-7203-b4db-d4c97170b4f7'
        with patch.object(renewal,'same_terminal',return_value={'agent_status':'idle'}), \
             patch.object(renewal.runtime,'herdr') as api, \
             patch.object(renewal,'read_screen',return_value='  Session: '+current), \
             patch.object(renewal.time,'sleep'), \
             patch.object(renewal.time,'monotonic',side_effect=range(100)):
            with self.assertRaisesRegex(RuntimeError,'different conversation'):
                renewal.identified(Mock(pane='w1:p1'),'/tmp',expected=old)
            api.assert_called_once_with('agent','prompt','w1:p1','/status')

    def test_changed_active_session_requires_consent_for_the_same_tasks(self):
        from dataclasses import replace
        from unittest.mock import patch
        from left_undone.runtime import Binding
        from left_undone.projects import project_store
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = Binding('codex','old','account','pane','term','ws','oldlog',42,'0')
            active = replace(old,session='active',history=str(root/'newlog'))
            Path(active.history).touch()
            db = project_store(root,old,root)
            self.addCleanup(db.close)
            db.add('import','One task')
            with patch.object(renewal,'session_project',return_value=root), \
                 patch.object(renewal,'active_source',return_value=active), \
                 patch.object(renewal,'identified'),patch.object(renewal.runtime,'herdr') as api:
                with self.assertRaisesRegex(RuntimeError,'1 tasks'):
                    renewal.run(root,old)
                approved = json.loads(renewal.journal(root,old).read_text())['approval']
                db.add('import','Second task')
                with self.assertRaisesRegex(RuntimeError,'2 tasks'):
                    renewal.run(root,old,approved)
                api.assert_not_called()
                self.assertFalse((root/'.left-undone/tasks.md').exists())
                approved = json.loads(renewal.journal(root,old).read_text())['approval']
                with patch.object(renewal,'wait',side_effect=RuntimeError('stop after preparation')):
                    with self.assertRaisesRegex(RuntimeError,'stop after preparation'):
                        renewal.run(root,old,approved)
                api.assert_called_once()
                self.assertEqual(api.call_args.args[:3],('agent','prompt',active.pane))
                self.assertEqual(json.loads(renewal.journal(root,old).read_text())['source']['session'],'active')
