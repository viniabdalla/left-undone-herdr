import argparse
import curses
import fcntl
import json
import os
import signal
import sys
import time
from dataclasses import asdict
from pathlib import Path
from .core import Collector,Store
from .runtime import Analyzer,Binding,PLUGIN,candidates,herdr,verify
from .ui import panel,picker
from .repository import project_root,repository_sessions,saved_sessions,pending_counts


def state_root():
    root=Path(os.environ.get('LEFT_UNDONE_STATE_DIR',str(Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'left-undone-herdr')))
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
            if env.get('LEFT_UNDONE_BINDING')==str(binding_file) and env.get('HERDR_PLUGIN_ENTRYPOINT_ID')=='panel':
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
        raise RuntimeError('Coletor anterior ainda encerrando; tente reabrir em instantes')


def open_panel(binding):
    verify(binding)
    root=state_root()
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
                same=previous==asdict(binding)
                starting=time.time()-old.get('created',0)<15
                if same and (starting or panel_process_alive(old['pane'],file)):
                    return {'reused':True,'pane':old['pane']}
                herdr('plugin','pane','close',old['pane'])
                wait_collector(root,binding.key)
        atomic_json(file,asdict(binding))
        result=herdr('plugin','pane','open','--plugin',PLUGIN,'--entrypoint','panel','--placement','split',
                     '--target-pane',binding.pane,'--direction','right','--no-focus',
                     '--env','LEFT_UNDONE_BINDING='+str(file),'--env','LEFT_UNDONE_STATE_DIR='+str(root))
        info=result.get('plugin_pane',result).get('pane')
        if not info:raise RuntimeError('Herdr abriu painel mas retornou formato inesperado; não repita sem conferir')
        record={'pane':info['pane_id'],'terminal':info['terminal_id'],'created':time.time()}
        atomic_json(mapping,record)
        return record


def collect(binding,root):
    def terminate(*_):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,terminate)
    with (root/(binding.key+'.collector.lock')).open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        db=Store(root/'state.db',binding.key)
        collector=Collector(db,binding.history,binding.kind,Analyzer(binding))
        status=root/(binding.key+'.status.json')
        try:
            while True:
                try:
                    verify(binding)
                    atomic_json(status,{'message':'Coletando…'})
                    collector.poll()
                    atomic_json(status,{'message':'Coleta ativa · '+time.strftime('%H:%M:%S')})
                    time.sleep(3)
                except Exception as e:
                    atomic_json(status,{'message':'Erro: '+str(e)[:400]+' · nova tentativa em 30 s'})
                    time.sleep(30)
        except KeyboardInterrupt:pass
        finally:db.close()


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description='Left Undone para Herdr')
    parser.add_argument('command',nargs='?',choices=['list','open','pick','panel','collect','export','import','items'],
                        help='Sem comando: abre as pendências do repo atual')
    parser.add_argument('--pane');parser.add_argument('--session');parser.add_argument('--binding',default=os.environ.get('LEFT_UNDONE_BINDING'))
    parser.add_argument('--file',type=Path)
    parser.add_argument('--repo',type=Path,help='Filtrar sessões pela raiz Git desta pasta (sem Git: pasta exata)')
    args=parser.parse_args()
    if args.command is None:
        args.command='open'
        if not args.pane and not args.session and args.repo is None:args.repo=Path.cwd()
    if args.repo is not None and (args.command not in ('list','open','pick') or args.pane or args.session):
        parser.error('--repo é usado com list/open/pick, sem --pane/--session')
    if args.command=='pick' and args.repo is None and os.environ.get('LEFT_UNDONE_REPO'):
        args.repo=Path(os.environ['LEFT_UNDONE_REPO'])
    try:
        root=state_root()
        if args.command in ('list','open','pick'):
            bs,errors=candidates()
            repo=None
            if args.repo is not None:
                if not args.repo.expanduser().is_dir():raise RuntimeError('Pasta do repo não existe: '+str(args.repo))
                repo=project_root(args.repo)
                bs=repository_sessions(bs,repo)
            if args.command=='list':
                print(json.dumps({'sessions':[asdict(b) for b in bs],'unavailable':errors},ensure_ascii=False,indent=2));return
            if repo is not None:
                saved=saved_sessions(root,repo)
                inactive=[b for b in saved if b.key not in {b.key for b in bs}]
                notes=[f'Repo: {repo}']
                if inactive:notes.append(f'{len(inactive)} conversa(s) salva(s) sem sessão ativa verificável; retome a conversa no agente para abrir seu painel.')
                if not bs:
                    notes.append('Nenhuma sessão ativa verificável neste repo. Abra ou retome uma conversa Codex/Claude nesta pasta e execute left-undone novamente.')
                    if args.command=='open':
                        print('\n'.join(notes+errors));return
                errors=notes+errors
            if args.command=='pick':
                curses.wrapper(picker,bs,errors,open_panel,counts=pending_counts(root,bs));return
            if args.pane and args.session:
                matches=[b for b in bs if b.pane==args.pane and b.session==args.session]
                if len(matches)!=1:raise RuntimeError('Pane/sessão não verificável: '+'; '.join(errors))
                print(json.dumps(open_panel(matches[0])));return
            if args.pane or args.session:raise RuntimeError('Informe --pane e --session juntos')
            if repo is not None and len(bs)==1:
                print(json.dumps(open_panel(bs[0])));return
            if sys.stdin.isatty() and sys.stdout.isatty():
                curses.wrapper(picker,bs,errors,open_panel,counts=pending_counts(root,bs));return
            # Agent tools have no interactive terminal. Keep their selector inside
            # Herdr too, as a regular split instead of a client popup.
            print(json.dumps(herdr('plugin','pane','open','--plugin',PLUGIN,'--entrypoint','picker','--placement','split','--direction','right',
                                  '--env','LEFT_UNDONE_REPO='+str(repo or ''),
                                  '--env','LEFT_UNDONE_STATE_DIR='+str(root))));return
        if not args.binding:raise RuntimeError('Informe --binding (arquivo produzido pela abertura do painel)')
        binding=Binding(**json.loads(Path(args.binding).read_text()))
        if args.command=='panel':
            def stop_panel(*_):raise KeyboardInterrupt
            signal.signal(signal.SIGTERM,stop_panel)
            signal.signal(signal.SIGHUP,stop_panel)
            try:curses.wrapper(panel,binding,root,Path(args.binding))
            except KeyboardInterrupt:pass
        elif args.command=='collect':collect(binding,root)
        else:
            db=Store(root/'state.db',binding.key)
            try:
                file=args.file or root/'exports'/binding.key/'latest.md'
                if args.command=='items':print(json.dumps(db.items(),ensure_ascii=False,indent=2))
                elif args.command=='export':file.parent.mkdir(parents=True,exist_ok=True);file.write_text(db.export_md());print(file)
                else:print('Importados:',db.import_md(file.read_text()))
            finally:db.close()
    except (RuntimeError,OSError,ValueError,KeyError) as e:
        print('Left Undone: '+str(e),file=sys.stderr);sys.exit(1)
