"""Small curses view; keyboard actions also usable by integration tests."""
import curses
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from .core import Store
from .runtime import send, send_selected, queue, queue_selected, QueueOffer
from .projects import project_store
from .ui_layout import (MouseInput, panel_layout, picker_layout, terminal_text,
                        queue_confirmation_layout, done_confirmation_layout)
from .collection_request import request_collection


def page_items(items,page,size=26):return items[page*size:(page+1)*size]


class DoneOffer(RuntimeError):
    def __init__(self,chosen):
        super().__init__('Confirme a conclusão dos itens selecionados')
        self.items=tuple((item['id'],item['text']) for item in chosen)


def confirm_done(store,offer):
    with store.conn:
        store.conn.execute('BEGIN IMMEDIATE')
        current={item['id']:item for item in store.items()}
        if any(item_id not in current or not current[item_id]['selected'] or
               current[item_id]['text']!=text for item_id,text in offer.items):
            raise RuntimeError('A seleção mudou. Revise os itens e confirme novamente.')
        store.done([item_id for item_id,_ in offer.items])
    return len(offer.items)


def handle_key(key,store,visible,submit,export):
    if len(key)==1 and 'a'<=key<='z':
        index=ord(key)-ord('a')
        if index<len(visible):store.toggle(visible[index]['id'])
    elif key=='1':return f'Enviados: {send_selected(store,submit)}. Permanecem até conclusão.'
    elif key=='2':
        chosen=[i for i in store.items() if i['selected']]
        if chosen:raise DoneOffer(chosen)
        return 'Nenhum item selecionado.'
    elif key=='3':
        export.parent.mkdir(parents=True,exist_ok=True)
        export.write_text(store.export_md());return 'Exportado: '+str(export)
    elif key=='4':return f'Importados: {store.import_md(export.read_text())}'
    return ''


def handle_action(action,store,visible,submit,export):
    if not action:return ''
    kind,value=action
    if kind=='item':
        if any(i['id']==value for i in store.items()):store.toggle(value)
    elif kind=='key':return handle_key(value,store,visible,submit,export)
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
    styles={'normal':0,'title':curses.A_BOLD,'selected':curses.A_REVERSE|curses.A_BOLD,'button':curses.A_REVERSE}
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


def panel(win,binding,root,binding_file):
    configure(win)
    db=project_store(root,binding)
    worker=subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'left-undone'),'collect','--binding',str(binding_file)],start_new_session=True)
    page=0;notice='';export=root/'exports'/binding.key/'latest.md';mouse=MouseInput();pending=None
    try:
        while True:
            h,w=win.getmaxyx();items=db.items()
            try:status=json.loads((root/(binding.key+'.status.json')).read_text()).get('message','')
            except (OSError,ValueError):status='Iniciando coleta…'
            if worker.poll() is not None:status='Coletor parou. Feche e reabra o painel. '+status
            subtitle=f'{binding.kind} · {binding.pane}'
            if getattr(db,'project',None):subtitle+=' · '+Path(db.project).name
            if pending:
                build=done_confirmation_layout if isinstance(pending,DoneOffer) else queue_confirmation_layout
                layout=build(w,h,len(pending.items))
            else:layout=panel_layout(items,w,h,page,subtitle,status,notice)
            if not pending:page=layout.page
            mouse.sync(layout);render(win,layout)
            try:key=win.get_wch()
            except curses.error:continue
            action=input_action(key,mouse,layout)
            if not action:continue
            if pending:
                if action in (('close',None),('key','2')):
                    notice=('Conclusão cancelada.' if isinstance(pending,DoneOffer) else 'Envio cancelado.')+' Seleção preservada.'
                    pending=None
                elif action==('key','1') and any(target.action==action for target in layout.targets):
                    try:
                        if isinstance(pending,DoneOffer):notice=f'Concluídos: {confirm_done(db,pending)}'
                        else:
                            count=queue_selected(db,pending,lambda text:queue(binding,text))
                            notice=f'Na fila: {count}. Permanecem até conclusão.'
                    except Exception as e:notice=str(e)
                    pending=None
                continue
            if action[0]=='close':break
            if action[0]=='next':page=min(page+1,layout.pages-1);continue
            if action[0]=='prev':page=max(0,page-1);continue
            if action==('key','5'):
                try:notice=request_collection(worker,root/(binding.key+'.collect-request'))
                except (OSError,RuntimeError) as e:notice=str(e)
                continue
            try:notice=handle_action(action,db,layout.visible,lambda text:send(binding,text),export) or notice
            except DoneOffer as offer:pending=offer
            except QueueOffer as offer:
                if binding.kind=='codex':pending=offer
                else:notice='A fila do Claude não está disponível nesta versão. Aguarde o agente terminar.'
            except Exception as e:notice=str(e)
    finally:
        worker.terminate()
        try:worker.wait(timeout=7)
        except subprocess.TimeoutExpired:os.killpg(worker.pid,signal.SIGKILL);worker.wait()
        db.close()


def picker(win,bindings,errors,choose,counts=None):
    configure(win);cursor=0;page=0;mouse=MouseInput();notice='; '.join(errors);size=None
    counts=counts or {}
    items=[{'id':i,'text':f'{b.kind} · {b.pane} · {b.session[:12]} · conta {Path(b.account).name}'
            +(f' · {counts[b.key] if counts[b.key] is not None else "?"} pendências' if b.key in counts else '')}
           for i,b in enumerate(bindings)]
    while True:
        h,w=win.getmaxyx()
        layout=picker_layout(items,w,h,page,cursor,notice,follow_cursor=size!=(w,h))
        size=(w,h)
        page=layout.page;mouse.sync(layout);render(win,layout)
        try:key=win.get_wch()
        except curses.error:continue
        if key in (curses.KEY_UP,curses.KEY_DOWN):
            cursor=max(0,min(len(items)-1,cursor+(1 if key==curses.KEY_DOWN else -1)))
            page=picker_layout(items,w,h,page,cursor,notice,follow_cursor=True).page
            continue
        action=('open',None) if key in ('\n','\r') else input_action(key,mouse,layout)
        if not action:continue
        kind,value=action
        if kind=='close':return
        if kind=='choose':cursor=value
        if kind in ('next','prev'):
            page=max(0,min(layout.pages-1,page+(1 if kind=='next' else -1)))
            visible=picker_layout(items,w,h,page,cursor).visible
            if visible:cursor=visible[0]['id']
        if kind=='open' and bindings and any(i['id']==cursor for i in layout.visible):
            try:choose(bindings[cursor]);return
            except (RuntimeError,OSError,ValueError) as e:notice=str(e)
