import curses
import unittest
from left_undone.ui_layout import cell_width, wrap_text, panel_layout, picker_layout, MouseInput


def item(i,text,selected=0):
    return {'id':i,'text':text,'selected':selected,'origin':'import'}

class LayoutTests(unittest.TestCase):
    def test_collect_button_is_clickable_without_selection_and_in_narrow_panel(self):
        for width,height in ((18,13),(40,30),(80,24)):
            for selected in (0,1):
                layout=panel_layout([item(1,'Task',selected)],width,height,0,'','','')
                target=next((t for t in layout.targets if t.action==('key','5')),None)
                self.assertIsNotNone(target)
                self.assertEqual(layout.hit(target.x,target.y),('key','5'))
                self.assertIn(1,[i['id'] for i in layout.visible])

    def test_narrow_panel_wraps_complete_task_and_hit_target_covers_each_line(self):
        text='Uma tarefa longa com palavras suficientes para quebrar em várias linhas sem cortar o final.'
        layout=panel_layout([item(1,text)],27,40,0,'codex','Coleta ativa','')
        rows=[line for line in layout.lines if line.action==('item',1)]
        self.assertGreater(len(rows),2)
        rendered=' '.join(line.text[6:] for line in rows)
        self.assertIn('cortar o final.',rendered)
        for line in layout.lines:self.assertLessEqual(line.x+cell_width(line.text),26)
        for line in rows:self.assertEqual(layout.hit(8,line.y),('item',1))
        self.assertIsNone(layout.hit(27,rows[0].y))

    def test_very_long_item_continues_across_pages_without_losing_words(self):
        words=['word'+str(i) for i in range(100)]
        items=[item(1,' '.join(words)),item(2,'last item')]
        first=panel_layout(items,24,18,0,'','','')
        self.assertGreater(first.pages,1)
        texts=[]
        for p in range(first.pages):
            layout=panel_layout(items,24,18,p,'','','')
            texts.extend(line.text for line in layout.lines if line.action==('item',1))
            self.assertLessEqual(len(layout.visible),26)
            self.assertEqual(layout.page,p)
        joined=' '.join(texts)
        for word in words:self.assertIn(word,joined)
        last=panel_layout(items,24,18,999,'','','')
        self.assertEqual(last.page,first.pages-1)
        self.assertTrue(any(i['id']==2 for i in last.visible))

    def test_buttons_are_visible_only_when_available_and_fit_narrow_width(self):
        for width in (18,24,67):
            plain=panel_layout([item(1,'text')],width,40,0,'','','')
            self.assertNotIn(('key','1'),[t.action for t in plain.targets])
            selected=panel_layout([item(1,'text',1)],width,40,0,'','','')
            actions=[t.action for t in selected.targets]
            for key in ('1','2','3','4'):self.assertIn(('key',key),actions)
            for target in selected.targets:
                self.assertGreaterEqual(target.x,0)
                self.assertLessEqual(target.x+target.width,width-1)
                self.assertLess(target.y,40)

    def test_selection_keeps_actions_and_item_visible_at_small_sizes(self):
        for width,height in ((18,13),(24,14)):
            layout=panel_layout([item(1,'Task selected',1)],width,height,0,'','','')
            self.assertEqual([i['id'] for i in layout.visible],[1])
            self.assertIn(('key','1'),[t.action for t in layout.targets])
            self.assertIn(('key','2'),[t.action for t in layout.targets])

    def test_picker_reflows_around_selected_session_on_resize(self):
        rows=[{'id':i,'text':f'claude pane {i} account and session details'} for i in range(10)]
        wide=picker_layout(rows,80,25,0,8,follow_cursor=True)
        narrow=picker_layout(rows,25,25,wide.page,8,follow_cursor=True)
        self.assertIn(8,[i['id'] for i in narrow.visible])

    def test_rendered_joiners_use_same_width_as_layout(self):
        from left_undone.ui import render
        layout=panel_layout([item(1,'👩‍💻'*5)],18,30,0,'','','')
        drawn=[]
        class Window:
            def erase(self):pass
            def refresh(self):pass
            def getmaxyx(self):return 30,18
            def addstr(self,y,x,text,attr):drawn.append((x,text))
        render(Window(),layout)
        self.assertTrue(all(x+cell_width(text)<=17 for x,text in drawn))
        self.assertIn('👩‍💻',''.join(text for _,text in drawn))

    def test_unicode_wrapping_obeys_terminal_cells(self):
        text='ação 漢字 🌞 cafe\u0301 '+('z'*40)
        lines=wrap_text(text,10)
        self.assertTrue(all(cell_width(line)<=10 for line in lines))
        self.assertEqual(''.join(lines).replace(' ',''),text.replace(' ',''))

    def test_tiny_panel_has_no_invisible_item_or_send_targets(self):
        for width,height in ((6,8),(22,6)):
            layout=panel_layout([item(1,'secret task',1)],width,height,0,'','','')
            self.assertEqual(layout.visible,[])
            self.assertTrue(all(t.action==('close',None) for t in layout.targets))

    def test_picker_wraps_rows_and_exposes_explicit_open_button(self):
        rows=[{'id':i,'text':f'claude pane {i} account and session details'} for i in range(12)]
        layout=picker_layout(rows,25,20,0,0)
        self.assertEqual(layout.hit(8,4),('choose',0))
        self.assertIn(('open',None),[t.action for t in layout.targets])
        self.assertGreater(layout.pages,1)

