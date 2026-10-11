# ผล repair loop ของชุด development เดิม

ทำงานบน week11_thanapat โดยไม่ commit/push/merge ไม่แก้ working SQLite, source PDFs, original OCR หรือ held-out. ใช้ curriculum-audit เพื่อแยกการแก้ retrieval ออกจากการเพิ่มข้อมูลหลักสูตร.

## ขอบเขตและผลที่วัด

รอบล่าสุดตรวจใหม่ 5 หมวด / 5 รูปแบบคำถาม / 70 profile-question cases / 140 HTTP requests ทั้งสอง endpoints ครบ 14 profiles. ไม่ใช่ 140 reasoning tasks. สองหมวด sequence/assessment มี 14 substantive, 38 partial/gap, 2 clarification, 2 legacy unreviewed. Math/filter 52/56 ตรง SQLite; อีก 4 กรณีเป็น legacy schema gap ไม่ใช่คะแนนความถูกต้องที่ผ่าน. Version-selection 28/28 เป็น clarification ไม่มีการคืนข้อเท็จจริงผิดฉบับ.

ตารางต่อไปมี 392 case identities ของชุด 14 หมวดเดิม โดย 9 หมวดใช้ conservative review ก่อนหน้า จึงไม่ใช่ผล fresh evaluation ทั้งชุด. substantive หมายถึงการตรวจข้อเท็จจริงหรือการคำนวณเทียบ SQLite ไม่ได้ยืนยันหนังสือทุกหน้า/printed folio ทุก citation. unreviewed ไม่ใช่ผ่าน.

| หมวด | ตอบถูกตาม DB | ข้อมูลขาด/ตอบบางส่วน | ขอให้ระบุ | ผิด/ไม่เกี่ยวข้องที่พบ | ขัดข้องที่พบ | ยังไม่ตรวจครบ |
|---|---:|---:|---:|---:|---:|---:|
| accelerated_plan | 0 | 0 | 0 | 0 | 0 | 28 |
| cross_version_trap | 0 | 0 | 28 | 0 | 0 | 0 |
| elective_alternatives | 22 | 4 | 0 | 0 | 0 | 2 |
| graduation_partial | 0 | 26 | 0 | 0 | 0 | 2 |
| minor_typo | 14 | 10 | 2 | 0 | 0 | 2 |
| misleading_assumption | 0 | 4 | 0 | 0 | 0 | 24 |
| multi_condition | 26 | 2 | 0 | 0 | 0 | 0 |
| name_paraphrase | 0 | 0 | 28 | 0 | 0 | 0 |
| plans_comparison | 0 | 2 | 0 | 0 | 0 | 26 |
| prerequisite_logic | 0 | 28 | 0 | 0 | 0 | 0 |
| semester_aggregation | 26 | 2 | 0 | 0 | 0 | 0 |
| shared_specialization | 12 | 14 | 0 | 0 | 0 | 2 |
| unsupported_description | 0 | 28 | 0 | 0 | 0 | 0 |
| version_comparison | 0 | 26 | 0 | 0 | 0 | 2 |

[ผลรายกรณีและที่มาของการจัดประเภท](results/relevance_loop_20261010/current-matrix.json). ไม่รายงาน accuracy รวมจากตารางนี้. Historical baseline 185 รายการยังไม่ครบ manual review แยกต่างหาก.

## Root causes และการแก้

