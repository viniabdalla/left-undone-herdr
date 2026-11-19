"""Small curses view; keyboard actions also usable by integration tests."""
import curses
import json
import os
import signal
import subprocess
import sys
import time
from tempfile import TemporaryFile
from . import dispatch
from .ui_layout import Layout, wrap_text
from pathlib import Path
from .language import collector_status, load_language, preference_root, toggle_language, tr
from .exchange import export_project, import_choices, import_selected
from .runtime import send, send_selected, queue, queue_selected, QueueOffer
from .projects import project_store
from .ui_layout import (MouseInput, import_layout, panel_layout, picker_layout, terminal_text,
                        confirmation_layout, queue_confirmation_layout, done_confirmation_layout, readable_panel_layout, project_label,
                        conversation_layout, dispatch_choice_layout, close_choice_layout)
from .collection_request import request_collection


def page_items(items,page,size=26):return items[page*size:(page+1)*size]


class DoneOffer(RuntimeError):
    def __init__(self,chosen):
        super().__init__(tr('Confirm completion of selected items'))
        self.items=tuple((item['id'],item['text']) for item in chosen)


def confirm_done(store,offer):
    with store.conn:
        store.conn.execute('BEGIN IMMEDIATE')
        current={item['id']:item for item in store.items()}
        if any(item_id not in current or not current[item_id]['selected'] or
               current[item_id]['text']!=text for item_id,text in offer.items):
            raise RuntimeError(tr('Selection changed. Review the items and confirm again.'))
        store.done([item_id for item_id,_ in offer.items])
    return len(offer.items)


class DispatchOffer:
    """Several tasks selected: ask whether each gets its own tab or all share one."""
    def __init__(self,count,plan):self.count=count;self.plan=plan


class CloseOffer:
    """Closing asks for confirmation and offers to export first."""


def open_monitor(root,binding,binding_file):
    """Open the agents monitor in a split below this panel, or focus it."""
    from .runtime import herdr, PLUGIN
    mapping=root/(binding.key+'.agents.json')
    try:old=json.loads(mapping.read_text())
    except (OSError,ValueError):old=None
    if old:
        try:live=herdr('pane','current','--pane',old['pane'])['pane']
        except RuntimeError:live={}
        if live.get('terminal_id')==old.get('terminal'):
            herdr('plugin','pane','focus',old['pane'])
            return tr('Agents monitor focused.')
    below=os.environ.get('HERDR_PANE_ID') or binding.pane
    result=herdr('plugin','pane','open','--plugin',PLUGIN,'--entrypoint','agents','--placement','split',
                 '--target-pane',below,'--direction','down','--no-focus',
                 '--env','LEFT_UNDONE_BINDING='+str(binding_file),'--env','LEFT_UNDONE_STATE_DIR='+str(root))
    info=result.get('plugin_pane',result).get('pane') or {}
    if info.get('pane_id'):
        tmp=mapping.with_suffix('.tmp.'+str(os.getpid()))
        tmp.write_text(json.dumps({'pane':info['pane_id'],'terminal':info.get('terminal_id')}));tmp.replace(mapping)
    return tr('Agents monitor opened below.')


def handle_key(key,store,visible,submit):
    if len(key)==1 and 'a'<=key<='z':
        index=ord(key)-ord('a')
        if index<len(visible):store.toggle(visible[index]['id'])
    elif key=='1':return tr('Sent: {0}. Items stay open until completed.').format(send_selected(store,submit))
    elif key=='2':
        chosen=[i for i in store.items() if i['selected']]
        if chosen:raise DoneOffer(chosen)
        return tr('No item selected.')
    return ''


def handle_action(action,store,visible,submit):
    if not action:return ''
    kind,value=action
    if kind=='item':
        if any(i['id']==value for i in store.items()):store.toggle(value)
    elif kind=='key':return handle_key(value,store,visible,submit)
    return ''


