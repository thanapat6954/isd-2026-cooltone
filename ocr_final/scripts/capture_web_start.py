"""Capture the real Windows launcher result and independent OpenAPI readiness."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import requests


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--qa-evidence',type=Path)
    parser.add_argument('--case-id')
    args=parser.parse_args()
    command=[shutil.which('pwsh') or shutil.which('powershell'),'-NoProfile','-File',str(args.app_root/'scripts/start_web.ps1')]
    result={'command':command,'started_utc':datetime.now(timezone.utc).isoformat(),'status':'in_progress'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    try:
        # Background children can inherit PIPE handles even after PowerShell exits.
        # Files let the bounded parent wait finish without waiting for server EOF.
        stdout_path=args.output.with_suffix('.stdout.log')
        stderr_path=args.output.with_suffix('.stderr.log')
        with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
            run=subprocess.run(command,cwd=args.app_root,stdout=stdout,stderr=stderr,timeout=75)
        result.update(exit_code=run.returncode,
                      stdout=stdout_path.read_text(encoding='utf-8',errors='replace'),
                      stderr=stderr_path.read_text(encoding='utf-8',errors='replace'))
        response=requests.get('http://127.0.0.1:8000/openapi.json',timeout=5)
        result.update(openapi_status=response.status_code,post_ask_registered='post' in response.json().get('paths',{}).get('/api/ask',{}),
                      frontend_status=requests.get('http://127.0.0.1:8000/frontend/',timeout=5).status_code,status='complete')
        if args.qa_evidence:
            from run_old2560_qa import check
            case=next(c for c in json.loads(args.qa_evidence.read_text(encoding='utf-8'))['cases'] if c['id']==args.case_id)
            api=requests.post('http://127.0.0.1:8000/api/ask',json={'question':case['question']},timeout=45)
            ui=requests.post('http://127.0.0.1:8000/ask',json={'curriculum':case['identity'].split('-')[0],'version':'old','question':case['question']},timeout=45)
            errors,_=check(api.json(),ui.json(),case['identity'],case['expect']) if api.status_code==ui.status_code==200 else (['HTTP error'],None)
            result['restart_probe']={'id':case['id'],'question':case['question'],'api_status':api.status_code,'frontend_status':ui.status_code,'response':api.json(),'frontend_response':ui.json(),'errors':errors,'passed':not errors}
    except Exception as error:
        result.update(status='failed',error=repr(error))
    result['finished_utc']=datetime.now(timezone.utc).isoformat()
    save()
    print(result.get('stdout','').strip())
    print('OpenAPI',result.get('openapi_status'),'POST /api/ask',result.get('post_ask_registered'),'frontend',result.get('frontend_status'))
    return int(result.get('exit_code')!=0 or result.get('openapi_status')!=200 or not result.get('post_ask_registered') or result.get('frontend_status')!=200 or result.get('restart_probe',{}).get('passed') is False)


if __name__=='__main__':raise SystemExit(main())
