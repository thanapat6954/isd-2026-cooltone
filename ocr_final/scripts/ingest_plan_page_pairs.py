"""Citation-only repair with reviewed source SHA, SQLite backup and staging."""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(connection):
    digest = hashlib.sha256()
    for table, in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        if table == 'plan_page_review':
            continue
        columns = [r[1] for r in connection.execute(f'PRAGMA table_info("{table}")')
                   if not (table == 'plan_item' and r[1] == 'printed_page_number')]
        for row in connection.execute('SELECT '+','.join('"'+c+'"' for c in columns)+f' FROM "{table}" ORDER BY rowid'):
            digest.update(json.dumps([table, list(row)], ensure_ascii=False).encode())
    return digest.hexdigest()


def apply_review(connection, review, review_hash):
    program = connection.execute('SELECT program_id,curriculum_version,source_file FROM program').fetchall()
    if len(program) != 1 or program[0][0].split('-')[0] != review['program'] or tuple(program[0][1:]) != (review['version'], review['source_file']):
        raise ValueError('Review/database identity mismatch')
    before = fingerprint(connection)
    connection.execute('CREATE TABLE IF NOT EXISTS plan_page_review (plan_item_id INTEGER PRIMARY KEY, source_file TEXT, pdf_page INTEGER, printed_page INTEGER, before_page INTEGER, review_sha256 TEXT)')
    changes = []
    for pdf, book in review['pages']:
        rows = connection.execute('SELECT id,printed_page_number FROM plan_item WHERE source_file=? AND page_number=?', (review['source_file'], pdf)).fetchall()
        for item, existing in rows:
            if existing not in (None, book):
                raise ValueError(f'Conflicting reviewed folio at row {item}; manual review required')
            approval = connection.execute('SELECT printed_page,review_sha256 FROM plan_page_review WHERE plan_item_id=?', (item,)).fetchone()
            if approval and tuple(approval) != (book, review_hash):
                raise ValueError('Existing approval changed')
            if existing is None:
                connection.execute('INSERT INTO plan_page_review VALUES (?,?,?,?,?,?)', (item, review['source_file'], pdf, book, existing, review_hash))
                connection.execute('UPDATE plan_item SET printed_page_number=? WHERE id=?', (book, item))
                changes.append({'row_id': item, 'pdf_page': pdf, 'old_book_page': existing, 'book_page': book})
    if fingerprint(connection) != before:
        raise ValueError('Non-citation facts changed')
    return changes


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--output-root', type=Path, required=True, help='New isolated directory, never working work/')
    p.add_argument('--reviews', type=Path, default=ROOT/'data/source_reviews/current_plan_page_pairs.json')
    p.add_argument('--database', type=Path, help='Limit ingestion to this rebuilt database')
    p.add_argument('--deploy', action='store_true', help='After isolated verification; backups retained in output-root')
    a = p.parse_args()
    app, output = a.app_root.resolve(), a.output_root.resolve()
    if output == app or app/'work' == output or (app/'work') in output.parents:
        raise ValueError('Use a separate isolated output directory')
    output.mkdir(parents=True, exist_ok=False)
    raw = json.loads(a.reviews.read_text(encoding='utf-8'))
    if raw['review_status'] != 'visually_verified':
        raise ValueError('Missing visual approval')
    manifest = {'scope': 'citation-only; curriculum facts fingerprint unchanged', 'databases': []}
    for review in raw['reviews']:
        if sha(app/'data/input'/review['source_file']) != review['source_sha256']:
            raise ValueError('Source SHA changed')
        for db in DatabaseRegistry(app).active_programs:
            if a.database and db.path.resolve() != a.database.resolve():
                continue
            if db.curriculum_version != review['version'] or db.program_id.split('-')[0] != review['program']:
                continue
            backup = output/'backups'/f'{db.curriculum_name}.db'
            staged = output/db.relative_path
            backup.parent.mkdir(parents=True, exist_ok=True)
            staged.parent.mkdir(parents=True, exist_ok=True)
            with closing(open_readonly(db.path)) as source:
                for destination in (backup, staged):
                    target = sqlite3.connect(destination)
                    try:
                        source.backup(target)
                        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                            raise ValueError('Invalid backup')
                    finally:
                        target.close()
            target = sqlite3.connect(staged)
            try:
                changes = apply_review(target, review, sha(a.reviews))
                target.commit()
                repeated = apply_review(target, review, sha(a.reviews))
                target.commit()
                if repeated or target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Idempotence/integrity failed')
            finally:
                target.close()
            if a.deploy:
                # Deploy a separate SQLite snapshot, retaining both evidence and backup.
                stage = db.path.with_name(db.path.name+'.'+output.name+'.stage')
                if stage.exists():
                    raise ValueError('Existing stage; investigate before overwriting')
                source = sqlite3.connect(staged)
                target = sqlite3.connect(stage)
                try:
                    source.backup(target)
                finally:
                    source.close()
                    target.close()
                os.replace(stage, db.path)
            manifest['databases'].append({'profile': db.curriculum_name, 'backup': str(backup), 'backup_sha256': sha(backup),
                'staged': str(staged), 'changes': changes, 'deployed': a.deploy, 'idempotent': True})
            (output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'profiles': len(manifest['databases']), 'changed_citations': sum(len(d['changes']) for d in manifest['databases']), 'deployed': a.deploy}))


if __name__ == '__main__':
    main()
