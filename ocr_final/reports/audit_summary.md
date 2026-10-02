# สรุปการตรวจและแก้ไข Curriculum OCR

## Summary

งานยังไม่เสร็จทั้งระบบ ผลต่อไปนี้เป็น development regression ที่อ้างอิงหน้าหนังสือที่ตรวจแล้ว ไม่ใช่ held-out accuracy หรือการตรวจหนังสือทุกหน้า

ตรวจ SQLite 16 ชุด รวมฐานที่ใช้งานจริงและฐาน validation; พบ FAIL 1377 รายการ และ NEEDS_REVIEW/SKIPPED 4882 รายการ ไม่ตีความรายการที่หายจากรายงานว่าแก้แล้วโดยอัตโนมัติ
ใช้ schema จริงและ SQLite mode=ro/query_only=ON; ไม่ใช้ชื่อโฟลเดอร์เดาเล่ม ไม่ใช้ข้อความใกล้รหัสเป็นเฉลย และไม่ใช้ SQL fallback คนละเส้นทางกับแอป

## สาเหตุที่ยืนยันและสิ่งที่แก้

- การค้นเฉพาะ prerequisite ทำให้รายวิชาที่มีอยู่แต่ไม่มี edge ถูกตอบเหมือนไม่พบรายวิชา แก้เป็น LEFT JOIN จาก course พร้อมแยก explicit_none / required / unknown
- ไม่มีข้อมูลใน DB ไม่ใช่หลักฐานว่าไม่มีในเล่ม คำตอบจึงระบุหลักสูตร/ฉบับที่ค้นและแจ้งความไม่ครบของข้อมูล ไม่อนุญาตลงทะเบียนโดยไม่มีข้อบังคับรองรับ
- คำว่าไม่เข้าร่วมสหกิจเคยเลือก coop; แก้คำระบุแผนภาษาไทยและใช้ program.plan แทน suffix ของ program_id
- คำถามชื่อรายวิชาที่ระบุหลักสูตรเคยถูกอ่านเป็นชื่อหลักสูตร แก้ intent โดยให้รหัสวิชามีความสำคัญก่อน
- AI.pdf หน้า PDF 1 ระบุหลักสูตรใหม่ พ.ศ. 2566 แก้ metadata/config/UI เป็น AI-2566 และเลือกปีที่ระบุจริงโดยไม่ fallback ข้ามฉบับ
- นำหลักฐาน prerequisite ที่ตรวจภาพแล้วกลับเข้า DB พร้อม SHA-256, หน้าเล่ม และ SQLite backup; ใช้ซ้ำหลัง rebuild ได้ ไม่แก้ original OCR หรือ held-out
- ใช้ชื่อภาษาไทยจากแถวที่ตรวจแล้วแก้ IT-2560 สองแถวที่สลับชื่อ และสามแถวที่มีหัวข้อแขนงวิชาปนในชื่อ หลักฐานก่อน/หลังอยู่ใน approved_name_prerequisite_ingest.json; ไม่ใช่ OCR accuracy ที่เพิ่มขึ้น
- cache_hit เก็บเวลาของคำขอปัจจุบัน ไม่รายงานเวลาเดิมของคำขอแรก; UI ระบุ SQL (database-backed) เมื่อไม่ได้เรียก LLM สร้างคำตอบ

## ผลตามหลักสูตรและฉบับ

| หลักสูตร/ฉบับ/แผน | ผ่านครั้งแรก | ขอบเขต |
|---|---:|---|
| `AI-2566-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `DSBA-2565-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `DSBA-2565-no-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `IT-2565-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `IT-2565-no-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `DSBA-2560-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `DSBA-2560-no-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `IT-2560-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `IT-2560-no-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `BIT-2565-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `BIT-2565-no-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `BIT-2560-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `BIT-2560-no-coop` | 5/5 | L1/L2 และข้อมูลไม่ครบ |
| `legacy` | 5/5 | ตรวจความปลอดภัยเมื่อข้อมูลไม่ยืนยัน ไม่ใช่ content accuracy |

รัน 3 รอบ รวม 210 คำตอบ; ชุดคำถามใช้ template และตัวอย่างที่เลือกเพื่อจับบั๊ก จึงไม่ใช้สัดส่วนนี้แทนความแม่นยำทั่วไปหรือเกณฑ์ >91%
legacy รวมข้อความรายวิชาจากหลายเล่มและยังไม่มีปีฉบับที่ยืนยัน จึงมีเฉลยด้านการไม่กล่าวอ้างเกินหลักฐานเท่านั้น ไม่อ้างว่า legacy content accuracy ผ่าน

## การอ้างอิงและ latency

การตรวจ citation ใน gold ตรวจชื่อแหล่งข้อมูล และตรวจเลขหน้าเฉพาะข้อที่เฉลยระบุหน้า ไม่ใช่การตรวจทุกประโยคในคำตอบกับภาพหนังสือทั้งเล่ม

| รอบ | ตัวอย่างที่ตอบถูกและมีสาระ | median (ms) | p95 (ms) | ต่ำกว่า 5 วินาที |
|---|---:|---:|---:|---:|
| 1 | 52 | 501.99 | 642.41 | 52/52 |
| 2 | 52 | 503.85 | 566.94 | 52/52 |
| 3 | 52 | 506.89 | 559.54 | 52/52 |

