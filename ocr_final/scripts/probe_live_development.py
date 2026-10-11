"""Replay exposed development categories against LIVE, with dependency guards."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--questions', type=Path, required=True)
    parser.add_argument('--category', action='append', required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--profile', action='append')
    args = parser.parse_args()
    from lab10_fastapi.curriculum_app.database import DatabaseRegistry
    import requests
    registry = DatabaseRegistry(args.app_root)
    profiles = registry.active_catalogs
    if args.profile:
        profiles = [p for p in profiles if p.curriculum_name in args.profile]
        if set(args.profile) != {p.curriculum_name for p in profiles}:
            raise ValueError('Unknown recorded profile')
    questions = [q for q in json.loads(args.questions.read_text(encoding='utf-8'))['cases']
                 if q['category'] in args.category]
    if set(args.category) != {q['category'] for q in questions}:
        raise ValueError('Unknown development category')
    dependencies = {str(p): digest(p) for p in [args.questions.resolve()] +
                    [d.path for d in profiles] +
                    list((args.app_root / 'lab10_fastapi/curriculum_app').glob('*.py'))}
    args.output.mkdir(parents=True, exist_ok=args.resume)
    path = args.output / 'results.json'
    if args.resume:
        result = json.loads(path.read_text(encoding='utf-8'))
        if result['dependencies'] != dependencies or result['categories'] != args.category:
            raise ValueError('Dependencies changed: retain evidence and use new output')
    else:
        result = {'scope': 'Actual LIVE exposed development replay, not held-out/source accuracy',
                  'url': args.url, 'dependencies': dependencies, 'categories': args.category, 'cases': []}
    completed = {c['id'] for c in result['cases']}
    for profile in profiles:
        program = (profile.program_id or 'legacy').split('-')[0]
        prefix = ('ฐานข้อมูลเดิม legacy' if not profile.program_id else
                  f"หลักสูตร {program} {profile.curriculum_version} " +
                  ('ไม่เข้าร่วมสหกิจ' if profile.plan == 'no-coop' else 'สหกิจ'))
        for question in questions:
            text = prefix + ': ' + question['question']
            for route in ('/api/ask', '/ask'):
                identity = f'{profile.curriculum_name}-{question["category"]}-{route}'
                if identity in completed:
                    continue
                payload = {'question': text}
                if route == '/ask':
                    payload.update(curriculum=program, version=(
                        'all versions' if not profile.program_id else
                        'old' if profile.curriculum_version == 2560 else 'latest'))
                started = time.perf_counter()
                try:
                    response = requests.post(args.url + route, json=payload, timeout=60)
                    status, body = response.status_code, response.json()
                except (requests.RequestException, ValueError) as exc:
                    status, body = None, {'transport_error': str(exc)}
                result['cases'].append({'id': identity, 'profile': profile.curriculum_name,
                    'category': question['category'], 'route': route, 'question': text,
                    'request': payload, 'status': status, 'body': body,
                    'elapsed_ms': round((time.perf_counter()-started)*1000, 2),
                    'judgment': 'pending manual evidence review'})
                result['dependencies_unchanged'] = all(digest(Path(p)) == h for p,h in dependencies.items())
                result['coverage'] = {'unique_wordings': len(questions), 'reasoning_categories': len(args.category),
                    'scoped_questions': len({(c['profile'],c['question']) for c in result['cases']}),
                    'http_requests': len(result['cases'])}
                partial = path.with_suffix('.partial')
                partial.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                partial.replace(path)
                if not result['dependencies_unchanged']:
                    raise ValueError('LIVE dependency changed during replay')
                print(identity, status, flush=True)


if __name__ == '__main__':
    main()
