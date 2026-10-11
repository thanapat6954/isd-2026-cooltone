"""Targeted in-place repair from production page approvals, never evaluation labels."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import open_readonly


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(db):
    result = {}
    for table, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        if table == 'plan_metadata_review':
            continue
        result[table] = [list(r) for r in db.execute(f'SELECT * FROM "{table}" ORDER BY rowid')]
    return result


def patch(db, approvals, profile, approval_hash):
    db.row_factory = sqlite3.Row
    identity = db.execute('SELECT program_id,curriculum_version,source_file,plan FROM program').fetchall()
    if len(identity) != 1 or tuple(identity[0]) != ('IT-'+profile.removeprefix('it-'),2565,'IT.pdf',profile.removeprefix('it-')):
        raise ValueError('Wrong curriculum/version/plan identity')
    changes = []
    db.execute('CREATE TABLE IF NOT EXISTS plan_metadata_review (approval_sha256 TEXT,row_id INTEGER,field TEXT,before_value TEXT,after_value TEXT,pdf_page INTEGER,printed_page INTEGER,PRIMARY KEY(approval_sha256,row_id,field))')
    for term in approvals['profiles'][profile]:
        if term['status'] != 'visually_verified' or term['source_file'] != 'IT.pdf':
            raise ValueError('Missing independent production approval')
        rows = [dict(r) for r in db.execute('SELECT * FROM plan_item WHERE year=? AND semester=? ORDER BY id',(term['year'],term['semester']))]
        if len(rows) != term['row_count'] or sum(r['credits'] for r in rows) != term['credits']:
            raise ValueError('Row count/credits disagree; metadata-only repair refused')
        remaining = {r['id']: r for r in rows}
        assignments = []
        # Exact concrete codes and recognizable patterns retain their own rows.
        for source in term['rows']:
            code = source['code'].upper()
            candidates = [r for r in remaining.values() if r['code'].upper() == code]
            if not candidates and 'X' in code:
                candidates = [r for r in remaining.values() if code in r['code'].upper()]
            if not candidates and code == 'XXXXXXXX':
                candidates = [r for r in remaining.values() if r['code'].startswith('ELEC-SLOT') and r['category'] == 'หมวดวิชาเลือกเสรี']
            if candidates:
                row = candidates[0]
                remaining.pop(row['id'])
                assignments.append((source,row))
            else:
                assignments.append((source,None))
        # Recovered rows have no course identity; replace that missing identity
        # only using the residual rows in the independently reviewed table.
        for source,row in assignments:
            if row is None:
                candidates = [r for r in remaining.values() if r['code'].startswith('ELEC-RECOVERED-')]
                if not candidates:
                    raise ValueError('Cannot safely match approved row')
                row = candidates[0]
                remaining.pop(row['id'])
            if row['credits'] != int(source['credits'].split('(')[0]):
                raise ValueError('Repair would change counted credits')
            placeholder = bool(re.search('[xX]',source['code']))
            updates = {'name_th':source['name_th'],'name_en':source['name_en'],
                       'credits_raw':source['credits'],'raw_code':source['code'] if placeholder else None,
                       'is_placeholder':int(placeholder),'code_pattern':source['code'].upper() if placeholder else None,
                       'source_file':'IT.pdf','page_number':source.get('page_number',term['pdf_page']),
                       'printed_page_number':source.get('printed_page_number',term['printed_page'])}
            if not placeholder and row['code'] != source['code']:
                if not row['code'].startswith('ELEC-RECOVERED-') or not db.execute('SELECT 1 FROM course WHERE code=?',(source['code'],)).fetchone():
                    raise ValueError('Concrete catalog evidence missing; no invented insertion')
                updates['code'] = source['code']
            if placeholder:
                kind = 'free' if source['code'].upper()=='XXXXXXXX' else ('general' if source['code'].startswith('9064') else 'major')
                updates.update(elective_type={'free':'free_elective','general':'general_education','major':'major_elective'}[kind],category={'free':'หมวดวิชาเลือกเสรี','general':'หมวดวิชาศึกษาทั่วไป','major':'หมวดวิชาเฉพาะ'}[kind],ctype='เลือก')
            else:
                updates['elective_type'] = None
                if row['code'].startswith('ELEC-RECOVERED-'):
                    updates.update(category='หมวดวิชาศึกษาทั่วไป',ctype='บังคับ')
            if row['code'].startswith('ELEC-RECOVERED-'):
                updates['note']='แถวที่ยืนยันจากภาพตารางต้นฉบับ'
            for field,value in updates.items():
                if row[field] == value:
                    continue
                db.execute('INSERT OR IGNORE INTO plan_metadata_review VALUES (?,?,?,?,?,?,?)',(approval_hash,row['id'],field,json.dumps(row[field],ensure_ascii=False),json.dumps(value,ensure_ascii=False),updates['page_number'],updates['printed_page_number']))
                db.execute(f'UPDATE plan_item SET {field}=? WHERE id=?',(value,row['id']))
                changes.append({'table':'plan_item','row_id':row['id'],'field':field,'before':row[field],'after':value,'pdf_page':updates['page_number'],'printed_page':updates['printed_page_number']})
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='plan_item_credit_option'").fetchone():
                for index,match in enumerate(re.finditer(r'(\d+)\((\d+)-(\d+)-(\d+)\)',source['credits']),1):
                    option=(row['id'],index,*map(int,match.groups()),match[0])
                    existing=db.execute('SELECT * FROM plan_item_credit_option WHERE plan_item_id=? AND alternative_index=?',(row['id'],index)).fetchone()
                    if existing and tuple(existing)!=option:
                        raise ValueError('Conflicting existing credit option; separate review required')
                    if not existing:
                        db.execute('INSERT INTO plan_item_credit_option VALUES (?,?,?,?,?,?,?)',option)
                        changes.append({'table':'plan_item_credit_option','row_id':row['id'],'alternative_index':index,'before':None,'after':list(option)})
            if not placeholder:
                for field in ('name_th','name_en'):
                    existing=db.execute(f'SELECT {field} FROM course WHERE code=?',(source['code'],)).fetchone()[0]
                    if existing!=source[field]:
                        db.execute(f'UPDATE course SET {field}=? WHERE code=?',(source[field],source['code']))
                        changes.append({'table':'course','code':source['code'],'field':field,'before':existing,'after':source[field]})
        if remaining:
            raise ValueError('Unmatched existing rows')
    return changes


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--app-root',type=Path,required=True)
    p.add_argument('--reviews',type=Path,default=ROOT/'data/source_reviews/IT-2565-plan-corrections.json')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    approval=json.loads(a.reviews.read_text(encoding='utf-8'))
    if sha(a.app_root/'data/input/IT.pdf')!=approval['source_sha256']:
        raise ValueError('Source hash changed')
    result={'purpose':'targeted reviewed metadata; no evaluation input','applied':a.apply,'databases':[]}
    for profile in ('it-coop','it-no-coop'):
        path=a.app_root/'work'/('lab8b_'+profile.replace('-','_'))/'curriculum.db'
        backup=a.output/(profile+'-before.db'); stage=a.output/(profile+'-stage.db')
        with closing(open_readonly(path)) as original:
            for target in (backup,stage):
                with closing(sqlite3.connect(target)) as dest:original.backup(dest)
        with closing(sqlite3.connect(stage)) as db,db:
            before=snapshot(db);changes=patch(db,approval,profile,sha(a.reviews));after=snapshot(db)
            if patch(db,approval,profile,sha(a.reviews)):raise ValueError('Not idempotent')
            touched={c['row_id'] for c in changes if c['table'] in ('plan_item','plan_item_credit_option')}
            codes={c['code'] for c in changes if c['table']=='course'}
            for table,old in before.items():
                if table in ('plan_item','plan_item_credit_option'):
                    old=[r for r in old if r[0] not in touched]; new=[r for r in after[table] if r[0] not in touched]
                elif table=='course':
                    old=[r for r in old if r[0] not in codes];new=[r for r in after[table] if r[0] not in codes]
                else:new=after[table]
                if old!=new:raise ValueError('Unaffected data changed: '+table)
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Integrity failure')
        if a.apply:
            # Apply the same bounded transaction, not a wholesale DB replacement.
            with closing(sqlite3.connect(path)) as db,db:
                if snapshot(db)!=before:raise ValueError('Working database changed after backup')
                if patch(db,approval,profile,sha(a.reviews))!=changes:raise ValueError('Staged/live patch differs')
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Live integrity failure')
        result['databases'].append({'profile':profile,'backup':str(backup),'backup_sha256':sha(backup),'changes':changes,'integrity':'ok','idempotent':True,'unaffected_rows_unchanged':True})
        (a.output/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'profiles':len(result['databases']),'changes':sum(len(d['changes']) for d in result['databases']),'applied':a.apply}))


if __name__=='__main__':main()
