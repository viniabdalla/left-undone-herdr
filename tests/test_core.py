import json
import tempfile
import unittest
from pathlib import Path
from left_undone.core import Store, Collector, validate_audit

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = Store(self.root / 'state.db', 'codex:account:session')
        self.addCleanup(self.db.close)
        self.log = self.root / 'log.jsonl'
        self.log.touch()

    def append(self, row):
        with self.log.open('a') as f: f.write(json.dumps(row)+'\n')

    def test_import_deduplicates_and_never_reopens_done(self):
        self.db.import_md('- [ ] Fix X\n- [x] Finished\n* [ ] Fix X\n')
        self.assertEqual([i['text'] for i in self.db.items()], ['Fix X'])
        self.db.done([self.db.items()[0]['id']])
        self.db.import_md('- [ ] Fix X')
        self.assertEqual(self.db.items(), [])

    def test_export_roundtrip_and_session_isolation(self):
        self.db.import_md('- [ ] Fix X')
        other = Store(self.root / 'state.db', 'claude:account:session')
        self.addCleanup(other.close)
        self.assertEqual(other.items(), [])
        other.import_md(self.db.export_md())
        self.assertEqual(other.items()[0]['text'], 'Fix X')

    def test_audit_is_strict_atomic_and_bounded(self):
        for bad in ({'done':[True],'add':[]},{'done':[1],'add':[]},{'done':[],'add':['x']*6},{'done':[],'add':[3]}):
            with self.assertRaises(ValueError): validate_audit(bad, [])
        self.assertEqual(validate_audit({'done':[],'add':['next']}, []), {'done':[], 'add':['next']})

    def test_codex_partial_line_repeated_turn_and_reopen(self):
        row={'type':'event_msg','payload':{'type':'task_complete','turn_id':'t1','last_agent_message':'I will add tests.'}}
        data=json.dumps(row)
        self.log.write_text(data[:20])
        calls=[]
        def analyze(reply, opened):
            calls.append(reply); return {'done':[], 'add':['Add tests']}
        c=Collector(self.db,self.log,'codex',analyze)
        c.poll(); self.assertEqual(calls,[])
        with self.log.open('a') as f:f.write(data[20:]+'\n')
        c.poll(); self.append(row); c.poll()
        Collector(self.db,self.log,'codex',analyze).poll()
        self.assertEqual(len(calls),1)
        self.assertEqual(self.db.items()[0]['text'],'Add tests')

    def test_failed_analysis_preserves_items_and_retries(self):
        self.db.import_md('- [ ] Keep me')
        self.append({'type':'event_msg','payload':{'type':'task_complete','turn_id':'t','last_agent_message':'Later'}})
        def fail(*args):raise RuntimeError('model unavailable')
        c=Collector(self.db,self.log,'codex',fail)
        with self.assertRaises(RuntimeError):c.poll()
        self.assertEqual(len(self.db.items()),1)
        c.analyze=lambda reply,opened:{'done':[], 'add':['Next']}
        c.poll();self.assertEqual(len(self.db.items()),2)

    def test_codex_plan_only_after_success_and_completed_removed(self):
        self.append({'type':'response_item','payload':{'type':'function_call','name':'update_plan','call_id':'1','arguments':json.dumps({'plan':[{'step':'Build','status':'pending'}]})}})
        c=Collector(self.db,self.log,'codex',lambda *_: {'done':[], 'add':[]})
        c.poll();self.assertEqual(self.db.items(),[])
        self.append({'type':'response_item','payload':{'type':'function_call_output','call_id':'1','output':'Plan updated'}})
        c.poll();self.assertEqual(self.db.items()[0]['origin'],'task')
        self.db.done([self.db.items()[0]['id']]);self.assertEqual(self.db.items(),[])

    def test_claude_tasks_and_final_ignore_sidechains(self):
        c=Collector(self.db,self.log,'claude',lambda reply,opened:{'done':[], 'add':['Deliver patch']})
        self.append({'type':'assistant','uuid':'a','message':{'stop_reason':'tool_use','content':[{'type':'tool_use','id':'call','name':'TodoWrite','input':{'todos':[{'content':'Build','status':'in_progress'}]}}]}})
        self.append({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'call','content':'ok'}]}})
        self.append({'type':'assistant','uuid':'f','message':{'stop_reason':'end_turn','content':[{'type':'text','text':'I will deliver a patch.'}]}})
        self.append({'type':'assistant','uuid':'side','isSidechain':True,'message':{'stop_reason':'end_turn','content':[{'type':'text','text':'ignore'}]}})
        c.poll();self.assertEqual({i['origin'] for i in self.db.items()},{'task','promise'})
        self.assertEqual(len(self.db.items()),2)

    def test_promises_close_without_removing_tasks(self):
        self.db.add('task','Build','t')
        self.db.add('promise','Ship','p')
        self.append({'type':'event_msg','payload':{'type':'task_complete','turn_id':'t','last_agent_message':'Shipped.'}})
        Collector(self.db,self.log,'codex',lambda r,o:{'done':[1],'add':[]}).poll()
        self.assertEqual([i['text'] for i in self.db.items()],['Build'])

if __name__=='__main__':unittest.main()

class NativeTaskTests(unittest.TestCase):
    setUp = CoreTests.setUp
    def test_native_completion_can_reopen_but_manual_completion_cannot(self):
        def update(n,status):
            self.db.commit_line({'offset':0,'pending':{}},[{'id':str(n),'kind':'upsert','tasks':[{'source':'1','text':'Build','status':status}]}],{})
        update(1,'pending');update(2,'completed');self.assertEqual(self.db.items(),[])
        update(3,'in_progress');self.assertEqual(len(self.db.items()),1)
        self.db.done([self.db.items()[0]['id']]);update(4,'pending')
        self.assertEqual(self.db.items(),[])
