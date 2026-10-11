"""Apply explicit source-approved field changes without replacing SQLite databases."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import open_readonly

ALLOWED = {'study_term': {'note'}, 'course': {'name_th', 'name_en'},
           'plan_item': {'code', 'name_th', 'name_en', 'credits_raw', 'raw_code',
                         'code_pattern', 'is_placeholder', 'elective_type', 'category'}}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def snapshot(db):
    return {table: [list(row) for row in db.execute(f'SELECT * FROM "{table}" ORDER BY rowid')]
            for table, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            if table != 'source_field_repair'}


def patch(db, approval, approval_sha):
    if approval.get('status') != 'visually_verified':
        raise ValueError('Independent source approval is required')
    identities = db.execute('SELECT program_id,curriculum_version,plan,source_file FROM program').fetchall()
    if identities != [tuple(approval[k] for k in ('program_id', 'version', 'plan', 'source_file'))]:
        raise ValueError('Source curriculum/version/plan mismatch')
    before = snapshot(db)
    db.execute('CREATE TABLE IF NOT EXISTS source_field_repair (approval_sha TEXT,table_name TEXT,row_id INTEGER,field TEXT,old_value TEXT,new_value TEXT,pdf_page INTEGER,printed_page INTEGER,PRIMARY KEY(approval_sha,table_name,row_id,field))')
    changes = []
    expected = {table: [row[:] for row in rows] for table, rows in before.items()}
    for item in approval.get('new_courses', []):
        # A missing catalog identity may be established only by its own source row.
        values = item['values']
        required = {'code', 'name_th', 'name_en', 'credits', 'source_file', 'page_number'}
        if set(values) != required or values['source_file'] != approval['source_file']:
            raise ValueError('Only source-approved minimal catalog fields may be inserted')
        if not item.get('evidence') or type(item.get('printed_page')) is not int or item['printed_page'] <= 0:
            raise ValueError('Independent catalog source evidence required')
        if (not isinstance(values['code'], str) or len(values['code']) != 8 or not values['code'].isdigit()
                or not isinstance(values['name_th'], str) or not values['name_th'].strip()
                or type(values['credits']) is not int or not 0 <= values['credits'] <= 12
                or type(values['page_number']) is not int or values['page_number'] <= 0):
            raise ValueError('Invalid approved catalog identity')
        columns = [r[1] for r in db.execute('PRAGMA table_info(course)')]
        existing = db.execute('SELECT * FROM course WHERE code=?', (values['code'],)).fetchone()
        if existing:
            if any(dict(zip(columns, existing))[k] != v for k, v in values.items()):
                raise ValueError('Conflicting existing catalog facts')
            continue
        db.execute('INSERT INTO course('+','.join(values)+') VALUES ('+','.join('?' for _ in values)+')', tuple(values.values()))
        new_row = db.execute('SELECT rowid,* FROM course WHERE code=?', (values['code'],)).fetchone()
        if any(value is not None for column, value in zip(columns, new_row[1:]) if column not in values):
            raise ValueError('Unapproved catalog content introduced by defaults or triggers')
        expected['course'].append(list(new_row[1:]))
        db.execute('INSERT INTO source_field_repair VALUES (?,?,?,?,?,?,?,?)',
                   (approval_sha, 'course', new_row[0], 'insert_identity', 'null', json.dumps(values, ensure_ascii=False), values['page_number'], item['printed_page']))
        changes.append({'table': 'course', 'row_id': new_row[0], 'field': 'insert_identity', 'old': None, 'new': values})
    for item in approval['changes']:
        table = item['table']
        if table not in ALLOWED or not set(item['values']) <= ALLOWED[table] or not item['values']:
            raise ValueError('Unapproved field')
        if set(item['before']) != set(item['values']):
            raise ValueError('Every field requires an exact before value')
        if any(type(item[k]) is not int or item[k] <= 0 for k in ('pdf_page', 'printed_page')):
            raise ValueError('Paired source pages required')
        columns = [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
        rows = db.execute(f'SELECT rowid,* FROM "{table}" WHERE rowid=?', (item['row_id'],)).fetchall()
        if len(rows) != 1:
            raise ValueError('Source-approved row does not exist')
        row = dict(zip(['rowid'] + columns, rows[0]))
        if row.get('source_file') != approval['source_file']:
            raise ValueError('Wrong source document')
        if 'page_number' in row and row['page_number'] != item['pdf_page']:
            raise ValueError('Source page disagrees with target row')
        if 'printed_page_number' in row and row['printed_page_number'] != item['printed_page']:
            raise ValueError('Printed page disagrees with target row')
        for field, value in item['values'].items():
            old = row[field]
            if old == value:
                continue
            if old != item['before'][field]:
                raise ValueError('Conflicting existing edit: ' + field)
            db.execute(f'UPDATE "{table}" SET "{field}"=? WHERE rowid=?', (value, item['row_id']))
            db.execute('INSERT INTO source_field_repair VALUES (?,?,?,?,?,?,?,?)',
                       (approval_sha, table, item['row_id'], field, json.dumps(old, ensure_ascii=False),
                        json.dumps(value, ensure_ascii=False), item['pdf_page'], item['printed_page']))
            changes.append({'table': table, 'row_id': item['row_id'], 'field': field, 'old': old, 'new': value})
            row_index = next(i for i, original in enumerate(before[table]) if original == list(rows[0][1:]))
            expected[table][row_index][columns.index(field)] = value
    if snapshot(db) != expected:
        raise ValueError('Unaffected facts changed')
    if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Integrity failure')
    return changes


def main():
    parser = argparse.ArgumentParser()
    for name in ('app-root', 'database', 'reviews', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    approval = json.loads(args.reviews.read_text(encoding='utf-8'))
    if sha(args.app_root/'data/input'/approval['source_file']) != approval['source_sha256']:
        raise ValueError('Source document changed')
    args.output.mkdir(parents=True, exist_ok=False)
    with closing(open_readonly(args.database)) as original:
        before = snapshot(original)
        for filename in ('before.db', 'stage.db'):
            with closing(sqlite3.connect(args.output/filename)) as target:
                original.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Invalid backup')
    approval_sha = sha(args.reviews)
    with closing(sqlite3.connect(args.output/'stage.db')) as stage, stage:
        changes = patch(stage, approval, approval_sha)
        if patch(stage, approval, approval_sha):
            raise ValueError('Not idempotent')
    if args.apply:
        with closing(sqlite3.connect(args.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if snapshot(db) != before:
                raise ValueError('Database changed after backup')
            if patch(db, approval, approval_sha) != changes or patch(db, approval, approval_sha):
                raise ValueError('Staged/live replay mismatch')
    result = {'database': str(args.database), 'backup': str(args.output/'before.db'),
              'backup_sha256': sha(args.output/'before.db'), 'source_sha256': approval['source_sha256'],
              'approval_sha256': approval_sha, 'applied': args.apply, 'changes': changes,
              'integrity': 'ok', 'idempotent': True, 'unaffected_facts_unchanged': True}
    (args.output/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'changes': len(changes), 'applied': args.apply, 'integrity': 'ok'}))


if __name__ == '__main__':
    main()
