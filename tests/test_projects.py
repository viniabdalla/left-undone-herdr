import tempfile
import threading
import unittest
from pathlib import Path

from left_undone.core import Store


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.db'

    def view(self, session, project='project-a'):
        from left_undone.projects import ProjectStore
        store = ProjectStore(self.path, session, project)
        self.addCleanup(store.close)
        return store

    def test_project_tasks_survive_new_session_but_promises_remain_private(self):
        a = self.view('codex-a')
        a.import_md('- [ ] Shared checklist')
        native = Store(self.path, 'codex-a');self.addCleanup(native.close)
        native.add('task', 'Native task', '1')
        native.add('promise', 'Private promise', 'p')
        b = self.view('claude-b')
        self.assertEqual({i['text'] for i in b.items()}, {'Shared checklist', 'Native task'})
        self.assertEqual(len(a.items()), 3)
        self.assertEqual(self.view('other', 'project-b').items(), [])

    def test_selection_is_private_and_completion_is_shared(self):
        a = self.view('a');b = self.view('b')
        a.import_md('- [ ] Shared')
        item = a.items()[0]['id']
        a.toggle(item)
        self.assertEqual(a.items()[0]['selected'], 1)
        self.assertEqual(b.items()[0]['selected'], 0)
        b.done([item])
        self.assertEqual(a.items(), [])
        self.assertEqual(b.items(), [])
        self.assertEqual(b.import_md('- [ ] Shared'), 0)

    def test_legacy_rows_selection_and_tombstones_are_preserved(self):
        legacy = Store(self.path, 'a');self.addCleanup(legacy.close)
        legacy.import_md('- [ ] Existing\n- [ ] Done')
        first, second = legacy.items()
        legacy.toggle(first['id']);legacy.done([second['id']])
        a = self.view('a');b = self.view('b')
        self.assertEqual(a.items()[0]['id'], first['id'])
        self.assertEqual(a.items()[0]['selected'], 1)
        self.assertEqual(b.items()[0]['selected'], 0)
        self.assertEqual(b.import_md('- [ ] Existing\n- [ ] Done'), 0)
        b.done([first['id']])
        self.assertEqual(legacy.items(), [])

    def test_other_project_and_private_promise_cannot_be_changed_by_id(self):
        a = self.view('a');a.import_md('- [ ] Shared')
        other = self.view('other', 'other-project');other.import_md('- [ ] Isolated')
        native = Store(self.path, 'a');self.addCleanup(native.close)
        native.add('promise', 'Private')
        b = self.view('b')
        private = next(i['id'] for i in a.items() if i['origin'] == 'promise')
        ids = [other.items()[0]['id'], private]
        b.done(ids)
        for item in ids:b.toggle(item)
        self.assertEqual(other.items()[0]['selected'], 0)
        self.assertEqual(len(a.items()), 2)

    def test_native_snapshot_is_scoped_and_completion_clears_other_selections(self):
        a = self.view('a');b = self.view('b')
        native_a = Store(self.path, 'a');native_b = Store(self.path, 'b')
        self.addCleanup(native_a.close);self.addCleanup(native_b.close)
        native_a.add('task', 'A', '1');native_b.add('task', 'B', '1')
        item = next(i['id'] for i in b.items() if i['text'] == 'A')
        b.toggle(item)
        native_a.commit_line({}, [{'id': 'finish', 'kind': 'snapshot', 'tasks': []}], {})
        self.assertEqual([i['text'] for i in b.items()], ['B'])
        native_a.commit_line({}, [{'id': 'reopen', 'kind': 'upsert',
            'tasks': [{'source': '1', 'text': 'A', 'status': 'pending'}]}], {})
        self.assertEqual(next(i['selected'] for i in b.items() if i['text'] == 'A'), 0)

    def test_reopening_and_repeated_import_do_not_duplicate(self):
        self.view('a').import_md('- [ ] One')
        b = self.view('b')
        self.assertEqual(b.import_md('- [ ] One'), 0)
        self.assertEqual([i['text'] for i in self.view('new').items()], ['One'])
        self.assertIn('- [ ] One', b.export_md())

    def test_private_promise_does_not_swallow_shared_checklist_import(self):
        native = Store(self.path, 'a');self.addCleanup(native.close)
        native.add('promise', 'Same text')
        a = self.view('a')
        self.assertEqual(a.import_md('- [ ] Same text'), 1)
        self.assertEqual(self.view('b').items()[0]['text'], 'Same text')

    def test_automatic_discovery_cannot_replace_existing_project_assignment(self):
        self.view('a', 'explicit-project').import_md('- [ ] Keep here')
        stale = self.view('a', 'stale-project')
        self.assertEqual(stale.project, 'explicit-project')
        self.assertEqual(self.view('b', 'explicit-project').items()[0]['text'], 'Keep here')

    def test_completion_racing_selection_cannot_resurrect_selection(self):
        a = self.view('a');b = self.view('b')
        native = Store(self.path, 'a');self.addCleanup(native.close)
        native.add('task', 'Concurrent', '1')
        item = b.items()[0]['id']
        finished = threading.Event();errors = []
        def complete():
            try:
                db = Store(self.path, 'a')
                try:db.commit_line({}, [{'id': 'finish', 'kind': 'snapshot', 'tasks': []}], {})
                finally:db.close()
            except Exception as error:errors.append(error)
            finally:finished.set()
        workers = []
        def on_query(sql):
            if sql.startswith('SELECT session FROM items') and not workers:
                worker = threading.Thread(target=complete);workers.append(worker);worker.start()
                finished.wait(.5)
        b.conn.set_trace_callback(on_query)
        try:b.toggle(item)
        finally:
            b.conn.set_trace_callback(None)
            for worker in workers:worker.join(7)
        self.assertEqual(errors, [])
        self.assertTrue(finished.is_set())
        native.commit_line({}, [{'id': 'reopen', 'kind': 'upsert',
            'tasks': [{'source': '1', 'text': 'Concurrent', 'status': 'pending'}]}], {})
        self.assertEqual(b.items()[0]['selected'], 0)
