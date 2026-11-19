"""Explicit exchange of session-owned copies through a worktree checklist."""
import fcntl
import hashlib
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from .core import clean
from .language import tr
from .repository import project_root


_BEGIN = '<!-- left-undone:tasks:v1 -->'
_END = '<!-- /left-undone:tasks -->'
_ID = r'[0-9a-f]{64}'
_OPEN = re.compile(r'- \[([ xX])\] (.+) <!-- left-undone:id=(' + _ID + r') -->')
_CLOSED = re.compile(r'<!-- left-undone:closed=(' + _ID + r') -->')
_SOURCE = 'left-undone:exchange:'


def _path(store, project):
    root = project if project is not None else getattr(store, 'project', None)
    if not root:
        raise ValueError(tr('No project is associated with this session'))
    return project_root(root) / '.left-undone' / 'tasks.md'


@contextmanager
def _locked(path):
    # The directory inode stays stable across atomic replacements of tasks.md.
    directory = os.open(path.parent.parent, os.O_DIRECTORY | os.O_RDONLY)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX)
        yield
    finally:
        os.close(directory)


def _document(path):
    try:
        with path.open(encoding='utf-8', newline='') as stream:
            lines = stream.readlines()
    except FileNotFoundError:
        return '# Left undone\n\n', {}, ''
    markers = [i for i, line in enumerate(lines) if line.rstrip('\r\n') in (_BEGIN, _END)]
    invalid = tr('Unrecognized project checklist format')
    if len(markers) != 2:
        raise ValueError(invalid)
    start, end = markers
    if lines[start].rstrip('\r\n') != _BEGIN or lines[end].rstrip('\r\n') != _END:
        raise ValueError(invalid)
    entries = {}
    for line in lines[start + 1:end]:
        line = line.rstrip('\r\n')
        task = _OPEN.fullmatch(line)
        closed = _CLOSED.fullmatch(line)
        if task:
            key = task[3]
            value = clean(task[2]) if task[1] == ' ' else None
            if value == '' or (value is not None and value != task[2]):
                raise ValueError(invalid)
        elif closed:
            key, value = closed[1], None
        else:
            raise ValueError(invalid)
        if key in entries:
            raise ValueError(invalid)
        entries[key] = value
    return ''.join(lines[:start]), entries, ''.join(lines[end + 1:])


def _key(row):
    source = row['source'] or ''
    if row['origin'] == 'import' and source.startswith(_SOURCE):
        key = source[len(_SOURCE):]
        if re.fullmatch(_ID, key):
            return key
    identity = json.dumps([row['session'], row['origin'], row['source']], ensure_ascii=False)
    return hashlib.sha256(identity.encode()).hexdigest()


def _local(store):
    # id, source and origin are persistent even if a collector renames an item.
    return store.conn.execute('SELECT * FROM items WHERE session=? ORDER BY id', (store.session,))


def open_exchange_ids(store):
    return {_key(row) for row in store.items()}


def _available(store, path, entries):
    # Pre-isolation imports with no recorded author belong to the project. Keep
    # these rows intact and require explicit selection to copy them locally.
    owner = 'project:' + hashlib.sha256(str(path.parent.parent).encode()).hexdigest()
    for row in store.conn.execute('SELECT * FROM items WHERE session=? AND status=? ORDER BY id',
                                  (owner, 'open')):
        entries.setdefault(_key(row), row['text'])
    return entries


def import_choices(store, project=None):
    path = _path(store, project)
    _, entries, _ = _document(path)
    owned = {_key(row) for row in _local(store)}
    return [dict(id=key, text=value, imported=key in owned)
            for key, value in _available(store, path, entries).items() if value is not None]


def import_selected(store, ids, project=None):
    path = _path(store, project)
    requested = set(ids)
    if not requested:
        return 0
    count = 0
    with _locked(path), store.conn:
        store.conn.execute('BEGIN IMMEDIATE')
        _, entries, _ = _document(path)
        owned = {_key(row) for row in _local(store)}
        for key, value in _available(store, path, entries).items():
            if value is None or key not in requested or key in owned:
                continue
            store.conn.execute('INSERT INTO items(session,origin,source,text) VALUES(?,?,?,?)',
                               (store.session, 'import', _SOURCE + key, value))
            count += 1
    return count


def export_project(store, project=None):
    return export_snapshot(store, project)[0]


def export_snapshot(store, project=None):
    """Publish and return the IDs of this conversation's published open rows."""
    published = []
    path = _path(store, project)
    with _locked(path):
        prefix, entries, suffix = _document(path)
        for row in _local(store):
            key = _key(row)
            if row['status'] == 'open':
                if key not in entries or (entries[key] is not None and row['source'] != _SOURCE + key):
                    entries[key] = row['text']
                if entries[key] is not None:
                    published.append(key)
            elif key in entries or row['source'] == _SOURCE + key:
                entries[key] = None
        lines = [_BEGIN]
        for key, value in entries.items():
            if value is None:
                lines.append(f'<!-- left-undone:closed={key} -->')
            else:
                lines.append(f'- [ ] {value} <!-- left-undone:id={key} -->')
        lines.append(_END)
        path.parent.mkdir(exist_ok=True)
        with NamedTemporaryFile(dir=path.parent, delete=False, mode='w', encoding='utf-8') as stream:
            temp = Path(stream.name)
            try:
                stream.write(prefix + '\n'.join(lines) + '\n' + suffix)
                stream.flush()
                os.fsync(stream.fileno())
                stream.close()
                temp.replace(path)
            finally:
                temp.unlink(missing_ok=True)
    return path, published
