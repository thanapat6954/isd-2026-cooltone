"""Bounded checks using only the already prepared fresh handoff copy."""
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    app = args.workspace.resolve()/'project with spaces/ocr_final'
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    python = str(app/'venv/Scripts/python.exe')
    for port in (8002,11436):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1',port)) == 0:
                raise ValueError('Occupied port; no service stopped')
    env = {k:v for k,v in os.environ.items() if not k.startswith(('CURRICULUM_','OLLAMA_','PYTHON','PIP_'))}
    env.update(PYTHONUTF8='1', CURRICULUM_DATABASE_ROOT='.', CURRICULUM_OLLAMA_MODEL='qwen3:4b',
        CURRICULUM_OLLAMA_URL='http://127.0.0.1:11436', OLLAMA_HOST='127.0.0.1:11436',
        OLLAMA_MODELS=str(args.workspace.resolve()/'fresh-models'), OLLAMA_NO_CLOUD='1')
    result = {'scope':'fresh handoff API/development regressions, not browser or held-out evaluation','steps':[]}
    def save():
        (output/'state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    def run(name,command,timeout=180,allowed=(0,)):
        result['active_step']=name
        save()
        with (output/(name+'.stdout.log')).open('wb') as out, (output/(name+'.stderr.log')).open('wb') as err:
            proc=subprocess.run(command,cwd=app,env=env,stdout=out,stderr=err,timeout=timeout)
        result['steps'].append({'step':name,'exit_code':proc.returncode})
        save()
        if proc.returncode not in allowed:
            raise RuntimeError(name+' failed; preserved logs')
    before={str(f.relative_to(app)):hashlib.sha256(f.read_bytes()).hexdigest() for f in app.rglob('curriculum.db')}
    model=None
    backend=False
    try:
        with (output/'ollama.log').open('wb') as log:
            model=subprocess.Popen([shutil.which('ollama'),'serve'],env=env,stdout=log,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW)
        result['model_pid']=model.pid
        save()
        for _ in range(100):
            try:
                with urllib.request.urlopen('http://127.0.0.1:11436/api/tags',timeout=2) as reply:
                    result['model_tags']=json.loads(reply.read())
                break
            except OSError:
                time.sleep(.2)
        else:
            raise TimeoutError('Model not ready')
        run('missing_model',[python,'scripts/verify_missing_model.py','--app-root','.',
            '--output',str(output/'missing-model.json')])
        run('launcher',['pwsh','-NoProfile','-File','scripts/start_web.ps1','-Port','8002'])
        backend=True
        run('gold',[python,'scripts/run_qa_gold.py','--app-root','.', '--url','http://127.0.0.1:8002',
            '--output',str(output/'gold.json'),'--runs','1'],timeout=240)
        run('audit',[python,'scripts/audit_all.py','--app-root','.', '--out',str(output/'audit')],allowed=(0,1))
        # Fetch a second real citation; this is server rendering, never browser automation.
        for file,page,book in [('BIT-65.pdf',28,23)]:
            with urllib.request.urlopen(f'http://127.0.0.1:8002/api/source-info/{file}?page={page}') as response:
                info=json.loads(response.read())
            if info['printed_page'] != book:
                raise ValueError('Citation mapping mismatch')
            with urllib.request.urlopen(f'http://127.0.0.1:8002/api/source-page/{file}/{page}',timeout=60) as response:
                image=response.read()
            if not image.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('PNG rendering failed')
            (output/'bit-citation.png').write_bytes(image)
            result['bit_citation']=info
        result['completed']=True
    except Exception as exc:
        result['failure']=str(exc)
        raise
    finally:
        if backend:
            run('stop',['pwsh','-NoProfile','-File','scripts/stop_web.ps1','-Port','8002'])
        if model is not None:
            model.terminate()
            model.wait(timeout=30)
        result['db_unchanged']=before == {str(f.relative_to(app)):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in app.rglob('curriculum.db')}
        result['owned_services_stopped']=True
        save()


if __name__=='__main__':
    main()
