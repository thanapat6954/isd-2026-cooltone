"""Development-only partial candidate probe; never activate or change working databases."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import requests


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--curriculum',required=True)
    parser.add_argument('--version',choices=('old','latest'),required=True)
    parser.add_argument('--question',action='append',required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env={**os.environ,'CURRICULUM_DATABASE_ROOT':str(args.candidate.resolve()),'PYTHONUTF8':'1'}
    record={'scope':'partial candidate API/source evidence; not normal startup/full activation or browser pass',
        'cases':[],'url':f'http://127.0.0.1:{port}','candidate':str(args.candidate.resolve())}
    def save():
        (args.output/'api.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    with (args.output/'backend.log').open('wb') as log:
        process=subprocess.Popen([sys.executable,'-m','uvicorn','lab10_fastapi.curriculum_app.main:app','--host','127.0.0.1','--port',str(port)],
            cwd=args.app_root.resolve(),env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    record['owned_pid']=process.pid;save()
    try:
        for _ in range(100):
            try:
                response=requests.get(record['url']+'/api/health',timeout=2)
                response.raise_for_status();record['health']=response.json();save();break
            except requests.RequestException:
                if process.poll() is not None: raise RuntimeError('owned backend exited')
                time.sleep(.1)
        else: raise RuntimeError('owned backend startup timeout')
        expected=args.app_root.resolve()/'scr/ocr_system/lab8b_curriculum_db.py'
        if Path(record['health']['lab8b_module']).resolve()!=expected: raise ValueError('wrong app root')
        for question in args.question:
            for route in ('/api/ask','/ask'):
                payload={'question':question}
                if route=='/ask': payload.update(curriculum=args.curriculum,version=args.version)
                started=time.perf_counter()
                response=requests.post(record['url']+route,json=payload,timeout=190)
                item={'route':route,'request':payload,'status':response.status_code,'seconds':round(time.perf_counter()-started,3),'response':response.json()}
                record['cases'].append(item);save();response.raise_for_status()
                for citation in item['response'].get('sources',[])[:1]:
                    filename=next(p.name for p in (args.app_root/'data/input').glob('*.pdf') if p.name in citation['section'])
                    info=requests.get(record['url']+f"/api/source-info/{filename}?page={citation['page']}",timeout=30)
                    info.raise_for_status();item['source_info']=info.json();save()
        record['completed']=True
    finally:
        process.terminate();process.wait(timeout=10)
        record['owned_process_stopped']=True;save()


if __name__=='__main__': main()
