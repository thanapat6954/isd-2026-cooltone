# ผลการแก้ไข DB-only และหลักฐานก่อนส่งงาน

ผลนี้ยืนยันเฉพาะคำถามและแถวที่ทดสอบ ไม่ใช่ accuracy ของหนังสือทั้งเล่ม และไม่ใช่หลักฐานว่าไม่มี hallucination ทุกกรณี

## ผลการทดสอบที่สังเกตจริง

- unit 108/108, schema 30/30; isolated provenance 21/21, migration replay/rollback 13/13
- gold 70/70; old development 65/65; version isolation 6/6; cards 45/45
- provenance 14/14 profile: ค่า-field เพิ่ม/เปลี่ยนจาก SQL replay 0; unknown grounding 14/14
- unknown complete-answer latency median 3332.20ms / p95 5863.59ms (n=14); ใต้ห้าวินาที 13/14 ไม่ใช่ cold-model หรือ hard-question benchmark

## ผลตาม profile

| profile | HIGH / MED ที่ยังเปิด | gold | อ้างอิง PDF / ทั้ง PDF+หน้าเล่ม | latency gold median / p95 ms | frozen unique | unknown grounding / ms | UI |
|---|---:|---:|---:|---:|---:|---:|---|
| `legacy-course-catalog` | 6215 / 0 | 5/5 | n/a | n/a | n/a | 1/1 / 5863.59 | n/a |
| `AI-2566-coop` | 3 / 0 | 5/5 | 4/4 / 0/4 | 585.65 / 609.58 (n=4) | 12/12 | 1/1 / 2714.42 | สังเกตจริง |
| `BIT-2560-coop` | 2 / 0 | 5/5 | 4/4 / 4/4 | 579.25 / 588.82 (n=4) | n/a | 1/1 / 3519.99 | สังเกตจริง |
| `BIT-2560-no-coop` | 2 / 0 | 5/5 | 4/4 / 4/4 | 568.50 / 589.88 (n=4) | n/a | 1/1 / 2819.68 | สังเกตจริง |
| `BIT-2565-coop` | 4 / 0 | 5/5 | 4/4 / 0/4 | 580.72 / 587.71 (n=4) | n/a | 1/1 / 3348.43 | สังเกตจริง |
| `BIT-2565-no-coop` | 4 / 0 | 5/5 | 4/4 / 0/4 | 596.19 / 611.11 (n=4) | n/a | 1/1 / 3476.50 | สังเกตจริง |
| `DSBA-2560-coop` | 2 / 0 | 5/5 | 4/4 / 4/4 | 1163.03 / 1292.14 (n=4) | n/a | 1/1 / 4781.38 | สังเกตจริง |
| `DSBA-2560-no-coop` | 2 / 0 | 5/5 | 4/4 / 4/4 | 1208.67 / 1233.17 (n=4) | n/a | 1/1 / 4034.33 | สังเกตจริง |
| `DSBA-2565-coop` | 3 / 0 | 5/5 | 4/4 / 4/4 | 565.35 / 583.99 (n=4) | 11/12 | 1/1 / 4054.94 | สังเกตจริง |
| `DSBA-2565-no-coop` | 3 / 0 | 5/5 | 4/4 / 4/4 | 578.82 / 589.38 (n=4) | 10/12 | 1/1 / 3315.97 | สังเกตจริง |
| `IT-2560-coop` | 2 / 0 | 5/5 | 4/4 / 4/4 | 961.09 / 1077.89 (n=4) | n/a | 1/1 / 2831.09 | สังเกตจริง |
| `IT-2560-no-coop` | 2 / 0 | 5/5 | 4/4 / 4/4 | 607.00 / 850.55 (n=4) | n/a | 1/1 / 2774.12 | สังเกตจริง |
| `IT-2565-coop` | 5 / 0 | 5/5 | 4/4 / 3/4 | 1173.97 / 1231.44 (n=4) | 12/12 | 1/1 / 2500.09 | สังเกตจริง |
| `IT-2565-no-coop` | 4 / 0 | 5/5 | 4/4 / 3/4 | 1002.26 / 1045.16 (n=4) | 12/12 | 1/1 / 2483.31 | สังเกตจริง |

จำนวน citation วัดการมี locator ใน DB ของคำตอบที่มีหลักฐาน ไม่ใช่ semantic citation accuracy; คำตอบ uncertainty ไม่มีข้อมูลรองรับจึงไม่นับเป็น citation หรือ latency success

unknown grounding ตรวจว่า SELECT และค่าที่แสดงตรงกับ SQLite; ความครบถ้วนและความเกี่ยวข้องของคำตอบยังไม่ได้ตรวจด้วยเฉลยอิสระ

frozen เป็นเฉลยเดิมที่สร้างจาก DB ไม่ใช่ GT อิสระจากหนังสือและไม่ใช่ชุดใหม่ที่ไม่เคยใช้ debugging ผลซ้ำรวม cache ไม่ใช่การสร้างคำตอบใหม่จากโมเดลสามครั้ง เฉลยและ hash ไม่เปลี่ยน

## สาเหตุและสิ่งที่แก้

