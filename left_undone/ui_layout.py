"""Cell-aware terminal layouts and mouse hit testing, independent of curses I/O."""
import curses
import unicodedata
from dataclasses import dataclass, field


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


def pages_for(items,width,rows,picker=False):
    pages=[[]];used=0
    for item in items:
        origin={'task':'TAREFA','promise':'PROMESSA','import':'IMPORTADO'}.get(item.get('origin'),'')
        text=item['text'] if picker else f'{origin} · {item["text"]}'
        lines=wrap_text(text,width-(2 if picker else 6))
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


def build_layout(items,width,height,page,subtitle,status,notice,picker=False,cursor=0):
    layout=Layout(width,height);usable=max(1,width-1)
    title='Escolha conversa' if picker else 'LEFT UNDONE'
    if width<18 or height<12:
        for y,line in enumerate(wrap_text('Aumente o painel para ver a lista.',usable)):
            if y<height-1:layout.add(y,0,line)
        layout.add(height-1,0,'[Fechar]',action=('close',None))
        return layout
    selected=sum(bool(i.get('selected')) for i in items)
    labels=[]
    if picker:
        if items:labels.append(('[Abrir]',('open',None)))
    else:
        if selected:labels.extend([(f'[1 Enviar {selected}]',('key','1')),(f'[2 Concluir {selected}]',('key','2'))])
        labels.extend([('[3 Exportar]',('key','3')),('[4 Importar]',('key','4')),
                       ('[5 Coletar agora]',('key','5'))])
    packed,button_rows=buttons(labels,usable)
    nav,nav_rows=buttons([('[<]',('prev',None)),('[>]',('next',None)),('[Fechar]',('close',None))],usable)
    # Compact status/notice before sacrificing the list or its action buttons.
    messages=max(0,min(4,height-4-button_rows-nav_rows-1-1))
    status_rows=min(2,(messages+1)//2);notice_rows=messages-status_rows
    footer=messages+button_rows+nav_rows+1
    room=height-4-footer
    if room<1:
        layout.add(0,0,title,'title')
        layout.add(2,0,'Aumente o painel')
        layout.add(height-1,0,'[Fechar]',action=('close',None))
        return layout
    pages=pages_for(items,usable,room,picker)
    page=max(0,min(page,len(pages)-1));layout.page=page;layout.pages=len(pages)
    layout.add(0,0,title,'title');layout.add(1,0,subtitle)
    layout.add(2,0,f'{len(items)} itens · {page+1}/{len(pages)}')
    y=4
    for index,(item,lines) in enumerate(pages[page]):
        layout.visible.append(item)
        action=('choose' if picker else 'item',item['id'])
        chosen=item['id']==cursor if picker else bool(item.get('selected'))
        prefix=('> ' if chosen else '  ') if picker else f'{chr(97+index)} [{"x" if chosen else " "}] '
        for n,line in enumerate(lines):
            layout.add(y,0,(prefix if n==0 else ' '*len(prefix))+line,'selected' if chosen else 'normal',action,usable)
            y+=1
    if not items:layout.add(4,0,'Nenhuma pendência.' if not picker else 'Nenhuma conversa.')
    y=height-footer
    for line in bounded_lines(status,usable,status_rows)+bounded_lines(notice,usable,notice_rows):layout.add(y,0,line);y+=1
    for row,x,label,action in packed:layout.add(y+row,x,label,'button',action)
    y+=button_rows
    for row,x,label,action in nav:layout.add(y+row,x,label,'button',action)
    layout.add(height-1,0,'Mouse / teclas')
    return layout


def panel_layout(items,width,height,page,subtitle,status,notice):
    return build_layout(items,width,height,page,subtitle,status,notice)


def picker_layout(items,width,height,page,cursor,notice='',follow_cursor=False):
    layout=build_layout(items,width,height,page,'Selecione e abra','',notice,True,cursor)
    if follow_cursor and items and not any(i['id']==cursor for i in layout.visible):
        for candidate in range(layout.pages):
            other=build_layout(items,width,height,candidate,'Selecione e abra','',notice,True,cursor)
            if any(i['id']==cursor for i in other.visible):return other
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
