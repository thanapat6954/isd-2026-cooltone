"""Verify L3 DB-set calculations, not independent full-book curriculum differences."""
import argparse
import json
from pathlib import Path
import re
import sys
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    registry = DatabaseRegistry(a.app_root)
    result = {'scope': 'L3 mechanical comparison of imported DB plan-course sets; book-wide completeness and independent source accuracy remain n/a', 'cases': []}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    for program in ['DSBA', 'IT', 'BIT']:
        for plan in ['coop', 'no-coop']:
            question = f"หลักสูตร {program} แผน{'สหกิจ' if plan=='coop' else 'ไม่เข้าร่วมสหกิจ'} วิชาใดมีในหลักสูตรเดิม แต่ไม่มีในหลักสูตรฉบับปรับปรุง"
            started = time.perf_counter()
            response = requests.post('http://127.0.0.1:8000/api/ask', json={'question': question}, timeout=90)
            body = response.json()
            expected, sources = {}, {}
            for query in body.get('queries', []):
                db = registry.find_path(Path(query['database_path']))
                if not db or db.curriculum_version not in [2560, 2565] or db.plan != plan:
                    raise ValueError('Cross-version/profile contamination')
                c = open_readonly(db.path)
                try:
                    rows = [dict(r) for r in c.execute(query['sql'])]
                finally:
                    c.close()
                expected[db.curriculum_version] = {str(r['code']) for r in rows}
                sources[db.curriculum_version] = sorted({r.get('source_file') for r in rows if r.get('source_file')})
            difference = sorted(expected.get(2560, set()) - expected.get(2565, set()))
            frontend = requests.post('http://127.0.0.1:8000/ask', json={'curriculum': program, 'version': 'all versions', 'question': question}, timeout=90)
            ui = frontend.json()
            codes_in_answer = set(re.findall(r'(?<!\d)\d{8}(?!\d)', body.get('answer', '')))
            ordinary = {code for code in difference if re.fullmatch(r'\d{8}', code)}
            placeholders = [code for code in difference if not re.fullmatch(r'\d{8}', code)]
            passed = (response.status_code == frontend.status_code == 200 and set(expected) == {2560, 2565} and
                      codes_in_answer == ordinary and body.get('answer') == ui.get('answer') and bool(ui.get('sources')))
            result['cases'].append({'profile': program + '-' + plan, 'question': question,
                                    'expected_db_difference': difference, 'placeholder_differences_need_review': placeholders,
                                    'source_files': sources, 'response': body, 'frontend_response': ui,
                                    'passed': passed, 'elapsed_ms': round((time.perf_counter()-started)*1000,2)})
            a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    result['summary'] = {'passed': sum(c['passed'] for c in result['cases']), 'n': len(result['cases']),
                         'independent_book_accuracy': 'n/a'}
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(result['summary'])
    return int(not all(c['passed'] for c in result['cases']))


if __name__ == '__main__':
    raise SystemExit(main())
