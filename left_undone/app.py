import argparse
import curses
import fcntl
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from .language import load_language, preference_root, tr
from .core import Collector,Store
from .runtime import Analyzer,Binding,PLUGIN,candidates,herdr,verify
from .ui import panel,picker
from .exchange import export_project, import_choices, import_selected
from .repository import project_root,repository_sessions,saved_sessions,pending_counts
from .projects import project_store
from .curation import Curator,CuratedStore,RULES as CURATOR_RULES
from .turn_review import TURN_RULES, assess, recent_reports
from .collection_request import wait_for_collection


def state_root():
    root=preference_root()
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    return root


def atomic_json(path,data):
    tmp=path.with_suffix('.tmp.'+str(os.getpid()))
    tmp.write_text(json.dumps(data));tmp.replace(path)


def panel_process_alive(pane, binding_file):
    info=herdr('pane','process-info','--pane',pane)['process_info']
    for process in info['foreground_processes']:
        try:
            proc=Path('/proc')/str(process['pid'])
            env=dict(x.split('=',1) for x in (proc/'environ').read_bytes().decode().split('\0') if '=' in x)
            if env.get('LEFT_UNDONE_BINDING')==str(binding_file) and env.get('HERDR_PLUGIN_ENTRYPOINT_ID') in ('panel','picker'):
                return True
        except (OSError,ValueError,UnicodeError):pass
    return False


def wait_collector(root,key):
    with (root/(key+'.collector.lock')).open('w') as lock:
        for _ in range(100):
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                return
            except BlockingIOError:time.sleep(.1)
        raise RuntimeError(tr('The previous collector is stopping. Try reopening in a moment.'))


def open_panel(binding,project=None,offer_import=False):
    verify(binding)
    root=state_root()
    db=project_store(root,binding,project)
    project=getattr(db,'project',None);db.close()
    with (root/(binding.key+'.open.lock')).open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        mapping=root/(binding.key+'.pane.json')
        file=root/(binding.key+'.binding.json')
        if mapping.exists():
            old=json.loads(mapping.read_text())
            try:live=herdr('pane','current','--pane',old['pane'])['pane']
            except RuntimeError:live={}
            if live.get('terminal_id')==old['terminal']:
                previous=json.loads(file.read_text()) if file.exists() else {}
                same=previous==asdict(binding) and old.get('project')==project
                starting=time.time()-old.get('created',0)<15
                # A panel left in another tab (the conversation was moved or a
                # new tab was opened) is invisible from the conversation, so
                # reopen it beside the conversation instead of focusing it.
                try:beside=herdr('pane','current','--pane',binding.pane)['pane'].get('tab_id')==live.get('tab_id')
                except RuntimeError:beside=True
                if same and beside and (starting or panel_process_alive(old['pane'],file)):
                    herdr('plugin','pane','focus',old['pane'])
                    return {'reused':True,'pane':old['pane']}
                herdr('plugin','pane','close',old['pane'])
                wait_collector(root,binding.key)
        atomic_json(file,asdict(binding))
        result=herdr('plugin','pane','open','--plugin',PLUGIN,'--entrypoint','panel','--placement','split',
                     '--target-pane',binding.pane,'--direction','right','--no-focus',
                     '--env','LEFT_UNDONE_BINDING='+str(file),'--env','LEFT_UNDONE_STATE_DIR='+str(root),
                     *(['--env','LEFT_UNDONE_OFFER_IMPORT=1'] if offer_import else []))
        info=result.get('plugin_pane',result).get('pane')
        if not info:raise RuntimeError(tr('Herdr opened panel but returned unexpected format; do not repeat without checking'))
        record={'pane':info['pane_id'],'terminal':info['terminal_id'],'created':time.time(),'project':project}
        atomic_json(mapping,record)
        return record


def open_here(binding,pane):
    """Prepare the panel to replace the picker in this same Herdr pane."""
    verify(binding)
    root=state_root()
    db=project_store(root,binding)
    project=getattr(db,'project',None);db.close()
    terminal=herdr('pane','current','--pane',pane)['pane']['terminal_id']
    with (root/(binding.key+'.open.lock')).open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        mapping=root/(binding.key+'.pane.json')
        file=root/(binding.key+'.binding.json')
        if mapping.exists():
            old=json.loads(mapping.read_text())
            if old.get('pane')!=pane:
                try:live=herdr('pane','current','--pane',old['pane'])['pane']
                except RuntimeError:live={}
                if live.get('terminal_id')==old.get('terminal'):
                    herdr('plugin','pane','close',old['pane'])
                    wait_collector(root,binding.key)
        atomic_json(file,asdict(binding))
        atomic_json(mapping,{'pane':pane,'terminal':terminal,'created':time.time(),'project':project})
    return file


