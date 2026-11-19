import curses
import unittest
from left_undone.ui_layout import cell_width, wrap_text, panel_layout, picker_layout, MouseInput


def item(i,text,selected=0):
    return {'id':i,'text':text,'selected':selected,'origin':'import'}

class LayoutTests(unittest.TestCase):
    def test_picker_shows_panel_title_above_clickable_details(self):
        rows=[{'id':0,'heading':'w5:p1 · Continue developing Git support',
               'text':'codex · 01a1c583-45f · account .codex · 10 open tasks'}]
        for width in (25,80):
            with self.subTest(width=width):
                layout=picker_layout(rows,width,25,0,0)
                lines=[line for line in layout.lines if line.action==('choose',0)]
                self.assertTrue(lines[0].text.startswith('> w5:p1 · Continue'))
                self.assertTrue(lines[1].text.startswith('  codex · 01a1c583-45f'))
                self.assertIn('10 open tasks',' '.join(line.text.strip() for line in lines))
                self.assertEqual(layout.hit(3,lines[1].y),('choose',0))

    def test_language_switch_has_clickable_target_in_picker_and_panel(self):
        for width in (24,80):
            for layout in (picker_layout([],width,30,0,0),panel_layout([],width,30,0,'','','')):
                with self.subTest(width=width,screen=layout.lines[0].text):
                    switch=next(line for line in layout.lines if line.text=='[9 Português]')
                    self.assertEqual(layout.hit(switch.x,switch.y),('key','9'))
                    self.assertEqual(layout.hit(switch.x+cell_width(switch.text)-1,switch.y),('key','9'))

    def test_collect_button_is_clickable_without_selection_and_in_narrow_panel(self):
        for width,height in ((18,13),(40,30),(80,24)):
            for selected in (0,1):
                layout=panel_layout([item(1,'Task',selected)],width,height,0,'','','')
                target=next((t for t in layout.targets if t.action==('key','5')),None)
                self.assertIsNotNone(target)
                self.assertEqual(layout.hit(target.x,target.y),('key','5'))
                self.assertIn(1,[i['id'] for i in layout.visible])

    def test_narrow_panel_wraps_complete_task_and_hit_target_covers_each_line(self):
        text='A long task with enough words to wrap across several lines without losing the ending.'
        layout=panel_layout([item(1,text)],27,40,0,'codex','Collection active','')
        rows=[line for line in layout.lines if line.action==('item',1)]
        self.assertGreater(len(rows),2)
        rendered=' '.join(line.text[6:] for line in rows)
        self.assertIn('losing the ending.',rendered)
        for line in layout.lines:self.assertLessEqual(line.x+cell_width(line.text),26)
        for line in rows:self.assertEqual(layout.hit(8,line.y),('item',1))
        self.assertIsNone(layout.hit(27,rows[0].y))

    def test_very_long_item_continues_across_pages_without_losing_words(self):
        words=['word'+str(i) for i in range(100)]
        items=[{**item(1,' '.join(words)),'created_at':200},{**item(2,'last item'),'created_at':100}]
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
    def test_mouse_actions_share_selection_send_and_done_with_keyboard(self):
        import tempfile
        from pathlib import Path
        from left_undone.core import Store
        from left_undone.ui import handle_action,DoneOffer,confirm_done
        with tempfile.TemporaryDirectory() as folder:
            db=Store(Path(folder)/'db','test');self.addCleanup(db.close)
            db.add('import','First task');db.add('import','Second task')
            first,second=db.items();sent=[]
            handle_action(('item',first['id']),db,db.items(),sent.append)
            self.assertTrue(db.items()[0]['selected']);self.assertEqual(sent,[])
            handle_action(('key','1'),db,db.items(),sent.append)
            self.assertEqual(sent,['You left this undone: First task']);self.assertEqual(len(db.items()),2)
            handle_action(('item',first['id']),db,db.items(),sent.append)
            with self.assertRaises(DoneOffer) as offer:handle_action(('key','2'),db,db.items(),sent.append)
            confirm_done(db,offer.exception)
            self.assertEqual([i['id'] for i in db.items()],[second['id']])


class ConversationLayoutTests(unittest.TestCase):
    def test_two_line_blocks_with_heading_and_clickable_rows(self):
        from left_undone.ui_layout import conversation_layout
        entries=[{'id':i,'title':f'Task {i}','detail':'Codex · account .codex · 2 open tasks','pane':f'wP:p{i}'} for i in range(3)]
        layout=conversation_layout(entries,60,24,0,1,'Workspace: repo · ~/Projects/repo')
        text={l.y:l.text for l in layout.lines if l.x==0}
        self.assertEqual(text[1],'Workspace: repo · ~/Projects/repo')
        self.assertEqual(text[4],'  Task 0')
        self.assertTrue(text[5].startswith('    Codex · account .codex'))
        self.assertTrue(text[6].startswith('─'))
        self.assertEqual(text[7],'▸ Task 1')
        self.assertEqual(layout.hit(10,8),('choose',1))
        self.assertTrue(any(l.text=='wP:p1' for l in layout.lines))

    def test_empty_workspace_says_so(self):
        from left_undone.ui_layout import conversation_layout
        layout=conversation_layout([],60,20,0,0,'Workspace: home')
        self.assertTrue(any('No conversations in this workspace.' in l.text for l in layout.lines))
        self.assertFalse(any(l.action==('open',None) for l in layout.lines))


class PanelTopControlsTests(unittest.TestCase):
    def test_paging_beside_counter_and_close_on_title_row(self):
        from left_undone.ui_layout import readable_panel_layout
        items=[{'id':i,'text':f'Task {i}','origin':'task','created_at':1.0+i} for i in range(40)]
        layout=readable_panel_layout(items,60,30,0,'/tmp/repo','','')
        rows={t.action:t.y for t in layout.targets}
        self.assertEqual(rows[('close',None)],0)
        self.assertEqual(rows[('prev',None)],rows[('next',None)])
        self.assertLess(rows[('next',None)],5)

    def test_dispatch_buttons_for_several_and_choice_screens(self):
        from left_undone.ui_layout import readable_panel_layout,dispatch_choice_layout,close_choice_layout
        items=[{'id':i,'text':f'Task {i}','origin':'task','created_at':1.0,'selected':1} for i in range(2)]
        labels=[l.text for l in readable_panel_layout(items,80,30,0,'/tmp/repo','','').lines]
        self.assertIn('[0 Dispatch 2]',labels);self.assertIn('[P Dispatch plan 2]',labels)
        choice=[l.text for l in dispatch_choice_layout(80,20,2,False).lines]
        self.assertIn('[1 Separate · 2 tabs]',choice);self.assertIn('[2 Together · 1 tab]',choice)
        close=[l.text for l in close_choice_layout(80,20,3).lines]
        self.assertIn('[1 Export and close]',close);self.assertIn('[2 Close without exporting]',close)
        self.assertNotIn('[1 Export and close]',[l.text for l in close_choice_layout(80,20,0).lines])
