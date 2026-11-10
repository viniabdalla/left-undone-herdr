"""Transactional session state and incremental structured transcript collectors."""
import copy
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def clean(text):
    return ' '.join(str(text).split())[:240]


def validate_audit(value, opened):
    if not isinstance(value, dict) or set(value) != {'done', 'add'}:
        raise ValueError('Analisador: esperado JSON com done e add')
    done, add = value['done'], value['add']
    if not isinstance(done, list) or any(type(n) is not int or not 1 <= n <= len(opened) for n in done):
        raise ValueError('Analisador: índice done inválido')
    if not isinstance(add, list) or len(add) > 5 or any(not isinstance(s, str) or not s.strip() or len(s) > 240 for s in add):
        raise ValueError('Analisador: add inválido (máximo 5 textos de 240 caracteres)')
    return {'done': list(dict.fromkeys(done)), 'add': list(dict.fromkeys(clean(s) for s in add))}


class Store:
    def __init__(self, path, session):
        self.session = session
        Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.conn = sqlite3.connect(path, timeout=5)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript('''
          PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY, session TEXT, origin TEXT, source TEXT,
            text TEXT, status TEXT DEFAULT 'open', selected INTEGER DEFAULT 0, dismissed INTEGER DEFAULT 0,
            UNIQUE(session,origin,source));
          CREATE TABLE IF NOT EXISTS processed (session TEXT, event TEXT, PRIMARY KEY(session,event));
          CREATE TABLE IF NOT EXISTS cursors (session TEXT PRIMARY KEY, value TEXT);
        ''')

        columns={r[1] for r in self.conn.execute('PRAGMA table_info(items)')}
        if 'dismissed' not in columns:
            with self.conn:
                self.conn.execute('ALTER TABLE items ADD COLUMN dismissed INTEGER DEFAULT 0')
                self.conn.execute("UPDATE items SET dismissed=1 WHERE status='done'")

    def close(self):
        self.conn.close()

    def items(self, origin=None):
        sql="SELECT * FROM items WHERE session=? AND status='open'"
        args=[self.session]
        if origin:sql+=' AND origin=?';args.append(origin)
        return [dict(r) for r in self.conn.execute(sql+" ORDER BY CASE origin WHEN 'task' THEN 0 ELSE 1 END,id",args)]

    def add(self, origin, text, source=None):
        text=clean(text)
        if not text:return
        source=source or hashlib.sha256(text.casefold().encode()).hexdigest()
        # A tombstone prevents imports/replayed snapshots reopening manually closed tasks.
        self.conn.execute('INSERT OR IGNORE INTO items(session,origin,source,text) VALUES(?,?,?,?)',
                          (self.session,origin,source,text))
        self.conn.commit()

    def done(self, ids):
        with self.conn:
            self.conn.executemany("UPDATE items SET status='done',selected=0,dismissed=1 WHERE session=? AND id=?",
                                  [(self.session,i) for i in ids])

    def toggle(self, item_id):
        with self.conn:
            self.conn.execute('UPDATE items SET selected=1-selected WHERE session=? AND id=?',(self.session,item_id))

    def clear_selection(self, ids):
        with self.conn:
            self.conn.executemany('UPDATE items SET selected=0 WHERE session=? AND id=?',[(self.session,i) for i in ids])

    def import_md(self, text):
        count=0
        for line in text.splitlines():
            m=re.match(r'^\s*[-*]\s+\[ \]\s+(.+?)\s*$',line)
            if not m:continue
            value=clean(m[1])
            if self.conn.execute('SELECT 1 FROM items WHERE session=? AND lower(text)=lower(?)',(self.session,value)).fetchone():continue
            self.add('import',value);count+=1
        return count

    def export_md(self):
        stamp=datetime.now(timezone.utc).isoformat(timespec='minutes')
        return '# Left undone\n\nExported '+stamp+'\n\n'+'\n'.join('- [ ] '+i['text'] for i in self.items())+'\n'

    def cursor(self):
        row=self.conn.execute('SELECT value FROM cursors WHERE session=?',(self.session,)).fetchone()
        return json.loads(row[0]) if row else {'offset':0,'pending':{}}

    def seen(self, event):
        return self.conn.execute('SELECT 1 FROM processed WHERE session=? AND event=?',(self.session,event)).fetchone() is not None

    def commit_line(self, state, events, audits):
        with self.conn:
            for event in events:
                key=event['id']
                if self.seen(key):continue
                kind=event['kind']
                if kind=='audit':
                    opened,audit=audits[key]
                    for n in audit['done']:
                        self.conn.execute("UPDATE items SET status='done',selected=0 WHERE id=? AND session=?",(opened[n-1]['id'],self.session))
                    for text in audit['add']:
                        # Dedupe against all open origins; completed promises may be made anew.
                        if not any(i['text'].casefold()==text.casefold() for i in self.items()):
                            source=key+':'+hashlib.sha256(text.encode()).hexdigest()
                            self.conn.execute('INSERT OR IGNORE INTO items(session,origin,source,text) VALUES(?,?,?,?)',(self.session,'promise',source,text))
                elif kind in ('snapshot','upsert'):
                    tasks=event['tasks']
                    if kind=='snapshot':
                        sources=[t['source'] for t in tasks]
                        for old in self.items('task'):
                            if old['source'] not in sources:
                                self.conn.execute("UPDATE items SET status='done',selected=0 WHERE id=?",(old['id'],))
                    for task in tasks:
                        status='done' if task['status'] in ('completed','deleted') else 'open'
                        old=self.conn.execute('SELECT * FROM items WHERE session=? AND origin=? AND source=?',(self.session,'task',task['source'])).fetchone()
                        if old:
                            self.conn.execute('UPDATE items SET text=?,status=?,selected=CASE WHEN ?="done" THEN 0 ELSE selected END WHERE id=?',
                                (clean(task.get('text') or old['text']), 'done' if old['dismissed'] else status,status,old['id']))
                        elif task.get('text'):
                            self.conn.execute('INSERT INTO items(session,origin,source,text,status) VALUES(?,?,?,?,?)',(self.session,'task',task['source'],clean(task['text']),status))
                self.conn.execute('INSERT OR IGNORE INTO processed VALUES(?,?)',(self.session,key))
            self.conn.execute('INSERT OR REPLACE INTO cursors VALUES(?,?)',(self.session,json.dumps(state)))


