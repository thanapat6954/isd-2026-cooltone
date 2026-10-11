# ตรวจคำอธิบายรายวิชาและแก้ ingestion — 8 ตุลาคม 2026

ทำงานบน `week11_thanapat`/`37b3ad5` โดยไม่ commit/push/merge ไม่แก้ main และไม่แตะ held-out ข้อมูลต้นฉบับ OCR ไม่เปลี่ยน การเพิ่มข้อมูลที่ตรวจด้วยคนเป็น reviewed-ingestion ไม่ใช่การเพิ่ม OCR accuracy

## หลักฐานจากเล่ม

| หลักสูตร | PDF หน้า / หน้าในเล่ม | สิ่งที่ตรวจยืนยัน | ข้อจำกัด |
|---|---|---|---|
| AI-2566 | 37 / 33 | ชื่อ 12 รายวิชาใน PLO matrix | ไม่มี prerequisite/category/สิทธิลงทะเบียนในหน้านี้ |
| AI-2566 | 287 / 283 | แคลคูลัส 1 ไม่มี prerequisite; แคลคูลัส 2 ต้องผ่าน 06046400; หัวข้อกลุ่มพื้นฐานคณิตศาสตร์และสถิติ | ไม่ใช่หลักฐานข้อยกเว้นลงทะเบียน |
| AI-2566 | 292 / 288 | 06046406 ต้องผ่าน 06046401 และ 06046402; 06046407/08 ระบุไม่มี prerequisite | ไม่ยืนยัน category จากหน้าที่ไม่มีหัวข้อกลุ่ม |
| BIT-2565 | 238 / 233 | 06036100/01 ระบุไม่มี prerequisite | ไม่ใช่ข้อมูลครบทุกวิชา |
| BIT-2565 | 257 / 252 | 06036147/48 มี 6(0-35-0), ระบุไม่มี prerequisite และเงื่อนไขโครงงาน/นำเสนอ | catalog ร่วมไม่ทำให้วิชาสหกิจเป็นวิชาที่ต้องเรียนในแผน no-coop |
| BIT-2565 | 274 / 269 | ตารางเทียบ 2560→2565: 06036046→06036147 และ 06036047→06036148 | ไม่ใช่หน้า prerequisite |
| BIT-2565 | 87 / 82; 93 / 88 | ข้อบังคับ 2564 และเกณฑ์จบข้อ 26: เรียนครบ/สอบผ่าน, GPA ตามโครงสร้างและ GPA สะสม ≥2.00, English Exit Exam ตามประกาศ, ศักดิ์ศรีนักศึกษา, ไม่มีหนี้/ภาระผูกพัน, เงื่อนไขอื่นตามประกาศ | ยังไม่ตรวจประกาศคะแนน English Exit และเงื่อนไขทั้งหมด ไม่ขยายผลไปเล่มอื่นโดยเดา |

ภาพใหม่ 14 หน้า: AI 37/287/292; BIT 238/257/274/84/85/87/92/93/94/95/96 อยู่ใน [source_pages](results/source_continuation_20261008/source_pages/) พร้อม source/image hashes ใน inventory JSON เก็บภาพ navigation ที่ไม่ใช่เกณฑ์จบไว้ด้วย ไม่ใช้ cached text เป็นเฉลย

Production approvals [description_prerequisites](../ocr_final/data/source_reviews/description_prerequisites_20261008.json) แยกจาก [development QA](../ocr_final/data/ground_truth/evaluation/description-development-20261008.json) และ [BIT graduation labels](../ocr_final/data/ground_truth/evaluation/BIT-2565/graduation-reviewed-20261008.json) ไม่มีคำถาม/expected answers ใน production approvals; graduation labels ใหม่ยังไม่เข้า production

## สาเหตุและผลแก้

1. Guard ใหม่ตรวจ orphan ก่อนตรวจ applicability ทำให้ rebuild บางแผนล้มเหลว: ย้าย skip ของ review-course ที่ไม่อยู่ในแผนมาหน้า validation; ยังคงปฏิเสธ orphan/conflicting edges และ conflicting source approvals
2. Catalog ของ BIT no-coop มีเฉพาะวิชาที่นำเข้าในแผน ไม่ครบ common course descriptions: เพิ่มเฉพาะสองวิชาที่มี full description fields และ source approval; ไม่เพิ่ม `plan_item` หรือยอดหน่วยกิต no-coop คำตอบบอกชัดว่าไม่ปรากฏในตารางแผนการเรียนของ DB ที่เลือก
3. Evaluation runner เดิมตรวจ prerequisite ทีละ string ไม่รองรับหลาย edges: เพิ่ม exact-set validation ที่ไม่ขึ้นกับลำดับ แต่ต้องมีครบและไม่มี edge เกิน พร้อม regression tests
4. คำตอบ prerequisite แสดง code อย่างเดียว: เพิ่มชื่อที่ดึงจาก SQL ไม่ hard-code ชื่อ และยังไม่รับรองสิทธิลงทะเบียน
5. Provenance runner ผูก port 8000: เพิ่ม `--url` เพื่อ replay SQL ของ isolated backend จริง ไม่เทียบคำตอบจาก live กับ DB คนละชุด
6. OneDrive staged replacement/checkpoint พบ WinError5: ไม่ overwrite working DB จาก failed rebuild เก็บ failed attempts; ย้ายงานไป local disk แล้ว copy ผล/backup ที่ตรวจ hash กลับ repository การ resume หลัง error นี้ทดสอบจริง แต่ยังไม่ใช่ process-kill recovery หรือ timeout exhaustion

