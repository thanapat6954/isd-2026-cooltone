"""Exercise a new partial DB through both real routes; keep outputs for source review."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import site
import socket
import subprocess
import sys
import time
import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--source-pdf', type=Path, required=True)
    parser.add_argument('--questions', type=Path, required=True, help='Development questions only, no expected answers')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    app = args.output/'app'
    app.mkdir()
    for folder in ('lab10_fastapi', 'frontend', 'scr'):
        shutil.copytree(ROOT/folder, app/folder, ignore=shutil.ignore_patterns('__pycache__', '.env'))
    (app/'data/input').mkdir(parents=True)
    os.link(args.source_pdf, app/'data/input'/args.source_pdf.name)
    db = app/'work/lab8b_bit_2565_no_coop/curriculum.db'
    db.parent.mkdir(parents=True)
    shutil.copy2(args.database, db)
    questions = json.loads(args.questions.read_text(encoding='utf-8'))
    if not isinstance(questions, list) or not all(isinstance(q, str) for q in questions):
        raise ValueError('Only question strings are accepted; no labels')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = {**os.environ, 'CURRICULUM_DATABASE_ROOT': str(app), 'PYTHONUTF8': '1',
        'PYTHONPATH': os.pathsep.join([str(app), *site.getsitepackages()])}
    record = {'scope': 'partial raw-plan DB, not full reconstruction/LIVE success',
        'url': f'http://127.0.0.1:{port}', 'cases': [],
        'database_sha256': hashlib.sha256(db.read_bytes()).hexdigest(),
        'source_sha256': hashlib.sha256(args.source_pdf.read_bytes()).hexdigest(),
        'code_hashes': {str(p.relative_to(app)): hashlib.sha256(p.read_bytes()).hexdigest() for p in app.rglob('*.py')}}
    with (args.output/'backend.log').open('wb') as log:
        child = subprocess.Popen([sys._base_executable, '-m', 'uvicorn',
            'lab10_fastapi.curriculum_app.main:app', '--host', '127.0.0.1', '--port', str(port)],
            cwd=app, env=env, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    record['owned_backend_pid'] = child.pid
    def save():
        (args.output/'api-results.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    save()
    try:
        for _ in range(60):
            try:
                if requests.get(record['url']+'/frontend/', timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            if child.poll() is not None:
                raise RuntimeError('Isolated backend exited; see log')
            time.sleep(.2)
        else:
            raise RuntimeError('Startup deadline exhausted')
        for route in ('/api/ask', '/ask'):
            for question in questions:
                payload = {'question': question} if route == '/api/ask' else {'curriculum': 'BIT', 'version': 'latest', 'question': question}
                start = time.perf_counter()
                response = requests.post(record['url']+route, json=payload, timeout=45)
                record['cases'].append({'route': route, 'request': payload, 'status': response.status_code,
                    'elapsed_ms': round((time.perf_counter()-start)*1000, 2), 'body': response.json()})
                save()
    except BaseException:
        child.terminate()
        child.wait(timeout=10)
        raise
    record['ready_for_browser'] = True
    save()
    print(json.dumps({'url': record['url'], 'owned_backend_pid': child.pid,
        'statuses': [c['status'] for c in record['cases']]}))


if __name__ == '__main__':
    main()
