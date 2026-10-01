"""Persist B1 verification and non-mutating deployed/backup evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from audit_live_curriculum_dbs import build_baseline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    app = args.app_root.resolve()
    backup_dir = app / 'work/backups/2026-10-01-before-placeholder-migration'
    backups = []
    for path in sorted(backup_dir.glob('*.db')):
        connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        try:
            integrity = connection.execute('PRAGMA integrity_check').fetchone()[0]
        finally:
            connection.close()
        backups.append({'path': path.relative_to(app).as_posix(),
                        'bytes': path.stat().st_size,
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'integrity': integrity})
    env = {**os.environ, 'PYTHONUTF8': '1', 'CURRICULUM_TEST_ROOT': str(app)}
    commands = [
        [sys.executable, '-m', 'unittest', 'discover', '-s', str(root / 'tests'), '-v'],
        [sys.executable, str(root / 'scr/ocr_system/lab8b_curriculum_db.py'), 'selftest'],
    ]
    runs = []
    for command in commands:
        completed = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                   encoding='utf-8', errors='replace', timeout=120)
        runs.append({'command': command, 'exit_code': completed.returncode,
                     'stdout': completed.stdout, 'stderr': completed.stderr})
    conversions = []
    for path in sorted((app / 'work').glob('lab8b_*/curriculum.conversion.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        conversions.append({'path': path.relative_to(app).as_posix(),
                            'fidelity_errors': data.get('fidelity_errors'),
                            'warnings': data.get('warnings'),
                            'plan_items': data.get('plan_items')})
    result = {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
              'backup_evidence': backups,
              'note': 'Current backup hashes prove integrity now, not equality to migrated live DBs.',
              'runs': runs, 'deployed_state': build_baseline(app),
              'last_conversion_reports': conversions}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(backups)} backups; test exit codes: {[r["exit_code"] for r in runs]}; {args.output}')
    return int(any(run['exit_code'] for run in runs)
               or any(item['integrity'] != 'ok' for item in backups))


if __name__ == '__main__':
    raise SystemExit(main())
