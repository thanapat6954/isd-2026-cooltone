"""Replay ingest twice and verify rollback on isolated SQLite copies only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly
from scripts.migrate_study_evidence import migrate
from scripts.rollback_db_only import backup, restore_snapshot


def snapshot(path):
    c = open_readonly(path)
    try:
        digest = hashlib.sha256()
        counts = {}
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for table in tables:
            counts[table] = c.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for row in c.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
                digest.update(json.dumps([table, list(row)], ensure_ascii=False).encode())
        return {'sha256_content': digest.hexdigest(), 'row_counts': counts,
                'integrity': c.execute('PRAGMA integrity_check').fetchone()[0]}
    finally:
        c.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--backups', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    ingestion = a.app_root / 'data/ground_truth/study_plan_relationships.json'
    manifest = json.loads(ingestion.read_text(encoding='utf-8'))
    approval = json.loads((ROOT / 'data/ground_truth/study_plan_db_review.json').read_text(encoding='utf-8'))
    original = json.loads(a.backups.read_text(encoding='utf-8'))
    old = {r['profile']: r for r in original['databases']}
    result = {'scope': 'Isolated replay of reviewed ingest on current DBs; not a full OCR/PDF rebuild', 'checks': []}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='db-only-build-') as folder:
        for db in DatabaseRegistry(a.app_root).active_programs:
            target = Path(folder) / (db.curriculum_name + '.db')
            backup(db.path, target)
            before = snapshot(target)
            first = migrate(target, db.program, manifest, approval, hashlib.sha256(ingestion.read_bytes()).hexdigest())
            second = migrate(target, db.program, manifest, approval, hashlib.sha256(ingestion.read_bytes()).hexdigest())
            after = snapshot(target)
            record = {'profile': db.curriculum_name, 'before': before, 'after': after,
                      'first_changes': len(first['changes']), 'second_changes': len(second['changes']),
                      'passed': before == after and not first['changes'] and not second['changes']}
            baseline = Path(old[db.curriculum_name]['backup'])
            recovery = target.with_suffix('.pre-rollback.db')
            restore = restore_snapshot(baseline, target, recovery)
            record['rollback'] = {**restore, 'baseline_content_matches': snapshot(target) == snapshot(baseline),
                                  'recovery_content_matches': snapshot(recovery) == before}
            record['passed'] = record['passed'] and record['rollback']['baseline_content_matches'] and record['rollback']['recovery_content_matches']
            result['checks'].append(record)
            a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    result['summary'] = {'passed': sum(r['passed'] for r in result['checks']), 'n': len(result['checks'])}
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(result['summary'])
    return int(not all(r['passed'] for r in result['checks']))


if __name__ == '__main__':
    raise SystemExit(main())
