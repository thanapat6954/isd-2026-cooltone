"""Isolated Windows handoff rehearsal; owned services only, source facts unchanged."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import requests


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-app', type=Path, required=True)
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--venv-source', type=Path, required=True)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--pdf-folder', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    # Child commands run from the isolated app; keep evidence in one destination.
    a.output = a.output.resolve()
    app = a.workspace.resolve()/'checkout with spaces/ocr_final'
    for port in (8001, 11435):
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1', port)) == 0:
                raise ValueError(f'Port {port} occupied; no process stopped')
    if (app/'scripts/start_web.ps1').exists():
        raise ValueError('Use a new workspace; existing evidence is preserved')
    shutil.copytree(a.source_app, app, dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('venv', '.venv', '__pycache__', 'work', 'reports', 'input', '*.db', '.env', 'node_modules'))
    def quote(path):
        return "'"+str(path).replace("'", "''")+"'"
    subprocess.run(['pwsh', '-NoProfile', '-Command', 'New-Item -ItemType Junction -Path '+quote(app/'venv')+' -Target '+quote(a.venv_source)], check=True, capture_output=True)
    shutil.copy2(app/'lab10_fastapi/curriculum_app/.env.example', app/'lab10_fastapi/curriculum_app/.env')
    (app/'data/input').mkdir(parents=True, exist_ok=True)
    for source in a.pdf_folder.glob('*.pdf'):
        os.link(source, app/'data/input'/source.name)
    env = {**os.environ, 'PYTHONUTF8': '1', 'CURRICULUM_OLLAMA_URL': 'http://127.0.0.1:11435',
           'CURRICULUM_DATABASE_ROOT': '.', 'CURRICULUM_OLLAMA_MODEL': 'qwen3:4b'}
    result = {'scope': 'current uncommitted code, isolated DB snapshots, reused verified venv/model files, separate cold service processes',
              'workspace': str(app), 'steps': [], 'limitations': ['Initial downloads/full OCR install not rerun', 'Not cold model generation benchmark']}
    def save():
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    def run(name, command):
        # A detached Windows child can inherit pipe handles and delay communicate()
        # after the launcher exits. File-backed logs keep the rehearsal bounded.
        stdout_path = a.output.parent/(name+'.stdout.log')
        stderr_path = a.output.parent/(name+'.stderr.log')
        with stdout_path.open('w', encoding='utf-8') as stdout, stderr_path.open('w', encoding='utf-8') as stderr:
            proc = subprocess.run(command, cwd=app, env=env, stdout=stdout, stderr=stderr, timeout=120)
        result['steps'].append({'step': name, 'command': [str(c) for c in command], 'exit_code': proc.returncode,
                                'stdout': stdout_path.read_text(encoding='utf-8'), 'stderr': stderr_path.read_text(encoding='utf-8')})
        save()
        print(name, 'exit', proc.returncode, flush=True)
        if proc.returncode:
            raise RuntimeError(name+' failed; raw output saved')
    python = str(app/'venv/Scripts/python.exe')
    save()
    run('runtime_install', [python, '-m', 'pip', 'install', '-r', 'requirements-web-tested.txt'])
    run('restore', [python, 'scripts/runtime_bundle.py', 'restore', '--bundle', str(a.bundle), '--app-root', '.'])
    def start_model():
        log = (a.output.parent/'isolated_ollama.log').open('ab')
        model = subprocess.Popen([shutil.which('ollama'), 'serve'], env={**env, 'OLLAMA_HOST': '127.0.0.1:11435'},
            stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(60):
            if model.poll() is not None:
                raise RuntimeError('Owned Ollama exited; see log')
            try:
                tags = requests.get('http://127.0.0.1:11435/api/tags', timeout=2).json()
                if any(m.get('name') == 'qwen3:4b' for m in tags.get('models', [])):
                    result['model_pid'] = model.pid
                    result['model_started_ticks'] = subprocess.check_output(['pwsh','-NoProfile','-Command',f'(Get-Process -Id {model.pid}).StartTime.ToUniversalTime().Ticks'],text=True).strip()
                    save()
                    return model
            except requests.RequestException:
                pass
            time.sleep(.25)
        raise RuntimeError('Owned model service not ready')
    model = start_model()
    for cycle in ('first', 'restart'):
        run(cycle+'_preflight', [python, 'scripts/check_setup.py', '--output', str(a.output.parent/(cycle+'_preflight.json'))])
        run(cycle+'_start', ['pwsh','-NoProfile','-File',str(app/'scripts/start_web.ps1'),'-Port','8001'])
        response = requests.post('http://127.0.0.1:8001/ask', json={'curriculum':'IT','version':'old',
            'question':'แผนไม่สหกิจศึกษา หลักสูตรนี้มีกี่ปี'}, timeout=30)
        body = response.json()
        passed = (response.status_code == 200 and '4 ปี' in body.get('answer','') and
                  any(s.get('page') == 6 and s.get('book_page') == 1 for s in body.get('sources',[])))
        result['steps'].append({'step':cycle+'_real_answer', 'passed':passed, 'status':response.status_code, 'response':body})
        save()
        if not passed:
            raise RuntimeError('Source-backed answer failed')
        if cycle == 'first':
            run('stop_backend', ['pwsh','-NoProfile','-File',str(app/'scripts/stop_web.ps1'),'-Port','8001'])
            model.terminate()
            model.wait(timeout=20)
            result['owned_model_stopped'] = True
            model = start_model()
    result['ready_for_browser'] = True
    save()
    print('Ready for browser: http://127.0.0.1:8001/frontend/', flush=True)


if __name__ == '__main__':
    main()
