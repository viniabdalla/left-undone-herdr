import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from left_undone.core import Store
from left_undone.manual_review import review_session
from left_undone.runtime import AgentBusy
from left_undone.ui_layout import panel_layout, readable_panel_layout


class ManualReviewTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.store = Store(self.root / 'db', 'one')
        self.addCleanup(self.store.close)
        self.binding = SimpleNamespace(kind='codex', key='one', session='one', history=self.root / 'history')
        self.binding.history.write_text(json.dumps({'type': 'event_msg', 'payload': {
            'type': 'task_complete', 'turn_id': 'old',
            'last_agent_message': 'I shipped A. The PDF is ready but has not been sent.'}}) + '\n')
        self.store.add('task', 'A')
        self.store.add('task', 'Generate and send the PDF')
        self.a, self.b = (str(i['id']) for i in self.store.items())
        with self.store.conn:
            self.store.conn.execute("INSERT INTO items(session,text,origin) VALUES('two','A','task')")

    def review(self, decisions, send_error=None):
        def answer(payload, *, output_schema):
            self.assertEqual(set(payload['tasks']), set(decisions))
            return decisions
        with patch('left_undone.manual_review.Analyzer') as model, \
             patch('left_undone.manual_review.verify'), \
             patch('left_undone.manual_review.send', side_effect=send_error) as send, \
             patch('left_undone.manual_review.queue') as queue:
            self.send = send
            self.queue = queue
            model.return_value.request.side_effect = answer
            return review_session(self.root, self.store, self.binding)

    def test_review_closes_proven_delivery_and_sends_only_remaining_work(self):
        result = self.review({self.a: dict(evidence=1, reason='A was shipped.'),
                              self.b: dict(evidence=0, reason='The PDF is ready. Send it.')})
        self.assertEqual([d['state'] for d in result], ['done', 'open'])
        self.assertEqual([i['text'] for i in self.store.items()], ['Generate and send the PDF'])
        self.assertEqual(self.store.conn.execute("SELECT status FROM items WHERE session='two'").fetchone()[0], 'open')
        self.send.assert_called_once()
        binding, text = self.send.call_args.args
        self.assertIs(binding, self.binding)
        self.assertIn('The PDF is ready. Send it.', text)
        self.assertNotIn('A was shipped', text)
        self.assertEqual(result[1]['delivery'], 'sent')

    def test_selected_done_never_sends(self):
        self.store.toggle(int(self.a))
        self.review({self.a: dict(evidence=1, reason='Shipped.')})
        self.send.assert_not_called()
        self.queue.assert_not_called()

    def test_busy_codex_queues_one_message_for_the_main_session(self):
        self.store.toggle(int(self.b))
        result = self.review({self.b: dict(evidence=0, reason='Verify delivery.')}, AgentBusy())
        self.queue.assert_called_once_with(*self.send.call_args.args)
        self.assertEqual(result[0]['delivery'], 'queued')
        self.assertEqual(len(self.store.items()), 2)

    def test_busy_claude_waits_and_revalidates_before_sending(self):
        self.binding.kind = 'claude'
        self.store.toggle(int(self.b))
        with patch('left_undone.manual_review.Analyzer') as model, \
             patch('left_undone.manual_review.verify'), \
             patch('left_undone.manual_review.send', side_effect=[AgentBusy(), None]) as send, \
             patch('left_undone.manual_review.time.sleep') as sleep:
            model.return_value.request.return_value = {
                self.b: dict(evidence=0, reason='Verify delivery.')}
            result = review_session(self.root, self.store, self.binding)
            self.assertEqual(result[0]['delivery'], 'sent')
            self.assertEqual(send.call_count, 2)
            sleep.assert_called_once()
            model.return_value.request.assert_called_once()

    def test_failed_send_is_reported_and_proven_closure_is_preserved(self):
        result = self.review({self.a: dict(evidence=1, reason='Shipped.'),
                              self.b: dict(evidence=0, reason='Send the PDF.')}, RuntimeError('missing receipt'))
        self.assertEqual(result[1]['delivery'], 'unconfirmed')
        self.assertIn('missing receipt', result[1]['error'])
        self.queue.assert_not_called()
        self.assertEqual(len(self.store.items()), 1)

    def test_invalid_evidence_causes_no_action(self):
        with self.assertRaises(ValueError):
            self.review({self.a: dict(evidence=9999, reason='Shipped.'),
                         self.b: dict(evidence=0, reason='Send the PDF.')})
        self.send.assert_not_called()
        self.assertEqual(len(self.store.items()), 2)

    def test_user_request_cannot_prove_completion(self):
        with self.binding.history.open('a') as f:
            f.write(json.dumps({'type': 'event_msg', 'payload': {
                'type': 'user_message', 'message': 'Please send the PDF.'}}) + '\n')
        self.store.toggle(int(self.b))
        with self.assertRaises(ValueError):
            self.review({self.b: dict(evidence=3, reason='Sent.')})
        self.send.assert_not_called()
        self.assertEqual(len(self.store.items()), 2)

    def test_selection_change_prevents_send(self):
        with patch('left_undone.manual_review.Analyzer') as model, \
             patch('left_undone.manual_review.verify'), patch('left_undone.manual_review.send') as send:
            def change(*args, **kwargs):
                self.store.toggle(int(self.a))
                return {i: dict(evidence=0, reason='Check delivery.') for i in (self.a, self.b)}
            model.return_value.request.side_effect = change
            with self.assertRaisesRegex(ValueError, 'Tasks changed'):
                review_session(self.root, self.store, self.binding)
            send.assert_not_called()

    def test_collect_and_review_have_distinct_mouse_targets_without_selection(self):
        for layout in (panel_layout([],80,35,0,'','',''),readable_panel_layout([],80,35,0,'project','','')):
            for key in ('5','V'):
                t = next(t for t in layout.targets if t.action==('key',key))
                self.assertEqual(layout.hit(t.x,t.y),('key',key))
