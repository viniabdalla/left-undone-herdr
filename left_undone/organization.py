"""Explicit, audited organization of verified session tasks; never an LLM action."""
import json
import math
from .language import tr


def organize_items(store,changes,event,*,associate=None):
    """Apply a reviewed snapshot atomically, retaining IDs, sources and tombstones."""
    conn=store.conn
    conn.execute('''CREATE TABLE IF NOT EXISTS panel_organization (
        event TEXT, item INTEGER, before_json TEXT NOT NULL, after_json TEXT NOT NULL,
        evidence TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(event,item))''')
    conn.commit()
    with store.curation_lock(), conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM panel_organization o JOIN items i ON i.id=o.item '
                        'WHERE o.event=? AND i.session=?', (event, store.session)).fetchone():
            return 0
        if associate is not None:
            current=conn.execute('SELECT project FROM project_sessions WHERE session=?',(store.session,)).fetchone()
            if not current or current[0]!=store.project:raise RuntimeError(tr('Association has changed; check again'))
        where,args=store.scope();snapshot=[]
        for change in changes:
            expected=change['expected'];item=expected['id']
            row=conn.execute('SELECT items.*, (SELECT created_at FROM item_creation WHERE item=items.id) AS created_at FROM items WHERE id=? AND '+where,[item,*args]).fetchone()
            if row is None or any(row[k]!=v for k,v in expected.items()):
                raise RuntimeError(tr('Item {0} changed; no changes applied').format(item))
            if row['origin'] not in ('task','import'):raise ValueError(tr('Private promises cannot be moved'))
            if row['origin']=='task' and not str(row['source']).startswith('curator:'):
                raise ValueError(tr('Native tasks remain linked to the original collector'))
            if not change.get('evidence'):raise ValueError(tr('Organization requires explicit evidence'))
            if 'created_at' in change and (type(change['created_at']) not in (int,float) or not math.isfinite(change['created_at'])):
                raise ValueError(tr('Invalid creation date'))
            snapshot.append((change,dict(row)))
        for change,before in snapshot:
            item=before['id']
            conn.execute('INSERT OR IGNORE INTO project_catalog VALUES(?)',(change['project'],))
            conn.execute('UPDATE items SET text=? WHERE id=? AND session=?',
                         (change.get('text',before['text']),item,store.session))
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
