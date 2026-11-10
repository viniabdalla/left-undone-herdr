import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from left_undone.runtime import Binding, verify_live, send_selected, Analyzer, resolve_history
from left_undone.core import Store

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.binding=Binding('codex','s1',str(self.root),'w1:p1','term1','w1',str(self.root/'log.jsonl'),10,'123')
        self.live={'agent':'codex','pane_id':'w1:p1','terminal_id':'term1','agent_session':{'kind':'id','value':'s1'},'agent_status':'idle'}

    def test_session_switch_or_missing_identity_refuses_send(self):
        verify_live(self.binding,self.live)
        for field,value in [('agent_session',{'value':'s2'}),('agent_session',None),('terminal_id','term2'),('agent','claude')]:
            changed=dict(self.live);changed[field]=value
            with self.assertRaises(RuntimeError):verify_live(self.binding,changed)

    def test_verify_checks_actual_foreground_pid_not_only_inherited_environment(self):
        from left_undone.runtime import verify
        def api(*args):
            if args[0]=='agent':return {'agent':self.live}
            return {'process_info':{'foreground_processes':[{'pid':999}]}}
        info={'pid':10,'started':'123','kind':'codex','pane':'w1:p1','account':str(self.root)}
        with patch('left_undone.runtime.herdr',side_effect=api),patch('left_undone.runtime.process_info',return_value=info),patch('left_undone.runtime.resolve_history',return_value=Path(self.binding.history)):
            with self.assertRaises(RuntimeError):verify(self.binding)

    def test_send_keeps_items_and_failed_send_keeps_selection(self):
        db=Store(self.root/'s.db','s1');self.addCleanup(db.close)
        db.add('promise','Build tests'); item=db.items()[0]; db.toggle(item['id'])
        sent=[]
        send_selected(db,lambda text:sent.append(text))
        self.assertIn('Build tests',sent[0]);self.assertEqual(len(db.items()),1)
        self.assertEqual(db.items()[0]['selected'],0)
        db.toggle(item['id'])
        def fail(text):raise RuntimeError('switched')
        with self.assertRaises(RuntimeError):send_selected(db,fail)
        self.assertEqual(db.items()[0]['selected'],1)

    def test_history_resolved_only_inside_selected_account(self):
        p=self.root/'sessions/2026/11/10';p.mkdir(parents=True)
        f=p/'rollout-s1.jsonl';f.write_text(json.dumps({'type':'session_meta','payload':{'id':'s1'}})+'\n')
        self.assertEqual(resolve_history('codex',self.root,'s1'),f.resolve())
        with self.assertRaises(RuntimeError):resolve_history('codex',self.root,'other')

    def test_shared_transcript_directory_is_allowed_but_account_stays_explicit(self):
        shared=self.root/'shared';shared.mkdir()
        account=self.root/'account';account.mkdir()
        (account/'projects').symlink_to(shared,target_is_directory=True)
        project=shared/'project';project.mkdir()
        f=project/'s1.jsonl';f.write_text(json.dumps({'sessionId':'s1'})+'\n')
        self.assertEqual(resolve_history('claude',account,'s1'),f.resolve())

    def test_analyzer_does_not_inherit_other_account_api_credentials(self):
        with patch.dict('os.environ',{'OPENAI_API_KEY':'parent-key','ANTHROPIC_API_KEY':'parent-key','ANTHROPIC_AUTH_TOKEN':'parent-token','ANTHROPIC_BASE_URL':'https://wrong.invalid'}):
            _,env=Analyzer(self.binding).command(self.root,self.root/'schema',self.root/'out')
        self.assertFalse('OPENAI_API_KEY' in env)
        self.assertFalse('ANTHROPIC_API_KEY' in env)
        self.assertFalse('ANTHROPIC_AUTH_TOKEN' in env)
        self.assertFalse('ANTHROPIC_BASE_URL' in env)

    def test_analyzer_uses_required_models_and_isolates_context(self):
        for kind,model in [('codex','gpt-6-luna'),('claude','haiku')]:
            b=Binding(kind,'s1',str(self.root),'w1:p1','term1','w1','log',10,'123')
            a=Analyzer(b)
            argv,env=a.command(self.root,self.root/'schema.json',self.root/'answer.json')
            self.assertIn(model,argv)
            self.assertEqual(env['LEFT_UNDONE_ANALYZER'],'1')
            self.assertNotIn('HERDR_PANE_ID',env)
            self.assertIn('--ephemeral' if kind=='codex' else '--no-session-persistence',argv)

class OpenTests(unittest.TestCase):
    def test_split_targets_pane_without_workspace_and_reuses_live_panel(self):
        from left_undone.app import open_panel
        with tempfile.TemporaryDirectory() as folder:
            b=Binding('codex','s','account','w1:p1','term','w1','log',10,'1')
            calls=[]
            def api(*args):
                calls.append(args)
                if args[:3]==('plugin','pane','open'):
                    self.assertNotIn('--workspace',args)
                    (Path(folder)/(b.key+'.pid')).write_text(str(__import__('os').getpid()))
                    return {'pane':{'pane_id':'w1:p2','terminal_id':'panel-term'}}
                return {'pane':{'pane_id':'w1:p2','terminal_id':'panel-term'}}
            with patch('left_undone.app.verify'),patch('left_undone.app.state_root',return_value=Path(folder)),patch('left_undone.app.herdr',side_effect=api):
                result=open_panel(b)
            self.assertEqual(result['pane'],'w1:p2')

class ReopenTests(unittest.TestCase):
    def test_same_session_with_new_process_replaces_owned_panel(self):
        from left_undone.app import open_panel,atomic_json
        from dataclasses import asdict
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);old=Binding('codex','s','account','w1:p1','term','w1','log',10,'1')
            new=Binding(**{**asdict(old),'pid':11,'started':'2'})
            atomic_json(root/(old.key+'.binding.json'),asdict(old))
            atomic_json(root/(old.key+'.pane.json'),{'pane':'w1:p2','terminal':'panel-term','pid':__import__('os').getpid()})
            calls=[]
            def api(*args):
                calls.append(args)
                if args[:3]==('plugin','pane','open'):return {'pane':{'pane_id':'w1:p3','terminal_id':'new-panel'}}
                if args[:2]==('pane','current'):return {'pane':{'pane_id':'w1:p2','terminal_id':'panel-term'}}
                return {}
            with patch('left_undone.app.verify'),patch('left_undone.app.state_root',return_value=root),patch('left_undone.app.herdr',side_effect=api),patch('left_undone.app.panel_process_alive',return_value=True,create=True):
                result=open_panel(new)
            self.assertIn(('plugin','pane','close','w1:p2'),calls)
            self.assertEqual(result['pane'],'w1:p3')

    def test_delayed_panel_start_does_not_duplicate(self):
        from left_undone.app import open_panel,atomic_json
        from dataclasses import asdict
        import time
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);b=Binding('codex','s','account','w1:p1','term','w1','log',10,'1')
            atomic_json(root/(b.key+'.binding.json'),asdict(b))
            atomic_json(root/(b.key+'.pane.json'),{'pane':'w1:p2','terminal':'panel-term','created':time.time()})
            def api(*args):
                self.assertNotEqual(args[:3],('plugin','pane','open'))
                return {'pane':{'pane_id':'w1:p2','terminal_id':'panel-term'}}
            with patch('left_undone.app.verify'),patch('left_undone.app.state_root',return_value=root),patch('left_undone.app.herdr',side_effect=api),patch('left_undone.app.panel_process_alive',return_value=False,create=True):
                self.assertTrue(open_panel(b)['reused'])
