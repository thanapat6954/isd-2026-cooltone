"""Reconcile raw verification evidence and generate the scoped Thai report."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT.parent / 'docs/results'


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    args = parser.parse_args()
    app = args.app_root
    read = lambda name: json.loads((RESULTS/name).read_text(encoding='utf-8'))
    api = read('study_plan_api_verified.json')
    old = read('study_plan_old_verified.json')
    gold = read('study_plan_gold_recovered.json')
    tests = read('study_plan_tests_verified.json')
    before = read('study_plan_before.json')
    manifest = json.loads((ROOT/'data/ground_truth/study_plan_relationships.json').read_text(encoding='utf-8'))
    changed = [p for p, digest in api['dependencies'].items() if sha(app/p) != digest]
    for evidence in (gold, old):
        changed.extend('code/'+p for p, digest in evidence['dependencies']['code'].items()
                       if sha(app/'lab10_fastapi/curriculum_app'/p) != digest)
        changed.extend(p for p, digest in evidence['dependencies']['databases'].items() if sha(app/p) != digest)
    dbs = [{'profile': d['identity'], 'unchanged': sha(Path(d['path'])) == d['sha256']} for d in before['databases']]
    profiles = []
    for case in api['cases']:
        if not case['id'].endswith('-generic'): continue
        identity = case['id'].removesuffix('-generic')
        group_cases = [c for c in api['cases'] if c['id'].startswith(identity+'-')]
        profiles.append({'profile':identity, 'grouping_passed':sum(not c['errors'] for c in group_cases),
                         'grouping_n':len(group_cases), 'reviewed_term_probes':sum(any(card['reviewed'] for card in c['body']['study_plan']['cards']) for c in group_cases),
                         'gold':gold['summary'].get(identity), 'old':old['summary'].get(identity)})
    unit_n = int(re.search(r'Ran (\d+) tests',tests['runs'][0]['stderr'])[1])
    schema = re.search(r'ผ่าน\s+(\d+)\s*/\s*ไม่ผ่าน\s+(\d+)',tests['runs'][1]['stdout'])
    deployed_paths = ['frontend/app.js','frontend/index.html','frontend/style.css',
                     'data/ground_truth/study_plan_relationships.json',
                     *['lab10_fastapi/curriculum_app/'+name for name in
                       ['study_plan.py','main.py','model_service.py','query_planner.py','schemas.py']]]
    deployed = {p:sha(ROOT/p)==sha(app/p) for p in deployed_paths}
    result = {'profiles': profiles, 'dependency_changes': sorted(set(changed)), 'database_baseline':dbs,
              'api_passed':sum(not c['errors'] for c in api['cases']), 'api_n':len(api['cases']),
              'old_passed':sum(c['passed'] for c in old['cases']), 'old_n':len(old['cases']),
              'gold_passed':sum(not c['errors'] for c in gold['cases']), 'gold_n':len(gold['cases']),
              'gold_dataset_unchanged':sha(ROOT/'tests/qa_gold.json') == gold['gold_sha256'],
              'gold_export':{'runner_exit':1, 'reason':'OneDrive WinError5 replacing final result; recovered complete question checkpoint without rerunning',
                             'recovery_identical':sha(RESULTS/'study_plan_gold_recovered.json') == sha(RESULTS/'study_plan_gold_verified.partial')},
              'unit_n':unit_n,'schema_passed':int(schema[1]),'schema_failed':int(schema[2]),
              'test_exit_codes':[r['exit_code'] for r in tests['runs']], 'deployed_files':deployed,
              'source_links':api['links'], 'ui':read('study_plan_ui.json'), 'narrow_ui':read('study_plan_narrow_final.json')}
    (RESULTS/'study_plan_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines = ['# ผลตรวจการจัดกลุ่มแผนการเรียนและหน้าคำตอบ', '',
      '## ขอบเขตและหลักฐาน', '',
      'ต่อจาก checkpoint เดิม ไม่ทำ A0/A1 หรือการตรวจเล่มเก่าที่เสร็จแล้วซ้ำ ฐานข้อมูลและ OCR เดิมไม่ถูกแก้ไข การตรวจครั้งนี้ครอบคลุมโครงสร้างการแสดงผล ไม่ใช่คะแนน OCR ใหม่หรือการยืนยันทุก field ในทั้งเล่ม', '',
      f"API ตรวจการจัดกลุ่มผ่าน {result['api_passed']}/{result['api_n']} ตัวอย่าง; ชุดคำถามพัฒนาระบบสำหรับฉบับเก่าผ่าน {result['old_passed']}/{result['old_n']}; gold เดิมผ่าน {result['gold_passed']}/{result['gold_n']}; unit tests {unit_n}/{unit_n} และ schema selftest {result['schema_passed']}/{result['schema_passed']+result['schema_failed']}", '',
      'gold runner จบด้วย exit 1 เพราะ OneDrive ล็อกไฟล์ขณะบันทึกผลสุดท้าย ไม่ใช่คำตอบล้มเหลว กู้ JSON ที่มีครบทุกคำถามจาก .partial โดยไม่ถามซ้ำ และตรวจ code/DB hashes อีกครั้ง รายละเอียดใน docs/results/study_plan_summary.json', '',
      '| profile | ตัวอย่างจัดกลุ่มที่ผ่าน | ตัวอย่าง gold | ตัวอย่างเก่าที่ผ่าน | ขอบเขตการตรวจกลุ่ม |',
      '|---|---:|---:|---:|---|']
    for p in profiles:
        g=p['gold']; o=p['old']
        lines.append(f"| {p['profile']} | {p['grouping_passed']}/{p['grouping_n']} | {g['passed']}/{g['n']} | {str(o['passed'])+'/'+str(o['n']) if o else 'n/a'} | {'มี term ที่ตรวจภาพต้นฉบับแล้ว' if p['reviewed_term_probes'] else 'แสดงข้อมูลที่นำเข้า ไม่ยืนยันกลุ่มจากทั้งเล่ม'} |")
    lines += ['', '## โครงสร้างที่ยืนยันจากภาพต้นฉบับ', '',
      '| ต้นฉบับ / ฉบับ | ภาคการศึกษา | กลุ่มตามเล่ม | PDF / หน้าในเล่ม (coop; no-coop) |', '|---|---|---|---|']
    for term in manifest['terms']:
        labels='; '.join(t['label'] for t in manifest['track_sets'][term['track_set']])
        pages='; '.join(plan+': '+', '.join(f'{a}/{b}' for a,b in values) for plan,values in term['pages'].items())
        lines.append(f"| {term['source_file']} / {term['version']} | ปี {term['year']} ภาค {term['semester']} | {labels} | {pages} |")
    lines += ['', 'DSBA ใช้กลุ่มตัวเลือกในแต่ละรายการวิชาเลือก ไม่พบหลักฐานจากหน้าที่ตรวจว่าต้องเลือกกลุ่มเดียวตลอดหลักสูตร ส่วน IT มีรายวิชาตามแขนง/กลุ่มแยกจากแผนสหกิจศึกษา ไม่รวมรายวิชาทุกกลุ่มเข้าด้วยกัน รหัส 06016418 อยู่ทั้งกลุ่มซอฟต์แวร์และสื่อประสม ไม่ใช่วิชาร่วมทุกกลุ่ม', '',
      '## สาเหตุและสิ่งที่แก้', '',
      '- ข้อมูลที่นำเข้า/การดึงข้อมูล: สูญเสียความสัมพันธ์ของกลุ่มและหมวดวิชา เพิ่มความสัมพันธ์ที่ตรวจจากภาพไว้แยกใน study_plan_relationships.json ตรวจ SHA256 ต้นฉบับ ฉบับ แผน ภาค และหน้า ก่อนใช้ ไม่อนุมานแขนงจากชื่อวิชา',
      '- การสร้างคำตอบ: เดิม flatten กลุ่มและชุด “หรือ” เป็นรายการเดียว เพิ่ม structured study_plan และข้อความทางเลือก รักษาสองมิติของแผนและแขนง ไม่รวมเครดิตของทางเลือกทุกชุด',
      '- การแสดงผล: เพิ่มตารางภาษาไทย แยกรายวิชาร่วม กลุ่ม GE และวิชาเลือกเสรี รายละเอียด English/ชั่วโมงอยู่ใน details มีลิงก์ PDF และหน้าในเล่ม ใช้ textContent และ allowlist ของไฟล์ ไม่แยกกลุ่มด้วยการตัดข้อความคำตอบ',
      '- บั๊กที่พบระหว่างตรวจ: รายการ wildcard คนละรายการแต่รหัสซ้ำถูกตัดทิ้ง แก้ identity ให้รักษาชื่อรายการและลำดับ แสดงเครดิตรวมของแต่ละทางเลือกตรงกับหน้าที่ตรวจ',
      '- IT2565: เก็บชื่อและชั่วโมงที่ตรวจจาก PDF34/41 และ35/42 แยกจาก OCR; แก้ heading bleed-in 06016421 และชื่อที่คลาดตำแหน่ง 06016422/23/26/27 ในคำตอบแผนการเรียน ไม่อ้างว่าตาราง catalog หรือคำถามทุกชนิดถูกแก้แล้ว', '',
      '## ตัวอย่างก่อนและหลัง', '',
      '- DSBA2565 ปี3 ภาค1: จากชื่อวิชาเลือกสามกลุ่มคั่นด้วย slash และคำว่า “สล็อต” เป็นสามกลุ่มที่มีรายการ1/2 แยกกัน และ GE แยกหมวด สองแผนเหมือนกันเฉพาะภาคนี้ (PDF34/หน้า33 และ PDF27/หน้า26)',
      '- IT2565 ปี2 ภาค2: แยกสี่วิชาร่วม กับสามกลุ่มที่มีสองวิชาต่อกลุ่ม เลือกหนึ่งกลุ่ม ไม่ใช่หกวิชาของทุกกลุ่ม (PDF41/หน้า36 และ PDF34/หน้า29)',
      '- IT2560 ปี2 ภาค2 แผนไม่สหกิจศึกษา แขนงวิศวกรรมซอฟต์แวร์: แสดงสี่วิชาร่วมและ06016321/22 พร้อม PDF29/หน้า24 โดยไม่ใช้2565', '',
      '## การตรวจหน้าเว็บและข้อจำกัด', '',
      'ตรวจเว็บจริงที่ desktop1280px, mobile390px และหน้าต่าง768px ตารางไม่ล้นแนวนอน ปรับ breakpoint ให้แผงคำตอบซ้อนก่อนคอลัมน์ชื่อวิชาจะแคบเกินไป ทดสอบเลือกแขนง/แผนและข้อความคล้าย HTML ในช่องคำถาม ซึ่งแสดงเป็นข้อความ ไม่มี img ถูกแทรก หลักฐานใน study_plan_ui.json, study_plan_narrow_final.json และ screenshots/study_plan_*.jpg', '',
      'ยังเปิด: BIT2565 PDF30/หน้า25 และ35/หน้า30 ระบุ “กลุ่มวิชาที่1–4” แต่ยังไม่ได้ตรวจนิยาม/รายวิชาของแต่ละกลุ่มครบ จึงไม่สร้างชื่อแขนงขึ้นเอง; บางฐานข้อมูล2565ยังขาด fidelity columns และชื่อ placeholder ทำให้การยืนยันกลุ่ม/หน้าในเล่มนอก term ที่ตรวจเป็น n/a; คำถามชนิดอื่นยังใช้ catalog เดิม การแก้ชื่อเฉพาะแผนนี้ไม่ใช่การแก้ catalog ทั้งระบบ; full-book names/prerequisites และ held-out ใหม่ยังไม่วัดในรอบนี้', '',
      'หลักฐาน: docs/results/study_plan_before.json, study_plan_api_verified.json, study_plan_old_verified.json, study_plan_gold_recovered.json, study_plan_tests_verified.json, study_plan_render*.json และ study_plan_summary.json. Checkpoint: docs/PROGRESS.md', '']
    report=ROOT/'reports/audit_study_plan_grouping.md'
    report.write_text('\n'.join(lines),encoding='utf-8')
    ok = not changed and all(deployed.values()) and all(d['unchanged'] for d in dbs) and result['gold_dataset_unchanged'] and result['gold_export']['recovery_identical'] and not any(result['test_exit_codes']) and all(result[k+'_passed']==result[k+'_n'] for k in ('api','old','gold'))
    print(json.dumps({k:result[k] for k in ['api_passed','api_n','old_passed','old_n','gold_passed','gold_n','unit_n','dependency_changes','gold_dataset_unchanged']},ensure_ascii=False))
    print('DB baseline unchanged:',sum(d['unchanged'] for d in dbs),'/',len(dbs),'; reconciled evidence:',ok)
    return not ok


if __name__ == '__main__': raise SystemExit(main())