def current_workspace():
    """The Herdr workspace this command runs in, with a readable heading."""
    try:context=json.loads(os.environ.get('HERDR_PLUGIN_CONTEXT_JSON') or '{}')
    except ValueError:context={}
    workspace=context.get('workspace_id') or os.environ.get('HERDR_WORKSPACE_ID')
    if not workspace:return None,None,None
    label=context.get('workspace_label') if context.get('workspace_id')==workspace else None
    folder=context.get('workspace_cwd') if context.get('workspace_id')==workspace else None
    try:
        info=herdr('workspace','get',workspace)['workspace']
        label=info.get('label') or label
        folder=(info.get('worktree') or {}).get('checkout_path') or folder
    except (RuntimeError,KeyError):pass
    heading=tr('Workspace: ')+(label or workspace)
    if folder:
        path=Path(folder)
        try:shown='~/'+str(path.relative_to(Path.home())) if path!=Path.home() else '~'
        except ValueError:shown=str(path)
        if path.name!=label or path==Path.home():heading+=' · '+shown
        else:heading=tr('Workspace: ')+shown
    suffix=Path(folder).name if folder else label
    return workspace,heading,suffix


def current_conversation(bindings):
    """The verified conversation that runs this command (skill call)."""
    pids=[];pid=os.getpid()
    for _ in range(64):
        try:pid=int((Path('/proc')/str(pid)/'stat').read_text().split(') ',1)[1].split()[1])
        except (OSError,ValueError,IndexError):break
        if pid<=1:break
        pids.append(pid)
    for pid in pids:
        matches=[b for b in bindings if b.pid==pid]
        if len(matches)==1:return matches[0]
    thread=os.environ.get('CODEX_THREAD_ID')
    matches=[b for b in bindings if thread and b.kind=='codex' and b.session==thread]
    if len(matches)==1:return matches[0]
    raise RuntimeError(tr('Could not identify the current conversation. Run left-undone list and open --pane --session.'))


def collect(binding,root):
    def terminate(*_):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,terminate)
    with (root/(binding.key+'.collector.lock')).open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        view=project_store(root,binding)
        curator=None
        if getattr(view,'project',None):
            model=Analyzer(binding,rules=CURATOR_RULES)
            delivery_model=Analyzer(binding,rules=TURN_RULES)
            curator=Curator(view, lambda context: assess(delivery_model.request, context, curate=model.request))
        db=(CuratedStore if curator else Store)(root/'state.db',binding.key)
        collector=Collector(db,binding.history,binding.kind,Analyzer(binding),curator.review if curator else None, session_id=binding.session)
        status=root/(binding.key+'.status.json')
        request=root/(binding.key+'.collect-request')
        upgrade_offset = db.cursor()['offset'] if curator and not db.seen('upgrade:turn-review-v2') else None
        try:
            while True:
                try:
                    request.unlink(missing_ok=True)
                    verify(binding)
                    atomic_json(status,{'message':tr('Collecting…')})
                    collector.poll()
                    if upgrade_offset is not None:
                        # Only the collector that owns this verified transcript can replay it.
                        for event, stamp in recent_reports(binding, upgrade_offset):
                            if db.seen(event['id']):
                                curator.review(event['reply'], '', 'delivery-review:'+event['id'], stamp,
                                    analyze=lambda ctx: assess(delivery_model.request, ctx))
                        with db.conn:
                            db.conn.execute('INSERT OR IGNORE INTO processed VALUES(?,?)',
                                            (db.session, 'upgrade:turn-review-v2'))
                        upgrade_offset = None
                    message=curator.refresh() if curator else tr('Collection active')
                    atomic_json(status,{'message':message+' · '+time.strftime('%H:%M:%S')})
                    wait_for_collection(request,3)
                except Exception as e:
                    atomic_json(status,{'message':tr('Error: ')+str(e)[:400]+tr(' · retrying in 30 s')})
                    wait_for_collection(request,30)
        except KeyboardInterrupt:pass
        finally:db.close();view.close()


