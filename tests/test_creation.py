import json
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from left_undone.core import Store, Collector
from left_undone.projects import ProjectStore
from left_undone.curation import Curator


class CreationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.path=self.root/'state.db'

    def store(self,session='a',project=False):
        db=ProjectStore(self.path,session,'project') if project else Store(self.path,session)
        self.addCleanup(db.close);return db

    def test_legacy_dates_stay_unknown_and_tombstones_and_selection_survive(self):
        conn=sqlite3.connect(self.path)
        conn.executescript('''CREATE TABLE items(id INTEGER PRIMARY KEY,session TEXT,origin TEXT,source TEXT,
            text TEXT,status TEXT DEFAULT 'open',selected INTEGER DEFAULT 0,dismissed INTEGER DEFAULT 0,
            UNIQUE(session,origin,source));
            INSERT INTO items VALUES(1,'a','import','one','Old','open',1,0);
            INSERT INTO items VALUES(2,'a','import','two','Closed','done',0,1);''')
        conn.close()
        db=self.store();self.assertIsNone(db.items()[0].get('created_at','missing'))
        self.assertEqual(db.items()[0]['selected'],1)
        self.assertEqual(db.import_md('- [ ] Closed'),0)
        again=self.store();self.assertIsNone(again.items()[0]['created_at'])

    def test_new_imports_keep_creation_date_after_reopen_and_edits(self):
        a=self.store(project=True);before=time.time();a.import_md('- [ ] New task')
        first=a.items()[0];self.assertGreaterEqual(first.get('created_at',0),before-.01)
        reopened=self.store('a',project=True);self.assertEqual(reopened.items()[0]['created_at'],first['created_at'])
        with a.conn:a.conn.execute('UPDATE items SET text=? WHERE id=?',('Rewritten',first['id']))
        self.assertEqual(a.items()[0]['created_at'],first['created_at'])
        self.assertEqual(a.import_md('- [ ] Rewritten'),0)
        a.done([first['id']]);self.assertEqual(a.import_md('- [ ] Rewritten'),0)

    def test_collected_promises_use_source_time_and_replay_preserves_creation(self):
        for kind in ('codex','claude'):
            with self.subTest(kind=kind):
                db=self.store(kind);log=self.root/(kind+'.jsonl')
                row=({'type':'event_msg','payload':{'type':'task_complete','turn_id':'one','last_agent_message':'I will ship'}}
                     if kind=='codex' else {'type':'assistant','uuid':'one','message':{'stop_reason':'end_turn','content':[{'type':'text','text':'I will ship'}]}})
                row['timestamp']='2026-11-10T12:00:00Z';log.write_text(json.dumps(row)+'\n')
                collector=Collector(db,log,kind,lambda *_:{'done':[],'add':['Ship']});collector.poll()
                self.assertEqual(db.items()[0].get('created_at'),1794312000.0)
                with log.open('a') as f:f.write(json.dumps(row)+'\n')
                collector.poll();self.assertEqual(db.items()[0]['created_at'],1794312000.0)

    def test_native_task_update_keeps_original_source_date(self):
        db=self.store();log=self.root/'codex.jsonl'
        def event(call,text,stamp):
            return [dict(type='response_item',timestamp=stamp,payload={'type':'function_call','name':'update_plan','call_id':call,'arguments':json.dumps({'plan':[{'step':text,'status':'pending'}]})}),
                    dict(type='response_item',timestamp=stamp,payload={'type':'function_call_output','call_id':call,'output':'ok'})]
        rows=event('one','Task','2026-11-10T12:00:00Z')+event('two','Task','2026-11-11T12:00:00Z')
        log.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        Collector(db,log,'codex',lambda *_:{'done':[],'add':[]}).poll()
        self.assertEqual(db.items()[0].get('created_at'),1794312000.0)

    def test_curator_addition_uses_source_time_and_update_cannot_change_it(self):
        db=self.store(project=True)
        empty={'complete':True,'add':[],'update':[],'done':[],'duplicate':[],'conflicts':[]}
        curator=Curator(db,lambda _:{**empty,'add':[{'scope':'project','text':'Ship','evidence':'Ship'}]})
        curator.review('Ship','','one','2026-11-10T12:00:00Z')
        item=db.items()[0];self.assertEqual(item.get('created_at'),1794312000.0)
        curator.analyze=lambda _:{**empty,'update':[{'id':item['id'],'text':'Ship tomorrow','evidence':'Ship tomorrow'}]}
        curator.review('Ship tomorrow','','two','2026-11-11T12:00:00Z')
        self.assertEqual(db.items()[0]['text'],'Ship tomorrow')
        self.assertEqual(db.items()[0]['created_at'],1794312000.0)

    def test_invalid_or_missing_source_timestamp_is_unknown(self):
        for n,stamp in enumerate((None,'bad','2026-11-10T12:00:00')):
            db=self.store(str(n));log=self.root/(str(n)+'.jsonl')
            log.write_text(json.dumps({'type':'event_msg','timestamp':stamp,'payload':{'type':'task_complete','turn_id':'one','last_agent_message':'Ship'}})+'\n')
            Collector(db,log,'codex',lambda *_:{'done':[],'add':['Ship']}).poll()
            self.assertIsNone(db.items()[0].get('created_at','missing'))

    def test_parallel_initialization_and_inserts_keep_distinct_dates(self):
        self.store();errors=[]
        def worker(n):
            try:
                db=Store(self.path,str(n))
                try:db.add('import','Item '+str(n));self.assertIsInstance(db.items()[0]['created_at'],float)
                finally:db.close()
            except Exception as e:errors.append(e)
        workers=[threading.Thread(target=worker,args=(n,)) for n in range(4)]
        for w in workers:w.start()
        for w in workers:w.join(8)
        self.assertEqual(errors,[])
