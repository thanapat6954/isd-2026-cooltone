# ผลแก้ elective-list และตรวจ LIVE source chain

## สาเหตุและการแก้

1. Validator อนุญาต synonym `elective` เฉพาะ prerequisite catalog จึงปฏิเสธ course-list ที่ตั้งใจกรอง `ctype`. แก้ให้รองรับเฉพาะ predicate ของ `ctype` เมื่อคำถามระบุวิชาเลือกจริง รวม `LOWER/LIKE/IN`; filter ชื่อหรือรายละเอียดที่โมเดลเพิ่มเองยังถูกปฏิเสธ.
2. Repair SQL เดิมมี named bindings ที่ไม่ตรง markers. ไม่ลบ bindings ที่เกินและไม่คลาย validation: เพิ่ม markers/keys ใน error และ previous bindings ใน repair prompt พร้อมกำหนดว่า SQL ไม่มี marker ต้องส่ง `parameters=[]`. Tests ยืนยัน fail-closed และ matching bindings. รอบคำถามนี้ใช้ deterministic SQL จึงไม่ได้พิสูจน์ความสามารถ real-LLM repair ทั่วไป.
3. LIVE plan_item ปี3/ภาค1 มี names/credits_raw/placeholder metadata เป็น null แม้ production approval มี source fields; ดู [BIT-2565-plan-corrections.json](../ocr_final/data/source_reviews/BIT-2565-plan-corrections.json) profile no-coop/PDF28. เตรียม [separate field approval](../ocr_final/data/source_reviews/BIT-2565-no-coop-year3-fields.json) จากภาพต้นฉบับ ไม่ใช่ raw OCR/evaluation labels/isolated answers.
4. View `v_study_plan` เก่ายังไม่ project fidelity columns จึงไม่ส่ง raw placeholder แม้ซ่อม plan_item แล้ว. แก้ generic SQL ให้ retrieve fields จาก matching plan_item.id ใน selected SQLite; ไม่มี factual JSON overlay. ชื่อหมวดใน UI ใช้ explicit language row name ก่อน stale broad category.

## Source และการซ่อมข้อมูล

- ตรวจ actual visible PDF28/book23 ตารางล่างปี3/ภาค1 6แถว/18หน่วยกิต แผนไม่สหกิจศึกษา; plan identity ต่อจาก independent review PDF26 section3.1.4.1. ไม่ใช้ข้อเท็จจริงจาก coop.
- Names/English names/credits/patterns/wildcard `96644xxx` และทางเลือก `3(3-0-6) หรือ 3(2-2-5)` มี source support. PDF-page และ printed-page ตรวจแยกกัน.
- Targeted transaction เปลี่ยน22 metadata fields ใน plan_item26–31 เท่านั้น. Counted credits, catalog facts, alternative groups, prerequisites, internal generated code และแถวอื่นคงเดิม. ไม่ replace DB ทั้งก้อน.
- SQLite backup/stage/integrity/idempotence/unchanged-facts ผ่าน: [repair result](results/bit_manifest_controls_20261010/live28-targeted-repair/result.json); backup [before.db](results/bit_manifest_controls_20261010/live28-targeted-repair/before.db), SHA256 `0a893a13200f2d5cd77272bcbd2341e07ee940d25682b35161a0415ed94509ac`.
- Rollback: ตรวจ current values เทียบ `changes[].new` ใน result ก่อน; ใช้ BEGIN IMMEDIATE ย้อนเฉพาะ22 fields เป็น `changes[].old` แล้วตรวจ integrity/foreign keys/unaffected rows. หากมี edit ใหม่ให้หยุด ไม่คัดลอก backup ทับ working DB อัตโนมัติ. Backup ใช้เป็นหลักฐานและ recovery source ไม่ใช่ wholesale replacement.
- Category field เก่าในรายละเอียด elective ยังเป็นหมวดเลือกเสรีและยังไม่ source-verified จากตารางนี้; prerequisites ไม่ได้ตรวจเพิ่ม. ไม่อ้างว่า every field/source claim ผ่าน.

