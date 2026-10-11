"""Bind independent partial observations to original-page images, never to DB answers."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.export_current_page_labels import validate_term_credits


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def validate_partial(profile):
    keys=[(term['year'],term['semester']) for term in profile['terms']]
    if len(keys)!=len(set(keys)) or not set(keys)<={(y,s) for y in range(1,5) for s in (1,2)}:
        raise ValueError('Duplicate or invalid semester')
    validate_term_credits(profile['terms'])
    missing={(y,s) for y in range(1,5) for s in (1,2)}-set(keys)
    if not missing and profile.get('printed_total') is not None and sum(term['printed_credits'] for term in profile['terms'])!=profile['printed_total']:
        raise ValueError('Printed program total mismatch')


def page_proofs(data, term, images):
    pairs=dict(data.get('page_pairs',[]))
    pairs[term['pdf_page']]=term['printed_page']
    proofs=[]
    for page in term.get('pdf_pages',[term['pdf_page']]):
        if page not in pairs:
            raise ValueError('Multi-page term lacks an independently reviewed printed folio')
        image=images/f"{Path(data['source_file']).stem}-{data['source_sha256'][:12]}-{page:03}.png"
        proofs.append({'source_file':data['source_file'],'source_sha256':data['source_sha256'],
                       'image':image.name,'image_sha256':digest(image),'pdf_page':page,
                       'printed_page':pairs[page],'review_status':'manually_inspected_rendered_image'})
    return proofs


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--observations',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--images',type=Path,required=True)
    p.add_argument('--output-root',type=Path,required=True)
    a=p.parse_args()
    data=json.loads(a.observations.read_text(encoding='utf-8'))
    if data['review_status']!='visually_verified' or digest(a.source_root/'data/input'/data['source_file'])!=data['source_sha256']:
        raise ValueError('Unreviewed or changed source')
    summary=[]
    for profile in data['profiles']:
        validate_partial(profile)
        terms=[];cases=[]
        for term in profile['terms']:
            proofs=page_proofs(data,term,a.images)
            proof=next(p for p in proofs if p['pdf_page']==term['pdf_page'])
            terms.append({**term,**proof,'page_evidence':proofs,'expected_options':[{'code':row[0],'credits_raw':row[1],
                          **({'name_th':data['reviewed_names'][row[0]][0],'name_en':data['reviewed_names'][row[0]][1]} if row[0] in data.get('reviewed_names',{}) else {}),
                          'alternative_group':row[2] if len(row)==3 else None,'source_row_index':i}
                          for i,row in enumerate(term['rows'])]})
            cases.append({'question':f"ปี {term['year']} ภาคการศึกษาที่ {term['semester']} เรียนกี่หน่วยกิต",
                          'credits':term['printed_credits'],'source':data['source_file'],'page':term['pdf_page'],
                          'book_page':term['printed_page'],'level':'L2','label_evidence':proof})
        identity={k:profile[k] for k in ('program','version','plan')}
        folder=a.output_root/f"{profile['program']}-{profile['version']}";folder.mkdir(parents=True,exist_ok=True)
        payload={**profile,'schema_version':1,'purpose':'partial_source_evaluation','identity':identity,
                 'source_file':data['source_file'],'verified_fields':data['verified_fields'],
                 'unverified_fields':data['unverified_fields'],'observations_sha256':digest(a.observations),'terms':terms}
        for key in ('specialization_groups','structure_evidence','counting_rule'):
            if key in data:payload[key]=data[key]
        qa={'purpose':'development/regression; NOT held-out','groups':[{'program':profile['program'],
            'versions':[profile['version']],'plans':[profile['plan']],'cases':cases}]}
        for suffix,value in [('terms',payload),('qa',qa)]:
            path=folder/f"{profile['plan']}-{suffix}.json"
            text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
            if path.exists() and path.read_text(encoding='utf-8')!=text:
                raise ValueError('Refusing to replace different evaluation labels')
            path.write_text(text,encoding='utf-8')
        summary.append({'identity':identity,'semesters':len(terms),'profile_course_options':sum(len(t['rows']) for t in terms),
                        'unique_non_placeholder_courses':len({r[0] for t in terms for r in t['rows'] if r[0].isdigit()}),
                        'reviewed_pages':len({t['pdf_page'] for t in terms})})
    print(json.dumps(summary))


if __name__=='__main__':main()
