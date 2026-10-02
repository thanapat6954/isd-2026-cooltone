"""Resumable real-API development probes for source-reviewed study plans."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    app = args.app_root
    manifest = json.loads((app/'data/ground_truth/study_plan_relationships.json').read_text(encoding='utf-8'))
    dependencies = {str(p.relative_to(app)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [*sorted((app/'lab10_fastapi/curriculum_app').glob('*.py')),
                              app/'data/ground_truth/study_plan_relationships.json',
                              *sorted((app/'work').glob('lab8b_*/curriculum.db'))]}
    result = {'dependencies': dependencies, 'cases': [], 'links': []}
    if args.resume and args.output.is_file():
        result = json.loads(args.output.read_text(encoding='utf-8'))
        if result['dependencies'] != dependencies: raise SystemExit('Dependencies changed; choose a new output')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save(): args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    cases = []
    for term in manifest['terms']:
        program = term['source_file'].split('.')[0].split('-')[0]
        version = 'old' if term['version'] == 2560 else 'latest'
        tracks = manifest['track_sets'][term['track_set']]
        for plan in term['pages']:
            question = f"ปี {term['year']} ภาคการศึกษาที่ {term['semester']} มีรายวิชาอะไรบ้าง แผน{'ไม่เข้าร่วมสหกิจ' if plan == 'no-coop' else 'สหกิจศึกษา'}"
            for track in [None, tracks[0]]:
                cases.append({'id': f"{program}-{term['version']}-{plan}-{term['year']}-{term['semester']}-{track['id'] if track else 'all'}",
                    'program': program, 'version': version, 'question': question + (f" {track['label']}" if track else ''),
                    'term': term, 'plan': plan, 'track': track})
    for db in DatabaseRegistry(app).active_programs:
        program = db.program_id.split('-')[0]
        cases.append({'id': db.curriculum_name+'-generic', 'program': program,
                      'version': 'old' if db.curriculum_version == 2560 else 'latest',
                      'question': f"ปี 1 ภาคการศึกษาที่ 1 มีรายวิชาอะไรบ้าง {'ไม่เข้าร่วมสหกิจ' if db.plan == 'no-coop' else 'สหกิจศึกษา'}",
                      'plan': db.plan})
    completed = {r['id'] for r in result['cases']}
    for case in cases:
        if case['id'] in completed: continue
        response = requests.post('http://127.0.0.1:8000/ask', json={'curriculum': case['program'], 'version': case['version'], 'question': case['question']}, timeout=45)
        body = response.json()
        cards = (body.get('study_plan') or {}).get('cards', [])
        errors = []
        if response.status_code != 200 or not cards: errors.append('HTTP or missing cards')
        if len(cards) != 1 or any(c['plan'] != case['plan'] for c in cards): errors.append('plan isolation')
        if case.get('term') and cards:
            term = case['term']; card = cards[0]
            if not card['reviewed']: errors.append('source review not applied')
            if any('ยังขาด' in n or 'ไม่ตรง' in n for n in card['notes']): errors.append('review mismatch')
            track_sections = [s for s in card['sections'] if s['kind'] == 'track']
            expected = [case['track']['label']] if case.get('track') else [t['label'] for t in manifest['track_sets'][term['track_set']]]
            if sorted(s['title'] for s in track_sections) != sorted(expected): errors.append('track grouping')
            for section in track_sections:
                if term.get('elective_pattern'):
                    if len(section['rows']) != len(term['elective_ordinals']): errors.append('elective slot duplication or loss')
                    if not all(r.get('credits_raw') == term['elective_credits_raw'] for r in section['rows']): errors.append('hours alternatives')
                else:
                    track = next(t for t in manifest['track_sets'][term['track_set']] if t['label'] == section['title'])
                    codes = term.get('track_codes_by_plan', {}).get(case['plan']) or term['track_codes']
                    if sorted(r['code'] for r in section['rows']) != sorted(codes[track['id']]): errors.append('track membership')
                common = [r for s in card['sections'] if s['kind'] != 'track' for r in s['rows']]
                seen = set(); total = 0
                for index, row in enumerate(common + section['rows']):
                    identity = ('alt', row['alt_group']) if row.get('alt_group') else ('row', index)
                    if identity not in seen: total += row['credits']; seen.add(identity)
                section['verified_choice_total'] = total
                if total != card['printed_total']: errors.append('single-track counted total differs from printed table')
            pages = term['pages'][case['plan']]
            if any([r.get('page_number'), r.get('printed_page_number')] not in pages for s in card['sections'] for r in s['rows']): errors.append('page provenance')
        result['cases'].append({'id': case['id'], 'request': {k:case[k] for k in ['program','version','question']},
                                'status': response.status_code, 'errors': errors, 'body': body})
        save()
    if not result['links']:
        for filename in manifest['sources']:
            response = requests.get('http://127.0.0.1:8000/api/source/'+filename, headers={'Range':'bytes=0-63'}, stream=True, timeout=15)
            prefix = next(response.iter_content(8), b''); response.close()
            result['links'].append({'source': filename, 'status': response.status_code, 'pdf_signature': prefix.startswith(b'%PDF')})
        response = requests.get('http://127.0.0.1:8000/api/source/requirements.txt', timeout=10)
        result['links'].append({'source': 'disallowed', 'status': response.status_code, 'expected': 404})
        save()
    failed = [c['id'] for c in result['cases'] if c['errors']]
    print(f"{len(result['cases'])-len(failed)}/{len(result['cases'])} cases passed; failed: {failed}; links: {result['links']}")
    return bool(failed)


if __name__ == '__main__': raise SystemExit(main())
