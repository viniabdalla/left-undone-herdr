import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from left_undone import app
from left_undone.core import Store
from left_undone.runtime import Binding


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=self.root/'repo with spaces';self.repo.mkdir()
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        self.sub=self.repo/'src';self.sub.mkdir()
        self.other=self.root/'other';self.other.mkdir()
        subprocess.run(['git','init','-q',str(self.other)],check=True)
        self.state=self.root/'state';self.state.mkdir()

    def binding(self,sid='s1',kind='codex',cwd=None,account='account'):
        path=self.root/(sid+'-'+kind+'.jsonl')
        row=({'type':'session_meta','payload':{'id':sid,'cwd':str(cwd or self.sub)}} if kind=='codex'
             else {'sessionId':sid,'cwd':str(cwd or self.sub),'type':'user'})
        path.write_text(json.dumps(row)+'\n')
        return Binding(kind,sid,account,'w1:p'+sid,'term'+sid,'w1',str(path),10,'1')

    def test_git_subfolder_symlink_and_separate_checkout(self):
        from left_undone.repository import project_root,repository_sessions
        alias=self.root/'alias';alias.symlink_to(self.repo,target_is_directory=True)
        a=self.binding();b=self.binding('s2','claude');c=self.binding('s3',cwd=self.other)
        self.assertEqual(project_root(alias/'src'),self.repo)
        self.assertEqual(repository_sessions([a,b,c],alias),[a,b])
        self.assertEqual(project_root(self.root),self.root)

    def test_wrong_uuid_or_missing_absolute_cwd_cannot_match(self):
        from left_undone.repository import session_project
        b=self.binding()
        for row in [{'type':'session_meta','payload':{'id':'wrong','cwd':str(self.repo)}},
                    {'type':'session_meta','payload':{'id':'s1','cwd':'relative'}},{}]:
            Path(b.history).write_text(json.dumps(row)+'\n')
            self.assertIsNone(session_project(b))

    def test_saved_sessions_and_counts_share_tasks_but_not_promises(self):
        from left_undone.repository import saved_sessions,pending_counts
        a=self.binding();b=self.binding('s2');other=self.binding('s3',cwd=self.other)
        for binding in [a,b,other]:
            (self.state/(binding.key+'.binding.json')).write_text(json.dumps(asdict(binding)))
        (self.state/'broken.binding.json').write_text('{')
        (self.state/'invalid.binding.json').write_text(json.dumps({**asdict(a),'history':None}))
        db=Store(self.state/'state.db',a.key);db.add('import','first');db.add('import','done')
        db.done([db.items()[1]['id']]);db.close()
        db=Store(self.state/'state.db',b.key);db.add('promise','second');db.add('promise','third');db.close()
        self.assertEqual({b.key for b in saved_sessions(self.state,self.repo)},{a.key,b.key})
        self.assertEqual(pending_counts(self.state,[a,b,other]),{a.key:1,b.key:3,other.key:0})

    def test_explicit_project_survives_discovery_and_missing_history_is_isolated(self):
        from left_undone.projects import project_store
        a=self.binding();b=self.binding('s2',cwd=self.other)
        with_store=project_store(self.state,a,self.other)
        with_store.import_md('- [ ] Moved project');with_store.close()
        reopened=project_store(self.state,a)
        self.assertEqual(reopened.project,str(self.other));reopened.close()
        other=project_store(self.state,b)
        self.assertEqual(other.items()[0]['text'],'Moved project');other.close()
        missing=self.binding('missing');Path(missing.history).unlink()
        isolated=project_store(self.state,missing)
        self.assertEqual(isolated.items(),[]);isolated.close()

    def test_worktrees_stay_separate_and_git_environment_cannot_override_repo(self):
        from left_undone.repository import project_root,repository_sessions
        subprocess.run(['git','-C',str(self.repo),'-c','user.name=Test','-c','user.email=test@example.invalid',
                        'commit','--allow-empty','-qm','fixture'],check=True)
        worktree=self.root/'worktree'
        subprocess.run(['git','-C',str(self.repo),'worktree','add','--detach','-q',str(worktree)],check=True)
        b=self.binding(cwd=worktree)
        with patch.dict(os.environ,{'GIT_DIR':str(self.repo/'.git'),'GIT_WORK_TREE':str(self.repo)}):
            self.assertEqual(project_root(worktree),worktree)
            self.assertEqual(repository_sessions([b],self.repo),[])

    def test_empty_repo_does_not_open_global_picker(self):
        opened,api,out=self.run_cli(['open','--repo',str(self.repo)],[self.binding(cwd=self.other)])
        opened.assert_not_called();api.assert_not_called();self.assertIn('Nenhuma sessão',out)

    def run_cli(self,args,bindings,tty=False):
        output=io.StringIO()
        output.isatty=lambda:tty
        with patch('sys.stdin.isatty',return_value=tty),patch('sys.argv',['left-undone',*args]),patch('left_undone.app.candidates',return_value=(bindings,[])),patch('left_undone.app.state_root',return_value=self.state),patch('left_undone.app.open_panel',return_value={'reused':True}) as opened,patch('left_undone.app.herdr',return_value={'ok':True}) as api,contextlib.redirect_stdout(output):
            app.main()
        return opened,api,output.getvalue()

    def test_no_arguments_opens_only_session_of_cwd(self):
        a=self.binding();other=self.binding('s2',cwd=self.other)
        with patch('pathlib.Path.cwd',return_value=self.sub):opened,api,_=self.run_cli([],[a,other])
        opened.assert_called_once_with(a);api.assert_not_called()

    def test_noninteractive_picker_uses_split_and_carries_absolute_repo(self):
        a=self.binding();b=self.binding('s2','claude')
        opened,api,_=self.run_cli(['open','--repo',str(self.sub)],[a,b])
        opened.assert_not_called()
        self.assertIn('LEFT_UNDONE_REPO='+str(self.repo),api.call_args.args)
        self.assertIn('split',api.call_args.args)
        self.assertNotIn('popup',api.call_args.args)

    def test_multiple_sessions_in_terminal_choose_inline_without_plugin_window(self):
        a=self.binding();b=self.binding('s2','claude')
        with patch('left_undone.app.curses.wrapper') as wrapper:
            opened,api,_=self.run_cli(['open','--repo',str(self.sub)],[a,b],tty=True)
        api.assert_not_called();opened.assert_not_called()
        self.assertEqual(wrapper.call_args.args[1],[a,b])

    def test_global_open_in_terminal_chooses_inline(self):
        with patch('left_undone.app.curses.wrapper') as wrapper:
            _,api,_=self.run_cli(['open'],[self.binding()],tty=True)
        api.assert_not_called();self.assertEqual(wrapper.call_count,1)

    def test_global_open_remains_global_despite_inherited_filter(self):
        with patch.dict(os.environ,{'LEFT_UNDONE_REPO':str(self.repo)}):
            opened,api,_=self.run_cli(['open'],[self.binding()])
        opened.assert_not_called()
        self.assertIn('LEFT_UNDONE_REPO=',api.call_args.args)

    def test_closed_session_explains_resume_without_opening(self):
        a=self.binding();(self.state/(a.key+'.binding.json')).write_text(json.dumps(asdict(a)))
        opened,api,out=self.run_cli(['open','--repo',str(self.repo)],[])
        opened.assert_not_called();api.assert_not_called();self.assertIn('retom',out.lower())

    def test_picker_filters_again_in_plugin_context_and_passes_counts(self):
        a=self.binding();other=self.binding('s2',cwd=self.other)
        with patch.dict(os.environ,{'LEFT_UNDONE_REPO':str(self.repo)}),patch('left_undone.app.curses.wrapper') as wrapper:
            self.run_cli(['pick'],[a,other])
        self.assertEqual(wrapper.call_args.args[1],[a])
        self.assertEqual(wrapper.call_args.kwargs['counts'],{a.key:0})


if __name__=='__main__':unittest.main()
