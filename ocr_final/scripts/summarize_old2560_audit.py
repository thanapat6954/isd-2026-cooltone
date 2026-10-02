"""Summarize raw six-profile evidence without converting coverage gaps to passes."""
from collections import Counter
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parent
RESULTS=REPO/'docs/results'


def read(name):return json.loads((RESULTS/name).read_text(encoding='utf-8'))


def main():
    db=read('old2560_db_verified_v2.json')
    baseline=read('old2560_baseline.json')
    terms=read('old2560_book_terms_verified.json')
    qa=read('old2560_qa_complete.json')
    isolation=read('old2560_version_isolation_complete.json')
    existing=read('old2560_existing_gold_complete.json')
    audit=json.loads((ROOT/'reports/audit_results.json').read_text(encoding='utf-8'))
    rows=[]
    for profile in db['profiles']:
        name=profile['profile']
        term=next(r for r in terms['results'] if r['profile'].replace('_','-')==name)
        book=next(r for r in terms['ledger'] if r['profile'].replace('_','-')==name)
        findings=next(d['findings'] for d in audit['datasets'] if d['database']==profile['database'])
        severity=Counter(f['severity'] for f in findings if f['status'] in ('FAIL','NEEDS_REVIEW','SKIPPED'))
        old=next(p for p in baseline['profiles'] if p['profile']==name)
        structural=profile['integrity']=='ok' and not any(profile[key] for key in ('required_columns_missing','duplicate_plan_keys','orphan_prerequisites','missing_names','plan_missing_names','plan_readability_candidates'))
        rows.append({'profile':name,'HIGH':severity['HIGH'],'MED':severity['MED']+severity['MEDIUM'],
                     'counts':profile['counts'],'structure_pass':structural,'semester_comparison_pass':term['passed'],
                     'pages_reviewed':sorted({t['pdf_page'] for t in book['terms']}),
                     'printed_pages_reviewed':sorted({t['printed_page'] for t in book['terms']}),
                     'semesters_passed':sum(t['passed'] for t in term['terms']),'semesters_n':len(term['terms']),
                     'credits':term['db_total'],'printed_credits':term['printed_total'],
                     'qa':qa['summary'][name.upper().replace('NO-COOP','no-coop').replace('-COOP','-coop')],
                     'frozen_inputs_unchanged':old['protected_inputs']==profile['protected_inputs'],
                     'remaining':'full names/category/type/prerequisite and book-wide absence evidence unmeasured'})
    if not qa['dependencies_unchanged'] or not isolation['dependencies_unchanged']:raise ValueError('Unstable final evidence')
    if not all(r['structure_pass'] and r['semester_comparison_pass'] and r['frozen_inputs_unchanged'] and r['qa']['passed']==r['qa']['n'] for r in rows):raise ValueError('Six-profile evidence has a failure')
    total=sum(r['qa']['n'] for r in rows)
    result={'status':'targeted repairs verified; complete independent book audit remains OPEN','profiles':rows,
            'development_qa':{'passed':sum(r['qa']['passed'] for r in rows),'n':total},
            'existing_gold':{'passed':sum(r['passed'] for r in existing['summary'].values()),'n':sum(r['n'] for r in existing['summary'].values())},
            'version_pairs':{'passed':sum(p['passed'] for p in isolation['pairs']),'n':len(isolation['pairs'])},
            'unmeasured':['full independent name/category/type accuracy','all course-description prerequisites','genuine book-wide course absence','final held-out accuracy/seed stability','cold LLM difficult-question latency','coherent specialization-bundle recommendation'],
            'cause_groups':{'code_bug':['Thai nominal matching and missing ambiguity clarification','guard rejected database-resolved name-only prerequisite codes','incidental course name overrode program selector','wildcard+ordinal collision across elective families','review ingest updated catalog but wrong plan-name columns'],
                            'data_ingest_bug':['IT coop fidelity migration was source-blocked','missing/distorted plan options restored from separately reviewed full terms','BIT prerequisite printed folio cannot use a fixed appendix offset'],
                            'OCR_loss':['missing IT network/project options and displaced names','specialization headings used as row names','IT lecture/lab-hour patterns wrong despite correct integer credits','DSBA shortened wildcard and BIT alternative label loss'],
                            'source_ambiguity':['IT specialization groups are mutually exclusive bundles; options are displayed, not a cross-branch registration recommendation','absence cannot be asserted from incomplete description coverage','BIT coop06036018 Thai space is printed; not changed']}}
    (RESULTS/'old2560_audit_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# ผลตรวจหลักสูตรเก่า พ.ศ. 2560','',
           '## Summary','',
           f'ตรวจทั้งหก profile ก่อนแก้ข้อมูลแล้ว โดยเก็บ baseline แยกไว้ งานแก้เฉพาะจุดผ่าน development Q&A {total}/{total} ข้อ แต่ยังไม่ยืนยันหนังสือทั้งเล่มหรือ held-out accuracy',
           'HIGH/MED นับจากรายงาน audit_all ที่ยังเปิดอยู่ ไม่ใช่จำนวนคำถามที่ตอบผิด แต่ละ profile มี HIGH ด้าน prerequisite coverage และ full source fidelity',
           'จำนวนหน้าด้านล่างหมายถึงหน้าตารางแผนการศึกษาที่ตรวจรหัส ตัวเลือก credit/hour pattern ผลรวม และเลขหน้า ไม่ใช่การตรวจทุก field/ทุกคำอธิบายรายวิชา','',
           '| profile | HIGH | MED | PDF ที่ตรวจ / หน้าในเล่ม | ภาคการศึกษาที่ตรง | หน่วยกิต DB / เล่ม | Q&A ที่ผ่าน | ยังไม่ยืนยัน |',
           '|---|---:|---:|---|---:|---:|---:|---|']
    for r in rows:
        pages=', '.join(map(str,r['pages_reviewed']))+' / '+', '.join(map(str,r['printed_pages_reviewed']))
        lines.append(f"| `{r['profile']}` | {r['HIGH']} | {r['MED']} | {pages} | {r['semesters_passed']}/{r['semesters_n']} | {r['credits']}/{r['printed_credits']} | {r['qa']['passed']}/{r['qa']['n']} | ชื่อ/หมวด/type/prerequisite ครบทั้งเล่ม n/a |")
    lines+=['','## HIGH','',
            '- ทุก profile: ยังตรวจคำอธิบายวิชาบังคับก่อนและ field ทั้งเล่มไม่ครบ การไม่มี prerequisite edge ไม่ใช่หลักฐานว่าไม่มีวิชาบังคับก่อน',
            '- งานที่เคยติด IT coop PDF36/40 และ BIT coop PDF30 แก้ผ่านข้อมูล ingest ที่ตรวจแยกและสำรอง DB แล้ว ไม่แก้ frozen OCR/A0/A1/held-out',
            '', '## สาเหตุและงานแก้','',
            '- code bug: แก้ name matching ภาษาไทยให้คืนตัวเลือกเมื่อกำกวม; guard อนุญาตเฉพาะรหัสที่ resolver ตรวจจาก DB แล้ว; ให้ตัวเลือกหลักสูตรชัดเจนมีลำดับก่อนคำในชื่อวิชา; แยก elective slot ที่ wildcard/เลขลำดับซ้ำ; อัปเดตชื่อใน plan_item จริง',
            '- data-ingest bug: ย้าย IT coop ไป schema fidelity ครบหก column และคืนแถว/กลุ่มตัวเลือกผ่าน full-term reviews; บันทึก BIT PDF174 เป็นหน้า97ในเล่มหลังตรวจภาพ ไม่ใช้ offset เดา',
            '- OCR loss: ตัวเลือก IT ขาด ชื่อเหลื่อมและหัวข้อแขนงปน; hour pattern ผิดแม้ผลรวมถูก; DSBA wildcard สั้นลงและชื่อ alternative BIT หาย แก้เฉพาะ curated ingest จึงไม่ใช่ OCR accuracy ที่ดีขึ้น',
            '- source ambiguity: ตาราง IT แยกแขนงเป็น bundle ที่เลือกอย่างใดอย่างหนึ่ง การแสดงทุกตัวเลือกไม่ได้อนุญาตให้ผสมแขนง; ช่องว่างในชื่อ BIT06036018 อยู่ในเล่ม จึงไม่แก้',
            '', '## หลักฐานและวิธีตรวจซ้ำ','',
            '- [baseline](../../docs/results/old2560_baseline.json), [เปรียบเทียบภาคการศึกษา](../../docs/results/old2560_book_terms_verified.json), [DB](../../docs/results/old2560_db_verified_v2.json)',
            '- [development Q&A](../../docs/results/old2560_qa_complete.json), [gold เดิม](../../docs/results/old2560_existing_gold_complete.json), [version isolation](../../docs/results/old2560_version_isolation_complete.json), [tests](../../docs/results/old2560_regressions_launcher_verified.json)',
            '- [UI ทั้งหก profile](../../docs/results/old2560_ui_observations.json), [UI ชื่อวิชา IT หลังแก้](../../docs/results/old2560_ui_final_name_question.json), [UI วิชาบังคับก่อนจากชื่อ](../../docs/results/old2560_ui_name_prerequisite.json)',
            '- [ผลคำสั่งเปิด backend และ HTTP](../../docs/results/old2560_backend_start_verified.json), [Q&A หลัง restart](../../docs/results/old2560_backend_restart_probe.json)',
            '- ใช้ scripts/audit_all.py, scripts/audit_old2560.py, scripts/compare_old2560_book_terms.py, scripts/run_old2560_qa.py, scripts/run_qa_gold.py และ scripts/run_version_isolation.py โดยระบุ --app-root และ --output ตาม docs/PROGRESS.md',
            '', '## ค่าที่ยังไม่ได้วัด','',
            '- full field accuracy, prerequisite coverage ครบทั้งเล่ม และหลักฐานยืนยันว่าไม่มีรายวิชาจริง: n/a',
            '- held-out accuracy/seed stability และ cold LLM latency สำหรับคำถามยาก: n/a ชุดที่ใช้แก้เป็น development probes ไม่ใช่ held-out',
            '- version isolation ทดสอบคำถามเดียวกันใน2560/2565ทั้งหกคู่ ผลต่างของรหัสในDBไม่ใช่การรับรอง field ของเล่ม2565ครบทุกแถว',
            '- ไม่ได้รัน OCR ใหม่ ไม่เปลี่ยน input เดิม และไม่แตะ main; การสร้าง DB ใหม่จาก OCR เดิมล้วนยังอาจ fail ตามข้อมูลที่หาย ให้ใช้ reviewed ingest และ helper ที่ระบุไว้','']
    (ROOT/'reports/audit_old2560_summary.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Wrote six-profile evidence summary; full audit remains OPEN')


if __name__=='__main__':main()
