"""Generate a bounded Thai evidence report from saved results, not model claims."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repository', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    a = p.parse_args()
    root, evidence = a.repository.resolve(), a.evidence.resolve()
    inventory = read(evidence/'inventory_final.json')
    audit = read(evidence/'audit_release/audit_results.json')
    gold = read(evidence/'checks_release/gold.json')
    old = read(evidence/'checks_release/old2560.json')
    frozen = read(evidence/'frozen_release.json')
    checks = read(evidence/'checks_release/checks.json')
    reference = read(evidence/'requirement_qa_release.json')
    terms = read(root/'docs/results/old2560_book_terms_verified.json')
    ledgers = {x['profile'].replace('_','-').casefold(): x for x in terms['ledger']}
    profiles = []
    for profile in inventory['profiles']:
        identity = profile['profile']
        dataset = next((d for d in audit['datasets'] if d['database'] == profile['database']), None)
        issues = dataset['findings'] if dataset else []
        term_pages = {t['pdf_page'] for t in ledgers.get(identity.casefold(), {}).get('terms', [])}
        refs = [c for c in reference['cases'] if c['profile'] == identity]
        reviewed_pages = term_pages | {r['page_number'] for c in refs for r in c['response'].get('rows', [])}
        if profile['source_file']:
            reviewed_pages.add(1)
        qa = [c for c in gold['cases'] if c['identity'] == ('legacy' if identity == 'legacy-course-catalog' else identity)]
        old_cases = [c for c in old['cases'] if c['identity'] == identity]
        profiles.append({'profile': identity, 'rows': profile['counts'], 'high': len(issues), 'med': 'n/a',
                         'statuses': dict(Counter(f['status'] for f in issues)),
                         'reviewed_pdf_pages': sorted(reviewed_pages), 'pages': len(reviewed_pages) if reviewed_pages else 'n/a',
                         'gold': {'passed': sum(c['passed'] for c in qa), 'n': len(qa)},
                         'old_dev': {'passed': sum(c['passed'] for c in old_cases), 'n': len(old_cases)},
                         'source_references': {'passed': sum(c['passed'] for c in refs), 'n': len(refs)},
                         'fidelity_schema_missing': profile['missing_fidelity_columns']})
    summary = {'scope': 'regression/source-reviewed subsets, NOT full-book independent accuracy', 'profiles': profiles,
               'audit_findings': dict(Counter(f['status'] for d in audit['datasets'] for f in d['findings'])),
               'frozen': frozen['summary'], 'unique_failed_frozen': sorted({c['profile']+'/'+c['id'].split('/')[1] for c in frozen['cases'] if not c['passed']}),
               'gold_latency': gold['latency'], 'shared_checks_exit_codes': {c['name']: c['exit_code'] for c in checks['jobs']},
               'dependencies_unchanged': checks['dependencies_unchanged']}
    (evidence/'handoff_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# ผลตรวจและส่งต่องาน week11', '',
             'งานอยู่ใน branch `week11_thanapat` ยังไม่ commit/push/PR/merge และไม่แก้ main รายงานนี้แยกผลที่สังเกตจากความถูกต้องทั้งเล่ม ไม่อ้างคะแนนอาจารย์', '',
             '## ผลแยกตามหลักสูตร', '',
             '| profile | แถว course / plan | HIGH / MED | หน้า PDF ที่ตรวจภาพสะสม | gold regression | old development | อ้างข้อบังคับ | ยังไม่ครบ |',
             '|---|---|---|---|---|---|---|---|']
    def fraction(value):
        return f"{value['passed']}/{value['n']}" if value['n'] else 'n/a'
    for item in profiles:
        rows = item['rows']
        lines.append(f"| {item['profile']} | {rows.get('course', rows.get('courses','n/a'))} / {rows.get('plan_item','n/a')} | {item['high']} / n/a | {item['pages']} | {fraction(item['gold'])} | {fraction(item['old_dev'])} | {fraction(item['source_references'])} | {'ตัวตน/ต้นฉบับ/ไม่มี UI' if item['profile']=='legacy-course-catalog' else 'ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม'} |")
    lines += ['', 'HIGH เป็นจำนวน finding รวม FAIL/NEEDS_REVIEW/SKIPPED ไม่ใช่จำนวนคำตอบผิด harness นี้ไม่มีการประเมิน MED แยกจึงเป็น n/a จำนวนหน้าคือภาพปก + academic-plan ledger รุ่นเก่า + graduation-reference pages ไม่ใช่ครบทุก field ของแต่ละหน้า', '',
              f"audit: {len(audit['datasets'])} datasets (รวม staged DSBA อีกสองไฟล์), FAIL {summary['audit_findings'].get('FAIL',0)}, incomplete {sum(summary['audit_findings'].get(k,0) for k in ('SKIPPED','NEEDS_REVIEW'))}; missing curricula `{audit['missing_curricula']}` exit1 จงใจ fail loudly ไม่ตีความว่าเป็นจำนวนข้อสอบผิด ดู [raw](audit_release/audit_results.json) และ audit_*.md เฉพาะ Summary/HIGH", '',
              '## สาเหตุและการแก้', '',
              '1. **code bug — citation:** SQL yearly aggregates ไม่มี pages และ frontend จับคู่ PDF/folio จากคนละ sorted lists เพิ่ม `page_evidence` ที่เป็นคู่จาก SQLite และไม่เดา folio เมื่อหลักฐานไม่เป็นคู่ unit/UI ทั้ง 13 profile ตรวจแล้ว; ไม่ยืนยัน citation ของทุก course/metadata',
              '2. **code bug — startup:** เคยยอมรับ backend คนละโฟลเดอร์หรือ Ollama ที่ไม่มีโมเดล เพิ่ม root/model/DB readiness, null-model guard และ owned start/stop ด้วย PID+UTC ticks ทดสอบ refusal แล้ว PID server เดิมไม่เปลี่ยน',
              '   แยก handoff/backups/verification folders ออกจาก runtime DB discovery และ audit เพื่อไม่เลือก snapshot เป็น production catalog ทดสอบ export bundle ใน app แล้วจำนวน active catalog คงเดิม',
              '3. **data-ingest gap — graduation references:** ตรวจภาพ 7 หน้า เก็บ regulation references ใน immutable `program_requirement` ทั้ง 13 profile ผ่าน source-hash guarded ingest ไม่ใช้ runtime JSON แทน SQL แยก production source-review จาก test labels แสดงข้อจำกัด appendix/3.5 ปี ไม่อนุญาตจบ/ลงทะเบียน',
              '4. **schema migration gap:** current IT/BIT 4 profile ขาด fidelity fields เพิ่ม columns แบบ NULL unknown ทุก plan value เดิมคงอยู่ ไม่อ้างว่า column ที่เพิ่มเป็น fact ที่ตรวจแล้ว legacy คนละ schema จึงไม่ยัด columns เหล่านี้ให้ legacy',
              '5. **OCR loss / data coverage — ยังเปิด:** ชื่อ หมวด description และ prerequisites ยังตรวจไม่ครบทุกเล่ม legacy มี 6147 page-fragment rows แต่ตัวตน/ปี/source fidelity ไม่ครบ curated fixes ไม่เพิ่ม OCR F1',
              '6. **source ambiguity / unavailable inputs — ยังเปิด:** หน้าเกณฑ์จบอ้างภาคผนวกซึ่งยังตรวจไม่ครบ ไม่รับรองแผน 3.5 ปี/ตารางเปิดวิชา ไม่พบ source ของ AI เก่า, same-year revision หรือ dual degree; registration availability ไม่เดา', '',
              'การนับ 61 changed/added fields ในรายงานก่อนแก้คือ factual57 + presentation4 ไม่ใช่ 61 คำตอบผิด ผล provenance ใหม่ต้องอ่าน raw ไม่เหมารวมทั้ง pipeline IT 06016422 ที่ตรวจไว้คืออินเทอร์เน็ตของสรรพสิ่ง IT.pdf PDF35/book30 และ42/book37 ไม่แก้ซ้ำโดยดู filename', '',
              '## การยืนยันและตัวหาร', '',
              '| รายการ | ผล | ความหมาย / ข้อจำกัด |', '|---|---|---|']
    for job in checks['jobs']:
        count = re.search(r'Ran (\d+) tests', job.get('stderr',''))
        label = f"{count[1]} tests" if count else 'ดู raw counts'
        lines.append(f"| {job['name']} | exit {job['exit_code']} · {label} | [คำสั่งและผลดิบ](checks_release/checks.json) |")
    lines += [f"| regulation reference API+/ask | {reference['summary']['passed']}/{reference['summary']['n']} คู่คำถาม | 7 source-reviewed references; ไม่ใช่ full graduation accuracy |",
              f"| frozen historical regression | {frozen['summary']['passed']}/{frozen['summary']['n']} requests, 3 runs | 60 unique cases ของ current5profiles; 3 unique failures ไม่แก้ labels |", '',
              'frozen failures: '+', '.join(summary['unique_failed_frozen']), '',
              'failure มาจากเฉลย internal placeholder identifiers ไม่ตรง schema รุ่นปัจจุบัน เก็บ failures ให้ตรวจ ไม่แก้ gold เพื่อให้ผ่าน ชุดนี้ DB-derived และเคยใช้ debug แล้ว ไม่ใช่ independent held-out อิสระ อีก 9 catalogs ไม่มี frozen set รวม old6profiles/legacy/BITcurrent2 ยังไม่ประเมิน final independent coverage มี expected-abstain เพียง 2 ข้อต่อ profile จึงเป็นหลักฐานอ่อน ไม่เท่ากับ book-wide absence precision/recall', '',
              'OCR CER/WER: ใช้ได้เฉพาะ transcription ที่เป็นอิสระ Field extraction correctness/completeness แยกจาก retrieval/answer/citation scores ผลรวม regression ไม่ใช่ full-book field accuracy; independent end-to-end accuracy/citation coverage ทุกหลักสูตรยัง n/a', '',
              '## เวลา', '',
              '| เงื่อนไข | n | median | p95 | ข้อจำกัด |', '|---|---|---|---|---|']
    for key, timing in gold['latency'].items():
        lines.append(f"| gold structured SQL, cache group {key} | {timing['n']} | {timing['median_ms']:.2f} ms | {timing['p95_ms']:.2f} ms | L3/L4 ยากและ generation ยังไม่วัด |")
    lines += ['| real UI unknown Qwen | 1 | request 11,892 ms / server 11,886 ms | n/a | ไม่ควบคุม warm/cache; >5s จึงไม่อ้าง bonus |',
              '| OCR/parse/index/ingestion แยก stage | n/a | n/a | n/a | งาน preprocessing แยกจาก per-question แต่ยังวัดไม่ครบ |', '',
              'paired_request_elapsed_ms ใน graduation tests คือ /api/ask + /ask สองคำขอ ไม่ใช้เป็น latency ของคำถามเดียว Cold backend restart ผ่านใน new venv แต่ Ollama ของผู้ใช้ยังทำงานอยู่ ไม่เรียกเป็น cold model generation', '',
              '## แอปจริงและ README', '',
              '- UI yearly totals 13/13 และ regulation references 13/13 ในแต่ละ selector/plan; source year/foliopairs/caveats ตรง source-reviewed subset [raw](graduation_ui.json)',
              '- new environment ใช้โค้ด uncommitted ปัจจุบัน new Python venv และ database snapshots 14 catalogs; PDFs เป็น hardlinks ต้นฉบับที่ไม่แก้ ไม่ใช่ freshly reconstructed OCR; qwen service เดิมพร้อมอยู่ [preflight](isolated_preflight_final.json)',
              '- desktop1280/mobile390 ไม่พบ horizontal overflow ในกรณีที่ตรวจ; idle/loading/success/missing-evidence/error ตรวจกับเว็บจริง ดู [UI](isolated_ui.json), [desktop](isolated_desktop.png), [mobile](isolated_mobile.png) และ prior UI suite ที่ frontend dependencies ไม่เปลี่ยน',
              '- new isolated API fact/remove/failure/version counterfactuals 5/5, production hashes ไม่เปลี่ยน [raw](requirement_isolation.json)',
              '- runtime bundle export/restore ตรวจ SHA/integrityและrefuse overwrite ไม่ใช่ GT ไม่รวม PDF/eval labels; local-only artifact ไม่ publish DB',
              '- rollback backup dry run17/17 (13 requirement+4schema) ผ่าน isolated rollback fixtureผ่าน ไม่ได้ rollback liveDBจริง; OneDrive output lock สองครั้งตรวจ partial/stage/backup/live แล้ว resume ที่localTEMP ไม่ reset Git/ไม่ทับข้อมูลโดยเดา',
              '- README หลักเขียนใหม่โดยคงวัตถุประสงค์/รหัสสมาชิกเดิม แยก setup/routine/rebuild ใช้relativelinks/sanitized.env; ไม่แก้ generated Lab09 EVAL หรืองาน ocr_system เดิม', '',
              'ยังไม่ยืนยัน: fresh OCR/full dependency installation บนเครื่องใหม่, initial model downloads, physical phone/screen reader/OS อื่น, PDF viewer ในแอปที่ก่อนหน้านี้แสดงว่าง, program-metadata citation บางคำถาม (ITold PDF33ยังไม่ยืนยันfolio/source support), full appendix, fresh independent frozen final evaluation/seed stability/complete L1–L4 challenge', '',
              '## Rubric และงานถัดไป', '',
              '[requirements → implementation → evidence → gap](REQUIREMENTS.md) ยืนยัน P2 weights20/20/20/30/10, accuracy bandsตามsourceและขอบที่ไม่ชัด โบนัสรวม+10 ไม่คิดคะแนนเอง มีL1/L2 subsetsกับold/new code comparison บางส่วน L3 accelerated/graduationcheckและL4 unavailable sourcesยังn/a', '',
              'ขั้นถัดไป: source-review program summary citationsและภาคผนวกที่กำหนดgraduation/prerequisites ทั้ง7booksทีละbatch → independentGT/questionmatrix → freezeheldoutที่ไม่เคยdebug → วัด retrieval/answer/completeness/citation/abstentionและcold/warmhard-questionlatencyแยกระดับ ห้ามใช้DB-derivedlabelsแทนsource GT', '',
              'slides/presentation PDF/narrated video deferred ไม่มีcommit/push/merge main. ตามประกาศล่าสุดที่ผู้ใช้แจ้ง วันที่12ตุลาคมเป็นวันที่เสนอมีเงื่อนไขไม่ยืนยัน. Memoryเดียวคือ [docs/PROGRESS.md](../../PROGRESS.md)', '']
    (evidence/'WEEK11_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Report profiles:', len(profiles), 'frozen failures:', summary['unique_failed_frozen'])


if __name__ == '__main__':
    main()
