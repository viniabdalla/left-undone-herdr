"""Collect a native provider plan without giving the worker a completion callback."""
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


def codex_plan(job, env, prompt, question_status):
    # The interactive binary has no plan-mode startup flag. Its app-server
    # accepts the same collaboration preset as /plan and emits a typed plan.
    proc = subprocess.Popen(['codex', 'app-server'], cwd=job['cwd'], env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def write(message):
        proc.stdin.write(json.dumps(message) + '\n')
        proc.stdin.flush()

    def receive():
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError('Codex closed before returning a plan')
        return json.loads(line)

    def request(number, method, params):
        write({'id': number, 'method': method, 'params': params})
        while True:
            response = receive()
            if response.get('id') == number and 'method' not in response:
                if 'error' in response:
                    raise ValueError(response['error']['message'])
                return response['result']

    try:
        request(1, 'initialize', {'clientInfo': {'name': 'left_undone', 'version': '1'},
                                  'capabilities': {'experimentalApi': True}})
        write({'method': 'initialized'})
        thread = request(2, 'thread/start', {'model': job['model'], 'cwd': job['cwd'],
                         'sandbox': 'read-only', 'approvalPolicy': 'never'})['thread']['id']
        mode = {'mode': 'plan', 'settings': {'model': job['model'],
                'reasoning_effort': job['effort'], 'developer_instructions': None}}
        turn = request(3, 'turn/start', {'threadId': thread, 'collaborationMode': mode,
                       'input': [{'type': 'text', 'text': prompt}]})['turn']['id']
        plan = ''
        last_message = ''
        while True:
            event = receive()
            method = event.get('method')
            data = event.get('params', {})
            if 'id' in event and method:
                if method == 'item/tool/requestUserInput' and data.get('turnId') == turn:
                    answers = {}
                    question_status('\n'.join(q['question'] for q in data['questions']))
                    for question in data['questions']:
                        print(question['question'], flush=True)
                        for option in question.get('options') or []:
                            print(option['label'], '—', option['description'], flush=True)
                        answers[question['id']] = {'answers': [input('> ')]}
                    write({'id': event['id'], 'result': {'answers': answers}})
                    question_status('')
                else:
                    write({'id': event['id'], 'error': {'code': -32601, 'message': 'Unsupported request'}})
            elif method == 'item/completed' and data.get('turnId') == turn:
                item = data['item']
                if item['type'] == 'plan':
                    plan = item['text']
                elif item['type'] == 'agentMessage':
                    last_message = item['text']
                    print(last_message, flush=True)
            elif method == 'turn/completed' and data['turn']['id'] == turn:
                if data['turn']['status'] != 'completed':
                    raise RuntimeError((data['turn'].get('error') or {}).get('message') or data['turn']['status'])
                if not plan.strip():
                    raise RuntimeError('Codex finished without returning a proposed plan'
                                       + (' · ' + last_message if last_message else ''))
                return plan.strip()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        proc.stdin.close()
        proc.stdout.close()


def run(kind, job, env, question_status):
    prompt = (f"Prepare an implementation plan for this task in {job['cwd']}:\n{job['task']}\n\n"
              f"Parent agent's brief:\n{job['brief']}\n\n"
              "Return the complete proposed plan in the requested language. "
              "Leave all implementation for a separate execution dispatch.")
    if kind == 'codex':
        return codex_plan(job, env, prompt, question_status)
    # Claude writes its native plan to a named Markdown file. A private
    # directory gives this dispatch exclusive ownership of the result.
    with TemporaryDirectory(dir=job['cwd'], prefix='.left-undone-plan-') as directory:
        argv = ['claude', '--print', '--permission-mode', 'plan', '--model', job['model'],
                '--effort', job['effort'], '--tools', 'Read,Glob,Grep,Write,Edit',
                '--settings', json.dumps({'plansDirectory': Path(directory).name}),
                '--output-format', 'json', '--', prompt]
        proc = subprocess.run(argv, cwd=job['cwd'], env=env, stdout=subprocess.PIPE, text=True)
        result = json.loads(proc.stdout) if proc.stdout.strip() else {}
        if proc.returncode or result.get('is_error'):
            raise RuntimeError(result.get('result') or f'Claude exited with status {proc.returncode}')
        files = [p for p in Path(directory).glob('*.md') if not p.is_symlink() and p.is_file()]
        if len(files) == 1:
            plan = files[0].read_text().strip()
            if plan:
                return plan
        message = result.get('result', '').strip()
        raise RuntimeError('Claude finished without writing a proposed plan' + (' · ' + message if message else ''))
