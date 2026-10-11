"""Record exact server identity and bounded development API/citation checks."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--refresh-process-identity', action='store_true', help='Refresh process evidence without repeating API questions')
    args = parser.parse_args()
    app = args.app_root.resolve()
    if not args.refresh_process_identity:
        args.output.mkdir(parents=True, exist_ok=False)
    url = f'http://127.0.0.1:{args.port}'
    state = {'app_root': str(app), 'url': url, 'cases': [], 'citations': [],
             'scope': 'development startup/API/source-renderer checks; NOT visible browser verification'}
    if args.refresh_process_identity:
        state = json.loads((args.output/'result.json').read_text(encoding='utf-8'))
        if state['app_root'] != str(app) or state['url'] != url:
            raise ValueError('Identity refresh must use the original app and port')

    def save():
        (args.output/'result.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')

    health = requests.get(url+'/api/health', timeout=15)
    health.raise_for_status()
    state['health'] = health.json()
    expected = app/'scr/ocr_system/lab8b_curriculum_db.py'
    if Path(state['health']['lab8b_module']).resolve() != expected.resolve():
        save()
        raise ValueError('Wrong folder serves the selected port')
    command = "[Console]::OutputEncoding = [Text.UTF8Encoding]::new(); Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn' -and $_.Name -match 'python' } | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3"
    processes = subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True, text=True, encoding='utf-8')
    processes.check_returncode()
    state['process_inventory_raw'] = processes.stdout
    state['process_record'] = json.loads((app/f'work/web/process-{args.port}.json').read_text(encoding='utf-8-sig'))
    state['process_inventory'] = json.loads(processes.stdout)
    state['conflicting_ports'] = {}
    for port in (8000, 8003, 8010):
        try:
            response = requests.get(f'http://127.0.0.1:{port}/api/health', timeout=10)
            state['conflicting_ports'][str(port)] = {'status': response.status_code, 'health': response.json()}
        except requests.RequestException as exc:
            state['conflicting_ports'][str(port)] = {'error': str(exc)}
    if args.refresh_process_identity:
        state['identity_refresh_note'] = 'Initial PowerShell stdout decode failed; fixed UTF8 capture. Existing API/citation results retained, not repeated.'
        save()
        print('Process and readiness identities refreshed; API requests not repeated')
        return
    before = {str(p.relative_to(app)): hashlib.sha256(p.read_bytes()).hexdigest() for p in app.rglob('curriculum.db')}
    state['runtime_hashes'] = {str(p.relative_to(app)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for folder in ('lab10_fastapi/curriculum_app', 'frontend', 'scripts')
                              for p in (app/folder).glob('*') if p.is_file() and p.suffix in ('.py', '.js', '.ps1')}
    save()
    questions = [
        ('IT', 'old', 'IT พ.ศ.2560 แผนไม่สหกิจศึกษา หลักสูตรนี้มีกี่ปี'),
        ('BIT', 'latest', 'BIT พ.ศ.2565 แผนไม่สหกิจศึกษา วิชารหัส 06036123 ชื่ออะไรและมีกี่หน่วยกิต'),
    ]
    for curriculum, version, question in questions:
        for route in ('/api/ask', '/ask'):
            payload = {'question': question}
            if route == '/ask':
                payload.update(curriculum=curriculum, version=version)
            started = time.perf_counter()
            response = requests.post(url+route, json=payload, timeout=60)
            case = {'route': route, 'request': payload, 'status': response.status_code,
                    'elapsed_ms': round((time.perf_counter()-started)*1000, 2), 'response': response.json()}
            state['cases'].append(case)
            save()
            response.raise_for_status()
            if route != '/ask':
                continue
            for citation in case['response'].get('sources', [])[:1]:
                files = [p.name for p in (app/'data/input').glob('*.pdf') if p.name in citation['section']]
                if len(files) != 1:
                    raise ValueError('Citation does not identify one source PDF')
                filename, page = files[0], citation['page']
                info = requests.get(url+f'/api/source-info/{filename}?page={page}', timeout=30)
                info.raise_for_status()
                image = requests.get(url+f'/api/source-page/{filename}/{page}', timeout=60)
                image.raise_for_status()
                if not image.content.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValueError('Source page is not PNG')
                destination = args.output/f'{filename}-{page}.png'
                destination.write_bytes(image.content)
                state['citations'].append({'citation': citation, 'info': info.json(), 'image': str(destination),
                    'book_page_matches': citation.get('book_page') == info.json().get('printed_page'),
                    'viewer_url': url+f'/source-viewer/{filename}?page={page}',
                    'source_sha256': hashlib.sha256((app/'data/input'/filename).read_bytes()).hexdigest()})
                save()
    state['db_unchanged'] = before == {str(p.relative_to(app)): hashlib.sha256(p.read_bytes()).hexdigest() for p in app.rglob('curriculum.db')}
    state['frontend_status'] = requests.get(url+'/frontend/', timeout=15).status_code
    state['completed'] = True
    save()
    print(json.dumps({'requests': len(state['cases']), 'statuses': [c['status'] for c in state['cases']],
                      'citation_checks': len(state['citations']), 'db_unchanged': state['db_unchanged']}))


if __name__ == '__main__':
    main()
