# ข้อกำหนดและหลักฐาน Week 11

ตรวจภาพหน้าจากต้นฉบับเมื่อ 2026-10-06 ไม่ใช้ OCR เป็นเฉลยอิสระ

## ข้อกำหนด P2

แหล่งข้อกำหนด: `ch1_Introduction.pdf` PDF หน้า 5/7 (SHA256 เริ่ม `2544eabb0c81`); ภาพและ hash อยู่ใน [inventory.json](inventory.json)

| ข้อกำหนด | น้ำหนัก | ส่วนที่ทำงาน | หลักฐาน | สถานะ / ช่องว่าง |
|---|---:|---|---|---|
| Database/RAG | 20 | SQLite read-only, schema validation, version isolation, DB-backed study relations | [DB-only report](../db_only_submission/DB_ONLY_REPORT.md), counterfactual tests | ตรวจส่วนที่แก้แล้ว; legacy identity และ prerequisite coverage ยังไม่ครบ |
| OCR | 20 | typhoon-ocr1.5-3b → normalization | รายงาน Lab09/robustness, rendered-page reviews | curated corrections ไม่ใช่ OCR gain; full-book transcription/field GT ไม่ครบ |
| ความแม่นยำ/คุณภาพผลลัพธ์ | 20 | คำตอบจากข้อมูลที่ค้นและการคำนวณที่กำหนด | gold regression, source review 49 ภาคการศึกษารุ่นเก่า | ไม่ใช่ full-book accuracy; final independent held-out ยังไม่ครบ |
| LLM question answering | 30 | Qwen เลือก SQL/field references เฉพาะคำถามที่ยังไม่เข้ารูปแบบ; ห้ามส่งข้อเท็จจริงอิสระ | provenance checks + UI/API | ต้องตรวจทั้งความหมาย ความครบ และ citation; HTTP 200 ไม่ใช่คะแนนความถูกต้อง |
| แอปและเอกสาร | 10 | Thai frontend, FastAPI, launcher, README | UI states/layout, setup checks | การเผยแพร่/สิทธิ์ collaborator ยังไม่ตรวจ; slides/video เลื่อนไว้ตามคำขอ |

เกณฑ์ในเอกสาร: ความแม่นยำ `>91%` เต็ม, `80–90%` ประมาณ 2/3, `<80%` ประมาณ 1/3; ส่วน LLM ระบุ `>91%` เต็ม, `80–90%` ครึ่ง, `<80%` เริ่มต้น ต้องตอบถูกพร้อมอ้างหน้า/หัวข้อ เกณฑ์ไม่ระบุช่วง `(90%,91%]` ชัดเจน จึงไม่กำหนดคะแนนเอง และไม่รับประกันคะแนนอาจารย์

| Challenge | สิ่งที่ต้องทำ | หลักฐานที่มี / ช่องว่าง |
|---|---|---|
| L1 | รหัส ชื่อ หน่วยกิต พร้อม source | gold/dev และ source-reviewed subset; ไม่ครบทุกวิชา |
| L2 | อ่านตาราง กรอง รวมหน่วยกิต prerequisite และเงื่อนไขลงทะเบียนตามเล่ม | 49/49 ภาคการศึกษารุ่นเก่าตรงในรหัส ตัวเลือก hour pattern และผลรวม; เงื่อนไขทั้งเล่มยังไม่ครบ |
| L3 | แผน 3.5 ปี ตรวจจบ เปรียบเทียบเก่า/ใหม่ | version isolation/comparison มี; แผนเร่ง/เงื่อนไขจบอิสระยัง n/a ห้ามรับรองการเปิดรายวิชา |
| L4 | หลาย revision รวมรุ่นปีเดียวกัน/สองปริญญาเมื่อมีแหล่งข้อมูล | มีสองปี DSBA/IT/BIT; ไม่พบต้นฉบับ same-year revision/dual-degree/AI เก่า จึงยังไม่อ้างครบ L4 |
| ความเร็ว | คำถามยาก `<5s` รวม retrieval + generation | ต้องแยก cold/warm/cache และคำตอบครบถูก; ผลเดิมไม่ใช่หลักฐาน cold challenge |

