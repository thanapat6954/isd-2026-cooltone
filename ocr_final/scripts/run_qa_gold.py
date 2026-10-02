"""Checkpoint real API development gold cases; never feed answers to production."""
import argparse
import hashlib
import json
import math
import statistics
import re
import time
import sys
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry


def cases(dataset):
    for group in dataset['groups']:
        for version in group['versions']:
            for plan in group['plans']:
                identity = '-'.join(str(v) for v in (group['program'], version, plan) if v is not None)
                context = 'legacy' if group['program'] == 'legacy' else f"หลักสูตร {group['program']} {version or 'ฉบับปัจจุบัน'} {'ไม่เข้าร่วมสหกิจ' if plan == 'no-coop' else 'สหกิจ'}"
                for index, case in enumerate(group['cases']):
                    yield f'{identity}-{index+1}', identity, context + ': ' + case['question'], case


def evaluate(body, identity, case):
    rows = body.get('rows', [])
    answer = body.get('answer', '')
    selected = body.get('selected_curricula', [])
    errors = []
    expected_identity = 'legacy-course-catalog' if identity == 'legacy' else identity
    if selected != [expected_identity]:
        errors.append('curriculum isolation')
    applicable = [row for row in rows if not case.get('code') or row.get('code') == case['code']]
    if case.get('uncertain'):
        if rows or expected_identity not in answer or 'จึงยังสรุปไม่ได้' not in answer:
            errors.append('missing evidence must be scoped uncertainty, not absence')
    elif not applicable:
        errors.append('expected course/evidence missing')
    else:
        for field in ('credits', 'name_th'):
            if field in case and not any(row.get(field) == case[field] for row in applicable):
                errors.append(field)
        if case.get('code') and case['code'] not in answer:
            errors.append('answer omits course')
        if 'credits' in case and not re.search(r'(?<!\d)' + str(case['credits']) + r'\s*หน่วยกิต',answer):
            errors.append('answer credits')
        if case.get('name_th') and case['name_th'] not in answer:
            errors.append('answer name')
        if case.get('status') == 'explicit_none' and 'เอกสารระบุว่าไม่มีวิชาบังคับก่อน' not in answer:
            errors.append('answer prerequisite NONE')
        if 'status' in case and not all(row.get('prerequisite_status') == case['status'] for row in applicable):
            errors.append('prerequisite status')
        if case.get('requires') and not any(row.get('requires') == case['requires'] for row in applicable):
            errors.append('required prerequisite')
        if case.get('requires') and case['requires'] not in answer:
            errors.append('answer prerequisite code')
        if case.get('registration_uncertain') and 'ยังสรุปไม่ได้' not in answer:
            errors.append('unsupported registration conclusion')
    citation = None
    if case.get('source'):
        supports = [row for row in applicable if (row.get('source_file') == case['source'] and row.get('page_number'))
                    or (case['source'] in str(row.get('source_files') or '').split(',') and row.get('source_pages'))]
        if case.get('page'):
            supports = [row for row in supports if row.get('page_number') == case['page'] or str(case['page']) in str(row.get('source_pages') or '').split(',')]
        if case.get('book_page'):
            supports = [row for row in supports if row.get('printed_page_number') == case['book_page']]
        citation = bool(supports)
        if not citation:
            errors.append('source/page support')
    return errors, citation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--gold', type=Path, default=ROOT / 'tests/qa_gold.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runs', type=int, default=2)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--app-root',type=Path,default=ROOT)
    args = parser.parse_args()
    dependency = hashlib.sha256(args.gold.read_bytes()).hexdigest()
    registry = DatabaseRegistry(args.app_root.resolve())
    dependencies = {'code':{path.name:hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (args.app_root / 'lab10_fastapi/curriculum_app').glob('*.py')},
        'databases':{item.relative_path:hashlib.sha256(item.path.read_bytes()).hexdigest() for item in registry.databases},
        'url':args.url}
    result = {'gold_sha256': dependency, 'purpose': 'development regression, not held-out accuracy',
              'dependencies':dependencies,
              'run_note': 'First measured request versus repeated request; not a guaranteed cold process/model start.', 'cases': []}
    if args.resume and args.output.exists():
        old = json.loads(args.output.read_text(encoding='utf-8'))
        if old['gold_sha256'] != dependency or old.get('dependencies') != dependencies:
            raise ValueError('Gold/code/database dependency changed: use a new result file')
        result = old
    done = {(entry['id'], entry['run']) for entry in result['cases']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        stage = args.output.with_suffix('.partial')
        stage.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        stage.replace(args.output)
    for run in range(args.runs):
        for key, identity, question, case in cases(json.loads(args.gold.read_text(encoding='utf-8'))):
            if (key, run) in done:
                continue
            start = time.perf_counter()
            body, errors, citation, status = {}, [], None, None
            try:
                response = requests.post(args.url.rstrip('/') + '/api/ask', json={'question': question}, timeout=45)
                status = response.status_code
                body = response.json()
                if status != 200:
                    errors = ['HTTP ' + str(status)]
                else:
                    errors, citation = evaluate(body, identity, case)
            except Exception as error:
                errors = [type(error).__name__ + ': ' + str(error)]
            result['cases'].append({'id': key, 'identity': identity, 'run': run, 'question': question,
                'level': case['level'], 'http_status': status, 'response': body,
                'elapsed_ms': round((time.perf_counter()-start)*1000,2),
                'cache_hit': (body.get('debug') or {}).get('cache_hit', False),
                'passed': not errors, 'citation_supported': citation, 'errors': errors})
            save()
    summary = {}
    slices = defaultdict(list)
    for entry in result['cases']:
        slices[entry['identity']].append(entry)
    for identity, entries in slices.items():
        first = [entry for entry in entries if entry['run'] == 0]
        summary[identity] = {'passed':sum(entry['passed'] for entry in first),'n':len(first)}
    result['summary'] = summary
    result['latency'] = {}
    for run in range(args.runs):
        entries = [entry for entry in result['cases'] if entry['run'] == run and entry['passed'] and entry['level'] != 'missing-evidence']
        values = sorted(entry['elapsed_ms'] for entry in entries)
        result['latency'][str(run)] = {'n':len(values), 'median_ms':round(statistics.median(values),2) if values else None,
            'p95_ms':values[max(0, math.ceil(len(values)*.95)-1)] if values else None,
            'under_5s':sum(value < 5000 for value in values), 'L3_L4_unmeasured':True}
    save()
    print(json.dumps({'summary':summary, 'latency':result['latency'],
                     'failed_ids': sorted({entry['id'] for entry in result['cases'] if not entry['passed']})}, ensure_ascii=False))
    return int(any(not entry['passed'] for entry in result['cases']))


if __name__ == '__main__':
    raise SystemExit(main())