## Actual development questions และผล

ทุกข้อเลือก BIT/2565/no-coop; ไม่ใช่ held-out. Same3uniquequestions ×2endpoints =6requests ต่อรอบ.

| คำถามจริง | ก่อนแก้ที่บันทึก | หลังแก้ LIVE | DB consistency / source support / completeness / citation |
| --- | --- | --- | --- |
| หลักสูตร BIT พ.ศ.2565 แผนไม่สหกิจศึกษา ปี 3 ภาคการศึกษาที่ 1 มีวิชาอะไรบ้างและรวมกี่หน่วยกิต | LIVE restart รอบแรกแสดง6contributionsแต่placeholderไม่มีชื่อ/creditpattern | มี6ชื่อ/credits/patterns;96644xxx; `3 + 3 + 3 + 3 + 3 + 3 = 18` | requested fieldsครบ; source tableรองรับ; citation PDF28/book23จริง |
| หลักสูตร BIT พ.ศ.2565 แผนไม่สหกิจศึกษา ปี 3 ภาค 1 มีวิชาเลือกอะไรบ้าง แสดงรหัส ชื่อและรูปแบบหน่วยกิต | isolated422: elective literal rejection แล้ว binding mismatch; ก่อนroutingfixตอบyear total18ที่ไม่เกี่ยวข้อง | `96644xxx วิชาเลือกด้านภาษาและการสื่อสาร — 3 หน่วยกิต (3(3-0-6) หรือ 3(2-2-5))` | requested fieldsครบ/SQLite-backed; source supportตรง; UI detail categoryยังunverified |
| หลักสูตร BIT พ.ศ.2565 แผนไม่สหกิจศึกษา วิชารหัส 06036123 ชื่ออะไรและมีกี่หน่วยกิต | recorded source factsถูกอยู่แล้ว ไม่อ้างว่าแก้ใหม่ | `06036123 เทคโนโลยีกลุ่มเมฆ (CLOUD TECHNOLOGY), 3 หน่วยกิต, L-P-S 3-0-6` | requested fieldsตรงSQLite/source PDF28/book23 |

HTTP200ทั้ง6 isolatedและ6finalLIVE, technical0. Requested field completenessผ่าน6/6; ไม่เท่ากับ independent accuracy ของทุกข้อหรือทุกclaim. Extra category claim ยังต้อง source review. SQL/retrieved rows/full actual answers/status/timing ไม่แก้ข้อความอยู่ [final LIVE raw evidence](results/bit_manifest_controls_20261010/live28-final-results.json), [initial LIVE gap](results/bit_manifest_controls_20261010/live28-validated-results.json), [intermediate repair](results/bit_manifest_controls_20261010/live28-repaired-results.json), และ `bit-wildcard28-validated-20261010/api-results.json`.

Actual isolatedUIและLIVEUI แสดง names/patterns/formula; citation clicks เปิด visible page28/book23. [LIVE answer screenshot](results/bit_manifest_controls_20261010/live28-final-ui.png), [LIVE source screenshot](results/bit_manifest_controls_20261010/live28-final-source.png), และ AX snapshots ใกล้กัน. Loading state สังเกตจริงระหว่าง request. Restart ใช้ scripts/start_web.ps1 → verified ownership → stop_web.ps1 → start_web.ps1; final listener PID46164. ไม่หยุด Ollama หรือ models.

## Verification ปัจจุบัน

- New dependency-locked run:323unit/30schema/7frontend/70gold (14profiles×5)/65old2560 QA/14provenance/6version sets ผ่าน;7jobs exit0/dependencies_unchanged=true. [checks](results/bit_manifest_controls_20261010/elective-shared-final/checks.json).
- ก่อนหน้านี้321unitมี1prerequisite LIKE synonym error: retained [failed checks](results/bit_manifest_controls_20261010/elective-shared-failed/checks.json), ไม่ลบผลที่ไม่ผ่าน. Focused41ก่อนfirstfix/38หลังfinalchangesเป็นคนละscope ไม่ใช่ accuracy denominator.
- Read-only audit16datasets: FAIL1372/incomplete4881/missingcurricula=[]; [after reports](results/bit_manifest_controls_20261010/elective-audit-after). HIGH BITno-coop prerequisite coverage4/304และfull-source-fidelityยังopen. ไม่ใช้ test pass ปิดsource gaps.
- เวลา6finalLIVErequestsเป็น structured SQLite paths ไม่ใช่ difficult-LLM benchmark; cold/warm model conditionsไม่ได้ควบคุม ไม่อ้าง <5s challenge จากรอบนี้.

