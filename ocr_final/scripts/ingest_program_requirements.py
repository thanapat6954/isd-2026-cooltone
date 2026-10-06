"""Add immutable source-reviewed requirements via verified backups and staging."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly

DDL = '''CREATE TABLE IF NOT EXISTS program_requirement (
 program_id TEXT NOT NULL, curriculum_version INTEGER NOT NULL, plan TEXT NOT NULL,
 topic TEXT NOT NULL, rule_text TEXT NOT NULL, regulation_year INTEGER NOT NULL,
 source_file TEXT NOT NULL, source_sha256 TEXT NOT NULL, page_number INTEGER NOT NULL,
 printed_page_number INTEGER NOT NULL, section TEXT NOT NULL, review_scope TEXT NOT NULL,
 review_method TEXT NOT NULL, review_input_sha256 TEXT NOT NULL,
 PRIMARY KEY(program_id,curriculum_version,plan,topic));'''


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def snapshot(source_path, target_path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source, target = open_readonly(source_path), sqlite3.connect(target_path)
    try:
        source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Snapshot integrity failure')
    finally:
        target.close()
        source.close()


def insert_review(connection, db, review, method, input_hash):
    """No replacement or UPDATE; conflicting prior approval must be re-reviewed."""
    connection.execute(DDL)
    values = (db.program_id, db.curriculum_version, db.plan, 'graduation_reference',
              review['rule_text'], review['regulation_year'], review['source_file'], review['sha256'],
              review['pdf_page'], review['book_page'], review['section'], review['review_scope'], method, input_hash)
    old = connection.execute('SELECT * FROM program_requirement WHERE program_id=? AND curriculum_version=? AND plan=? AND topic=?', values[:4]).fetchone()
    if old is not None:
        if tuple(old) != values:
            raise ValueError('Existing source review differs; no automatic overwrite')
        return False
    connection.execute('INSERT INTO program_requirement VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', values)
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, default=ROOT)
    p.add_argument('--reviews', type=Path, default=ROOT/'data/source_reviews/graduation_references.json')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--database', type=Path)
    a = p.parse_args()
    app = a.app_root.resolve()
    document = json.loads(a.reviews.read_text(encoding='utf-8'))
    input_hash = sha(a.reviews)
    registry = DatabaseRegistry(app)
    result = {'purpose': 'source-reference ingestion; not complete graduation rules', 'databases': [], 'applied': a.apply}
    def save():
        a.output.parent.mkdir(parents=True, exist_ok=True)
        stage = a.output.with_suffix('.partial')
        stage.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        stage.replace(a.output)
    # Validate every source and mapping before creating any stage or live change.
    matches = []
    for review in document['reviews']:
        source = app/'data/input'/review['source_file']
        if review['review_status'] != 'visually_verified' or review['review_scope'] != 'reference_only' or sha(source) != review['sha256']:
            raise ValueError('Unverified or changed source; repeat page review')
        profiles = [db for db in registry.active_programs
                    if (db.program_id or '').split('-')[0] == review['program'] and db.curriculum_version == review['version']
                    and (not a.database or db.path.resolve() == a.database.resolve())]
        if not profiles:
            if a.database:
                continue
            raise ValueError('Reviewed curriculum has no matching database')
        for db in profiles:
            if (db.program or {}).get('source_file') != review['source_file']:
                raise ValueError('Database/source identity differs')
            matches.append((db, review))
    folder = app/'work/backups/program-requirements'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    for db, review in matches:
        before_hash = sha(db.path)
        backup = folder/(db.curriculum_name+'.db')
        staged = folder/'staged'/(db.curriculum_name+'.db')
        snapshot(db.path, backup)
        snapshot(db.path, staged)
        with closing(sqlite3.connect(staged)) as connection, connection:
            before = {table: connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                      for table in ('course','plan_item','prerequisite')}
            inserted = insert_review(connection, db, review, document['review_method'], input_hash)
            connection.commit()
            after = {table: connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in before}
            if before != after or connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Existing curriculum data or integrity changed')
        result['databases'].append({'profile': db.curriculum_name, 'live': str(db.path), 'before_sha256': before_hash,
                                    'backup': str(backup), 'backup_sha256': sha(backup), 'stage': str(staged),
                                    'stage_sha256': sha(staged), 'preserved_counts': before, 'inserted': inserted,
                                    'source_review': review, 'integrity': 'ok'})
        save()
    if a.apply:
        if any(sha(Path(r['live'])) != r['before_sha256'] or sha(Path(r['backup'])) != r['backup_sha256'] for r in result['databases']):
            raise ValueError('Dependency changed before deployment')
        for row in result['databases']:
            if row['inserted']:
                snapshot(Path(row['stage']), Path(row['live']))
            row['after_sha256'] = sha(Path(row['live']))
            row['deployed'] = True
            save()
    print('Validated', len(result['databases']), 'profiles; applied=', a.apply)


if __name__ == '__main__':
    main()
