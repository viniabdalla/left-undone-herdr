import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from left_undone.runtime import Binding

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
        # A 38-column pane wraps the UUID under the label.
        narrow = '  Session:\n                       01a1f08a-b9ef-7\n                       1c2-977e-4d0b0c\n                       22aba6\n  Context window:      92% left'
        self.assertEqual(renewal.status_session(narrow), sid)
        self.assertIsNone(renewal.status_session('  Session:\n      01a1f08a-b9ef-7\n  Context window: x'))

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


class UniversalHandoffTests(unittest.TestCase):
    def test_receipt_reads_claude_final_reply_and_codex_task_complete(self):
        from left_undone.renewal import receipt
        with tempfile.TemporaryDirectory() as folder:
            claude = Path(folder)/'claude.jsonl'
            claude.write_text(json.dumps({'type':'assistant','message':{'stop_reason':'end_turn',
                'content':[{'type':'text','text':'Saved.\nREADY-abc ref-42'}]}})+'\n')
            self.assertEqual(receipt(claude,0,'READY-abc'),'ref-42')
            codex = Path(folder)/'codex.jsonl'
            codex.write_text(json.dumps({'type':'event_msg','payload':{'type':'task_complete',
                'last_agent_message':'RESTORED-x OK'}})+'\n')
            self.assertEqual(receipt(codex,0,'RESTORED-x'),'OK')

    def test_skill_is_found_by_name_only_when_installed(self):
        from left_undone.renewal import find_skill, skill_hint
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binding = Binding('claude','s',str(root/'account'),'p','t','w','h',1,'1')
            with patch('pathlib.Path.home',return_value=root/'home'):
                self.assertIsNone(find_skill(binding,root/'project'))
                self.assertEqual(skill_hint(binding,root/'project'),'')
                skill = root/'home/.claude/skills/someone-handoff'
                skill.mkdir(parents=True);(skill/'SKILL.md').write_text('x')
                self.assertEqual(find_skill(binding,root/'project'),'someone-handoff')
                self.assertIn('someone-handoff',skill_hint(binding,root/'project'))
                codex = Binding('codex','s',str(root/'account'),'p','t','w','h',1,'1')
                self.assertIsNone(find_skill(codex,root/'project'))

    def test_claude_init_needs_command_then_finished_reply(self):
        from left_undone.renewal import claude_init_done
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'c.jsonl'
            init = {'type':'user','message':{'content':'<command-name>/init</command-name>'}}
            reply = {'type':'assistant','message':{'stop_reason':'end_turn','content':[]}}
            path.write_text(json.dumps(reply)+'\n'+json.dumps(init)+'\n')
            self.assertFalse(claude_init_done(path))
            path.write_text(json.dumps(init)+'\n'+json.dumps(reply)+'\n')
            self.assertTrue(claude_init_done(path))

    def test_default_claude_account_launches_without_config_dir(self):
        # CLAUDE_CONFIG_DIR=~/.claude makes Claude read ~/.claude/.claude.json instead of
        # ~/.claude.json, losing folder trust and user MCP servers.
        from left_undone.renewal import account_env
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            with patch('pathlib.Path.home',return_value=home):
                self.assertEqual(account_env('claude',str(home/'.claude')),([],['-u','CLAUDE_CONFIG_DIR']))
                other = str(home/'work-claude')
                self.assertEqual(account_env('claude',other),(['--env','CLAUDE_CONFIG_DIR='+other],[]))
                self.assertEqual(account_env('codex',str(home/'.codex')),
                                 (['--env','CODEX_HOME='+str(home/'.codex')],[]))

    def test_successor_waits_until_its_transcript_records_the_worktree(self):
        # Herdr announces the Claude session before the transcript file exists.
        from left_undone.renewal import split_binding
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            history = root/'new.jsonl'
            source = Binding('claude','old',str(root/'account'),'p1','t1','w','h',1,'1')
            new = Binding('claude','new',str(root/'account'),'p2','t2','w',str(history),2,'2')
            job = {'pane':'p2','terminal':'t2','token':'tok','project':str(root),'source':{'session':'old'}}
            with patch('left_undone.runtime.candidates',return_value=([new],[])), \
                 patch('left_undone.runtime.process_environment',return_value={'LEFT_UNDONE_HANDOFF':'tok'}), \
                 patch('left_undone.runtime.verify',return_value={'agent_status':'idle'}):
                self.assertIsNone(split_binding(source,job))
                history.write_text(json.dumps({'type':'user','sessionId':'new','cwd':str(root)})+'\n')
                with patch('left_undone.renewal.project_root',side_effect=lambda p:Path(p)), \
                     patch('left_undone.repository.project_root',side_effect=lambda p:Path(p)):
                    self.assertEqual(split_binding(source,job),new)
                    history.write_text(json.dumps({'type':'user','sessionId':'new','cwd':'/elsewhere'})+'\n')
                    with self.assertRaises(RuntimeError):
                        split_binding(source,job)