- code bug: runtime JSON overlay และ unknown free prose ถูกแทนด้วย SQL relations + structured row/field references; โมเดลส่งเฉพาะตำแหน่งหลักฐาน ไม่ส่งค่าที่จะแสดง
- data-ingest bug: IT 06016422 สลับกับชื่อความมั่นคงโครงสร้างพื้นฐาน แก้จาก IT.pdf PDF35/หน้าเล่ม30 และ PDF42/หน้าเล่ม37 เป็นอินเทอร์เน็ตของสรรพสิ่ง พร้อม correction history
- retrieval bug: query ไม่เลือก credits_raw/หน้าเล่มจากแถวแผน และไม่รองรับภาคเรียน/รหัสทั้งหมด แก้ parser/query; แยกปีหลักสูตรกับชั้นปี
- SQL repair: redundant identity filter บน program ถูก normalize เฉพาะ DB มีหนึ่งแถวและ safe SELECT ก่อน/หลังได้ค่าที่บันทึกเดียวกัน; false predicate, wrong exact ID, fact filters, multirow และ alias ผิดความหมายยังถูกปฏิเสธ
- inventory เดิม 61 ค่า-field แยก factual 57 / presentation 4; ตรวจ rendered page 16 หน้า ไม่ใช่จำนวนคำตอบผิด

## Migration และ rollback

สำรอง active DB ด้วย SQLite backup API พร้อม integrity/hash ก่อนแก้; เพิ่ม study_term/page/track/item/member/correction และ v_study_plan ใน isolated copy ก่อน deploy. JSON ที่ตรวจแล้วเป็น ingestion input เท่านั้น ไม่มี runtime factual overlay.
รันจาก repository root (PowerShell); แทนค่าตัวแปรด้วยตำแหน่ง live app ที่ใช้อยู่:

```powershell
$liveApp = '<path-to-live-app-with-PDFs-and-DBs>'
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/prepare_db_only.py --app-root $liveApp --output docs/results/new_backups.json
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/migrate_study_evidence.py --app-root $liveApp --backups docs/results/new_backups.json --output docs/results/new_migration.json
# Validate isolated copies before deployment; do not reuse the old baseline after DB changes.
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/verify_db_only_isolation.py --migration docs/results/new_migration.json --backups docs/results/new_backups.json --output docs/results/new_isolation.json
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/migrate_study_evidence.py --app-root $liveApp --backups docs/results/new_backups.json --deploy-evidence docs/results/new_migration.json --output docs/results/new_deployment.json --apply
# Dry run rollback first. Stop the verified backend before --apply.
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/rollback_db_only.py --app-root $liveApp --backups docs/results/db_only_backups.json --profile IT-2565-coop --output docs/results/rollback_check.json
# Repeat the same rollback command with --apply only when restoration is intended.
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/run_db_only_release_checks.py --app-root $liveApp --output-dir docs/results/new_release
```

rollback รักษา pre-rollback snapshot อีกชุด; หากย้อนทั้ง release ต้องคืนทุก DB ที่ต้องการและไฟล์ runtime จาก work/backups/db-only/<stamp>/code แล้วเริ่ม backend ใหม่. ไม่รัน rollback บน production ในการตรวจครั้งนี้; ทดสอบบน isolated DB แล้วเท่านั้น.

## ข้อจำกัดและงานที่ยังเปิด

- OCR loss / source ambiguity: prerequisite และ full-book names/category/การจบการศึกษายังไม่ครบ; current IT/BIT สี่ profile ยังขาด fidelity columns บางส่วน นอก migration นี้
- legacy มีหลายเล่มและยังไม่มีปี/ฉบับที่ยืนยัน; gold เป็น safety regression ไม่ใช่ content accuracy และไม่มี UI selector
- frozen DSBA สาม set cases ยังพึ่ง internal placeholder ID เดิม ไม่แก้เฉลยเพื่อให้ผ่าน; ดู frozen.json สำหรับค่าที่ขาด
- L3 DB-set calculation และ version isolation ไม่ยืนยัน full-book difference; L4 same-year revision/dual-degree ไม่มีเอกสาร, AI ฉบับเก่าไม่มี source; accuracy จึงเป็น n/a
- บาง metadata/aggregate citations ยังไม่มีหน้าเล่ม; ไม่อนุมาน offset เพิ่ม. แหล่ง general_education ยังไม่มี PDF provenance ครบ
- ตัวอย่าง UI unknown ของ IT-2560-no-coop อ้าง program metadata ที่ PDF33 แต่ยังไม่ได้ยืนยันว่าหน้านี้รองรับทั้งยอดรวมและระยะเวลาศึกษา ต้องตรวจ provenance เพิ่มก่อนนับ semantic citation accuracy
- unknown semantic accuracy, true absence precision/recall, cold model latency และ independent three-run generation stability ยังเป็น n/a; expected-abstain ชุด frozen มีเพียงสองข้อต่อ profile
- UI พบ loading/success/missing/error/recovery และ actual cards; การวัดครบทุกชนิดคำถามบนทุก viewport ยังเป็น n/a

- OCR metrics ไม่ได้เพิ่มจาก curated DB correction; original OCR ไม่เปลี่ยน และการทดสอบครั้งนี้ไม่ใช่การรัน OCR ใหม่

## ไฟล์หลักฐาน

- raw release: `docs/results/db_only_release_verified`; exit codes ใน release_checks.json
- backups/deployment/source renders/isolation/build replay: docs/results/db_only_*.json
- UI observations/screenshots: docs/results/db_only_ui*.json และ docs/results/screenshots/db_only_*.jpg
- CSV/JSON สำหรับส่งงาน: questions_answers_citations.csv / .json และ evaluation_summary.json ในโฟลเดอร์เดียวกับรายงานนี้
- checkpoint เดียว: docs/PROGRESS.md; feature branch audit/curriculum-challenge; ไม่ push หรือแก้ main
