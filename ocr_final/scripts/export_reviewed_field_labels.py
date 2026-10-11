"""Export partial development labels from prior visual approvals, not DB answers."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def collect(app,source_root):
    grouped=defaultdict(list)
    for file in ('prerequisite_source_reviews.json','old2560_name_reviews.json'):
        path=app/'data/source_reviews/shared'/file
        for document in json.loads(path.read_text(encoding='utf-8'))['documents']:
            if document.get('review_status',document.get('status'))!='visually_verified':
                raise ValueError('Unapproved observation; do not promote to labels')
            source=document['source_file']
            source_hash=document.get('source_sha256',document.get('sha256'))
            if sha(source_root/'data/input'/source)!=source_hash:raise ValueError('Changed source PDF')
            version=document.get('version',document.get('curriculum_version'))
            key=(document['program'],version)
            evidence={'source_file':source,'source_sha256':source_hash,'pdf_page':document.get('pdf_page',document.get('page_number')),
                      'printed_page':document.get('printed_page',document.get('printed_page_number')),
                      'section':'course description' if file.startswith('prerequisite') else 'academic plan',
                      'approval':path.relative_to(app).as_posix(),'approval_sha256':sha(path),
                      'review_sample_id':document.get('review_sample_id'),'status':'reused_visual_approval; not newly reviewed'}
            if file.startswith('prerequisite'):
                if document['status'] not in {'required','explicit_none'}:raise ValueError('Unknown prerequisite status')
                for code in document['codes']:
                    expected={'prerequisite_status':document['status'],'requires':document.get('requires',[])}
                    # Do not infer a course name from the current DB or another curriculum.
                    if code in document.get('name_th_by_code',{}):expected['name_th']=document['name_th_by_code'][code]
                    grouped[key].append({'id':f'{file}:{source}:{evidence["pdf_page"]}:{code}','code':code,'expected':expected,'evidence':evidence})
            else:
                for row in document['rows']:
                    grouped[key].append({'id':f'{file}:{source}:{evidence["pdf_page"]}:{row["code"]}','code':row['code'],
                        'expected':{k:v for k,v in row.items() if k in {'name_th','name_en'}},'evidence':evidence})
    return grouped

def main():
    p=argparse.ArgumentParser();p.add_argument('--app-root',type=Path,default=ROOT)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();outputs=[]
    for (program,year),labels in sorted(collect(a.app_root,a.source_root).items()):
        if len({r['id'] for r in labels})!=len(labels):raise ValueError('Duplicate label IDs')
        data={'schema_version':1,'purpose':'partial_source_evaluation','identity':{'program':program,'version':year,'revision':None,'plan':None},
              'scope':'shared course fields only; plan membership NOT inferred; reused development approvals, not independent held-out',
              'unverified_fields':['full course coverage','plan membership','graduation conditions','complete L1-L4'],
              'labels':labels}
        dest=a.app_root/'data/ground_truth/evaluation'/f'{program}-{year}'/'reviewed-fields.json'
        dest.parent.mkdir(parents=True,exist_ok=True)
        payload=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
        if dest.exists() and dest.read_text(encoding='utf-8')!=payload:raise ValueError('Refusing different labels')
        dest.write_text(payload,encoding='utf-8')
        outputs.append({'path':dest.relative_to(a.app_root).as_posix(),'labels':len(labels),'sha256':sha(dest)})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(outputs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'datasets':len(outputs),'labels':sum(r['labels'] for r in outputs)}))

if __name__=='__main__':main()
