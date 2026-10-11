"""DB-relative checks for the two repaired categories, not source/gold accuracy."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--english', action='store_true')
    a = p.parse_args()
    raw = json.loads(a.input.read_text(encoding='utf-8'))
    results = []
    for case in raw['cases']:
        body = case['body']
        rows = body.get('rows', (case.get('trace') or {}).get('rows', []))
        issues = []
        queries = body.get('queries') or (case.get('trace') or {}).get('queries') or []
        if not queries:
            issues.append('no query evidence')
        for query in queries:
            path = query['database_path']
            with sqlite3.connect(Path(path).as_uri() + '?mode=ro', uri=True) as db:
                db.execute('PRAGMA query_only=ON')
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master")}
                if 'v_study_plan' not in tables:
                    issues.append('legacy schema lacks verified study-plan evidence')
                    continue
                if case['category'] == 'semester_aggregation':
                    expected = list(db.execute('SELECT semester,credits FROM v_semester_credits WHERE year=2 AND semester IN (1,2) ORDER BY semester'))
                    actual = sorted((r.get('semester'), r.get('credits')) for r in rows if r.get('year') == 2)
                    if actual != expected:
                        issues.append('semester rows/totals differ from selected SQLite')
                    if len(expected) != 2:
                        issues.append('selected DB does not contain both semesters')
                    if 'รายการที่ใช้คำนวณ' not in body.get('answer', ''):
                        issues.append('calculation evidence missing from answer')
                elif case['category'] == 'multi_condition':
                    expected = list(db.execute("SELECT code,name_en FROM v_study_plan WHERE year=2 AND credits>=3 AND (ctype LIKE '%บังคับ%' OR LOWER(ctype) LIKE '%required%')"))
                    actual = rows
                    if {r[0] for r in expected} != {r.get('code') for r in actual}:
                        issues.append('filtered course set differs from selected SQLite')
                    if any(r.get('year') != 2 or (r.get('credits') or 0) < 3 for r in actual):
                        issues.append('year/minimum-credit condition violated')
                    if a.english and any(name and name not in body.get('answer', '') for _, name in expected):
                        issues.append('requested English names omitted')
        if case['status'] != 200:
            issues.append('technical failure')
        if not body.get('answer', '').strip():
            issues.append('empty answer')
        results.append({'id': case['id'], 'profile': case['profile'], 'category': case['category'],
                        'route': case['route'], 'issues': issues, 'passed': not issues})
    out = {'scope': 'exposed development checks against selected SQLite only; not independent book or held-out accuracy',
           'cases': results, 'n': len(results), 'passed': sum(r['passed'] for r in results),
           'issues': dict(Counter(issue for r in results for issue in r['issues']))}
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'cases'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
