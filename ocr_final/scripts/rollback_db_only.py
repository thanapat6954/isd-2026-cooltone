"""Validate or restore one backed-up catalog; preserve a pre-rollback snapshot."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integrity(path):
    source = open_readonly(path)
    try:
        return source.execute('PRAGMA integrity_check').fetchone()[0]
    finally:
        source.close()


def backup(source_path, target_path):
    source = open_readonly(source_path)
    target = sqlite3.connect(target_path)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    if integrity(target_path) != 'ok':
        raise ValueError('Invalid backup/restore result')


def restore_snapshot(source_path, target_path, recovery_path):
    """Only caller-validated paths; the current DB remains recoverable."""
    if integrity(source_path) != 'ok':
        raise ValueError('Invalid rollback source')
    if recovery_path.exists():
        raise ValueError('Refusing to overwrite a recovery snapshot')
    recovery_path.parent.mkdir(parents=True, exist_ok=True)
    backup(target_path, recovery_path)
    backup(source_path, target_path)
    return {'integrity': integrity(target_path), 'recovery_path': str(recovery_path),
            'recovery_sha256': sha(recovery_path), 'restored_sha256': sha(target_path)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--backups', type=Path, required=True)
    p.add_argument('--profile', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    manifest = json.loads(a.backups.read_text(encoding='utf-8'))
    item = next(x for x in manifest['databases'] if x['profile'] == a.profile)
    source, live = Path(item['backup']).resolve(), Path(item['live']).resolve()
    allowed = {db.path for db in DatabaseRegistry(a.app_root).active_catalogs}
    if live not in allowed or source.parent != Path(manifest['backup_folder']).resolve():
        raise ValueError('Rollback target outside the verified application/backup inventory')
    if sha(source) != item['backup_sha256'] or integrity(source) != 'ok':
        raise ValueError('Backup changed or corrupt')
    result = {'profile': a.profile, 'backup': str(source), 'live': str(live),
              'backup_verified': True, 'mode': 'restore' if a.apply else 'dry_run',
              'note': 'Stop the verified backend before --apply; restore matching code snapshots before restart.'}
    if a.apply:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        recovery = a.app_root / 'work/backups/db-only-rollback' / stamp / (a.profile + '.db')
        result.update(restore_snapshot(source, live, recovery))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(result['mode'], a.profile, 'verified')


if __name__ == '__main__':
    main()
