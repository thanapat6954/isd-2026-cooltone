"""Observed API counterfactuals on isolated copies, never on deployed source data."""
import argparse
from contextlib import closing
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from lab10_fastapi.curriculum_app import main as web
from lab10_fastapi.curriculum_app.config import settings
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
from lab10_fastapi.curriculum_app.study_evidence import read_study_evidence


def main():
    p=argparse.ArgumentParser();p.add_argument('--migration',type=Path,required=True)
    p.add_argument('--backups',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();stages=json.loads(a.migration.read_text(encoding='utf-8'))
    backups=json.loads(a.backups.read_text(encoding='utf-8'))
    result={'purpose':'Synthetic counterfactuals on disposable copied DBs only','checks':[]}
    def record(name,passed,**evidence):
        result['checks'].append({'name':name,'passed':bool(passed),**evidence})
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='db-only-validation-') as folder:
        app=Path(folder)
        files={x['profile']:Path(x['stage']) for x in stages['databases']}
        files.update({x['profile']:Path(x['backup']) for x in backups['databases'] if x['profile']=='legacy-course-catalog'})
        targets={}
        for identity,path in files.items():
            target=app/'work'/identity/'curriculum.db';target.parent.mkdir(parents=True)
            src=open_readonly(path);dst=sqlite3.connect(target)
            try:src.backup(dst)
            finally:src.close();dst.close()
            targets[identity]=target
        registry=DatabaseRegistry(app);assistant=QwenTextToSQL(replace(settings,debug=True,sql_repair_attempts=0),None)
        with patch.object(web,'registry',registry),patch.object(web,'model',assistant):
            client=TestClient(web.app)
            q='IT-2565-coop วิชา 06016422 มีกี่หน่วยกิต'
            before=client.post('/api/ask',json={'question':q});body=before.json()
            record('source-reviewed-conflict',before.status_code==200 and body['rows'][0]['name_th']=='อินเทอร์เน็ตของสรรพสิ่ง',body=body)
            path=targets['IT-2565-coop']
            with closing(sqlite3.connect(path)) as c,c:c.execute("UPDATE course SET credits=7 WHERE code='06016422'")
            changed=client.post('/api/ask',json={'question':q});body=changed.json()
            record('fact-change-invalidates-cache',changed.status_code==200 and body['rows'][0]['credits']==7 and '7 หน่วยกิต' in body['answer'],body=body)
            with closing(sqlite3.connect(path)) as c,c:
                c.execute("DELETE FROM study_member WHERE plan_item_id IN (SELECT id FROM plan_item WHERE code='06016422')")
                c.execute("DELETE FROM study_item WHERE plan_item_id IN (SELECT id FROM plan_item WHERE code='06016422')")
                c.execute("DELETE FROM plan_item WHERE code='06016422'")
                c.execute("DELETE FROM course WHERE code='06016422'")
            missing=client.post('/api/ask',json={'question':q});body=missing.json()
            record('removed-evidence-no-json-fallback',missing.status_code==200 and not body.get('rows') and 'IT-2565-coop' in body['answer'] and '7 หน่วยกิต' not in body['answer'],body=body)
            for identity in files:
                if identity=='legacy-course-catalog': question='legacy วิชา 06066302 มีกี่หน่วยกิต'
                else:question=identity+' ปี 2 ภาคการศึกษาที่ 2 มีรายวิชาอะไรบ้าง'
                response=client.post('/api/ask',json={'question':question});body=response.json()
                record(identity+'-sqlite-only-no-json-or-pdf',response.status_code==200 and body.get('selected_curricula')==[identity] and bool(body.get('rows')),body=body)
            review_db=next(d for d in registry.active_programs if d.curriculum_name=='IT-2560-coop')
            with closing(sqlite3.connect(review_db.path)) as c,c:c.execute('UPDATE study_term SET printed_total=123 WHERE year=2 AND semester=2')
            payload={'curriculum':'IT','version':'old','question':'ปี 2 ภาคการศึกษาที่ 2 มีรายวิชาอะไรบ้าง แผนสหกิจศึกษา'}
            changed=client.post('/ask',json=payload);body=changed.json()
            record('term-total-from-sqlite',changed.status_code==200 and body['study_plan']['cards'][0]['printed_total']==123,body=body)
            with closing(sqlite3.connect(review_db.path)) as c,c:
                c.execute('DELETE FROM study_member');c.execute('DELETE FROM study_item')
                c.execute('DELETE FROM study_track');c.execute('DELETE FROM study_page');c.execute('DELETE FROM study_term')
            removed=client.post('/ask',json=payload);body=removed.json()
            record('removed-relations-no-overlay',removed.status_code==200 and not body['study_plan']['cards'][0]['reviewed'] and body['study_plan']['cards'][0]['printed_total'] is None,body=body)
            path.write_bytes(b'synthetic broken sqlite')
            try: read_study_evidence(next(d for d in registry.databases if d.curriculum_name=='IT-2565-coop'))
            except sqlite3.DatabaseError as e:record('db-failure-read-raises',True,error=str(e))
            else:record('db-failure-read-raises',False)
            failed=client.post('/api/ask',json={'question':q});body=failed.json()
            record('db-failure-api-explicit-error',failed.status_code>=400 and 'detail' in body and 'answer' not in body,status=failed.status_code,body=body)
    result['summary']={'passed':sum(x['passed'] for x in result['checks']),'n':len(result['checks'])}
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(result['summary'])
    return int(result['summary']['passed']!=result['summary']['n'])


if __name__=='__main__':raise SystemExit(main())
