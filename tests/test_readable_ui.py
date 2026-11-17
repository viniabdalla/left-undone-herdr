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

class ReadableUITests(unittest.TestCase):
    def test_history_and_project_navigation_preserve_binding_and_scoped_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);binding=Binding('codex','test',folder,'w0:p0','none','w0','none',1,'1')
            a=ProjectStore(root/'state.db',binding.key,'/a');self.addCleanup(a.close)
            b=ProjectStore(root/'state.db','other','/b');self.addCleanup(b.close)
            a.import_md('- [ ] Task A: detail A');b.import_md('- [ ] Task B: detail B')
            file=root/'binding.json';file.write_text(json.dumps(asdict(binding)))
            class Worker:
                pid=999999999
                def poll(self):return None
                def terminate(self):pass
                def wait(self,timeout):return 0
            class Window:
                def __init__(self):
                    self.frames=[];self.lines=[]
                    self.keys=iter(['a','7','7','8',curses.KEY_DOWN,'\n','a','1','\x1b'])
                def keypad(self,value):pass
                def timeout(self,value):pass
                def getmaxyx(self):return 40,80
                def erase(self):self.lines=[]
                def addstr(self,y,x,text,attr):self.lines.append(text)
                def refresh(self):self.frames.append('\n'.join(self.lines))
                def get_wch(self):return next(self.keys)
            window=Window();sent=[]
            with patch('left_undone.ui.subprocess.Popen',return_value=Worker()),patch('left_undone.ui.send',side_effect=lambda binding,text:sent.append((binding.session,text))):
                ui.panel(window,binding,root,file)
            self.assertTrue(any('HISTÓRICO' in f for f in window.frames))
            self.assertTrue(any('Escolha projeto' in f for f in window.frames))
            self.assertEqual(sent,[('test','You left this undone: Task B: detail B')])
            self.assertEqual(a.items()[0]['selected'],1)
            self.assertEqual(a.conn.execute('SELECT project FROM project_sessions WHERE session=?',(binding.key,)).fetchone()[0],'/a')
