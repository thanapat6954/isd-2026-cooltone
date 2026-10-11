"""Build a NEW partial plan DB from a hash-checked raw OCR job, never gold labels."""
import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import time
from types import SimpleNamespace
import requests
from scripts import extract_manifest_pages as runner

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-job', type=Path, required=True)
    parser.add_argument('--source-pdf', type=Path, required=True)
    parser.add_argument('--metadata-db', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan', choices=('coop', 'no_coop'), required=True)
    args = parser.parse_args()
    state = json.loads((args.raw_job/'manifest-extraction.json').read_text(encoding='utf-8'))
    runner.validate_completed(state, args.raw_job)
    if runner.sha(args.source_pdf) != state['dependencies']['source_sha256']:
        raise ValueError('Source PDF changed')
    args.output.mkdir(parents=True, exist_ok=False)
    lab7 = load('raw_plan_lab7', ROOT/'scr/ocr_system/lab7b_curriculum.py')
    lab8 = load('raw_plan_lab8', ROOT/'scr/ocr_system/lab8b_curriculum_db.py')
    lab7.REQUEST_TIMEOUT = 120
    original_chat = lab7.ollama_chat
    calls = []
    record = {'scope': 'partial raw extraction build, not reviewed ingestion/full reconstruction',
        'input_job_sha256': runner.sha(args.raw_job/'manifest-extraction.json'),
        'source_sha256': runner.sha(args.source_pdf), 'pages': [], 'model_calls': calls,
        'parser_sha256': runner.sha(ROOT/'scr/ocr_system/lab7b_curriculum.py'),
        'builder_sha256': runner.sha(ROOT/'scr/ocr_system/lab8b_curriculum_db.py')}
    def save():
        (args.output/'parse-build.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    def bounded_chat(*positional, **keyword):
        keyword['retries'] = 0
        response = original_chat(*positional, **keyword)
        calls.append({'response': response})
        save()
        return response
    lab7.ollama_chat = bounded_chat
    models = requests.get(lab7.OLLAMA_HOST+'/api/tags', timeout=5).json()['models']
    record['model'] = next(m for m in models if m['name'] == lab7.MODEL_TEXT)
    courses, totals = [], []
    save()
    for row in state['processed']:
        page = row['pdf_page']
        record['running'] = page
        save()
        start = time.perf_counter()
        result = lab7._text_to_json_chunked([(args.raw_job/f'page-{page}.md').read_text(encoding='utf-8')],
            page_numbers=[page], source_file=args.source_pdf.name)
        for course in result.get('courses') or []:
            # Use the manifest's independently reviewed folio, never a guessed offset.
            course['printed_page_number'] = row['printed_book_page']
        path = args.output/f'parsed-{page}.json'
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        courses.extend(result.get('courses') or [])
        totals.extend(result.get('term_totals') or [])
        record['pages'].append({'pdf_page': page, 'seconds': round(time.perf_counter()-start, 2),
            'courses': len(result.get('courses') or []), 'parsed_sha256': runner.sha(path)})
        save()
    before = runner.sha(args.metadata_db)
    with sqlite3.connect(args.metadata_db.resolve().as_uri()+'?mode=ro', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        program = dict(conn.execute('SELECT * FROM program').fetchone())
    if program['plan'] != args.plan.replace('_', '-'):
        raise ValueError('Metadata plan differs from requested build')
    converted, conversion = lab8.convert_lab7b({'courses': courses, 'term_totals': totals},
        program_id=program['program_id'], program_name=program['name_th'],
        total_credits=program['total_credits'], years=program['years'], target_plan=args.plan,
        curriculum_version=program['curriculum_version'], is_latest=bool(program['is_latest']),
        plan_variant=program['plan'])
    converted['program'] = program
    input_path = args.output/'converted-raw.json'
    input_path.write_text(json.dumps(converted, ensure_ascii=False, indent=2), encoding='utf-8')
    lab8.cmd_load(SimpleNamespace(input=str(input_path), database=str(args.output/'partial.db'), replace=False))
    conn = lab8.open_db(args.output/'partial.db', readonly=True)
    record.update(integrity=conn.execute('PRAGMA integrity_check').fetchone()[0],
        verification=lab8.verify_db(conn), conversion=conversion,
        plan_rows=[dict(r) for r in conn.execute('SELECT * FROM plan_item')], running=None,
        metadata_origin='read-only working program metadata only; not freshly extracted program facts',
        working_db_unchanged=runner.sha(args.metadata_db) == before)
    conn.close()
    save()
    print(json.dumps({'pages': record['pages'], 'integrity': record['integrity'],
        'working_db_unchanged': record['working_db_unchanged']}))


if __name__ == '__main__':
    main()
