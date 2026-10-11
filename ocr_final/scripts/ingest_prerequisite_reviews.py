"""Back up and stage source-reviewed prerequisite metadata, preserving unknowns."""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly

EVIDENCE_DDL = '''CREATE TABLE IF NOT EXISTS course_prerequisite_evidence (
 code TEXT PRIMARY KEY, status TEXT NOT NULL CHECK(status IN ('explicit_none','required')),
 source_file TEXT NOT NULL, page_number INTEGER NOT NULL, printed_page_number INTEGER,
 source_sha256 TEXT NOT NULL, review_method TEXT NOT NULL
);'''


def validate_existing(connection, review, codes, available):
    """Source approvals may add evidence, never silently replace conflicting facts."""
    if not codes:
        return
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required = set(review.get('requires', [])) if review['status'] == 'required' else set()
    if not required <= available:
        raise ValueError('Reviewed prerequisite absent from selected curriculum; orphan refused')
    for code in codes:
        existing = {r[0] for r in connection.execute('SELECT requires FROM prerequisite WHERE code=?',(code,))}
        if not existing <= required:
            raise ValueError('Existing prerequisite conflicts with reviewed source; no destructive overwrite')
        if 'course_prerequisite_evidence' in tables:
            row=connection.execute('SELECT status,source_file,page_number,printed_page_number,source_sha256 FROM course_prerequisite_evidence WHERE code=?',(code,)).fetchone()
            expected=(review['status'],review['source_file'],review['page_number'],review['printed_page_number'],review['sha256'])
            if row and tuple(row)!=expected:
                raise ValueError('Conflicting existing source approval; explicit reconciliation required')


def catalog_additions(review, available):
    """Only complete separately approved description fields may create catalog rows."""
    additions = {}
    fields = {'name_th', 'name_en', 'credits', 'lecture_h', 'lab_h', 'self_h'}
    for code, values in review.get('course_fields_by_code', {}).items():
        if code not in review['codes'] or set(values) != fields:
            raise ValueError('Catalog approval must contain exactly the reviewed description fields')
        if not values['name_th'] or not values['name_en'] or any(type(values[k]) is not int or values[k] < 0 for k in ('credits','lecture_h','lab_h','self_h')):
            raise ValueError('Incomplete or invalid catalog source approval')
        if code not in available:
            additions[code] = values
    return additions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, default=ROOT)
    parser.add_argument('--reviews', type=Path, default=ROOT / 'data/source_reviews/shared/prerequisite_source_reviews.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--database', type=Path, help='Restrict the reviewed ingest to one rebuilt database')
    args = parser.parse_args()
    app = args.app_root.resolve()
    documents = json.loads(args.reviews.read_text(encoding='utf-8'))['documents']
    registry = DatabaseRegistry(app)
    updates = []
    for review in documents:
        if review['review_status'] != 'visually_verified' or review['status'] not in ('explicit_none', 'required'):
            raise ValueError('Review must explicitly verify the prerequisite status')
        targets = [db for db in registry.active_programs
            if (not args.database or db.path.resolve() == args.database.resolve())
            and (db.program_id or '').split('-')[0] == review['program']
            and db.curriculum_version == review['curriculum_version']]
        if not targets:
            continue
        if review['status'] == 'required' and not review.get('requires'):
            raise ValueError('Required review must list prerequisite codes')
        with (app / 'data/input' / review['source_file']).open('rb') as handle:
            sha = hashlib.file_digest(handle, 'sha256').hexdigest()
        if sha != review['sha256']:
            raise ValueError('Source changed; repeat visual review before ingestion')
        for db in targets:
            source = open_readonly(db.path)
            try:
                available = {r[0] for r in source.execute('SELECT code FROM course')}
                additions = catalog_additions(review, available)
                available |= additions.keys()
                codes = [code for code in review['codes'] if code in available]
                # A review for a course absent from this plan does not apply to it.
                if not codes:
                    continue
                validate_existing(source,review,codes,available)
                if review['status'] == 'explicit_none' and any(source.execute('SELECT 1 FROM prerequisite WHERE code=?', (code,)).fetchone() for code in codes):
                    raise ValueError('Existing prerequisite conflicts with reviewed NONE; no destructive overwrite allowed')
                result = {'database': db.relative_path, 'source_file': review['source_file'],
                          'pdf_page': review['page_number'], 'printed_page': review['printed_page_number'],
                          'codes': codes, 'applied': args.apply, 'name_changes': [], 'catalog_additions': additions}
                for code, name in review.get('name_th_by_code', {}).items():
                    if code in codes and code not in additions:
                        old = source.execute('SELECT name_th FROM course WHERE code=?',(code,)).fetchone()[0]
                        if old != name:
                            result['name_changes'].append({'code':code,'old':old,'new':name})
                if args.apply:
                    tag = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
                    backup_dir = app / 'work/backups/prerequisite-review' / tag
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    backup_path = backup_dir / (db.path.parent.name + '.db')
                    backup = sqlite3.connect(backup_path)
                    try:
                        source.backup(backup)
                        if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                            raise ValueError('Backup integrity check failed')
                    finally:
                        backup.close()
                    descriptor, filename = tempfile.mkstemp(prefix='prerequisite-stage-', suffix='.sqlite', dir=db.path.parent)
                    os.close(descriptor)
                    staged = sqlite3.connect(filename)
                    try:
                        source.backup(staged)
                        staged.executescript(EVIDENCE_DDL)
                        for code, fields in additions.items():
                            staged.execute('INSERT INTO course(code,name_th,name_en,credits,lecture_h,lab_h,self_h,source_file,page_number) VALUES (?,?,?,?,?,?,?,?,?)',
                                           (code,fields['name_th'],fields['name_en'],fields['credits'],fields['lecture_h'],fields['lab_h'],fields['self_h'],review['source_file'],review['page_number']))
                        for code in codes:
                            if review.get('name_th_by_code', {}).get(code):
                                staged.execute('UPDATE course SET name_th=? WHERE code=?',
                                    (review['name_th_by_code'][code],code))
                                if 'name_th' in {r[1] for r in staged.execute('PRAGMA table_info(plan_item)')}:
                                    staged.execute('UPDATE plan_item SET name_th=? WHERE code=?',
                                        (review['name_th_by_code'][code],code))
                            staged.execute('INSERT OR IGNORE INTO course_prerequisite_evidence VALUES (?,?,?,?,?,?,?)',
                                           (code, review['status'], review['source_file'], review['page_number'],
                                            review['printed_page_number'], sha, 'visually_verified_official_course_description'))
                            for required in review.get('requires', []) if review['status'] == 'required' else []:
                                staged.execute('INSERT OR IGNORE INTO prerequisite VALUES (?,?,?,?,?)',
                                               (code, required, 'pre', review['source_file'], review['page_number']))
                        staged.commit()
                        if staged.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                            raise ValueError('Staged integrity check failed')
                    finally:
                        staged.close()
                    result['backup'] = backup_path.relative_to(app).as_posix()
                    with backup_path.open('rb') as handle:
                        result['backup_sha256'] = hashlib.file_digest(handle, 'sha256').hexdigest()
                    # Close the source handle before replacing on Windows.
                    source.close()
                    os.replace(filename, db.path)
                updates.append(result)
            finally:
                source.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'updates': updates}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(updates)} matched databases; applied={args.apply}; results={args.output}')


if __name__ == '__main__':
    main()
