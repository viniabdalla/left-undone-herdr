import curses
import os
import time
import unittest
from left_undone.ui_layout import panel_layout,MouseInput


def task(n,stamp,origin='import',selected=0):
    return {'id':n,'created_at':stamp,'origin':origin,'text':'Task '+str(n),'selected':selected}


class OrderingTests(unittest.TestCase):
    def test_creation_order_crosses_origins_with_unknown_last_and_stable_ties(self):
        items=[task(1,None),task(2,100,'task'),task(3,300,'promise',1),task(4,100)]
        latest=panel_layout(items,80,40,0,'','','')
        self.assertEqual([i['id'] for i in latest.visible],[3,4,2,1])
        oldest=panel_layout(items,80,40,0,'','','',newest_first=False)
        self.assertEqual([i['id'] for i in oldest.visible],[2,4,3,1])
        self.assertEqual(next(i['selected'] for i in oldest.visible if i['id']==3),1)
        self.assertEqual([i['id'] for i in items],[1,2,3,4])

    def test_top_order_button_mouse_target_and_narrow_width(self):
        for width in (18,24,80):
            for newest in (False,True):
                layout=panel_layout([task(1,None)],width,30,0,'','','',newest_first=newest)
                target=next((t for t in layout.targets if t.action==('key','6')),None)
                self.assertIsNotNone(target)
                self.assertLess(target.y,4)
                self.assertEqual(MouseInput().event(target.x,target.y,curses.BUTTON1_CLICKED,layout),('key','6'))
                self.assertTrue(all(line.x+len(line.text)<=width-1 for line in layout.lines))

    def test_creation_date_is_local_and_invalid_dates_are_explicit(self):
        old=os.environ.get('TZ');os.environ['TZ']='America/Fortaleza';time.tzset()
        try:
            items=[task(1,1794312000),task(2,None),task(3,float('inf'))]
            layout=panel_layout(items,80,40,0,'','','')
            text='\n'.join(line.text for line in layout.lines)
            self.assertIn('10/11/2026 09:00',text)
            self.assertEqual(text.count('data desconhecida'),2)
        finally:
            if old is None:os.environ.pop('TZ',None)
            else:os.environ['TZ']=old
            time.tzset()

    def test_unknown_and_equal_dates_are_stable_across_pages(self):
        items=[task(i,None if i%2 else 100) for i in range(1,40)]
        first=panel_layout(items,24,18,0,'','','')
        ids=[]
        for page in range(first.pages):
            for item in panel_layout(items,24,18,page,'','','').visible:
                if not ids or item['id']!=ids[-1]:ids.append(item['id'])
        self.assertEqual(ids,list(range(38,0,-2))+list(range(39,0,-2)))
