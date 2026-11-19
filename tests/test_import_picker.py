import curses
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from left_undone import ui
from left_undone.language import load_language
from left_undone.ui_layout import import_layout
from test_readable_ui import Window, Worker
from left_undone.projects import ProjectStore
from left_undone.runtime import Binding


class ImportPickerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        load_language(self.root)
        self.choices = [
            {'id': str(i), 'text': f'Task {i}', 'imported': i == 0} for i in range(31)
        ]

    def test_keyboard_paging_keeps_only_explicit_available_selections(self):
        window = Window(['1', 'a', 'b', curses.KEY_RIGHT, 'c', '1'])
        self.assertEqual(ui.pick_imports(window, self.choices, '/project'), ['1', '28'])
        self.assertIn('0 selected', window.frames[0])
        self.assertIn('Already imported · Task 0', window.frames[0])
        self.assertIn('[1 Import 2]', window.frames[-1])

    def test_click_and_escape_cancel_without_importing(self):
        window = Window([curses.KEY_MOUSE, '\x1b'])
        layout = import_layout(self.choices, set(), 80, 40, 0, '/project')
        self.assertNotIn(('item', '0'), [t.action for t in layout.targets])
        hit = next(t for t in layout.targets if t.action == ('item', '2'))
        with patch('left_undone.ui.curses.getmouse', return_value=(0, hit.x, hit.y, 0, curses.BUTTON1_CLICKED)):
            self.assertIsNone(ui.pick_imports(window, self.choices, '/project'))
        self.assertIn('[1 Import 1]', window.frames[-1])

    def test_export_from_one_panel_and_import_one_checked_copy_in_another(self):
        project = self.root / 'project'
        project.mkdir()
        for session in ('source', 'destination'):
            binding = Binding('codex', session, str(self.root), 'w0:p0', 'none', 'w0', 'none', 1, '1')
            store = ProjectStore(self.root/'state.db', binding.key, project)
            self.addCleanup(store.close)
            if session == 'source':
                store.add('task', 'First')
                store.add('promise', 'Second')
                keys = ['3', '\x1b']
            else:
                self.assertEqual(store.items(), [])
                keys = ['4', 'b', '1', '4', '\x1b', '\x1b']
            window = Window(keys)
            with patch.object(ui, 'subprocess', Mock(Popen=Mock(return_value=Worker()))):
                ui.panel(window, binding, self.root, self.root/'binding.json')
        self.assertEqual([item['text'] for item in store.items()], ['Second'])
        self.assertIn('Already imported · Second', window.frames[-2])

    def test_project_switch_export_import_and_failure_leave_session_linked(self):
        binding = Binding('codex', 'linked', str(self.root), 'w0:p0', 'none', 'w0', 'none', 1, '1')
        db = ProjectStore(self.root/'state.db', binding.key, '/a')
        self.addCleanup(db.close)
        other = ProjectStore(self.root/'state.db', 'other', '/b')
        self.addCleanup(other.close)
        other.add('task', 'Not exported')
        keys = ['8', curses.KEY_DOWN, '\n', '3', '4', 'b', '\x1b', '4', 'b', '1', '4', '\x1b']
        window = Window(keys)
        path = self.root/'tasks.json'
        with patch.object(ui.subprocess, 'Popen', return_value=Worker()), \
             patch.object(ui, 'export_project', return_value=path) as export, \
             patch.object(ui, 'import_choices', side_effect=[self.choices, self.choices, ValueError('Invalid file')]), \
             patch.object(ui, 'import_selected', return_value=1) as confirm:
            ui.panel(window, binding, self.root, self.root/'binding.json')
        target, project = export.call_args.args
        self.assertEqual((target.session, target.project, project), (binding.key, '/a', '/b'))
        confirm.assert_called_once_with(target, ['1'], '/b')
        frames = '\n'.join(window.frames)
        for message in (str(path), 'Import canceled.', 'Imported: 1', 'Invalid file'):
            self.assertIn(message, frames)
        self.assertNotIn('Not exported', frames)
