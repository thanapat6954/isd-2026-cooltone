"""Generate a bounded Thai report from measured results, with explicit limits."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0,str(ROOT))


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'reports/audit_summary.md')
    args = parser.parse_args()
    audit = read(ROOT/'reports/audit_results.json')
    qa = read(PROJECT/'docs/results/qa_gold_final_2026-10-02.json')
    tests = read(PROJECT/'docs/results/current_audit_final_regressions.json')
    ui = read(PROJECT/'docs/results/ui_api_agreement_2026-10-02.json')
    issues = [finding for item in audit['datasets'] for finding in item['findings']]
    statuses = Counter(item['status'] for item in issues)
    categories = Counter((item['check'],item['status']) for item in issues)
    lines = ['# สรุปการตรวจและแก้ไข Curriculum OCR', '', '## Summary', '',
        'งานยังไม่เสร็จทั้งระบบ ผลต่อไปนี้เป็น development regression ที่อ้างอิงหน้าหนังสือที่ตรวจแล้ว ไม่ใช่ held-out accuracy หรือการตรวจหนังสือทุกหน้า', '',
        f"ตรวจ SQLite {len(audit['datasets'])} ชุด รวมฐานที่ใช้งานจริงและฐาน validation; พบ FAIL {statuses['FAIL']} รายการ และ NEEDS_REVIEW/SKIPPED {statuses['NEEDS_REVIEW']+statuses['SKIPPED']} รายการ ไม่ตีความรายการที่หายจากรายงานว่าแก้แล้วโดยอัตโนมัติ",
        'ใช้ schema จริงและ SQLite mode=ro/query_only=ON; ไม่ใช้ชื่อโฟลเดอร์เดาเล่ม ไม่ใช้ข้อความใกล้รหัสเป็นเฉลย และไม่ใช้ SQL fallback คนละเส้นทางกับแอป', '',
        '## สาเหตุที่ยืนยันและสิ่งที่แก้', '',
        '- การค้นเฉพาะ prerequisite ทำให้รายวิชาที่มีอยู่แต่ไม่มี edge ถูกตอบเหมือนไม่พบรายวิชา แก้เป็น LEFT JOIN จาก course พร้อมแยก explicit_none / required / unknown',
        '- ไม่มีข้อมูลใน DB ไม่ใช่หลักฐานว่าไม่มีในเล่ม คำตอบจึงระบุหลักสูตร/ฉบับที่ค้นและแจ้งความไม่ครบของข้อมูล ไม่อนุญาตลงทะเบียนโดยไม่มีข้อบังคับรองรับ',
        '- คำว่าไม่เข้าร่วมสหกิจเคยเลือก coop; แก้คำระบุแผนภาษาไทยและใช้ program.plan แทน suffix ของ program_id',
        '- คำถามชื่อรายวิชาที่ระบุหลักสูตรเคยถูกอ่านเป็นชื่อหลักสูตร แก้ intent โดยให้รหัสวิชามีความสำคัญก่อน',
        '- AI.pdf หน้า PDF 1 ระบุหลักสูตรใหม่ พ.ศ. 2566 แก้ metadata/config/UI เป็น AI-2566 และเลือกปีที่ระบุจริงโดยไม่ fallback ข้ามฉบับ',
        '- นำหลักฐาน prerequisite ที่ตรวจภาพแล้วกลับเข้า DB พร้อม SHA-256, หน้าเล่ม และ SQLite backup; ใช้ซ้ำหลัง rebuild ได้ ไม่แก้ original OCR หรือ held-out',
        '- ใช้ชื่อภาษาไทยจากแถวที่ตรวจแล้วแก้ IT-2560 สองแถวที่สลับชื่อ และสามแถวที่มีหัวข้อแขนงวิชาปนในชื่อ หลักฐานก่อน/หลังอยู่ใน approved_name_prerequisite_ingest.json; ไม่ใช่ OCR accuracy ที่เพิ่มขึ้น',
        '- cache_hit เก็บเวลาของคำขอปัจจุบัน ไม่รายงานเวลาเดิมของคำขอแรก; UI ระบุ SQL (database-backed) เมื่อไม่ได้เรียก LLM สร้างคำตอบ', '',
        '## ผลตามหลักสูตรและฉบับ', '',
        '| หลักสูตร/ฉบับ/แผน | ผ่านครั้งแรก | ขอบเขต |', '|---|---:|---|']
    for identity, values in qa['summary'].items():
        lines.append(f"| `{identity}` | {values['passed']}/{values['n']} | {'ตรวจความปลอดภัยเมื่อข้อมูลไม่ยืนยัน ไม่ใช่ content accuracy' if identity == 'legacy' else 'L1/L2 และข้อมูลไม่ครบ'} |")
    runs = sorted({case['run'] for case in qa['cases']})
    lines += ['', f"รัน {len(runs)} รอบ รวม {len(qa['cases'])} คำตอบ; ชุดคำถามใช้ template และตัวอย่างที่เลือกเพื่อจับบั๊ก จึงไม่ใช้สัดส่วนนี้แทนความแม่นยำทั่วไปหรือเกณฑ์ >91%",
        'legacy รวมข้อความรายวิชาจากหลายเล่มและยังไม่มีปีฉบับที่ยืนยัน จึงมีเฉลยด้านการไม่กล่าวอ้างเกินหลักฐานเท่านั้น ไม่อ้างว่า legacy content accuracy ผ่าน', '',
        '## การอ้างอิงและ latency', '',
        'การตรวจ citation ใน gold ตรวจชื่อแหล่งข้อมูล และตรวจเลขหน้าเฉพาะข้อที่เฉลยระบุหน้า ไม่ใช่การตรวจทุกประโยคในคำตอบกับภาพหนังสือทั้งเล่ม', '',
        '| รอบ | ตัวอย่างที่ตอบถูกและมีสาระ | median (ms) | p95 (ms) | ต่ำกว่า 5 วินาที |', '|---|---:|---:|---:|---:|']
    for run, values in qa['latency'].items():
        lines.append(f"| {int(run)+1} | {values['n']} | {values['median_ms']:.2f} | {values['p95_ms']:.2f} | {values['under_5s']}/{values['n']} |")
    gold = read(ROOT/'tests/qa_gold.json')
    from scripts.run_qa_gold import cases
    content_cases = [case for _,_,_,case in cases(gold) if case.get('source')]
    exact_page_cases = [case for case in content_cases if case.get('page')]
    supported = [case for case in qa['cases'] if case['run'] == 0 and case['citation_supported'] is not None]
    hits = Counter((case['run'],case['cache_hit']) for case in qa['cases'])
    lines += ['',f"gold มีแหล่งอ้างอิง {len(content_cases)} ข้อ ระบุหน้า PDF แบบเฉพาะ {len(exact_page_cases)} ข้อ; metadata citation ผ่าน {sum(case['citation_supported'] for case in supported)}/{len(supported)} ข้อในรอบแรก ข้อที่ตรวจแค่ชื่อไฟล์ยังไม่ใช่ semantic citation accuracy เต็มรูปแบบ",
        'latency วัดเวลาฝั่ง client ครบคำตอบ HTTP รวมการค้นคืนและจัดรูปแบบ กรณีเหล่านี้ใช้ deterministic SQL ไม่ได้วัดการสร้างคำตอบยากด้วย LLM; ตัดข้อข้อมูลไม่ครบออกจาก latency ของคำตอบที่มีสาระ',
        'ไม่เรียกรอบแรกว่า cold start เพราะไม่ยืนยันว่า process/model/cache เย็น และยังไม่ยืนยัน challenge L3/L4 ต่ำกว่า 5 วินาที',
        'cache hits/misses: ' + '; '.join(f"รอบ {run+1} hit {hits[(run,True)]}/{hits[(run,True)]+hits[(run,False)]}, miss {hits[(run,False)]}/{hits[(run,True)]+hits[(run,False)]}" for run in runs), '',
        '## การทดสอบแอปและข้อกำหนด', '',
        f"คำสั่ง regression และ schema selftest มี exit code {[item['exit_code'] for item in tests['runs']]}; raw output ใน docs/results/current_audit_final_regressions.json",
        f"UI และ /ask ตรงกัน {sum(case['passed'] for case in ui['cases'])}/{len(ui['cases'])} กรณี ใน AI/DSBA/IT/BIT ฉบับปัจจุบัน; mobile ตรวจเฉพาะคำตอบ prerequisite ของ DSBA ที่ viewport 390x844 ไม่มี horizontal overflow ไม่ใช่ UI coverage ครบทุกฉบับ/ระดับ",
        'เกณฑ์ P2 ยืนยันจาก ch1_Introduction.pdf หน้า PDF 5/7: DB/RAG 20, OCR 20, output quality 20, LLM 30, แอปและเอกสาร 10; prerequisite/เงื่อนไขลงทะเบียนเป็น L2, เปรียบเทียบเก่า/ใหม่เป็น L3, ฉบับแก้ไขปีเดียวกัน/สองปริญญาเป็น L4; bonus รวมไม่เกิน +10 และคำตอบยากต้องรวม retrieval+generation ภายใน 5 วินาที',
        'ch9_EvaluationAndOverfitting (1).pdf หน้า PDF 17/19/25/26 ให้แยก extraction/schema/retrieval/answer, วัด Execution Accuracy, Faithfulness และ citation coverage, ตรวจ slice ตามแหล่งข้อมูลและความเสถียร; ยังไม่มีใบสั่งงาน Lab 9 ที่ยืนยัน จึงไม่สร้างข้อกำหนดเอง', '',
        '## HIGH', '',
        '1. ยังมีห้า profile ที่ rebuild ถูกบล็อกโดยตาราง OCR เสีย: IT-2560 coop (PDF36/40), IT-2565 no-coop (PDF36/37), IT-2565 coop (PDF43/44), BIT-2565 no-coop (PDF29/30), BIT-2565 coop (PDF34/35) ต้องตรวจภาพและแก้ extraction ไม่สร้าง electives ชดเชยหน่วยกิต',
        '2. prerequisite ที่นำเข้าครบเฉพาะแถวที่ตรวจแล้ว ส่วนที่เหลือยัง unknown; legacy เป็น page fragments และมีรหัส/หน้า/บริบทที่ต้องตรวจ ห้ามล้างทิ้งอัตโนมัติ',
        '3. ยังไม่ยืนยันชื่อ หน่วยกิต หมวดวิชา เงื่อนไขจบ และ citation ทุกแถวกับทั้งเล่ม; general_education_ground_truth.json ยังขาด PDF provenance ใน audit',
        '4. ชุด held-out ไม่ถูกเปลี่ยนและยังไม่ได้ประเมินรอบสุดท้าย; seed stability ของโมเดล, false abstain/abstain recall แบบ independent held-out, การตอบ L3/L4, cold/warm LLM และ latency challenge ยังไม่วัด',
        '5. ไม่พบเอกสารฉบับแก้ไขปีเดียวกันหรือสองปริญญา และไม่มี AI ฉบับเก่า จึงยังตรวจ challenge เหล่านี้ไม่ได้; legacy ไม่มีตัวเลือกใน UI', '',
        '| ประเภท finding | สถานะ | จำนวน |','|---|---|---:|']
    for (kind,status),count in sorted(categories.items()):
        lines.append(f'| `{kind}` | {status} | {count} |')
    lines += ['', '## หลักฐานและการทำต่อ', '',
        '- รายการรายวิชาที่ตรวจและ findings: reports/audit_results.json และ reports/audit_*.md',
        '- คำถาม/คำตอบ/เวลา: docs/results/qa_gold_final_2026-10-02.json; เฉลย development: tests/qa_gold.json',
        '- การแก้ที่มี backup: docs/results/approved_name_prerequisite_ingest.json, approved_prerequisite_ingest.json และ ai_identity_cover_review.json',
        '- API/UI: docs/results/ui_observations_2026-10-02.json, ui_api_agreement_2026-10-02.json และ screenshots/',
        '- OCR metrics เดิมยังแยกจากการแก้ DB: docs/results/a1_field_metrics.json; ใช้เฉพาะแถวที่ visually verified ไม่ใช้ OCR ตรวจตัวเอง',
        '- checkpoint ที่เป็นแหล่งเดียว: docs/PROGRESS.md ที่ root ของ feature repository; ทำต่อจาก NEXT ACTION', '']
    args.output.write_text('\n'.join(lines),encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