## งานต่อที่ได้ทำและ gaps

- Fresh relevant PDF32 หนึ่งattempt/fullpage200DPI/temp0/model+prompt identitiesเดิม: model200แต่empty11.46s;0usablepages. ตรวจ actual fullPNGมี12course rowsในY1/S2และY2/S1/18+18 และbook27 ไม่ใช่ blank/irrelevant. ไม่parse/buildจากempty; [failed checkpoint](results/bit_manifest_controls_20261010/bit-relevant32-20261010/manifest-extraction.json). ไม่ retry28หรือ31.
- Raw OCR กับ approved LIVE corrections อยู่คนละทาง:22fieldrepairsไม่ใช่OCRaccuracy improvement. No held-out answersเข้า production.
- Independent evaluation preparation ตรวจเฉพาะ index/runner metadata: data/ground_truth/README.md ระบุว่า qa_goldเป็นdevelopment, historical questionsสร้างจากDB,ยังไม่มีnewsource-grounded frozenครบL1–L4. ไม่เปิด held-out expected answers/ไม่เรียก DB-derived robustness เป็น independent final evaluation.
- ยังไม่วัดครบ: full relevant-page reconstructionทุกprofile, broader prerequisites/category/conditions, untouched source-grounded held-out, real-LLM binding/fallback mutation/failure checks, controlled difficult latency, process recoveryครอบคลุม, legacy identity, first-machine installation. Verified-owned LIVE restartไม่ใช่ clean-first-machine install.

Branch week11_thanapat; existingedits preserved/no commit/push/merge/main/slides/video. รายละเอียด NEXT/action/jobs อยู่ authoritative [PROGRESS.md](PROGRESS.md) เท่านั้น.

## ตรวจซ้ำหลังกลับมาทำงาน วันที่ 11 ตุลาคม 2026

ตรวจ dependency files ของ locked run 514 ไฟล์: ไม่เปลี่ยนทั้ง514ไฟล์ จึงใช้ผล regression เดิมได้โดยไม่เรียกซ้ำโดยไม่มี dependency change. ไม่ใช่การอ้างผลก่อนแก้เป็นผลของ code ใหม่. ไม่มี OCR/check/probe jobs ค้าง; backend เดิมหยุดแล้ว จึงเรียก LIVE `scripts/start_web.ps1` และยืนยัน listener8000/PID10092 พร้อม log `work/web/backend-25691011-001749-835.stderr.log`.

Same3uniquequestions ×2endpoints =6requests ใหม่: ตรวจ actual answers แล้ว requested fields ครบทั้ง6; HTTP200ทั้ง6, latency370.84–409.23ms (structured SQLite paths, ไม่ใช่ controlled difficult-LLM benchmark). Names/credits/wildcard96644xxx/สองcreditpatterns/formula18 และชื่อ CLOUD TECHNOLOGY ยังตรงผล source review เดิม. [raw results ใหม่](results/bit_manifest_controls_20261010/live28-resumed-20261011.json).

การเรียก browser control เพื่อตรวจ viewer ซ้ำถูก policy ปฏิเสธ จึงไม่พยายาม bypass และไม่อ้างว่าตรวจ UI ใหม่ในวันที่11แล้ว. ภาพ LIVE และ citation navigation ที่ตรวจจริงใน batch ก่อนหน้ายังเก็บไว้; code dependencies ไม่เปลี่ยน. Category detail ยังไม่ independently source-verified และ real-LLM repair ยังไม่วัดเพิ่ม.