def task_events(name, args, output, key):
    if name in ('TodoWrite','update_plan'):
        rows=args.get('todos',[]) if name=='TodoWrite' else args.get('plan',[])
        return [{'kind':'snapshot','id':key,'tasks':[{'source':clean(t.get('content',t.get('step',''))),'text':t.get('content',t.get('step','')),'status':t.get('status','pending')} for t in rows]}]
    if name=='TaskCreate':
        match=re.search(r'Task #([\w-]+)',str(output))
        tid=output.get('task',{}).get('id') if isinstance(output,dict) else None
        tid=tid or (match[1] if match else None)
        if tid:return [{'kind':'upsert','id':key,'tasks':[{'source':str(tid),'text':args.get('subject',''),'status':'pending'}]}]
    if name=='TaskUpdate' and args.get('taskId'):
        return [{'kind':'upsert','id':key,'tasks':[{'source':str(args['taskId']),'text':args.get('subject'),'status':args.get('status','pending')}]}]
    return []


class CodexAdapter:
    def feed(self, row, state, fallback):
        p=row.get('payload',{})
        if row.get('type')=='event_msg' and p.get('type')=='task_complete':
            reply=p.get('last_agent_message','')
            return [{'kind':'audit','id':'turn:'+str(p.get('turn_id') or fallback),'reply':reply}] if reply else []
        if row.get('type')!='response_item':return []
        if p.get('type')=='function_call':
            name=p.get('name','').split('.')[-1]
            if name in ('update_plan','TodoWrite','TaskCreate','TaskUpdate'):
                args=p.get('arguments',{})
                try:args=json.loads(args) if isinstance(args,str) else args
                except ValueError:return []
                state['pending'][p['call_id']]=[name,args]
        elif p.get('type')=='function_call_output':
            call=state['pending'].pop(p.get('call_id'),None)
            output=p.get('output','')
            if call and not p.get('is_error') and not re.search(r'\b(error|failed)\b',str(output),re.I):
                return task_events(*call,output,'tool:'+p['call_id'])
        return []


class ClaudeAdapter:
    def feed(self, row, state, fallback):
        if row.get('isSidechain') or row.get('agentId'):return []
        msg=row.get('message',{}); content=msg.get('content',[])
        if not isinstance(content,list):return []
        events=[]
        if row.get('type')=='assistant':
            for b in content:
                if b.get('type')=='tool_use' and b.get('name') in ('TodoWrite','TaskCreate','TaskUpdate'):
                    state['pending'][b['id']]=[b['name'],b.get('input',{})]
            if msg.get('stop_reason')=='end_turn':
                reply='\n'.join(b.get('text','') for b in content if b.get('type')=='text')
                if reply:events.append({'kind':'audit','id':'turn:'+str(msg.get('id') or row.get('uuid') or fallback),'reply':reply})
        elif row.get('type')=='user':
            for b in content:
                if b.get('type')!='tool_result':continue
                call=state['pending'].pop(b.get('tool_use_id'),None)
                if call and not b.get('is_error'):
                    events+=task_events(*call,b.get('content',''),'tool:'+b['tool_use_id'])
        return events


class Collector:
    def __init__(self, store, path, kind, analyze):
        self.store=store;self.path=Path(path);self.analyze=analyze
        self.adapter=CodexAdapter() if kind=='codex' else ClaudeAdapter()

    def poll(self, limit=500):
        state=self.store.cursor();stat=self.path.stat();identity=[stat.st_dev,stat.st_ino]
        if state.get('identity')!=identity or stat.st_size<state['offset']:
            state={'offset':0,'pending':{},'identity':identity}
        with self.path.open('rb') as f:
            f.seek(state['offset'])
            for _ in range(limit):
                line=f.readline()
                if not line or not line.endswith(b'\n'):break
                try:row=json.loads(line)
                except (ValueError,UnicodeError) as e:raise ValueError('Histórico contém linha JSON inválida; cursor preservado') from e
                new=copy.deepcopy(state);new['offset']=f.tell()
                key=hashlib.sha256(line).hexdigest()
                events=self.adapter.feed(row,new,key);audits={}
                for event in events:
                    if event['kind']=='audit' and not self.store.seen(event['id']):
                        opened=self.store.items('promise')
                        value=self.analyze(event['reply'],[i['text'] for i in opened])
                        audits[event['id']]=(opened,validate_audit(value,opened))
                self.store.commit_line(new,events,audits)
                state=new