gold มีแหล่งอ้างอิง 52 ข้อ ระบุหน้า PDF แบบเฉพาะ 26 ข้อ; metadata citation ผ่าน 52/52 ข้อในรอบแรก ข้อที่ตรวจแค่ชื่อไฟล์ยังไม่ใช่ semantic citation accuracy เต็มรูปแบบ
latency วัดเวลาฝั่ง client ครบคำตอบ HTTP รวมการค้นคืนและจัดรูปแบบ กรณีเหล่านี้ใช้ deterministic SQL ไม่ได้วัดการสร้างคำตอบยากด้วย LLM; ตัดข้อข้อมูลไม่ครบออกจาก latency ของคำตอบที่มีสาระ
ไม่เรียกรอบแรกว่า cold start เพราะไม่ยืนยันว่า process/model/cache เย็น และยังไม่ยืนยัน challenge L3/L4 ต่ำกว่า 5 วินาที
cache hits/misses: รอบ 1 hit 0/70, miss 70/70; รอบ 2 hit 70/70, miss 0/70; รอบ 3 hit 70/70, miss 0/70

## การทดสอบแอปและข้อกำหนด

คำสั่ง regression และ schema selftest มี exit code [0, 0]; raw output ใน docs/results/current_audit_final_regressions.json
UI และ /ask ตรงกัน 4/4 กรณี ใน AI/DSBA/IT/BIT ฉบับปัจจุบัน; mobile ตรวจเฉพาะคำตอบ prerequisite ของ DSBA ที่ viewport 390x844 ไม่มี horizontal overflow ไม่ใช่ UI coverage ครบทุกฉบับ/ระดับ
เกณฑ์ P2 ยืนยันจาก ch1_Introduction.pdf หน้า PDF 5/7: DB/RAG 20, OCR 20, output quality 20, LLM 30, แอปและเอกสาร 10; prerequisite/เงื่อนไขลงทะเบียนเป็น L2, เปรียบเทียบเก่า/ใหม่เป็น L3, ฉบับแก้ไขปีเดียวกัน/สองปริญญาเป็น L4; bonus รวมไม่เกิน +10 และคำตอบยากต้องรวม retrieval+generation ภายใน 5 วินาที
ch9_EvaluationAndOverfitting (1).pdf หน้า PDF 17/19/25/26 ให้แยก extraction/schema/retrieval/answer, วัด Execution Accuracy, Faithfulness และ citation coverage, ตรวจ slice ตามแหล่งข้อมูลและความเสถียร; ยังไม่มีใบสั่งงาน Lab 9 ที่ยืนยัน จึงไม่สร้างข้อกำหนดเอง

## HIGH

1. ยังมีห้า profile ที่ rebuild ถูกบล็อกโดยตาราง OCR เสีย: IT-2560 coop (PDF36/40), IT-2565 no-coop (PDF36/37), IT-2565 coop (PDF43/44), BIT-2565 no-coop (PDF29/30), BIT-2565 coop (PDF34/35) ต้องตรวจภาพและแก้ extraction ไม่สร้าง electives ชดเชยหน่วยกิต
2. prerequisite ที่นำเข้าครบเฉพาะแถวที่ตรวจแล้ว ส่วนที่เหลือยัง unknown; legacy เป็น page fragments และมีรหัส/หน้า/บริบทที่ต้องตรวจ ห้ามล้างทิ้งอัตโนมัติ
3. ยังไม่ยืนยันชื่อ หน่วยกิต หมวดวิชา เงื่อนไขจบ และ citation ทุกแถวกับทั้งเล่ม; general_education_ground_truth.json ยังขาด PDF provenance ใน audit
4. ชุด held-out ไม่ถูกเปลี่ยนและยังไม่ได้ประเมินรอบสุดท้าย; seed stability ของโมเดล, false abstain/abstain recall แบบ independent held-out, การตอบ L3/L4, cold/warm LLM และ latency challenge ยังไม่วัด
5. ไม่พบเอกสารฉบับแก้ไขปีเดียวกันหรือสองปริญญา และไม่มี AI ฉบับเก่า จึงยังตรวจ challenge เหล่านี้ไม่ได้; legacy ไม่มีตัวเลือกใน UI

| ประเภท finding | สถานะ | จำนวน |
|---|---|---:|
| `application_retrieval` | FAIL | 1 |
| `code` | FAIL | 1371 |
| `code_on_cited_page` | NEEDS_REVIEW | 4843 |
| `fidelity_schema` | FAIL | 5 |
| `full_source_fidelity` | NEEDS_REVIEW | 16 |
| `legacy_identity` | NEEDS_REVIEW | 1 |
| `prerequisite_coverage` | NEEDS_REVIEW | 15 |
| `reference_coverage` | SKIPPED | 7 |

## หลักฐานและการทำต่อ

- รายการรายวิชาที่ตรวจและ findings: reports/audit_results.json และ reports/audit_*.md
- คำถาม/คำตอบ/เวลา: docs/results/qa_gold_final_2026-10-02.json; เฉลย development: tests/qa_gold.json
- การแก้ที่มี backup: docs/results/approved_name_prerequisite_ingest.json, approved_prerequisite_ingest.json และ ai_identity_cover_review.json
- API/UI: docs/results/ui_observations_2026-10-02.json, ui_api_agreement_2026-10-02.json และ screenshots/
- OCR metrics เดิมยังแยกจากการแก้ DB: docs/results/a1_field_metrics.json; ใช้เฉพาะแถวที่ visually verified ไม่ใช้ OCR ตรวจตัวเอง
- checkpoint ที่เป็นแหล่งเดียว: docs/PROGRESS.md ที่ root ของ feature repository; ทำต่อจาก NEXT ACTION
