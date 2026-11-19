"""Cell-aware terminal layouts and mouse hit testing, independent of curses I/O."""
import curses
import math
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from .language import language_button, stored_label, tr


def char_width(char):
    if unicodedata.combining(char) or unicodedata.category(char) in ('Mn','Me','Cf'):return 0
    return 2 if unicodedata.east_asian_width(char) in ('W','F') else 1


def cell_width(text):return sum(char_width(c) for c in text)


def terminal_text(text):
    return ''.join(c if c.isprintable() or c=='\u200d' else ' ' for c in str(text))


def wrap_text(text,width):
    width=max(1,width);out=[];line=''
    for word in terminal_text(text).split():
        if line and cell_width(line+' '+word)<=width:
            line+=' '+word;continue
        if line:out.append(line);line=''
        for char in word:
            if line and cell_width(line+char)>width:out.append(line);line=''
            line+=char
    if line:out.append(line)
    return out or ['']


def fit(text,width):
    out=''
    for c in terminal_text(text):
        if cell_width(out+c)>width:break
        out+=c
    return out


@dataclass
class Line:
    y:int
    x:int
    text:str
    style:str='normal'
    action:tuple|None=None


@dataclass
class Target:
    x:int
    y:int
    width:int
    action:tuple


@dataclass
class Layout:
    width:int
    height:int
    page:int=0
    pages:int=1
    lines:list=field(default_factory=list)
    targets:list=field(default_factory=list)
    visible:list=field(default_factory=list)

    def add(self,y,x,text,style='normal',action=None,target_width=None):
        if not (0<=y<self.height and 0<=x<self.width-1):return
        text=fit(text,self.width-1-x)
        self.lines.append(Line(y,x,text,style,action))
        if action and text:
            self.targets.append(Target(x,y,min(target_width or cell_width(text),self.width-1-x),action))

    def hit(self,x,y):
        for t in self.targets:
            if t.y==y and t.x<=x<t.x+t.width:return t.action
        return None

    @property
    def signature(self):
        return self.width,self.height,self.page,tuple((t.x,t.y,t.width,t.action) for t in self.targets)


def buttons(labels,width):
    """Pack complete buttons onto as many rows as needed."""
    out=[];x=0;y=0
    for label,action in labels:
        label=fit(label,width)
        if x and x+cell_width(label)>width:y+=1;x=0
        out.append((y,x,label,action));x+=cell_width(label)+1
    return out, y+1 if out else 0


def creation_date(item):
    stamp=item.get('created_at')
    if type(stamp) not in (float,int) or not math.isfinite(stamp):return None
    try:return datetime.fromtimestamp(stamp)
    except (ValueError,OverflowError,OSError):return None


def sort_items(items,newest_first=True):
    direction=-1 if newest_first else 1
    return sorted(items,key=lambda i:(creation_date(i) is None,
        direction*i['created_at'] if creation_date(i) is not None else 0,direction*i['id']))


def pages_for(items,width,rows,picker=False,exchange=False):
    pages=[[]];used=0
    for item in items:
        origin={'task':tr('TASK'),'promise':tr('PROMISE'),'import':tr('IMPORTED')}.get(item.get('origin'),'')
        text=item['text'] if picker or exchange else f'{origin} · {item["text"]}'
        line_width=width-(2 if picker else 6)
        lines=wrap_text(text,line_width)
        if not picker and not exchange:
            created=creation_date(item)
            date=created.strftime('%d/%m/%Y %H:%M') if created else tr('unknown date')
            lines.extend(wrap_text(tr('Created: ')+date,line_width))
        if picker and item.get('heading'):
            heading=item['heading']
            if cell_width(terminal_text(heading))>line_width:
                heading=fit(heading,line_width-1)+'…'
            lines.insert(0,heading)
            if used and len(lines)<=rows and used+len(lines)>rows:
                pages.append([]);used=0
        while lines:
            if used==rows or len(pages[-1])==26:pages.append([]);used=0
            segment=lines[:rows-used];lines=lines[len(segment):]
            pages[-1].append((item,segment));used+=len(segment)
    return pages


