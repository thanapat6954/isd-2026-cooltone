"""Reuse approved rendered-page observations, never generate labels from SQLite."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(data):
    if data['purpose'] != 'partial_source_evaluation':
        raise ValueError('Wrong purpose')
    identity=data['identity']
    if identity['version'] != 2560 or identity['program'] not in {'DSBA','IT','BIT'} or identity['plan'] not in {'coop','no-coop'}:
        raise ValueError('Unreviewed identity')
    keys=[]
    for term in data['terms']:
        if term['review_status']!='manually_inspected_rendered_image' or not term['pdf_page'] or not term['printed_page'] or not term['source_sha256'] or not term['image_sha256']:
            raise ValueError('Missing independent page evidence')
        if term['source_file'] != data['source_file']:
            raise ValueError('Wrong source version')
        keys.append((term['year'],term['semester']))
        for row in term['expected_options']:
            if not row['code'] or not row['credits_raw']:
                raise ValueError('Missing reviewed row')
    if len(keys)!=len(set(keys)):
        raise ValueError('Duplicate term')
    # Alternatives/tracks must not be summed as independent required courses.
    if sum(t['printed_credits'] for t in data['terms']) != data['printed_total']:
        raise ValueError('Printed total mismatch')

def qa_labels(data):
    """Explicit development cases; expected credits come only from reviewed cells."""
    term=data['terms'][0]
    identity=data['identity']
    cases=[]
    for row in term['expected_options']:
        if not re.fullmatch(r'\d{8}',row['code']):continue
        cases.append({'question':f'วิชา {row["code"]} มีกี่หน่วยกิต','code':row['code'],
                      'credits':int(re.match(r'\d+',row['credits_raw']).group()),'source':data['source_file'],
                      'page':term['pdf_page'],'book_page':term['printed_page'],'level':'L1',
                      'label_evidence':{'image':term['image'],'image_sha256':term['image_sha256'],'source_sha256':term['source_sha256'],'printed_cell':row}})
        if len(cases)==5:break
    if len(cases)<5:raise ValueError('Insufficient directly reviewed course rows')
    cases.append({'question':f'ปี {term["year"]} ภาคการศึกษาที่ {term["semester"]} เรียนกี่หน่วยกิต',
                  'credits':term['printed_credits'],'source':data['source_file'],'page':term['pdf_page'],
                  'book_page':term['printed_page'],'level':'L2',
                  'label_evidence':{'image':term['image'],'image_sha256':term['image_sha256'],'source_sha256':term['source_sha256'],'printed_term_total':term['printed_credits']}})
    return {'schema_version':1,'purpose':'development regression from reused visually reviewed book cells; NOT held-out',
            'identity':identity,'unverified_levels':['L3','L4'],'groups':[{'program':identity['program'],
              'versions':[identity['version']],'plans':[identity['plan']],'cases':cases}]}

def export(ledger_path, app, source_root, evidence_root):
    raw=json.loads(ledger_path.read_text(encoding='utf-8'))
    outputs=[]
    for profile in raw['ledger']:
        program,version,plan=profile['profile'].split('_',2)
        data={'schema_version':1,'purpose':'partial_source_evaluation',
              'identity':{'program':program.upper(),'version':int(version),'revision':None,'plan':plan.replace('_','-')},
              'source_file':profile['source_file'],'printed_total':profile['printed_total'],
              'provenance':{'review_ledger':'docs/results/old2560_book_terms_verified.json','review_ledger_sha256':digest(ledger_path),'method':'reused rendered-page observations; no new visual review; not DB-derived'},
              'verified_fields':['code','credits_raw','year','semester','printed_credits','pdf_page','printed_page'],
              'unverified_fields':['name_th','name_en','category','track membership','prerequisites','graduation requirements','L1-L4 independent Q&A'],
              'terms':profile['terms']}
        validate(data)
        for term in data['terms']:
            if digest(source_root/'data/input'/data['source_file'])!=term['source_sha256']:
                raise ValueError('Source changed; do not reuse review')
            image=Path(term['image'])
            image=image if image.is_absolute() else evidence_root/image
            if digest(image)!=term['image_sha256']:
                raise ValueError('Reviewed image changed')
        dest=app/'data/ground_truth/evaluation'/f'{program.upper()}-{version}'/(plan.replace('_','-')+'-terms.json')
        dest.parent.mkdir(parents=True,exist_ok=True)
        payload=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
        if dest.exists() and dest.read_text(encoding='utf-8')!=payload:
            raise ValueError('Refusing to replace different labels')
        dest.write_text(payload,encoding='utf-8')
        questions=dest.with_name(plan.replace('_','-')+'-qa.json')
        qa_payload=json.dumps(qa_labels(data),ensure_ascii=False,indent=2)+'\n'
        if questions.exists() and questions.read_text(encoding='utf-8')!=qa_payload:
            raise ValueError('Refusing changed development labels')
        questions.write_text(qa_payload,encoding='utf-8')
        outputs.append({'path':dest.relative_to(app).as_posix(),'terms':len(data['terms']),'rows':sum(len(t['expected_options']) for t in data['terms']),'sha256':digest(dest)})
    return outputs

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--app-root',type=Path,default=ROOT)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--evidence-root',type=Path,default=ROOT.parent)
    p.add_argument('--ledger',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    results=export(a.ledger,a.app_root,a.source_root,a.evidence_root)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'profiles':len(results),'terms':sum(r['terms'] for r in results),'rows':sum(r['rows'] for r in results)}))

if __name__=='__main__':main()
