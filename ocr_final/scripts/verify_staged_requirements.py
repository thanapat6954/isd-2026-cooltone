"""Exercise approved staged databases in isolation without a model or live writes."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.ingest_program_requirements import snapshot,sha
from lab10_fastapi.curriculum_app.config import settings
from lab10_fastapi.curriculum_app.database import DatabaseRegistry
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL


class NoModel:
    def ollama_generate(self,*args,**kwargs):
        raise AssertionError('Structured rules must remain SQLite backed')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output-root',type=Path,required=True)
    a=parser.parse_args();a.output_root.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(a.manifest.read_text(encoding='utf-8'))
    for row in manifest['databases']:
        if sha(Path(row['stage']))!=row['stage_sha256']:raise ValueError('Stage changed')
        snapshot(Path(row['stage']),a.output_root/'work'/row['profile']/'curriculum.db')
    registry=DatabaseRegistry(a.output_root)
    model=QwenTextToSQL(replace(settings,database_root=a.output_root),NoModel())
    results=[]
    for db in registry.active_programs:
        plan='ไม่เข้าร่วมสหกิจ' if db.plan=='no-coop' else 'สหกิจ'
        answer=model.ask(registry,f'หลักสูตร BIT 2565 {plan}: เกณฑ์การสำเร็จการศึกษามีอะไรบ้าง')
        passed=('2.00' in answer['answer'] and 'English Exit' in answer['answer'] and 'ยังยืนยันไม่ได้' in answer['answer']
                and any(r.get('page_number')==93 and r.get('printed_page_number')==88 for r in answer['rows']))
        results.append({'profile':db.curriculum_name,'passed':passed,'result':answer})
    unchanged=all(sha(Path(r['live']))==r['before_sha256'] for r in manifest['databases'])
    result={'profiles':results,'n':len(results),'passed':sum(r['passed'] for r in results),'working_databases_unchanged':unchanged}
    (a.output_root/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='profiles'}))
    return int(not unchanged or result['passed']!=result['n'] or result['n']!=2)


if __name__=='__main__':raise SystemExit(main())
