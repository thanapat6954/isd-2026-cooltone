# ผล development questions และ clean startup — 9 ตุลาคม 2569

ใช้ curriculum-audit บน week11_thanapat / HEAD37b3ad5; ไม่มี commit/push/merge. ข้อมูลตอบมาจาก selected SQLite เท่านั้น ไม่เพิ่ม schema/description เพื่อ probe ไม่อ่าน held-out. ผลนี้เป็น DB-relative development verification ไม่ใช่ independent book accuracy หรือคะแนนที่รับรองจากผู้สอน

## ขอบเขตที่วัดจริง

Baseline84requests และ after84requests: 3คำถาม×2routes×14catalogs (13curriculum profiles +legacy). ไม่อ้างว่าเป็น84reasoningtasksต่างกัน: ชุดนี้มี stored relationship/course comparison, description/ambiguity และ unsupported planning. หลังแก้ comparison/legacy rerunเฉพาะ BIT2565สองแผน12requests และlegacy6requests ไม่ทำprofileที่ไม่เปลี่ยนซ้ำ

| หมวดคำตอบหลังแก้ในขอบเขตที่ตรวจ | จำนวน / denominator | ความหมาย |
|---|---|---|
| substantive | 26/84 | 22คำตอบexplicit prerequisite edgesตรงDB;4BITcomparisonหลังtargetedfixครบสองcode/ชื่ออังกฤษ/creditdelta |
| justified insufficient evidence / partial rule disclosure | 52/84 | 24description casesของ13profilesที่มีdescription_thว่างทุกแถว +28planning casesไม่มีtimetable/transcript/registrationpermission |
| clarification | 2/84 | IT2565coopพบหลายวิชาและขอเลือก แต่ยังบอกว่าdescriptionขาด |
| legacy quality ยังไม่ยืนยัน | 4/84 | 2catalog answersยังมีtruncated/unknownnamesจากingest และ2content answersต้องตรวจ raw_text ก่อนรับรองว่าไม่มีหลักฐาน |
| technical failures | 0/84 | ไม่ใช่ correctness proof; deliberate tablefailurecycleแยกต่างหาก |
| wrong/irrelevant after-answer ที่ยังเปิด | n/a | ไม่อ้าง overall0errors; legacyและuntestedcategoriesยังไม่ครบ |

ค่า52ข้างต้นเป็นความถูกต้องของการแจ้งข้อจำกัดฐานข้อมูล ไม่ใช่52คำตอบเนื้อหาหลักสูตรครบถ้วน. ไม่ถือ missing prerequisite edge = ไม่มี prerequisite

## ตาม curriculum/version/plan

ทุกแถวมี n=6requests; ใช้ known identity จาก DB ไม่เดาจากfilename. ไม่มีการรวมตัวเลือกหลายแผนหรือspecializationพร้อมกัน. รายการก่อนแก้มี profile ID ซ้ำข้ามปี; reportนี้ใช้ trace.queries.curriculum_name ไม่ใช้ ID นั้นเป็นidentity. Harnessใหม่ใช้ canonicalcurriculum_nameเพื่อresumeไม่ชนปี

| profile | substantive | gap / partial rules | clarification | ยังไม่ยืนยัน |
|---|---:|---:|---:|---:|
| AI-2566-coop | 2 | 4 | 0 | 0 |
| BIT-2560-coop | 2 | 4 | 0 | 0 |
| BIT-2560-no-coop | 2 | 4 | 0 | 0 |
| BIT-2565-coop | 2 | 4 | 0 | 0 |
| BIT-2565-no-coop | 2 | 4 | 0 | 0 |
| DSBA-2560-coop | 2 | 4 | 0 | 0 |
| DSBA-2560-no-coop | 2 | 4 | 0 | 0 |
| DSBA-2565-coop | 2 | 4 | 0 | 0 |
| DSBA-2565-no-coop | 2 | 4 | 0 | 0 |
| IT-2560-coop | 2 | 4 | 0 | 0 |
| IT-2560-no-coop | 2 | 4 | 0 | 0 |
| IT-2565-coop | 2 | 2 | 2 | 0 |
| IT-2565-no-coop | 2 | 4 | 0 | 0 |
| legacy-course-catalog | 0 | 2 | 0 | 4 |

