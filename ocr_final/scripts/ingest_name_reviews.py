"""Stage source-reviewed canonical names; never use fuzzy matching to edit data."""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry,open_readonly


def changes(db,reviews):
    result=[]
    columns={r[1] for r in db.execute('PRAGMA table_info(plan_item)')}
    for review in reviews:
        for row in review['rows']:
            old=db.execute('SELECT name_th,name_en FROM course WHERE code=?',(row['code'],)).fetchone()
            labels=[dict(r) for r in db.execute('SELECT name_th,name_en FROM plan_item WHERE code=?',(row['code'],))] if {'name_th','name_en'}<=columns else []
            if old and (any(old[key]!=row[key] for key in ('name_th','name_en')) or any(any(label[key]!=row[key] for key in ('name_th','name_en')) for label in labels)):
                result.append({'code':row['code'],'before':dict(old),'after':row,
                               'plan_labels_before':labels,
                               'source_file':review['source_file'],'pdf_page':review['pdf_page'],
                               'printed_page':review['printed_page']})
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--reviews',type=Path,default=ROOT/'data/ground_truth/old2560_name_reviews.json')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--database',type=Path)
    args=parser.parse_args()
    app=args.app_root.resolve()
    documents=json.loads(args.reviews.read_text(encoding='utf-8'))['documents']
    results=[]
    for info in DatabaseRegistry(app).active_catalogs:
        if args.database and info.path.resolve()!=args.database.resolve(): continue
        reviews=[r for r in documents if r['program']==str(info.program_id or '').removesuffix('-no-coop').removesuffix('-coop') and r['version']==info.curriculum_version]
        if not reviews: continue
        for review in reviews:
            if review['status']!='visually_verified' or hashlib.sha256((app/'data/input'/review['source_file']).read_bytes()).hexdigest()!=review['source_sha256']:
                raise ValueError('Source review hash/status mismatch')
        source=open_readonly(info.path)
        try:
            changed=changes(source,reviews)
            if not changed: continue
            result={'database':info.relative_path,'changes':changed,'applied':args.apply}
            results.append(result)
            if args.apply:
                tag=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
                backup=app/'work/backups/name-review'/tag/(info.path.parent.name+'.db')
                backup.parent.mkdir(parents=True,exist_ok=True)
                with sqlite3.connect(backup) as target:
                    source.backup(target)
                    if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Backup integrity')
                descriptor,filename=tempfile.mkstemp(prefix='names-stage-',suffix='.sqlite',dir=info.path.parent)
                os.close(descriptor)
                target=sqlite3.connect(filename)
                try:
                    source.backup(target)
                    columns={r[1] for r in target.execute('PRAGMA table_info(plan_item)')}
                    for item in changed:
                        row=item['after']
                        target.execute('UPDATE course SET name_th=?,name_en=? WHERE code=?',(row['name_th'],row['name_en'],row['code']))
                        if {'name_th','name_en'}<=columns:
                            target.execute('UPDATE plan_item SET name_th=?,name_en=? WHERE code=?',(row['name_th'],row['name_en'],row['code']))
                    target.commit()
                    if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Staged integrity')
                finally: target.close()
                source.close()
                result.update(backup=str(backup),backup_integrity='ok',backup_sha256=hashlib.sha256(backup.read_bytes()).hexdigest())
                args.output.parent.mkdir(parents=True,exist_ok=True)
                args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                os.replace(filename,info.path)
        finally: source.close()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Databases',len(results),'name changes',sum(len(r['changes']) for r in results),'applied',args.apply)


if __name__=='__main__': main()
