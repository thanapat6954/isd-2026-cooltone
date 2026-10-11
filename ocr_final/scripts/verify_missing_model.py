"""Real missing-model readiness/API behavior; never remove or download models."""
import argparse
import json
import os
from pathlib import Path
import sys
import socket
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve existing evidence')
    os.environ['CURRICULUM_DATABASE_ROOT'] = str(args.app_root.resolve())
    os.environ['CURRICULUM_OLLAMA_MODEL'] = 'curriculum-audit-missing-20261009:latest'
    import requests
    import uvicorn
    from lab10_fastapi.curriculum_app import main as web
    before = requests.get(web.settings.ollama_url+'/api/tags', timeout=10).json()
    if any(m['name'] == web.settings.ollama_model for m in before['models']):
        raise ValueError('Chosen missing model actually exists; no changes made')
    result = {'scope':'in-process real application routes and real Ollama, not browser/first-machine install',
              'configured_missing_model':web.settings.ollama_model, 'ready':web.model.available(), 'cases':[]}
    missing = requests.post(web.settings.ollama_url+'/api/generate',json={
        'model':web.settings.ollama_model,'prompt':'Readiness probe','stream':False},timeout=10)
    result['model_request']={'status':missing.status_code,'body':missing.json()}
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(web.app,host='127.0.0.1',port=port,log_level='error'))
    worker = threading.Thread(target=server.run,daemon=True)
    worker.start()
    deadline = time.monotonic()+15
    while not server.started:
        if time.monotonic()>deadline:
            raise TimeoutError('Missing-model probe backend did not start')
        time.sleep(.05)
    try:
        for route,payload in [('/api/ask', {'question':'หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาวิชาโครงงาน'}),
                              ('/ask', {'curriculum':'IT','version':'latest','question':'หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาวิชาโครงงาน'})]:
            response = requests.post(f'http://127.0.0.1:{port}'+route, json=payload,timeout=30)
            result['cases'].append({'route':route,'status':response.status_code,'body':response.json()})
    finally:
        server.should_exit = True
        worker.join(timeout=10)
        result['server_stopped'] = not worker.is_alive()
    after = requests.get(web.settings.ollama_url+'/api/tags', timeout=10).json()
    result['models_unchanged'] = before == after
    # Evidence-only paths need not call the model; an explicit DB gap is legitimate.
    for case in result['cases']:
        case['outcome'] = ('model_unavailable' if case['status']==503 else
            'database_only_gap' if case['status']==200 and
            'หลักฐานจาก SQLite ยังไม่พอ' in case['body'].get('answer','') else 'unexpected')
    result['passed'] = (not result['ready'] and result['models_unchanged'] and missing.status_code==404
        and all(c['outcome']!='unexpected' for c in result['cases']))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    return int(not result['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
