import tempfile
import unittest
from pathlib import Path
from left_undone.projects import ProjectStore

class ProjectViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'state.db'

    def store(self,s,p):
        db=ProjectStore(self.path,s,p);self.addCleanup(db.close);return db

    def test_view_changes_only_display_and_keeps_private_promises_in_own_project(self):
        a=self.store('a','/a');a.add('promise','Private A')
        b=self.store('b','/b');b.add('promise','Private B');b.import_md('- [ ] Shared B')
        view=a.view_project('/b');self.addCleanup(view.close)
        self.assertEqual([i['text'] for i in view.items()],['Shared B'])
        self.assertEqual(a.conn.execute('SELECT project FROM project_sessions WHERE session="a"').fetchone()[0],'/a')
        self.assertEqual(a.available_projects(),['/a','/b'])
        chosen=view.items()[0]['id'];view.toggle(chosen)
        self.assertEqual(view.items()[0]['selected'],1);self.assertEqual(b.items()[0]['selected'],0)
        self.assertEqual([i['text'] for i in a.items()],['Private A'])

    def test_history_excludes_open_and_retains_recorded_reason(self):
        a=self.store('a','/a');a.import_md('- [ ] Closed\n- [ ] Open');item=a.items()[0]
        a.done([item['id']]);a.note_closure(item['id'],'Concluída','Verified work')
        history=a.history_items()
        self.assertEqual([i['id'] for i in history],[item['id']])
        self.assertEqual(history[0]['closure_reason'],'Concluída')
        self.assertEqual(a.items()[0]['text'],'Open')
