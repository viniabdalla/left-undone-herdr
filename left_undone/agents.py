"""Herdr monitor for the source conversation and its dispatched agents."""
import curses
import json
import sqlite3
import subprocess
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

from . import dispatch
from .language import load_language, preference_root, tr
from .runtime import herdr, resolve_history
from .ui import configure, put
from .ui_layout import Layout, MouseInput, cell_width, fit, wrap_text


def read_usage(path, cache):
    """Consume complete transcript records once, including across log rotation."""
    stat = path.stat()
    identity = (stat.st_dev, stat.st_ino)
    previous, offset, context, window, total = cache.get(path, (None, 0, None, None, None))
    if identity != previous or stat.st_size < offset:
        offset, context, window, total = 0, None, None, None
    with path.open('rb') as stream:
        stream.seek(offset)
        for line in stream:
            if not line.endswith(b'\n'):
                break
            offset += len(line)
            if b'"token_count"' not in line:
                continue
            payload = json.loads(line).get('payload', {})
            if payload.get('type') != 'token_count':
                continue
            info = payload.get('info') or {}
            context = (info.get('last_token_usage') or {}).get('total_tokens', context)
            window = info.get('model_context_window', window)
            total = (info.get('total_token_usage') or {}).get('total_tokens', total)
    cache[path] = identity, offset, context, window, total
    return context, window, total


DEFAULT_BUDGET = 500_000


def token_budget(root):
    try:
        value = int((root / 'token-budget').read_text())
        return value if 0 < value <= 999_999_999_999 else DEFAULT_BUDGET
    except (OSError, ValueError):
        return DEFAULT_BUDGET


def edit_budget(win, root, current):
    digits = str(current)
    replace = True
    while True:
        win.erase()
        put(win, 0, tr('Token reference per agent'))
        put(win, 1, digits)
        put(win, 2, tr('Enter Save · Esc Cancel'))
        win.refresh()
        try:
            key = win.get_wch()
        except curses.error:
            continue
        if key == '\x1b':
            return current
        if key in ('\r', '\n', curses.KEY_ENTER) and digits and int(digits) > 0:
            with NamedTemporaryFile('w', dir=root, delete=False) as temp:
                temp.write(digits+'\n')
            Path(temp.name).replace(root/'token-budget')
            return int(digits)
        if key in ('\x7f', '\b', curses.KEY_BACKSPACE):
            digits = digits[:-1]
            replace = False
        elif isinstance(key,str) and key in '0123456789' and (replace or len(digits)<12):
            digits = key if replace else digits+key
            replace = False


def claude_total(path, cache, session):
    stat = path.stat()
    identity = (stat.st_dev, stat.st_ino)
    previous, offset, messages, total = cache.get(path, (None, 0, {}, 0))
    if previous != identity or stat.st_size < offset:
        offset, messages, total = 0, {}, 0
    with path.open('rb') as stream:
        stream.seek(offset)
        for line in stream:
            if not line.endswith(b'\n'):
                break
            offset += len(line)
            if b'"usage"' not in line:
                continue
            row = json.loads(line)
            if row.get('type') != 'assistant' or row.get('sessionId') != session or row.get('isSidechain'):
                continue
            message = row.get('message', {})
            mid, usage = message.get('id'), message.get('usage') or {}
            if not mid or 'input_tokens' not in usage or 'output_tokens' not in usage:
                continue
            count = sum(usage.get(k,0) or 0 for k in ('input_tokens','output_tokens',
                        'cache_creation_input_tokens','cache_read_input_tokens'))
            total += count - messages.get(mid,0)
            messages[mid] = count
    cache[path] = identity, offset, messages, total
    return total if messages else None


def agent_info(pane, terminal):
    if not pane or pane.get('terminal_id') != terminal:
        return tr('Closed')
    if not pane.get('agent'):
        return tr('Terminal')
    status = pane.get('agent_status')
    return tr({'working':'Working','idle':'Idle','done':'Idle','blocked':'Blocked'}.get(status,'Unknown'))


def describe(row, pane, binding, paths, cache):
    state = agent_info(pane, row['terminal'])
    if row['main'] and pane and pane.get('agent') and pane['agent'] != binding.kind:
        state = tr('Session changed')
    total = None
    if pane and pane.get('terminal_id') == row['terminal'] and pane.get('agent') == binding.kind:
        sid = (pane.get('agent_session') or {}).get('value')
        if sid and (not row['main'] or sid == binding.session):
            try:
                if sid not in paths:
                    paths[sid] = resolve_history(binding.kind,binding.account,sid)
                if binding.kind == 'codex':
                    total = read_usage(paths[sid],cache)[2]
                else:
                    total = claude_total(paths[sid],cache,sid)
            except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired):
                pass
        elif row['main'] and sid != binding.session:
            state = tr('Session changed')
    return state, total


