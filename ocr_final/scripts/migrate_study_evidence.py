"""Ingest reviewed book facts into backed-up/staged SQLite, with correction history."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly
from lab10_fastapi.curriculum_app.study_evidence import DDL


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def migrate(path, program, manifest, approval, input_hash):
    """Caller owns the isolated copy or a verified backup; no original OCR edits."""
    if approval.get('status') != 'visually_verified': raise ValueError('Missing visual approval')
    if approval.get('ingestion_sha256') != input_hash: raise ValueError('Visual review is bound to a different ingestion input')
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    changes = []
    try:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.executescript(DDL)
        columns = {r[1] for r in connection.execute('PRAGMA table_info(plan_item)')}
        for column in ('name_th', 'name_en', 'credits_raw', 'printed_page_number'):
            if column not in columns:
                connection.execute(f'ALTER TABLE plan_item ADD COLUMN {column} ' + ('INTEGER' if column == 'printed_page_number' else 'TEXT'))
        view_cols = [r[1] for r in connection.execute('PRAGMA table_info(v_plan)')]
        fields = []
        for name in view_cols:
            if name in ('name_th', 'name_en'): fields.append(f'COALESCE(p.{name},v.{name}) AS {name}')
            elif name not in ('credits_raw', 'printed_page_number'): fields.append('v.' + name)
        fields += ['p.credits_raw', 'p.printed_page_number']
        connection.execute('CREATE VIEW IF NOT EXISTS v_study_plan AS SELECT ' + ','.join(fields) + ' FROM v_plan v JOIN plan_item p ON p.id=v.id')
        for term in manifest['terms']:
            plan = program['plan']
            if int(program['curriculum_version']) != term['version'] or plan not in term['pages']: continue
            if not str(program['program_id']).split('-')[0] == term['source_file'].split('.')[0].split('-')[0]: continue
            if any(page not in approval['approved_pages'].get(term['source_file'], []) for page in term['pages'][plan]):
                raise ValueError('Term includes an unapproved page')
            identity = (program['program_id'], term['version'], plan, term['year'], term['semester'], term['source_file'])
            total = term.get('printed_total_by_plan', {}).get(plan, term.get('printed_total'))
            connection.execute('INSERT OR IGNORE INTO study_term(program_id,version,plan,year,semester,source_file,source_sha256,printed_total,note,review_method) VALUES (?,?,?,?,?,?,?,?,?,?)',
                               identity + (manifest['sources'][term['source_file']], total, term['note'], manifest['review_method']))
            tid = connection.execute('SELECT id FROM study_term WHERE program_id=? AND version=? AND plan=? AND year=? AND semester=? AND source_file=?', identity).fetchone()[0]
            for pdf, book in term['pages'][plan]:
                connection.execute('INSERT OR IGNORE INTO study_page VALUES (?,?,?)', (tid,pdf,book))
            tracks = manifest['track_sets'][term['track_set']]
            for track in tracks:
                connection.execute('INSERT OR IGNORE INTO study_track VALUES (?,?,?,?)', (tid,track['id'],track['label'],json.dumps(track.get('aliases', []),ensure_ascii=False)))
            rows = [dict(r) for r in connection.execute('SELECT * FROM v_study_plan WHERE year=? AND semester=? AND source_file=?', (term['year'],term['semester'],term['source_file']))]
            codes = term.get('track_codes_by_plan', {}).get(plan) or term.get('track_codes', {})
            expected = set(term.get('shared_codes', [])) | {c for values in codes.values() for c in values}
            if expected - {r['code'] for r in rows}: raise ValueError('Missing reviewed term members: ' + str(expected - {r['code'] for r in rows}))
            for row in rows:
                folio = next((book for pdf,book in term['pages'][plan] if row['page_number']==pdf), None)
                if folio is None: raise ValueError('Term row points to an unreviewed page')
                facts = dict(term.get('row_facts', {}).get(row['code'], {}))
                facts['printed_page_number'] = folio
                pattern = ''
                for field in ('code_pattern','raw_code','code'):
                    match = re.search(r'[0-9xX]{6,8}', str(row.get(field) or ''))
                    if match and re.search('[xX]', match[0]): pattern=match[0].lower(); break
                ordinal = re.search(r'(\d+)\s*$', str(row.get('name_en') or row.get('name_th') or ''))
                if not ordinal: ordinal = re.search(r'(\d+)\s*$', str(row.get('name_th') or ''))
                slot = pattern == term.get('elective_pattern') and ordinal and int(ordinal[1]) in term.get('elective_ordinals', [])
                if slot: facts['credits_raw'] = term['elective_credits_raw']
                general = pattern in term.get('general_patterns', [])
                if general: facts.update(name_th=term['general_name'], credits_raw=term['general_credits_raw'])
                if facts.get('credits_raw') and int(facts['credits_raw'].split('(')[0]) != row['credits']:
                    raise ValueError('Reviewed hours disagree with counted credits')
                for field, value in facts.items():
                    if row.get(field) != value:
                        connection.execute(f'UPDATE plan_item SET {field}=? WHERE id=?', (value,row['id']))
                        connection.execute('INSERT INTO study_correction(term_id,plan_item_id,target,field,old_value,new_value,pdf_page,printed_page,ingestion_sha256,reviewed_on) VALUES (?,?,?,?,?,?,?,?,?,?)',
                                           (tid,row['id'],'plan_item',field,json.dumps(row.get(field),ensure_ascii=False),json.dumps(value,ensure_ascii=False),row['page_number'],folio,input_hash,approval['reviewed_on']))
                        changes.append({'code':row['code'],'field':field,'old':row.get(field),'new':value,'pdf_page':row['page_number'],'book_page':folio})
                # Verified ordinary names must also fix name-only/detail retrieval,
                # not merely mask a wrong catalog row at presentation time.
                if row['code'] in term.get('row_facts', {}):
                    for field in ('name_th','name_en'):
                        if field in facts:
                            old = connection.execute(f'SELECT {field} FROM course WHERE code=?', (row['code'],)).fetchone()
                            if old and old[0] != facts[field]:
                                connection.execute(f'UPDATE course SET {field}=? WHERE code=?', (facts[field],row['code']))
                                connection.execute('INSERT INTO study_correction(term_id,plan_item_id,target,field,old_value,new_value,pdf_page,printed_page,ingestion_sha256,reviewed_on) VALUES (?,?,?,?,?,?,?,?,?,?)',
                                                   (tid,row['id'],'course',field,json.dumps(old[0],ensure_ascii=False),json.dumps(facts[field],ensure_ascii=False),row['page_number'],folio,input_hash,approval['reviewed_on']))
                shared = row['code'] in term.get('shared_codes', [])
                connection.execute('INSERT OR IGNORE INTO study_item VALUES (?,?,?,?,?)', (row['id'],tid,int(shared),f'{pattern}-{ordinal[1]}' if slot else None,'วิชาศึกษาทั่วไป' if general else None))
                for track in tracks:
                    if slot or row['code'] in codes.get(track['id'], []):
                        connection.execute('INSERT OR IGNORE INTO study_member VALUES (?,?,?,?)',
                                           (row['id'],track['id'],track['elective_name']+' '+ordinal[1] if slot else None,None))
        if connection.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Foreign-key violation')
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Integrity failure')
        connection.commit()
        return {'changes': changes, 'term_count':connection.execute('SELECT count(*) FROM study_term').fetchone()[0],
                'history_count':connection.execute('SELECT count(*) FROM study_correction').fetchone()[0], 'integrity':'ok'}
    except Exception:
        connection.rollback(); raise
    finally:
        connection.close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--backups', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--database', type=Path)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--deploy-evidence', type=Path)
    a=p.parse_args(); app=a.app_root.resolve()
    manifest_path=app/'data/ground_truth/study_plan_relationships.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    approval=json.loads((ROOT/'data/ground_truth/study_plan_db_review.json').read_text(encoding='utf-8'))
    for source, expected in manifest['sources'].items():
        if sha(app/'data/input'/source)!=expected: raise ValueError('Changed source '+source)
    baseline=json.loads(a.backups.read_text(encoding='utf-8'))
    backup_map={Path(x['live']).resolve():x for x in baseline['databases']}
    if a.deploy_evidence:
        if not a.apply: raise ValueError('--deploy-evidence requires explicit --apply')
        result=json.loads(a.deploy_evidence.read_text(encoding='utf-8'))
        allowed={db.path for db in DatabaseRegistry(app).active_programs}
        for item in result['databases']:
            live=Path(item['live']).resolve(); stage=Path(item['stage']).resolve()
            if live not in allowed or live not in backup_map or stage.parent.parent != Path(backup_map[live]['backup']).resolve().parent:
                raise ValueError('Deployment targets outside the validated backup batch')
            if sha(live)!=backup_map[live]['live_sha256'] or sha(stage)!=item['stage_sha256']:
                raise ValueError('Live or staged dependency changed')
        for item in result['databases']:
            src=open_readonly(Path(item['stage'])); target=sqlite3.connect(item['live'])
            try:
                src.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Deployment integrity failure')
            finally: target.close();src.close()
            item['deployed_sha256']=sha(Path(item['live']))
            result['stage']='deployed_from_validated_isolated_copies'
            a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Deployed previously validated isolated databases:',len(result['databases']))
        return
    result={'stage':'apply' if a.apply else 'isolated', 'databases':[]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    for db in DatabaseRegistry(app).active_programs:
        if a.database and db.path!=a.database.resolve(): continue
        backup=backup_map.get(db.path)
        if not backup or backup['integrity']!='ok' or sha(Path(backup['backup']))!=backup['backup_sha256']:
            raise ValueError('Missing or changed verified backup: '+str(db.path))
        if sha(db.path)!=backup['live_sha256']: raise ValueError('Live DB changed after baseline: '+str(db.path))
        stage=Path(backup['backup']).parent/'staged'/Path(backup['backup']).name
        stage.parent.mkdir(parents=True,exist_ok=True)
        if stage.exists(): raise ValueError('Choose a fresh backup batch; do not overwrite a stage')
        src=open_readonly(db.path); dest=sqlite3.connect(stage)
        try: src.backup(dest)
        finally: dest.close();src.close()
        evidence=migrate(stage,db.program,manifest,approval,sha(manifest_path))
        result['databases'].append({'profile':db.curriculum_name,'live':str(db.path),'stage':str(stage),'backup':backup['backup'],**evidence,'stage_sha256':sha(stage)})
        a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Validated isolated databases:',len(result['databases']))
    if a.apply:
        # SQLite backup copies the validated stage into the existing live file;
        # no DROP, DELETE, destructive rebuild or active-WAL file replacement.
        for item in result['databases']:
            live=Path(item['live'])
            if sha(live)!=backup_map[live]['live_sha256']: raise ValueError('Live DB changed before deployment')
            src=open_readonly(Path(item['stage'])); target=sqlite3.connect(live)
            try:
                src.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Deployment integrity failure')
            finally: target.close();src.close()
            item['deployed_sha256']=sha(live)
            a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Deployed with recoverable backups:',len(result['databases']))


if __name__=='__main__': main()
