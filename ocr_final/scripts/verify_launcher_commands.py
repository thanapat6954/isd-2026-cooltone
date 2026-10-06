"""Exercise documented launcher commands on an isolated app, without changing DBs."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import requests


def listening(port):
    with socket.socket() as connection:
        return connection.connect_ex(('127.0.0.1', port)) == 0


def normalize_cli_output(value):
    # PowerShell wraps error messages with a margin marker at console width.
    return ' '.join(value.replace('|', ' ').split())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8001)
    parser.add_argument('--occupied-port', type=int, default=8000)
    args = parser.parse_args()
    app, output = args.app_root.resolve(), args.output.resolve()
    if args.port == args.occupied_port or listening(args.port):
        raise ValueError('Test port must be unused and distinct; no process stopped')
    expected = str(app/'scr/ocr_system/lab8b_curriculum_db.py').lower()
    original = requests.get(f'http://127.0.0.1:{args.occupied_port}/api/health', timeout=5).json()
    if original.get('lab8b_module', '').lower() == expected:
        raise ValueError('Occupied port must belong to a different application folder')
    def hashes():
        return {str(p.relative_to(app)): hashlib.sha256(p.read_bytes()).hexdigest() for p in app.rglob('*.db')}
    before = hashes()
    result = {'scope': 'Launcher safety/start/idempotency/stop only, not answer accuracy', 'steps': []}
    output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    def run(name, script, port, expected_exit):
        command = ['pwsh', '-NoProfile', '-File', str(app/'scripts'/script), '-Port', str(port)]
        stdout_path, stderr_path = output.parent/(name+'.stdout.log'), output.parent/(name+'.stderr.log')
        with stdout_path.open('w', encoding='utf-8') as stdout, stderr_path.open('w', encoding='utf-8') as stderr:
            response = subprocess.run(command, cwd=app, stdout=stdout, stderr=stderr, timeout=120)
        step = {'name': name, 'command': command, 'exit_code': response.returncode,
                'stdout': stdout_path.read_text(encoding='utf-8'), 'stderr': stderr_path.read_text(encoding='utf-8')}
        step['passed'] = response.returncode == expected_exit
        result['steps'].append(step)
        save()
        if not step['passed']:
            raise RuntimeError(name+' failed; see raw logs')
    run('wrong_root_guard', 'start_web.ps1', args.occupied_port, 1)
    if 'No process was stopped' not in normalize_cli_output(result['steps'][-1]['stderr']):
        raise RuntimeError('Wrong-root rejection did not confirm preservation')
    run('alternate_start', 'start_web.ps1', args.port, 0)
    health = requests.get(f'http://127.0.0.1:{args.port}/api/health', timeout=5).json()
    if health.get('lab8b_module', '').lower() != expected or not health.get('ollama_ready'):
        raise RuntimeError('Unexpected backend identity/readiness; no unrelated server stopped')
    run('already_running', 'start_web.ps1', args.port, 0)
    if 'Backend already running' not in result['steps'][-1]['stdout']:
        raise RuntimeError('Repeated start did not identify the existing backend')
    run('alternate_stop', 'stop_web.ps1', args.port, 0)
    result['test_port_stopped'] = not listening(args.port)
    after = requests.get(f'http://127.0.0.1:{args.occupied_port}/api/health', timeout=5).json()
    result['original_application_preserved'] = original.get('lab8b_module') == after.get('lab8b_module')
    result['database_count'] = len(before)
    result['database_hashes_unchanged'] = before == hashes()
    result['passed'] = all(s['passed'] for s in result['steps']) and all(result[k] for k in
        ('test_port_stopped', 'original_application_preserved', 'database_hashes_unchanged'))
    save()
    print(json.dumps({k: result[k] for k in ('passed', 'database_count', 'database_hashes_unchanged', 'test_port_stopped')}, indent=2))
    return int(not result['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