[baseline](results/profile_development_20261009/results.json), [after](results/profile_development_20261009_after/results.json), [BITtargetedfinal](results/profile_development_bit_final_20261009/results.json), [legacyfinal](results/profile_development_legacy_final_20261009/results.json), [read-only capabilities](results/profile_development_20261009_after/db-capabilities.json). ทุก13profilesมีdescription_th nonempty0; raw_text ของlegacyไม่ใช่descriptionที่จัดโครงสร้างแล้วและยังต้องตรวจ relevance

## Root causes และการแก้

- Retrieval: modeltopicเลือกชื่อรายวิชาเพียงหนึ่งปลาย ทำให้ AI /ask abstain ทั้งที่มีedge. เพิ่ม literal DB-name lookupจากquestionในselectedDBก่อนรวมmodelterms; ไม่ยกเว้น SQL validation และไม่เพิ่มfacts
- Evidence selection: planning/registration questionกลับได้programsummaryหรือlegacyfragment. แยก required-evidence type; query recorded program_requirement และแจ้งว่าข้อกำหนดไม่ใช่สิทธิ์ลงทะเบียน/guaranteedgraduation ไม่มีtranscript/timetableที่ยืนยัน
- Reasoning/retrieval: QueryPlanเก็บcourse_codeตัวแรก ทำให้comparisonตอบไม่ครบ. ขยาย SQL เป็นINทุก8digitcodeที่ผู้ใช้ระบุ; คำนวณผลต่างจากcreditsที่ดึงมา ไม่ใช้ค่าคงที่
- Technical failure: course tableหายแล้วmodelดึงplan_itemแทนdescription. Fail loudlyเมื่อrequiredcourse tableไม่พร้อม; HTTP422พร้อมข้อความtechnical ไม่ทำfabricatedfallback
- Presentation: legacyถูกส่งเข้าsemesterstudyplanrendererจนNoneyear/code. แยกcatalogrendererและกรองuncodedOCRfragments; ไม่ลบsourceDBrows ไม่อ้างlegacyidentity/sourcecorrectnessจากformatfix

## ตัวอย่างจริง before / after

### /ask: หลักสูตร AI 2566 สหกิจ: อธิบายความสัมพันธ์ระหว่างแคลคูลัส 2กับแคลคูลัส 1 ตามข้อมูลที่บันทึก

ก่อนแก้ HTTP200 / 858.75ms:

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน AI-2566-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ไม่มีหลักฐานความสัมพันธ์ระหว่างรายวิชาที่บันทึกไว้ในผลที่ดึงจาก SQLite; คำอธิบายหรือยอดรวมหลักสูตรเพียงอย่างเดียวไม่ยืนยันความสัมพันธ์

หลังแก้ HTTP200 / 1088.96ms:

AI-2566-coop — รหัสวิชา: 06046401; วิชาบังคับก่อน: 06046400; ประเภทความสัมพันธ์ที่บันทึก: pre — แสดงเฉพาะความสัมพันธ์ที่บันทึกในตาราง prerequisite ไม่ยืนยันความเชื่อมโยงเนื้อหาอื่น

SQLก่อน:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('แคลคูลัส 2')) > 0 OR INSTR(LOWER(name_en), LOWER('แคลคูลัส 2')) > 0 OR INSTR(LOWER(description_th), LOWER('แคลคูลัส 2')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('แคลคูลัส 2')) > 0 OR INSTR(LOWER(name_en), LOWER('แคลคูลัส 2')) > 0 OR INSTR(LOWER(description_th), LOWER('แคลคูลัส 2')) > 0) LIMIT 100
```

SQLหลัง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('แคลคูลัส 1')) > 0 OR INSTR(LOWER(name_en), LOWER('แคลคูลัส 1')) > 0 OR INSTR(LOWER(description_th), LOWER('แคลคูลัส 1')) > 0 OR INSTR(LOWER(name_th), LOWER('แคลคูลัส 2')) > 0 OR INSTR(LOWER(name_en), LOWER('แคลคูลัส 2')) > 0 OR INSTR(LOWER(description_th), LOWER('แคลคูลัส 2')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึก')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึก')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึก')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('แคลคูลัส 1')) > 0 OR INSTR(LOWER(name_en), LOWER('แคลคูลัส 1')) > 0 OR INSTR(LOWER(description_th), LOWER('แคลคูลัส 1')) > 0 OR INSTR(LOWER(name_th), LOWER('แคลคูลัส 2')) > 0 OR INSTR(LOWER(name_en), LOWER('แคลคูลัส 2')) > 0 OR INSTR(LOWER(description_th), LOWER('แคลคูลัส 2')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึก')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึก')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึก')) > 0) LIMIT 100
```

