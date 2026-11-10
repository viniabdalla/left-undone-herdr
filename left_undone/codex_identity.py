"""Active Codex thread proof from the native ``thread-id`` terminal title item.

Herdr learns the Codex session from SessionStart, which Codex 0.167 only fires
on the next turn; after /new or /resume it keeps announcing the previous UUID.
The Codex TUI redraws its terminal title as soon as the visible thread changes.
The title is free text (thread name, project, live setup preview), so it counts
as evidence only when this process was started with a command-line override that
makes ``thread-id`` the sole title item, and the whole title is one UUID prefix.

The prefix is never used to pick a history file or to report a session to
Herdr. It only (a) confirms that a full UUID already verified by the native
integration is the active one, and (b) recognises, among full UUIDs that were
confirmed natively in this same process/pane/terminal, exactly one.
"""
import fcntl
import json
import os
import re
try:import tomllib
except ModuleNotFoundError:tomllib = None  # Python 3.10: conservative fallback below
from pathlib import Path

REQUIRED = ['thread-id']
SETUP = 'inicie o Codex com -c \'tui.terminal_title=["thread-id"]\''
# Codex 0.167 truncates the item to 8-4-4-4-5 hex digits plus "...".
TITLE = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{5,12})(?:\.\.\.|…)?')
MISSING = object()
MANAGED = '/etc/codex/managed_config.toml'


class Unverifiable(RuntimeError):
    """The active Codex conversation cannot be proven; block collection/sending."""


def state_root():
    root = Path(os.environ.get('LEFT_UNDONE_STATE_DIR', str(Path(os.environ.get(
        'XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'left-undone-herdr')))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _toml_value(raw):
    if tomllib is None:
        # Without a TOML parser accept only JSON-compatible values; anything
        # else stays a raw string, which never equals REQUIRED (blocks).
        try:return json.loads(raw)
        except ValueError:return raw
    try:return tomllib.loads('v=' + raw)['v']
    except tomllib.TOMLDecodeError:return raw


def _table(data, *path):
    for key in path:
        if not isinstance(data, dict):return MISSING
        data = data.get(key, MISSING)
    return data


def _load(path):
    try:
        if tomllib is None:
            # Python 3.10 cannot parse TOML: any mention of the title blocks.
            text = Path(path).read_text(errors='replace')
            return {'tui': {'terminal_title': None}} if 'terminal_title' in text else {}
        with open(path, 'rb') as stream:return tomllib.load(stream)
    except FileNotFoundError:return {}
    except (OSError, ValueError) as error:
        raise Unverifiable(f'Configuração Codex ilegível ({path}); não é possível provar o título') from error


def _cli(argv):
    """tui.terminal_title override from the Codex command line, or MISSING."""
    title, index = MISSING, 1
    while index < len(argv):
        arg = argv[index];index += 1
        if arg == '--':break
        if arg in ('-c', '--config') and index < len(argv):
            value = argv[index];index += 1
        elif arg.startswith('--config='):value = arg.split('=', 1)[1]
        elif arg.startswith('-c') and len(arg) > 2:value = arg[2:]
        else:continue
        key, _, raw = value.partition('=')
        normalized = re.sub(r'[\s"\']', '', key)
        if normalized == 'tui.terminal_title':title = _toml_value(raw)
        elif 'terminal_title' in normalized or normalized == 'tui':
            raise Unverifiable('Override de linha de comando do Codex altera o título de forma não verificável')
    return title


def command_line(pid):
    return [x for x in (Path('/proc') / str(pid) / 'cmdline').read_bytes().decode(errors='replace').split('\0') if x]


def started_at(pid):
    """Process start as epoch seconds (from /proc, not from argv or files)."""
    fields = (Path('/proc') / str(pid) / 'stat').read_text().split(') ', 1)[1].split()
    boot = next(int(line.split()[1]) for line in Path('/proc/stat').read_text().splitlines() if line.startswith('btime '))
    return boot + int(fields[19]) / os.sysconf('SC_CLK_TCK')


def title_items(pid, account):
    """Title items the running Codex was started with, or Unverifiable.

    Config files only show the current file, not what the TUI loaded, so the
    proof is the immutable command-line override of this process.
    """
    cli = _cli(command_line(pid))
    if _table(_load(MANAGED), 'tui', 'terminal_title') is not MISSING:
        raise Unverifiable('Configuração gerenciada do Codex define o título; não verificável')
    if cli is MISSING:
        raise Unverifiable('Codex iniciado sem -c \'tui.terminal_title=["thread-id"]\'; ID ativo não verificável')
    # The TUI's own title setup saves to config.toml and applies live; a later
    # rewrite can drop the field while the runtime title stays. The current file
    # never proves the runtime, so any write after start blocks.
    config = Path(account) / 'config.toml'
    try:changed = config.stat().st_mtime >= started_at(pid) - 1
    except FileNotFoundError:changed = False
    if changed:
        raise Unverifiable('config.toml do Codex foi alterado depois do início do processo; '
                           'título não verificável até reabrir o Codex')
    return cli


def active_prefix(live, pid, account):
    if title_items(pid, account) != REQUIRED:
        raise Unverifiable('Codex não exibe só o ID nativo da conversa no título ('+SETUP+'); coleta e envio bloqueados')
    match = TITLE.fullmatch((live.get('terminal_title') or '').strip())
    if not match:
        raise Unverifiable('Título do Codex sem ID de conversa verificável; coleta e envio bloqueados')
    return match.group(1)


def confirmed_session(live, proc, alive):
    """Full UUID of the conversation active in a verified Codex process."""
    prefix = active_prefix(live, proc['pid'], proc['account'])
    session = live.get('agent_session') or {}
    native = session.get('value') if session.get('kind') == 'id' else None
    key = '\0'.join([proc['account'], live.get('pane_id') or '', live.get('terminal_id') or '',
                     str(proc['pid']), str(proc['started'])])
    root = state_root()
    with (root / 'codex-confirmed.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root / 'codex-confirmed.json'
        try:data = json.loads(path.read_text())
        except (OSError, ValueError):data = {}
        data = {k: v for k, v in data.items() if isinstance(v, list) and alive(*k.split('\0')[3:5])}
        if native and native.startswith(prefix) and native not in data.setdefault(key, []):
            data[key].append(native)
            tmp = path.with_suffix('.tmp.' + str(os.getpid()))
            tmp.write_text(json.dumps(data));tmp.replace(path)
        known = [s for s in data.get(key, []) if s.startswith(prefix)]
    if len(known) == 1:return known[0]
    if known:raise Unverifiable('ID ativo do Codex corresponde a mais de uma conversa confirmada; bloqueado')
    raise Unverifiable(f'Conversa ativa no Codex (ID {prefix}…) ainda sem confirmação nativa neste processo '
                       '(após /new, /resume ou início); envie uma mensagem diretamente nessa conversa e reabra o painel')
