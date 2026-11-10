import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from left_undone import runtime, ui_layout
from left_undone.core import Store


class BusyQueueTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.db=Store(self.root/'state.db','test');self.addCleanup(self.db.close)
        self.db.add('import','Primeira tarefa');self.db.add('import','Segunda tarefa')
        for item in self.db.items():self.db.toggle(item['id'])

    def offer(self):
        def busy(_):raise runtime.AgentBusy('Agente ocupado')
        with self.assertRaises(runtime.QueueOffer) as result:runtime.send_selected(self.db,busy)
        return result.exception

    def test_busy_offer_freezes_selection_and_confirmation_only_clears_sent_items(self):
        offer=self.offer()
        self.assertTrue(all(i['selected'] for i in self.db.items()))
        self.db.add('import','Selecionada depois')
        last=self.db.items()[-1];self.db.toggle(last['id'])
        sent=[]
        count=runtime.queue_selected(self.db,offer,sent.append)
        self.assertEqual(count,2)
        self.assertEqual(sent,['You left this undone: Primeira tarefa\nYou left this undone: Segunda tarefa'])
        self.assertEqual([i['id'] for i in self.db.items() if i['selected']],[last['id']])
        self.assertEqual(len(self.db.items()),3)

    def test_changed_or_completed_or_deselected_item_never_gets_queued(self):
        for change in ('text','done','selection'):
            with self.subTest(change=change):
                db=Store(self.root/(change+'.db'),'test')
                try:
                    db.add('import','Original');item=db.items()[0];db.toggle(item['id'])
                    def busy(_):raise runtime.AgentBusy('busy')
                    with self.assertRaises(runtime.QueueOffer) as result:runtime.send_selected(db,busy)
                    if change=='text':
                        with db.conn:db.conn.execute('UPDATE items SET text=? WHERE id=?',('Alterada',item['id']))
                    elif change=='done':db.done([item['id']])
                    else:db.toggle(item['id'])
                    queued=[]
                    with self.assertRaisesRegex(RuntimeError,'mudou'):runtime.queue_selected(db,result.exception,queued.append)
                    self.assertEqual(queued,[])
                finally:db.close()

    def test_failed_queue_keeps_selected_items_without_retry(self):
        offer=self.offer();attempts=[]
        def fail(text):attempts.append(text);raise RuntimeError('indisponível')
        with self.assertRaises(RuntimeError):runtime.queue_selected(self.db,offer,fail)
        self.assertEqual(len(attempts),1)
        self.assertTrue(all(i['selected'] for i in self.db.items()))

    def test_concurrent_completion_waits_until_queue_acceptance(self):
        offer=self.offer();first=self.db.items()[0]['id']
        ready=threading.Event();attempt=threading.Event();finished=threading.Event();errors=[]
        def complete():
            other=Store(self.root/'state.db','test')
            try:
                ready.set();attempt.wait(3);other.done([first]);finished.set()
            except Exception as error:errors.append(error)
            finally:other.close()
        worker=threading.Thread(target=complete);worker.start();self.assertTrue(ready.wait(3))
        queued=[]
        def submit(text):
            attempt.set()
            self.assertFalse(finished.wait(.2),'item changed between validation and queue acceptance')
            queued.append(text)
        try:runtime.queue_selected(self.db,offer,submit)
        finally:attempt.set();worker.join(6)
        self.assertEqual(errors,[]);self.assertTrue(finished.is_set())
        self.assertEqual(len(queued),1)
        self.assertEqual([i['text'] for i in self.db.items()],['Segunda tarefa'])

    def test_confirmation_fits_narrow_panel_and_only_exposes_queue_or_cancel(self):
        build=getattr(ui_layout,'queue_confirmation_layout',None)
        self.assertIsNotNone(build)
        for width,height in ((18,12),(24,14),(60,24)):
            layout=build(width,height,2)
            self.assertEqual({t.action for t in layout.targets},{('key','1'),('key','2')})
            for t in layout.targets:
                self.assertEqual(layout.hit(t.x,t.y),t.action)
                self.assertLess(t.y,height-1)
            self.assertTrue(all(line.x+ui_layout.cell_width(line.text)<width for line in layout.lines))


class NativeQueueTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='left-undone-native-queue-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.sid='00000000-0000-4000-8000-000000000001'
        path=self.root/'sessions/2026/11/10';path.mkdir(parents=True)
        self.history=path/f'rollout-2026-11-10T18-00-00-{self.sid}.jsonl'
        self.history.write_text(json.dumps({'type':'session_meta','timestamp':'2026-11-10T18:00:00Z',
            'payload':{'id':self.sid,'timestamp':'2026-11-10T18:00:00Z','cwd':str(self.root),
                       'originator':'codex_cli_rs','cli_version':'0.167.0','source':'cli','model_provider':'openai'}})+'\n')
        self.binding=runtime.Binding('codex',self.sid,str(self.root),'w1:p1','term1','w1',str(self.history),1,'1')

    @unittest.skipUnless(shutil.which('codex'),'Codex CLI not installed')
    def test_real_cli_persists_exact_payload_in_verified_account_without_a_model(self):
        text='You left this undone: Teste literal $(touch /tmp/should-not-exist) `echo x`\nOutra tarefa'
        with patch.object(runtime,'verify',return_value={'agent_status':'working'}), \
             patch.dict(os.environ,{'CODEX_HOME':'/wrong/account','CODEX_THREAD_ID':'wrong-thread'}):
            runtime.queue(self.binding,text)
        with closing(sqlite3.connect(self.root/'queue_1.sqlite')) as db:
            rows=db.execute('SELECT thread_id,payload_json FROM queued_items').fetchall()
        self.assertEqual(len(rows),1);self.assertEqual(rows[0][0],self.sid)
        self.assertEqual(json.loads(rows[0][1])['UserInput']['content'][0]['text'],text)
        self.assertEqual(len(self.history.read_text().splitlines()),1)

    def test_identity_change_prevents_queue_submission(self):
        with patch.object(runtime,'verify',side_effect=RuntimeError('Vínculo mudou')):
            with self.assertRaisesRegex(RuntimeError,'Vínculo mudou'):runtime.queue(self.binding,'test')
        self.assertFalse((self.root/'queue_1.sqlite').exists())

    def test_claude_has_no_queue_fallback_to_typing_a_prompt(self):
        from dataclasses import replace
        with self.assertRaisesRegex(RuntimeError,'Claude'):runtime.queue(replace(self.binding,kind='claude'),'test')
        self.assertFalse((self.root/'queue_1.sqlite').exists())

    def test_failure_timeout_or_wrong_receipt_never_claims_success(self):
        for result in (subprocess.CompletedProcess([],1,'','failed'),
                       subprocess.CompletedProcess([],0,'Queued message x for another thread.',''),
                       subprocess.TimeoutExpired('codex',20)):
            with self.subTest(result=result):
                options={'side_effect':result} if isinstance(result,Exception) else {'return_value':result}
                with patch.object(runtime,'verify',return_value={'agent_status':'working'}), \
                     patch.object(runtime.subprocess,'run',**options):
                    with self.assertRaisesRegex(RuntimeError,'confirm'):runtime.queue(self.binding,'test')