RelevantrowsและPDF/printedpageที่DBบันทึก (nullไม่เติมด้วยoffset):

```json
[
  {
    "code": "06046400",
    "name_th": "แคลคูลัส 1",
    "name_en": "CALCULUS 1",
    "credits": null,
    "requires": null,
    "source_file": "AI.pdf",
    "page_number": 23,
    "printed_page_number": 19
  },
  {
    "code": "06046401",
    "name_th": "แคลคูลัส 2",
    "name_en": "CALCULUS 2",
    "credits": null,
    "requires": null,
    "source_file": "AI.pdf",
    "page_number": 23,
    "printed_page_number": 19
  },
  {
    "code": "06046401",
    "name_th": null,
    "name_en": null,
    "credits": null,
    "requires": "06046400",
    "source_file": "AI.pdf",
    "page_number": 287,
    "printed_page_number": 283
  }
]
```

### /ask: หลักสูตร BIT 2565 สหกิจ: ช่วยเทียบ 06036100 กับ 06036101 ชื่อภาษาอังกฤษและหน่วยกิตต่างกันยังไง

ก่อนแก้ HTTP200 / 77.81ms:

BIT-2565-coop: 06036100 พื้นฐานทางด้านเทคโนโลยีสารสนเทศ (INFORMATION TECHNOLOGY FUNDAMENTALS), 3 หน่วยกิต, L-P-S 2-2-5 (ที่มา: BIT-65.pdf หน้า 31)

หลังแก้ HTTP200 / 16.50ms:

BIT-2565-coop: 06036100 พื้นฐานทางด้านเทคโนโลยีสารสนเทศ (INFORMATION TECHNOLOGY FUNDAMENTALS), 3 หน่วยกิต, L-P-S 2-2-5 (ที่มา: BIT-65.pdf หน้า 31)
BIT-2565-coop: 06036101 คณิตศาสตร์สำหรับธุรกิจ (MATHEMATICS FOR BUSINESS), 3 หน่วยกิต, L-P-S 3-0-6 (ที่มา: BIT-65.pdf หน้า 31)
BIT-2565-coop: ผลต่างหน่วยกิต = 3 - 3 = 0 หน่วยกิต (คำนวณจากสองรายวิชาที่ดึงมา)

SQLก่อน:

```sql
SELECT code, name_th, name_en, credits, lecture_h, lab_h, self_h, source_file, page_number, (SELECT MIN(p.printed_page_number) FROM plan_item p WHERE p.code = course.code AND p.source_file = course.source_file AND p.page_number = course.page_number) AS printed_page_number FROM course WHERE code = '06036100' LIMIT 100
```

SQLหลัง:

```sql
SELECT code, name_th, name_en, credits, lecture_h, lab_h, self_h, source_file, page_number, (SELECT MIN(p.printed_page_number) FROM plan_item p WHERE p.code = course.code AND p.source_file = course.source_file AND p.page_number = course.page_number) AS printed_page_number FROM course WHERE code IN ('06036100', '06036101') LIMIT 100
```

RelevantrowsและPDF/printedpageที่DBบันทึก (nullไม่เติมด้วยoffset):

```json
[
  {
    "code": "06036100",
    "name_th": "พื้นฐานทางด้านเทคโนโลยีสารสนเทศ",
    "name_en": "INFORMATION TECHNOLOGY FUNDAMENTALS",
    "credits": 3,
    "requires": null,
    "source_file": "BIT-65.pdf",
    "page_number": 31,
    "printed_page_number": 26
  },
  {
    "code": "06036101",
    "name_th": "คณิตศาสตร์สำหรับธุรกิจ",
    "name_en": "MATHEMATICS FOR BUSINESS",
    "credits": 3,
    "requires": null,
    "source_file": "BIT-65.pdf",
    "page_number": 31,
    "printed_page_number": 26
  }
]
```

