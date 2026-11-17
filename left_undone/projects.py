"""Persistent project task views; collectors remain scoped to their own session."""
import hashlib
import json
import re
from pathlib import Path

from .core import Store, clean
from .runtime import Binding
from .repository import project_root, session_project


class ProjectStore(Store):
    def __init__(self, path, session, project, *, view=False):
        super().__init__(path, session)
        self.path=path
        self.project = str(project)
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS project_sessions (session TEXT PRIMARY KEY, project TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS project_selections (
                viewer TEXT, item INTEGER, PRIMARY KEY(viewer,item));
            CREATE TABLE IF NOT EXISTS project_catalog (project TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS item_closures (
                item INTEGER PRIMARY KEY, reason TEXT NOT NULL, evidence TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS clear_project_selections
                AFTER UPDATE OF status ON items WHEN NEW.status='done'
                BEGIN DELETE FROM project_selections WHERE item=NEW.id; END;
        ''')
        with self.conn:
            if not view:
                self.conn.execute('INSERT OR IGNORE INTO project_sessions VALUES(?,?)', (session, self.project))
                self.project = self.conn.execute('SELECT project FROM project_sessions WHERE session=?', (session,)).fetchone()[0]
            self.conn.execute('INSERT OR IGNORE INTO project_catalog VALUES(?)',(self.project,))
        self.owner = 'project:' + hashlib.sha256(self.project.encode()).hexdigest()

    def scope(self):
        return ("((items.session=? AND EXISTS(SELECT 1 FROM project_sessions WHERE session=? AND project=?)) OR (items.origin IN ('task','import') AND "
                "(items.session=? OR items.session IN "
                "(SELECT session FROM project_sessions WHERE project=?))))",
                [self.session, self.session, self.project, self.owner, self.project])

    def available_projects(self):
        return [r[0] for r in self.conn.execute('SELECT project FROM project_catalog UNION SELECT project FROM project_sessions ORDER BY project')]

    def view_project(self,project):
        return ProjectStore(self.path,self.session,project,view=True)

    def history_items(self):
        where,args=self.scope()
        return [dict(r) for r in self.conn.execute('SELECT items.*, '
            '(SELECT created_at FROM item_creation WHERE item=items.id) AS created_at, '
            "COALESCE((SELECT reason FROM item_closures WHERE item=items.id),'Encerrada') AS closure_reason "
            "FROM items WHERE status='done' AND "+where+' ORDER BY id DESC',args)]

    def note_closure(self,item_id,reason,evidence):
        where,args=self.scope()
        with self.conn:
            self.conn.execute('INSERT OR REPLACE INTO item_closures SELECT id,?,? FROM items '
                "WHERE id=? AND status='done' AND "+where,[reason,evidence,item_id,*args])

    def items(self, origin=None):
        where, args = self.scope()
        if origin:where += ' AND items.origin=?';args.append(origin)
        rows = self.conn.execute('SELECT items.*, (SELECT created_at FROM item_creation WHERE item=items.id) AS created_at, EXISTS(SELECT 1 FROM project_selections '
            'WHERE viewer=? AND item=items.id) AS viewer_selected FROM items WHERE ' + where +
            " AND status='open' ORDER BY CASE origin WHEN 'task' THEN 0 ELSE 1 END,id", [self.session, *args])
        result = []
        for row in rows:
            item = dict(row)
            selected = item.pop('viewer_selected')
            if item['session'] != self.session:item['selected'] = selected
            result.append(item)
        return result

    def toggle(self, item_id):
        where, args = self.scope()
        with self.conn:
            self.conn.execute('BEGIN IMMEDIATE')
            row = self.conn.execute('SELECT session FROM items WHERE id=? AND status=\'open\' AND ' + where,
                                    [item_id, *args]).fetchone()
            if not row:return
            if row['session'] == self.session:
                self.conn.execute('UPDATE items SET selected=1-selected WHERE id=?', (item_id,))
            elif not self.conn.execute('DELETE FROM project_selections WHERE viewer=? AND item=?',
                                      (self.session, item_id)).rowcount:
                self.conn.execute('INSERT INTO project_selections VALUES(?,?)', (self.session, item_id))

    def done(self, ids):
        where, args = self.scope()
        with self.conn:
            self.conn.executemany("UPDATE items SET status='done',selected=0,dismissed=1 WHERE id=? AND " + where,
                                  [[item, *args] for item in ids])

    def clear_selection(self, ids):
        with self.conn:
            self.conn.executemany('UPDATE items SET selected=0 WHERE session=? AND id=?',
                                  [(self.session, item) for item in ids])
            self.conn.executemany('DELETE FROM project_selections WHERE viewer=? AND item=?',
                                  [(self.session, item) for item in ids])

    def import_md(self, text):
        where, args = self.scope()
        count = 0
        with self.conn:
            self.conn.execute('BEGIN IMMEDIATE')
            known = {row[0].casefold() for row in self.conn.execute(
                "SELECT text FROM items WHERE origin IN ('task','import') AND " + where, args)}
            for line in text.splitlines():
                match = re.match(r'^\s*[-*]\s+\[ \]\s+(.+?)\s*$', line)
                if not match:continue
                value = clean(match[1])
                if not value or value.casefold() in known:continue
                source = hashlib.sha256(value.casefold().encode()).hexdigest()
                self.conn.execute('INSERT OR IGNORE INTO items(session,origin,source,text) VALUES(?,?,?,?)',
                                  (self.owner, 'import', source, value))
                known.add(value.casefold());count += 1
        return count


def project_store(root, binding, project=None):
    """Explicit assignments persist; legacy bindings are discovered without moving rows."""
    base = Store(Path(root) / 'state.db', binding.key)
    try:
        base.conn.execute('CREATE TABLE IF NOT EXISTS project_sessions (session TEXT PRIMARY KEY, project TEXT NOT NULL)')
        saved = base.conn.execute('SELECT project FROM project_sessions WHERE session=?', (binding.key,)).fetchone()
        chosen = project_root(project) if project is not None else (Path(saved[0]) if saved else session_project(binding))
        if chosen is None:return base
        for file in Path(root).glob('*.binding.json'):
            try:
                old = Binding(**json.loads(file.read_text()))
                if base.conn.execute('SELECT 1 FROM project_sessions WHERE session=?', (old.key,)).fetchone():continue
                previous = session_project(old)
                if previous is not None:
                    base.conn.execute('INSERT OR IGNORE INTO project_sessions VALUES(?,?)', (old.key, str(previous)))
            except (OSError, ValueError, TypeError):continue
        if project is not None:
            base.conn.execute('INSERT OR REPLACE INTO project_sessions VALUES(?,?)', (binding.key, str(chosen)))
        base.conn.commit()
    except BaseException:
        base.close();raise
    base.close()
    return ProjectStore(Path(root) / 'state.db', binding.key, chosen)