def configure(win):
    try:curses.curs_set(0)
    except curses.error:pass
    win.keypad(True);win.timeout(300)
    try:
        curses.mouseinterval(150)
        curses.mousemask(curses.BUTTON1_PRESSED|curses.BUTTON1_RELEASED|curses.BUTTON1_CLICKED|
                         curses.BUTTON4_PRESSED|getattr(curses,'BUTTON5_PRESSED',0))
    except curses.error:pass


def put(win,y,text,attr=0,x=0):
    h,w=win.getmaxyx()
    if 0<=y<h and 0<=x<w-1:
        safe=terminal_text(text)
        try:win.addstr(y,x,safe,attr)
        except curses.error:pass


def render(win,layout):
    styles={'normal':0,'title':curses.A_BOLD,'selected':curses.A_REVERSE|curses.A_BOLD,'button':curses.A_REVERSE,'dim':curses.A_DIM}
    win.erase()
    for line in layout.lines:put(win,line.y,line.text,styles[line.style],line.x)
    win.refresh()


def input_action(key,mouse,layout):
    if key==curses.KEY_MOUSE:
        try:
            _,x,y,_,mask=curses.getmouse()
            return mouse.event(x,y,mask,layout)
        except curses.error:return None
    if key=='\x1b':return ('close',None)
    if key==curses.KEY_RIGHT:return ('next',None)
    if key==curses.KEY_LEFT:return ('prev',None)
    if isinstance(key,str):return ('key',key)
    return None


def pick_imports(win, choices, project, title=None, hint=None):
    selected = set()
    mouse = MouseInput()
    page = 0
    while True:
        height, width = win.getmaxyx()
        layout = import_layout(choices, selected, width, height, page, project, title, hint)
        page = layout.page
        mouse.sync(layout)
        render(win, layout)
        try:
            key = win.get_wch()
        except curses.error:
            continue
        action = input_action(key, mouse, layout)
        if not action:
            continue
        kind, value = action
        if kind == 'close':
            return None
        if kind in ('prev', 'next'):
            page = max(0, min(layout.pages - 1, page + (1 if kind == 'next' else -1)))
        if action == ('key', '1') and any(target.action == action for target in layout.targets):
            return [choice['id'] for choice in choices if choice['id'] in selected]
        if kind == 'key' and len(value) == 1 and 'a' <= value <= 'z':
            index = ord(value) - ord('a')
            if index < len(layout.visible) and not layout.visible[index]['imported']:
                kind, value = 'item', layout.visible[index]['id']
        if kind == 'item':
            if value in selected:
                selected.remove(value)
            else:
                selected.add(value)


def dispatch_reports(win, db):
    def content():
        for job in dispatch.records(db.conn,db.session):
            header = ' · '.join(filter(None, [tr(dispatch.STATES[job['state']]), job['tab'], job['model'], job['effort']]))
            yield from (job['task'],header,job['summary'],'')
    report_view(win,tr('Dispatch reports'),content,'R')


def report_view(win,title,content,shortcut):
    offset = 0
    mouse = MouseInput()
    while True:
        height,width = win.getmaxyx()
        layout = Layout(width,height)
        lines = []
        for value in content():
            lines.extend(wrap_text(value,max(1,width-2)) if value else [''])
        size = max(1,height-3)
        offset = max(0,min(offset,max(0,len(lines)-size)))
        layout.add(0,0,title,'title')
        for y,line in enumerate(lines[offset:offset+size],1):
            layout.add(y,0,line)
        layout.add(height-1,0,'[<]',action=('prev',None))
        layout.add(height-1,4,'[>]',action=('next',None))
        layout.add(height-1,8,tr('[Close]'),action=('close',None))
        mouse.sync(layout);render(win,layout)
        try:key=win.get_wch()
        except curses.error:continue
        action=input_action(key,mouse,layout)
        if action==('close',None) or key==shortcut:return
        if action==('next',None) or key==curses.KEY_DOWN:offset+=size
        if action==('prev',None) or key==curses.KEY_UP:offset-=size


