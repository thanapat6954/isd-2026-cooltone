"""Development/regression probes from inspected pages; not held-out evaluation."""
import argparse
import json
from pathlib import Path
import requests


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='http://127.0.0.1:8000')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = {'scope': 'IT-2560 metadata PDF6/book1 visual review; development regression only', 'cases': []}
    for plan in ('coop', 'no-coop'):
        prefix = 'แผน'+('สหกิจศึกษา' if plan == 'coop' else 'ไม่สหกิจศึกษา')+' '
        for question, field, expected in (('หลักสูตรนี้มีทั้งหมดกี่หน่วยกิต', 'total_credits', 130),
            ('หลักสูตรนี้มีกี่ปี', 'years', 4), ('ชื่อหลักสูตรคืออะไร', 'name_th', 'เทคโนโลยีสารสนเทศ')):
            api = requests.post(a.url+'/api/ask', json={'question': 'หลักสูตร IT 2560 '+prefix+question}, timeout=45)
            frontend = requests.post(a.url+'/ask', json={'curriculum': 'IT', 'version': 'old', 'question': prefix+question}, timeout=45)
            body, ui = api.json(), frontend.json()
            rows = body.get('rows', [])
            value_ok = len(rows) == 1 and (rows[0].get(field) == expected if field != 'name_th'
                                          else str(rows[0].get(field, '')).startswith(expected))
            passed = (api.status_code == frontend.status_code == 200 and value_ok
                and body.get('selected_curricula') == ['IT-2560-'+plan]
                and body.get('answer') == ui.get('answer')
                and rows[0].get('source_file') == 'IT-60.pdf' and rows[0].get('page_number') == 6
                and rows[0].get('printed_page_number') == 1
                and len(ui.get('sources', [])) == 1 and ui['sources'][0].get('page') == 6
                and ui['sources'][0].get('book_page') == 1
                and str(ui['sources'][0].get('section', '')).startswith('IT-60.pdf'))
            result['cases'].append({'profile': 'IT-2560-'+plan, 'question': question, 'passed': passed,
                                    'api_status': api.status_code, 'frontend_status': frontend.status_code,
                                    'api': body, 'frontend': ui})
        response = requests.post(a.url+'/api/ask', json={'question': 'หลักสูตร IT 2565 '+prefix+'หลักสูตรนี้มีกี่ปี'}, timeout=45)
        body = response.json()
        passed = (response.status_code == 200 and body.get('selected_curricula') == ['IT-2565-'+plan]
                  and body.get('rows') and all(r.get('source_file') == 'IT.pdf' for r in body['rows']))
        result['cases'].append({'profile': 'IT-2565-'+plan, 'scope': 'isolation only, not full metadata accuracy',
                                'passed': bool(passed), 'api': body})
    result['summary'] = {'passed': sum(c['passed'] for c in result['cases']), 'n': len(result['cases'])}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(result['summary'])
    return 0 if all(c['passed'] for c in result['cases']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
