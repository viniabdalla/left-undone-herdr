import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from left_undone.core import Store
from left_undone.runtime import Binding


class CollectionRequestTests(unittest.TestCase):
    def test_request_wakes_error_wait_revalidates_and_collects_incrementally(self):
        from left_undone.collection_request import request_collection
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);history=root/'history.jsonl'
            history.write_text(json.dumps({'type':'event_msg','payload':{'type':'task_complete',
                'turn_id':'one','last_agent_message':'I will build the button.'}})+'\n')
            script=root/'worker.py'
            script.write_text('''import sys,time
from pathlib import Path
from left_undone import app
from left_undone.runtime import Binding
root=Path(sys.argv[1])
binding=Binding('codex','manual-test',str(root),'w0:p0','none','w0',str(root/'history.jsonl'),1,'1')
def verify(binding):
 with (root/'attempts').open('a') as f:f.write('verify\\n')
 if not (root/'allow').exists():raise RuntimeError('identity blocked')
def analyze(reply,opened):
 with (root/'analysis').open('a') as f:f.write('analyze\\n')
 while not (root/'release').exists():time.sleep(.02)
 return {'done':[],'add':['Automatic work' if 'automatic' in reply else 'Build the button']}
app.verify=verify
app.Analyzer=lambda binding:analyze
app.collect(binding,root)
''')
            env={**os.environ,'PYTHONPATH':str(Path.cwd())}
            worker=subprocess.Popen([sys.executable,str(script),tmp],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            binding=Binding('codex','manual-test',tmp,'w0:p0','none','w0',str(history),1,'1')
            request=root/(binding.key+'.collect-request')
            db=Store(root/'state.db',binding.key)
            def wait_for(predicate,timeout=2):
                end=time.monotonic()+timeout
                while time.monotonic()<end:
                    if predicate():return
                    if worker.poll() is not None:self.fail(worker.communicate()[1].decode())
                    time.sleep(.02)
                self.fail('Timed out waiting for collection: '+(root/(binding.key+'.status.json')).read_text())
            def attempts():return (root/'attempts').read_text().count('verify') if (root/'attempts').exists() else 0
            try:
                wait_for(lambda:(root/(binding.key+'.status.json')).exists())
                request_collection(worker,request)
                wait_for(lambda:attempts()>=2)
                self.assertEqual(db.items(),[])
                (root/'allow').touch();request_collection(worker,request)
                wait_for(lambda:(root/'analysis').exists())
                # Requests while busy coalesce and never run analysis concurrently.
                for _ in range(5):request_collection(worker,request)
                self.assertEqual((root/'analysis').read_text().count('analyze'),1)
                (root/'release').touch()
                wait_for(lambda:len(db.items())==1 and attempts()>=4)
                self.assertEqual(db.items()[0]['text'],'Build the button')
                self.assertEqual((root/'analysis').read_text().count('analyze'),1)
                self.assertFalse(request.exists())
                # Automatic polling still consumes new events without a request.
                with history.open('a') as f:
                    f.write(json.dumps({'type':'event_msg','payload':{'type':'task_complete',
                        'turn_id':'two','last_agent_message':'I will do automatic work.'}})+'\n')
                wait_for(lambda:len(db.items())==2,timeout=5)
                self.assertEqual({i['text'] for i in db.items()},{'Build the button','Automatic work'})
            finally:
                worker.terminate();worker.communicate(timeout=5);db.close()
            with self.assertRaisesRegex(RuntimeError,'Coletor parou'):
                request_collection(worker,request)
            self.assertFalse(request.exists())
