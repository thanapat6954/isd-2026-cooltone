"""Checkpoint a backed-up rebuild from separate, hash-guarded reviewed ingest."""
import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_lab8b import PROFILES
from audit_old2560 import PROFILES as OLD_PROFILES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--profile', choices=[p.replace('_', '-') for p in OLD_PROFILES], required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
    if {p['profile'] for p in baseline['profiles']} != {p.replace('_', '-') for p in OLD_PROFILES}:
        raise ValueError('All six baseline profiles must be recorded before any data fix')
    data = json.loads(args.input.read_text(encoding='utf-8'))
    if not data.get('reviewed_ingest_corrections'):
        raise ValueError('Refuse an input without a separately reviewed correction')
    app = args.app_root.resolve()
    config = PROFILES[args.profile]
    folder = app / 'work' / ('lab8b_' + args.profile.replace('-', '_'))
    db = folder / 'curriculum.db'
    frozen = folder / 'lab7b/pred_vlm.json'
    original_hash = hashlib.sha256(frozen.read_bytes()).hexdigest()
    for review in data['reviewed_ingest_corrections']:
        if review['status'] != 'visually_verified' or hashlib.sha256((app / 'data/input' / review['source_file']).read_bytes()).hexdigest() != review['source_sha256']:
            raise ValueError('Review/source SHA mismatch')
    tag = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    backup = app / 'work/backups/old2560-review' / tag / (folder.name + '.db')
    backup.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True)
    destination = sqlite3.connect(backup)
    try:
        source.execute('PRAGMA query_only=ON')
        source.backup(destination)
        integrity = destination.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok':
            raise ValueError('Backup integrity failed')
    finally:
        source.close()
        destination.close()
    result = {'profile': args.profile, 'backup': str(backup), 'backup_integrity': integrity,
              'backup_sha256': hashlib.sha256(backup.read_bytes()).hexdigest(),
              'input': str(args.input), 'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
              'frozen_input_sha256': original_hash, 'runs': []}
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save()
    converted = folder / 'reviewed_curriculum_v2.json'
    lab8 = ROOT / 'scr/ocr_system/lab8b_curriculum_db.py'
    commands = [
        [sys.executable, str(lab8), 'import-lab7b', '-i', str(args.input), '-o', str(converted),
         '--program-id', config['program_id'], '--program-name', config['program_name'],
         '--total-credits', str(config['total_credits']), '--years', '4', '--curriculum-version', '2560',
         '--target-plan', config['target_plan'], '--plan', config['target_plan'].replace('_', '-'),
         '--printed-page-offset', str(config['printed_page_offset'])],
        [sys.executable, str(lab8), 'load', '-i', str(converted), '-d', str(db), '--replace'],
        [sys.executable, str(ROOT / 'scripts/ingest_prerequisite_reviews.py'), '--app-root', str(app),
         '--database', str(db), '--reviews', str(ROOT / 'data/ground_truth/prerequisite_source_reviews.json'),
         '--output', str(args.output.with_name(args.output.stem + '_prerequisites.json')), '--apply'],
        [sys.executable, str(lab8), 'verify', '-d', str(db), '-o', str(folder / 'reviewed_verify_v2.json')],
    ]
    commands.insert(-1,[sys.executable,str(ROOT/'scripts/ingest_name_reviews.py'),'--app-root',str(app),
                       '--database',str(db),'--apply','--output',str(args.output.with_name(args.output.stem+'_names.json'))])
    for command in commands:
        result['next_command'] = command
        save()
        run = subprocess.run(command, cwd=app, capture_output=True, text=True, encoding='utf-8')
        result['runs'].append({'command': command, 'exit_code': run.returncode,
                               'stdout': run.stdout, 'stderr': run.stderr})
        save()
        print(args.profile, command[2], 'exit', run.returncode)
        if run.returncode:
            raise RuntimeError(f'Failed command; raw output in {args.output}; backup retained')
    result['frozen_input_unchanged'] = original_hash == hashlib.sha256(frozen.read_bytes()).hexdigest()
    result['next_command'] = None
    save()
    if not result['frozen_input_unchanged']:
        raise ValueError('Frozen input changed unexpectedly')


if __name__ == '__main__':
    main()
