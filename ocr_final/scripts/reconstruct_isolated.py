"""Resume full parser/build jobs in a separate code snapshot, never live work/."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_lab8b import PROFILES


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def latest_results(records):
    """A failed attempt stays recorded but must not prevent a real resume."""
    return {record['profile']: record for record in records}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--output-root', type=Path, required=True)
    p.add_argument('--profiles', nargs='+', choices=list(PROFILES), default=list(PROFILES))
    p.add_argument('--fresh-ocr', action='store_true', help='Use real VLM extraction, not saved OCR; may take hours')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--manifest-dir', type=Path, help='Reviewed selections: raw book OCR stays separate from study-plan parsing')
    p.add_argument('--reuse-job', type=Path, action='append', default=[])
    a = p.parse_args()
    source, output = a.source_root.resolve(), a.output_root.resolve()
    if a.manifest_dir and not a.fresh_ocr:
        raise ValueError('Manifest extraction requires --fresh-ocr; cached pages may still be reused with valid hashes')
    if output == source or source in output.parents or output == ROOT or ROOT in output.parents:
        raise ValueError('Output must be outside both application roots')
    protected = [*source.glob('work/lab8b_*/curriculum.db'), *source.glob('work/lab8b_*/lab7b/pred_vlm.json'),
                 *source.glob('work/lab8b_*/lab7b/intermediate_vlm.md'), *source.glob('data/input/*.pdf')]
    dependencies = {str(f): sha(f) for f in protected}
    code = [*ROOT.glob('scripts/*.py'), *ROOT.glob('scr/ocr_system/*.py'), *ROOT.glob('lab10_fastapi/curriculum_app/*.py'), ROOT/'run_lab8b.py']
    code += list((ROOT/'data/source_reviews').rglob('*.json'))
    dependencies.update({str(f): sha(f) for f in code})
    if a.manifest_dir:
        for book in {PROFILES[name]['input'].name for name in a.profiles}:
            manifest = (a.manifest_dir/(Path(book).stem+'.json')).resolve()
            dependencies[str(manifest)] = sha(manifest)
    configuration = {name: os.environ.get(name) for name in
        ('LAB7_MODEL_OCR','LAB7_MODEL_TEXT','LAB7_DPI','LAB7_CHUNK','LAB7B_NUM_CTX',
         'LAB7B_NUM_PREDICT','LAB7B_OCR_NUM_CTX','LAB7B_OCR_NUM_PREDICT','LAB7B_OCR_TEMPERATURE','LAB7B_OCR_RETRIES','OLLAMA_HOST')}
    configuration['manifest_dir'] = str(a.manifest_dir.resolve()) if a.manifest_dir else None
    configuration['reuse_jobs'] = [str(job.resolve()) for job in a.reuse_job]
    state_path = output/'reconstruction.json'
    app = output/'app'
    if a.resume:
        state = json.loads(state_path.read_text(encoding='utf-8'))
        if state['dependencies'] != dependencies or state['fresh_ocr'] != a.fresh_ocr or state.get('configuration') != configuration:
            raise ValueError('Dependencies changed; use a new output root')
    else:
        output.mkdir(parents=True, exist_ok=False)
        app.mkdir()
        for folder in ('scr','scripts','lab10_fastapi','frontend','data/source_reviews'):
            shutil.copytree(ROOT/folder, app/folder, ignore=shutil.ignore_patterns('__pycache__','.env'))
        for filename in ('run_lab8b.py',):
            shutil.copy2(ROOT/filename, app/filename)
        (app/'data/input').mkdir(parents=True)
        for pdf in source.glob('data/input/*.pdf'):
            # Read-only consumers only; hardlinks avoid duplicating large books.
            os.link(pdf, app/'data/input'/pdf.name)
        for profile in PROFILES.values():
            folder = profile['out'].relative_to(ROOT)
            pred = source/folder/'lab7b/pred_vlm.json'
            if pred.exists():
                target = app/folder/'lab7b/pred_vlm.json'
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(pred, target)
                markdown = pred.with_name('intermediate_vlm.md')
                if markdown.exists():
                    shutil.copy2(markdown, target.with_name(markdown.name))
        state = {'scope': 'fresh OCR through build' if a.fresh_ocr else 'saved OCR through full configured parser/build; NOT fresh OCR or independent accuracy',
                 'fresh_ocr': a.fresh_ocr, 'configuration':configuration, 'dependencies': dependencies, 'profiles': [], 'running': None}
    def save():
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    save()
    if a.manifest_dir:
        for book in sorted({PROFILES[name]['input'].name for name in a.profiles}):
            manifest = a.manifest_dir/(Path(book).stem+'.json')
            raw_output = output/'raw_books'/Path(book).stem
            raw_output.parent.mkdir(exist_ok=True)
            command = [sys.executable, '-X', 'utf8', str(app/'scripts/extract_manifest_pages.py'),
                       '--manifest', str(manifest.resolve()), '--source-root', str(app), '--output', str(raw_output)]
            if raw_output.exists():
                command.append('--resume')
            for reuse in a.reuse_job:
                command.extend(['--reuse-job', str(reuse.resolve())])
            state['running'] = 'raw_book:'+book
            save()
            result = subprocess.run(command, env={**os.environ, 'PYTHONUTF8':'1'},
                                    stdout=(output/(book+'.raw.stdout.log')).open('a',encoding='utf-8'),
                                    stderr=(output/(book+'.raw.stderr.log')).open('a',encoding='utf-8'))
            state.setdefault('raw_books', []).append({'source_file':book, 'exit_code':result.returncode,
                                                       'page_state':str(raw_output/'manifest-extraction.json')})
            save()
            if result.returncode:
                return result.returncode
            # Only configured plan pages enter the existing plan parser. Other raw
            # descriptions/regulations remain separate, never coerced into course rows.
            for name in a.profiles:
                if PROFILES[name]['input'].name == book:
                    destination = app/PROFILES[name]['out'].relative_to(ROOT)/'lab7b/ocr_page_checkpoints'
                    destination.mkdir(parents=True, exist_ok=True)
                    for cache in (raw_output/'ocr_page_checkpoints').glob('*.json'):
                        shutil.copy2(cache, destination/cache.name)
    completed = {name for name, result in latest_results(state['profiles']).items() if result['exit_code'] == 0}
    env = {**os.environ, 'PYTHONUTF8':'1', 'CURRICULUM_DATABASE_ROOT':str(app)}
    for profile in a.profiles:
        if profile in completed:
            continue
        state['running'] = profile
        save()
        command = [sys.executable,'-X','utf8','run_lab8b.py','--program',profile,'--skip-eval']
        if not a.fresh_ocr:
            command.append('--skip-lab7')
        start = time.perf_counter()
        attempt = 1 + sum(r['profile']==profile for r in state['profiles'])
        log_name = profile if attempt == 1 else f'{profile}-attempt-{attempt}'
        with (output/f'{log_name}.stdout.log').open('w',encoding='utf-8') as stdout, (output/f'{log_name}.stderr.log').open('w',encoding='utf-8') as stderr:
            result = subprocess.run(command,cwd=app,env=env,stdout=stdout,stderr=stderr)
        state['profiles'].append({'profile':profile,'exit_code':result.returncode,'seconds':round(time.perf_counter()-start,2),
                                  'attempt':attempt,'command':command,'stdout':f'{log_name}.stdout.log','stderr':f'{log_name}.stderr.log'})
        save()
        print(profile, 'exit', result.returncode, flush=True)
    state['running'] = None
    state['protected_unchanged'] = all(sha(Path(f))==h for f,h in dependencies.items())
    save()
    return int(any(r['exit_code'] for r in latest_results(state['profiles']).values()) or not state['protected_unchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
