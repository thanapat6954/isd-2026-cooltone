"""Preserve all active SQLite catalogs and runtime dependency identities."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    app = a.app_root.resolve()
    folder = app / 'work/backups/db-only' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    folder.mkdir(parents=True, exist_ok=False)
    paths = [*sorted((app / 'lab10_fastapi').rglob('*.py')),
             *sorted((app / 'frontend').glob('*')),
             app / 'data/ground_truth/study_plan_relationships.json']
    paths = [x for x in paths if x.is_file()]
    result = {'backup_folder': str(folder), 'files': {}, 'databases': [], 'protected': {}}
    for path in paths:
        rel = path.relative_to(app)
        dest = folder / 'code' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
        result['files'][str(rel)] = digest(path)
    protected = [*sorted((app / 'work').glob('lab8b_*/lab7b/pred_vlm.json')),
                 *sorted((app / 'data/input').glob('*.pdf')),
                 *sorted((ROOT / 'tests').glob('*gold*.json')),
                 ROOT / 'robustness_eval.py']
    for path in protected:
        if path.is_file(): result['protected'][str(path)] = digest(path)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    for db in DatabaseRegistry(app).active_catalogs:
        dest = folder / (db.curriculum_name + '.db')
        source = open_readonly(db.path)
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
            integrity = target.execute('PRAGMA integrity_check').fetchone()[0]
            if integrity != 'ok': raise RuntimeError(f'Invalid backup: {dest}')
        finally:
            target.close(); source.close()
        result['databases'].append({'profile': db.curriculum_name, 'live': str(db.path),
                                   'backup': str(dest), 'integrity': integrity,
                                   'live_sha256': digest(db.path), 'backup_sha256': digest(dest)})
        a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Verified {len(result['databases'])} backups in {folder}")


if __name__ == '__main__': main()
