"""Rehearse from the actual local ZIP submission, not the checkout or LIVE folder."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.workspace.mkdir(parents=True,exist_ok=False)
    args.output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((args.package/'handoff-manifest.json').read_text(encoding='utf-8'))
    state={'scope':'actual submission ZIPs, fresh venv and model store','steps':[]}
    def save():
        (args.output/'package-state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    save()
    for item in manifest['archives']:
        archive=args.package/item['file']
        with archive.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=item['sha256']:
                raise ValueError('Submission archive hash mismatch')
        target=args.workspace/('submitted-project' if item['file']=='curriculum-project.zip' else 'supplied-artifacts')
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if not (target/name).resolve().is_relative_to(target.resolve()):
                    raise ValueError('Unsafe archive path')
            bundle.extractall(target)
    project=args.workspace/'submitted-project'
    for item in manifest['code_files']:
        if hashlib.sha256((project/item['path']).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Packaged code differs from prepared inventory')
    state['archive_hashes_valid']=True
    state['code_files_verified']=len(manifest['code_files'])
    state['active_step']='fresh_zip_rehearsal'
    save()
    command=[sys.executable,str(project/'ocr_final/scripts/verify_fresh_handoff.py'),
        '--project-root',str(project),'--workspace',str(args.workspace/'fresh-run'),
        '--bundle',str(args.workspace/'supplied-artifacts/runtime-data'),
        '--output',str(args.output/'rehearsal.json')]
    with (args.output/'job.stdout.log').open('wb') as out,(args.output/'job.stderr.log').open('wb') as err:
        proc=subprocess.run(command,stdout=out,stderr=err,timeout=1200)
    state['rehearsal_exit_code']=proc.returncode
    save()
    if proc.returncode:
        raise RuntimeError('Fresh ZIP rehearsal failed; preserve results and logs')
    # Check documented CLI commands against only this rehearsal's downloaded model.
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',11437))==0:
            raise ValueError('CLI probe port occupied')
    env={k:v for k,v in os.environ.items() if not k.startswith('OLLAMA_')}
    env.update(OLLAMA_HOST='127.0.0.1:11437',OLLAMA_MODELS=str((args.workspace/'fresh-run/fresh-models').resolve()),OLLAMA_NO_CLOUD='1')
    with (args.output/'cli-service.log').open('wb') as log:
        service=subprocess.Popen([shutil.which('ollama'),'serve'],env=env,stdout=log,stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW)
    state['cli_model_pid']=service.pid
    state['active_step']='documented_cli'
    save()
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen('http://127.0.0.1:11437/api/tags',timeout=2):
                    break
            except OSError:
                time.sleep(.2)
        for name,command in [('list',[shutil.which('ollama'),'list']),('pull',[shutil.which('ollama'),'pull','qwen3:4b'])]:
            with (args.output/(name+'.stdout.log')).open('wb') as out,(args.output/(name+'.stderr.log')).open('wb') as err:
                result=subprocess.run(command,env=env,stdout=out,stderr=err,timeout=120)
            state['steps'].append({'step':name,'exit_code':result.returncode,
                'note':'CLI pull is idempotence verification; first download measured separately from empty store'})
            save()
            if result.returncode:
                raise RuntimeError('Documented CLI command failed')
    finally:
        service.terminate()
        service.wait(timeout=30)
        state['cli_service_stopped']=True
        save()
    state['completed']=True
    state['active_step']=None
    save()


if __name__=='__main__':
    main()
