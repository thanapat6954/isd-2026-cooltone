"""Review the existing development sequence/assessment batch against SQLite.

This is DB-relative verification, not independent book accuracy or held-out.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import open_readonly


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8'))
    reviews = []
    for case in data['cases']:
        body, profile = case['body'], case['profile']
        answer = body.get('answer', '')
        entry = {'id': case['id'], 'profile': profile, 'category': case['category'],
                 'route': case['route'], 'status': case['status'], 'answer': answer,
                 'http_is_not_correctness': True, 'issues': []}
        if case['status'] != 200:
            entry['outcome'] = 'technical_failure'
        elif case['category'] == 'unsupported_description':
            if body.get('rows') or 'ไม่มีหลักฐาน' not in answer or profile not in answer:
                entry['outcome'] = 'incorrect_irrelevant'
            else:
                entry['outcome'] = 'justified_partial_gap'
        else:
            # /ask deliberately has no raw rows/SQL in its public contract.
            # Replay its matching /api/ask trace, but judge the actual /ask
            # answer and source presentation separately.
            trace = next(c['body'] for c in data['cases'] if c['profile'] == profile
                         and c['category'] == case['category'] and c['route'] == '/api/ask')
            queries = trace.get('queries', [])
            entry['project_names_in_selected_db'] = []
            entry['stored_edges_in_selected_db'] = []
            for path in sorted({query['database_path'] for query in queries}):
                with closing(open_readonly(Path(path))) as connection:
                    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if 'course' in tables:
                        entry['project_names_in_selected_db'].extend(dict(row) for row in connection.execute(
                            "SELECT code,name_th,source_file,page_number FROM course WHERE name_th LIKE ?", ('%โครงงาน%',)))
                        entry['stored_edges_in_selected_db'].extend(dict(row) for row in connection.execute(
                            "SELECT p.code,p.requires,p.kind,p.source_file,p.page_number FROM prerequisite p "
                            "JOIN course c ON c.code=p.code WHERE c.name_th LIKE ?", ('%โครงงาน%',)))
            edges = [row for row in trace.get('rows', []) if row.get('requires')]
            source_edges = {(row['code'], row['requires'], row['kind']) for row in entry['stored_edges_in_selected_db']}
            if any((row.get('code'), row.get('requires'), row.get('kind')) not in source_edges for row in edges):
                entry['issues'].append('relationship not found in selected SQLite')
            if any(str(row['code']) not in answer or str(row['requires']) not in answer for row in edges):
                entry['issues'].append('retrieved relationship omitted from answer')
            if edges:
                entry['outcome'] = 'clarification' if len({(r['code'], r['requires']) for r in edges}) > 1 else 'substantive_correct'
                if entry['outcome'] == 'clarification' and 'โปรดระบุ' not in answer:
                    entry['issues'].append('multiple candidate pairs not clarified')
            else:
                entry['outcome'] = 'justified_partial_gap'
                # Missing extraction and absent courses are not interchangeable.
                if 'ไม่มีหลักฐาน' not in answer or profile not in answer:
                    entry['issues'].append('gap not explicit or missing selected identity')
            if profile == 'legacy-course-catalog':
                entry['issues'].append('legacy source/version identity still unverified')
            if entry['issues']:
                entry['outcome'] = 'unreviewed'
            entry['citation_scope'] = 'SQLite page metadata; independent book support not re-reviewed in this batch'
        other = next(c for c in data['cases'] if c['profile'] == profile and c['category'] == case['category'] and c['route'] != case['route'])
        entry['counterpart_answer_identical'] = answer == other['body'].get('answer', '')
        reviews.append(entry)
    counts = {}
    for row in reviews:
        key = row['outcome']
        counts[key] = counts.get(key, 0) + 1
    output = {'scope': 'DB-relative development; not final source accuracy', 'input': str(args.input),
              'source_databases_unchanged': data.get('source_databases_unchanged'),
              'counts': counts, 'cases': reviews}
    with args.output.open('w', encoding='utf-8') as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2)
    print(json.dumps(counts))


if __name__ == '__main__':
    main()
