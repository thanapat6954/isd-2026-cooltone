"""Record read-only UI release checks; browser observations must be supplied separately."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--previous-gold', type=Path, required=True)
    parser.add_argument('--node', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    app = args.app_root.resolve()
    evidence = args.evidence.resolve()
    observations = json.loads((evidence / 'ui_checks.json').read_text(encoding='utf-8'))
    gold = json.loads((evidence / 'gold.json').read_text(encoding='utf-8'))
    previous = json.loads(args.previous_gold.read_text(encoding='utf-8'))
    result = {'purpose': 'UI release regression, not new curriculum accuracy or source-fidelity proof'}
    command = [str(args.node), '--test', 'tests/test_frontend_presentation.mjs']
    process = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=30)
    result['presentation_tests'] = {'command': command, 'exit_code': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr}
    files = ['frontend/index.html', 'frontend/style.css', 'frontend/app.js', 'frontend/presentation.mjs',
             'frontend/fonts/NotoSansThai-variable.ttf', 'frontend/fonts/OFL.txt',
             'tests/test_frontend_presentation.mjs', 'scripts/verify_ui_refinement.py', 'DESIGN.md']
    result['deployment'] = [{'path': file, 'bytes': (root / file).stat().st_size, 'sha256': digest(root / file),
                             'live_matches': digest(root / file) == digest(app / file)} for file in files]
    result['preserved_dependencies'] = {
        'backend_code_unchanged_from_previous_verified_gold': gold['dependencies']['code'] == previous['dependencies']['code'],
        'databases_unchanged_from_previous_verified_gold': gold['dependencies']['databases'] == previous['dependencies']['databases'],
        'gold_unchanged': gold['gold_sha256'] == previous['gold_sha256'],
        'database_n': len(gold['dependencies']['databases']),
        'current_database_hashes_still_match': all(digest(app / file) == sha for file, sha in gold['dependencies']['databases'].items()),
        'current_backend_hashes_still_match': all(digest(app / 'lab10_fastapi/curriculum_app' / file) == sha for file, sha in gold['dependencies']['code'].items()),
    }
    result['gold_summary'] = gold.get('summary')
    result['pdf_routes'] = []
    urls = sorted({link['href'] for check in observations for link in check.get('links', []) if isinstance(link, dict)} |
                  {link for check in observations for link in check.get('links', []) if isinstance(link, str)})
    by_file = {urlparse(url).path.rsplit('/', 1)[-1]: url for url in urls}
    for file, url in by_file.items():
        with requests.get(url.split('#')[0], headers={'Range': 'bytes=0-3'}, stream=True, timeout=15) as response:
            first_bytes = next(response.iter_content(4), b'')
            result['pdf_routes'].append({'file': file, 'url': url, 'status': response.status_code,
                                         'content_type': response.headers.get('Content-Type'),
                                         'pdf_signature': first_bytes == b'%PDF'})
    desktop = next(check for check in observations if check['case'] == 'desktop IT latest plan')
    response = requests.post('http://127.0.0.1:8000/ask', json={'curriculum': 'IT', 'version': 'latest',
                             'question': 'ปี 2 ภาคการศึกษาที่ 2 มีวิชาอะไรบ้าง'}, timeout=30)
    response.raise_for_status()
    data = response.json()
    rows = [row for card in data['study_plan']['cards'] for section in card['sections'] for row in section['rows']]
    matches = []
    for row, rendered in zip(rows, desktop['rows']):
        code = row.get('raw_code') or row.get('code_pattern') or row.get('code')
        name = row.get('name_th') or row.get('name_en')
        matches.append({'code': code, 'name': name, 'code_present': not code or code in rendered,
                        'name_present': not name or name in rendered,
                        'credits_present': row.get('credits') is None or str(row['credits']) in rendered,
                        'recorded_text': rendered})
    result['plan_rendering'] = {'api_status': response.status_code, 'api_rows': len(rows),
                                'ui_rows': len(desktop['rows']), 'matches': matches,
                                'all_match': len(rows) == len(desktop['rows']) and all(m['code_present'] and m['name_present'] and m['credits_present'] for m in matches)}
    colors = next(check['colors'] for check in observations if check['case'] == 'final mobile table and colors')
    def luminance(color):
        channels = [int(value) / 255 for value in re.findall(r'\d+', color)[:3]]
        linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in channels]
        return sum(value * weight for value, weight in zip(linear, [.2126, .7152, .0722]))
    def ratio(first, second):
        light, dark = sorted([luminance(first), luminance(second)], reverse=True)
        return round((light + .05) / (dark + .05), 2)
    result['rendered_contrast'] = {role: ratio(colors[role], 'rgb(255, 255, 255)') for role in ['body', 'muted', 'link']}
    result['rendered_contrast']['primary_button'] = ratio(colors['button'], colors['buttonBackground'])
    selectors = [check for check in observations if check['case'] == 'selector and submission']
    by_case = {check['case']: check for check in observations}
    result['ui_observation_checks'] = {
        'all_available_selector_combinations': len(selectors) == 10 and all(check['state'] == 'success' and check['context'].startswith(check['program'] + ' · ') for check in selectors),
        'loading_locks_controls': by_case['real loading']['state'] == 'loading' and by_case['real loading']['disabled'] and by_case['real loading']['busy'] == 'true',
        'insufficient_evidence_shows_warning': by_case['insufficient evidence']['sources'] == '0 แหล่ง' and by_case['insufficient evidence']['warning'],
        'validation_focuses_input': by_case['empty validation']['state'] == 'error' and by_case['empty validation']['invalid'] == 'true' and by_case['empty validation']['focus'] == 'question-input',
        'network_error_retains_question': by_case['real backend disconnected']['state'] == 'error' and by_case['real backend disconnected']['retry'] and bool(by_case['real backend disconnected']['input']),
        'retry_recovers': by_case['real retry recovery']['state'] == 'success',
        'timeout_retains_question': by_case['real cold model timeout']['state'] == 'error' and by_case['real cold model timeout']['retry'] and bool(by_case['real cold model timeout']['input']),
        'Shift_Enter_preserves_newline': by_case['Shift Enter']['input'].endswith('\n'),
        'details_keyboard': by_case['mobile details keyboard']['open'],
        'answer_identity_does_not_follow_selector': by_case['answer identity survives selector change']['selected'] == 'IT' and by_case['answer identity survives selector change']['answerContext'].startswith('DSBA · '),
        'long_answer_history_cap': by_case['L3 long answer Enter submit']['characters'] > 3000 and by_case['L3 long answer Enter submit']['historyCount'] == 5,
        'no_narrow_overflow': by_case['320px long plan']['scrollWidth'] <= 320 and by_case['768px plan']['scrollWidth'] <= 768 and by_case['mobile long answer']['documentWidth'] <= 390,
        'citation_touch_targets': all(height >= 44 for height in by_case['final mobile table and colors']['sourceTargets']),
    }
    result['audit_report_summaries'] = []
    for report in sorted((evidence / 'audit_reports').glob('audit_*.md')):
        text = report.read_text(encoding='utf-8')
        summary = text.split('## Summary', 1)[-1].split('## HIGH', 1)[0].strip()
        high = text.split('## HIGH', 1)[-1].split('\n## ', 1)[0]
        statuses = re.findall(r'^- (FAIL|NEEDS_REVIEW|SKIPPED) ', high, flags=re.MULTILINE)
        result['audit_report_summaries'].append({'report': report.name, 'summary': summary,
                                                'high': {status: statuses.count(status) for status in ['FAIL', 'NEEDS_REVIEW', 'SKIPPED']}})
    result['unverified'] = ['In-app PDF viewer rendered blank; routes and exact URLs checked, not visible PDF page rendering.',
                            'Physical phones, screen readers, true browser 200% zoom and OS reduced-motion setting were not exercised.',
                            'Cold open-ended model request timed out at 30 seconds; UI handling verified, model response not verified.',
                            'Full book/source fidelity, legacy selector and source-blocked L4 remain previous audit limitations.']
    booleans = [value for key, value in result['preserved_dependencies'].items() if key != 'database_n']
    result['passed'] = process.returncode == 0 and all(item['live_matches'] for item in result['deployment']) and all(booleans) and result['plan_rendering']['all_match'] and all(item['pdf_signature'] and item['status'] in (200, 206) for item in result['pdf_routes']) and all(value >= 4.5 for value in result['rendered_contrast'].values()) and all(result['ui_observation_checks'].values())
    (evidence / 'release_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'presentation_exit': process.returncode, 'deployment_n': len(files),
                      'preserved': result['preserved_dependencies'], 'pdf_routes_n': len(result['pdf_routes']),
                      'plan_rows_match': result['plan_rendering']['all_match']}, ensure_ascii=False))
    return int(not result['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
