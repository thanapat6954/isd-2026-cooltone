"""Export observed release results and a bounded Thai report; no new API calls."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry

STRINGS = {
    'title': '# ผลการแก้ไข DB-only และหลักฐานก่อนส่งงาน',
    'scope': 'ผลนี้ยืนยันเฉพาะคำถามและแถวที่ทดสอบ ไม่ใช่ accuracy ของหนังสือทั้งเล่ม และไม่ใช่หลักฐานว่าไม่มี hallucination ทุกกรณี',
    'table': '| profile | HIGH / MED ที่ยังเปิด | gold | อ้างอิง PDF / ทั้ง PDF+หน้าเล่ม | latency gold median / p95 ms | frozen unique | unknown grounding / ms | UI |',
    'divider': '|---|---:|---:|---:|---:|---:|---:|---|',
    'frozen': 'frozen เป็นเฉลยเดิมที่สร้างจาก DB ไม่ใช่ GT อิสระจากหนังสือและไม่ใช่ชุดใหม่ที่ไม่เคยใช้ debugging ผลซ้ำรวม cache ไม่ใช่การสร้างคำตอบใหม่จากโมเดลสามครั้ง เฉลยและ hash ไม่เปลี่ยน',
    'issues': '## ข้อจำกัดและงานที่ยังเปิด',
    'citation': 'จำนวน citation วัดการมี locator ใน DB ของคำตอบที่มีหลักฐาน ไม่ใช่ semantic citation accuracy; คำตอบ uncertainty ไม่มีข้อมูลรองรับจึงไม่นับเป็น citation หรือ latency success',
    'unknown': 'unknown grounding ตรวจว่า SELECT และค่าที่แสดงตรงกับ SQLite; ความครบถ้วนและความเกี่ยวข้องของคำตอบยังไม่ได้ตรวจด้วยเฉลยอิสระ',
}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def citations(body):
    output = []
    for row in body.get('rows', []):
        file = row.get('source_file') or row.get('source_files')
        page = row.get('page_number') or row.get('source_pages')
        book = row.get('printed_page_number') or row.get('source_printed_pages')
        if file and page:
            output.append({'source_file': file, 'pdf_page': page, 'printed_page': book})
    return list({json.dumps(x, ensure_ascii=False, sort_keys=True): x for x in output}.values())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--release', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    a = p.parse_args()
    a.release = a.release.resolve()
    a.output_dir = a.output_dir.resolve()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    release = load(a.release / 'release_checks.json')
    if len([x for x in release['jobs'] if x.get('completed')]) != 8 or not release.get('runtime_unchanged'):
        raise ValueError('Release checks are incomplete or dependencies changed')
    gold, frozen, unknown, old = [load(a.release / (name + '.json')) for name in ['gold', 'frozen', 'unknown', 'old2560']]
    audit = load(ROOT / 'reports/audit_results.json')
    ui = load(REPO / 'docs/results/db_only_ui_release.json')
    registry = DatabaseRegistry(a.app_root)
    active = registry.active_catalogs
    current_code = {x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in (a.app_root / 'lab10_fastapi/curriculum_app').glob('*.py')}
    if current_code != release['dependencies']:
        raise ValueError('The deployed code no longer matches the measured release')
    summary, exports = [], []
    for db in active:
        profile = db.curriculum_name
        key = 'legacy' if profile == 'legacy-course-catalog' else profile
        cases = [x for x in gold['cases'] if x['identity'] == key]
        evidence = [x for x in cases if x['response'].get('rows') and x['passed'] and x.get('level') != 'missing-evidence']
        pdf = sum(bool(citations(x['response'])) for x in evidence)
        both = sum(bool(citations(x['response'])) and all(c['printed_page'] is not None for c in citations(x['response'])) for x in evidence)
        latencies = [x['elapsed_ms'] for x in evidence]
        frozen_cases = [x for x in frozen['cases'] if x['profile'] == profile and x['run'] == 1]
        model_cases = [x for x in unknown['cases'] if x['profile'] == profile]
        dataset = next(x for x in audit['datasets'] if Path(x['database']).as_posix() == Path(db.relative_path).as_posix())
        counts = Counter(x['severity'] for x in dataset['findings'] if x['status'] in ['FAIL', 'NEEDS_REVIEW', 'SKIPPED'])
        record = {'profile': profile, 'high': counts['HIGH'], 'med': counts['MED'],
                  'gold_passed': sum(x['passed'] for x in cases), 'gold_n': len(cases),
                  'pdf_cited': pdf, 'both_pages_cited': both, 'citation_n': len(evidence),
                  'gold_median_ms': round(statistics.median(latencies), 2) if latencies else None,
                  'gold_p95_ms': round(percentile(latencies, .95), 2) if latencies else None,
                  'frozen_passed': sum(x['passed'] for x in frozen_cases), 'frozen_n': len(frozen_cases),
                  'unknown_grounded': sum(x['passed'] for x in model_cases), 'unknown_n': len(model_cases),
                  'unknown_ms': model_cases[0]['elapsed_ms'] if model_cases else None,
                  'ui_observed': any(x['profile'] == profile for x in ui['observations'])}
        summary.append(record)
    for category, result in [('gold', gold), ('old-development', old), ('frozen', frozen), ('unknown-grounding', unknown)]:
        for item in result['cases']:
            body = item['response']
            exports.append({'suite': category, 'profile': item.get('profile') or item.get('identity'),
                            'id': item['id'], 'question': item['question'], 'answer': body.get('answer', ''),
                            'citations': citations(body), 'elapsed_ms': item.get('elapsed_ms'),
                            'passed': item['passed'], 'http_status': item.get('status', item.get('http_status', item.get('api_status'))),
                            'error': body.get('detail'), 'score_scope': category})
    comparison = load(REPO / 'docs/results/db_only_l3_verified.json')
    for index, item in enumerate(comparison['cases'], 1):
        exports.append({'suite': 'L3-db-set-replay', 'profile': item['profile'], 'id': f'L3-{index}',
                        'question': item['question'], 'answer': item['response'].get('answer', ''),
                        'citations': citations(item['response']), 'elapsed_ms': item['elapsed_ms'],
                        'passed': item['passed'], 'http_status': 200 if item['passed'] else None,
                        'error': None, 'score_scope': 'Imported code-set calculation, not full-book or semantic equivalence accuracy'})
    export_path = a.output_dir / 'questions_answers_citations.json'
    export_path.write_text(json.dumps({'limitations': [STRINGS['scope'], STRINGS['frozen'], STRINGS['unknown']], 'cases': exports}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (a.output_dir / 'questions_answers_citations.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(exports[0]))
        writer.writeheader()
        for item in exports:
            writer.writerow({**item, 'citations': json.dumps(item['citations'], ensure_ascii=False)})
    before = load(REPO / 'docs/results/db_only_provenance_verified_20261004.json')
    review = load(ROOT / 'data/ground_truth/study_plan_db_review.json')
    inventory = []
    for case in before['cases']:
        for change in case['changes']:
            row = next((r for r in case['body'].get('rows', []) if r.get('code') == change.get('code')), {})
            source = row.get('source_file')
            inventory.append({'profile': case['profile'], **change, 'type': 'presentation' if change['field'] == 'requirement_id' else 'factual',
                              'source_file': source, 'pdf_page': row.get('page_number'),
                              'reviewed_pdf_and_book_pages': review['approved_pages'].get(source, []),
                              'resolution': 'SQLite relation/renderer identifier' if change['field'] == 'requirement_id' else 'Book-reviewed stored fact or stored-column query correction',
                              'approval': 'ocr_final/data/ground_truth/study_plan_db_review.json'})
    (a.output_dir / 'overlay_contribution_inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    source_evidence = {'classification': dict(Counter(x['type'] for x in inventory)),
                       'fields': dict(Counter(x['field'] for x in inventory)),
                       'source_review_pages': sum(len(x) for x in review['approved_pages'].values())}
    unit = load(a.release / 'unit.json')
    unit_n = int(re.search(r'Ran (\d+) tests', unit['runs'][0]['stderr'])[1])
    schema_n = int(re.search(r'ผ่าน\s+(\d+)\s*/', unit['runs'][1]['stdout'])[1])
    provenance = load(a.release / 'provenance.json')['summary']
    cards = load(a.release / 'cards.json')['cases']
    versions = load(a.release / 'versions.json')['pairs']
    isolation = load(REPO / 'docs/results/db_only_isolation_verified.json')['summary']
    replay = load(REPO / 'docs/results/db_only_build_replay.json')['summary']
    valid_unknown_ms = [x['elapsed_ms'] for x in unknown['cases'] if x['passed'] and x.get('category') == 'stored_values']
    overall = {'profiles': summary, 'source_evidence': source_evidence,
               'gold': gold['summary'], 'gold_latency': gold['latency'], 'frozen': frozen['summary'], 'unknown': unknown['summary'],
               'protected_unchanged': frozen['protected_unchanged'], 'ui_profiles': ui['covered'],
               'unit_tests': unit_n, 'schema_tests': schema_n, 'isolation': isolation, 'build_replay': replay,
               'unknown_latency': {'n':len(valid_unknown_ms), 'median_ms':round(statistics.median(valid_unknown_ms),2),
                                   'p95_ms':round(percentile(valid_unknown_ms,.95),2),
                                   'under_5s':sum(x<5000 for x in valid_unknown_ms)},
               'audit': {'datasets': len(audit['datasets']), 'fail': sum(x['status']=='FAIL' for d in audit['datasets'] for x in d['findings']),
                         'incomplete': sum(x['status'] in ['SKIPPED','NEEDS_REVIEW'] for d in audit['datasets'] for x in d['findings'])}}
    (a.output_dir / 'evaluation_summary.json').write_text(json.dumps(overall, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = [STRINGS['title'], '', STRINGS['scope'], '', '## ผลการทดสอบที่สังเกตจริง', '',
             f"- unit {unit_n}/{unit_n}, schema {schema_n}/{schema_n}; isolated provenance {isolation['passed']}/{isolation['n']}, migration replay/rollback {replay['passed']}/{replay['n']}",
             f"- gold {sum(x['passed'] for x in gold['cases'])}/{len(gold['cases'])}; old development {sum(x['passed'] for x in old['cases'])}/{len(old['cases'])}; version isolation {sum(x['passed'] for x in versions)}/{len(versions)}; cards {sum(not x['errors'] and x['status']==200 for x in cards)}/{len(cards)}",
             f"- provenance {provenance['http_200']}/{provenance['profiles']} profile: ค่า-field เพิ่ม/เปลี่ยนจาก SQL replay {provenance['changed_or_added_field_count']}; unknown grounding {unknown['summary']['passed']}/{unknown['summary']['n']}",
             f"- unknown complete-answer latency median {overall['unknown_latency']['median_ms']:.2f}ms / p95 {overall['unknown_latency']['p95_ms']:.2f}ms (n={overall['unknown_latency']['n']}); ใต้ห้าวินาที {overall['unknown_latency']['under_5s']}/{overall['unknown_latency']['n']} ไม่ใช่ cold-model หรือ hard-question benchmark", '',
             '## ผลตาม profile', '', STRINGS['table'], STRINGS['divider']]
    for row in summary:
        n = row['citation_n']
        baseline = f"{row['frozen_passed']}/{row['frozen_n']}" if row['frozen_n'] else 'n/a'
        time = f"{row['gold_median_ms']:.2f} / {row['gold_p95_ms']:.2f} (n={n})" if n else 'n/a'
        cited = f"{row['pdf_cited']}/{n} / {row['both_pages_cited']}/{n}" if n else 'n/a'
        lines.append(f"| `{row['profile']}` | {row['high']} / {row['med']} | {row['gold_passed']}/{row['gold_n']} | {cited} | {time} | {baseline} | {row['unknown_grounded']}/{row['unknown_n']} / {row['unknown_ms']:.2f} | {'สังเกตจริง' if row['ui_observed'] else 'n/a'} |")
    lines += ['', STRINGS['citation'], '', STRINGS['unknown'], '', STRINGS['frozen'], '',
              '## สาเหตุและสิ่งที่แก้', '',
              '- code bug: runtime JSON overlay และ unknown free prose ถูกแทนด้วย SQL relations + structured row/field references; โมเดลส่งเฉพาะตำแหน่งหลักฐาน ไม่ส่งค่าที่จะแสดง',
              '- data-ingest bug: IT 06016422 สลับกับชื่อความมั่นคงโครงสร้างพื้นฐาน แก้จาก IT.pdf PDF35/หน้าเล่ม30 และ PDF42/หน้าเล่ม37 เป็นอินเทอร์เน็ตของสรรพสิ่ง พร้อม correction history',
              '- retrieval bug: query ไม่เลือก credits_raw/หน้าเล่มจากแถวแผน และไม่รองรับภาคเรียน/รหัสทั้งหมด แก้ parser/query; แยกปีหลักสูตรกับชั้นปี',
              '- SQL repair: redundant identity filter บน program ถูก normalize เฉพาะ DB มีหนึ่งแถวและ safe SELECT ก่อน/หลังได้ค่าที่บันทึกเดียวกัน; false predicate, wrong exact ID, fact filters, multirow และ alias ผิดความหมายยังถูกปฏิเสธ',
              f"- inventory เดิม {len(inventory)} ค่า-field แยก factual {source_evidence['classification'].get('factual',0)} / presentation {source_evidence['classification'].get('presentation',0)}; ตรวจ rendered page {source_evidence['source_review_pages']} หน้า ไม่ใช่จำนวนคำตอบผิด", '',
              '## Migration และ rollback', '',
              'สำรอง active DB ด้วย SQLite backup API พร้อม integrity/hash ก่อนแก้; เพิ่ม study_term/page/track/item/member/correction และ v_study_plan ใน isolated copy ก่อน deploy. JSON ที่ตรวจแล้วเป็น ingestion input เท่านั้น ไม่มี runtime factual overlay.',
              'รันจาก repository root (PowerShell); แทนค่าตัวแปรด้วยตำแหน่ง live app ที่ใช้อยู่:', '',
              '```powershell', "$liveApp = '<path-to-live-app-with-PDFs-and-DBs>'",
              '.\\ocr_final\\venv\\Scripts\\python.exe ocr_final/scripts/prepare_db_only.py --app-root $liveApp --output docs/results/new_backups.json',
              '.\\ocr_final\\venv\\Scripts\\python.exe ocr_final/scripts/migrate_study_evidence.py --app-root $liveApp --backups docs/results/new_backups.json --output docs/results/new_migration.json',
              '# Validate isolated copies before deployment; do not reuse the old baseline after DB changes.',
              '.\\ocr_final\\venv\\Scripts\\python.exe ocr_final/scripts/verify_db_only_isolation.py --migration docs/results/new_migration.json --backups docs/results/new_backups.json --output docs/results/new_isolation.json',
              '.\\ocr_final\\venv\\Scripts\\python.exe ocr_final/scripts/migrate_study_evidence.py --app-root $liveApp --backups docs/results/new_backups.json --deploy-evidence docs/results/new_migration.json --output docs/results/new_deployment.json --apply',
              '# Dry run rollback first. Stop the verified backend before --apply.',
              '.\\ocr_final\\venv\\Scripts\\python.exe ocr_final/scripts/rollback_db_only.py --app-root $liveApp --backups docs/results/db_only_backups.json --profile IT-2565-coop --output docs/results/rollback_check.json',
              '# Repeat the same rollback command with --apply only when restoration is intended.',
              '.\\ocr_final\\venv\\Scripts\\python.exe ocr_final/scripts/run_db_only_release_checks.py --app-root $liveApp --output-dir docs/results/new_release', '```', '',
              'rollback รักษา pre-rollback snapshot อีกชุด; หากย้อนทั้ง release ต้องคืนทุก DB ที่ต้องการและไฟล์ runtime จาก work/backups/db-only/<stamp>/code แล้วเริ่ม backend ใหม่. ไม่รัน rollback บน production ในการตรวจครั้งนี้; ทดสอบบน isolated DB แล้วเท่านั้น.', '',
              STRINGS['issues'], '',
              '- OCR loss / source ambiguity: prerequisite และ full-book names/category/การจบการศึกษายังไม่ครบ; current IT/BIT สี่ profile ยังขาด fidelity columns บางส่วน นอก migration นี้',
              '- legacy มีหลายเล่มและยังไม่มีปี/ฉบับที่ยืนยัน; gold เป็น safety regression ไม่ใช่ content accuracy และไม่มี UI selector',
              '- frozen DSBA สาม set cases ยังพึ่ง internal placeholder ID เดิม ไม่แก้เฉลยเพื่อให้ผ่าน; ดู frozen.json สำหรับค่าที่ขาด',
              '- L3 DB-set calculation และ version isolation ไม่ยืนยัน full-book difference; L4 same-year revision/dual-degree ไม่มีเอกสาร, AI ฉบับเก่าไม่มี source; accuracy จึงเป็น n/a',
              '- บาง metadata/aggregate citations ยังไม่มีหน้าเล่ม; ไม่อนุมาน offset เพิ่ม. แหล่ง general_education ยังไม่มี PDF provenance ครบ',
              '- ตัวอย่าง UI unknown ของ IT-2560-no-coop อ้าง program metadata ที่ PDF33 แต่ยังไม่ได้ยืนยันว่าหน้านี้รองรับทั้งยอดรวมและระยะเวลาศึกษา ต้องตรวจ provenance เพิ่มก่อนนับ semantic citation accuracy',
              '- unknown semantic accuracy, true absence precision/recall, cold model latency และ independent three-run generation stability ยังเป็น n/a; expected-abstain ชุด frozen มีเพียงสองข้อต่อ profile',
              '- UI พบ loading/success/missing/error/recovery และ actual cards; การวัดครบทุกชนิดคำถามบนทุก viewport ยังเป็น n/a', '',
              '- OCR metrics ไม่ได้เพิ่มจาก curated DB correction; original OCR ไม่เปลี่ยน และการทดสอบครั้งนี้ไม่ใช่การรัน OCR ใหม่', '',
              '## ไฟล์หลักฐาน', '',
              f'- raw release: `{a.release.relative_to(REPO).as_posix()}`; exit codes ใน release_checks.json',
              '- backups/deployment/source renders/isolation/build replay: docs/results/db_only_*.json',
              '- UI observations/screenshots: docs/results/db_only_ui*.json และ docs/results/screenshots/db_only_*.jpg',
              '- CSV/JSON สำหรับส่งงาน: questions_answers_citations.csv / .json และ evaluation_summary.json ในโฟลเดอร์เดียวกับรายงานนี้',
              '- checkpoint เดียว: docs/PROGRESS.md; feature branch audit/curriculum-challenge; ไม่ push หรือแก้ main', '']
    report = a.output_dir / 'DB_ONLY_REPORT.md'
    report.write_text('\n'.join(lines), encoding='utf-8')
    # Export no debug paths, tokens or complete database dumps.
    public_json = export_path.read_text(encoding='utf-8')
    if re.search(r'C:\\\\Users|OneDrive|(?:sk-|ghp_)[A-Za-z0-9]{15}', public_json):
        raise ValueError('Local path or credential-like pattern in question export')
    print('Profiles', len(summary), 'exported cases', len(exports), 'inventory', len(inventory))


if __name__ == '__main__':
    main()
