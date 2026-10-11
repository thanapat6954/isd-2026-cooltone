"""Measured fresh delivery and actual-artifact lifecycle. Leaves working apps untouched."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-root',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8005)
    parser.add_argument('--resume',action='store_true',help='Reuse only successful fresh preparation, not running services or failed checks')
    args=parser.parse_args()
    root=args.project_root.resolve()
    workspace=args.workspace.resolve()
    output=args.output.resolve()
    if not args.resume:
        workspace.mkdir(parents=True,exist_ok=False)
        output.mkdir(parents=True,exist_ok=False)
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',args.port))==0:
            raise ValueError('test port occupied; nothing stopped')
    app=workspace/'delivered project/ocr_final'
    if not args.resume:
        shutil.copytree(root/'ocr_final',app,ignore=shutil.ignore_patterns('venv','.venv','work','reports','input','tmp',
            '*.db','*.db-wal','*.db-shm','.env','__pycache__','node_modules'))
        shutil.copy2(root/'README.md',app.parent/'README.md')
    # Supplied artifacts are physical copies, no LIVE or developer venv dependency.
    bundle=app.parent/'supplied-artifacts/runtime-data'
    if not args.resume:
        shutil.copytree(args.bundle,bundle)
    env={k:v for k,v in os.environ.items() if not k.startswith(('CURRICULUM_', 'OLLAMA_', 'PYTHON', 'PIP_'))}
    env.update(PYTHONUTF8='1',CURRICULUM_DATABASE_ROOT='.',CURRICULUM_OLLAMA_MODEL='qwen3:4b',
        CURRICULUM_OLLAMA_URL='http://127.0.0.1:11434',OLLAMA_HOST='http://127.0.0.1:11434')
    python=str(app/'venv/Scripts/python.exe')
    state={'scope':'actual supplied-artifact lifecycle; fresh venv; shared already-installed model service explicitly disclosed',
        'app_root':str(app),'port':args.port,'steps':[], 'checks':{}, 'limitations':[
        'OS installers not rehearsed', 'fresh model download inherited from prior measured unchanged-model rehearsal',
        'browser previously policy-blocked; no browser interaction attempted', 'fresh OCR probe one page, not all profiles']}
    if args.resume:
        shutil.copy2(output/'verification.json',output/('verification-before-resume-'+str(time.time_ns())+'.json'))
        state=json.loads((output/'verification.json').read_text(encoding='utf-8'))
        state.setdefault('retained_failures',[]).append(state.pop('failure',None))
    def save():
        (output/'verification.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    def run(name,command,*,expected=0,timeout=240,cwd=app,extra=None):
        if args.resume and name in {'fresh-venv','fresh-runtime-rebuild-dependencies','pip-check','freeze','restore','preflight'} and any(
                s['name']==name and s['exit_code']==0 for s in state['steps']):
            return (output/(name+'.stdout.log')).read_text(encoding='utf-8-sig',errors='replace')
        state['running']=name
        save()
        started=time.perf_counter()
        with (output/(name+'.stdout.log')).open('wb') as out,(output/(name+'.stderr.log')).open('wb') as err:
            result=subprocess.run(list(map(str,command)),env={**env,**(extra or {})},cwd=cwd,stdout=out,stderr=err,timeout=timeout)
        state['steps'].append({'name':name,'command':list(map(str,command)),'seconds':round(time.perf_counter()-started,3),'exit_code':result.returncode})
        save()
        print(name,result.returncode,flush=True)
        if result.returncode!=expected:
            raise RuntimeError(name+' unexpected exit; inspect retained logs')
        return (output/(name+'.stdout.log')).read_text(encoding='utf-8-sig',errors='replace')
    def http(path,payload=None):
        request=urllib.request.Request(f'http://127.0.0.1:{args.port}'+path,
            data=json.dumps(payload).encode() if payload else None,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=190) as response:
            return json.loads(response.read())
    def ps(name,script,*,expected=0,extra=None):
        return run(name,['pwsh','-NoProfile','-File',app/'scripts'/script,'-Port',args.port],expected=expected,extra=extra)
    def answers(cycle):
        health=http('/api/health')
        if Path(health['lab8b_module']).resolve()!=app/'scr/ocr_system/lab8b_curriculum_db.py':
            raise ValueError('wrong server root')
        if health['queryable_database_count']!=14:
            raise ValueError('incomplete loaded set')
        state['checks'][cycle+'-health']=health
        records=[]
        for route,payload in (
            ('/api/ask',{'question':'IT 2560 แผนไม่สหกิจศึกษา หลักสูตรนี้มีกี่ปี'}),
            ('/ask',{'question':'แผนไม่สหกิจศึกษา หลักสูตรนี้มีกี่ปี','curriculum':'IT','version':'old'}),
            ('/api/ask',{'question':'BIT 2565 แผนไม่สหกิจศึกษา วิชา 06036123 มีชื่อและหน่วยกิตอะไร'}),
            ('/ask',{'question':'แผนไม่สหกิจศึกษา วิชา 06036123 มีชื่อและหน่วยกิตอะไร','curriculum':'BIT','version':'latest'})):
            started=time.perf_counter()
            result=http(route,payload)
            records.append({'route':route,'payload':payload,'seconds':round(time.perf_counter()-started,3),'response':result})
            state['checks'][cycle+'-answers']=records
            save()
            text=json.dumps(result,ensure_ascii=False)
            if payload.get('curriculum')=='IT' or payload['question'].startswith('IT '):
                if '4' not in text or 'IT-60.pdf' not in text:
                    raise ValueError('duration answer/citation missing')
            elif '06036123' not in text or 'cloud technology' not in text.casefold():
                raise ValueError('course answer/citation missing')
            if route=='/ask':
                for citation in result.get('sources',[])[:1]:
                    filename=next((name for name in ('IT-60.pdf','BIT-65.pdf') if name in citation['section']),None)
                    if not filename:
                        raise ValueError('citation source missing')
                    info=http(f"/api/source-info/{filename}?page={citation['page']}")
                    if info.get('printed_page')!=citation.get('book_page'):
                        raise ValueError('citation folio mismatch')
                    records[-1]['citation_source_info']=info
                    save()
        state['checks'][cycle+'-answers']=records
        save()
    save()
    started_backend=False
    try:
        run('fresh-venv',['py','-3.11','-m','venv','venv'])
        run('fresh-runtime-rebuild-dependencies',[python,'-m','pip','--isolated','install','--no-cache-dir','--index-url','https://pypi.org/simple','-r','requirements-rebuild.txt'],timeout=600)
        run('pip-check',[python,'-m','pip','check'])
        run('freeze',[python,'-m','pip','freeze'])
        run('restore',[python,'scripts/runtime_bundle.py','restore','--bundle','../supplied-artifacts/runtime-data','--app-root','.'])
        run('preflight',[python,'scripts/check_setup.py'])
        with socket.socket() as free:
            free.bind(('127.0.0.1',0)); unrelated_port=free.getsockname()[1]
        with (output/'unrelated-server.log').open('wb') as log:
            unrelated=subprocess.Popen([python,'-m','http.server',str(unrelated_port),'--bind','127.0.0.1'],cwd=app,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(100):
                with socket.socket() as ready:
                    if ready.connect_ex(('127.0.0.1',unrelated_port))==0: break
                time.sleep(.05)
            run('occupied-port-reject',['pwsh','-NoProfile','-File',app/'scripts/start_web.ps1','-Port',unrelated_port],expected=1)
            if unrelated.poll() is not None:
                raise ValueError('unrelated service was stopped')
            state['checks']['occupied_port']={'port':unrelated_port,'pid':unrelated.pid,'still_running_after_rejection':True};save()
        finally:
            unrelated.terminate();unrelated.wait(timeout=10)
        ps('start-bundled','start_web.ps1'); started_backend=True
        answers('bundled')
        # The active consumer lock must reject activation without altering the pointer.
        imported=json.loads(run('import-bundle',[python,'scripts/database_build.py','import-bundle','--bundle','../supplied-artifacts/runtime-data']))
        candidate=imported['candidate']
        run('activation-reject-running',[python,'scripts/database_build.py','activate','--candidate',candidate],expected=1)
        ps('stop-bundled','stop_web.ps1'); started_backend=False
        activated=json.loads(run('activate-existing',[python,'scripts/database_build.py','activate','--candidate',candidate]))
        state['checks']['activation']=activated; save()
        ps('start-activated','start_web.ps1'); started_backend=True
        answers('activated')
        ps('stop-activated','stop_web.ps1'); started_backend=False
        # Real post-pointer failure and profile mismatch tests preserve active bytes.
        code="""import sys,json,sqlite3
