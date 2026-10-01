"""Save real HTTP evidence for frontend/API startup, without changing databases."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:8000')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = []
    for path in ('/', '/frontend/app.js', '/openapi.json', '/api/health'):
        response = requests.get(args.url + path, timeout=30)
        results.append({'method': 'GET', 'path': path, 'status': response.status_code,
                        'final_url': response.url,
                        'data': response.json() if path == '/api/health' else None})
    payload = {'question': 'ปี 4 ภาคการศึกษาที่ 2 มีวิชาอะไรบ้าง',
               'curriculum': 'BIT', 'version': 'old'}
    response = requests.post(args.url + '/ask', json=payload, timeout=60)
    results.append({'method': 'POST', 'path': '/ask', 'request': payload,
                    'status': response.status_code, 'data': response.json()})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'captured_at': datetime.now(timezone.utc).isoformat(),
                                      'checks': results}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print([(item['method'], item['path'], item['status']) for item in results])
    if any(item['status'] != 200 for item in results):
        raise SystemExit(1)
    if not results[-1]['data'].get('sources'):
        raise SystemExit('Expected database-backed citations for the smoke question')


if __name__ == '__main__':
    main()
