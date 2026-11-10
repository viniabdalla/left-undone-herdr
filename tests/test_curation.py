import tempfile
import unittest
import json
from pathlib import Path
from left_undone.core import Store
from left_undone.projects import ProjectStore


def decisions(**kwargs):
    return {**{'complete': True, 'add': [], 'update': [], 'done': [], 'duplicate': [], 'conflicts': []}, **kwargs}


class CurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.db'
        self.a = ProjectStore(self.path, 'a', 'project')
        self.b = ProjectStore(self.path, 'b', 'project')
        self.addCleanup(self.a.close);self.addCleanup(self.b.close)

    def curator(self, analyze):
        from left_undone.curation import Curator
        return Curator(self.a, analyze)

    def test_global_update_done_and_new_task_are_applied_once(self):
        self.a.import_md('- [ ] Add mouse\n- [ ] Build tests')
        mouse, tests = self.a.items()
        calls = []
        def analyze(context):
            calls.append(context)
            return decisions(update=[{'id': mouse['id'], 'text': 'Mouse wheel support', 'evidence': 'Mouse wheel remains'}],
                done=[{'id': tests['id'], 'evidence': 'Tests passed'}],
                add=[{'scope': 'project', 'text': 'Keyboard support', 'evidence': 'Keyboard support next'}])
        curator = self.curator(analyze)
        reply = 'Tests passed. Mouse wheel remains. Keyboard support next.'
        curator.review(reply, '', 'event1');curator.review(reply, '', 'event1')
        self.assertEqual(len(calls), 1)
        self.assertEqual({i['text'] for i in self.b.items()}, {'Mouse wheel support', 'Keyboard support'})
        self.assertEqual(len(curator.changes()), 3)

    def test_conflict_and_foreign_tasks_are_preserved_while_distinct_work_is_added(self):
        native = Store(self.path, 'b');self.addCleanup(native.close)
        native.add('task', 'Other session work')
        self.a.import_md('- [ ] Contested')
        other = next(i for i in self.a.items() if i['origin'] == 'task')
        contested = next(i for i in self.a.items() if i['origin'] == 'import')
        curator = self.curator(lambda _: decisions(done=[{'id': other['id'], 'evidence': 'Finished'},
                    {'id': contested['id'], 'evidence': 'Finished'}], conflicts=[contested['id']],
                    add=[{'scope': 'project', 'text': 'Different task', 'evidence': 'Different task'}]))
        curator.review('Finished. Different task remains.', '', 'e1')
        self.assertEqual({i['text'] for i in self.b.items()}, {'Other session work', 'Contested', 'Different task'})

    def test_semantic_duplicate_is_archived_but_distinct_item_remains(self):
        self.a.import_md('- [ ] Mouse support\n- [ ] Enable mouse interaction\n- [ ] Keyboard navigation')
        keep, duplicate, different = self.a.items()
        curator = self.curator(lambda _: decisions(duplicate=[{'id': duplicate['id'], 'keep': keep['id']}]))
        curator.refresh();curator.refresh()
        self.assertEqual({i['id'] for i in self.b.items()}, {keep['id'], different['id']})
        self.assertEqual(curator.changes()[0]['action'], 'duplicate')

    def test_no_model_calls_without_new_event_or_list_change(self):
        calls = []
        curator = self.curator(lambda value: calls.append(value) or decisions())
        curator.refresh();curator.refresh()
        self.a.import_md('- [ ] New task');curator.refresh();curator.refresh()
        self.a.toggle(self.a.items()[0]['id']);curator.refresh()
        self.assertEqual(len(calls), 1)

    def test_concurrent_manual_completion_rejects_stale_reply_without_losing_event(self):
        from left_undone.curation import StaleReview
        self.a.import_md('- [ ] Existing');item = self.a.items()[0]
        def racing(_):
            self.b.done([item['id']])
            return decisions(update=[{'id': item['id'], 'text': 'Rewritten', 'evidence': 'Rewritten'}])
        curator = self.curator(racing)
        with self.assertRaises(StaleReview):curator.review('Rewritten', '', 'race')
        self.assertFalse(self.a.seen('race'))
        self.assertEqual(self.a.items(), [])
        self.assertEqual(curator.changes(), [])

    def test_evidence_and_manual_tombstones_are_required(self):
        self.a.import_md('- [ ] Keep closed');item = self.a.items()[0];self.a.done([item['id']])
        curator = self.curator(lambda _: decisions(add=[{'scope': 'project', 'text': 'Keep closed', 'evidence': 'Keep closed'}]))
        curator.review('Keep closed remains.', '', 'closed')
        self.assertEqual(self.a.items(), [])
        curator.analyze = lambda _: decisions(add=[{'scope': 'project', 'text': 'Invented', 'evidence': 'not present'}])
        with self.assertRaises(ValueError):curator.review('Hello', '', 'invented')
        self.assertFalse(self.a.seen('invented'))

    def test_native_snapshot_absence_does_not_conclude_pending_work(self):
        from left_undone.curation import CuratedStore
        store = CuratedStore(self.path, 'a');self.addCleanup(store.close)
        store.add('task', 'Keep', 'k')
        store.commit_line({}, [{'id': 'empty', 'kind': 'snapshot', 'tasks': []}], {})
        self.assertEqual(store.items()[0]['text'], 'Keep')

    def test_other_promises_are_readonly_context_and_new_session_promises_stay_private(self):
        native = Store(self.path, 'b');self.addCleanup(native.close);native.add('promise', 'Private B')
        seen = []
        def analyze(context):
            seen.extend(context['items'])
            return decisions(add=[{'scope': 'session', 'text': 'Private A', 'evidence': 'Private A'}])
        self.curator(analyze).review('Private A next.', '', 'promise')
        self.assertFalse(next(i['writable'] for i in seen if i['text'] == 'Private B'))
        self.assertEqual([i['text'] for i in self.b.items()], ['Private B'])
        self.assertEqual([i['text'] for i in self.a.items()], ['Private A'])

    def test_collector_passes_request_and_final_reply_and_replays_after_failure(self):
        from left_undone.core import Collector
        from left_undone.curation import CuratedStore
        log = self.path.parent / 'history.jsonl'
        rows = [
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Add keyboard support'}]}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Keep mouse working'}]}},
            {'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 'turn1', 'last_agent_message': 'Keyboard support is next.'}},
        ]
        log.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        calls = []
        def failed(context):calls.append(context);raise RuntimeError('quota')
        curator = self.curator(failed)
        store = CuratedStore(self.path, 'a');self.addCleanup(store.close)
        collector = Collector(store, log, 'codex', None, curator.review)
        with self.assertRaises(RuntimeError):collector.poll()
        self.assertEqual(self.a.items(), [])
        self.assertIn('Add keyboard support', calls[0]['request'])
        self.assertIn('Keep mouse working', calls[0]['request'])
        curator.analyze = lambda context: decisions(add=[{'text': 'Keyboard support', 'scope': 'project', 'evidence': 'Keyboard support is next.'}])
        collector.poll();collector.poll();curator.refresh()
        self.assertEqual([i['text'] for i in self.b.items()], ['Keyboard support'])
        self.assertNotIn('request', store.cursor())

    def test_claude_tool_result_does_not_replace_user_request(self):
        from left_undone.core import Collector
        from left_undone.curation import CuratedStore
        log = self.path.parent / 'claude.jsonl'
        rows = [
            {'type': 'user', 'message': {'content': 'Add keyboard support'}},
            {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'untrusted output'}]}},
            {'type': 'assistant', 'message': {'id': 'm1', 'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': 'Keyboard support next.'}]}},
        ]
        log.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        seen = []
        curator = self.curator(lambda context: seen.append(context) or decisions())
        store = CuratedStore(self.path, 'a');self.addCleanup(store.close)
        Collector(store, log, 'claude', None, curator.review).poll()
        self.assertEqual(seen[0]['request'], 'Add keyboard support')

    def test_aba_changes_invalidate_review_even_when_text_returns_to_original(self):
        from left_undone.curation import StaleReview
        self.a.import_md('- [ ] Original');item = self.a.items()[0]
        def racing(context):
            with self.b.conn:
                self.b.conn.execute('UPDATE items SET text=? WHERE id=?', ('Temporary',item['id']))
                self.b.conn.execute('UPDATE items SET text=? WHERE id=?', ('Original',item['id']))
            return decisions(done=[{'id': item['id'], 'evidence': 'Done'}])
        curator=self.curator(racing)
        with self.assertRaises(StaleReview):curator.review('Done', '', 'aba')
        self.assertEqual(self.a.items()[0]['text'], 'Original')

    def test_foreign_private_promise_cannot_hide_visible_work(self):
        native = Store(self.path, 'b');self.addCleanup(native.close);native.add('promise', 'Review result')
        curator = self.curator(lambda _: decisions(add=[{'scope': 'project', 'text': 'Review result', 'evidence': 'Review result'}]))
        curator.review('Review result next', '', 'visible')
        self.assertEqual([i['text'] for i in self.a.items()], ['Review result'])
        shared = self.a.items()[0]
        foreign = native.items()[0]
        curator.analyze = lambda _: decisions(duplicate=[{'id': shared['id'], 'keep': foreign['id']}])
        curator.review('', '', 'merge-private')
        self.assertEqual(self.a.items()[0]['id'], shared['id'])

    def test_refresh_cache_is_per_viewer_without_idle_thrash(self):
        from left_undone.curation import Curator
        self.a.import_md('- [ ] Mouse support')
        native = Store(self.path, 'b');self.addCleanup(native.close);native.add('task', 'Enable mouse interaction')
        target = self.a.items('import')[0]['id'];duplicate = native.items()[0]['id']
        actions = decisions(duplicate=[{'id': duplicate, 'keep': target}]);calls = []
        ca = self.curator(lambda _: actions)
        cb = Curator(self.b, lambda ctx: calls.append(ctx) or actions)
        ca.refresh();cb.refresh()
        self.assertEqual(len(calls), 1)
        self.assertEqual([i['text'] for i in self.b.items()], ['Mouse support'])
        cb.refresh();ca.refresh();cb.refresh();ca.refresh()
        self.assertEqual(len(calls), 1)

    def test_old_history_cannot_complete_a_new_shared_task(self):
        from left_undone.core import Collector
        from left_undone.curation import CuratedStore
        self.a.import_md('- [ ] Run release verification');item = self.a.items()[0]
        curator = self.curator(lambda _: decisions(done=[{'id': item['id'], 'evidence': 'Release verification passed'}]))
        log=self.path.parent/'old.jsonl'
        log.write_text(json.dumps({'timestamp':'2025-01-01T00:00:00Z','type':'event_msg',
            'payload':{'type':'task_complete','turn_id':'old','last_agent_message':'Release verification passed'}})+'\n')
        db=CuratedStore(self.path,'a');self.addCleanup(db.close)
        Collector(db,log,'codex',None,curator.review).poll()
        self.assertEqual(self.b.items()[0]['id'],item['id'])

    def test_large_checklist_is_supported_and_incomplete_review_does_not_consume_event(self):
        actions=[{'scope':'project','text':f'Task {n}','evidence':f'Task {n}'} for n in range(12)]
        curator=self.curator(lambda _:decisions(add=actions))
        curator.review('\n'.join(a['text'] for a in actions),'','large')
        self.assertEqual(len(self.b.items()),12)
        curator.analyze=lambda _:decisions(complete=False)
        with self.assertRaises(ValueError):curator.review('More work','','incomplete')
        self.assertFalse(self.a.seen('incomplete'))

    def test_historical_completion_cannot_override_a_recent_edit_of_an_old_item(self):
        self.a.import_md('- [ ] Old task');item=self.a.items()[0]
        curator=self.curator(lambda _:decisions(done=[{'id':item['id'],'evidence':'Finished'}]))
        with self.a.conn:
            self.a.conn.execute('UPDATE curation_item_time SET created=0 WHERE item=?',(item['id'],))
            self.a.conn.execute('UPDATE items SET text=? WHERE id=?',('Revised task',item['id']))
        curator.review('Finished','','old-event','2025-01-01T00:00:00Z')
        self.assertEqual(self.a.items()[0]['text'],'Revised task')

    def test_project_reassignment_during_analysis_blocks_old_project_write(self):
        from left_undone.curation import StaleReview
        self.a.import_md('- [ ] Keep');item=self.a.items()[0]
        def move(context):
            with self.b.conn:self.b.conn.execute('UPDATE project_sessions SET project=? WHERE session=?',('other','a'))
            return decisions(done=[{'id':item['id'],'evidence':'Done'}])
        curator=self.curator(move)
        with self.assertRaises(StaleReview):curator.review('Done','','moved')
        self.assertEqual(self.b.items()[0]['text'],'Keep')

    def test_assistant_sample_prompts_are_not_task_evidence(self):
        reply='Para testar, envie:\n   ```text\n   Ficou pendente criar uma tela Teste LU-1350.\n   ```\nEsperado: uma tarefa.'
        seen=[]
        def analyze(context):
            seen.append(context)
            return decisions(add=[{'scope':'project','text':'Criar tela Teste LU-1350',
                                   'evidence':'Ficou pendente criar uma tela Teste LU-1350.'}])
        curator=self.curator(analyze)
        with self.assertRaises(ValueError):curator.review(reply,'Como eu testo?','example')
        self.assertNotIn('Ficou pendente',seen[0]['reply'])
        self.assertEqual(self.a.items(),[])

    def test_real_user_request_still_counts_when_assistant_quotes_it_in_a_fence(self):
        curator=self.curator(lambda _:decisions(add=[{'scope':'project','text':'Criar tela real',
                                                      'evidence':'Criar tela real'}]))
        curator.review('```text\nCriar tela real\n```','Criar tela real é uma pendência aprovada.','real-request')
        self.assertEqual(self.a.items()[0]['text'],'Criar tela real')

    def test_inline_backticks_do_not_swallow_following_real_prose(self):
        from left_undone.curation import prose_evidence
        self.assertIn('Revisar segurança',prose_evidence('```npm test``` é só exemplo.\nRevisar segurança continua pendente.'))

    def test_quoted_fenced_examples_are_also_excluded(self):
        from left_undone.curation import prose_evidence
        result=prose_evidence('Exemplo:\n> ```text\n> Criar tela fictícia\n> ```\nSem tarefa nova.')
        self.assertNotIn('Criar tela fictícia',result)
        self.assertIn('Sem tarefa nova.',result)
