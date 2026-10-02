"""Expanded source-backed development probes, separate from protected held-out."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_qa_gold import cases,evaluate
from lab10_fastapi.curriculum_app.database import DatabaseRegistry


def dataset():
    old=json.loads((ROOT/'tests/qa_gold.json').read_text(encoding='utf-8'))
    groups=[]
    names={'DSBA':('06026100','พื้นฐานทางด้านเทคโนโลยีสารสนเทศ'),
           'IT':('06016323','การโปรแกรมอุปกรณ์เคลื่อนที่'),
           'BIT':('06036010','กระบวนการธุรกิจและการวางแผนทรัพยากรองค์กร')}
    for group in old['groups']:
        if group['versions']!=[2560] or group['program'] not in names: continue
        for plan in group['plans']:
            program=group['program']
            items=[dict(item) for item in group['cases']]
            code,name=names[program]
            items.append({'question':f'วิชา{name}มีกี่หน่วยกิต','code':code,'credits':3,'name_th':name,
                          'source':program+'-60.pdf','level':'name-only',
                          'evidence':'docs/results/a1_ground_truth_review.json (approved only)'})
            prerequisite_name={'DSBA':'การสร้างโปรแกรมทางสถิติ','IT':'การโปรแกรมอุปกรณ์เคลื่อนที่',
                               'BIT':'กระบวนการธุรกิจและการวางแผนทรัพยากรองค์กร'}[program]
            prerequisite_case=next(dict(c) for c in group['cases'] if c.get('requires'))
            prerequisite_case.update(question=f'วิชา{prerequisite_name}มีวิชาบังคับก่อนอะไร',level='name-only-prerequisite')
            items.append(prerequisite_case)
            if program=='IT':
                items.append({'question':'วิชาการเขียนโปรแกรมมีกี่หน่วยกิต','ambiguous':True,'level':'name-only'})
                items.append({'question':'ปี 3 ภาคการศึกษาที่ 1 มีรายวิชาอะไรบ้าง','code':code,'year':3,'semester':1,'source':'IT-60.pdf','level':'placement',
                              'names_by_code':{'06016333':'เทคโนโลยีการให้บริการอินเตอร์เน็ต','06016343':'การออกแบบและพัฒนาเกม'},
                              'evidence':'rendered IT-60 PDF37/30 full-term reviews'})
                items.append({'question':'ปี 3 ภาคการศึกษาที่ 2 มีรายวิชาอะไรบ้าง','source':'IT-60.pdf',
                              'page':38 if plan=='coop' else 31,'book_page':33 if plan=='coop' else 26,
                              'raw_credits_by_code':{'06016326':'3(3-0-6)','06016337':'3(3-0-6)','06016338':'3(3-0-6)'},
                              'level':'credit-hour-pattern','evidence':'rendered IT-60 PDF38/31 term reviews'})
                term=(4,2) if plan=='coop' else (4,1)
                items.append({'question':f'ปี {term[0]} ภาคการศึกษาที่ {term[1]} มีรายวิชาอะไรบ้าง',
                              'slot_names':['วิชาเลือกเสรี 1','วิชาเลือกเสรี 2'],
                              'credit_alternative':'3(3-0-6) หรือ 3(2-2-5)',
                              'source':'IT-60.pdf','page':40 if plan=='coop' else 32,'book_page':35 if plan=='coop' else 27,
                              'level':'elective-alternatives','evidence':'rendered IT-60 PDF40/32'})
                items.append({'question':'ปี 2 ภาคการศึกษาที่ 2 มีรายวิชาอะไรบ้าง',
                              'candidate_codes':['06016321','06016322','06016331','06016332','06016341','06016342'],
                              'alternative':True,'source':'IT-60.pdf','page':36 if plan=='coop' else 29,'level':'alternatives'})
            elif program=='DSBA':
                items.append({'question':'ปี 1 ภาคการศึกษาที่ 1 มีรายวิชาอะไรบ้าง','code':code,'year':1,'semester':1,
                              'source':'DSBA-60.pdf','level':'placement'})
                items.append({'question':'ปี 4 ภาคการศึกษาที่ 2 มีรายวิชาอะไรบ้าง',
                              'candidate_codes':['06026130','06026131'] if plan=='coop' else [],
                              'slot_names':[] if plan=='coop' else ['วิชาเลือกเสรี 2'],
                              'alternative':plan=='coop','source':'DSBA-60.pdf','page':34 if plan=='coop' else 29,
                              'book_page':29 if plan=='coop' else 24,'level':'elective-alternatives'})
                items.append({'question':'ปี 4 ภาคการศึกษาที่ 1 มีรายวิชาอะไรบ้าง',
                              'slot_names':['วิชาเลือกเสรี 1'],
                              **({'credit_alternative':'3(3-0-6) หรือ 3(2-2-5)'} if plan=='no-coop' else {}),
                              'source':'DSBA-60.pdf','level':'elective-alternatives'})
                if plan=='coop':
                    items.append({'question':'ปี 3 ภาคการศึกษาที่ 2 มีรายวิชาอะไรบ้าง',
                                  'credit_alternative':'3(3-0-6) หรือ 3(2-2-5)','source':'DSBA-60.pdf','page':33,
                                  'book_page':28,'level':'elective-alternatives','evidence':'rendered DSBA-60 PDF33'})
            else:
                items.append({'question':'ปี 3 ภาคการศึกษาที่ 1 มีรายวิชาอะไรบ้าง','code':code,'year':3,'semester':1,
                              'source':'BIT-60.pdf','level':'placement'})
                items.append({'question':'ปี 4 ภาคการศึกษาที่ 2 มีรายวิชาอะไรบ้าง',
                              'slot_names':['วิชาเลือกเสรี 1','วิชาเลือกเสรี 2'] if plan=='coop' else ['วิชาเลือกเสรี 2'],
                              'source':'BIT-60.pdf','page':30 if plan=='coop' else 26,'book_page':25 if plan=='coop' else 21,
                              'level':'elective','evidence':'rendered BIT-60 PDF30/26'})
                items.append({'question':'ปี 4 ภาคการศึกษาที่ 1 มีรายวิชาอะไรบ้าง',
                              'candidate_codes':['06036046','06036047'] if plan=='coop' else ['06036019'],
                              'alternative':plan=='coop','source':'BIT-60.pdf','level':'alternatives'})
            groups.append({'program':program,'versions':[2560],'plans':[plan],'cases':items})
    return {'purpose':'development probes; prior approved A1 facts and new rendered table reviews; not held-out accuracy',
            'unmeasured':['true book-wide absent-course proof','full independent prerequisite coverage'], 'groups':groups}


def check(body,frontend,identity,case):
    errors,citation=evaluate(body,identity,case)
    rows=body.get('rows',[])
    answer=body.get('answer','')
    if case.get('ambiguous'):
        if len({r.get('code') for r in rows})<2 or 'โปรดระบุรหัสวิชา' not in answer: errors.append('candidate clarification')
    for code in case.get('candidate_codes',[]):
        if code not in {r.get('code') for r in rows}: errors.append('missing printed alternative '+code)
    for field,mapping in [('name_th',case.get('names_by_code',{})),('credits_raw',case.get('raw_credits_by_code',{}))]:
        for code,value in mapping.items():
            if not any(r.get('code')==code and r.get(field)==value for r in rows):errors.append(field+' mismatch '+code)
    for name in case.get('slot_names',[]):
        if not any(r.get('is_placeholder') and name in str(r.get('name_th')) for r in rows): errors.append('missing elective slot '+name)
    if case.get('alternative') and 'หรือ' not in answer: errors.append('alternative not displayed')
    if case.get('credit_alternative') and not any(r.get('credits_raw')==case['credit_alternative'] for r in rows): errors.append('credit/hour alternative lost')
    for field in ('year','semester'):
        if field in case and not all(r.get(field)==case[field] for r in rows): errors.append('placement '+field)
    if frontend.get('answer')!=answer: errors.append('frontend/API answer disagreement')
    sources=frontend.get('sources',[])
    if rows and not sources: errors.append('no frontend sources')
    missing_book=sum(not s.get('book_page') for s in sources)
    if missing_book: errors.append(f'missing printed page for {missing_book} sources')
    if any('-60.pdf' not in s.get('section','') or '2560' not in s.get('section','') for s in sources): errors.append('source version leak')
    return errors,citation


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--app-root',type=Path,default=ROOT)
    args=parser.parse_args()
    data=dataset()
    fingerprint=hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    def dependencies():
        return {'code':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.app_root/'lab10_fastapi/curriculum_app').glob('*.py')},
                'databases':{d.relative_path:hashlib.sha256(d.path.read_bytes()).hexdigest() for d in DatabaseRegistry(args.app_root).active_programs},'url':args.url}
    initial=dependencies()
    result={'dataset':data,'dataset_sha256':fingerprint,'dependencies':initial,'cases':[]}
    if args.resume and args.output.exists():
        result=json.loads(args.output.read_text(encoding='utf-8'))
        if result['dataset_sha256']!=fingerprint or result.get('dependencies')!=initial: raise ValueError('Dataset/code/database changed; use a new result')
    done={c['id'] for c in result['cases']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():
        stage=args.output.with_suffix('.partial')
        stage.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        stage.replace(args.output)
    save()
    for key,identity,question,case in cases(data):
        if key in done: continue
        begin=time.perf_counter()
        api=requests.post(args.url+'/api/ask',json={'question':question},timeout=45)
        ui=requests.post(args.url+'/ask',json={'curriculum':identity.split('-')[0],'version':'old','question':question},timeout=45)
        body,frontend=api.json(),ui.json()
        errors,citation=check(body,frontend,identity,case) if api.status_code==ui.status_code==200 else (['HTTP error'],None)
        result['cases'].append({'id':key,'identity':identity,'question':question,'expect':case,
                               'api_status':api.status_code,'frontend_status':ui.status_code,'response':body,
                               'frontend_response':frontend,'errors':errors,'passed':not errors,
                               'elapsed_ms':round((time.perf_counter()-begin)*1000,2),'citation_supported':citation})
        save()
    result['summary']={identity:{'n':sum(c['identity']==identity for c in result['cases']),
                                'passed':sum(c['identity']==identity and c['passed'] for c in result['cases'])}
                       for identity in sorted({c['identity'] for c in result['cases']})}
    result['dependencies_unchanged']=dependencies()==initial
    save()
    print(json.dumps(result['summary'],ensure_ascii=False))
    return int(not result['dependencies_unchanged'] or any(not c['passed'] for c in result['cases']))


if __name__=='__main__': sys.exit(main())
