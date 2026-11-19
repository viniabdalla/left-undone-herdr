"""Real curses confirmation: cancelling preserves work and queueing needs a choice."""
import fcntl
import json
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from dataclasses import asdict
from pathlib import Path
from left_undone.core import Store
from left_undone.runtime import Binding


class QueuePTYTests(unittest.TestCase):
    def test_mouse_keyboard_cancel_and_failed_queue_preserve_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);binding=Binding('codex','queue-ui',tmp,'w0:p0','none','w0','none',1,'1')
            file=root/'binding.json';file.write_text(json.dumps(asdict(binding)))
            db=Store(root/'state.db',binding.key);self.addCleanup(db.close)
            db.add('import','First task');db.add('import','Second task')
            script=root/'ui.py'
            script.write_text('''import curses,json,sys
from pathlib import Path
from left_undone import ui
from left_undone.runtime import Binding,AgentBusy
root=Path(sys.argv[1]);file=root/'binding.json'
def send(binding,text):raise AgentBusy('busy')
def queue(binding,text):
 if (root/'fail').exists():raise RuntimeError('Queue failed in test')
 with (root/'queued').open('a') as f:f.write(json.dumps(text)+'\\n')
ui.send=send;ui.queue=queue
original=ui.render
def render(win,layout):
 original(win,layout)
 data={'lines':[line.text for line in layout.lines],
       'targets':[(t.x,t.y,t.action) for t in layout.targets]}
 temp=root/'screen.tmp';temp.write_text(json.dumps(data));temp.replace(root/'screen.json')
ui.render=render
curses.wrapper(ui.panel,Binding(**json.loads(file.read_text())),root,file)
''')
            master,slave=pty.openpty()
            fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,40,0,0))
            env={**os.environ,'TERM':'xterm-256color','PYTHONPATH':str(Path.cwd()),
                 'HERDR_ENV':'0','LEFT_UNDONE_STATE_DIR':tmp}
            env.pop('CODEX_THREAD_ID',None)
            p=subprocess.Popen([sys.executable,str(script),tmp],stdin=slave,stdout=slave,stderr=slave,env=env,start_new_session=True)
            os.close(slave);output=bytearray()
            def screen():
                try:return json.loads((root/'screen.json').read_text())
                except (OSError,ValueError):return {'lines':[],'targets':[]}
            def contains(text):return text in ' '.join(screen()['lines'])
            def wait_for(predicate):
                end=time.monotonic()+5
                while time.monotonic()<end:
                    while select.select([master],[],[],0)[0]:
                        try:output.extend(os.read(master,65536))
                        except OSError:break
                    if predicate():return
                    if p.poll() is not None:self.fail(output.decode(errors='replace')[-1600:])
                    time.sleep(.02)
                self.fail('Timed out: '+str(screen()))
            def key(value):os.write(master,value.encode())
            def click(action):
                x,y,_=next(t for t in screen()['targets'] if t[2]==list(action))
                os.write(master,f'\x1b[<0;{x+1};{y+1}M\x1b[<0;{x+1};{y+1}m'.encode())
            try:
                wait_for(lambda:contains('LEFT UNDONE'))
                self.assertTrue(contains('[9 Português]'))
                click(('key','9'));wait_for(lambda:contains('[9 English]'))
                self.assertTrue(contains('IMPORTADO ·'))
                key('9');wait_for(lambda:contains('[9 Português]'))
                rows=[line for line in screen()['lines'] if 'IMPORTED ·' in line]
                self.assertIn('Second task',rows[0])
                key('6');wait_for(lambda:contains('Oldest first'))
                rows=[line for line in screen()['lines'] if 'IMPORTED ·' in line]
                self.assertIn('First task',rows[0])
                key('a');wait_for(lambda:db.items()[0]['selected']==1)
                key('6');wait_for(lambda:contains('Newest first'))
                self.assertTrue(db.items()[0]['selected'])
                click(('key','6'));wait_for(lambda:contains('Oldest first'))
                self.assertTrue(db.items()[0]['selected'])
                wait_for(lambda:contains('Send 1'))
                click(('key','1'));wait_for(lambda:contains('AGENT BUSY'))
                self.assertFalse((root/'queued').exists())
                click(('key','2'));wait_for(lambda:contains('Send canceled'))
                self.assertEqual(len(db.items()),2);self.assertTrue(db.items()[0]['selected'])
                key('1');wait_for(lambda:contains('AGENT BUSY'))
                key('\x1b');wait_for(lambda:contains('LEFT UNDONE'))
                self.assertIsNone(p.poll());self.assertTrue(db.items()[0]['selected'])
                key('1');wait_for(lambda:contains('AGENT BUSY'))
                fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',8,40,0,0));os.kill(p.pid,signal.SIGWINCH)
                wait_for(lambda:contains('Enlarge the panel'))
                key('1');time.sleep(.15)
                self.assertFalse((root/'queued').exists(),'cannot confirm when the question is not visible')
                fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',30,40,0,0));os.kill(p.pid,signal.SIGWINCH)
                wait_for(lambda:contains('AGENT BUSY'));key('2');wait_for(lambda:contains('LEFT UNDONE'))
                key('1');wait_for(lambda:contains('AGENT BUSY'))
                click(('key','1'));wait_for(lambda:contains('Queued: 1'))
                self.assertFalse(db.items()[0]['selected']);self.assertEqual(len(db.items()),2)
                queued=[json.loads(line) for line in (root/'queued').read_text().splitlines()]
                self.assertEqual(queued,['You left this undone: First task'])
                key('b');wait_for(lambda:db.items()[1]['selected']==1)
                key('1');wait_for(lambda:contains('AGENT BUSY'))
                (root/'fail').touch();key('1');wait_for(lambda:contains('Queue failed'))
                self.assertTrue(db.items()[1]['selected'])
                self.assertEqual(len((root/'queued').read_text().splitlines()),1)
                (root/'fail').unlink();key('1');wait_for(lambda:contains('AGENT BUSY'))
                key('1');wait_for(lambda:not db.items()[1]['selected'])
                queued=[json.loads(line) for line in (root/'queued').read_text().splitlines()]
                self.assertEqual(queued,['You left this undone: First task','You left this undone: Second task'])
                for n in range(50):db.add('import',f'Extra task {n}')
                wait_for(lambda:contains('52 items'))
                click(('next',None));wait_for(lambda:' · 2/' in ' '.join(screen()['lines']))
                key('a');wait_for(lambda:contains('Send 1'))
                previous=next(line for line in screen()['lines'] if '52 items' in line)
                key('1');wait_for(lambda:contains('AGENT BUSY'))
                key('2');wait_for(lambda:contains('LEFT UNDONE'))
                self.assertIn(previous,screen()['lines'],'cancel must preserve the current list page')
                original={i['id'] for i in db.items()};chosen=next(i['id'] for i in db.items() if i['selected'])
                key('2');wait_for(lambda:contains('MARK TASKS COMPLETE'))
                self.assertEqual(len(db.items()),52)
                key('2');wait_for(lambda:contains('Completion canceled'))
                self.assertIn(previous,screen()['lines'])
                self.assertTrue(next(i for i in db.items() if i['id']==chosen)['selected'])
                key('2');wait_for(lambda:contains('MARK TASKS COMPLETE'))
                key('\x1b');wait_for(lambda:contains('LEFT UNDONE'));self.assertIsNone(p.poll())
                click(('key','2'));wait_for(lambda:contains('MARK TASKS COMPLETE'))
                fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',8,40,0,0));os.kill(p.pid,signal.SIGWINCH)
                wait_for(lambda:contains('Enlarge the panel'));key('1');time.sleep(.15)
                self.assertEqual(len(db.items()),52)
                fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',30,40,0,0));os.kill(p.pid,signal.SIGWINCH)
                wait_for(lambda:contains('MARK TASKS COMPLETE'))
                click(('key','1'));wait_for(lambda:len(db.items())==51)
                self.assertEqual({i['id'] for i in db.items()},original-{chosen})
                wait_for(lambda:contains('LEFT UNDONE'))
                # Adding action buttons reflows page 2; choose stable item IDs,
                # since the letter b may become the former a after that reflow.
                targets=list(dict.fromkeys(tuple(t[2]) for t in screen()['targets'] if t[2][0]=='item'))[:2]
                click(tuple(targets[0]));wait_for(lambda:contains('Send 1'))
                click(tuple(targets[1]));wait_for(lambda:contains('Send 2'))
                self.assertEqual(sum(i['selected'] for i in db.items()),2)
                key('2');wait_for(lambda:contains('MARK TASKS COMPLETE'))
                self.assertTrue(contains('2 items'));self.assertEqual(len(db.items()),51)
                key('1');wait_for(lambda:len(db.items())==49)
                self.assertFalse(any(i['selected'] for i in db.items()))
                key('\x1b');p.wait(timeout=5);self.assertEqual(p.returncode,0)
            finally:
                if p.poll() is None:p.terminate();p.wait(timeout=10)
                os.close(master)
