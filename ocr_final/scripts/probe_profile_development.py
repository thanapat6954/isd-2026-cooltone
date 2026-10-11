"""Bounded, resumable development HTTP matrix; SQLite snapshots, no gold inputs."""
import argparse
from contextlib import closing
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save_result(path, result):
    partial = path.with_suffix('.partial')
    with partial.open('w', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    partial.replace(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--questions', type=Path, help='Exposed development wording only; never held-out/gold answers')
    p.add_argument('--category', action='append', help='Rerun only affected development categories')
    p.add_argument('--profile', action='append', help='Exact recorded curriculum_name; limits reruns to affected profiles')
    a = p.parse_args()
    from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly
    source_registry = DatabaseRegistry(a.app_root)
    profiles = source_registry.active_catalogs
    if a.profile:
        profiles = [item for item in profiles if item.curriculum_name in a.profile]
        if {item.curriculum_name for item in profiles} != set(a.profile):
            raise ValueError('Unknown recorded profile selector')
    a.output.mkdir(parents=True, exist_ok=a.resume)
    result_path = a.output / 'results.json'
    dependencies = {str(item.path): digest(item.path) for item in profiles}
    dependencies.update({str(path): digest(path) for path in (ROOT / 'lab10_fastapi/curriculum_app').glob('*.py')})
    development = None
    if a.questions:
        development = json.loads(a.questions.read_text(encoding='utf-8'))['cases']
        if a.category:
            development = [c for c in development if c['category'] in a.category]
            if {c['category'] for c in development} != set(a.category):
                raise ValueError('Unknown development category')
        dependencies[str(a.questions.resolve())] = digest(a.questions)
        dependencies['selected_categories'] = sorted(a.category or [])
    if a.resume:
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if result['dependencies'] != dependencies:
            raise ValueError('Dependencies changed; use a new output directory')
    else:
        result = {'scope': 'DB-relative development tests, NOT independent source/held-out accuracy',
                  'dependencies': dependencies, 'cases': [], 'model_calls': []}
    isolated = a.output / 'app'
    for item in profiles:
        target = isolated / item.relative_path
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with closing(open_readonly(item.path)) as src, closing(sqlite3.connect(target)) as dst:
                src.backup(dst)
    os.environ['CURRICULUM_DATABASE_ROOT'] = str(isolated.resolve())
    import requests
    import uvicorn
    from lab10_fastapi.curriculum_app import main as web
    web.model.config = replace(web.model.config, request_timeout=45)
    traces = []
    real_ask = web.model.ask
    def trace_ask(*args, **kwargs):
        value = real_ask(*args, **kwargs)
        traces.append(value)
        return value
    web.model.ask = trace_ask
    real_generate = web.model.lab8b.ollama_generate
    def trace_generate(*args, **kwargs):
        started = time.perf_counter()
        entry = {'model': kwargs['model']}
        result['model_calls'].append(entry)
        try:
            value = real_generate(*args, **kwargs)
            entry['output'] = value
            return value
        except Exception as exc:
            entry['error'] = str(exc)
            raise
        finally:
            entry['elapsed_ms'] = round((time.perf_counter()-started)*1000, 2)
    web.model.lab8b.ollama_generate = trace_generate
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(web.app, host='127.0.0.1', port=port, log_level='error'))
    worker = threading.Thread(target=server.run, daemon=True)
    worker.start()
    until = time.monotonic()+15
    while not server.started:
        if time.monotonic()>until:
            raise TimeoutError('Startup failed')
        time.sleep(.05)
    completed = {case['id'] for case in result['cases']}
    try:
        for index, item in enumerate(profiles):
            identity = item.curriculum_name
            program = (item.program_id or 'legacy').split('-')[0]
            prefix = 'ฐานข้อมูลเดิม legacy' if not item.program_id else f"หลักสูตร {program} {item.curriculum_version} {'ไม่เข้าร่วมสหกิจ' if item.plan == 'no-coop' else 'สหกิจ'}"
            with closing(open_readonly(item.path)) as db:
                if item.schema_family == 'lab8b':
                    names = [dict(row) for row in db.execute('SELECT code,name_th,name_en,credits,description_th FROM course WHERE name_th IS NOT NULL AND code NOT LIKE \'ELEC-%\' ORDER BY code LIMIT 3')]
                    edges = [dict(row) for row in db.execute('SELECT p.code,p.requires,a.name_th AS course_name,b.name_th AS required_name FROM prerequisite p JOIN course a ON a.code=p.code JOIN course b ON b.code=p.requires LIMIT 1')]
                else:
                    names, edges = [], []
            # Reasoning/wording varies across categories; facts are checked separately.
            topics = names[:2]
            if edges:
                e = edges[0]
                positive = f"อธิบายความสัมพันธ์ระหว่าง{e['course_name']}กับ{e['required_name']} ตามข้อมูลที่บันทึก"
                category = 'stored_relationship'
            elif topics:
                positive = f"ช่วยเทียบ {topics[0]['code']} กับ {topics[-1]['code']} ชื่อภาษาอังกฤษและหน่วยกิตต่างกันยังไง"
                category = 'course_comparison'
            else:
                positive, category = 'มีรายวิชาอะไรบ้าง', 'legacy_catalog'
            wording = ['อธิบายเนื้อหาวิชาการเขียนโปรแกรม', 'ขอรายละเอียดเนื้อหาของรายวิชาที่เกี่ยวกับธุรกิจ', 'ระบบคอมพิวเตอร์เรียนเกี่ยวกับอะไร', 'ช่วยเล่าเนื้อหาของโครงงาน']
            cases = [(category, positive, {'names': names, 'edges': edges}),
                     ('description_or_ambiguity', wording[index % len(wording)], {'description_evidence': names}),
                     ('unsupported_planning', 'ถ้ายังไม่ผ่านทุกวิชา ช่วยรับรองว่าจบได้ในสามปีครึ่งและลงทะเบียนเทอมหน้าได้แน่นอน', {'limitation': 'Do not infer offering/permission or guarantee graduation'})]
            if development is not None:
                cases = [(c['category'], c['question'], {'applicability': c['scope']}) for c in development]
            for number, (kind, text, expectation) in enumerate(cases):
                question = prefix + ': ' + text
                for route in ('/api/ask', '/ask'):
                    key = f'{identity}-{number}-{route}'
                    if key in completed:
                        continue
                    web.model._answer_cache.clear()
                    traces.clear()
                    payload = {'question': question}
                    if route == '/ask':
                        payload.update(curriculum=program, version='old' if item.curriculum_version == 2560 else 'latest')
                    started = time.perf_counter()
                    try:
                        response = requests.post(f'http://127.0.0.1:{port}{route}', json=payload, timeout=55)
                        value, status = response.json(), response.status_code
                    except requests.RequestException as exc:
                        value, status = {'transport_error': str(exc)}, None
                    result['cases'].append({'id': key, 'profile': identity, 'category': kind, 'route': route,
                        'question': question, 'status': status, 'body': value, 'trace': traces[-1] if traces else None,
                        'elapsed_ms': round((time.perf_counter()-started)*1000, 2), 'db_review_inputs': expectation,
                        'judgment': 'pending manual DB-relative review'})
                    save_result(result_path, result)
                    print(key, status, flush=True)
    finally:
        server.should_exit = True
        worker.join(timeout=10)
        result['server_stopped'] = not worker.is_alive()
        result['source_databases_unchanged'] = all(digest(Path(path)) == value for path, value in dependencies.items() if path.endswith('.db'))
        result['coverage'] = {'wordings_n': len({c['question'].split(': ', 1)[-1] for c in result['cases']}),
            'scoped_questions_n': len({(c['profile'], c['question']) for c in result['cases']}),
            'categories_n': len({c['category'] for c in result['cases']}), 'http_requests_n': len(result['cases'])}
        save_result(result_path, result)
    print('Cases:', len(result['cases']), 'profiles:', len(profiles), flush=True)


if __name__ == '__main__':
    main()
