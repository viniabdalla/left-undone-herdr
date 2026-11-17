import tempfile
import unittest
from pathlib import Path
from left_undone.projects import ProjectStore

class OrganizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=ProjectStore(Path(self.tmp.name)/'state.db','viewer','/old');self.addCleanup(self.db.close)
        self.db.import_md('- [ ] Old title\n- [ ] Already done')

    def change(self,item,**kwargs):
        return {'expected':{k:item[k] for k in ('id','session','origin','source','text','status')},'project':'/new','evidence':'Reviewed task and scope',**kwargs}

    def organizer(self):
        from left_undone.organization import organize_items
        return organize_items

    def test_atomic_move_preserves_identity_history_reason_and_source_date(self):
        a,b=self.db.items();source=a['source']
        changes=[self.change(a,text='Readable: same task',created_at=1234,evidence='Exact source event timestamp'),
                 self.change(b,reason='Concluída',evidence='Verified implementation')]
        result=self.organizer()(self.db,changes,'test-event',associate='/new')
        self.assertEqual(result,2)
        self.assertEqual(self.organizer()(self.db,changes,'test-event',associate='/new'),0)
        view=self.db.view_project('/new');self.addCleanup(view.close)
        item=view.items()[0];self.assertEqual(item['id'],a['id']);self.assertEqual(item['source'],source)
        # A proved existing creation date must never be replaced during organization.
        self.assertEqual(item['created_at'],a['created_at'])
        self.assertEqual(view.history_items()[0]['closure_reason'],'Concluída')
        self.assertEqual(view.conn.execute('SELECT count(*) FROM panel_organization').fetchone()[0],2)
        self.assertEqual(view.conn.execute('SELECT project FROM project_sessions WHERE session="viewer"').fetchone()[0],'/new')

    def test_stale_snapshot_rolls_back_every_change(self):
        a,b=self.db.items();changes=[self.change(a,text='Changed: description'),self.change(b,reason='Duplicada',evidence='Same obligation')]
        changes[1]['expected']['text']='stale'
        with self.assertRaisesRegex(RuntimeError,'mudou'):self.organizer()(self.db,changes,'stale')
        self.assertEqual([i['text'] for i in self.db.items()],['Old title','Already done'])
        self.assertEqual(self.db.conn.execute('SELECT project FROM project_sessions WHERE session="viewer"').fetchone()[0],'/old')

    def test_private_promises_cannot_be_moved_between_projects(self):
        self.db.add('promise','Private')
        private=next(i for i in self.db.items() if i['origin']=='promise')
        with self.assertRaisesRegex(ValueError,'privad'):self.organizer()(self.db,[self.change(private)],'private')

    def test_legacy_import_selection_survives_becoming_shared(self):
        self.db.add('import','Legacy import','native')
        item=next(i for i in self.db.items() if i['source']=='native')
        self.db.toggle(item['id'])
        self.organizer()(self.db,[self.change(item)],'selection')
        view=self.db.view_project('/new');self.addCleanup(view.close)
        self.assertEqual(view.items()[0]['selected'],1)

    def test_collector_native_tasks_are_not_moved_or_reopened_by_aliasing(self):
        self.db.add('task','Native task','tool-1')
        item=next(i for i in self.db.items() if i['source']=='tool-1')
        with self.assertRaisesRegex(ValueError,'nativas'):
            self.organizer()(self.db,[self.change(item)],'native')
        self.assertEqual(next(i['session'] for i in self.db.items() if i['source']=='tool-1'),'viewer')
