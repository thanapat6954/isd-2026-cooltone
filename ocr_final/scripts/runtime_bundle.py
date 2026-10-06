"""Portable runtime snapshots, not ground truth. Never overwrite a destination DB."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def within(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise ValueError('Invalid bundle relative path')
    path = (root / relative).resolve()
    if path == root.resolve() or not path.is_relative_to(root.resolve()):
        raise ValueError('Bundle path escapes the destination')
    return path


def snapshot(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents an existing database from being truncated.
    with destination.open('xb'):
        pass
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro', uri=True)) as src:
        src.execute('PRAGMA query_only=ON')
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Snapshot integrity failed: '+str(destination))


def export_bundle(app, output):
    if output.exists():
        raise FileExistsError('Use a new bundle directory; existing artifacts are preserved')
    databases = DatabaseRegistry(app).active_catalogs
    if not databases:
        raise ValueError('No runtime databases found')
    output.mkdir(parents=True)
    result = {'format': 1, 'scope': 'runtime snapshot; partial book review, NOT independent ground truth',
              'databases': [], 'source_pdfs': []}
    for db in databases:
        target = within(output, db.relative_path)
        snapshot(db.path, target)
        result['databases'].append({'path': db.relative_path, 'profile': db.curriculum_name,
                                   'sha256': sha(target), 'bytes': target.stat().st_size,
                                   'integrity': 'ok', 'version': db.curriculum_version, 'plan': db.plan})
    for path in sorted((app/'data/input').glob('*.pdf')):
        result['source_pdfs'].append({'path': 'data/input/'+path.name, 'sha256': sha(path)})
    (output/'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


def restore_bundle(bundle, app):
    manifest = json.loads((bundle/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format') != 1 or not manifest.get('databases'):
        raise ValueError('Unsupported or empty runtime bundle')
    planned = []
    for item in manifest['databases']:
        source, target = within(bundle, item['path']), within(app, item['path'])
        if target.exists():
            raise FileExistsError('Restore never overwrites an existing database: '+str(target))
        if target.name != 'curriculum.db' or sha(source) != item['sha256']:
            raise ValueError('Invalid database name or snapshot hash')
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as connection:
            connection.execute('PRAGMA query_only=ON')
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Invalid snapshot integrity')
        if any(target == prior[1] for prior in planned):
            raise ValueError('Duplicate bundle path')
        planned.append((source, target))
    # Verify every path/hash before writing anything. Source PDFs are separate inputs.
    for source, target in planned:
        snapshot(source, target)
    return {'restored': len(planned), 'source_pdfs_required_separately': manifest.get('source_pdfs', []),
            'scope': manifest.get('scope')}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    ex = sub.add_parser('export')
    ex.add_argument('--app-root', type=Path, default=ROOT)
    ex.add_argument('--output', type=Path, required=True)
    re = sub.add_parser('restore')
    re.add_argument('--bundle', type=Path, required=True)
    re.add_argument('--app-root', type=Path, default=ROOT)
    args = p.parse_args()
    result = export_bundle(args.app_root.resolve(), args.output.resolve()) if args.action == 'export' else restore_bundle(args.bundle.resolve(), args.app_root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
