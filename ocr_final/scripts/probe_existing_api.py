"""Incremental development probes against an existing server, with no gold answers."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--questions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--curriculum', required=True)
    parser.add_argument('--version', default='latest')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    questions = json.loads(args.questions.read_text(encoding='utf-8'))
    if not isinstance(questions, list) or not all(isinstance(q, str) for q in questions):
        raise ValueError('Only exposed development question strings are accepted')
    identity = {'url': args.url, 'curriculum': args.curriculum, 'version': args.version,
                'question_sha256': hashlib.sha256(args.questions.read_bytes()).hexdigest(),
                'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if args.resume:
        state = json.loads(args.output.read_text(encoding='utf-8'))
        if state['identity'] != identity:
            raise ValueError('Probe identity changed; retain old evidence and use a new output')
    else:
        if args.output.exists():
            raise ValueError('Output exists; use explicit compatible resume or a new path')
        state = {'identity': identity, 'cases': [], 'interpretation': 'Actual outputs, not correctness grades'}
    def save():
        partial = args.output.with_suffix('.partial')
        partial.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        partial.replace(args.output)
    completed = {(case['route'], case['request']['question']) for case in state['cases']}
    for route in ('/api/ask', '/ask'):
        for question in questions:
            if (route, question) in completed:
                continue
            payload = {'question': question}
            if route == '/ask':
                payload.update(curriculum=args.curriculum, version=args.version)
            start = time.perf_counter()
            try:
                response = requests.post(args.url.rstrip('/')+route, json=payload, timeout=60)
                body = response.json()
                # Exclude only verbose schema diagnostics, not answers/rows/SQL.
                body = {key: value for key, value in body.items() if key != 'schemas'}
                case = {'route': route, 'request': payload, 'status': response.status_code, 'body': body}
            except requests.RequestException as exc:
                case = {'route': route, 'request': payload, 'technical_error': str(exc)}
            case['elapsed_ms'] = round((time.perf_counter()-start)*1000, 2)
            state['cases'].append(case)
            save()
    print(json.dumps({'requests': len(state['cases']), 'statuses': [c.get('status') for c in state['cases']]}))


if __name__ == '__main__':
    main()
