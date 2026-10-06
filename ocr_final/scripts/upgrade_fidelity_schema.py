"""Add absent fidelity fields without guessing or changing any stored facts."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly
from scripts.runtime_bundle import sha, snapshot

FIELDS = {'raw_code': 'TEXT', 'is_placeholder': 'INTEGER', 'code_pattern': 'TEXT',
          'elective_type': 'TEXT', 'alternative_index': 'INTEGER', 'printed_page_number': 'INTEGER'}


def upgrade(connection):
    columns = {r[1] for r in connection.execute('PRAGMA table_info(plan_item)')}
    added = []
    for name, kind in FIELDS.items():
        if name not in columns:
            # NULL is unknown. In particular, do not call existing elective slots non-placeholders.
            connection.execute(f'ALTER TABLE plan_item ADD COLUMN {name} {kind}')
            added.append(name)
    return added


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, default=ROOT)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--resume-from', type=Path, help='Recover a saved deployment checkpoint, using a new writable output')
    a = p.parse_args()
    app = a.app_root.resolve()
    folder = app/'work/backups/fidelity-schema'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    result = {'purpose': 'schema only; new NULL fields require separate source-reviewed ingestion', 'databases': [], 'applied': a.apply}
    def save():
        a.output.parent.mkdir(parents=True, exist_ok=True)
        stage = a.output.with_suffix('.partial')
        stage.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        stage.replace(a.output)
    if a.resume_from:
        result = json.loads(a.resume_from.read_text(encoding='utf-8'))
        for row in result['databases']:
            live, backup, staged = Path(row['live']), Path(row['backup']), Path(row['stage'])
            if not live.resolve().is_relative_to(app) or sha(backup) != row['backup_sha256']:
                raise ValueError('Unexpected live path or altered backup')
            expected = row.get('after_sha256') if row.get('deployed') else row['before_sha256']
            if sha(live) != expected:
                raise ValueError('Live database differs from checkpoint')
            with closing(open_readonly(backup)) as original, closing(open_readonly(staged)) as stage:
                old_columns = [r[1] for r in original.execute('PRAGMA table_info(plan_item)')]
                selection = 'SELECT '+','.join('"'+c+'"' for c in old_columns)+' FROM plan_item'
                if [tuple(r) for r in original.execute(selection)] != [tuple(r) for r in stage.execute(selection)]:
                    raise ValueError('Stage differs from backed-up original facts')
                if set(FIELDS) - {r[1] for r in stage.execute('PRAGMA table_info(plan_item)')} or stage.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Stage schema/integrity invalid')
        save()
    for db in ([] if a.resume_from else DatabaseRegistry(app).active_programs):
        with closing(open_readonly(db.path)) as con:
            missing = set(FIELDS) - {r[1] for r in con.execute('PRAGMA table_info(plan_item)')}
            if not missing:
                continue
            before = list(con.execute('SELECT * FROM plan_item'))
            rows = [tuple(row) for row in before]
            columns = [r[1] for r in con.execute('PRAGMA table_info(plan_item)')]
        backup, staged = folder/(db.curriculum_name+'.db'), folder/'staged'/(db.curriculum_name+'.db')
        original_hash = sha(db.path)
        snapshot(db.path, backup)
        snapshot(db.path, staged)
        with closing(sqlite3.connect(staged)) as con, con:
            added = upgrade(con)
            after = con.execute('SELECT '+','.join('"'+name+'"' for name in columns)+' FROM plan_item').fetchall()
            if after != rows or con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Migration changed prior facts or integrity')
        result['databases'].append({'profile': db.curriculum_name, 'live': str(db.path), 'before_sha256': original_hash,
                                    'backup': str(backup), 'backup_sha256': sha(backup), 'stage': str(staged),
                                    'added': added, 'previous_rows_preserved': len(rows), 'integrity': 'ok'})
        save()
    if a.apply:
        if any(sha(Path(row['live'])) != row['before_sha256'] for row in result['databases'] if not row.get('deployed')):
            raise ValueError('Database changed since backup; deployment refused')
        for row in result['databases']:
            if row.get('deployed'):
                continue
            with closing(sqlite3.connect(Path(row['stage']).as_uri()+'?mode=ro', uri=True)) as src:
                with closing(sqlite3.connect(row['live'])) as dst:
                    src.backup(dst)
            row['after_sha256'] = sha(Path(row['live']))
            row['deployed'] = True
            save()
    save()
    print('Schema-only profiles:', len(result['databases']), 'applied:', a.apply)


if __name__ == '__main__':
    main()
