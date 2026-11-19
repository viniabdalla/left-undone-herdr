import curses
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch
from left_undone.projects import ProjectStore
from left_undone.runtime import Binding
from left_undone import ui
from left_undone.language import load_language


class Worker:
    pid=999999999
    def poll(self):return None
    def terminate(self):pass
    def wait(self,timeout):return 0


class Window:
    def __init__(self,keys):
        self.frames=[];self.lines=[]
        self.keys=iter(keys)
    def keypad(self,value):pass
    def timeout(self,value):pass
    def getmaxyx(self):return 40,80
    def erase(self):self.lines=[]
    def addstr(self,y,x,text,attr):self.lines.append(text)
    def refresh(self):self.frames.append('\n'.join(self.lines))
    def get_wch(self):return next(self.keys)

class ReadableUITests(unittest.TestCase):
    def test_handoff_confirmation_survives_reload_and_enter_or_cancel(self):
        from left_undone.renewal import journal
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            binding=Binding('codex','old',folder,'pane','term','ws','log',1,'1')
            store=ProjectStore(root/'state.db',binding.key,folder)
            self.addCleanup(store.close)
            store.add('task','Carry this task')
            for key in ('\n','h','\x1b'):
                path=journal(root,binding)
                path.write_text(json.dumps(dict(stage='confirm',active='new',selection=[],approval='stale')))
                window=Window(['a',key,'\x1b'])
                worker=Mock()
                worker.poll.return_value=None
                with patch.object(ui.subprocess,'Popen',return_value=worker) as launch:
                    ui.panel(window,binding,root,root/'binding.json')
                self.assertIn('[H Confirm handoff]',window.frames[0])
                self.assertIn('new tab?',window.frames[0])
                self.assertIn('1 item',window.frames[1])
                if key=='\x1b':
                    self.assertFalse(path.exists())
                    self.assertEqual(launch.call_count,1)
                else:
                    approval=json.loads(path.read_text())['approval']
                    self.assertNotEqual(approval,'stale')
                    self.assertEqual(launch.call_args.args[0][-2:],['--confirm-source',approval])

    def test_history_and_project_navigation_preserve_binding_and_scoped_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);binding=Binding('codex','test',folder,'w0:p0','none','w0','none',1,'1')
            a=ProjectStore(root/'state.db',binding.key,'/a');self.addCleanup(a.close)
            b=ProjectStore(root/'state.db','other','/b');self.addCleanup(b.close)
            a.import_md('- [ ] Task A: detail A');b.import_md('- [ ] Task B: detail B')
            file=root/'binding.json';file.write_text(json.dumps(asdict(binding)))
            window=Window(['a','7','7','8',curses.KEY_DOWN,'\n','1','\x1b']);sent=[]
            with patch('left_undone.ui.subprocess.Popen',return_value=Worker()),patch('left_undone.ui.send',side_effect=lambda binding,text:sent.append((binding.session,text))):
                ui.panel(window,binding,root,file)
            self.assertTrue(any('HISTORY' in f for f in window.frames))
            self.assertTrue(any('Choose exchange project' in f for f in window.frames))
            self.assertEqual(sent,[('test','You left this undone: Task A: detail A')])
            self.assertFalse(a.items()[0]['selected'])
            self.assertFalse(any('Task B' in frame for frame in window.frames))
            self.assertIn('[8 Exchange project: b]', window.frames[-1])
            self.assertEqual(a.conn.execute('SELECT project FROM project_sessions WHERE session=?',(binding.key,)).fetchone()[0],'/a')

    def test_language_toggle_persists_and_preserves_legacy_task_and_shortcuts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binding = Binding('codex','legacy',folder,'w0:p0','none','w0','none',1,'1')
            file = root/'binding.json'
            file.write_text(json.dumps(asdict(binding)))
            store = ProjectStore(root/'state.db', binding.key, '/project')
            self.addCleanup(store.close)
            legacy = 'VOCÊ · Conferir fatura: validar o valor original.'
            store.import_md('- [ ] ' + legacy)
            window = Window(['a','9','\x1b'])
            reopened = Window(['9','\x1b'])
            with patch('left_undone.ui.subprocess.Popen', return_value=Worker()):
                ui.panel(window, binding, root, file)
                # Simulate a fresh process's English default before reopening.
                load_language(root/'fresh')
                ui.panel(reopened, binding, root, file)

            for frame, section, switch in (
                (window.frames[0], 'For you · 1', '[9 Português]'),
                (window.frames[-1], 'PARA VOCÊ · 1', '[9 English]'),
                (reopened.frames[0], 'PARA VOCÊ · 1', '[9 English]'),
                (reopened.frames[-1], 'For you · 1', '[9 Português]'),
            ):
                self.assertIn(switch, frame)
                self.assertIn(section, frame)
                human_tasks = frame.split(section, 1)[1]
                self.assertIn('Conferir fatura', human_tasks)
                self.assertIn('validar o valor original.', human_tasks)
            self.assertIn('[1 Enviar 1]', reopened.frames[0])
            self.assertIn('[1 Send 1]', reopened.frames[-1])
            self.assertEqual(store.items()[0]['text'], legacy)
            self.assertTrue(store.items()[0]['selected'])

    def test_picker_refreshes_conversation_details_when_language_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binding = Binding('codex','example',folder,'w0:p0','none','w0','none',1,'1')
            window = Window(['9','9','\n'])
            chosen = []
            with patch.object(ui, 'preference_root', return_value=root):
                ui.picker(window, [binding], [], chosen.append, counts={binding.key: 2})
            en, pt, back = window.frames
            self.assertIn('Untitled in Herdr', en)
            self.assertIn('2 open tasks', en)
            self.assertIn('Sem título no Herdr', pt)
            self.assertIn('2 pendências', pt)
            self.assertEqual(en, back)
            self.assertEqual(chosen, [binding])
