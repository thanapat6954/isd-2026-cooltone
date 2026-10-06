"""Source-backed reference QA; save actual answers/folios and partial checkpoints."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, default=ROOT)
    p.add_argument('--url', default='http://127.0.0.1:8000')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    gold = ROOT/'tests/qa_graduation_reference.json'
    labels = json.loads(gold.read_text(encoding='utf-8'))
    profiles = DatabaseRegistry(a.app_root).active_programs
    fingerprint = {'gold': hashlib.sha256(gold.read_bytes()).hexdigest(),
                   'databases': {d.curriculum_name: hashlib.sha256(d.path.read_bytes()).hexdigest() for d in profiles},
                   'code': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.app_root/'lab10_fastapi/curriculum_app').glob('*.py')}}
    result = {'scope': labels['purpose'], 'dependencies': fingerprint, 'cases': []}
    if a.resume and a.output.exists():
        result = json.loads(a.output.read_text(encoding='utf-8'))
        if result['dependencies'] != fingerprint:
            raise ValueError('Dependencies changed; use a new output')
    done = {c['id'] for c in result['cases']}
    def save():
        a.output.parent.mkdir(parents=True, exist_ok=True)
        stage = a.output.with_suffix('.partial')
        stage.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        stage.replace(a.output)
    save()
    for db in profiles:
        label = next(l for l in labels['source_cases'] if l['program'] == db.program_id.split('-')[0] and l['version'] == db.curriculum_version)
        for index, question in enumerate(('เกณฑ์การสำเร็จการศึกษามีอะไรบ้าง', 'แผนนี้ครบเงื่อนไขจบไหม', 'อยากจบใน 3.5 ปี ทำได้ไหม')):
            key = db.curriculum_name + '-' + str(index)
            if key in done:
                continue
            context = f"หลักสูตร {label['program']} {label['version']} แผน{'สหกิจศึกษา' if db.plan == 'coop' else 'ไม่สหกิจศึกษา'}: {question}"
            started = time.perf_counter()
            response = requests.post(a.url+'/api/ask', json={'question': context}, timeout=45)
            frontend = requests.post(a.url+'/ask', json={'curriculum': 'AIT' if label['program'] == 'AI' else label['program'],
                                     'version': 'old' if label['version'] == 2560 else 'latest', 'question': context}, timeout=45)
            body, ui = response.json(), frontend.json()
            rows = body.get('rows', [])
            passed = (response.status_code == frontend.status_code == 200 and body.get('selected_curricula') == [db.curriculum_name] and
                      len(rows) == 1 and rows[0].get('regulation_year') == label['regulation_year'] and
                      rows[0].get('source_file') == label['source_file'] and rows[0].get('page_number') == label['page'] and
                      rows[0].get('printed_page_number') == label['book_page'] and
                      body.get('answer') == ui.get('answer') and str(label['regulation_year']) in body.get('answer', '') and
                      'ยังยืนยันไม่ได้' in body.get('answer', '') and (index != 2 or 'ยังรับรองไม่ได้' in body.get('answer', '')) and
                      (not label.get('requires_plo') or 'PLOs' in body.get('answer', '')) and
                      any(s.get('page') == label['page'] and s.get('book_page') == label['book_page'] and s.get('section', '').startswith(label['source_file']) for s in ui.get('sources', [])))
            result['cases'].append({'id': key, 'profile': db.curriculum_name, 'question': context, 'passed': passed,
                                    'api_status': response.status_code, 'frontend_status': frontend.status_code,
                                    'response': body, 'frontend_response': ui, 'paired_request_elapsed_ms': round((time.perf_counter()-started)*1000,2)})
            save()
    result['summary'] = {'passed': sum(c['passed'] for c in result['cases']), 'n': len(result['cases']),
                         'full_graduation_accuracy': 'n/a', 'accelerated_plan_feasibility': 'n/a'}
    save()
    print(result['summary'])
    return 0 if all(c['passed'] for c in result['cases']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
