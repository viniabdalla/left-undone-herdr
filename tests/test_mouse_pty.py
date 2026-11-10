"""Exercise ncurses' real SGR decoding and state changes in a terminal."""
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

class MousePTYTests(unittest.TestCase):
    def test_sgr_click_send_resize_and_keyboard_in_real_curses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);b=Binding('codex','mouse-test','/tmp','w0:p0','none','w0','none',1,'1')
            binding=root/'binding.json';binding.write_text(json.dumps(asdict(b)))
            db=Store(root/'state.db',b.key);self.addCleanup(db.close)
            db.add('import','A long task whose complete ending must remain visible after narrowing the panel')
            first=db.items()[0]['id'];sent=root/'sent.txt'
            script=root/'run.py'
            script.write_text('''import curses,json,sys
from pathlib import Path
from left_undone.runtime import Binding
from left_undone import ui
root=Path(sys.argv[1]);file=root/'binding.json'
def submit(binding,text):
 with (root/'sent.txt').open('a') as f:f.write(text+'\\n')
ui.send=submit
original=ui.MouseInput.event
def event(self,x,y,mask,layout):
 result=original(self,x,y,mask,layout)
 with (root/'mouse-events').open('a') as f:f.write(repr((x,y,mask,result))+'\\n')
 return result
ui.MouseInput.event=event
curses.wrapper(ui.panel,Binding(**json.loads(file.read_text())),root,file)
''')
            master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,40,0,0))
            env={**os.environ,'TERM':'xterm-256color','PYTHONPATH':str(Path.cwd()),'LEFT_UNDONE_STATE_DIR':tmp,'HERDR_ENV':'0'}
            env.pop('CODEX_THREAD_ID',None)
            p=subprocess.Popen([sys.executable,str(script),tmp],stdin=slave,stdout=slave,stderr=slave,env=env,start_new_session=True)
            os.close(slave);output=bytearray()
            def drain():
                while select.select([master],[],[],0)[0]:
                    try:output.extend(os.read(master,65536))
                    except OSError:break
            def wait_for(predicate):
                end=time.monotonic()+5
                while time.monotonic()<end:
                    drain()
                    if predicate():return
                    if p.poll() is not None:self.fail('UI exited: '+output.decode(errors='replace'))
                    time.sleep(.03)
                self.fail('Timed out: '+(root/'mouse-events').read_text() if (root/'mouse-events').exists() else output.decode(errors='replace')[-1800:])
            def click(x,y):os.write(master,f'\x1b[<0;{x};{y}M\x1b[<0;{x};{y}m'.encode())
            try:
                wait_for(lambda:b'1006' in output and b'LEFT UNDONE' in output)
                # First task occupies y=5 onward in one-based terminal coordinates.
                click(10,6)
                wait_for(lambda:db.items()[0]['selected']==1)
                wait_for(lambda:b'Enviar 1' in output)
                # At 40x30, selected action buttons occupy row 27.
                click(5,27)
                wait_for(lambda:sent.exists())
                wait_for(lambda:db.items()[0]['selected']==0)
                self.assertEqual(sent.read_text().count('You left this undone:'),1)
                self.assertEqual(len(db.items()),1)
                fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',30,24,0,0));os.kill(p.pid,signal.SIGWINCH)
                time.sleep(.15);drain()
                click(10,7)
                wait_for(lambda:db.items()[0]['selected']==1)
                # Keyboard completion remains compatible with mouse selection.
                os.write(master,b'2');wait_for(lambda:len(db.items())==0)
                os.write(master,b'\x1b');p.wait(timeout=5)
                self.assertEqual(p.returncode,0)
            finally:
                if p.poll() is None:p.terminate();p.wait(timeout=10)
                os.close(master)
