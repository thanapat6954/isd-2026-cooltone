"""Probe the same semester question against both versions, with raw API evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry


def validate(response,identity,source):
    return (response.get('selected_curricula')==[identity]
            and bool(response.get('rows'))
            and all(r.get('_source',{}).get('curriculum_name')==identity
                    and r.get('_source',{}).get('curriculum_version')==int(identity.split('-')[1])
                    and r.get('source_file')==source for r in response['rows']))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    args=parser.parse_args()
    def dependencies():
        return {'code':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.app_root/'lab10_fastapi/curriculum_app').glob('*.py')},
                'db':{d.relative_path:hashlib.sha256(d.path.read_bytes()).hexdigest() for d in DatabaseRegistry(args.app_root).active_programs}}
    result={'dependencies':dependencies(),'purpose':'version-isolation development check, NOT book-wide accuracy','pairs':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    for program in ('DSBA','IT','BIT'):
        for plan in ('coop','no-coop'):
            pair={'program':program,'plan':plan,'responses':[]}
            result['pairs'].append(pair)
            for version in (2560,2565):
                identity=f'{program}-{version}-{plan}'
                question=f'หลักสูตร {program} {version} '+('สหกิจ' if plan=='coop' else 'ไม่เข้าร่วมสหกิจ')+': ปี 4 ภาคการศึกษาที่ 2 มีรายวิชาอะไรบ้าง'
                source=f'{program}-60.pdf' if version==2560 else 'BIT-65.pdf' if program=='BIT' else f'{program}.pdf'
                api=requests.post(args.url+'/api/ask',json={'question':question},timeout=45)
                ui=requests.post(args.url+'/ask',json={'curriculum':program,'version':'old' if version==2560 else 'latest','question':question},timeout=45)
                body,frontend=api.json(),ui.json()
                passed=api.status_code==ui.status_code==200 and validate(body,identity,source) and body['answer']==frontend.get('answer')
                passed=passed and bool(frontend.get('sources')) and all(source in s.get('section','') and str(version) in s.get('section','') for s in frontend.get('sources',[]))
                pair['responses'].append({'identity':identity,'question':question,'api_status':api.status_code,'frontend_status':ui.status_code,
                                          'response':body,'frontend_response':frontend,'passed':passed})
                save()
            code_sets=[{r['code'] for r in p['response'].get('rows',[])} for p in pair['responses']]
            pair['code_sets_differ']=code_sets[0]!=code_sets[1]
            pair['passed']=all(p['passed'] for p in pair['responses']) and pair['code_sets_differ']
            save()
    result['dependencies_unchanged']=dependencies()==result['dependencies']
    save()
    print('Version pairs',sum(p['passed'] for p in result['pairs']),'/',len(result['pairs']),'unchanged',result['dependencies_unchanged'])
    return int(not result['dependencies_unchanged'] or not all(p['passed'] for p in result['pairs']))


if __name__=='__main__':raise SystemExit(main())