- parsing/retrieval: informal prerequisite/sequence ไม่ถูกจัดเป็น relationship และ topic จาก model แกว่ง. ใช้ explicit name spans และ ordinal-aware matching กับ SQLite; ไม่เลือก course code โดยเดา.
- reasoning/coverage: หลายคู่รายวิชาต้อง clarification; คำตอบหลายแผนต้องบอกแผนที่ไม่มี matching evidence ไม่ซ่อนช่องว่าง.
- SQL validation: curriculum year ไม่ใช่ course-code filter; wildcard ว่างไม่อนุญาต. Binding และ validator เดิมยังคงอยู่.
- evidence selection: future exam/instructor teaching ไม่อยู่ใน supported schemas; คืนข้อจำกัดเฉพาะแทนชื่อวิชา/program totals.
- schema capability: legacy ไม่มี placement fields; ไม่สร้าง SQL รวมยอดภาคเรียนจาก catalog ทั้งหมด.
- presentation/provenance: แสดงชื่อ model เฉพาะเมื่อมี actual request-local model call. SQL-only และ cached paths ติด label ตามจริง. รอบใหม่ 2 categories มี model calls=0 จึงไม่ใช่ผลทดสอบ real-LLM fallback หรือ SLA.
- environment: OneDrive atomic checkpoint replace เกิด WinError5 สองครั้ง; เก็บ failed outputs และ resume โดย dependency lock ในนอก OneDrive. ไม่ลบ prior evidence.

## ตัวอย่างจริงก่อนและหลัง

### IT-2565-coop / minor_typo

คำถามจริง: หลักสูตร IT 2565 สหกิจ: วิชาโครงงานหนึ่งกับโครงงานสองต่อกันยังไง มีพรีรีเควสิทมั้ย

ก่อนแก้ (HTTP 422):

ไม่สามารถค้นฐานข้อมูลได้: IT-2565-coop: SQL added a filter value not present in the question: 'IT2565'

SQL ก่อนแก้: ไม่ได้บันทึกใน response ของกรณีนี้ ไม่อนุมานจาก model calls ของกรณีอื่น

หลังแก้ (HTTP 200):

IT-2565-coop — รหัสวิชา: 06016407; วิชาบังคับก่อน: 06016406; ประเภทความสัมพันธ์ที่บันทึก: pre — แสดงเฉพาะความสัมพันธ์ที่บันทึกในตาราง prerequisite ไม่ยืนยันความเชื่อมโยงเนื้อหาอื่น

SQL หลังแก้:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE course_name_matches(name_th, 'โครงงานหนึ่ง') OR course_name_matches(name_en, 'โครงงานหนึ่ง') OR INSTR(normalize_course_name(description_th), normalize_course_name('โครงงานหนึ่ง')) > 0 OR course_name_matches(name_th, 'โครงงานสอง') OR course_name_matches(name_en, 'โครงงานสอง') OR INSTR(normalize_course_name(description_th), normalize_course_name('โครงงานสอง')) > 0) AND p.requires IN (SELECT code FROM course WHERE course_name_matches(name_th, 'โครงงานหนึ่ง') OR course_name_matches(name_en, 'โครงงานหนึ่ง') OR INSTR(normalize_course_name(description_th), normalize_course_name('โครงงานหนึ่ง')) > 0 OR course_name_matches(name_th, 'โครงงานสอง') OR course_name_matches(name_en, 'โครงงานสอง') OR INSTR(normalize_course_name(description_th), normalize_course_name('โครงงานสอง')) > 0) LIMIT 100
```

แถวความสัมพันธ์ที่ใช้: `[{"code": "06016407", "requires": "06016406", "kind": "pre", "source_file": "IT.pdf", "page_number": 326, "printed_page_number": null}]`

Printed folio ของ prerequisite ที่ยังไม่ยืนยันคงเป็น unknown; ไม่ยืม folio จาก study-plan page มายืนยัน prerequisite. รายละเอียดเวลา/SQL/rows/route traces อยู่ใน raw JSON ไม่อ้าง cold/warm จากการรันนี้.

### IT-2560-no-coop / minor_typo

คำถามจริง: หลักสูตร IT 2560 ไม่เข้าร่วมสหกิจ: วิชาโครงงานหนึ่งกับโครงงานสองต่อกันยังไง มีพรีรีเควสิทมั้ย

ก่อนแก้ (HTTP 422):

ไม่สามารถค้นฐานข้อมูลได้: IT-2560-no-coop: SQL added a filter value not present in the question: 'IT2560'

SQL ก่อนแก้: ไม่ได้บันทึกใน response ของกรณีนี้ ไม่อนุมานจาก model calls ของกรณีอื่น

หลังแก้ (HTTP 200):

IT-2560-no-coop — รหัสวิชา: 06016330; วิชาบังคับก่อน: 06016329; ประเภทความสัมพันธ์ที่บันทึก: pre
IT-2560-no-coop — รหัสวิชา: 06016340; วิชาบังคับก่อน: 06016339; ประเภทความสัมพันธ์ที่บันทึก: pre
IT-2560-no-coop — รหัสวิชา: 06016350; วิชาบังคับก่อน: 06016349; ประเภทความสัมพันธ์ที่บันทึก: pre — แสดงเฉพาะความสัมพันธ์ที่บันทึกในตาราง prerequisite ไม่ยืนยันความเชื่อมโยงเนื้อหาอื่น
พบหลายคู่รายวิชาที่ตรงชื่อที่ถาม โปรดระบุรหัสหรือชื่อเต็มของคู่ที่ต้องการ ไม่เลือกคู่ใดให้โดยการเดา

SQL หลังแก้:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE course_name_matches(name_th, 'โครงงานหนึ่ง') OR course_name_matches(name_en, 'โครงงานหนึ่ง') OR INSTR(normalize_course_name(description_th), normalize_course_name('โครงงานหนึ่ง')) > 0 OR course_name_matches(name_th, 'โครงงานสอง') OR course_name_matches(name_en, 'โครงงานสอง') OR INSTR(normalize_course_name(description_th), normalize_course_name('โครงงานสอง')) > 0) AND p.requires IN (SELECT code FROM course WHERE course_name_matches(name_th, 'โครงงานหนึ่ง') OR course_name_matches(name_en, 'โครงงานหนึ่ง') OR INSTR(normalize_course_name(description_th), normalize_course_name('โครงงานหนึ่ง')) > 0 OR course_name_matches(name_th, 'โครงงานสอง') OR course_name_matches(name_en, 'โครงงานสอง') OR INSTR(normalize_course_name(description_th), normalize_course_name('โครงงานสอง')) > 0) LIMIT 100
```

