"""Names-only reviewed ingestion with recoverable snapshots; no evaluation input."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry,open_readonly


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def non_name_fingerprint(db):
    digest=hashlib.sha256()
    for table, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        if table=='course_name_review':continue
        columns=[r[1] for r in db.execute(f'PRAGMA table_info("{table}")') if not (table in ('course','plan_item') and r[1] in ('name_th','name_en'))]
        for row in db.execute('SELECT '+','.join('"'+c+'"' for c in columns)+f' FROM "{table}" ORDER BY rowid'):
            digest.update(json.dumps([table,list(row)],ensure_ascii=False).encode())
    return digest.hexdigest()


def apply_names(db, approval, approval_sha):
    if approval.get('review_status')!='visually_verified':raise ValueError('Names require visual source approval')
    identity=db.execute('SELECT program_id,curriculum_version,source_file,plan FROM program').fetchall()
    if len(identity)!=1:raise ValueError('Ambiguous database identity')
    program,version,source,plan=identity[0]
    if (program.split('-')[0],version,source)!=(approval['program'],approval['version'],approval['source_file']):
        raise ValueError('Source identity mismatch')
    before=non_name_fingerprint(db)
    db.execute('CREATE TABLE IF NOT EXISTS course_name_review (code TEXT,field TEXT,table_name TEXT,row_id INTEGER,before_value TEXT,after_value TEXT,source_file TEXT,pdf_page INTEGER,printed_page INTEGER,approval_sha256 TEXT,PRIMARY KEY(code,field,table_name,row_id,approval_sha256))')
    changes=[]
    for review in approval['reviews']:
        if review['plan']!=plan:continue
        if not review.get('names') or not set(review['names'])<={'name_th','name_en'}:raise ValueError('Only reviewed name fields may change')
        if any(not isinstance(v,str) or not v.strip() for v in review['names'].values()):raise ValueError('Empty reviewed name')
        if not all(type(review[k]) is int and review[k]>0 for k in ('pdf_page','printed_page')):raise ValueError('Missing paired source pages')
        if not db.execute('SELECT 1 FROM course WHERE code=?',(review['code'],)).fetchone():raise ValueError('Reviewed course missing; no invented catalog insertion')
        for table in ('course','plan_item'):
            for field,value in review['names'].items():
                for rowid,old in db.execute(f'SELECT rowid,{field} FROM {table} WHERE code=?',(review['code'],)).fetchall():
                    if old==value:continue
                    db.execute('INSERT INTO course_name_review VALUES (?,?,?,?,?,?,?,?,?,?)',(review['code'],field,table,rowid,old,value,source,review['pdf_page'],review['printed_page'],approval_sha))
                    db.execute(f'UPDATE {table} SET {field}=? WHERE rowid=?',(value,rowid))
                    changes.append({'code':review['code'],'field':field,'table':table,'row_id':rowid,'old':old,'new':value,'pdf_page':review['pdf_page'],'printed_page':review['printed_page']})
    if before!=non_name_fingerprint(db):raise ValueError('Non-name course facts/relationships changed')
    return changes


def deploy_names(db, approval, approval_sha, changes, before_fingerprint, original_names):
    """Guard and replay a staged patch inside the caller's transaction."""
    db.execute('BEGIN IMMEDIATE')
    current_names=[tuple(r) for table in ('course','plan_item') for r in db.execute(f'SELECT ?,rowid,name_th,name_en FROM {table} ORDER BY rowid',(table,))]
    if non_name_fingerprint(db)!=before_fingerprint or current_names!=original_names:
        raise ValueError('Working database changed after backup')
    if apply_names(db,approval,approval_sha)!=changes:
        raise ValueError('Staged/live name updates differ')
    if apply_names(db,approval,approval_sha):
        raise ValueError('Live name update not idempotent')
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Live integrity violation')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--app-root',type=Path,required=True);p.add_argument('--reviews',type=Path,required=True)
    p.add_argument('--output-root',type=Path,required=True);p.add_argument('--database',type=Path);p.add_argument('--deploy',action='store_true')
    a=p.parse_args();root=a.app_root.resolve();out=a.output_root.resolve()
    if root==out or root/'work'==out or root/'work' in out.parents:raise ValueError('Use isolated staging outside work')
    out.mkdir(parents=True,exist_ok=False)
    approval=json.loads(a.reviews.read_text(encoding='utf-8'))
    if sha(root/'data/input'/approval['source_file'])!=approval['source_sha256']:raise ValueError('Source hash changed')
    result={'scope':'names only; non-name fingerprint unchanged','databases':[]}
    for info in DatabaseRegistry(root).active_programs:
        if a.database and info.path.resolve()!=a.database.resolve():continue
        if info.program_id.split('-')[0]!=approval['program'] or info.curriculum_version!=approval['version']:continue
        backup=out/'backups'/f'{info.curriculum_name}.db';backup.parent.mkdir(exist_ok=True)
        stage=out/f'{info.curriculum_name}.db'
        with closing(open_readonly(info.path)) as source:
            before_fingerprint=non_name_fingerprint(source)
            original_names=[tuple(r) for table in ('course','plan_item') for r in source.execute(f'SELECT ?,rowid,name_th,name_en FROM {table} ORDER BY rowid',(table,))]
            for dest in (backup,stage):
                with closing(sqlite3.connect(dest)) as target:
                    source.backup(target)
                    if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Invalid snapshot')
        with closing(sqlite3.connect(stage)) as db,db:
            changes=apply_names(db,approval,sha(a.reviews))
            if apply_names(db,approval,sha(a.reviews)):raise ValueError('Name ingestion not idempotent')
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Invalid staged database')
        if a.deploy:
            # Replay only the approved updates under a lock; never replace the DB.
            with closing(sqlite3.connect(info.path)) as db,db:
                deploy_names(db,approval,sha(a.reviews),changes,before_fingerprint,original_names)
        result['databases'].append({'profile':info.curriculum_name,'backup':str(backup),'backup_sha256':sha(backup),'stage':str(stage),'stage_sha256':sha(stage),'changes':changes,'deployed':a.deploy,'integrity':'ok','idempotent':True})
        (out/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'profiles':len(result['databases']),'name_field_changes':sum(len(d['changes']) for d in result['databases']),'deployed':a.deploy}))


if __name__=='__main__':main()
