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
            db.add('import','Primeira tarefa');db.add('import','Segunda tarefa')
            script=root/'ui.py'
            script.write_text('''import curses,json,sys
from pathlib import Path
from left_undone import ui
from left_undone.runtime import Binding,AgentBusy
root=Path(sys.argv[1]);file=root/'binding.json'
def send(binding,text):raise AgentBusy('busy')
def queue(binding,text):
 if (root/'fail').exists():raise RuntimeError('Fila não confirmada no teste')
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
                key('a');wait_for(lambda:db.items()[0]['selected']==1)
                wait_for(lambda:contains('Enviar 1'))
                click(('key','1'));wait_for(lambda:contains('AGENTE OCUPADO'))
                self.assertFalse((root/'queued').exists())
                click(('key','2'));wait_for(lambda:contains('Envio cancelado'))
                self.assertEqual(len(db.items()),2);self.assertTrue(db.items()[0]['selected'])
                key('1');wait_for(lambda:contains('AGENTE OCUPADO'))
                key('\x1b');wait_for(lambda:contains('LEFT UNDONE'))
                self.assertIsNone(p.poll());self.assertTrue(db.items()[0]['selected'])
                key('1');wait_for(lambda:contains('AGENTE OCUPADO'))
                fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',8,40,0,0));os.kill(p.pid,signal.SIGWINCH)
                wait_for(lambda:contains('Aumente o painel'))
                key('1');time.sleep(.15)
                self.assertFalse((root/'queued').exists(),'cannot confirm when the question is not visible')
                fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',30,40,0,0));os.kill(p.pid,signal.SIGWINCH)
                wait_for(lambda:contains('AGENTE OCUPADO'));key('2');wait_for(lambda:contains('LEFT UNDONE'))
                key('1');wait_for(lambda:contains('AGENTE OCUPADO'))
                click(('key','1'));wait_for(lambda:contains('Na fila: 1'))
                self.assertFalse(db.items()[0]['selected']);self.assertEqual(len(db.items()),2)
                queued=[json.loads(line) for line in (root/'queued').read_text().splitlines()]
                self.assertEqual(queued,['You left this undone: Primeira tarefa'])
                key('b');wait_for(lambda:db.items()[1]['selected']==1)
                key('1');wait_for(lambda:contains('AGENTE OCUPADO'))
                (root/'fail').touch();key('1');wait_for(lambda:contains('Fila não confirmada'))
                self.assertTrue(db.items()[1]['selected'])
                self.assertEqual(len((root/'queued').read_text().splitlines()),1)
                (root/'fail').unlink();key('1');wait_for(lambda:contains('AGENTE OCUPADO'))
                key('1');wait_for(lambda:not db.items()[1]['selected'])
                queued=[json.loads(line) for line in (root/'queued').read_text().splitlines()]
                self.assertEqual(queued,['You left this undone: Primeira tarefa','You left this undone: Segunda tarefa'])
                for n in range(50):db.add('import',f'Tarefa extra {n}')
                wait_for(lambda:contains('52 itens'))
                click(('next',None));wait_for(lambda:' · 2/' in ' '.join(screen()['lines']))
                key('a');wait_for(lambda:contains('Enviar 1'))
                previous=next(line for line in screen()['lines'] if '52 itens' in line)
                key('1');wait_for(lambda:contains('AGENTE OCUPADO'))
                key('2');wait_for(lambda:contains('LEFT UNDONE'))
                self.assertIn(previous,screen()['lines'],'cancel must preserve the current list page')
                original={i['id'] for i in db.items()};chosen=next(i['id'] for i in db.items() if i['selected'])
                key('2');wait_for(lambda:contains('CONCLUIR TAREFAS'))
                self.assertEqual(len(db.items()),52)
                key('2');wait_for(lambda:contains('Conclusão cancelada'))
                self.assertIn(previous,screen()['lines'])
                self.assertTrue(next(i for i in db.items() if i['id']==chosen)['selected'])
                key('2');wait_for(lambda:contains('CONCLUIR TAREFAS'))
                key('\x1b');wait_for(lambda:contains('LEFT UNDONE'));self.assertIsNone(p.poll())
                click(('key','2'));wait_for(lambda:contains('CONCLUIR TAREFAS'))
                fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',8,40,0,0));os.kill(p.pid,signal.SIGWINCH)
                wait_for(lambda:contains('Aumente o painel'));key('1');time.sleep(.15)
                self.assertEqual(len(db.items()),52)
                fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',30,40,0,0));os.kill(p.pid,signal.SIGWINCH)
                wait_for(lambda:contains('CONCLUIR TAREFAS'))
                click(('key','1'));wait_for(lambda:len(db.items())==51)
                self.assertEqual({i['id'] for i in db.items()},original-{chosen})
                wait_for(lambda:contains('LEFT UNDONE'))
                # Adding action buttons reflows page 2; choose stable item IDs,
                # since the letter b may become the former a after that reflow.
                targets=[t[2] for t in screen()['targets'] if t[2][0]=='item'][:2]
                click(tuple(targets[0]));wait_for(lambda:contains('Enviar 1'))
                click(tuple(targets[1]));wait_for(lambda:contains('Enviar 2'))
                self.assertEqual(sum(i['selected'] for i in db.items()),2)
                key('2');wait_for(lambda:contains('CONCLUIR TAREFAS'))
                self.assertTrue(contains('2 itens'));self.assertEqual(len(db.items()),51)
                key('1');wait_for(lambda:len(db.items())==49)
                self.assertFalse(any(i['selected'] for i in db.items()))
                key('\x1b');p.wait(timeout=5);self.assertEqual(p.returncode,0)
            finally:
                if p.poll() is None:p.terminate();p.wait(timeout=10)
                os.close(master)
