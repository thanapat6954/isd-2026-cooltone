"""Compact, read-only six-profile checkpoint; source coverage is never inferred."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.audit_live_curriculum_dbs import inspect_database
except ModuleNotFoundError:
    from audit_live_curriculum_dbs import inspect_database

PROFILES = tuple(f'{program}_2560_{plan}' for program in ('dsba', 'it', 'bit')
                 for plan in ('coop', 'no_coop'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_plan_labels(db):
    return [dict(row) for row in db.execute(
        "SELECT code,name_th,source_file,page_number FROM v_plan WHERE name_th LIKE '%กลุ่มวิชา%' "
        "OR name_th LIKE '%แขนงวิชา%' OR name_th LIKE '%ภาคการศึกษา%' "
        "OR name_th LIKE '%'||char(10)||'%' OR name_th LIKE '%'||char(13)||'%' OR name_th LIKE '%�%'")]


def capture(app, audit=None):
    result = {'captured_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'six old profiles; no source accuracy inferred from database agreement',
              'profiles': []}
    audited = {row['database']: row for row in (audit or {}).get('datasets', [])}
    for profile in PROFILES:
        path = app / 'work' / f'lab8b_{profile}' / 'curriculum.db'
        if not path.exists():
            result['profiles'].append({'profile': profile, 'missing_database': True})
            continue
        item = inspect_database(path, app)
        item['sha256'] = digest(path)
        with sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            item['integrity'] = db.execute('PRAGMA integrity_check').fetchone()[0]
            item['counts'] = {table: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                              for table in ('program', 'course', 'plan_item', 'prerequisite')}
            item['duplicate_plan_keys'] = [dict(row) for row in db.execute(
                'SELECT program_id,year,semester,code,COUNT(*) AS n FROM plan_item '
                'GROUP BY program_id,year,semester,code HAVING COUNT(*) > 1')]
            item['orphan_prerequisites'] = [dict(row) for row in db.execute(
                'SELECT p.code,p.requires FROM prerequisite p LEFT JOIN course c ON c.code=p.code '
                'LEFT JOIN course r ON r.code=p.requires WHERE c.code IS NULL OR r.code IS NULL')]
            item['missing_names'] = db.execute("SELECT COUNT(*) FROM course WHERE name_th IS NULL OR TRIM(name_th)='' ").fetchone()[0]
            item['plan_missing_names'] = db.execute("SELECT COUNT(*) FROM v_plan WHERE name_th IS NULL OR TRIM(name_th)='' ").fetchone()[0]
            item['plan_readability_candidates'] = inspect_plan_labels(db)
            item['readability_candidates'] = []
            for row in db.execute('SELECT code,name_th,source_file,page_number FROM course'):
                name = row['name_th'] or ''
                flags = [label for label, condition in (
                    ('replacement character', '\ufffd' in name),
                    ('line break', '\n' in name or '\r' in name),
                    ('heading bleed candidate', bool(re.search('กลุ่มวิชา|ภาคการศึกษา|แผนการศึกษา', name))),
                    ('split Thai candidate', bool(re.search(r'[ก-๙] +[ก-๙]', name)))) if condition]
                if flags:
                    item['readability_candidates'].append(dict(row) | {'flags': flags})
        # Full independent semester review is a separate evidence source, not this check.
        item['printed_book_comparison'] = None
        item['audit_findings'] = audited.get(item['database'], {}).get('findings', [])
        item['protected_inputs'] = {str(p.relative_to(app)): digest(p)
            for p in (path.parent / 'lab7b').glob('pred*.json')}
        result['profiles'].append(item)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = capture(args.app_root.resolve(), json.loads(args.audit.read_text(encoding='utf-8')) if args.audit else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for row in result['profiles']:
        if row.get('missing_database'):
            print(row['profile'], 'MISSING')
        else:
            print(row['profile'], row['counts'], 'missing fidelity=', row['required_columns_missing'],
                  'counted credits=', sum(t['counted_credit_sum'] for t in row['terms']),
                  'readability candidates=', len(row['readability_candidates']))
    return int(any(row.get('missing_database') or row.get('required_columns_missing')
                   or row.get('orphan_prerequisites') or row.get('duplicate_plan_keys')
                   or row.get('missing_names') or row.get('plan_missing_names') or row.get('plan_readability_candidates')
                   for row in result['profiles']))


if __name__ == '__main__':
    raise SystemExit(main())