def review_lines(process,errors,db):
    code = process.poll()
    if code is None:
        return [tr('Checking task completion…')]
    if code:
        errors.seek(0)
        return [errors.read().strip() or tr('Review failed')]
    row = db.conn.execute('SELECT report FROM manual_reviews WHERE session=?',(db.session,)).fetchone()
    report = json.loads(row[0])
    labels = {'done':tr('Completed'),'open':tr('Open')}
    counts = {state:sum(i['state']==state for i in report) for state in labels}
    lines = [' · '.join(f'{label} {counts[state]}' for state,label in labels.items())]
    for item in report:
        lines.extend(['',labels[item['state']]+' · '+item['task'],item['reason']])
        if item.get('delivery') == 'sent':
            lines.append(tr('Sent to the main session'))
        elif item.get('delivery') == 'queued':
            lines.append(tr('Queued for the main session'))
        elif item.get('delivery') == 'unconfirmed':
            lines.append(tr('Delivery unconfirmed') + ' · ' + item['error'])
        if item.get('quote'):
            lines.append(item['source']+' · '+item['quote'])
    return lines


def panel(win,binding,root,binding_file):
    load_language(root)
    configure(win)
    db=project_store(root,binding)
    exchange_project=getattr(db,'project',None)
    dispatch.setup(db.conn)
    last_dispatch = None
    review_worker = None
    review_errors = None
    renewal_worker = None
    from .renewal import journal, pending_confirmation
    state = journal(root,binding)
    confirmation = pending_confirmation(root,binding,db)
    renewal_errors = None
    checked_tabs = 0
    history=False;projects=None;project_cursor=0
    worker=subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'left-undone'),'collect','--binding',str(binding_file)],start_new_session=True)
    page=0;notice='';mouse=MouseInput();pending=None;newest_first=True
    old_pane = os.environ.pop('LEFT_UNDONE_CLOSE_SOURCE',None)
    if old_pane:
        notice = tr('Connected. You can close the old pane {0}.').format(old_pane)
    offer = os.environ.pop('LEFT_UNDONE_OFFER_IMPORT', None)
    if exchange_project and not old_pane:
        try:
            waiting = [c for c in import_choices(db, exchange_project) if not c['imported']]
        except Exception:  # Best effort: the list must open even if the repo is unreadable.
            waiting = []
        if waiting and offer:
            ids = pick_imports(win, import_choices(db, exchange_project), exchange_project,
                               title=tr('Saved tasks in this repo'),
                               hint=tr('Choose what to bring into this conversation. Esc skips.'))
            notice = (tr('Nothing imported. Press 4 to import later.') if not ids else
                      tr('Imported: {0}').format(import_selected(db, ids, exchange_project)))
        elif waiting:
            notice = tr('{0} saved tasks in this repo, none imported. Press 4 to import.').format(len(waiting))
    try:
        while True:
            h,w=win.getmaxyx();items=db.history_items() if history else db.items()
            try:status=json.loads((root/(binding.key+'.status.json')).read_text()).get('message','')
            except (OSError,ValueError):status=tr('Starting collection…')
            status=collector_status(status)
            if worker.poll() is not None:status=tr('Collector stopped. Close and reopen the panel. ')+status
            subtitle=f'{binding.kind} · {binding.pane}'
            if getattr(db,'project',None):subtitle+=' · '+Path(db.project).name
            jobs = dispatch.records(db.conn,db.session,latest=True)
            if jobs and time.monotonic()-checked_tabs > 10:
                dispatch.check_tabs(db.conn, db.session, binding.workspace)
                checked_tabs = time.monotonic()
            if jobs:
                latest = jobs[0]
                snapshot = tuple(latest)
                if snapshot != last_dispatch:
                    notice = ''
                    last_dispatch = snapshot
                status = tr(dispatch.STATES[latest['state']])+' · '+(latest['summary'] or latest['tab'] or latest['task'])
            if renewal_worker is not None:
                result = renewal_worker.poll()
                if result is None:
                    notice = tr('Preparing handoff…')
                    if state.exists():
                        stage = json.loads(state.read_text())['stage']
                        notice = tr({'preparing':'Preparing handoff…','switching':'Opening new conversation…',
                                     'initializing':'Running /init…','restoring':'Restoring handoff…',
                                     'complete':'Restoring handoff…'}.get(stage,'Opening new conversation…'))
                else:
                    renewal_errors.seek(0)
                    notice = renewal_errors.read().strip() or tr('Handoff finished')
                    renewal_errors.close()
                    renewal_errors = renewal_worker = None
                    job = json.loads(state.read_text()) if state.exists() else {}
                    if result == 3 and job.get('stage') == 'confirm':
                        confirmation = job
                        from .runtime import herdr
                        pane = os.environ.get('HERDR_PANE_ID')
                        if pane:
                            try:
                                if herdr('pane','layout','--pane',pane)['layout']['focused_pane_id'] == binding.pane:
                                    herdr('plugin','pane','focus',pane)
                            except RuntimeError:
                                pass
                    if result == 0:
                        from .runtime import Binding
                        return Binding(**json.loads(journal(root,binding).read_text())['binding'])
            if confirmation:
                question = (tr('Codex is in another conversation. Carry these tasks into a new tab?')
                            if confirmation['active'] != binding.session else
                            tr('Prepare the handoff and open the agent in a new tab?'))
                layout=confirmation_layout(w,h,len(confirmation['selection']),tr('CONFIRM HANDOFF'),
                                           question,tr('[H Confirm handoff]'))
            elif renewal_worker is not None:
                layout=Layout(w,h)
                layout.add(0,0,tr('HANDOFF'),'title')
                for y,line in enumerate(wrap_text(notice,max(1,w-1)),2):
                    layout.add(y,0,line)
            elif isinstance(pending,DispatchOffer):
                layout=dispatch_choice_layout(w,h,pending.count,pending.plan)
            elif isinstance(pending,CloseOffer):
                layout=close_choice_layout(w,h,len(db.items()) if exchange_project else 0)
            elif pending:
                build=done_confirmation_layout if isinstance(pending,DoneOffer) else queue_confirmation_layout
                layout=build(w,h,len(pending.items))
            elif projects is not None:
                rows=[{'id':i,'heading':project_label(p)+(tr(' · current') if p==exchange_project else ''),'text':p} for i,p in enumerate(projects)]
                layout=picker_layout(rows,w,h,page,project_cursor,notice=tr('Conversation: {0} · {1}').format(binding.kind, binding.pane),
                                     follow_cursor=True,title=tr('Choose exchange project'))
            elif getattr(db,'project',None):
                layout=readable_panel_layout(items,w,h,page,exchange_project,status,notice,newest_first=newest_first,history=history,recipient=f'{binding.kind} · {binding.session[:8]} · '+tr('account {0}').format(Path(binding.account).name)+f' · {binding.pane}',dispatch_reports=bool(jobs))
            else:layout=panel_layout(items,w,h,page,subtitle,status,notice,newest_first=newest_first,dispatch_reports=bool(jobs))
            if not pending:page=layout.page
            mouse.sync(layout);render(win,layout)
            try:key=win.get_wch()
            except curses.error:continue
            if projects is not None and key in (curses.KEY_UP,curses.KEY_DOWN):
                project_cursor=max(0,min(len(projects)-1,project_cursor+(1 if key==curses.KEY_DOWN else -1)))
                continue
            if projects is not None and key in ('\n','\r'):action=('open',None)
            else:action=input_action(key,mouse,layout)
            if not action:continue
            approval = None
            if confirmation:
                if action in (('close',None),('key','2')):
                    confirmation = pending_confirmation(root,binding,db,cancel=confirmation['approval'])
                    notice=''
                    continue
                if (action[0]!='key' or action[1] not in ('1','h','H','\r','\n') or
                        not any(target.action==('key','1') for target in layout.targets)):
                    continue
                approval=confirmation['approval']
                confirmation=None
                action=('key','H')
            if renewal_worker is not None and action[0]!='close':continue
            if action == ('key', '9') and not pending:
                try:
                    toggle_language(root)
                    page=0;notice=''
                except OSError as error:
                    notice=str(error)
                continue
            if projects is not None:
                if action[0]=='close':projects=None;page=0
                elif action[0]=='choose':project_cursor=action[1]
                elif action[0] in ('prev','next'):
                    project_cursor=max(0,min(len(projects)-1,project_cursor+(1 if action[0]=='next' else -1)))
                elif action[0]=='open' and projects:
                    exchange_project=projects[project_cursor]
                    projects=None;page=0;notice=''
                continue
            if isinstance(pending,DispatchOffer):
                offer=pending
                if action==('close',None):
                    pending=None;notice=tr('Dispatch canceled.')+tr(' Selection kept.')
                elif action in (('key','1'),('key','2')):
                    pending=None
                    try:notice=dispatch.request(db,binding,root,plan=offer.plan,together=action==('key','2'))
                    except Exception as e:notice=str(e)
                continue
            if isinstance(pending,CloseOffer):
                if action==('close',None):
                    pending=None;notice=''
                elif action==('key','1') and any(target.action==action for target in layout.targets):
                    try:
                        export_project(db, exchange_project);break
                    except Exception as e:pending=None;notice=str(e)
                elif action==('key','2'):break
                continue
            if pending:
                if action in (('close',None),('key','2')):
                    notice=(tr('Completion canceled.') if isinstance(pending,DoneOffer) else tr('Send canceled.'))+tr(' Selection kept.')
                    pending=None
                elif action==('key','1') and any(target.action==action for target in layout.targets):
                    try:
                        if isinstance(pending,DoneOffer):notice=tr('Completed: {0}').format(confirm_done(db,pending))
                        else:
                            count=queue_selected(db,pending,lambda text:queue(binding,text))
                            notice=tr('Queued: {0}. Items stay open until completed.').format(count)
                    except Exception as e:notice=str(e)
                    pending=None
                continue
            if action[0]=='close':
                if (exchange_project or db.items()) and renewal_worker is None:pending=CloseOffer();continue
                break
            if action==('key','8') and getattr(db,'project',None):
                projects=db.available_projects();project_cursor=projects.index(exchange_project);page=0
                continue
            if action==('key','7') and getattr(db,'project',None):
                history=not history;page=0;notice=''
                continue
            if action==('key','6'):
                newest_first=not newest_first;page=0
                continue
            if action[0]=='next':page=min(page+1,layout.pages-1);continue
            if action[0]=='prev':page=max(0,page-1);continue
            if action==('key','V'):
                if review_worker is None:
                    review_errors = TemporaryFile(mode='w+',encoding='utf-8')
                    review_worker = subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'left-undone'),
                                                      'review','--binding',str(binding_file)], stdout=subprocess.DEVNULL,
                                                     stderr=review_errors,start_new_session=True)
                report_view(win,tr('Review'),lambda:review_lines(review_worker,review_errors,db),'V')
                if review_worker.poll() is not None:
                    review_worker=None
                    review_errors.close()
                    review_errors=None
                continue
            if action==('key','5'):
                try:notice=request_collection(worker,root/(binding.key+'.collect-request'))
                except (OSError,RuntimeError) as e:notice=str(e)
                continue
            if action==('key','R') and jobs:
                dispatch_reports(win,db);notice=''
                continue
            if action==('key','M'):
                try:notice=open_monitor(root,binding,binding_file)
                except Exception as e:notice=str(e)
                continue
            if history:continue
            try:
                if action==('key','H') and getattr(db,'project',None):
                    renewal_errors = TemporaryFile(mode='w+',encoding='utf-8')
                    renewal_worker = subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'left-undone'),
                                                       'renew','--binding',str(binding_file),
                                                       *(['--confirm-source',approval] if approval else [])],
                                                      stderr=renewal_errors,stdout=subprocess.DEVNULL)
                elif action in (('key','P'),('key','0')):
                    count=sum(bool(i['selected']) for i in db.items())
                    if count>1:pending=DispatchOffer(count,action==('key','P'))
                    else:notice=dispatch.request(db,binding,root,plan=action==('key','P'))

                elif action==('key','3'):
                    path=export_project(db, exchange_project)
                    notice=tr('Exported: ')+str(path)
                elif action==('key','4'):
                    choices=import_choices(db, exchange_project)
                    ids=pick_imports(win, choices, exchange_project)
                    notice=(tr('Import canceled.') if ids is None else
                            tr('Imported: {0}').format(import_selected(db, ids, exchange_project)))
                else:
                    notice=handle_action(action,db,layout.visible,lambda text:send(binding,text)) or notice
            except DoneOffer as offer:pending=offer
            except QueueOffer as offer:
                if binding.kind=='codex':pending=offer
                else:notice=tr('Claude queuing is unavailable in this version. Wait for the agent to finish.')
            except Exception as e:notice=str(e)
    finally:
        if renewal_worker is not None and renewal_worker.poll() is None:
            renewal_worker.terminate();renewal_worker.wait()
        if renewal_errors is not None:renewal_errors.close()
        if review_errors is not None:review_errors.close()
        worker.terminate()
        try:worker.wait(timeout=7)
        except subprocess.TimeoutExpired:os.killpg(worker.pid,signal.SIGKILL);worker.wait()
        db.close()


