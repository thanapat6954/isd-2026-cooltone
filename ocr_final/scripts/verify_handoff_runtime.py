"""Read-only readiness, PDF transport and repository documentation-link checks."""
import argparse
import json
from pathlib import Path
import re
import requests


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='http://127.0.0.1:8000')
    p.add_argument('--repository', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = {'scope': 'Transport/readiness/link checks, not visual PDF-page or answer correctness', 'pdf_routes': [], 'links': []}
    health = requests.get(a.url+'/api/health', timeout=10)
    result['health'] = {'status': health.status_code, 'body': health.json()}
    result['frontend_status'] = requests.get(a.url+'/frontend/', timeout=10).status_code
    for source in ('AI.pdf','DSBA.pdf','DSBA-60.pdf','IT.pdf','IT-60.pdf','BIT-65.pdf','BIT-60.pdf'):
        response = requests.get(a.url+'/api/source/'+source, headers={'Range':'bytes=0-7'}, timeout=10)
        result['pdf_routes'].append({'file': source, 'status': response.status_code, 'content_type': response.headers.get('content-type'),
                                     'content_range': response.headers.get('content-range'), 'pdf_signature': response.content.startswith(b'%PDF'),
                                     'passed': response.status_code == 206 and response.content.startswith(b'%PDF')})
    for relative in ('README.md', 'ocr_final/frontend/README.md'):
        path = a.repository/relative
        text = path.read_text(encoding='utf-8')
        targets = re.findall(r'\]\(([^)]+)\)', text)
        targets += re.findall(r'(?:src|href)=[\"\']([^\"\']+)[\"\']', text)
        for target in targets:
            if target.startswith(('https://','http://','#')):
                continue
            destination = (path.parent/target.split('#')[0]).resolve()
            result['links'].append({'document': relative, 'link': target, 'exists': destination.exists(),
                                    'inside_repository': destination.is_relative_to(a.repository.resolve())})
        if re.search(r'C:[/\\]Users|OneDrive', text):
            # OneDrive is legitimate troubleshooting prose; only absolute paths are forbidden.
            result.setdefault('absolute_personal_paths', {})[relative] = bool(re.search(r'C:[/\\]Users', text))
    result['passed'] = health.status_code == 200 and result['frontend_status'] == 200 and all(r['passed'] for r in result['pdf_routes']) and all(r['exists'] and r['inside_repository'] for r in result['links']) and not any(result.get('absolute_personal_paths', {}).values())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Passed:', result['passed'], 'PDF routes:', len(result['pdf_routes']), 'local links:', len(result['links']))
    return int(not result['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
