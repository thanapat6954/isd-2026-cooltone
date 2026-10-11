"""Validate lossless migration, declared coverage, isolation and real local links."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def validate_migration(app,manifest):
    rows=[]
    for item in manifest['files']:
        target=app/(item['destination'] or item['old_path'])
        backup=Path(manifest['recovery'])/item['old_path']
        original=json.loads(backup.read_text(encoding='utf-8-sig'))
        current=json.loads(target.read_text(encoding='utf-8-sig'))
        match=sha(target)==item['sha256'] and current==original
        if not match:raise ValueError(f'Label changed {target}')
        rows.append({'old_path':item['old_path'],'new_path':target.relative_to(app).as_posix(),'sha256_unchanged':match,
                     'count_before':len(original.get('courses',[])) if isinstance(original,dict) else len(original),
                     'count_after':len(current.get('courses',[])) if isinstance(current,dict) else len(current),
                     'obsolete_path_absent':not (app/item['old_path']).exists()})
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--app-root',type=Path,default=ROOT)
    p.add_argument('--migration',type=Path,help='Local recovery manifest; omit for schema/link-only validation')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();app=a.app_root.resolve()
    migrated=validate_migration(app,json.loads(a.migration.read_text(encoding='utf-8'))) if a.migration else []
    runner=load_module(app/'run_lab8b.py','dataset_runner')
    validator=load_module(ROOT/'scripts/export_reviewed_term_labels.py','dataset_terms')
    profiles=[]
    for key,profile in runner.PROFILES.items():
        program=re.sub(r'-(?:no-)?coop$','',profile['program_id'])
        year=profile['curriculum_version'];plan=profile['target_plan'].replace('_','-')
        folder=app/'data/ground_truth/evaluation'/f'{program}-{year}'
        partial=folder/(plan+'-terms.json')
        gt=Path(profile['gt']) if profile.get('gt') else None
        if gt and not gt.is_file():raise ValueError(f'Broken configured GT: {gt}')
        data=json.loads(gt.read_text(encoding='utf-8')) if gt else {}
        flat_rows=data.get('courses',[])
        exact=Counter(json.dumps(r,ensure_ascii=False,sort_keys=True) for r in flat_rows)
        placements=Counter((str(r.get('code')),str(r.get('year')),str(r.get('semester'))) for r in flat_rows)
        duplicate_review={'identical_row_excess':sum(n-1 for n in exact.values()),
                          'course_placement_key_collisions':sum(n-1 for n in placements.values()),
                          'interpretation':'review candidates only; repeated wildcard slots/alternatives/tracks may be legitimate; never auto-delete'}
        if data.get('program') not in (None,program,'AIT' if program=='AI' else program):raise ValueError('Wrong label program')
        if data.get('plan') and data['plan'].replace('_','-')!=plan:raise ValueError('Wrong label plan')
        terms=json.loads(partial.read_text(encoding='utf-8')) if partial.exists() else {}
        if terms:
            if year == 2560:
                validator.validate(terms)
            else:
                current_validator=load_module(ROOT/'scripts/export_current_page_labels.py','current_terms')
                current_validator.validate({**terms['identity'],'printed_total':terms['printed_total'],'terms':terms['terms']})
            if terms['identity']['program']!=program or terms['identity']['version']!=year or terms['identity']['plan']!=plan:
                raise ValueError('Cross-profile term labels')
        fields_path=folder/'reviewed-fields.json'
        fields=json.loads(fields_path.read_text(encoding='utf-8')) if fields_path.exists() else {}
        if fields:
            if fields['identity']['program']!=program or fields['identity']['version']!=year:raise ValueError('Cross-version fields')
            if len({r['id'] for r in fields['labels']})!=len(fields['labels']):raise ValueError('Duplicate field label')
            for label in fields['labels']:
                evidence=label['evidence']
                if not evidence['pdf_page'] or sha(app/evidence['approval'])!=evidence['approval_sha256']:raise ValueError('Changed/missing approval')
                if evidence['source_file']!=profile['input'].name:raise ValueError('Wrong source PDF')
        qa_path=folder/(plan+'-qa.json')
        qa=json.loads(qa_path.read_text(encoding='utf-8')) if qa_path.exists() else {}
        if qa and qa['identity']!=terms['identity']:raise ValueError('Wrong QA identity')
        profiles.append({'profile':key,'program':program,'curriculum_version':year,'revision':None,'plan':plan,
          'identity_evidence':'run_lab8b.PROFILES + prior rendered cover/term review; filenames not independent proof',
          'source_pdf':profile['input'].name,'configured_pdf_pages':profile['pages'],'flat_labels':gt.relative_to(app).as_posix() if gt else None,
          'flat_row_count':len(data.get('courses',[])) if gt else None,
          'flat_duplicate_review':duplicate_review if gt else None,
          'flat_missing_field_counts':{key:sum(r.get(key) in (None,'') for r in flat_rows) for key in ('name_th','name_en','credits','prerequisite')} if gt else None,
          'reviewed_terms':partial.relative_to(app).as_posix() if terms else None,
          'reviewed_term_count':len(terms.get('terms',[])),
          'reviewed_fields':fields_path.relative_to(app).as_posix() if fields else None,
          'reviewed_field_label_count':len(fields.get('labels',[])),
          'source_reviewed_development_qa':qa_path.relative_to(app).as_posix() if qa else None,
          'source_reviewed_development_qa_n':len(qa['groups'][0]['cases']) if qa else None,
          'verification':'partial rendered-page ledger' if terms else 'existing labels not fully independently verified' if gt else 'missing independent labels',
          'missing':['full independent names/category/prerequisites','graduation conditions','complete source-grounded L1-L4','new untouched held-out'],
          'plan_evidence':'reviewed rendered academic-plan terms' if terms else 'configured plan; full book relationship review remains partial'})
    profiles.append({'profile':'legacy','program':None,'curriculum_version':None,'revision':None,'plan':None,
                     'verification':'identity unresolved; no inferred year or plan','flat_labels':None,'reviewed_term_count':0,
                     'missing':['authoritative document/profile isolation','independent source labels','source-grounded content Q&A']})
    runtime='\n'.join(p.read_text(encoding='utf-8') for p in (app/'lab10_fastapi/curriculum_app').glob('*.py'))
    prohibited=['data/ground_truth/evaluation','versioned_eval_questions.json','qa_gold.json']
    if any(term in runtime for term in prohibited):raise ValueError('Evaluation reference in production runtime')
    links=[]
    index=app/'data/ground_truth/README.md'
    for target in re.findall(r'\]\(([^)]+)\)',index.read_text(encoding='utf-8')):
        if not (index.parent/target).exists():raise ValueError(f'Broken index link {target}')
        links.append(target)
    result={'migration':migrated,'migration_hash_check':'PASS' if a.migration else 'n/a; no local pre-migration manifest',
            'profiles':profiles,'index_links_checked':len(links),
            'runtime_static_evaluation_access_check':'PASS; does not replace runtime counterfactual evidence',
            'deletions':[],'scope':'organization/schema validation; NOT new book verification'}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    (app/'data/ground_truth/catalog.json').write_text(json.dumps({'schema_version':1,'profiles':profiles},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['', '## ความครอบคลุมแยกรายหลักสูตรและแผน', '',
      '| หลักสูตร/ปี | แผน | แหล่งข้อมูล | flat labels | semesters จากภาพที่ตรวจแล้ว | field labels ร่วม | L1–L2 development | สิ่งที่ยังขาด |', '|---|---|---|---|---|---|---|---|']
    for row in profiles:
        gt=row.get('flat_labels');display=f"[{row.get('flat_row_count')} rows]({Path(gt).relative_to('data/ground_truth').as_posix()})" if gt else 'n/a'
        partial=row.get('reviewed_terms');count=f"[{row['reviewed_term_count']}]({Path(partial).relative_to('data/ground_truth').as_posix()})" if partial else 'n/a'
        field_path=row.get('reviewed_fields'); field_count=f"[{row['reviewed_field_label_count']}]({Path(field_path).relative_to('data/ground_truth').as_posix()})" if field_path else 'n/a'
        qa_path=row.get('source_reviewed_development_qa');qa_count=f"[{row['source_reviewed_development_qa_n']}]({Path(qa_path).relative_to('data/ground_truth').as_posix()})" if qa_path else 'n/a'
        lines.append(f"| {row.get('program') or 'legacy'} / {row.get('curriculum_version') or 'ยังไม่ทราบ'} | {row.get('plan') or 'ยังไม่ยืนยัน'} | {row.get('source_pdf') or 'หลายเล่ม ยังไม่แยก identity'} | {display} | {count} | {field_count} | {qa_count} | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |")
    # Replace only this generated table; repeated validation stays deterministic.
    marker='\n## ความครอบคลุมแยกรายหลักสูตรและแผน'
    base=index.read_text(encoding='utf-8').split(marker)[0]
    index.write_text(base+'\n'.join(lines)+'\n',encoding='utf-8')
    final_links=re.findall(r'\]\(([^)]+)\)',index.read_text(encoding='utf-8'))
    for target in final_links:
        if not (index.parent/target).exists():raise ValueError(f'Broken generated link {target}')
    result['index_links_checked']=len(final_links)
    result['index_sha256']=sha(index)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'lossless_files':len(migrated),'profiles':len(profiles),'index_links_checked':result['index_links_checked']}))

if __name__=='__main__':main()