คะแนนพิเศษรวมสูงสุด **+10** ไม่ใช่ +20 จากสองรายการ

## L11 และประกาศล่าสุด

ตรวจ `L11_Front End Development_1.pdf` (SHA256 เริ่ม `25c83337ddd7`) PDF หน้า 9,16–18,28–29 / หน้าใน slide 12,22,24,25,36,40: responsive; README API contract; idle/loading/success/error; API key เฉพาะ backend; ไม่ใช้ innerHTML กับคำตอบ; backend validation; wireframe/HTML/CSS/JS ต่อ API จริง

แอปมี wireframe และ API contract เดิมใน `ocr_final/frontend/` ใช้ textContent, backend Pydantic และสถานะทั้งสี่แล้ว ต้องตรวจ running application หลังเปลี่ยน backend ด้วย ประกาศใน slide ระบุวันที่เดิม 5 ตุลาคม แต่ **ประกาศล่าสุดที่ผู้ใช้แจ้งว่าเลื่อน supersedes ข้อนี้**; 12 ตุลาคมเป็นวันที่เสนอแบบมีเงื่อนไข ไม่ใช่นัดยืนยัน ไม่พบไฟล์ประกาศใหม่แยกต่างหากใน inputs ที่ตรวจ

## ตรวจตัวตนหนังสือ

| หนังสือ | ปี/ชนิดจากภาพปก PDF หน้า 1 | สถานะ |
|---|---|---|
| DSBA-60.pdf | หลักสูตรใหม่ 2560 | ตรวจภาพแล้ว |
| IT-60.pdf | หลักสูตรปรับปรุง 2560 | ตรวจภาพแล้ว |
| BIT-60.pdf | หลักสูตรใหม่ 2560 (นานาชาติ) | ตรวจภาพแล้ว |
| DSBA.pdf | หลักสูตรปรับปรุง 2565 | ตรวจภาพแล้ว |
| IT.pdf | หลักสูตรปรับปรุง 2565 | ตรวจภาพแล้ว |
| BIT-65.pdf | หลักสูตรปรับปรุง 2565 (นานาชาติ) | ตรวจภาพแล้ว |
| AI.pdf | หลักสูตรใหม่ 2566 | ใช้ผลตรวจภาพเดิม `ai_identity_cover_review.json`; ไม่ตรวจงานเดิมซ้ำ |

inventory พบ 7 PDF, 13 normalized profiles + legacy 1 รายการ; legacy รวม page fragments ไม่ใช่หนังสือรุ่นเพิ่มเติมที่ยืนยันแล้ว ดู [inventory.json](inventory.json) สำหรับ hash/database/source mapping

## Ground truth ที่มีและที่ยังขาด

ไม่ตัดสินจากชื่อไฟล์อย่างเดียว: มี `study_plan_relationships.json` ครอบคลุม IT-2560 และ current DSBA/IT; `prerequisite_source_reviews.json` มี DSBA/IT/BIT-2560; `old2560_name_reviews.json` มี IT-2560; ledger ใน `docs/results/old2560_book_terms_verified.json` ครบ 49 ภาคการศึกษาของทั้งหกรุ่นเก่า (รหัส ตัวเลือก hour patterns และผลรวม ไม่ใช่ทุก field)

AIT/current DSBA/IT มี flat/master plan GT แต่ provenance ของทุก field ยังไม่ได้ตรวจครบ BIT/current ใช้ OCR/combined review บางส่วน ไม่พบ full independent GT ที่ตรวจทั้งเล่ม AI/legacy ไม่อยู่ใน A1 stratified old/current DSBA/IT/BIT batch นี้ ทุก profile ยังขาด independent full names/category/description/prerequisite/graduation review และ book-wide absence proof

ไฟล์ `versioned_eval_questions.json` และผล robustness เดิมมี labels ที่สร้างจาก DB/ใช้ debug แล้ว จึงไม่ใช่ held-out อิสระที่ไม่เคยใช้ปรับแก้ ไม่ส่งเข้า production ไม่แก้ frozen labels เพื่อให้คะแนนดีขึ้น
