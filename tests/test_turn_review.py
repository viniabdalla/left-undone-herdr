import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from left_undone.core import Collector
from left_undone.curation import CuratedStore, Curator
from left_undone.projects import ProjectStore
from left_undone.runtime import Binding
from left_undone.turn_review import assess, recent_reports


class TurnReviewTests(unittest.TestCase):
    def test_partial_delivery_is_recorded_once_with_its_exact_quote(self):
        with TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp)/'db', 'session', 'project')
            self.addCleanup(store.close)
            store.import_md('- [ ] Generate video\n- [ ] Publish video')
            generated, publish = store.items()
            quote = 'I rendered the video.'
            def analyze(context, *, output_schema):
                self.assertEqual({i['id'] for i in context['check']}, {generated['id'], publish['id']})
                self.assertNotIn('session', context['check'][0])
                return {str(generated['id']): [dict(requirement='Render video', passage=1)],
                        str(publish['id']): [dict(requirement='Publish video', passage=0)]}
            curator = Curator(store, lambda ctx: assess(analyze, ctx))
            report = quote+' Publishing is blocked pending approval.'
            curator.review(report, 'Please generate and publish it.', 'event')
            curator.review(report, '', 'event')
            self.assertEqual([x['id'] for x in store.items()], [publish['id']])
            self.assertEqual(store.history_items()[0]['closure_evidence'], quote)
            self.assertEqual(len(curator.changes()), 1)

    def test_request_only_evidence_or_missing_decisions_leave_event_retryable(self):
        with TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp)/'db', 'session', 'project')
            self.addCleanup(store.close)
            store.import_md('- [ ] Approve release')
            item = store.items()[0]['id']
            for proposed in ({str(item):[dict(requirement='Approve release', passage=2)]},
                             {str(item): []}, {}):
                curator = Curator(store, lambda ctx: assess(lambda _, **kw: proposed, ctx))
                with self.assertRaises(ValueError):
                    curator.review('Waiting for approval.', 'If I say “I approved it.”', 'event')
                self.assertFalse(store.seen('event'))
                self.assertEqual(len(store.items()), 1)

    def test_final_event_reconciles_separate_deliveries_and_requires_every_part(self):
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / 'db'
            store = ProjectStore(db, 'session', 'project')
            self.addCleanup(store.close)
            store.import_md('- [ ] Show questions and keep blocked tasks open\n'
                            '- [ ] Show the destination tab\n- [ ] Publish the change log\n'
                            '- [ ] Build and publish the package\n- [ ] Verify on Windows')
            questions, destination, changelog, package, windows = store.items()
            final = ('Questions appear in this panel. The destination tab is visible.\n\n'
                     'Blocked tasks stay open. The package was built. Publication is blocked. '
                     'I may have checked Windows.')
            calls = []
            def analyze(payload, *, output_schema):
                calls.append(payload)
                self.assertEqual(payload['passages'][1], 'Questions appear in this panel.')
                self.assertEqual(payload['previous_reply'], 'I plan to verify on Windows.')
                self.assertEqual({i['id'] for i in payload['check']},
                                 {questions['id'], destination['id'], changelog['id'],
                                  package['id'], windows['id']})
                return {
                    str(questions['id']): [
                        dict(requirement='Show questions', passage=1),
                        dict(requirement='Keep blocked tasks open', passage=3)],
                    str(destination['id']): [
                        dict(requirement='Show destination', passage=2)],
                    str(changelog['id']): [dict(requirement='Publish change log', passage=0)],
                    str(package['id']): [
                        dict(requirement='Build package', passage=4),
                        dict(requirement='Publish package', passage=0)],
                    str(windows['id']): [dict(requirement='Verify on Windows', passage=0)]}
            curator = Curator(store, lambda ctx: assess(analyze, ctx))
            reader = CuratedStore(db, store.session)
            self.addCleanup(reader.close)
            path = Path(tmp) / 'history'
            event = json.dumps({'timestamp': '2099-01-01T00:00:00Z', 'type': 'event_msg',
                                'payload': {'type': 'task_complete', 'turn_id': 'delivery',
                                            'last_agent_message': final}}) + '\n'
            previous = json.dumps({'timestamp': '2098-01-01T00:00:00Z', 'type': 'event_msg',
                                   'payload': {'type': 'task_complete', 'turn_id': 'plan',
                                               'last_agent_message': 'I plan to verify on Windows.'}}) + '\n'
            with reader.conn:
                reader.conn.execute('INSERT INTO processed VALUES(?,?)', (store.session, 'turn:plan'))
            path.write_text(previous + event + event)
            Collector(reader, path, 'codex', None, curator.review).poll()
            self.assertEqual(len(calls), 1)
            self.assertEqual({i['id'] for i in store.items()},
                             {changelog['id'], package['id'], windows['id']})
            history = {i['id']: i['closure_evidence'] for i in store.history_items()}
            self.assertEqual(history[questions['id']].splitlines(),
                             ['Questions appear in this panel.', 'Blocked tasks stay open.'])
            self.assertEqual(history[destination['id']], 'The destination tab is visible.')
            self.assertEqual(len(curator.changes()), 2)
            self.assertTrue(store.seen('turn:delivery'))

    def test_failed_list_curation_retries_delivery_and_addition_together(self):
        with TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / 'db', 'session', 'project')
            self.addCleanup(store.close)
            store.import_md('- [ ] Render the file')
            item = store.items()[0]['id']
            attempts = []

            def deliveries(payload, *, output_schema):
                self.assertEqual(payload['passages'][1], 'I rendered the file.')
                return {str(item): [dict(requirement='Render the file', passage=1)]}

            def curate(payload, *, output_schema):
                attempts.append(payload)
                self.assertLessEqual(len(payload['reply']), 12000)
                self.assertEqual(payload['items'][0]['status'], 'done')
                self.assertFalse(payload['items'][0]['writable'])
                if len(attempts) == 1:
                    raise TimeoutError()
                return dict(complete=True, update=[], conflicts=[], duplicate=[],
                            add=[dict(text='Publish the file', scope='project', owner='agent',
                                      evidence='I will publish it tomorrow.')])

            curator = Curator(store, lambda ctx: assess(deliveries, ctx, curate=curate))
            report = 'I rendered the file. ' + 'Details. ' * 1400 + 'I will publish it tomorrow.'
            with self.assertRaises(TimeoutError):
                curator.review(report, '', 'turn:render')
            self.assertFalse(store.seen('turn:render'))
            self.assertEqual([i['id'] for i in store.items()], [item])
            curator.review(report, '', 'turn:render')
            curator.review(report, '', 'turn:render')
            self.assertEqual(len(attempts), 2)
            self.assertEqual([i['text'] for i in store.items()], ['Publish the file'])
            self.assertEqual(store.history_items()[0]['closure_evidence'], 'I rendered the file.')
            self.assertCountEqual([change['action'] for change in curator.changes()], ['done', 'add'])

    def test_backfill_reads_only_consumed_final_replies(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'history'
            event=lambda t: (json.dumps({'type':'event_msg','timestamp':'2026-11-01T00:00:00Z',
                'payload':{'type':'task_complete','turn_id':t,'last_agent_message':t}})+'\n').encode()
            path.write_bytes(event('old')+event('new'))
            binding=Binding('codex','id',tmp,'w1:p1','t','w1',str(path),1,'1')
            rows=recent_reports(binding,len(event('old')))
            self.assertEqual([e['id'] for e,_ in rows],['turn:old'])