from pathlib import Path
sys.path.insert(0,'.')
from scripts.database_build import *
app=Path('.').resolve(); bundle=Path('../supplied-artifacts/runtime-data').resolve()
before=(app/'work/active-build.json').read_bytes(); old={str(x.path):sha(x.path) for x in DatabaseRegistry(app).active_catalogs}
c=import_bundle(bundle,app)
def fail(stage):
    if stage=='after-pointer': raise RuntimeError('injected after atomic pointer')
try: activation(app,c,failure_hook=fail)
except RuntimeError: pass
assert (app/'work/active-build.json').read_bytes()==before
assert all(sha(Path(p))==h for p,h in old.items())
c=import_bundle(bundle,app); m=read(c/'build.json'); row=next(r for r in m['databases'] if r.get('version'))
with sqlite3.connect(c/row['path']) as db: db.execute('UPDATE program SET curriculum_version=9999'); db.commit()
row['sha256']=sha(c/row['path']);write(c/'build.json',m)
assert not validate(c,app)['ready']
try: activation(app,c)
except ValueError: pass
assert (app/'work/active-build.json').read_bytes()==before
c=import_bundle(bundle,app);m=read(c/'build.json');(c/m['databases'][0]['path']).unlink()
assert not validate(c,app)['ready']
assert (app/'work/active-build.json').read_bytes()==before
print(json.dumps({'after_pointer_failure_recovered':True,'mismatched_rejected':True,'partial_rejected':True,'old_database_hashes_unchanged':True}))
"""
        (output/'failure-probe.py').write_text(code,encoding='utf-8')
        state['checks']['failures']=json.loads(run('failure-probes',[python,output/'failure-probe.py']))
        # Failed genuine OCR-model invocation over the active set must not change it.
        pointer_before=(app/'work/active-build.json').read_bytes()
        run('missing-ocr-model-build',[python,'scripts/database_build.py','rebuild','--profiles','ai','--max-pages','1','--stage-timeout','150'],expected=1,
            extra={'LAB7_MODEL_OCR':'missing-instructor-test-model:latest'},timeout=200)
        state['checks']['failed_build_kept_pointer']=(app/'work/active-build.json').read_bytes()==pointer_before
        run('missing-answer-model-preflight',[python,'scripts/check_setup.py'],expected=1,extra={'CURRICULUM_OLLAMA_MODEL':'missing-instructor-test-model:latest'})
        ps('missing-answer-model-launcher','start_web.ps1',expected=1,extra={'CURRICULUM_OLLAMA_MODEL':'missing-instructor-test-model:latest'})
        pdf=app/'data/input/AI.pdf'
        pdf.rename(pdf.with_suffix('.pdf.withheld'))
        try:
            ps('missing-file-launcher','start_web.ps1',expected=1)
        finally:
            pdf.with_suffix('.pdf.withheld').rename(pdf)
        run('rollback',[python,'scripts/database_build.py','rollback','--backup',activated['backup']])
        ps('start-recovered','start_web.ps1'); started_backend=True
        answers('recovered')
        ps('stop-recovered','stop_web.ps1'); started_backend=False
        # Reconstruct without any prior DB: only code/configuration, PDF and page selection.
        fresh=workspace/'pdf-only app'
        for folder in ('scripts','scr','lab10_fastapi'):
            shutil.copytree(app/folder,fresh/folder,ignore=shutil.ignore_patterns('__pycache__','.env'))
        shutil.copy2(app/'run_lab8b.py',fresh/'run_lab8b.py')
        (fresh/'data/input').mkdir(parents=True)
        shutil.copyfile(app/'data/input/AI.pdf',fresh/'data/input/AI.pdf')
        shutil.copytree(app/'data/source_reviews/page_selection',fresh/'data/source_reviews/page_selection')
        state['checks']['fresh_before']={'database_files':list(map(str,fresh.rglob('*.db'))),
            'ocr_files':list(map(str,fresh.rglob('pred*.json'))),'master_files':list(map(str,fresh.rglob('master.json'))),
            'evaluation_files':list(map(str,fresh.rglob('*gold*json')))}
        save()
        run('fresh-ai23-from-pdf',[python,fresh/'scripts/database_build.py','--app-root',fresh,'rebuild','--profiles','ai','--max-pages','1','--stage-timeout','180'],expected=1,timeout=420,cwd=fresh)
        state['checks']['fresh_ocr_result']=[json.loads(p.read_text(encoding='utf-8')) for p in fresh.glob('work/staging/*/build.json')]
        state['completed']=True
    except Exception as exc:
        state['failure']=str(exc)
        raise
    finally:
        if started_backend:
            try: ps('cleanup-backend','stop_web.ps1')
            except Exception as exc: state['cleanup_error']=str(exc)
        state['running']=None
        save()


if __name__=='__main__':
    main()