แถวความสัมพันธ์ที่ใช้: `[{"code": "06016330", "requires": "06016329", "kind": "pre", "source_file": "IT-60.pdf", "page_number": 236, "printed_page_number": null}, {"code": "06016340", "requires": "06016339", "kind": "pre", "source_file": "IT-60.pdf", "page_number": 242, "printed_page_number": null}, {"code": "06016350", "requires": "06016349", "kind": "pre", "source_file": "IT-60.pdf", "page_number": 247, "printed_page_number": null}]`

Printed folio ของ prerequisite ที่ยังไม่ยืนยันคงเป็น unknown; ไม่ยืม folio จาก study-plan page มายืนยัน prerequisite. รายละเอียดเวลา/SQL/rows/route traces อยู่ใน raw JSON ไม่อ้าง cold/warm จากการรันนี้.

### AI-2566-coop / unsupported_description

คำถามจริง: หลักสูตร AI 2566 สหกิจ: ขอตัวอย่างหัวข้อสอบและภาษาโปรแกรมที่อาจารย์จะใช้สอนเทอมหน้า โดยอ้างเฉพาะข้อมูลหลักสูตรที่บันทึก

ก่อนแก้ (HTTP 200):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน AI-2566-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก

SQL ก่อนแก้: SELECT code, name_th, description_th, source_file, page_number FROM course LIMIT 100

หลังแก้ (HTTP 200):

ยังยืนยันข้อมูลที่ถามไม่ได้จากฐานข้อมูลที่ค้น: AI-2566-coop ข้อมูลที่นำเข้าอาจไม่ครบ จึงยังสรุปไม่ได้ว่ารายวิชาหรือเงื่อนไขนี้ไม่มีในเล่มหลักสูตร — ฐานข้อมูลหลักสูตรที่เลือกไม่มีหลักฐานหัวข้อสอบหรือแผนการสอนของอาจารย์ในภาคเรียนที่ถาม; ชื่อวิชา คำอธิบายหลักสูตร และหน่วยกิตไม่ยืนยันข้อมูลนี้

