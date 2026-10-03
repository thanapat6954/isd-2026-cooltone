"""Run/checkpoint release regressions sequentially, without changing expectations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    a.output_dir = a.output_dir.resolve()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = a.output_dir / 'release_checks.json'
    dependencies = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (a.app_root / 'lab10_fastapi/curriculum_app').glob('*.py')}
    result = {'dependencies': dependencies, 'jobs': [], 'note': 'Sequential jobs; expected failures remain recorded, never changed to pass.'}
    if a.resume and checkpoint.exists():
        result = json.loads(checkpoint.read_text(encoding='utf-8'))
        if result['dependencies'] != dependencies:
            raise ValueError('Runtime changed; choose a new result directory')
    app_args = ['--app-root', str(a.app_root)]
    jobs = [('unit', 'capture_b1_checkpoint.py', app_args),
            ('provenance', 'audit_answer_provenance.py', app_args),
            ('gold', 'run_qa_gold.py', app_args + ['--runs', '1']),
            ('old2560', 'run_old2560_qa.py', app_args),
            ('versions', 'run_version_isolation.py', app_args),
            ('cards', 'verify_study_plans.py', app_args),
            ('frozen', 'verify_db_only_live.py', app_args + ['--mode', 'frozen', '--runs', '3']),
            ('unknown', 'verify_db_only_live.py', app_args + ['--mode', 'unknown'])]
    done = {job['name'] for job in result['jobs'] if job.get('completed')}
    def save():
        checkpoint.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save()
    for name, script, args in jobs:
        if name in done:
            continue
        command = [sys.executable, str(ROOT / 'scripts' / script), *args, '--output', str(a.output_dir / (name + '.json'))]
        partial = (a.output_dir / (name + '.json')).exists()
        if a.resume and partial and name in {'gold', 'old2560', 'cards', 'frozen', 'unknown'}:
            command.append('--resume')
        entry = {'name': name, 'command': command, 'completed': False}
        result['jobs'].append(entry)
        save()
        print('Starting', name, flush=True)
        with (a.output_dir / (name + '.stdout.log')).open('w', encoding='utf-8') as out, (a.output_dir / (name + '.stderr.log')).open('w', encoding='utf-8') as err:
            proc = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err, timeout=1800)
        entry.update(exit_code=proc.returncode, completed=True)
        save()
        print(name, 'exit', proc.returncode, flush=True)
    result['runtime_unchanged'] = dependencies == {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (a.app_root / 'lab10_fastapi/curriculum_app').glob('*.py')}
    save()
    return int(not result['runtime_unchanged'] or any(job['exit_code'] for job in result['jobs'] if job.get('completed')))


if __name__ == '__main__':
    raise SystemExit(main())