def bounded_lines(text,width,count):
    if count<=0:return []
    rows=wrap_text(text,width)
    if len(rows)>count:rows=rows[:count];rows[-1]=fit(rows[-1],width-1)+'…'
    return rows+['']*(count-len(rows))


def build_layout(items,width,height,page,subtitle,status,notice,picker=False,cursor=0,title=None,dispatch_reports=False):
    layout=Layout(width,height);usable=max(1,width-1)
    title=title or (tr('Choose conversation') if picker else 'LEFT UNDONE')
    if width<18 or height<12:
        for y,line in enumerate(wrap_text(tr('Enlarge the panel to view the list.'),usable)):
            if y<height-1:layout.add(y,0,line)
        layout.add(height-1,0,tr('[Close]'),action=('close',None))
        return layout
    selected=sum(bool(i.get('selected')) for i in items)
    labels=[]
    if picker:
        if dispatch_reports:labels.append((tr('[R Dispatch reports]'), ('key','R')))
        labels.append((language_button(), ('key','9')))
        if items:labels.append((tr('[Open]'),('open',None)))
    else:
        if selected == 1:labels.extend([('[0 Dispatch Sub-Agent]',('key','0')), (tr('[P Dispatch Plan]'),('key','P'))])
        if selected:labels.extend([(tr('[1 Send {0}]').format(selected),('key','1')),(tr('[2 Mark complete {0}]').format(selected),('key','2'))])
        if dispatch_reports:labels.append((tr('[R Dispatch reports]'), ('key','R')))
        labels.append((language_button(), ('key','9')))
        labels.extend([(tr('[3 Export]'),('key','3')),(tr('[4 Import]'),('key','4')),
                       (tr('[5 Collect now]'),('key','5')),(tr('[V Review]'),('key','V'))])
    packed,button_rows=buttons(labels,usable)
    nav,nav_rows=buttons([('[<]',('prev',None)),('[>]',('next',None)),(tr('[Close]'),('close',None))],usable)
    if not picker and height - button_rows - nav_rows < 6:
        labels = [(f'[{action[1]}]' if action[1] in ('1','2','3','4','5','R','V') else label, action)
                  for label,action in labels]
        packed,button_rows=buttons(labels,usable)
    # Compact status/notice before sacrificing the list or its action buttons.
    messages=max(0,min(4,height-4-button_rows-nav_rows-1-1))
    status_rows=min(2,(messages+1)//2);notice_rows=messages-status_rows
    footer=messages+button_rows+nav_rows+1
    room=height-4-footer
    if room<1:
        layout.add(0,0,title,'title')
        layout.add(2,0,tr('Enlarge the panel'))
        layout.add(height-1,0,tr('[Close]'),action=('close',None))
        return layout
    pages=pages_for(items,usable,room,picker)
    page=max(0,min(page,len(pages)-1));layout.page=page;layout.pages=len(pages)
    layout.add(0,0,title,'title');layout.add(1,0,subtitle)
    layout.add(2,0,tr('{0} items · {1}/{2}').format(len(items), page+1, len(pages)))
    y=4
    for index,(item,lines) in enumerate(pages[page]):
        layout.visible.append(item)
        action=('choose' if picker else 'item',item['id'])
        chosen=item['id']==cursor if picker else bool(item.get('selected'))
        prefix=('> ' if chosen else '  ') if picker else f'{chr(97+index)} [{"x" if chosen else " "}] '
        for n,line in enumerate(lines):
            layout.add(y,0,(prefix if n==0 else ' '*len(prefix))+line,'selected' if chosen else 'normal',action,usable)
            y+=1
    if not items:layout.add(4,0,tr('No open tasks.') if not picker else tr('No conversations.'))
    y=height-footer
    for line in bounded_lines(status,usable,status_rows)+bounded_lines(notice,usable,notice_rows):layout.add(y,0,line);y+=1
    for row,x,label,action in packed:layout.add(y+row,x,label,'button',action)
    y+=button_rows
    for row,x,label,action in nav:layout.add(y+row,x,label,'button',action)
    layout.add(height-1,0,tr('Mouse / keys'))
    return layout


def panel_layout(items,width,height,page,subtitle,status,notice,newest_first=True,dispatch_reports=False):
    layout=build_layout(sort_items(items,newest_first),width,height,page,subtitle,status,notice,dispatch_reports=dispatch_reports)
    if width>=18 and any(t.action==('key','5') for t in layout.targets):
        order=(tr('Newest first') if newest_first else tr('Oldest first')) if width>=28 else (tr('Newest ↓') if newest_first else tr('Oldest ↑'))
        layout.add(3,0,'[6 '+order+']','button',('key','6'))
    return layout


def confirmation_layout(width,height,count,title,question,confirm_label):
    layout=Layout(width,height);usable=max(1,width-1)
    if width<18 or height<12:
        layout.add(0,0,tr('Enlarge the panel'))
        layout.add(height-1,0,tr('[2 Cancel]'),action=('key','2'))
        return layout
    layout.add(0,0,title,'title')
    layout.add(1,0,f'{count} '+('item' if count==1 else tr('items')))
    labels=[(confirm_label,('key','1')),
            (tr('[2 Cancel]'),('key','2'))]
    packed,rows=buttons(labels,usable)
    for y,line in enumerate(bounded_lines(question,usable,height-rows-4),3):
        layout.add(y,0,line)
    for row,x,label,action in packed:
        layout.add(height-rows-1+row,x,label,'button',action)
    layout.add(height-1,0,tr('Esc: cancel'))
    return layout


def queue_confirmation_layout(width,height,count):
    return confirmation_layout(width,height,count,tr('AGENT BUSY'),
        tr('The agent is working. Queue this request for later?'),
        tr('[1 Add to queue]') if width>=20 else tr('[1 Queue]'))


def done_confirmation_layout(width,height,count):
    question=(tr('Mark the selected item as complete?') if count==1 else
              tr('Mark the {0} selected items as complete?').format(count))
    return confirmation_layout(width,height,count,tr('MARK TASKS COMPLETE'),question,tr('[1 Confirm]'))


def picker_layout(items,width,height,page,cursor,notice='',follow_cursor=False,title=None):
    layout=build_layout(items,width,height,page,tr('Select and open'),'',notice,True,cursor,title)
    if follow_cursor and items and not any(i['id']==cursor for i in layout.visible):
        for candidate in range(layout.pages):
            other=build_layout(items,width,height,candidate,tr('Select and open'),'',notice,True,cursor,title)
            if any(i['id']==cursor for i in other.visible):return other
    return layout


def import_layout(choices, selected, width, height, page, project):
    layout = Layout(width, height)
    usable = max(1, width - 1)
    labels = [(tr('[1 Import {0}]').format(len(selected)), ('key', '1') if selected else None)]
    labels.extend([('[<]', ('prev', None)), ('[>]', ('next', None)),
                   (tr('[Esc Cancel]'), ('close', None))])
    controls, control_rows = buttons(labels, usable)
    room = height - control_rows - 4
    if room < 1 or width < 18:
        layout.add(0, 0, tr('Enlarge the panel'))
        layout.add(height - 1, 0, tr('[Esc Cancel]'), action=('close', None))
        return layout
    rows = [dict(choice, text=tr('Already imported · ') + choice['text'])
            if choice['imported'] else choice for choice in choices]
    pages = pages_for(rows, usable, room, exchange=True)
    layout.pages = len(pages)
    layout.page = max(0, min(page, len(pages) - 1))
    layout.add(0, 0, tr('Import from project'), 'title')
    layout.add(1, 0, str(project))
    layout.add(2, 0, tr('{0} selected · page {1}/{2}').format(
        len(selected), layout.page + 1, layout.pages))
    y = 4
    for index, (choice, lines) in enumerate(pages[layout.page]):
        layout.visible.append(choice)
        chosen = choice['id'] in selected
        prefix = '  [–] ' if choice['imported'] else f'{chr(97 + index)} [{"x" if chosen else " "}] '
        action = None if choice['imported'] else ('item', choice['id'])
        style = 'dim' if choice['imported'] else 'selected' if chosen else 'normal'
        for n, line in enumerate(lines):
            layout.add(y, 0, (prefix if n == 0 else '      ') + line, style, action, usable)
            y += 1
    if not choices:
        layout.add(4, 0, tr('No exported tasks in this project.'))
    for row, x, label, action in controls:
        layout.add(height - control_rows + row, x, label, 'button' if action else 'dim', action)
    return layout


class MouseInput:
    def __init__(self):self.armed=None;self.signature=None

    def sync(self,layout):
        if self.signature!=layout.signature:self.armed=None;self.signature=layout.signature

    def event(self,x,y,mask,layout):
        self.sync(layout)
        if mask & curses.BUTTON4_PRESSED:self.armed=None;return ('prev',None)
        if mask & getattr(curses,'BUTTON5_PRESSED',0):self.armed=None;return ('next',None)
        target=layout.hit(x,y)
        if mask & curses.BUTTON1_CLICKED:self.armed=None;return target
        if mask & curses.BUTTON1_PRESSED:self.armed=target;return None
        if mask & curses.BUTTON1_RELEASED:
            armed=self.armed;self.armed=None
            if armed is not None and armed==target:return target
        return None


def card_pages(items,width,rows,history=False):
    """Paginate semantic blocks, retaining headings and every word of long cards."""
    groups=[(tr('Completed'),items)] if history else [
        (tr('For the agent'),[i for i in items if not i['text'].startswith('VOCÊ · ')]),
        (tr('For you'),[i for i in items if i['text'].startswith('VOCÊ · ')])]
    pages=[[]];active=None
    def heading(label):
        nonlocal active
        if len(pages[-1])>=rows-1:pages.append([])
        pages[-1].append((None,label,'title'));active=label
    for label,group in groups:
        label=f'{label} · {len(group)}'
        heading(label)
        if not group:
            message=tr('Nothing needs your attention.') if label.startswith(tr('For you')) else tr('No open tasks.')
            if history:message=tr('No completed items.')
            for line in wrap_text(message,width-2):
                if len(pages[-1])==rows:pages.append([]);heading(label)
                pages[-1].append((None,line,'dim'))
            continue
        for item in group:
            text=item['text'].removeprefix('VOCÊ · ')
            title,separator,detail=text.partition(': ')
            if history:title+=' · '+stored_label(item.get('closure_reason','Closed'))
            lines=[(line,'title') for line in wrap_text(title,width-6)]
            if separator:lines.extend((line,'normal') for line in wrap_text(detail,width-6))
            if history and item.get('closure_evidence'):
                lines.extend((line,'normal') for line in wrap_text(item['closure_evidence'],width-6))
            created=creation_date(item)
            if created:lines.extend((line,'dim') for line in wrap_text(created.strftime('%d/%m/%Y %H:%M'),width-6))
            # A fitting card stays whole; long cards continue with the same ID.
            count=len({r[0]['id'] for r in pages[-1] if r[0] is not None})
            if count>=26 or (len(lines)+1<=rows-1 and len(pages[-1])+len(lines)>rows):
                pages.append([]);heading(label)
            for line,style in lines:
                if len(pages[-1])==rows:pages.append([]);heading(label)
                pages[-1].append((item,line,style))
            if len(pages[-1])<rows:pages[-1].append((None,'','normal'))
    return pages


def project_label(project):
    name=Path(project).name
    if name.startswith('left-undone-herdr'):return 'Left Undone'
    return {'git-todo-atlas':'Atlas'}.get(name,name)


def readable_panel_layout(items,width,height,page,project,status,notice,newest_first=True,history=False,recipient='',dispatch_reports=False):
    if width<18 or height<16:
        return build_layout([],width,min(height,11),0,'','','')
    layout=Layout(width,height);usable=width-1
    selected=0 if history else sum(bool(i.get('selected')) for i in items)
    labels=[]
    if selected == 1:labels.extend([('[0 Dispatch Sub-Agent]',('key','0')), (tr('[P Dispatch Plan]'),('key','P'))])
    if selected:labels.extend([(tr('[1 Send {0}]').format(selected),('key','1')),(tr('[2 Mark complete {0}]').format(selected),('key','2'))])
    labels.extend([(tr('[3 Export]'),('key','3')),(tr('[4 Import]'),('key','4')),(tr('[5 Collect]'),('key','5')),(tr('[V Review]'),('key','V'))])
    if recipient.startswith('codex · '):labels.append((tr('[H Handoff + new]'),('key','H')))
    if history:labels=[]
    if dispatch_reports:labels.append((tr('[R Dispatch reports]'), ('key','R')))
    controls,control_rows=buttons(labels,usable)
    navigation,nav_rows=buttons([('[<]',('prev',None)),('[>]',('next',None)),(tr('[Close]'),('close',None))],usable)
    top,top_rows=buttons([(tr('[6 Newest ↓]') if newest_first else tr('[6 Oldest ↑]'),('key','6')),
                         (tr('[7 Open tasks]') if history else tr('[7 History]'),('key','7')),(language_button(),('key','9'))],usable)
    start=3+top_rows
    unknown=sum(creation_date(i) is None for i in items)
    footer=control_rows+nav_rows+2+(1 if unknown else 0)
    room=height-footer-start
    if room<3:
        layout.add(0,0,tr('Enlarge the panel'));layout.add(height-1,0,tr('[Close]'),action=('close',None));return layout
    ordered=sort_items(items,newest_first)
    pages=card_pages(ordered,usable,room,history)
    page=max(0,min(page,len(pages)-1));layout.page=page;layout.pages=len(pages)
    layout.add(0,0,('LEFT UNDONE' if not history else tr('LEFT UNDONE · HISTORY'))+(' · '+recipient if recipient else ''),'title')
    layout.add(1,0,tr('[8 Exchange project: ')+project_label(project)+']','button',('key','8'))
    for y,x,label,action in top:layout.add(2+y,x,label,'button',action)
    layout.add(2+top_rows,0,f'{len(items)} '+(tr('closed') if history else tr('open task') if len(items)==1 else tr('open tasks'))+tr(' · page {0}/{1}').format(page+1, len(pages)),'dim')
    indices={};seen=set();y=start
    for item,line,style in pages[page]:
        if item is None:layout.add(y,0,line,style);y+=1;continue
        first=item['id'] not in seen
        if first:
            indices[item['id']]=len(indices);seen.add(item['id']);layout.visible.append(item)
        index=indices[item['id']]
        prefix=('• ' if history else f'{chr(97+index)} [{"x" if item.get("selected") else " "}] ') if first else ('  ' if history else '      ')
        action=None if history else ('item',item['id'])
        layout.add(y,0,prefix+line,'selected' if item.get('selected') and not history else style,action,usable);y+=1
    y=height-footer
    if unknown:layout.add(y,0,tr('{0} older records without dates.').format(unknown),'dim');y+=1
    status=status.replace(tr('Curation up to date'),tr('Collector active'))
    layout.add(y,0,notice or status,'dim');y+=1
    for row,x,label,action in controls:layout.add(y+row,x,label,'button',action)
    y+=control_rows
    for row,x,label,action in navigation:layout.add(y+row,x,label,'button',action)
    layout.add(height-1,0,tr('Mouse / keys'),'dim')
    return layout
