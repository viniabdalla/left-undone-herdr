import unittest
from left_undone import ui_layout

class ReadablePanelTests(unittest.TestCase):
    def layout(self,items,width=70,height=40,page=0,history=False):
        build=getattr(ui_layout,'readable_panel_layout',None)
        self.assertIsNotNone(build,'Project panel needs a readable grouped layout')
        return build(items,width,height,page,'left-undone-herdr','Coletor ativo','',history=history)

    def test_groups_titles_one_unknown_notice_and_no_origin_noise(self):
        items=[{'id':1,'text':'Revisar pendências: encontrar conclusões ignoradas.','origin':'task'},
               {'id':2,'text':'VOCÊ · Confirmar escolha: escolher tarefas no relatório.','origin':'import'}]
        layout=self.layout(items)
        text='\n'.join(l.text for l in layout.lines)
        self.assertIn('PARA A IA',text);self.assertIn('PARA VOCÊ',text)
        self.assertNotIn('TAREFA ·',text);self.assertNotIn('IMPORTADO ·',text)
        self.assertEqual(text.count('sem data'),1)
        title=next(l for l in layout.lines if 'Revisar pendências' in l.text)
        self.assertEqual(title.style,'title')
        self.assertTrue(any(l.y>title.y and 'encontrar conclusões' in l.text for l in layout.lines))
        for key in ('6','7','8'):self.assertIn(('key',key),[t.action for t in layout.targets])

    def test_empty_human_group_and_readonly_history(self):
        items=[{'id':1,'text':'Ação: fazer a ação','origin':'task','selected':1,'closure_reason':'Duplicada'}]
        self.assertIn('Nada depende de você agora','\n'.join(l.text for l in self.layout(items).lines))
        layout=self.layout(items,history=True)
        self.assertIn('Duplicada','\n'.join(l.text for l in layout.lines))
        self.assertFalse(any(t.action[0]=='item' or t.action in [('key','1'),('key','2')] for t in layout.targets))

    def test_long_cards_pagination_narrow_panels_keep_all_text(self):
        words=['word'+str(i) for i in range(80)]
        items=[{'id':1,'text':'Long card: '+' '.join(words),'origin':'task'}]
        for width in (18,28,70):
            first=self.layout(items,width,24)
            text=' '.join(l.text for p in range(first.pages) for l in self.layout(items,width,24,p).lines if l.action==('item',1))
            for word in words:self.assertIn(word,text)
            for p in range(first.pages):
                layout=self.layout(items,width,24,p)
                self.assertTrue(all(l.x+ui_layout.cell_width(l.text)<width for l in layout.lines))