## ผลที่สังเกต

| การตรวจ | ผล | หลักฐาน |
|---|---|---|
| saved-OCR isolated rebuild | 13/13; protected unchanged | [manifest](results/source_continuation_20261008/reconstruction.json) |
| DB integrity / partial semester labels | 13/13; 73/73; code/hour mismatches 0 | [source check](results/source_continuation_20261008/catalog_rebuilt_labels.json) |
| description API รอบแรกและซ้ำ | 13/13 ทั้งสองรอบ | [raw](results/source_continuation_20261008/description_qa_final.json) |
| live description API | 13/13 | [raw](results/source_continuation_20261008/live_description_qa.json) |
| live shared regressions | unit179/schema30/frontend6/gold70/old65/provenance14/version-pairs6 ผ่าน; dependency hashes ไม่เปลี่ยนขณะรัน | [raw](results/source_continuation_20261008/live_checks/checks.json) |
| isolated SQL provenance | 14/14; 0 added/changed post-SQL fields; 0 unmatched rows | [raw](results/source_continuation_20261008/provenance.json) |
| actual live UI | AI prerequisite ทั้งสอง codes; BIT ทั้งสอง plans + no-coop scope warning; paired PDF/book citations; console ไม่มี error/warn ในสองกรณี | [AI](results/source_continuation_20261008/live_ai_ui.json), [BIT](results/source_continuation_20261008/live_bit_ui.json) |
| live gold structured latency | n=52, median471.57ms, p95512.50ms | [raw](results/source_continuation_20261008/live_checks/gold.json) |
| readonly audit หลังแก้ | 16datasets; FAIL1372/incomplete4881; missing curricula0 ยังไม่ผ่าน | [reports](results/source_continuation_20261008/audit-after/) |

| Profile | ใหม่: prerequisite cases | gold เดิม | coverage ที่เพิ่ม |
|---|---:|---:|---|
| AI-2566-coop | 5/5 | 5/5 | 5 course facts |
| BIT-2565-coop | 4/4 | 5/5 | 4 course facts |
| BIT-2565-no-coop | 4/4 | 5/5 | 4 course facts; เพิ่ม catalog2 ไม่เพิ่มแผน |
| DSBA-2565 coop/no-coop | n/a | 5/5 ต่อแผน | ไม่เพิ่ม source labels รอบนี้ |
| IT-2565 coop/no-coop | n/a | 5/5 ต่อแผน | ไม่เพิ่ม source labels รอบนี้ |
| DSBA/IT/BIT-2560 ทั้งหกแผน | n/a | 5/5 ต่อแผน; expanded65/65รวม | reused labels เดิม ไม่ review ซ้ำ |
| legacy | n/a | 5/5 safety cases | snapshot DB เดิม ไม่ใช่ reconstruction/identity verification |

เก็บ backup 8 snapshots สำหรับสาม working DB พร้อม integrity/hash ใน [ingest manifest](results/source_continuation_20261008/live_ingest.json) และ [durable backups](results/source_continuation_20261008/backups/) Rollback ต้องเลือก snapshot แรกของแต่ละ DB ก่อน batch, สำรองสถานะใหม่ก่อน, ตรวจ hash/integrity และหยุด verified backend ไม่ restore snapshot ระหว่าง batch โดยไม่ตรวจลำดับ ไม่ได้ rollback จริง

## ยังไม่ยืนยัน / งานถัดไป

- เป็น saved-OCR reconstruction ไม่ fresh OCR/full-book run; ไม่มี raw extraction accuracy เพิ่มจาก batch นี้
- independent study-plan labels DSBA/IT-2565 ทั้งสี่แผนยังขาด; field/prerequisite/category/graduation ทุกเล่มยังไม่ครบ
- BIT graduation labels ยังไม่เข้า production; current runtime จึงยังตอบเพียง reference-only ไม่อ้าง eligibility ครบ
- PDF URL/paired citations มีจริง แต่ in-app viewer แสดง blank screen: [ภาพ](results/source_continuation_20261008/pdf_viewer_blank.png) ยังไม่ยืนยัน visible viewer สำเร็จ
- program-summary folios ยังไม่ครบ; untouched held-out, cold/warm difficult LLM latency, actual timeout exhaustion/process-kill recovery, clean first-time install/model download และ legacy identity ยัง n/a
- ไม่มี verified AI-old/same-year revision/dual-degree inputs; L4 ที่ต้องใช้ข้อมูลเหล่านี้ยัง blocked
- ผล provenance รอบนี้เป็น structured SQL replay และ synthetic guard; ไม่ใช่ exhaustive real LLM fallback verification

คำสั่ง resume และ authoritative NEXT ACTION อยู่ [PROGRESS.md](PROGRESS.md) ไม่ทำ slides/video/publication