### /api/ask: ฐานข้อมูลเดิม legacy: ถ้ายังไม่ผ่านทุกวิชา ช่วยรับรองว่าจบได้ในสามปีครึ่งและลงทะเบียนเทอมหน้าได้แน่นอน

ก่อนแก้ HTTP200 / 3605.78ms:

legacy-course-catalog — ชื่อภาษาไทย: จอมเกล้าเจ้าคูณท
legacy-course-catalog — ชื่อภาษาไทย: วท.บ.
legacy-course-catalog — ชื่อภาษาไทย: สารบัญ

หลังแก้ HTTP200 / 59.08ms:

ยังยืนยันข้อมูลที่ถามไม่ได้จากฐานข้อมูลที่ค้น: legacy-course-catalog ข้อมูลที่นำเข้าอาจไม่ครบ จึงยังสรุปไม่ได้ว่ารายวิชาหรือเงื่อนไขนี้ไม่มีในเล่มหลักสูตร — ยังรับรองการลงทะเบียนหรือการจบตามเวลาที่ขอไม่ได้: ผลที่ดึงจาก SQLite ไม่มีข้อมูลยืนยันครบทั้งการเปิดรายวิชาในเทอมที่ต้องการ ผลการเรียนรายบุคคล และเงื่อนไขอนุญาตลงทะเบียน; ข้อกำหนดหลักสูตรที่มีไม่ใช่การรับรองสิทธิ์รายบุคคล

SQLก่อน:

```sql
SELECT course_code AS code, course_name_th AS name_th, course_name_en AS name_en, credits, source_file, page_number FROM courses LIMIT 5
```

SQLหลัง:

```sql
SELECT * FROM courses WHERE 0 LIMIT 100
```

RelevantrowsและPDF/printedpageที่DBบันทึก (nullไม่เติมด้วยoffset):

```json
[]
```

### /ask: หลักสูตร IT 2565 สหกิจ: อธิบายเนื้อหาวิชาการเขียนโปรแกรม

ก่อนแก้ HTTP200 / 953.89ms:

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้ — รายวิชาที่พบ: 06066302 การเขียนโปรแกรมเว็บพื้นฐาน; 06016415 การเขียนโปรแกรมเชิงฟังก์ชัน โปรดระบุว่าต้องการรายวิชาใด; การเลือกชื่อให้ชัดยังไม่ทดแทนคำอธิบายที่ขาดในฐานข้อมูล

หลังแก้ HTTP200 / 964.97ms:

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้ — รายวิชาที่พบ: 06066302 การเขียนโปรแกรมเว็บพื้นฐาน; 06016415 การเขียนโปรแกรมเชิงฟังก์ชัน โปรดระบุว่าต้องการรายวิชาใด; การเลือกชื่อให้ชัดยังไม่ทดแทนคำอธิบายที่ขาดในฐานข้อมูล

SQLก่อน:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('การเขียนโปรแกรม')) > 0 OR INSTR(LOWER(name_en), LOWER('การเขียนโปรแกรม')) > 0 OR INSTR(LOWER(description_th), LOWER('การเขียนโปรแกรม')) > 0 LIMIT 100
```

SQLหลัง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('การเขียนโปรแกรม')) > 0 OR INSTR(LOWER(name_en), LOWER('การเขียนโปรแกรม')) > 0 OR INSTR(LOWER(description_th), LOWER('การเขียนโปรแกรม')) > 0 LIMIT 100
```

RelevantrowsและPDF/printedpageที่DBบันทึก (nullไม่เติมด้วยoffset):

```json
[
  {
    "code": "06066302",
    "name_th": "การเขียนโปรแกรมเว็บพื้นฐาน",
    "name_en": "FUNDAMENTAL WEB PROGRAMMING",
    "credits": null,
    "requires": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "printed_page_number": 36
  },
  {
    "code": "06016415",
    "name_th": "การเขียนโปรแกรมเชิงฟังก์ชัน",
    "name_en": "FUNCTIONAL PROGRAMMING",
    "credits": null,
    "requires": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "printed_page_number": 36
  }
]
```

## Same-process provenance / cache / recovery