SQL หลังแก้:

```sql
SELECT code, source_file, page_number FROM course WHERE 0 LIMIT 100
```

แถวความสัมพันธ์ที่ใช้: `[]`

Printed folio ของ prerequisite ที่ยังไม่ยืนยันคงเป็น unknown; ไม่ยืม folio จาก study-plan page มายืนยัน prerequisite. รายละเอียดเวลา/SQL/rows/route traces อยู่ใน raw JSON ไม่อ้าง cold/warm จากการรันนี้.

## การตรวจแอปจริงและข้อจำกัด

- IT2565 UI แสดง 06016407 → 06016406 ทั้งสองแผน. Study-plan sources PDF43/book38, PDF44/book39, PDF37/book32; prerequisite PDF326 printed folio ยัง unknown.
- IT2560 UI แสดงสามคู่เฉพาะ no-coop และขอรหัส/ชื่อเต็ม; แจ้ง IT2560-coop ไม่มี matching relationship evidence. ไม่มี IT2565 code/source ปะปน. PDF236/242/247 printed folios ยัง unknown.
- Future-teaching UI แจ้ง specific gap/ชื่อสองแผน/0 sources; ไม่สร้าง curriculum fact หรือ citation.
- โหลด idle/loading/success และ gap จริง; console warn/error=[] ใน tab ที่ตรวจ. ไม่ทวน viewer cases ที่ dependencies ไม่เปลี่ยน.

[ภาพหลังแก้และ DOM](results/relevance_loop_20261010/ui-old-sequence-final.jpg), [DOM ล่าสุด](results/relevance_loop_20261010/ui-old-sequence-final-dom.txt).

## งานที่ยังไม่ปิด

- Current matrix ยังมี unreviewed cases และ historical baseline manual review ยังไม่ครบ; ไม่ถือ justified gap เป็น overall accuracy.
- Plans-comparison Year4 totals: production-approved IT term inputs มีอยู่ แต่ study_term ยังไม่ครบ ต้อง targeted backed-up ingestion แยกจาก evaluation labels และตรวจ idempotence/fact fingerprints.
- Prerequisite/condition coverage และ printed folios ของ description-page citations ยังไม่ครบ.
- Fresh manifest-aware reconstruction, untouched held-out, real-LLM mutation/removal/failure recovery, difficult cold/warm latency, process-kill recovery, legacy identity และ complete first-machine installation ยังไม่เสร็จ.
- Audit16datasetsยัง FAIL1372/incomplete4881; counts ไม่เท่ากับจำนวนคำตอบผิด. CER/WER ใหม่/held-out accuracy/difficult p95=n/a.

## คำสั่งและหลักฐาน

ไฟล์ที่แก้ในรอบนี้: runtime `model_service.py`, `query_planner.py`, `database.py`, `main.py` ใน repository และ LIVE; tests `test_fallback_relevance.py`, `test_sql_parameters.py`, `test_http_timeouts.py`; เพิ่ม `scripts/verify_sequence_batch.py`. ไม่แก้ README, working databases หรือ curriculum labels ในรอบนี้.

Latest dependency-locked checks: 266 unit, 30 schema, 6 frontend, 70 gold, 65 old2560, 14 provenance และ 6 version sets; ทั้ง 7 jobs exit0 และ dependencies_unchanged=true. Tests เหล่านี้ไม่ใช่ full-book accuracy, untouched held-out หรือ real-LLM fallback assessment.

ใช้ Python ของ live venv จาก repository ocr_final. `scripts/probe_profile_development.py` และ `scripts/verify_sequence_batch.py` อ่าน development set เดิมและ isolated SQLite. `scripts/run_handoff_checks.py` ล็อก dependencies และเก็บ 7 jobs; [latest output](results/relevance_loop_20261010/checks-latest/checks.json). [read-only audit](results/relevance_loop_20261010/audit/audit_results.json).

คำสั่ง resume และสถานะล่าสุดอยู่ [authoritative checkpoint](PROGRESS.md).