def conversation_title(title,suffix=None):
    """Herdr titles often end in ' | <folder>'; the picker heading already names it."""
    title=(title or '').strip()
    if suffix and title.endswith(' | '+suffix):title=title[:-len(suffix)-3].strip()
    return title or tr('Untitled in Herdr')


def picker(win,bindings,errors,choose,counts=None,titles=None,heading=None,suffix=None):
    """Choose one verified conversation. Returns whatever choose returns."""
    root=preference_root()
    load_language(root)
    configure(win);cursor=0;page=0;mouse=MouseInput();notice='; '.join(errors);size=None
    counts=counts or {}
    titles=titles or {}
    while True:
        items=[]
        for i,b in enumerate(bindings):
            detail=tr('{0} · account {1}').format(b.kind.capitalize(), Path(b.account).name)
            if b.key in counts:
                detail+=tr(' · {0} open tasks').format(counts[b.key] if counts[b.key] is not None else '?')
            items.append({'id':i,'title':conversation_title(titles.get(b.pane),suffix),'detail':detail,'pane':b.pane})
        h,w=win.getmaxyx()
        layout=conversation_layout(items,w,h,None if size!=(w,h) else page,cursor,heading or tr('Herdr conversations'),notice)
        size=(w,h)
        page=layout.page;mouse.sync(layout);render(win,layout)
        try:key=win.get_wch()
        except curses.error:continue
        if key in (curses.KEY_UP,curses.KEY_DOWN):
            cursor=max(0,min(len(items)-1,cursor+(1 if key==curses.KEY_DOWN else -1)))
            page=conversation_layout(items,w,h,None,cursor,'',notice).page
            continue
        action=('open',None) if key in ('\n','\r') else input_action(key,mouse,layout)
        if not action:continue
        kind,value=action
        if action == ('key', '9'):
            try:
                toggle_language(root)
                notice=''
            except OSError as error:
                notice=str(error)
            continue
        if kind=='close':return None
        if kind=='choose':cursor=value
        if kind in ('next','prev'):
            page=max(0,min(layout.pages-1,page+(1 if kind=='next' else -1)))
            visible=conversation_layout(items,w,h,page,cursor,'',notice).visible
            if visible:cursor=visible[0]['id']
        if kind=='open' and bindings and any(i['id']==cursor for i in layout.visible):
            try:return choose(bindings[cursor])
            except (RuntimeError,OSError,ValueError) as e:notice=str(e)
