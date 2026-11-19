import hashlib
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from left_undone.core import Store
from left_undone.exchange import export_project, import_choices, import_selected


class ExchangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.a = self.store('codex-A')
        self.b = self.store('claude-B')

    def store(self, session):
        store = Store(self.root / 'state.db', session)
        store.project = self.project
        self.addCleanup(store.close)
        return store

    def test_publish_pick_complete_publish_and_stale_export(self):
        self.a.add('task', 'First')
        self.a.add('promise', 'Second')
        self.assertEqual(import_choices(self.b), [])
        path = export_project(self.a)
        self.assertEqual(path, self.project / '.left-undone' / 'tasks.md')
        self.assertEqual(self.b.items(), [])
        first, second = import_choices(self.b)
        self.assertTrue(all(c['imported'] for c in import_choices(self.a)))
        self.assertEqual(import_selected(self.b, [second['id'], second['id']]), 1)
        self.assertEqual([r['text'] for r in self.b.items()], ['Second'])
        self.assertEqual(import_selected(self.b, [second['id']]), 0)
        self.b.done([self.b.items()[0]['id']])
        self.assertEqual(import_selected(self.b, [second['id']]), 0)
        self.assertEqual(len(import_choices(self.a)), 2)
        export_project(self.b)
        self.assertEqual([c['id'] for c in import_choices(self.a)], [first['id']])
        self.assertEqual(len(self.a.items()), 2)
        export_project(self.a)
        self.assertEqual(import_choices(self.b), [first])
        self.assertEqual(import_selected(self.b, [second['id']]), 0)
        self.assertNotIn('Second', path.read_text())

    def test_empty_export_preserves_file_and_unknown_format_is_safe(self):
        self.a.add('task', 'Original')
        path = export_project(self.a)
        standalone = 'Intro\n' + path.read_text() + 'Outro\n'
        path.write_text(standalone)
        export_project(self.b)
        self.assertEqual(path.read_text(), standalone)
        path.write_text('# User notes\n- [ ] Unknown\n')
        with self.assertRaises(ValueError):
            export_project(self.b)
        self.assertEqual(path.read_text(), '# User notes\n- [ ] Unknown\n')

    def test_revalidate_checked_items_and_preserve_distinct_project_files(self):
        self.a.add('task', 'Change me')
        path = export_project(self.a)
        choice, = import_choices(self.b)
        path.write_text(path.read_text().replace('- [ ] Change me', '- [x] Change me'))
        self.assertEqual(import_selected(self.b, [choice['id']]), 0)
        other = self.root / 'other'
        other.mkdir()
        self.assertEqual(import_choices(self.b, other), [])

    def test_linked_git_worktrees_have_separate_exchanges(self):
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True)
        git = ['git', '-C', str(self.project)]
        subprocess.run(git + ['-c', 'user.name=test', '-c', 'user.email=test@example.invalid',
                              'commit', '--allow-empty', '-qm', 'fixture'], check=True)
        second = self.root / 'worktree'
        subprocess.run(git + ['worktree', 'add', '--detach', '-q', str(second)], check=True)
        nested = self.project / 'src'
        nested.mkdir()
        self.a.add('task', 'Main task')
        path = export_project(self.a, nested)
        self.assertEqual(path.parent.parent, self.project)
        self.assertEqual(import_choices(self.b, second), [])
        self.b.add('promise', 'Worktree promise')
        export_project(self.b, second)
        self.assertEqual([r['text'] for r in import_choices(self.b)], ['Main task'])
        self.assertEqual([r['text'] for r in import_choices(self.a, second)], ['Worktree promise'])

    def test_legacy_unattributed_rows_require_explicit_copy(self):
        owner = 'project:' + hashlib.sha256(str(self.project).encode()).hexdigest()
        legacy = self.store(owner)
        legacy.add('import', 'Old shared task')
        self.assertEqual(self.b.items(), [])
        old, = import_choices(self.b)
        self.assertFalse(old['imported'])
        self.assertEqual(import_selected(self.b, [old['id']]), 1)
        self.b.done([self.b.items()[0]['id']])
        export_project(self.b)
        self.assertEqual(import_choices(self.a), [])
        self.assertEqual([r['text'] for r in legacy.items()], ['Old shared task'])

    def test_parallel_exports_merge_and_duplicate_imports_are_idempotent(self):
        for name in ('codex-A', 'claude-B'):
            self.store(name).add('task', name)
        barrier = threading.Barrier(2)

        def publish(name):
            store = Store(self.root / 'state.db', name)
            try:
                barrier.wait(timeout=5)
                export_project(store, self.project)
            finally:
                store.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(publish, ['codex-A', 'claude-B']))
        choices = import_choices(self.a)
        self.assertEqual({r['text'] for r in choices}, {'codex-A', 'claude-B'})
        keys = [r['id'] for r in choices]

        def pick(_):
            store = Store(self.root / 'state.db', 'new')
            try:
                barrier.wait(timeout=5)
                return import_selected(store, keys, self.project)
            finally:
                store.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(pick, range(2))), [0, 2])
        self.assertEqual(len(self.store('new').items()), 2)
