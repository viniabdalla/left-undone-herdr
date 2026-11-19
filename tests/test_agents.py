import json
import tempfile
import unittest
from pathlib import Path

from left_undone.agents import agent_info, read_usage


class AgentMonitorTests(unittest.TestCase):
    def test_terminal_identity_and_agent_state(self):
        pane = {'terminal_id':'first','agent':'codex','agent_status':'blocked'}
        self.assertEqual(agent_info(pane,'first'),'Blocked')
        self.assertEqual(agent_info(pane,'replacement'),'Closed')
        self.assertEqual(agent_info({**pane,'agent':None},'first'),'Terminal')

    def test_token_totals_are_cumulative_and_partial_events_are_retried(self):
        def event(total):
            return json.dumps({'payload':{'type':'token_count','info':{'model_context_window':1000,
                'last_token_usage':{'total_tokens':120},'total_token_usage':{'total_tokens':total}}}})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'session'; cache={}
            path.write_text(event(150)+'\n'+event(300))
            self.assertEqual(read_usage(path,cache),(120,1000,150))
            with path.open('a') as stream:stream.write('\n')
            self.assertEqual(read_usage(path,cache),(120,1000,300))
            self.assertEqual(read_usage(path,cache),(120,1000,300))

    def test_reflow_keeps_task_text_and_native_tab_titles(self):
        from left_undone.agents import monitor_lines
        from left_undone.ui_layout import cell_width
        main=dict(main=True,tab='wP:t1',pane='wP:p1',label='1')
        job=dict(main=False,tab='wP:t5',pane='wP:pG',label='Dispatch · 211',state='done',
                 task='Left Undone / Configuração: ' + '長'*49 + ' final')
        blocked=dict(job,tab='wP:t4',pane='wP:pF',label='Dispatch · 202')
        rows=[(main,'Idle',None),(job,'Idle',1),(blocked,'Blocked',2)]
        for width in (12,19,38,63,64,88,120):
            with self.subTest(width=width):
                lines=monitor_lines(rows,width)
                cells=[(x,text) for line in lines for x,text,_ in line]
                self.assertTrue(all(x+cell_width(text)<=width for x,text in cells))
                content=''.join(text for _,text in cells)
                self.assertEqual(content.count('長'),98)
                self.assertEqual(content.count('final'),2)
                self.assertLess(content.index('202'),content.index('211'))
                self.assertIn('wP:pF',content)

    def test_review_button_identifies_its_dispatch_and_requires_idle_main(self):
        from left_undone.agents import monitor_lines
        main = dict(main=True, tab='t', pane='p', label='Main')
        job = dict(main=False, tab='t2', pane='p2', label='Worker', task='Read file', state='done',
                   dispatch_id=42, attempt=0, verdict=None, reason=None)
        for state in ('Idle', 'Working'):
            targets = {}
            lines = monitor_lines([(main,state,None),(job,'Closed',None)], 38, targets)
            self.assertEqual(bool(targets), state=='Idle')
            if targets:
                y, = targets
                self.assertEqual(targets[y], (42, 0))
                self.assertIn('Review', lines[y][0][1])
        job.update(verdict='done', reason='The file was read.')
        lines = monitor_lines([(main,'Working',None),(job,'Closed',None)], 38, {})
        self.assertIn('Done', ' '.join(s for line in lines for _,s,_ in line))
        self.assertIn('The file was read.', ' '.join(s for line in lines for _,s,_ in line))

    def test_budget_meter_uses_cumulative_consumption(self):
        from left_undone.agents import usage_meter
        self.assertIn('▰▰▰▰▰▰▱▱▱▱ 60%', usage_meter(200000,500000))
        self.assertIn('100%',usage_meter(0,500000))
        self.assertIn('620,000',usage_meter(620000,500000))
        self.assertIn('▱▱▱▱▱▱▱▱▱▱ 0%',usage_meter(620000,500000))
        self.assertIn('50%',usage_meter(200000,400000))
        self.assertNotIn('%',usage_meter(None,500000))

    def test_claude_usage_counts_each_response_once_including_cache(self):
        from left_undone.agents import claude_total
        def row(mid, out, sid='session'):
            return json.dumps(dict(type='assistant',sessionId=sid,message=dict(id=mid,
                usage=dict(input_tokens=10,output_tokens=out,cache_read_input_tokens=5))))+'\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'session'
            path.write_text(row('a',1)+row('a',2)+row('unrelated',90,'other'))
            cache = {}
            self.assertEqual(claude_total(path,cache,'session'),17)
            with path.open('a') as stream:
                stream.write(row('b',3))
            self.assertEqual(claude_total(path,cache,'session'),35)

    def test_reference_editor_saves_and_cancel_preserves_the_value(self):
        from unittest.mock import MagicMock
        from left_undone.agents import edit_budget, token_budget
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            win = MagicMock()
            win.getmaxyx.return_value = (20,60)
            self.assertEqual(token_budget(root),500000)
            win.get_wch.side_effect = list('400000\n')
            self.assertEqual(edit_budget(win,root,500000),400000)
            win.get_wch.side_effect = ['3','\x1b']
            self.assertEqual(edit_budget(win,root,400000),400000)
            self.assertEqual(token_budget(root),400000)
