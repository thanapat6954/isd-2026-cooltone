"""Read-only, resumable handoff inventory; recorded OCR is never independent GT."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_suffix('.partial')
    stage.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    stage.replace(path)


def describe_json(path, root):
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    records = []
    def walk(value):
        if isinstance(value, dict):
            records.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(data)
    counts = {key: sum(key in r for r in records) for key in
              ('code', 'course_code', 'name_th', 'credits', 'prerequisite', 'year', 'semester', 'page_number', 'printed_page_number')}
    return {'path': path.relative_to(root).as_posix(), 'sha256': sha(path), 'field_record_counts': counts,
            'top_level': sorted(data) if isinstance(data, dict) else 'list',
            'versions_recorded': sorted({str(r[k]) for r in records for k in ('version', 'curriculum_version') if k in r}),
            'sources_recorded': sorted({str(r['source_file']) for r in records if r.get('source_file')}),
            'label_status': 'must inspect source review provenance; presence/field counts are NOT verified coverage'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render', nargs='*', default=[], help='Existing PDF path:1-based page; reusable hash-keyed renders')
    args = parser.parse_args()
    root = args.app_root.resolve()
    result = {'scope': 'read-only inventory, not source accuracy', 'sources': [], 'profiles': [], 'ground_truth': [], 'renders': []}
    for path in sorted((root / 'data/input').glob('*.pdf')):
        result['sources'].append({'source_file': path.name, 'sha256': sha(path), 'bytes': path.stat().st_size})
    for db in DatabaseRegistry(root).active_catalogs:
        with open_readonly(db.path) as connection:
            tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            counts = {name: connection.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                      for name in ('course', 'plan_item', 'prerequisite', 'course_prerequisite_evidence', 'study_item', 'courses') if name in tables}
            cols = {r[1] for r in connection.execute('PRAGMA table_info(plan_item)')}
            fidelity = sorted({'raw_code', 'is_placeholder', 'code_pattern', 'elective_type', 'alternative_index', 'printed_page_number'} - cols)
        result['profiles'].append({'profile': db.curriculum_name, 'database': db.relative_path, 'sha256': sha(db.path),
                                  'version': db.curriculum_version, 'plan': db.plan, 'counts': counts,
                                  'missing_fidelity_columns': fidelity, 'source_file': (db.program or {}).get('source_file')})
    for path in sorted((root / 'data/ground_truth').glob('*.json')):
        result['ground_truth'].append(describe_json(path, root))
    for spec in args.render:
        import pymupdf
        path_text, page_text = spec.rsplit(':', 1)
        path, page = Path(path_text).resolve(), int(page_text)
        digest = sha(path)
        image = args.output.parent / 'source_pages' / f'{path.stem}-{digest[:12]}-{page:03}.png'
        image.parent.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(path) as document:
            if not 1 <= page <= len(document):
                raise ValueError(f'Invalid source page {path.name}:{page}')
            if not image.exists():
                document[page-1].get_pixmap(dpi=130, alpha=False).save(image)
        result['renders'].append({'source_file': path.name, 'sha256': digest, 'pdf_page': page,
                                  'image': image.name, 'image_sha256': sha(image), 'status': 'rendered, NOT yet visually reviewed'})
        save(args.output, result)
    save(args.output, result)
    print(json.dumps({'sources': len(result['sources']), 'profiles': len(result['profiles']),
                      'ground_truth_files': len(result['ground_truth']), 'renders': len(result['renders'])}))


if __name__ == '__main__':
    main()