def usage_meter(total, budget):
    if total is None:
        return tr('Tokens')+' · '+tr('No data')
    remaining = max(0, budget-total)
    percent = 100*remaining/budget
    filled = round(10*remaining/budget)
    label = '<1' if 0 < percent < 1 else str(round(percent))
    number = f'{total:,}'.replace(',',tr(','))
    return tr('{0} tokens used').format(number)+' · '+'▰'*filled+'▱'*(10-filled)+' '+tr('{0}% left').format(label)


def state_cell(state):
    symbol = '○' if state == tr('Idle') else '●'
    return symbol+' '+state


def state_style(state):
    if state == tr('Blocked'):
        return 'alert'
    if state == tr('Working'):
        return 'active'
    return 'normal'


def monitor_lines(rows, width, targets=None, budget=DEFAULT_BUDGET):
    """Build physical lines at the current width before applying vertical scrolling."""
    width = max(1,width)
    lines = []

    def text(value,style='normal'):
        lines.extend([[(0,part,style)] for part in wrap_text(value,width)])

    def columns(cells,widths):
        wrapped = [wrap_text(value,space) for (value,_),space in zip(cells,widths)]
        for i in range(max(map(len,wrapped))):
            line = []
            x = 0
            for parts,(_,style),space in zip(wrapped,cells,widths):
                if i<len(parts):
                    line.append((x,parts[i],style))
                x += space+2
            lines.append(line)

    jobs = [entry for entry in rows if not entry[0]['main']]
    main_idle = any(row['main'] and state == tr('Idle') for row,state,_ in rows)
    jobs.sort(key=lambda entry:entry[1]!=tr('Blocked'))
    for row,state,total in rows:
        if not row['main']:
            continue
        title = tr('Main session').upper()+'   '+row['label']
        for part in wrap_text(title,width):
            lines.append([(0,part+' '*(width-cell_width(part)),'band')])
        address = ' / '.join(filter(None,(row['tab'],row['pane'])))
        text(state_cell(state)+'   '+address,state_style(state))
        text(usage_meter(total,budget),'context')
        lines.append([])

    text(tr('Sub-agents').upper()+'  '+str(len(jobs)),'heading')
    wide = width>=64
    widths = [width-30,13,13]
    if wide and jobs:
        columns([(tr(label),'dim') for label in ('Tab','Agent','Delivery')],widths)
    for row,state,total in jobs:
        task = row['task'].removeprefix('Left Undone / ')
        title = row['label']
        delivery = tr('Delivered') if row['state']=='done' else tr(dispatch.STATES.get(row['state'],'Unknown'))
        address = ' / '.join(filter(None,(row['tab'],row['pane'])))
        if wide:
            columns([(title,'heading'),(state_cell(state),state_style(state)),
                     (delivery,'normal')],widths)
            text(address,'dim')
        else:
            text(title,'heading')
            text(address,'dim')
            text(tr('Agent')+'  '+state_cell(state),state_style(state))
            text(tr('Delivery')+'  '+delivery)
        text(usage_meter(total,budget),'context')
        text(task,'dim')
        verdict = row.get('verdict')
        pending = row.get('attempt') and not verdict
        if verdict:
            label = tr('Done') if verdict == 'done' else tr('Not done')
            text(tr('Main verdict')+' · '+label+' — '+row['reason'], 'heading')
        elif pending:
            message = ('Review request unconfirmed. Check the Main before retrying.'
                       if row['reason'] else 'Waiting for the Main’s verdict.')
            text(tr(message), 'dim')
        if main_idle and 'dispatch_id' in row:
            label = tr('[Retry review]') if pending else tr('[Review]')
            for part in wrap_text(label,width):
                if targets is not None:
                    targets[len(lines)] = (row['dispatch_id'],row['attempt'])
                lines.append([(0,part,'button')])
        lines.append([])
    if not jobs:
        text(tr('No dispatched agents yet.'),'dim')
    return lines


def palette():
    styles = {'normal':0,'heading':curses.A_BOLD,'dim':curses.A_DIM,
              'band':curses.A_REVERSE|curses.A_BOLD,'alert':curses.A_BOLD,
              'context':0,'active':curses.A_BOLD,'button':curses.A_UNDERLINE}
    if curses.has_colors():
        try:
            curses.use_default_colors()
            # Base ANSI slots follow the terminal theme, which can be monochrome.
            blue, red = (75, 203) if curses.COLORS >= 256 else (curses.COLOR_BLUE, curses.COLOR_RED)
            for i,(style,fg,bg) in enumerate([('band',curses.COLOR_BLACK,curses.COLOR_CYAN),
                    ('alert',red,-1),('active',blue,-1),
                    ('context',curses.COLOR_CYAN,-1)],1):
                curses.init_pair(i,fg,bg)
                styles[style]=curses.color_pair(i) | (0 if style=='context' else curses.A_BOLD)
        except curses.error:
            pass
    return styles


