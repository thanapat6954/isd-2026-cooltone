"""Checkpoint frozen API regressions and real unknown-intent model probes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scr/ocr_system'))
import lab8b_curriculum_db as lab8
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly
from lab10_fastapi.curriculum_app.model_service import FACT_LABELS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def referenced_answer(body):
    """Check each emitted unknown fact against a returned stored-column value."""
    answer = body.get('answer', '')
    if not answer:
        return 'no_answer', False
    if 'ยังยืนยัน' in answer or 'หลักฐานไม่เพียงพอ' in answer or 'หลักฐานจาก SQLite ยังไม่พอ' in answer:
        return 'insufficient_evidence', all(p in answer for p in body.get('selected_curricula', []))
    rows = body.get('rows', [])
    for line in answer.splitlines():
        if ' — ' not in line:
            return 'unsupported_format', False
        profile, fields = line.split(' — ', 1)
        candidates = [r for r in rows if r.get('_source', {}).get('curriculum_name') == profile]
        emitted = fields.split('; ')
        if not candidates or not any(all(
            part in {f'{label}: {r[key]}' for key, label in FACT_LABELS.items()
                     if key in r and r[key] is not None}
            for part in emitted) for r in candidates):
            return 'unsupported_value', False
    return 'stored_values', bool(answer and rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--mode', choices=['frozen', 'unknown'], required=True)
    p.add_argument('--runs', type=int, default=3)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--url', default='http://127.0.0.1:8000')
    a = p.parse_args()
    registry = DatabaseRegistry(a.app_root)
    profiles = registry.active_catalogs
    frozen = {d.curriculum_name: d.path.parent / 'robustness/heldout_questions_v2.json'
              for d in profiles if (d.path.parent / 'robustness/heldout_questions_v2.json').is_file()}
    protected = {str(path): sha(path) for path in frozen.values()}
    dependencies = {'code': {path.name: sha(path) for path in (a.app_root / 'lab10_fastapi/curriculum_app').glob('*.py')},
                    'databases': {d.curriculum_name: sha(d.path) for d in profiles}, 'frozen': protected,
                    'mode': a.mode, 'runs': a.runs, 'url': a.url}
    result = {'dependencies': dependencies, 'cases': [], 'limitations': [
        'Frozen expectations are historical DB-derived regressions, not independent book ground truth.',
        'Repeated cached API calls are not independent temperature=0 generation runs.',
        'Original score_one set scoring is subset-based; this adapter does not change it.',
        'Missing evidence does not establish book-wide absence.',
        'Unknown probes measure grounding, not independent semantic answer accuracy.']}
    if a.resume and a.output.exists():
        result = json.loads(a.output.read_text(encoding='utf-8'))
        if result['dependencies'] != dependencies:
            raise ValueError('Dependencies changed; choose a new output')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save()
    completed = {c['id'] for c in result['cases']}
    for db in profiles:
        if a.mode == 'frozen':
            if db.curriculum_name not in frozen:
                continue
            questions = json.loads(frozen[db.curriculum_name].read_text(encoding='utf-8'))
        else:
            questions = [{'id': 'unknown-summary', 'question': 'ช่วยสรุปข้อมูลที่บันทึกไว้ของหลักสูตรนี้'}]
        for question in questions:
            for run in range(1, (a.runs if a.mode == 'frozen' else 1) + 1):
                identity = f"{db.curriculum_name}/{question['id']}/{run}"
                if identity in completed:
                    continue
                context = 'legacy' if db.schema_family == 'legacy-course-catalog' else db.curriculum_name
                text = context + ': ' + question['question']
                start = time.perf_counter()
                response = requests.post(a.url + '/api/ask', json={'question': text}, timeout=180)
                body = response.json()
                case = {'id': identity, 'profile': db.curriculum_name, 'run': run,
                        'question': text, 'status': response.status_code,
                        'elapsed_ms': round((time.perf_counter() - start) * 1000, 2),
                        'response': body, 'passed': False}
                if a.mode == 'frozen':
                    case['expect'] = question['expect']
                    case['slice'] = question.get('slice')
                    correct, why = lab8.score_one(question['expect'], body)
                    scoped = (question['expect']['type'] != 'none' or
                              (db.curriculum_name in body.get('answer', '') and 'จึงยังสรุปไม่ได้' in body.get('answer', '')))
                    case.update(score_one=correct, why=why, scoped_uncertainty=scoped,
                                passed=response.status_code == 200 and correct and scoped and
                                body.get('selected_curricula') == [db.curriculum_name])
                else:
                    category, grounded = referenced_answer(body) if response.status_code == 200 else ('http_error', False)
                    # Replay the actual SELECT read-only: metadata is excluded from comparison.
                    replay_ok = True
                    for query in body.get('queries', []):
                        if Path(query['database_path']).resolve() != db.path.resolve():
                            replay_ok = False
                            continue
                        connection = open_readonly(db.path)
                        try:
                            raw = [dict(r) for r in connection.execute(query['sql']).fetchall()]
                        finally:
                            connection.close()
                        replay_ok = replay_ok and all({k: v for k, v in r.items() if not k.startswith('_')} in raw
                                                      for r in body.get('rows', []))
                    case.update(category=category, replay_ok=replay_ok,
                                passed=response.status_code == 200 and body.get('intent') == 'unknown' and grounded and replay_ok and
                                body.get('selected_curricula') == [db.curriculum_name])
                result['cases'].append(case)
                save()
                print(identity, response.status_code, case['passed'], flush=True)
    result['protected_unchanged'] = all(sha(Path(path)) == digest for path, digest in protected.items())
    result['dependencies_unchanged'] = dependencies['databases'] == {d.curriculum_name: sha(d.path) for d in profiles}
    result['coverage'] = {d.curriculum_name: sum(c['profile'] == d.curriculum_name for c in result['cases']) for d in profiles}
    result['summary'] = {'passed': sum(c['passed'] for c in result['cases']), 'n': len(result['cases']),
                         'missing_frozen_profiles': [d.curriculum_name for d in profiles if d.curriculum_name not in frozen],
                         'supported_unknown_answers': sum(c.get('category') == 'stored_values' for c in result['cases']),
                         'uncertainty_answers': sum(c.get('category') == 'insufficient_evidence' for c in result['cases'])}
    save()
    print(json.dumps(result['summary'], ensure_ascii=False), flush=True)
    return int(not result['protected_unchanged'] or not result['dependencies_unchanged'] or not all(c['passed'] for c in result['cases']))


if __name__ == '__main__':
    raise SystemExit(main())
