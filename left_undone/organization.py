"""Explicit, audited organization of verified shared tasks; never an LLM action."""
import fcntl
import hashlib
import json
import math
from contextlib import ExitStack
from pathlib import Path


def organize_items(store,changes,event,*,associate=None):
    """Apply a reviewed snapshot atomically, retaining IDs, sources and tombstones."""
    conn=store.conn
    conn.execute('''CREATE TABLE IF NOT EXISTS panel_organization (
        event TEXT, item INTEGER, before_json TEXT NOT NULL, after_json TEXT NOT NULL,
        evidence TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(event,item))''')
    conn.commit()
    projects={store.project,*(change['project'] for change in changes)}
    root=Path(conn.execute('PRAGMA database_list').fetchone()[2]).parent
    with ExitStack() as stack:
        for project in sorted(projects):
            key='project:'+hashlib.sha256(project.encode()).hexdigest()
            lock=stack.enter_context((root/(key+'.curation.lock')).open('a'))
            fcntl.flock(lock,fcntl.LOCK_EX)
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('SELECT 1 FROM panel_organization WHERE event=?',(event,)).fetchone():return 0
            if associate is not None:
                current=conn.execute('SELECT project FROM project_sessions WHERE session=?',(store.session,)).fetchone()
                if not current or current[0]!=store.project:raise RuntimeError('Associação mudou; confira novamente')
            where,args=store.scope();snapshot=[]
            for change in changes:
                expected=change['expected'];item=expected['id']
                row=conn.execute('SELECT items.*, (SELECT created_at FROM item_creation WHERE item=items.id) AS created_at FROM items WHERE id=? AND '+where,[item,*args]).fetchone()
                if row is None or any(row[k]!=v for k,v in expected.items()):
                    raise RuntimeError(f'Item {item} mudou; nenhuma alteração aplicada')
                if row['origin'] not in ('task','import'):raise ValueError('Promessas privadas não podem ser movidas')
                if row['origin']=='task' and not str(row['source']).startswith('curator:'):
                    raise ValueError('Tarefas nativas permanecem vinculadas ao coletor original')
                if not change.get('evidence'):raise ValueError('Organização exige evidência explícita')
                if 'created_at' in change and (type(change['created_at']) not in (int,float) or not math.isfinite(change['created_at'])):
                    raise ValueError('Data de criação inválida')
                snapshot.append((change,dict(row)))
            for change,before in snapshot:
                item=before['id'];project=change['project'];owner='project:'+hashlib.sha256(project.encode()).hexdigest()
                conn.execute('INSERT OR IGNORE INTO project_catalog VALUES(?)',(project,))
                if before['selected'] and conn.execute('SELECT 1 FROM project_sessions WHERE session=?',(before['session'],)).fetchone():
                    conn.execute('INSERT OR IGNORE INTO project_selections VALUES(?,?)',(before['session'],item))
                conn.execute('UPDATE items SET session=?,text=? WHERE id=?',(owner,change.get('text',before['text']),item))
                if change.get('reason'):
                    conn.execute("UPDATE items SET status='done',selected=0,dismissed=1 WHERE id=?",(item,))
                    conn.execute('INSERT OR REPLACE INTO item_closures VALUES(?,?,?)',(item,change['reason'],change['evidence']))
                if 'created_at' in change:
                    conn.execute('INSERT INTO item_creation VALUES(?,?) ON CONFLICT(item) DO UPDATE SET created_at=excluded.created_at '
                        'WHERE item_creation.created_at IS NULL',(item,change['created_at']))
                after=dict(conn.execute('SELECT items.*, (SELECT created_at FROM item_creation WHERE item=items.id) AS created_at, '
                    '(SELECT reason FROM item_closures WHERE item=items.id) AS closure_reason FROM items WHERE id=?',(item,)).fetchone())
                conn.execute('INSERT INTO panel_organization(event,item,before_json,after_json,evidence) VALUES(?,?,?,?,?)',
                    (event,item,json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False),change['evidence']))
            if associate is not None:
                conn.execute('UPDATE project_sessions SET project=? WHERE session=?',(associate,store.session))
    return len(snapshot)
