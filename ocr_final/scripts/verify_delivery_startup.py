"""Bounded delivery checks in an already restored isolated application.

Uses development Q&A only for evaluation, never as production inputs.
Does not install packages, download models, rebuild PDFs or control shared services.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_qa_gold import cases, evaluate


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--port', type=int, default=8002)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    url = f'http://127.0.0.1:{a.port}'
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('PYTHON', 'CURRICULUM_DATABASE_ROOT', 'CURRICULUM_BUILD'))}
    env['PYTHONUTF8'] = '1'
    result = {'application': str(ROOT), 'model_service_reused': True,
              'purpose': 'delivery/development verification; not OCR or independent evaluation',
              'steps': [], 'requests': [], 'browser_click': 'blocked by recorded policy; no bypass'}
    def save():
        (a.output/'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    def run(name, command, allow_failure=False, environment=None):
        start = time.perf_counter()
        with (a.output/(name+'.log')).open('wb') as log:
            proc = subprocess.run(command, cwd=ROOT, env=environment or env,
                                  stdout=log, stderr=subprocess.STDOUT, timeout=600)
        result['steps'].append({'name': name, 'exit': proc.returncode,
                                'seconds': round(time.perf_counter()-start, 3)})
        save()
        if not allow_failure and proc.returncode: raise RuntimeError(name+' failed')
        return proc.returncode
    start_cmd = ['pwsh', '-NoProfile', '-File', 'scripts/start_web.ps1', '-Port', str(a.port)]
    stop_cmd = ['pwsh', '-NoProfile', '-File', 'scripts/stop_web.ps1', '-Port', str(a.port)]
    before = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
              for f in ROOT.rglob('*.db')}
    selected = {}
    dataset = json.loads((ROOT/'tests/qa_gold.json').read_text(encoding='utf-8'))
    for key, identity, question, expectation in cases(dataset):
        if identity not in selected and expectation.get('level') != 'missing-evidence':
            selected[identity] = (question, expectation)
    assert len(selected) == 14, 'Development coverage must include every runtime catalog'
    owned = False
    try:
        for cycle in range(2):
            run(f'start-{cycle}', start_cmd); owned = True
            health = requests.get(url+'/api/health', timeout=10).json()
            assert Path(health['lab8b_module']).resolve() == ROOT/'scr/ocr_system/lab8b_curriculum_db.py'
            assert health['status'] == 'ok' and health['queryable_database_count'] == 14
            assert all(Path(db['database_path']).resolve().is_relative_to(ROOT) for db in health['databases'])
            result[f'health-{cycle}'] = health
            assert requests.get(url+'/frontend/', timeout=10).status_code == 200
            for asset in ('app.js', 'active_scope.mjs', 'source-viewer.html', 'source-viewer.js'):
                assert requests.get(url+'/frontend/'+asset, timeout=10).status_code == 200
            if cycle == 0:
                run('development-gold', [sys.executable, '-X', 'utf8', 'scripts/run_qa_gold.py',
                    '--app-root', str(ROOT), '--url', url, '--runs', '1', '--output', str(a.output/'gold.json')])
            for identity, (question, expectation) in selected.items():
                for route in ('/api/ask', '/ask'):
                    payload = {'question': question}
                    if route == '/ask':
                        program = identity.split('-')[0]
                        payload.update(curriculum='AIT' if program == 'AI' else program,
                                       version='old' if '-2560-' in identity else 'latest')
                    response = requests.post(url+route, json=payload, timeout=190)
                    body = response.json(); assert response.status_code == 200, body
                    if route == '/api/ask':
                        errors, citation = evaluate(body, identity, expectation)
                        assert not errors, (identity, errors)
                    else:
                        api = requests.post(url+'/api/ask', json={'question': question}, timeout=190).json()
                        assert body['answer'] == api['answer'], (identity, 'Adapter answer differs')
                        if expectation.get('source'):
                            assert body.get('sources'), (identity, 'Missing frontend citations')
                    result['requests'].append({'cycle': cycle, 'identity': identity, 'route': route,
                                                'question': question, 'response': body})
                    if route == '/ask' and expectation.get('source'):
                        source = expectation['source']; page = expectation.get('page') or body['sources'][0]['page']
                        info = requests.get(f'{url}/api/source-info/{source}?page={page}', timeout=20).json()
                        assert info['sha256'] == hashlib.sha256((ROOT/'data/input'/source).read_bytes()).hexdigest()
                        assert requests.get(f'{url}/source-viewer/{source}?page={page}', timeout=10).status_code == 200
                        image = requests.get(f'{url}/api/source-page/{source}/{page}', timeout=30)
                        assert image.status_code == 200 and image.content.startswith(b'\x89PNG')
                        result.setdefault('sources', []).append(info)
                    save()
            run(f'stop-{cycle}', stop_cmd); owned = False
        missing = dict(env); missing['CURRICULUM_OLLAMA_MODEL'] = 'delivery-verification-model-does-not-exist'
        assert run('missing-model', start_cmd, True, missing) != 0
        pdf = ROOT/'data/input/AI.pdf'; hidden = pdf.with_suffix('.pdf.delivery-check')
        pdf.rename(hidden)
        try: assert run('missing-file', start_cmd, True) != 0
        finally: hidden.rename(pdf)
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', a.port)); occupied.listen()
            assert run('occupied-port', start_cmd, True) != 0
            assert occupied.fileno() >= 0
        after = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
                 for f in ROOT.rglob('*.db')}
        assert before == after
        result.update(completed=True, database_hashes_unchanged=True, model_downloads=0,
                      tested_catalogs=sorted(selected), owned_backend_stopped=True)
    except Exception as e:
        result['failure'] = repr(e)
        raise
    finally:
        if owned: run('failure-owned-stop', stop_cmd, True)
        save()
    print(json.dumps({'completed': True, 'catalogs': len(selected), 'requests': len(result['requests'])}))


if __name__ == '__main__':
    main()