class MouseTests(unittest.TestCase):
    def setUp(self):
        self.layout=panel_layout([item(1,'first'),item(2,'second')],40,25,0,'','','')
        self.mouse=MouseInput()
        self.target=next(t for t in self.layout.targets if t.action==('item',1))

    def event(self,mask,x=None,y=None,layout=None):
        return self.mouse.event(self.target.x if x is None else x,self.target.y if y is None else y,mask,layout or self.layout)

    def test_press_release_toggles_once(self):
        self.assertIsNone(self.event(curses.BUTTON1_PRESSED))
        self.assertEqual(self.event(curses.BUTTON1_RELEASED),('item',1))
        self.assertIsNone(self.event(curses.BUTTON1_RELEASED))

    def test_drag_blank_right_click_and_resize_do_not_activate(self):
        self.event(curses.BUTTON1_PRESSED)
        self.assertIsNone(self.event(curses.BUTTON1_RELEASED,x=0,y=0))
        self.assertIsNone(self.event(curses.BUTTON3_PRESSED))
        self.event(curses.BUTTON1_PRESSED)
        resized=panel_layout([item(1,'first'),item(2,'second')],20,25,0,'','','')
        self.assertIsNone(self.event(curses.BUTTON1_RELEASED,layout=resized))

    def test_curses_aggregated_click_activates_once(self):
        self.assertEqual(self.event(curses.BUTTON1_CLICKED),('item',1))
        self.assertIsNone(self.event(curses.BUTTON1_RELEASED))

    def test_wheel_routes_to_page_actions(self):
        self.assertEqual(self.event(curses.BUTTON4_PRESSED),('prev',None))
        self.assertEqual(self.event(curses.BUTTON5_PRESSED),('next',None))

class ActionTests(unittest.TestCase):
    def test_mouse_actions_share_selection_send_done_and_exports_with_keyboard(self):
        import tempfile
        from pathlib import Path
        from left_undone.core import Store
        from left_undone.ui import handle_action
        with tempfile.TemporaryDirectory() as folder:
            db=Store(Path(folder)/'db','test');self.addCleanup(db.close)
            db.add('import','First task');db.add('import','Second task')
            first,second=db.items();sent=[];export=Path(folder)/'out.md'
            handle_action(('item',first['id']),db,db.items(),sent.append,export)
            self.assertTrue(db.items()[0]['selected']);self.assertEqual(sent,[])
            handle_action(('key','1'),db,db.items(),sent.append,export)
            self.assertEqual(sent,['You left this undone: First task']);self.assertEqual(len(db.items()),2)
            handle_action(('item',first['id']),db,db.items(),sent.append,export)
            handle_action(('key','2'),db,db.items(),sent.append,export)
            self.assertEqual([i['id'] for i in db.items()],[second['id']])
            handle_action(('key','3'),db,db.items(),sent.append,export)
            export.write_text(export.read_text()+'- [ ] Third task\n')
            handle_action(('key','4'),db,db.items(),sent.append,export)
            self.assertEqual(len(db.items()),2)
