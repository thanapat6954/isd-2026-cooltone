# แนวทางเตรียม independent evaluation

## สถานะและขอบเขต

เอกสารนี้เป็น protocol ไม่ใช่ชุดเฉลย ไม่ใช่ผล held-out และไม่เพิ่มข้อเท็จจริงให้ production. Current development gold ครอบคลุม14profiles แต่ยังใช้แทน independent source-grounded accuracy ไม่ได้. กรณี elective, category และ OCR ที่เปิดดูใน batch นี้เป็น development เท่านั้น.

## การแยกข้อมูล

1. เก็บ original OCR โดยไม่แก้ข้อความและเก็บ configuration/hash.
2. เก็บ source-approved production correction พร้อมภาพและ approval แยกจาก labels.
3. เก็บ exposed development/regression cases พร้อมการเปลี่ยนสถานะเมื่อเคยใช้ debug.
4. สร้าง frozen independent evaluation ใหม่จาก rendered source โดยไม่ใช้ chatbot/OCR/SQLite เป็น independent truth. ห้ามนำ expected answers เข้า production หรือ prompt.

## การเตรียมแต่ละ profile

ใช้ identity mappings ที่ตรวจแล้วจาก catalog และ source reviews ไม่อนุมานจากชื่อไฟล์. ตรวจ AI-2566, DSBA/IT/BIT-2560/2565 และแผนที่มีจริง; legacy ต้องมี source identity ก่อนอ้าง source fidelity. ไม่สร้าง AI-old, same-year revision หรือ dual-degree ที่ไม่มีหลักฐาน.

ขั้นต่ำที่วางแผนคือ5independentquestionsต่อprofileที่ source identity ยืนยันแล้ว ไม่ใช่ตัวเลขที่ประเมินเสร็จ. ต้องหลากหลาย reasoning ไม่ใช่เปลี่ยน course code ใน template เดิม: facts, plans/totals, alternatives/shared-specialization requirements, prerequisites/conditions, comparisons และ genuinely unsupported questions. L3/L4 ที่ source ไม่พอให้ระบุ n/a ไม่สร้างเงื่อนไขใหม่.

แต่ละ label ต้องบันทึก source hash, curriculum/version/plan, PDF page, printed page ที่ตรวจแยก, section/table/footnote, claim scope และผู้ตรวจ/วันที่. ความสัมพันธ์ AND/OR ต้องมีข้อความรองรับ. หลักฐานที่ยังไม่พอคง unverified; missing SQLite ไม่ได้แปลว่า source ไม่มีข้อมูล.

## Freeze และวัดผล

- ก่อน freeze ตรวจซ้ำจากภาพโดยไม่เปิด application answers แล้วบันทึก dataset hash และรายชื่อ exposed IDs ที่ห้ามนับเป็น untouched.
- Runner ต้องใช้เฉพาะ question/input กับระบบ production; expected answer ใช้ใน grader ภายนอกเท่านั้น.
- รายงาน DB consistency, source fidelity, retrieval coverage, answer completeness และ citation support แยกกัน. HTTP200ไม่ใช่ correctness pass.
- แยก substantive correct, justified partial/gap, clarification, unnecessary abstention, incorrect/irrelevant, technical failure และ unreviewed.
- รายงาน denominator ตาม uniquequestions, HTTPrequests, profile-course cases, sourcepages และ semesters ไม่รวมกันเป็น accuracy เดียว.
- หากใช้ held-out failure ทำ fix ให้บันทึก exposure และเลิกอ้าง untouched final status ของกรณีนั้น; ต้องเตรียมชุดใหม่ก่อน final assessment.
- Cold/warm latency ต้องมี model/process/cache conditions, count, median/p95 และ failures/timeouts; ไม่ใช้ structured SQL timings เป็น difficult-LLM SLA.

## Gaps ที่ยังไม่ใช่ผลประเมิน

ชุด frozen source-grounded ครบทุกprofile/L1–L4, source identity ของ legacy บางส่วน และ prerequisite/condition coverage ยังไม่เสร็จ. ขั้นต่อไปคือ reconcile label/source-review coverage จาก catalog แล้วตรวจหน้าที่ยังขาด; ไม่คัดลอก exposed BIT examples เข้า final held-out.
