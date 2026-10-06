"""Correct source-reviewed program citations, preserving every curriculum fact."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry
from scripts.ingest_program_requirements import sha, snapshot


def facts(connection):
    """Logical fingerprint; never export entire tables to the report."""
    import hashlib
    digest = hashlib.sha256()
    tables = sorted(r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    if r[0] != 'program_metadata_review' and not r[0].startswith('sqlite_'))
    for table in tables:
        name = table.replace('"', '""')
        columns = [r[1] for r in connection.execute(f'PRAGMA table_info("{name}")')
                   if table != 'program' or r[1] not in ('source_file', 'page_number', 'printed_page_number')]
        fields = ','.join('"'+c.replace('"', '""')+'"' for c in columns)
        rows = sorted(json.dumps(list(r), ensure_ascii=False, default=str)
                      for r in connection.execute(f'SELECT {fields} FROM "{name}"'))
        digest.update(json.dumps([table, columns, rows], ensure_ascii=False).encode())
    return digest.hexdigest()


def apply_review(connection, db, review, input_hash):
    """Reject mismatched facts/identity before schema changes; citation-only UPDATE."""
    connection.row_factory = sqlite3.Row
    rows = connection.execute('SELECT * FROM program').fetchall()
    if len(rows) != 1:
        raise ValueError('Citation review requires exactly one program row')
    row = dict(rows[0])
    suffixes = {'coop': ' (สหกิจศึกษา)', 'no-coop': ' (ไม่เข้าร่วมสหกิจศึกษา)'}
    if (row.get('program_id') != db.program_id or row.get('curriculum_version') != review['version']
        or row.get('plan') not in review['plans'] or row.get('plan') != db.plan
        or row.get('program_id') != review['program']+'-'+db.plan
        or row.get('source_file') != review['source_file']):
        raise ValueError('Source review identity/version/plan mismatch')
    expected_name = review['name_th_base']+suffixes[db.plan]
    if (row.get('name_th') not in (review['name_th_base'], expected_name)
        or any(row.get(k) != review[k] for k in ('total_credits', 'years'))):
        raise ValueError('Existing facts differ from the inspected book; citation-only repair refused')
    if (review.get('review_status') != 'visually_verified' or review.get('scope') != 'citation_only_existing_facts'
        or any(type(review[k]) is not int or review[k] < 1 for k in ('pdf_page', 'book_page'))):
        raise ValueError('Invalid or unverified source review')
    approved = json.dumps(review, ensure_ascii=False, sort_keys=True)
    connection.execute('''CREATE TABLE IF NOT EXISTS program_metadata_review (
      program_id TEXT PRIMARY KEY, before_json TEXT NOT NULL, approved_json TEXT NOT NULL,
      review_input_sha256 TEXT NOT NULL)''')
    old = connection.execute('SELECT * FROM program_metadata_review WHERE program_id=?', (db.program_id,)).fetchone()
    if old:
        if old['approved_json'] != approved or old['review_input_sha256'] != input_hash:
            raise ValueError('Existing approval differs; no automatic overwrite')
        if (row.get('page_number'), row.get('printed_page_number')) != (review['pdf_page'], review['book_page']):
            raise ValueError('Citation changed after approval; re-review required')
        return False
    if 'printed_page_number' not in row:
        connection.execute('ALTER TABLE program ADD COLUMN printed_page_number INTEGER')
    connection.execute('INSERT INTO program_metadata_review VALUES (?,?,?,?)',
                       (db.program_id, json.dumps(row, ensure_ascii=False), approved, input_hash))
    connection.execute('UPDATE program SET page_number=?, printed_page_number=? WHERE program_id=?',
                       (review['pdf_page'], review['book_page'], db.program_id))
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, default=ROOT)
    p.add_argument('--reviews', type=Path)
    p.add_argument('--database', type=Path)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    app = a.app_root.resolve()
    reviews_path = a.reviews or app/'data/source_reviews/program_metadata.json'
    document = json.loads(reviews_path.read_text(encoding='utf-8'))
    pairs = []
    for review in document['reviews']:
        if sha(app/'data/input'/review['source_file']) != review['sha256']:
            raise ValueError('Source changed; repeat visual review')
        pairs.extend((db, review) for db in DatabaseRegistry(app).active_programs
                     if db.program_id == review['program']+'-'+str(db.plan)
                     and db.curriculum_version == review['version'] and db.plan in review['plans']
                     and (not a.database or db.path.resolve() == a.database.resolve()))
    folder = app/'work/backups/program-metadata'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    result = {'scope': 'citation-only; all curriculum facts preserved', 'applied': a.apply,
              'backup_folder': str(folder), 'databases': []}
    def save():
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for db, review in pairs:
        before_hash = sha(db.path)
        backup, stage = folder/(db.curriculum_name+'.db'), folder/'staged'/(db.curriculum_name+'.db')
        snapshot(db.path, backup)
        snapshot(db.path, stage)
        with closing(sqlite3.connect(stage)) as c, c:
            before = facts(c)
            changed = apply_review(c, db, review, sha(reviews_path))
            after = facts(c)
            if before != after or c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Curriculum facts or integrity changed')
        result['databases'].append({'profile': db.curriculum_name, 'live': str(db.path), 'before_sha256': before_hash,
            'backup': str(backup), 'backup_sha256': sha(backup), 'stage': str(stage), 'stage_sha256': sha(stage),
            'facts_sha256': before, 'changed': changed, 'integrity': 'ok', 'source_review': review})
        save()
    if a.apply:
        if any(sha(Path(r['live'])) != r['before_sha256'] or sha(Path(r['backup'])) != r['backup_sha256']
               or sha(Path(r['stage'])) != r['stage_sha256'] for r in result['databases']):
            raise ValueError('Dependencies changed before deployment')
        for r in result['databases']:
            if r['changed']:
                snapshot(Path(r['stage']), Path(r['live']))
            r['after_sha256'] = sha(Path(r['live']))
            r['deployed'] = True
            save()
    save()
    print(json.dumps({'profiles': len(pairs), 'applied': a.apply, 'changed': sum(r['changed'] for r in result['databases'])}))


if __name__ == '__main__':
    main()
