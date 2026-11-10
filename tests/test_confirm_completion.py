import tempfile
import unittest
from pathlib import Path
from left_undone import ui, ui_layout
from left_undone.core import Store


class CompletionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.db=Store(self.root/'db','test');self.addCleanup(self.db.close)
        self.db.add('import','Primeira tarefa');self.db.add('import','Segunda tarefa')
        for item in self.db.items():self.db.toggle(item['id'])

    def offer(self,mouse=False):
        cls=getattr(ui,'DoneOffer',None);self.assertIsNotNone(cls)
        with self.assertRaises(cls) as result:
            if mouse:ui.handle_action(('key','2'),self.db,self.db.items(),lambda _:None,self.root/'out.md')
            else:ui.handle_key('2',self.db,self.db.items(),lambda _:None,self.root/'out.md')
        return result.exception

    def test_keyboard_and_mouse_request_confirmation_without_completing(self):
        for mouse in (False,True):
            offer=self.offer(mouse)
            self.assertEqual(offer.items,tuple((i['id'],i['text']) for i in self.db.items()))
            self.assertEqual(len(self.db.items()),2)
            self.assertTrue(all(i['selected'] for i in self.db.items()))

    def test_confirmation_completes_only_frozen_selection(self):
        offer=self.offer()
        self.db.add('import','Outra selecionada depois');last=self.db.items()[-1]
        self.db.toggle(last['id'])
        self.assertEqual(ui.confirm_done(self.db,offer),2)
        self.assertEqual([i['id'] for i in self.db.items()],[last['id']])
        self.assertTrue(self.db.items()[0]['selected'])

    def test_changed_item_rejects_the_whole_confirmation(self):
        offer=self.offer();first=self.db.items()[0]
        with self.db.conn:self.db.conn.execute('UPDATE items SET text=? WHERE id=?',('Mudou',first['id']))
        with self.assertRaisesRegex(RuntimeError,'mudou'):ui.confirm_done(self.db,offer)
        self.assertEqual(len(self.db.items()),2)
        self.assertTrue(all(i['selected'] for i in self.db.items()))

    def test_deselected_or_completed_item_rejects_remaining_completion(self):
        offer=self.offer();first,second=self.db.items()
        self.db.toggle(first['id'])
        with self.assertRaisesRegex(RuntimeError,'mudou'):ui.confirm_done(self.db,offer)
        self.assertEqual(len(self.db.items()),2)
        self.db.toggle(first['id']);self.db.done([first['id']])
        with self.assertRaisesRegex(RuntimeError,'mudou'):ui.confirm_done(self.db,offer)
        self.assertEqual(self.db.items()[0]['id'],second['id'])
        self.assertTrue(self.db.items()[0]['selected'])

    def test_no_selection_does_not_open_confirmation_or_complete_items(self):
        for item in self.db.items():self.db.toggle(item['id'])
        notice=ui.handle_key('2',self.db,self.db.items(),lambda _:None,self.root/'out.md')
        self.assertIn('selec',notice.lower());self.assertEqual(len(self.db.items()),2)

    def test_confirmation_is_clickable_and_small_panel_only_allows_cancel(self):
        build=getattr(ui_layout,'done_confirmation_layout',None);self.assertIsNotNone(build)
        for width,height in ((18,12),(40,30)):
            layout=build(width,height,3)
            self.assertEqual({t.action for t in layout.targets},{('key','1'),('key','2')})
            question=' '.join(line.text for line in layout.lines)
            self.assertIn('3 itens',question);self.assertIn('concluídos?',question)
        layout=build(40,8,3)
        self.assertEqual([t.action for t in layout.targets],[('key','2')])

    def test_shared_project_completion_uses_the_viewers_selection(self):
        from left_undone.projects import ProjectStore
        a=ProjectStore(self.root/'shared.db','a','project')
        b=ProjectStore(self.root/'shared.db','b','project')
        self.addCleanup(a.close);self.addCleanup(b.close)
        a.import_md('- [ ] Compartilhada\n- [ ] Outra')
        first=b.items()[0];b.toggle(first['id'])
        with self.assertRaises(ui.DoneOffer) as offer:
            ui.handle_key('2',b,b.items(),lambda _:None,self.root/'out.md')
        self.assertEqual(len(a.items()),2)
        self.assertEqual(ui.confirm_done(b,offer.exception),1)
        self.assertEqual([i['text'] for i in a.items()],['Outra'])
        self.assertFalse(any(i['selected'] for i in b.items()))
