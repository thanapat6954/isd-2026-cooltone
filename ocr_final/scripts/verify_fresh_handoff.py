"""Fresh environment and empty-model-store rehearsal, never using LIVE at runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--project-root', type=Path, required=True)
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--backend-port', type=int, default=8002)
    p.add_argument('--model-port', type=int, default=11436)
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    if not a.resume and (a.workspace.exists() or a.output.exists()):
        raise ValueError('Use a new rehearsal directory; never overwrite evidence')
    for port in (a.backend_port, a.model_port):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise ValueError(f'Port {port} already used; nothing stopped')
    project = a.workspace.resolve()/'project with spaces'
    app = project/'ocr_final'
    a.output = a.output.resolve()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    state = {'scope':'fresh venv, pip without cache, new empty model store, copied artifacts',
             'project':str(project), 'steps':[], 'limitations':[
                 'Uses installed Python/Ollama executables; OS installers not rehearsed',
                 'Browser verification blocked separately; API/source-render checks are not UI verification']}
    if a.resume:
        state = json.loads(a.output.read_text(encoding='utf-8'))
        if state.get('completed') or (state.get('model_pid') and not state.get('owned_services_stopped')):
            raise ValueError('Check/stop only verified-owned jobs before resuming; never duplicate services')
        state.pop('failure', None)
        state['resumed_after'] = state.get('active_step')
    def save():
        partial = a.output.with_suffix('.partial')
        partial.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        for attempt in range(10):
            try:
                partial.replace(a.output)
                break
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(.2)
    env = {k:v for k,v in os.environ.items() if not k.startswith(('CURRICULUM_', 'OLLAMA_', 'PYTHON', 'PIP_'))}
    env.update(PYTHONUTF8='1', PIP_NO_CACHE_DIR='1', PIP_CONFIG_FILE=os.devnull,
               CURRICULUM_DATABASE_ROOT='.', CURRICULUM_OLLAMA_MODEL='qwen3:4b',
               CURRICULUM_OLLAMA_URL=f'http://127.0.0.1:{a.model_port}',
               OLLAMA_HOST=f'127.0.0.1:{a.model_port}',
               OLLAMA_MODELS=str(a.workspace.resolve()/'fresh-models'), OLLAMA_NO_CLOUD='1')
    model_url = env['CURRICULUM_OLLAMA_URL']
    backend_url = f'http://127.0.0.1:{a.backend_port}'
    def http(url, payload=None, timeout=30):
        request = urllib.request.Request(url,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    def run(name, command, timeout=240):
        if a.resume and name in {'fresh_venv','fresh_packages','pip_check','restore'} and any(
                s['step'] == name and s['exit_code'] == 0 for s in state['steps']):
            return
        state['active_step'] = name
        save()
        start = time.perf_counter()
        out = a.output.parent/(name+'.stdout.log')
        err = a.output.parent/(name+'.stderr.log')
        with out.open('wb') as stdout, err.open('wb') as stderr:
            result = subprocess.run(command, cwd=app, env=env, stdout=stdout,
                                    stderr=stderr, timeout=timeout)
        state['steps'].append({'step':name,'exit_code':result.returncode,
            'seconds':round(time.perf_counter()-start,2),'command':list(map(str,command)),
            'stdout':str(out),'stderr':str(err)})
        save()
        if result.returncode:
            raise RuntimeError(name+' failed; inspect saved logs')
    save()
    if not a.resume:
        shutil.copytree(a.project_root/'ocr_final', app, ignore=shutil.ignore_patterns(
            'venv','.venv','work','reports','input','tmp','*.db','*.db-wal','*.db-shm',
            '.env','__pycache__','node_modules'))
        shutil.copy2(a.project_root/'README.md', project/'README.md')
        shutil.copytree(a.bundle, project/'supplied-artifacts/runtime-data')
        shutil.copy2(app/'lab10_fastapi/curriculum_app/.env.example', app/'lab10_fastapi/curriculum_app/.env')
    if not (project/'docs').exists():
        shutil.copytree(a.project_root/'docs', project/'docs', ignore=shutil.ignore_patterns(
            'results','history','*.log','PROGRESS.md'))
    run('fresh_venv', ['py','-3.11','-m','venv','venv'])
    python = str(app/'venv/Scripts/python.exe')
    run('fresh_packages', [python,'-m','pip','--isolated','install','--no-cache-dir',
        '--index-url','https://pypi.org/simple','-r','requirements-web-tested.txt'], timeout=600)
    run('pip_check', [python,'-m','pip','check'])
    run('restore', [python,'scripts/runtime_bundle.py','restore','--bundle',
        str(project/'supplied-artifacts/runtime-data'),'--app-root','.'])
    state['runtime_code_sha256'] = {str(f.relative_to(app)):hashlib.sha256(f.read_bytes()).hexdigest()
        for folder in ('lab10_fastapi','frontend','scripts') for f in (app/folder).rglob('*')
        if f.is_file() and f.suffix in {'.py','.js','.mjs','.html','.css','.ps1'}}
    state['artifact_manifest_sha256'] = hashlib.sha256(
        (project/'supplied-artifacts/runtime-data/manifest.json').read_bytes()).hexdigest()
    run('runtime_versions',[python,'-m','pip','freeze'])
    def start_model():
        log = (a.output.parent/'fresh-ollama.log').open('ab')
        proc = subprocess.Popen([shutil.which('ollama'),'serve'], env=env,
            stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        log.close()
        state['model_pid']=proc.pid
        save()
        for _ in range(120):
            if proc.poll() is not None:
                raise RuntimeError('Isolated model server exited')
            try:
                http(model_url+'/api/tags', timeout=2)
                return proc
            except OSError:
                time.sleep(.25)
        raise TimeoutError('Isolated model server not ready')
    model = None
    backend_started = False
    try:
        model = start_model()
        tags = http(model_url+'/api/tags')
        initial = state.setdefault('initial_tags',tags)
        if initial.get('models') or (tags.get('models') and not a.resume):
            raise ValueError('Model store was not empty')
        state['active_step']='first_model_download'
        save()
        start = time.perf_counter()
        request = urllib.request.Request(model_url+'/api/pull',
            data=json.dumps({'model':'qwen3:4b','stream':True}).encode(),
            headers={'Content-Type':'application/json'})
        download_log = a.output.parent/'model-pull.jsonl'
        if not tags.get('models'):
            with urllib.request.urlopen(request, timeout=120) as response, download_log.open('ab') as log:
                for line in response:
                    log.write(line)
                    log.flush()
                    progress = json.loads(line)
                    state['download_progress']=progress
                    save()
                    if progress.get('error'):
                        raise RuntimeError(progress['error'])
            state['download_seconds']=round(time.perf_counter()-start,2)
        else:
            state['download_reused_from_same_rehearsal']=True
        state['installed_tags']=http(model_url+'/api/tags')
        state['model_store_bytes']=sum(f.stat().st_size for f in Path(env['OLLAMA_MODELS']).rglob('*') if f.is_file())
        state['model_test']=http(model_url+'/api/generate', {
            'model':'qwen3:4b','prompt':'Return the single word READY.','stream':False,
            'think':False,'options':{'temperature':0,'num_predict':32}}, timeout=180)
        save()
        db_hashes = {str(f.relative_to(app)): hashlib.sha256(f.read_bytes()).hexdigest()
                     for f in app.rglob('curriculum.db')}
        for cycle in ('first','restart'):
            run(cycle+'_preflight',[python,'scripts/check_setup.py','--output',str(a.output.parent/(cycle+'-preflight.json'))])
            run(cycle+'_start',['pwsh','-NoProfile','-File','scripts/start_web.ps1','-Port',str(a.backend_port)])
            backend_started = True
            answers = []
            for route, payload in [('/ask',{'curriculum':'IT','version':'old',
                'question':'แผนไม่สหกิจศึกษา หลักสูตรนี้มีกี่ปี'}),
                ('/api/ask',{'question':'หลักสูตร BIT พ.ศ.2565 แผนไม่สหกิจศึกษา วิชารหัส 06036123 ชื่ออะไรและมีกี่หน่วยกิต'})]:
                body = http(backend_url+route,payload)
                answers.append({'route':route,'request':payload,'response':body})
                state[cycle+'_answers']=answers
                save()
                if not body.get('answer') or (route == '/ask' and not body.get('sources')) or (route == '/api/ask' and not body.get('rows')):
                    raise ValueError('Real answer/evidence missing; /ask intentionally does not expose rows')
                if route == '/ask' and '4' not in body['answer']:
                    raise ValueError('Program-duration answer missing expected DB value')
                if route == '/api/ask' and not any(str(row.get('code')) == '06036123' for row in body['rows']):
                    raise ValueError('Retrieved evidence does not identify requested course')
            state[cycle+'_answers']=answers
            with urllib.request.urlopen(backend_url+'/frontend/') as response:
                state[cycle+'_frontend_status']=response.status
            # Server rendering is not proof of visible browser rendering.
            sources = answers[0]['response'].get('sources',[])
            state[cycle+'_citation_checks']=[]
            for source in sources[:1]:
                file = source.get('source_file') or source.get('file')
                if not file:
                    files = [f.name for f in (app/'data/input').glob('*.pdf') if f.name in source.get('section','')]
                    if len(files) != 1:
                        raise ValueError('Citation section does not identify one supplied source file')
                    file = files[0]
                page = source.get('page')
                info = http(backend_url+f'/api/source-info/{file}?page={page}')
                if source.get('book_page') != info.get('printed_page'):
                    raise ValueError('Citation/DB printed-page mapping mismatch')
                with urllib.request.urlopen(backend_url+f'/api/source-page/{file}/{page}', timeout=60) as response:
                    rendered = response.read()
                if not rendered.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValueError('Source renderer did not return PNG bytes')
                image = a.output.parent/(cycle+'-citation.png')
                image.write_bytes(rendered)
                state[cycle+'_citation_checks'].append({'file':file,'pdf_page':page,
                    'book_page':source.get('book_page'), 'source_info':info, 'rendered_png':str(image),
                    'rendered_bytes':len(rendered), 'source_exists':bool(file and (app/'data/input'/file).is_file())})
            save()
            run(cycle+'_stop',['pwsh','-NoProfile','-File','scripts/stop_web.ps1','-Port',str(a.backend_port)])
            backend_started = False
            model.terminate()
            model.wait(timeout=30)
            model = None
            if cycle == 'first':
                model = start_model()
        state['db_unchanged_after_startup']=db_hashes == {
            str(f.relative_to(app)):hashlib.sha256(f.read_bytes()).hexdigest() for f in app.rglob('curriculum.db')}
        state['completed']=True
        state['active_step']=None
        save()
    except Exception as exc:
        state['failure']=f'{type(exc).__name__}: {exc}'
        save()
        raise
    finally:
        if backend_started:
            run('cleanup_backend',['pwsh','-NoProfile','-File','scripts/stop_web.ps1','-Port',str(a.backend_port)])
        if model is not None:
            model.terminate()
            model.wait(timeout=30)
        state['owned_services_stopped']=True
        save()


if __name__ == '__main__':
    main()