[finalcycle](results/profile_cache_cycle_final_20261009/result.json): 5stages×3requests=15; A/B6requestsเปลี่ยนmarkerตามisolatedDB (รวมrepeatcachehit); removal3ไม่พูดmarkerซ้ำ; tablefailure3เป็น422ไม่มีfactualanswer; restoredtable3กลับ200และไม่พูดmarkerซ้ำ. Cachehit4repeatบนvalidstages, firstrequestหลังDBmutationcache_hit=false. WorkingDBhashคงเดิม. Markerเป็นsyntheticprovenancefixtureไม่ใช่coursequalityหรือsourceevidence. เก็บ[failedชื่อไม่ตรง](results/profile_cache_cycle_20261009/result.json)และ[ก่อนtechnicalguard](results/profile_cache_cycle_20261009_b/result.json)ไว้

## Clean installation และ browser

- แยกcopyที่รวมuncommittedimplementation, Python3.11.9venvใหม่; pinnedwebrequirementsติดตั้งได้จริงและpipcheckไม่พบbrokenrequirements
- Restore14SQLite snapshotsจากportablebundle (integrityตรวจทุกDB); sourcePDF7ไฟล์เป็นlocalinputs ไม่downloadfacts. [preflight](results/profile_development_20261009_after/clean-preflight.json) ready=true และconfiguredqwen3:4bพร้อม
- start_web.ps1 -Port8006, stop_web.ps1 -Port8006, restartผ่าน; ไม่หยุดLIVE8000/Ollama. ใช้modelserviceที่มีอยู่แล้ว **การติดตั้งOllama/modelครั้งแรกและforcedmodelcoldยังn/a**
- actualbrowser: AIrelationshipมีทั้งcodesและpairedcitations, [UI](results/profile_development_20261009_after/clean-ai-ui.png)/[DOM](results/profile_development_20261009_after/clean-ai-ui.txt); server1333ms/end-to-end1430ms
- actualcitationclickเปิดAI.pdfPDF287/book283และเห็นpageimage [ภาพ](results/profile_development_20261009_after/clean-citation.png)/[DOM](results/profile_development_20261009_after/clean-citation.txt). เป็นvisibleviewerverification ไม่ใช่fullpagefactreviewใหม่
- BITcomparisonทั้งสองcodesและdelta [UI](results/profile_development_bit_final_20261009/clean-bit-ui.png)/[DOM](results/profile_development_bit_final_20261009/clean-bit-ui.txt); server185ms/end-to-end214ms เป็นstructuredquestion ไม่ใช่difficultLLMbenchmark
- [transport/readiness](results/profile_development_20261009_after/clean-runtime.json):7PDF routes/33relativeREADMElinksผ่าน. HTTP206แยกจากvisibleproofข้างบน

## Timing / tests / remaining gaps

[shared-final](results/profile_development_20261009_after/shared-final/checks.json):230unit/schema30/frontend6/gold70/oldQA65/provenance14/version_sets6;7jobs exit0/dependencies_unchanged=true. [v1](results/profile_development_20261009_after/shared-v1/checks.json)เก็บก่อนcomparison/tablefailurefix ไม่ลบผลเก่า. ไม่รวมregressionsเป็นaccuracyเดียว

Questionsในmatrixมีexplicitprogram/year/planทั้งroutesและตอบจากselectedDBตรงidentity; sourcepage/printedfolioที่ไม่มีในDBยังunknown. ไม่ได้ทำvisibleUIทุก14profileรอบนี้. Difficult cold/warmmedian/p95ยังn/a; clearanswercacheไม่ได้ยืนยันmodelcold และการรันmodelร่วมกันไม่ใช่latencybenchmarkที่ควบคุมเงื่อนไข

เพิ่ม[ชุดdevelopmentหลากหลาย](../ocr_final/tests/development_curriculum_questions_20261009.json)14reasoning/wordingcategories ไม่มีgoldfacts/heldoutanswers; ยังไม่ได้runทั้งหมด. Semesteraggregations/sharedtracks/electives/old-newใช้verifiedregressionsเดิมเป็นscopeแยก ไม่อ้างว่าmatrix3questionsครอบคลุมL1–L4ครบ. ยังขาดinformal/typo robustness, multi-conditioncompleteness, specialization-specific reasoning และplanningconstraintsที่มีพอจะให้substantiveplan

