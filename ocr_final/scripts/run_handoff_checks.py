"""Save raw shared-pipeline checks per job; resume only identical dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    app, output = a.app_root.resolve(), a.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = list((app/'lab10_fastapi/curriculum_app').glob('*.py'))
    paths += [d.path for d in DatabaseRegistry(app).databases]
    paths += list((ROOT/'tests').glob('*.json'))
    paths += list((ROOT/'tests').glob('test_*.*'))
    paths += list((ROOT/'scripts').glob('*.py'))
    paths += list((ROOT/'scripts').glob('*.ps1'))
    paths += list((ROOT/'frontend').glob('*.*'))
    paths += [ROOT/'scr/ocr_system/lab8b_curriculum_db.py']
    paths += list((app/'work').glob('lab8b_*/lab7b/pred_vlm.json'))
    paths += list((app/'data/input').glob('*.pdf'))
    dependencies = {str(path): sha(path) for path in paths}
    state_path = output/'checks.json'
    state = {'purpose': 'observed regression/provenance, NOT full independent book accuracy',
             'started_utc': datetime.now(timezone.utc).isoformat(), 'dependencies': dependencies, 'jobs': []}
    if a.resume and state_path.exists():
        state = json.loads(state_path.read_text(encoding='utf-8'))
        if state['dependencies'] != dependencies:
            raise ValueError('Dependencies changed; use a new output folder')
    def save():
        stage = state_path.with_suffix('.partial')
        stage.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        stage.replace(state_path)
    env = {**os.environ, 'PYTHONUTF8': '1', 'CURRICULUM_TEST_ROOT': str(app)}
    jobs = [
        ('unit', [sys.executable, '-X', 'utf8', '-m', 'unittest', 'discover', '-s', 'tests', '-v']),
        ('schema', [sys.executable, '-X', 'utf8', 'scr/ocr_system/lab8b_curriculum_db.py', 'selftest']),
        ('frontend', ['node', '--test', 'tests/test_frontend_presentation.mjs']),
        ('gold', [sys.executable, '-X', 'utf8', 'scripts/run_qa_gold.py', '--app-root', str(app), '--runs', '1', '--output', str(output/'gold.json')]),
        ('old2560', [sys.executable, '-X', 'utf8', 'scripts/run_old2560_qa.py', '--app-root', str(app), '--output', str(output/'old2560.json')]),
        ('provenance', [sys.executable, '-X', 'utf8', 'scripts/audit_answer_provenance.py', '--app-root', str(app), '--output', str(output/'provenance.json')]),
        ('version_sets', [sys.executable, '-X', 'utf8', 'scripts/verify_db_version_diff.py', '--app-root', str(app), '--output', str(output/'version_sets.json')]),
    ]
    save()
    done = {j['name'] for j in state['jobs'] if j['exit_code'] == 0}
    for name, command in jobs:
        if name in done:
            continue
        state['running'] = name
        save()
        process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=600)
        state['jobs'].append({'name': name, 'command': command, 'exit_code': process.returncode,
                              'stdout': process.stdout, 'stderr': process.stderr})
        save()
        print(name, 'exit', process.returncode, flush=True)
        if process.returncode:
            print('Stopped after failing check; raw output saved. No data or labels changed.')
            return 1
    state['running'] = None
    state['dependencies_unchanged'] = all(sha(Path(path)) == value for path, value in dependencies.items())
    save()
    return 0 if state['dependencies_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
