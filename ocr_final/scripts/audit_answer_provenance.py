"""Read-only live-API provenance probes; not an answer-accuracy evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
from lab10_fastapi.curriculum_app.query_planner import QueryPlan


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    app = args.app_root.resolve()
    registry = DatabaseRegistry(app)
    files = [d.path for d in registry.active_catalogs]
    files += list((app / 'lab10_fastapi/curriculum_app').glob('*.py'))
    files += [app / 'frontend/app.js', app / 'data/ground_truth/study_plan_relationships.json']
    before = {str(p): sha(p) for p in files}
    result = {'scope': 'Live API versus read-only replay of returned SQL; no source-book accuracy claim',
              'dependencies_before': before, 'cases': []}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    save()
    for db in registry.active_catalogs:
        if db.schema_family == 'legacy-course-catalog':
            question = 'legacy วิชา 06066302 มีกี่หน่วยกิต'
        else:
            question = f'{db.curriculum_name} ปี 3 ภาคการศึกษาที่ 1 มีรายวิชาอะไรบ้าง'
        response = requests.post('http://127.0.0.1:8000/api/ask', json={'question': question}, timeout=45)
        body = response.json()
        case = {'profile': db.curriculum_name, 'question': question, 'status': response.status_code,
                'body': body, 'replays': [], 'changes': [], 'unmatched_rows': []}
        originals = []
        for query in body.get('queries', []):
            path = Path(query['database_path']).resolve()
            if registry.find_path(path) is None:
                raise RuntimeError('Returned query points outside the discovered database inventory')
            sql = query['sql']
            if not sql.strip().casefold().startswith(('select ', 'with ')):
                raise RuntimeError('Refusing non-query SQL replay')
            connection = open_readonly(path)
            try:
                rows = [dict(row) for row in connection.execute(sql).fetchall()]
            finally:
                connection.close()
            case['replays'].append({'database_path': str(path), 'sql': sql, 'rows': rows})
            originals.extend((str(path), row) for row in rows)
        for row in body.get('rows', []):
            path = str(Path(row['_source']['database_path']).resolve())
            candidates = [raw for p, raw in originals if p == path
                          and all(raw.get(k) == row.get(k) for k in ('code', 'year', 'semester'))]
            if not candidates:
                case['unmatched_rows'].append(row.get('code'))
                continue
            raw = min(candidates, key=lambda r: sum(r.get(k) != row.get(k) for k in r))
            for field in sorted(set(raw) | {k for k in row if not k.startswith('_')}):
                if field not in raw or raw.get(field) != row.get(field):
                    case['changes'].append({'code': row.get('code'), 'field': field,
                                            'present_in_sql_result': field in raw,
                                            'sql_value': raw.get(field), 'returned_value': row.get(field)})
        result['cases'].append(case)
        save()
    payload = {'curriculum': 'IT', 'version': 'latest',
               'question': 'ปี 3 ภาคการศึกษาที่ 1 มีรายวิชาอะไรบ้าง แผนสหกิจศึกษา'}
    frontend = requests.post('http://127.0.0.1:8000/ask', json=payload, timeout=45)
    result['frontend_probe'] = {'request': payload, 'status': frontend.status_code,
                                'body': frontend.json()}
    # Synthetic guard probe, never sent to the server or shown as a course fact.
    marker = 'SYNTHETIC_UNSUPPORTED_FACT_999'
    rows = [{'credits': 3, '_source': {'curriculum_name': 'synthetic-single-profile'}}]
    returned = QwenTextToSQL._ground_answer(QueryPlan('unknown'), rows, marker)
    result['unknown_guard_probe'] = {'synthetic_only': True, 'rows': rows,
                                     'model_text': marker, 'returned_text': returned,
                                     'unsupported_text_rejected': returned != marker}
    result['dependencies_after'] = {str(p): sha(p) for p in files}
    result['unchanged'] = before == result['dependencies_after']
    result['live_repo_product_equal'] = {
        str(p.relative_to(app)): sha(ROOT / p.relative_to(app)) == sha(p)
        for p in files if p.suffix != '.db' and p.relative_to(app).parts[0] not in {'work'}
        and (ROOT / p.relative_to(app)).is_file()
    }
    result['summary'] = {'profiles': len(result['cases']),
                         'http_200': sum(c['status'] == 200 for c in result['cases']),
                         'profiles_with_non_sql_values': [c['profile'] for c in result['cases'] if c['changes']],
                         'changed_or_added_field_count': sum(len(c['changes']) for c in result['cases']),
                         'unmatched_rows': sum(len(c['unmatched_rows']) for c in result['cases']),
                         'tested_rows_and_guard_pass': not any(c['changes'] or c['unmatched_rows'] or c['status']!=200 for c in result['cases']) and returned != marker}
    save()
    print(json.dumps(result['summary'], ensure_ascii=False))
    print(f"Dependencies unchanged: {result['unchanged']}; synthetic unsupported text rejected: {returned != marker}")
    return 1 if result['summary']['profiles_with_non_sql_values'] or returned == marker else 0


if __name__ == '__main__':
    raise SystemExit(main())
