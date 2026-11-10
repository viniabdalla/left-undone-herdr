import tempfile
import unittest
from pathlib import Path
from left_undone.core import Store
from left_undone.ui import page_items, handle_key

class UITests(unittest.TestCase):
    def test_selection_send_done_export_import_and_paging(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Store(Path(tmp)/'state.db','s');self.addCleanup(db.close)
            for n in range(30):db.add('promise',f'Task {n}')
            self.assertEqual(len(page_items(db.items(),0,10)),10)
            self.assertEqual(page_items(db.items(),2,10)[0]['text'],'Task 20')
            sent=[];export=Path(tmp)/'latest.md'
            visible=page_items(db.items(),0,10)
            handle_key('a',db,visible,sent.append,export)
            self.assertEqual(db.items()[0]['selected'],1)
            handle_key('1',db,visible,sent.append,export)
            self.assertEqual(len(sent),1);self.assertEqual(len(db.items()),30)
            handle_key('b',db,visible,sent.append,export)
            handle_key('2',db,visible,sent.append,export)
            self.assertEqual(len(db.items()),29)
            handle_key('3',db,visible,sent.append,export)
            self.assertTrue(export.read_text().startswith('# Left undone'))
            handle_key('4',db,visible,sent.append,export)
            self.assertEqual(len(db.items()),29)

    def test_external_signal_stops_collector(self):
        import json,os,pty,subprocess,sys,time
        from dataclasses import asdict
        from left_undone.runtime import Binding
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binding=root/'binding.json'
            binding.write_text(json.dumps(asdict(Binding('codex','test','/tmp','w0:p0','none','w0','none',1,'1'))))
            master,slave=pty.openpty()
            env={**os.environ,'TERM':'xterm','HERDR_ENV':'0','LEFT_UNDONE_STATE_DIR':tmp}
            p=subprocess.Popen([sys.executable,'left-undone','panel','--binding',str(binding)],stdin=slave,stdout=slave,stderr=slave,env=env)
            os.close(slave);worker=None
            try:
                for _ in range(100):
                    children=Path(f'/proc/{p.pid}/task/{p.pid}/children').read_text().split()
                    if children:worker=int(children[0]);break
                    time.sleep(.02)
                self.assertIsNotNone(worker)
                time.sleep(.2)
                p.terminate();p.wait(timeout=10)
                self.assertFalse(Path(f'/proc/{worker}').exists(),'coletor sobreviveu à UI')
            finally:
                if p.poll() is None:p.kill();p.wait()
                if worker and Path(f'/proc/{worker}').exists():
                    try:os.kill(worker,9)
                    except ProcessLookupError:pass
                os.close(master)
