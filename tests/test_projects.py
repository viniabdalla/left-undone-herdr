import tempfile
import unittest
from pathlib import Path

from left_undone.core import Store
from left_undone.projects import ProjectStore
from left_undone.curation import Curator


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.db'

    def view(self, session, project='project-a'):
        store = ProjectStore(self.path, session, project)
        self.addCleanup(store.close)
        return store

    def test_tasks_promises_and_imports_are_session_private(self):
        a = self.view('a')
        a.import_md('- [ ] Checklist')
        a.add('task', 'Native task', '1')
        a.add('promise', 'Private promise', 'p')
        for other in (self.view('b'), self.view('c', 'project-c')):
            self.assertEqual(other.items(), [])
            for item in a.items():
                other.toggle(item['id'])
                other.done([item['id']])
            self.assertEqual(other.history_items(), [])
        self.assertEqual(len(a.items()), 3)
        self.assertFalse(any(i['selected'] for i in a.items()))

    def test_import_tombstones_and_duplicate_text_are_private(self):
        a = self.view('a')
        a.import_md('- [ ] Repeated')
        a.done([a.items()[0]['id']])
        self.assertEqual(a.import_md('- [ ] Repeated'), 0)
        b = self.view('b')
        self.assertEqual(b.import_md('- [ ] Repeated'), 1)
        self.assertEqual(b.import_md('- [ ] Repeated'), 0)
        self.assertEqual(len(b.items()), 1)
        self.assertEqual(len(a.history_items()), 1)
        self.assertEqual(b.history_items(), [])

    def test_automatic_discovery_cannot_replace_existing_project_assignment(self):
        self.view('a', 'explicit-project').import_md('- [ ] Keep here')
        stale = self.view('a', 'stale-project')
        self.assertEqual(stale.project, 'explicit-project')
        self.assertEqual(stale.items()[0]['text'], 'Keep here')
        self.assertEqual(self.view('b', 'explicit-project').items(), [])

    def test_legacy_owner_is_restored_only_when_creation_audit_identifies_it(self):
        a = self.view('a')
        legacy = Store(self.path, a.owner)
        self.addCleanup(legacy.close)
        legacy.add('task', 'Curated in A', 'curator:event')
        legacy.add('import', 'Unknown importer', 'unknown')
        known, unknown = legacy.items()
        Curator(a, None)
        with a.conn:
            a.conn.execute("INSERT INTO curation_changes(project,session,action,item) VALUES(?,?,'add',?)",
                           (a.project, 'a', known['id']))
            a.conn.execute('INSERT INTO project_selections VALUES(?,?)', ('a', known['id']))
        self.assertEqual(self.view('b').items(), [])
        own_items = self.view('a').items()
        self.assertEqual([(r['id'], r['selected']) for r in own_items], [(known['id'], 1)])
        self.assertEqual([r['id'] for r in legacy.items()], [unknown['id']])

    def test_organization_audit_restores_original_session_even_if_import_source_was_reused(self):
        import json
        from left_undone.organization import organize_items

        a = self.view('a')
        a.add('import', 'Newer private import', 'same-source')
        existing = a.items()[0]
        legacy = Store(self.path, a.owner)
        self.addCleanup(legacy.close)
        legacy.add('import', 'Earlier import', 'same-source')
        earlier = legacy.items()[0]
        legacy.done([earlier['id']])
        organize_items(a, [], 'setup')
        with a.conn:
            a.conn.execute('INSERT INTO panel_organization(event,item,before_json,after_json,evidence) VALUES(?,?,?,?,?)',
                           ('original-move', earlier['id'], json.dumps({'session': 'a'}), '{}', 'old audit'))
        restored = self.view('a')
        self.assertEqual([i['id'] for i in restored.items()], [existing['id']])
        self.assertEqual([i['id'] for i in restored.history_items()], [earlier['id']])
        self.assertEqual(self.view('b').history_items(), [])

    def test_legacy_session_rows_keep_ids_selection_and_tombstones(self):
        native = Store(self.path, 'a')
        self.addCleanup(native.close)
        native.import_md('- [ ] Remains open\n- [ ] Done')
        first, second = native.items()
        native.toggle(first['id'])
        native.done([second['id']])
        a = self.view('a')
        self.assertEqual([(r['id'], r['selected']) for r in a.items()], [(first['id'], 1)])
        self.assertEqual([r['id'] for r in a.history_items()], [second['id']])
        self.assertEqual(a.import_md('- [ ] Done'), 0)
        self.assertEqual(self.view('b').items(), [])

    def test_checklist_import_is_distinct_from_same_text_promise(self):
        a = self.view('a')
        a.add('promise', 'Same text')
        self.assertEqual(a.import_md('- [ ] Same text'), 1)
        self.assertEqual({i['origin'] for i in a.items()}, {'promise', 'import'})
        self.assertEqual(self.view('b').items(), [])

    def test_native_completion_and_late_toggle_cannot_leave_reopened_item_selected(self):
        a = self.view('a')
        a.add('task', 'Native task', '1')
        item = a.items()[0]['id']
        a.toggle(item)
        a.commit_line({}, [{'id': 'finish', 'kind': 'snapshot', 'tasks': []}], {})
        a.toggle(item)
        a.commit_line({}, [{'id': 'reopen', 'kind': 'upsert',
                            'tasks': [{'source': '1', 'text': 'Active again', 'status': 'pending'}]}], {})
        self.assertEqual([(i['id'], i['selected']) for i in a.items()], [(item, 0)])
