"""Session-owned task lists and the project used for explicit task exchange."""
import fcntl
import hashlib
import json
import re
from contextlib import contextmanager
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
            self.conn.execute('BEGIN IMMEDIATE')
            self._restore_legacy_owners()
            if not view:
                self.conn.execute('INSERT OR IGNORE INTO project_sessions VALUES(?,?)', (session, self.project))
                self.project = self.conn.execute('SELECT project FROM project_sessions WHERE session=?', (session,)).fetchone()[0]
            self.conn.execute('INSERT OR IGNORE INTO project_catalog VALUES(?)',(self.project,))
        self.owner = 'project:' + hashlib.sha256(self.project.encode()).hexdigest()

    def _restore_legacy_owners(self):
        """Recover proven owners in place. Unattributed rows remain available for import."""
        legacy = {r['id']: set() for r in self.conn.execute(
            "SELECT id FROM items WHERE session GLOB 'project:*'")}
        if not legacy:
            return
        tables = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'curation_changes' in tables:
            for item, session in self.conn.execute("SELECT item, session FROM curation_changes WHERE action='add'"):
                if item in legacy and session and not session.startswith('project:'):
                    legacy[item].add(session)
        if 'panel_organization' in tables:
            for item, before in self.conn.execute('SELECT item, before_json FROM panel_organization'):
                if item not in legacy:
                    continue
                try:
                    session = json.loads(before)['session']
                except (KeyError, TypeError, ValueError):
                    continue
                if isinstance(session, str) and session and not session.startswith('project:'):
                    legacy[item].add(session)
        for item, owners in legacy.items():
            if len(owners) != 1:
                continue
            session, = owners
            origin, source = self.conn.execute('SELECT origin,source FROM items WHERE id=?', (item,)).fetchone()
            # The owner may have imported another copy after a historical move.
            # Keep both IDs and retain the original source inside the disambiguated key.
            while self.conn.execute('SELECT 1 FROM items WHERE session=? AND origin=? AND source=?',
                                    (session, origin, source)).fetchone():
                source = f'{source}:legacy:{item}'
            self.conn.execute(
                "UPDATE items SET session=?, source=?, selected=(status='open' AND "
                "(selected OR EXISTS(SELECT 1 FROM project_selections WHERE viewer=? AND item=?))) "
                "WHERE id=?", (session, source, session, item, item))

    @contextmanager
    def curation_lock(self):
        key = hashlib.sha256(self.session.encode()).hexdigest()
        with (Path(self.path).parent / f'session:{key}.curation.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def scope(self):
        return 'items.session=?', [self.session]

    def available_projects(self):
        return [r[0] for r in self.conn.execute('SELECT project FROM project_catalog UNION SELECT project FROM project_sessions ORDER BY project')]

    def view_project(self,project):
        return ProjectStore(self.path,self.session,project,view=True)

    def history_items(self):
        where,args=self.scope()
        return [dict(r) for r in self.conn.execute('SELECT items.*, '
            '(SELECT created_at FROM item_creation WHERE item=items.id) AS created_at, '
            "COALESCE((SELECT reason FROM item_closures WHERE item=items.id),'Closed') AS closure_reason "
            ", (SELECT evidence FROM item_closures WHERE item=items.id) AS closure_evidence FROM items WHERE status='done' AND "+where+' ORDER BY id DESC',args)]

    def note_closure(self,item_id,reason,evidence):
        where,args=self.scope()
        with self.conn:
            self.conn.execute('INSERT OR REPLACE INTO item_closures SELECT id,?,? FROM items '
                "WHERE id=? AND status='done' AND "+where,[reason,evidence,item_id,*args])

    def toggle(self, item_id):
        with self.conn:
            self.conn.execute("UPDATE items SET selected=1-selected WHERE session=? AND id=? AND status='open'",
                              (self.session, item_id))

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
                row = self.conn.execute('INSERT OR IGNORE INTO items(session,origin,source,text) VALUES(?,?,?,?)',
                                        (self.session, 'import', source, value))
                known.add(value.casefold())
                count += row.rowcount
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
