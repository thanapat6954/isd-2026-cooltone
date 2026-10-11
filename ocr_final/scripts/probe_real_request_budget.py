"""Real Ollama calls and isolated SQLite snapshots; no answer mocks or gold labels."""
import argparse
from contextlib import closing
from dataclasses import replace
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import socket
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--app-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--budget',type=float,default=1)
    p.add_argument('--ollama-log',type=Path)
    p.add_argument('--question', action='append', help='Development questions; no gold labels are read')
    p.add_argument('--mutate-course', help='Synthetic provenance fixture in isolated snapshot only')
    p.add_argument('--description', default=None)
    p.add_argument('--break-course-table', action='store_true')
    p.add_argument('--cycle-description', action='store_true', help='Same-process A/cache/B/removal/table-failure/recovery in the isolated snapshot')
    a=p.parse_args()
    if a.budget<=0:raise ValueError('A positive actual request budget is required')
    if a.cycle_description and not a.mutate_course:
        raise ValueError('Cycle requires --mutate-course for isolated fixture selection')
    a.output.mkdir(parents=True,exist_ok=False)
    isolated=a.output/'app';db=isolated/'work/lab8b_it_coop/curriculum.db';db.parent.mkdir(parents=True)
    source=a.app_root/'work/lab8b_it_coop/curriculum.db'
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as original,closing(sqlite3.connect(db)) as dest:
        original.backup(dest)
    if a.mutate_course or a.break_course_table:
        with sqlite3.connect(db) as fixture:
            if a.mutate_course:
                fixture.execute('UPDATE course SET description_th=? WHERE code=?', (a.description, a.mutate_course))
            if a.break_course_table:
                fixture.execute('ALTER TABLE course RENAME TO isolated_unavailable_course')
    os.environ['CURRICULUM_DATABASE_ROOT']=str(isolated.resolve())
    os.environ['CURRICULUM_REQUEST_TIMEOUT']='1'
    import requests
    import uvicorn
    from lab10_fastapi.curriculum_app import main as web
    web.model.config=replace(web.model.config,request_timeout=a.budget)
    log_offset=a.ollama_log.stat().st_size if a.ollama_log and a.ollama_log.exists() else None
    try:resident_before=requests.get(web.settings.ollama_url+'/api/ps',timeout=5).json()
    except requests.RequestException:resident_before=None
    calls=[];real_generate=web.model.lab8b.ollama_generate
    def observed_generate(*args,**kwargs):
        started=time.perf_counter();record={'budget_s':kwargs['timeout'],'model':kwargs['model']};calls.append(record)
        try:
            result=real_generate(*args,**kwargs)
            record['returned']=True
            record['raw_model_output']=result
            return result
        except Exception as exc:
            record['exception']=type(exc).__name__
            raise
        finally:record['elapsed_ms']=round((time.perf_counter()-started)*1000,2)
    web.model.lab8b.ollama_generate=observed_generate
    traces=[];real_ask=web.model.ask
    def observed_ask(*args,**kwargs):
        answer=real_ask(*args,**kwargs)
        traces.append(answer)
        return answer
    web.model.ask=observed_ask
    result={'scope':'isolated actual local HTTP contracts; real model; not browser or difficult-question accuracy','started_utc':datetime.now(timezone.utc).isoformat(),'resident_before':resident_before,'positive_budget_s':a.budget,'model_calls':calls,'requests':[],'source_db_sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'isolated_mutation':{'code':a.mutate_course,'description':a.description,'broken_course_table':a.break_course_table}}
    with socket.socket() as reserved:
        reserved.bind(('127.0.0.1',0));port=reserved.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(web.app,host='127.0.0.1',port=port,log_level='warning',timeout_graceful_shutdown=2))
    worker=threading.Thread(target=server.run,daemon=True);worker.start()
    ready_deadline=time.perf_counter()+10
    while not server.started:
        if time.perf_counter()>ready_deadline:raise TimeoutError('Isolated server startup failed')
        time.sleep(.05)
    url=f'http://127.0.0.1:{port}'
    cases = [(route, question) for question in (a.question or ['หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างการพัฒนาซอฟต์แวร์กับระบบคอมพิวเตอร์ โดยอ้างเฉพาะข้อมูลที่บันทึกไว้']) for route in ('/api/ask','/ask')]
    if a.cycle_description:
        cases = [(route, question, stage) for stage in ('A', 'B', 'removed', 'failure', 'recovered')
                 for question in (a.question or []) for route in ('/api/ask', '/api/ask', '/ask')]
    else:
        cases = [(route, question, None) for route, question in cases]
    current_stage = None
    for route, question, stage in cases:
        if stage != current_stage:
            with sqlite3.connect(db) as fixture:
                if stage == 'failure':
                    fixture.execute('ALTER TABLE course RENAME TO isolated_unavailable_course')
                else:
                    if current_stage == 'failure':
                        fixture.execute('ALTER TABLE isolated_unavailable_course RENAME TO course')
                    fixture.execute('UPDATE course SET description_th=? WHERE code=?',
                                    ('ISOLATED_CYCLE_'+stage if stage in {'A','B'} else None, a.mutate_course))
            current_stage = stage
        # Explicitly unknown intent so the deterministic renderer cannot bypass the model.
        from lab10_fastapi.curriculum_app.query_planner import detect_intent
        if detect_intent(question).intent!='unknown':raise ValueError('Probe must exercise actual LLM fallback')
        if not a.cycle_description:
            web.model._answer_cache.clear()
        traces.clear()
        payload={'question':question}
        if route=='/ask':payload.update(curriculum='IT',version='latest')
        started=time.perf_counter();response=requests.post(url+route,json=payload,timeout=a.budget+10)
        result['requests'].append({'route':route,'question':question,'stage':stage,'status':response.status_code,'body':response.text,'elapsed_ms':round((time.perf_counter()-started)*1000,2), 'trace':traces[-1] if traces else None})
        recovery=requests.post(url+route,json={**payload,'question':'หลักสูตร IT 2565 สหกิจ ปี 4 ภาคการศึกษาที่ 1 เรียนกี่หน่วยกิต'},timeout=10)
        result['requests'].append({'route':route,'kind':'subsequent structured recovery','status':recovery.status_code,'body':recovery.json()})
        (a.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    server.should_exit=True;worker.join(timeout=5)
    result['isolated_server_stopped']=not worker.is_alive()
    result['finished_utc']=datetime.now(timezone.utc).isoformat()
    result['source_db_unchanged']=result['source_db_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
    if log_offset is not None:
        time.sleep(1)
        with a.ollama_log.open('rb') as stream:
            stream.seek(log_offset);appended=stream.read(65536).decode('utf-8',errors='replace')
        result['ollama_appended_events']=[line for line in appended.splitlines() if '/api/chat' in line or 'context canceled' in line]
    (a.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'statuses':[r['status'] for r in result['requests']],'real_model_calls':len(calls),'server_stopped':result['isolated_server_stopped']}))


if __name__=='__main__':main()