def main():
    load_language(preference_root())
    os.umask(0o077)
    if sys.argv[1:2] in (['dispatch'], ['dispatch-worker'], ['dispatch-report'], ['dispatch-verdict']):
        from . import dispatch
        try:
            return dispatch.main(sys.argv[1], sys.argv[2:])
        except (OSError, RuntimeError, ValueError, KeyError, sqlite3.Error, subprocess.SubprocessError) as error:
            sys.exit('Left Undone: '+str(error))
    parser=argparse.ArgumentParser(description=tr('Left Undone for Herdr'))
    parser.add_argument('command',nargs='?',choices=['list','open','pick','panel','collect','export','import','items','recover','changes','review','agents','renew'],
                        help=tr('With no command, choose a Herdr conversation'))
    parser.add_argument('--pane');parser.add_argument('--session');parser.add_argument('--binding',default=os.environ.get('LEFT_UNDONE_BINDING'))
    parser.add_argument('--file',type=Path)
    parser.add_argument('--id', dest='import_ids', action='append', metavar='TASK_ID',
                        help='Import this project task (repeat for multiple tasks).')
    parser.add_argument('--confirm-source',help=argparse.SUPPRESS)
    parser.add_argument('--marker',help=tr('Fresh commentary marker used to recover the Codex session'))
    parser.add_argument('--project',type=Path,help=tr('Link this conversation explicitly to the project (open --pane --session)'))
    parser.add_argument('--current',action='store_true',help=tr('Open the panel of the conversation running this command'))
    parser.add_argument('--repo',type=Path,help=tr('Filter sessions by Git root of this folder (without Git: exact folder)'))
    args=parser.parse_args()
    if args.import_ids and (args.command != 'import' or args.file):
        parser.error('--id requires project import without --file')
    if args.project is not None and (args.command!='open' or not args.pane or not args.session or args.repo is not None):
        parser.error(tr('--project requires open --pane --session without --repo'))
    if args.project is not None and not args.project.expanduser().is_dir():parser.error(tr('Project folder does not exist'))
    if args.command is None:
        args.command='open'
    if args.repo is not None and (args.command not in ('list','open','pick') or args.pane or args.session):
        parser.error(tr('--repo requires list/open/pick without --pane or --session'))
    if args.command=='pick' and args.repo is None and os.environ.get('LEFT_UNDONE_REPO'):
        args.repo=Path(os.environ['LEFT_UNDONE_REPO'])
    try:
        root=state_root()
        if args.command=='recover':
            from .recovery import recover
            print(json.dumps(asdict(recover(args.marker)),ensure_ascii=False,indent=2));return
        if args.command in ('list','open','pick'):
            titles={}
            bs,errors=candidates(titles=titles)
            repo=None
            if args.repo is not None:
                if not args.repo.expanduser().is_dir():raise RuntimeError(tr('Repo folder does not exist: ')+str(args.repo))
                repo=project_root(args.repo)
                bs=repository_sessions(bs,repo,root)
            if args.command=='list':
                print(json.dumps({'sessions':[asdict(b) for b in bs],'unavailable':errors},ensure_ascii=False,indent=2));return
            if repo is not None:
                saved=saved_sessions(root,repo)
                inactive=[b for b in saved if b.key not in {b.key for b in bs}]
                notes=[f'Repo: {repo}']
                if inactive:notes.append(tr('{0} saved conversation(s) without a verified active session. Resume in the agent to open the panel.').format(len(inactive)))
                if not bs:
                    notes.append(tr('No active session verifiable in this repo. Open or resume a Codex/Claude conversation in this folder and run left-undone again.'))
                    if args.command=='open':
                        print('\n'.join(notes+errors));return
                errors=notes+errors
            if args.current:
                if args.command!='open' or args.pane or args.session or repo is not None:
                    raise RuntimeError(tr('--current requires open without --pane, --session or --repo'))
                print(json.dumps(open_panel(current_conversation(bs))));return
            heading=suffix=None
            if repo is None and not (args.pane or args.session):
                workspace,heading,suffix=current_workspace()
                if workspace:
                    bs=[b for b in bs if b.workspace==workspace]
                    errors=[e for e in errors if e.startswith(workspace+':')]
            if args.command=='pick':
                pane=os.environ.get('HERDR_PANE_ID')
                here=os.environ.get('HERDR_PLUGIN_ENTRYPOINT_ID')=='picker' and pane
                choose=(lambda b:open_here(b,pane)) if here else (lambda b:open_panel(b,offer_import=True))
                chosen=curses.wrapper(picker,bs,errors,choose,counts=pending_counts(root,bs),titles=titles,heading=heading,suffix=suffix)
                if here and chosen:
                    try:herdr('pane','rename',pane,'Left Undone')
                    except RuntimeError:pass
                    os.environ['LEFT_UNDONE_BINDING']=str(chosen)
                    os.environ['LEFT_UNDONE_OFFER_IMPORT']='1'
                    os.execv(sys.executable,[sys.executable,sys.argv[0],'panel','--binding',str(chosen)])
                return
            if args.pane and args.session:
                matches=[b for b in bs if b.pane==args.pane and b.session==args.session]
                if len(matches)!=1:raise RuntimeError(tr('Unverified pane/session: ')+'; '.join(errors))
                print(json.dumps(open_panel(matches[0],args.project) if args.project is not None else open_panel(matches[0])));return
            if args.pane or args.session:raise RuntimeError(tr('Provide --pane and --session together'))
            if repo is not None and len(bs)==1:
                print(json.dumps(open_panel(bs[0])));return
            if sys.stdin.isatty() and sys.stdout.isatty():
                curses.wrapper(picker,bs,errors,lambda b:open_panel(b,offer_import=True),counts=pending_counts(root,bs),
                               titles=titles,heading=heading,suffix=suffix);return
            # Agent tools have no interactive terminal. Keep their selector inside
            # Herdr too, as a regular split instead of a client popup.
            print(json.dumps(herdr('plugin','pane','open','--plugin',PLUGIN,'--entrypoint','picker','--placement','split','--direction','right',
                                  '--env','LEFT_UNDONE_REPO='+str(repo or ''),
                                  '--env','LEFT_UNDONE_STATE_DIR='+str(root))));return
        if not args.binding:raise RuntimeError(tr('Provide --binding with the file created when the panel opened'))
        binding=Binding(**json.loads(Path(args.binding).read_text()))
        if args.command=='renew':
            from .renewal import ConfirmationRequired, run
            try:
                run(root,binding,args.confirm_source)
            except ConfirmationRequired as error:
                print(error,file=sys.stderr)
                sys.exit(3)
            return
        if args.command=='panel':
            def stop_panel(*_):raise KeyboardInterrupt
            signal.signal(signal.SIGTERM,stop_panel)
            signal.signal(signal.SIGHUP,stop_panel)
            try:
                successor=curses.wrapper(panel,binding,root,Path(args.binding))
                if successor:
                    verify(successor)
                    target=root/(successor.key+'.binding.json')
                    atomic_json(target,asdict(successor))
                    old=root/(binding.key+'.pane.json')
                    if old.exists():
                        record=json.loads(old.read_text())
                        if record['pane']==os.environ.get('HERDR_PANE_ID'):
                            atomic_json(root/(successor.key+'.pane.json'),record)
                            old.unlink()
                    if successor.pane != binding.pane:
                        os.environ['LEFT_UNDONE_CLOSE_SOURCE']=binding.pane
                    os.environ['LEFT_UNDONE_BINDING']=str(target)
                    os.execv(sys.executable,[sys.executable,sys.argv[0],'panel','--binding',str(target)])
            except KeyboardInterrupt:pass
        elif args.command=='collect':collect(binding,root)
        else:
            db=project_store(root,binding)
            try:
                if args.command=='agents':
                    from .agents import monitor
                    verify(binding)
                    curses.wrapper(monitor,binding,db)
                elif args.command=='items':print(json.dumps(db.items(),ensure_ascii=False,indent=2))
                elif args.command=='review':
                    from .manual_review import review_session
                    print(json.dumps(review_session(root,db,binding),ensure_ascii=False,indent=2))
                elif args.command=='changes':
                    if not getattr(db,'project',None):raise RuntimeError(tr('Chat without associated project'))
                    print(json.dumps(Curator(db,None).changes(),ensure_ascii=False,indent=2))
                elif args.file is not None:
                    project = getattr(db, 'project', None)
                    if project and args.file.resolve() == (Path(project) / '.left-undone' / 'tasks.md').resolve():
                        raise ValueError(tr('Use project exchange without --file for this checklist'))
                    if args.command == 'export':
                        args.file.parent.mkdir(parents=True, exist_ok=True)
                        args.file.write_text(db.export_md(), encoding='utf-8')
                        print(args.file)
                    else:
                        print(db.import_md(args.file.read_text(encoding='utf-8')))
                elif not getattr(db, 'project', None):
                    raise RuntimeError(tr('Chat without associated project'))
                elif args.command == 'export':
                    print(export_project(db))
                elif args.import_ids:
                    print(import_selected(db, args.import_ids))
                else:
                    print(json.dumps(import_choices(db), ensure_ascii=False, indent=2))
            finally:db.close()
    except (RuntimeError,OSError,ValueError,KeyError) as e:
        print('Left Undone: '+str(e),file=sys.stderr);sys.exit(1)