def monitor(win, binding, db):
    configure(win)
    styles = palette()
    dispatch.setup(db.conn)
    paths, cache = {binding.session:Path(binding.history)}, {}
    first = 0
    refresh = 0
    rows = []
    error = ''
    notice = ''
    mouse = MouseInput()
    budget = token_budget(preference_root())
    selected = retry = None
    while True:
        if time.monotonic() >= refresh:
            try:
                load_language(preference_root())
                live = {p['pane_id']:p for p in herdr('pane','list','--workspace',binding.workspace)['panes']}
                tabs = herdr('tab','list','--workspace',binding.workspace)['tabs']
                labels = {t['tab_id']:t.get('label') or str(t['number']) for t in tabs}
                parent = live.get(binding.pane,{})
                from .renewal import confirmed_successor
                binding = confirmed_successor(preference_root(), binding, parent, live)
                parent = live.get(binding.pane,{})
                main = dict(main=True, task=tr('Main session'),pane=binding.pane,terminal=binding.terminal,
                            tab=parent.get('tab_id','—'),state='')
                jobs = [dict(j,main=False) for j in dispatch.records(db.conn,binding.key)]
                main['label'] = labels.get(main['tab'],main['tab'])
                for job in jobs:
                    job['label'] = labels.get(job['tab']) or f"Dispatch · {job['item']}"
                rows = [(row,*describe(row,live.get(row['pane']),binding,paths,cache)) for row in [main,*jobs]]
                error = ''
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
                error = str(exc)
            refresh = time.monotonic()+3
        h,w = win.getmaxyx()
        win.erase()
        width=max(1,w-1)
        targets = {}
        lines=monitor_lines(rows,width,targets,budget)
        totals=[value for row,_,value in rows if not row['main']]
        if any(value is not None for value in totals):
            label=tr('Cumulative dispatch tokens') if None not in totals else tr('Known cumulative dispatch tokens')
            total=sum(value for value in totals if value is not None)
            footer=wrap_text(f'{label}  {total:,}',width)
        else:
            footer=[]
        footer.append(tr('[B] Reference per agent')+' '+f'{budget:,}'.replace(',',tr(',')))
        if notice:
            footer = wrap_text(notice,width) + footer
        if error:
            lines.extend([[(0,line,'alert')] for line in wrap_text(error,width)])
        # At very small heights let the footer scroll as part of the content.
        if h<len(footer)+4:
            lines.extend([[(0,line,'dim')] for line in footer])
            footer=[]
        hint=h>=3
        room=max(1,h-len(footer)-int(hint))
        first=max(0,min(first,len(lines)-room))
        layout = Layout(w, room)
        for y,line in enumerate(lines[first:first+room]):
            for x,value,style in line:
                action = targets.get(first+y)
                attr = styles[style]
                if action:
                    layout.add(y,x,value,action=action)
                    if action == selected:
                        attr |= curses.A_REVERSE
                put(win,y,fit(value,width-x),attr,x)
        mouse.sync(layout)
        for y,value in enumerate(footer,h-int(hint)-len(footer)):
            put(win,y,value,styles['dim'])
        if hint:
            help_text=tr('↑ ↓ Scroll · Esc Close') if len(lines)>room else tr('Esc Close')
            if targets:
                help_text = tr('Tab Select · Enter Review · ↑ ↓ Scroll · Esc Close')
            put(win,h-1,fit(help_text,width),styles['dim'])
        win.refresh()
        try:key=win.get_wch()
        except curses.error:continue
        if key in ('B','b'):
            try:
                budget = edit_budget(win,preference_root(),budget)
            except OSError as exc:
                notice = str(exc)
            continue
        if key=='\x1b':
            if retry:
                retry=None;notice=''
                continue
            return
        if key==curses.KEY_DOWN:first+=1
        if key==curses.KEY_UP:first-=1
        if key==curses.KEY_NPAGE:first+=room
        if key==curses.KEY_PPAGE:first-=room
        action = None
        if key=='\t' and targets:
            actions=list(dict.fromkeys(targets.values()))
            selected=actions[(actions.index(selected)+1)%len(actions)] if selected in actions else actions[0]
            y=next(y for y,target in targets.items() if target==selected)
            first=min(y,max(first,y-room+1))
            retry=None;notice=''
        elif key in ('\r','\n',curses.KEY_ENTER):
            if any(t.action==selected for t in layout.targets):
                action=selected
        elif key==curses.KEY_MOUSE:
            try:
                _,x,y,_,mask=curses.getmouse()
                if mask & curses.BUTTON4_PRESSED:first-=3
                elif mask & getattr(curses,'BUTTON5_PRESSED',0):first+=3
                else:action=mouse.event(x,y,mask,layout)
            except curses.error:pass
        if action:
            selected=action
            pending=any(not row['main'] and (row['dispatch_id'],row['attempt'])==action
                        and row['attempt'] and not row['verdict'] for row,_,_ in rows)
            if pending and (retry!=action or key==curses.KEY_MOUSE):
                retry=action
                notice=tr('Replace the previous request? Enter to retry · Esc to cancel')
                continue
            retry=None
            try:
                dispatch.request_verdict(db.conn,binding,preference_root(),*action)
                notice=''
            except (OSError,ValueError,RuntimeError,sqlite3.Error,subprocess.SubprocessError) as exc:
                notice=str(exc)
            refresh=0
