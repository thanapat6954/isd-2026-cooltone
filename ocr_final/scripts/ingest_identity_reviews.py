"""Back up and apply explicit visually approved cover identity metadata."""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry,open_readonly


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root',type=Path,default=ROOT)
    parser.add_argument('--reviews',type=Path,default=ROOT/'data/ground_truth/document_identity_reviews.json')
    parser.add_argument('--database',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args = parser.parse_args()
    registry = DatabaseRegistry(args.app_root.resolve())
    changes = []
    for review in json.loads(args.reviews.read_text(encoding='utf-8'))['reviews']:
        if review['review_status'] != 'visually_verified' or not review.get('sha256'):
            raise ValueError('Identity review needs visual approval and a source hash')
        for db in registry.active_programs:
            if args.database and db.path != args.database.resolve():
                continue
            if (db.program_id or '').split('-')[0] != review['program']:
                continue
            with (args.app_root/'data/input'/review['source_file']).open('rb') as handle:
                sha = hashlib.file_digest(handle,'sha256').hexdigest()
            if sha != review['sha256']:
                raise ValueError('Source changed; repeat cover review')
            source = open_readonly(db.path)
            try:
                if source.execute('SELECT source_file FROM program').fetchone()[0] != review['source_file']:
                    raise ValueError('Program source identity differs; cannot override by folder name')
                result = {'database':db.relative_path,'before':db.program,'after_version':review['curriculum_version'],
                    'source_file':review['source_file'],'pdf_page':review['pdf_page'],'source_sha256':sha,'applied':args.apply}
                if args.apply:
                    folder = args.app_root/'work/backups/identity-review'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
                    folder.mkdir(parents=True)
                    backup_path = folder/(db.path.parent.name+'.db')
                    backup = sqlite3.connect(backup_path)
                    try:
                        source.backup(backup)
                        if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                            raise ValueError('Backup integrity failure')
                    finally:
                        backup.close()
                    descriptor,filename = tempfile.mkstemp(prefix='identity-stage-',suffix='.sqlite',dir=db.path.parent)
                    os.close(descriptor)
                    staged = sqlite3.connect(filename)
                    try:
                        source.backup(staged)
                        staged.execute('UPDATE program SET curriculum_version=?,is_latest=?',
                            (review['curriculum_version'],int(review['is_latest'])))
                        staged.commit()
                        if staged.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                            raise ValueError('Staged integrity failure')
                    finally:
                        staged.close()
                    source.close()
                    os.replace(filename,db.path)
                    result['backup'] = backup_path.relative_to(args.app_root).as_posix()
                changes.append(result)
            finally:
                source.close()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'changes':changes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{len(changes)} matched identity reviews; applied={args.apply}; results={args.output}')


if __name__ == '__main__':
    main()