Freshreconstructionต่อที่[BITcoopjobmanifest](results/fresh_bit_coop_20261009/reconstruction.json):PDF31–35เพียง5studyplanpages. แยกrawOCRออกจากreviewedproductioningest ห้ามอ้างfullrelevantbookหรือrawOCRaccuracyจากreviewedfields. Untouchedindependentheldoutยังไม่ได้run; legacyidentity/raw_textsourceisolation, broaderprerequisites, processkillrecovery และfirstmodelinstallationยังเปิด. ไม่มีAIold/sameyearrevision/dualdegreesourceที่ยืนยัน

## Fresh BIT และข้อแก้ที่ตรวจจากต้นฉบับ

Fresh OCR/build แผนสหกิจศึกษา BIT-2565 ประมวลผล PDF31–35 รวม5หน้า ใช้189.86s; มี checkpoint แยกทุกหน้า ไม่เปลี่ยน working DB หรือ original OCR. [ผลก่อนแก้](results/fresh_bit_coop_20261009/source-label-check.json): integrity1/1, semester totals8/8 แต่พบ2field mismatchesจากแถวเดียว Y3/S1. ไม่ใช่ full-book reconstruction และ raw OCR field accuracy ยัง n/a

ตรวจ[ภาพ PDF33/book28](results/fresh_bit_coop_20261009/bit-pdf33-book28.png)โดยอิสระ: elective ภาษาใช้96644xxx แต่ fresh OCR อ่าน9664xxxx. Credit alternatives `3(3-0-6) หรือ 3(2-2-5)` อยู่ใน OCR แล้ว; mismatch ที่สองเป็นผลจากจับคู่รหัสไม่พบ ไม่ใช่ alternative หาย. เพิ่ม approval สำหรับตารางสหกิจศึกษานี้ใน [production input](../ocr_final/data/source_reviews/BIT-2565-plan-corrections.json) โดยไม่คัดลอก evaluation หรืออีกแผน. ตารางไม่บอก prerequisite/category จึงคง unknown

สร้าง DB ใหม่จาก fresh OCR เดิมโดยไม่เรียก OCR ซ้ำ: [manifest](results/fresh_bit_coop_reviewed_20261009/reconstruction.json),8.06s; protected inputs unchanged. [ผลหลังแก้](results/fresh_bit_coop_reviewed_20261009/source-label-check.json): integrity1/1, semester totals8/8, partial code/credit-pattern mismatches0. ผลนี้เป็น reviewed-ingestion correctness ไม่ใช่ OCR accuracy improvement. Failed baselineยังอยู่; working DBไม่ถูกแทนที่

[Regression](results/fresh_bit_coop_reviewed_20261009/regression.json):231unit testsและschema selftestผ่าน; เพิ่มidempotence/preserved-original/unknown-prerequisite testสำหรับapprovalนี้. Full-book names/prerequisites/graduation verificationยังไม่อยู่ใน denominatorดังกล่าว

Read-only auditล่าสุด16datasetsยัง FAIL1372/incomplete4881/missingcurricula0; เป็นจำนวน findings ไม่ใช่อัตราคำตอบผิด. [รายงาน BIT Summary/HIGH](results/profile_development_20261009_after/audit-current/audit_BIT-2565-coop-088b37ca.md) ยังพบ prerequisite coverage4/302 และ full source fidelityที่ไม่ยืนยัน. การแก้ isolated buildไม่ได้อ้างว่าปิด findingsเหล่านี้

Page manifests7เล่ม reconcileแล้ว: include87/2322physical pages,skip0,unreviewed2235. ไม่ถือหน้าที่ยังไม่ตรวจว่า irrelevant. Freshรอบนี้ครอบคลุม5included study-plan pagesในBIT-65 เท่านั้น. แยก clean backend8006หยุดแล้ว; LIVE8000/Ollamaคงอยู่. ไม่มีcommit/push/merge

Final dependency-locked run หลังsource approval/testเพิ่ม: [raw checks](results/profile_development_20261009_after/shared-source-review-final/checks.json),7jobs exit0/dependencies_unchanged=true: unit231/schema30/frontend6/gold70/old2560QA65/provenance14/version_sets6. การผ่านregressionเหล่านี้ไม่แทน independent held-out, all-profile visible browser review หรือ full-book ground truth
