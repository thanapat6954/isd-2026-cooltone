"""Kill only our isolated OCR child, preserve checkpoints, then resume real OCR."""
import argparse
import json
import os
import site
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--reuse-job',type=Path)
    parser.add_argument('--reuse-page-job', type=Path, action='append', default=[])
    parser.add_argument('--page', type=int, action='append')
    parser.add_argument('--segments', type=int, choices=(1, 2), default=1)
    parser.add_argument('--prompt-file', type=Path)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new isolated output, never overwrite interruption evidence')
    args.output.mkdir(parents=True)
    raw=args.output/'raw'
    # Kill the actual worker, not the Windows venv launcher parent.
    command=[sys._base_executable,'-X','utf8',str(ROOT/'scripts/extract_manifest_pages.py'),
             '--manifest',str(args.manifest.resolve()),'--source-root',str(args.source_root.resolve()),'--output',str(raw.resolve())]
    if args.reuse_job:
        command.extend(['--reuse-job',str(args.reuse_job.resolve())])
    for reuse in args.reuse_page_job:
        command.extend(['--reuse-page-job', str(reuse.resolve())])
    for page in args.page or []:
        command.extend(['--page', str(page)])
    command.extend(['--segments', str(args.segments)])
    if args.prompt_file:
        command.extend(['--prompt-file', str(args.prompt_file.resolve())])
    record={'scope':'owned real OCR child process only, no live servers/DB changes','command':command}
    checkpoint=args.output/'recovery.json'
    env={**os.environ, 'PYTHONUTF8':'1', 'PYTHONPATH':os.pathsep.join(site.getsitepackages())}
    def save():
        checkpoint.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (args.output/'before-kill.stdout.log').open('w',encoding='utf-8') as out, (args.output/'before-kill.stderr.log').open('w',encoding='utf-8') as err:
        child=subprocess.Popen(command,stdout=out,stderr=err,env=env)
        record['owned_pid']=child.pid
        save()
        until=time.monotonic()+240
        while child.poll() is None:
            path=raw/'manifest-extraction.json'
            if path.exists():
                state=json.loads(path.read_text(encoding='utf-8'))
                if state['processed'] and state['running'] is not None:
                    record['before_kill']={'processed':state['processed'],'running':state['running']}
                    child.terminate()
                    record['killed_exit_code']=child.wait(timeout=15)
                    save()
                    break
            if time.monotonic()>until:
                child.terminate()
                child.wait(timeout=15)
                record['blocked']='No completed-page checkpoint before bounded kill window'
                save()
                return 1
            time.sleep(.1)
        else:
            record['blocked']='Job completed or failed before interruption could be observed'
            record['initial_exit_code']=child.returncode
            save()
            return 1
    with (args.output/'resume.stdout.log').open('w',encoding='utf-8') as out, (args.output/'resume.stderr.log').open('w',encoding='utf-8') as err:
        record['resume_exit_code']=subprocess.run(command+['--resume'],stdout=out,stderr=err,
            env=env).returncode
    final=json.loads((raw/'manifest-extraction.json').read_text(encoding='utf-8'))
    record['final']={'processed_n':len(final['processed']),'pending_n':len(final['pending']),
                     'pending_requested_n':len(final.get('pending_requested', final['pending'])),
                     'failed_attempts_n':len(final['failed']),'source_unchanged':final.get('source_unchanged'),
                     'unique_pages_n':len({p['pdf_page'] for p in final['processed']})}
    # Completion of the bounded request is not completion of the source manifest.
    record['passed']=record['resume_exit_code']==0 and record['final']['pending_requested_n']==0 and record['final']['unique_pages_n']==len(final['processed'])
    save()
    print(json.dumps(record['final']))
    return int(not record['passed'])


if __name__=='__main__':
    raise SystemExit(main())
