# ดัชนีข้อมูลสำหรับตรวจหลักสูตร

## ผลตรวจภาพเพิ่มเติม 9 ตุลาคม 2569

### รอบต่อเนื่องล่าสุด — ใช้ก่อนตารางประวัติด้านล่าง

IT-2565 ตรวจตารางครบทั้งสองแผน แผนละ 8/8 ภาคและ 129 หน่วยกิต: labels เดิมแผนละ 2 ภาคใช้ร่วมกับ [labels อีก 6 ภาคต่อแผน](evaluation/semester-review-20261009-b/IT-2565/coop-terms.json) และ [ไม่สหกิจศึกษา](evaluation/semester-review-20261009-b/IT-2565/no-coop-terms.json) รวมแผนละ 54 ตัวเลือก (รวมกลุ่มทางเลือก ไม่ใช่จำนวนวิชาที่ต้องเรียนทั้งหมด) รหัสจริงไม่ซ้ำ 47 สหกิจศึกษา / 45 ไม่สหกิจศึกษา ตรวจ shared courses และกลุ่มวิชาบังคับเฉพาะสาขา 15 หน่วยกิตจาก PDF25/หน้า20 ต้องเลือกหนึ่งกลุ่ม; โมดูลวิชาเลือกไม่บังคับเลือกโมดูลเดียวตาม PDF29/หน้า24. ชื่อที่ตรวจเพิ่มอยู่ใน [source observations](evaluation/IT-2565/semester-observations-20261009-b.json); ยังไม่ครอบคลุมชื่อทั้ง catalog หรือ prerequisite.

DSBA-2565 สหกิจศึกษาปี4ภาค1ตรวจเพิ่มจาก PDF36/หน้า35 พบ 06026215 โครงงาน2 จำนวน3หน่วยกิต รวมภาค12: ข้ออ้างเดิมว่ารหัส/ชื่อหายเป็นการอ่านภาพผิด ไม่ใช่แหล่งข้อมูลหายหรือข้อแก้ของ renderer. [labels ใหม่ครบ8ภาค](evaluation/semester-review-20261009-b/DSBA-2565/coop-terms.json) มี45ตัวเลือก/36รหัสจริงไม่ซ้ำ รวม132; [ไม่สหกิจศึกษา](evaluation/semester-review-20261009-b/DSBA-2565/no-coop-terms.json) ครบ8ภาค45ตัวเลือก/34รหัสจริงไม่ซ้ำ. เก็บ labels/ผลเดิมไว้เป็นประวัติ ไม่แก้ held-out. รายละเอียดและหลักฐานอยู่ `docs/results/it_plan_review_20261009/` ที่ repository root.

ตารางด้านล่างเป็นสถานะก่อนรอบต่อเนื่องนี้ ไม่ใช่ coverage ปัจจุบัน.

ข้อมูลด้านล่างเป็น development/regression จากภาพต้นฉบับโดยอิสระ ไม่ใช่ held-out และไม่ใช้เป็น production ingestion เฉลยเดิมไม่ถูกเปลี่ยนเพื่อให้ตรงกับคำตอบระบบ

| หลักสูตร/แผน | ภาคการศึกษาที่ตรวจ | ตัวเลือกรายวิชาใน profile | รายวิชารหัสจริงไม่ซ้ำใน profile | หน้าที่ตรวจ | labels |
|---|---|---|---|---|---|
| DSBA-2565 ไม่สหกิจศึกษา | 8 จาก 8 | 45 | 34 | PDF23–29 / หน้า22–28 | [no-coop-terms.json](evaluation/DSBA-2565/no-coop-terms.json) |
| DSBA-2565 สหกิจศึกษา | 7 จาก 8 | 41 | 35 | PDF30–36 / หน้า29–35 | [coop-terms.json](evaluation/DSBA-2565/coop-terms.json) |
| IT-2565 ไม่สหกิจศึกษา | 2 จาก 8 | 13 | 13 | PDF31–32 / หน้า26–27 | [no-coop-terms.json](evaluation/IT-2565/no-coop-terms.json) |
| IT-2565 สหกิจศึกษา | 2 จาก 8 | 13 | 13 | PDF38–39 / หน้า33–34 | [coop-terms.json](evaluation/IT-2565/coop-terms.json) |

ตัวเลือกนับรหัสทางเลือกแต่ละรายการ ส่วนหน่วยกิตของทางเลือกคิดเพียงหนึ่งชุด ไม่รวม elective slots เป็นรายวิชารหัสจริง ค่า unique ในแต่ละ profile รวมข้าม profile ไม่ได้เพราะมีรายวิชาร่วมกัน ชื่อ หมวดวิชา เงื่อนไขเลือกกลุ่ม และวิชาบังคับก่อนยังไม่ยืนยันครบจาก labels ชุดนี้ DSBA สหกิจ ปี4ภาค1 ยังไม่ทำเฉลยจากแถวที่รหัส/ชื่อไม่ปรากฏในภาพต้นฉบับ ต้องตรวจขอบตารางต่อ ไม่เติมโดยอาศัยแผนอื่น ตาราง coverage เดิมด้านล่างเป็นประวัติก่อน batch นี้

แยก evaluation labels ออกจากข้อมูลที่ใช้ ingestion อย่างชัดเจน การย้ายไฟล์ไม่ใช่การยืนยันข้อมูลกับหนังสือ และไม่เปลี่ยนเฉลยเดิม

สหกิจศึกษา = coop; ไม่สหกิจศึกษา = no-coop ส่วนไม่แยกแผนหมายถึง dataset ไม่ระบุแผน ไม่ใช่ข้อสรุปว่าเล่มไม่มีแผนอื่น

`AIT` ใน labels เดิมถูกใช้กับ AI ผ่าน `run_lab8b.PROFILES.ai`; approval ปก AI.pdf หน้า PDF 1 ระบุ 2566 ส่วน IT ใช้ IT.pdf รุ่น 2565 จึงเป็นคนละหลักสูตร ไม่ใช่รุ่นของ IT (metadata plan ใน AIT เดิมเป็น null ยังต้องตรวจว่าครอบคลุมแผนใด)

## ชื่อเดิมและตำแหน่งปัจจุบัน

| ชื่อเดิม | ตำแหน่งใหม่ | หน้าที่และหลักฐาน identity | สถานะ |
|---|---|---|---|
| `AIT_academic_plan.json` | [data/ground_truth/evaluation/AI-2566/academic_plan.json](evaluation/AI-2566/academic_plan.json) | เฉลย evaluation: run_lab8b.PROFILES.ai; document_identity_reviews ปก หน้า PDF 1 | ยังไม่ยืนยันทุกแถว; plan=null ใน labels ไม่ได้ยืนยันว่าเล่มไม่แยกแผน |
| `document_identity_reviews.json` | [data/source_reviews/shared/document_identity_reviews.json](../source_reviews/shared/document_identity_reviews.json) | ข้อมูลสำหรับ ingestion: ingest_identity_reviews.py; AI.pdf ปก หน้า PDF 1 | source-reviewed identity เฉพาะที่มี approval |
| `DSBA_academic_plan_coop.json` | [data/ground_truth/evaluation/DSBA-2565/coop.json](evaluation/DSBA-2565/coop.json) | เฉลย evaluation: run_lab8b.PROFILES.dsba-coop; DSBA unified source_pages_by_plan | labels ที่สร้างต่อจาก master; ไม่ใช่หลักฐานอิสระครบทุก field |
| `DSBA_academic_plan_no_coop.json` | [data/ground_truth/evaluation/DSBA-2565/no-coop.json](evaluation/DSBA-2565/no-coop.json) | เฉลย evaluation: run_lab8b.PROFILES.dsba-no-coop; DSBA unified source_pages_by_plan | labels ที่สร้างต่อจาก master; ไม่ใช่หลักฐานอิสระครบทุก field |
| `DSBA_ground_truth.json` | [data/source_reviews/DSBA-2565/master.json](../source_reviews/DSBA-2565/master.json) | ข้อมูลสำหรับ ingestion: run_lab8b lab8_input; source_file + plans + schedule_by_plan | ข้อมูล clean import เดิม; ไม่ถือว่าทุก field visually verified |
| `general_education_ground_truth.json` | [data/source_reviews/shared/general_education_ground_truth.json](../source_reviews/shared/general_education_ground_truth.json) | ข้อมูลสำหรับ ingestion: run_lab8b --general-education | ยังขาด PDF provenance; ชื่อ directory ไม่ยืนยันข้อเท็จจริง |
| `IT_academic_plan_coop.json` | [data/ground_truth/evaluation/IT-2565/coop.json](evaluation/IT-2565/coop.json) | เฉลย evaluation: run_lab8b.PROFILES.it-coop; IT.pdf หน้าตารางแผนที่มี review | labels จาก spreadsheet; ยังไม่ยืนยันทุกแถว |
| `IT_academic_plan_no_coop.json` | [data/ground_truth/evaluation/IT-2565/no-coop.json](evaluation/IT-2565/no-coop.json) | เฉลย evaluation: run_lab8b.PROFILES.it-no-coop; IT.pdf หน้าตารางแผนที่มี review | labels จาก spreadsheet; ยังไม่ยืนยันทุกแถว |
| `old2560_name_reviews.json` | [data/source_reviews/shared/old2560_name_reviews.json](../source_reviews/shared/old2560_name_reviews.json) | ข้อมูลสำหรับ ingestion: ingest_name_reviews.py; แถวที่มี approval แยก source | source-reviewed subset เท่านั้น |
| `prerequisite_source_reviews.json` | [data/source_reviews/shared/prerequisite_source_reviews.json](../source_reviews/shared/prerequisite_source_reviews.json) | ข้อมูลสำหรับ ingestion: ingest_prerequisite_reviews.py; documents/source hashes/pages | source-reviewed subset ไม่ใช่วิชาบังคับก่อนครบทั้งเล่ม |
| `rules_ground_truth.json` | [data/ground_truth/shared/rules.json](shared/rules.json) | กฎ evaluation ที่ยังไม่ยืนยัน: content programs/rules จาก spreadsheet; ยังไม่มี page mapping ที่ยืนยันราย label | ปี/revision/page ของแต่ละ label ยังไม่ยืนยัน; ห้ามใช้เป็น production facts |
| `study_plan_db_review.json` | [data/source_reviews/shared/study_plan_db_review.json](../source_reviews/shared/study_plan_db_review.json) | หลักฐาน approval: migrate_study_evidence.py; ingestion_sha256 and approved_pages | approval/provenance ไม่ใช่ evaluation answers |
| `study_plan_relationships.json` | [data/source_reviews/shared/study_plan_relationships.json](../source_reviews/shared/study_plan_relationships.json) | ความสัมพันธ์ในแผน: migrate_study_evidence.py; approval study_plan_db_review.json | approved page/term subset ไม่ใช่ครบทุก track |

## ความครอบคลุมและข้อจำกัด

- evaluation/ เก็บ labels รายหลักสูตร/ปี แยก plan; shared/ เก็บกฎที่ยังไม่ยืนยันปีและ page; history/ เก็บกรณี development ที่สร้างจาก DB ไม่ใช่ held-out
- ../source_reviews/ เก็บ master, source approval และ relationships สำหรับ build/ingestion เท่านั้น runtime chatbot อ่าน SQLite ไม่อ่าน evaluation answers
- evaluation/*-2560/*-terms.json คือ ledger เดิมจาก rendered pages: codes, credit patterns/options, term totals, PDF/book pages เท่านั้น ชื่อ/category/prerequisite/เงื่อนไขจบที่ไม่ได้ตรวจคงเป็น unknown ห้ามป้อนเข้า flat-course evaluator
- BIT-2565 ทั้งสองแผนยังไม่มี flat evaluation labels; AI/DSBA/IT labels ปัจจุบันยังไม่ครบ field/source verification; legacy ยังไม่ยืนยัน identity จึงไม่สร้างปีหรือแผนขึ้นเอง
- L1–L4: tests/qa_gold.json เป็น development regression; historical versioned questions สร้างจาก DB ไม่ใช่หลักฐานอิสระ; ยังไม่มีชุด source-grounded ครบทุกระดับและ frozen ใหม่
- ไม่มีการลบ labels ที่ไม่ทราบหน้าที่ ไม่มีการแก้ DB/PDF/OCR/held-out; recovery เก็บนอก active dataset discovery ตาม migration manifest

## ความครอบคลุมแยกรายหลักสูตรและแผน

รอบ8ตุลาคมเพิ่ม [development prerequisite QA](evaluation/description-development-20261008.json): AI-2566 5กรณี, BIT-2565 4กรณีต่อแผน จากภาพคำอธิบายรายวิชา พร้อม [BIT graduation ข้อ26](evaluation/BIT-2565/graduation-reviewed-20261008.json) ที่ตรวจเฉพาะ appendix ของ BIT ยังไม่ใช่ coverage ทุกวิชา/ทุกเล่มหรือ held-out แยก production approvalsไว้ `data/source_reviews/description_prerequisites_20261008.json` ซึ่งไม่มีคำถาม/expected answers

| หลักสูตร/ปี | แผน | แหล่งข้อมูล | flat labels | semesters จากภาพที่ตรวจแล้ว | field labels ร่วม | L1–L2 development | สิ่งที่ยังขาด |
|---|---|---|---|---|---|---|---|
| DSBA / 2565 | coop | DSBA.pdf | [44 rows](evaluation/DSBA-2565/coop.json) | n/a | [3](evaluation/DSBA-2565/reviewed-fields.json) | n/a | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| DSBA / 2565 | no-coop | DSBA.pdf | [45 rows](evaluation/DSBA-2565/no-coop.json) | n/a | [3](evaluation/DSBA-2565/reviewed-fields.json) | n/a | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| AI / 2566 | coop | AI.pdf | [57 rows](evaluation/AI-2566/academic_plan.json) | [8](evaluation/AI-2566/coop-terms.json) | n/a | [13](evaluation/AI-2566/coop-qa.json) | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| IT / 2565 | no-coop | IT.pdf | [108 rows](evaluation/IT-2565/no-coop.json) | n/a | [4](evaluation/IT-2565/reviewed-fields.json) | n/a | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| IT / 2565 | coop | IT.pdf | [106 rows](evaluation/IT-2565/coop.json) | n/a | [4](evaluation/IT-2565/reviewed-fields.json) | n/a | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| DSBA / 2560 | no-coop | DSBA-60.pdf | n/a | [9](evaluation/DSBA-2560/no-coop-terms.json) | [5](evaluation/DSBA-2560/reviewed-fields.json) | [6](evaluation/DSBA-2560/no-coop-qa.json) | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| DSBA / 2560 | coop | DSBA-60.pdf | n/a | [8](evaluation/DSBA-2560/coop-terms.json) | [5](evaluation/DSBA-2560/reviewed-fields.json) | [6](evaluation/DSBA-2560/coop-qa.json) | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| IT / 2560 | no-coop | IT-60.pdf | n/a | [8](evaluation/IT-2560/no-coop-terms.json) | [17](evaluation/IT-2560/reviewed-fields.json) | [6](evaluation/IT-2560/no-coop-qa.json) | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| IT / 2560 | coop | IT-60.pdf | n/a | [8](evaluation/IT-2560/coop-terms.json) | [17](evaluation/IT-2560/reviewed-fields.json) | [6](evaluation/IT-2560/coop-qa.json) | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| BIT / 2565 | no-coop | BIT-65.pdf | n/a | [8](evaluation/BIT-2565/no-coop-terms.json) | n/a | [13](evaluation/BIT-2565/no-coop-qa.json) | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| BIT / 2565 | coop | BIT-65.pdf | n/a | [8](evaluation/BIT-2565/coop-terms.json) | n/a | [13](evaluation/BIT-2565/coop-qa.json) | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| BIT / 2560 | no-coop | BIT-60.pdf | n/a | [8](evaluation/BIT-2560/no-coop-terms.json) | [2](evaluation/BIT-2560/reviewed-fields.json) | [6](evaluation/BIT-2560/no-coop-qa.json) | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| BIT / 2560 | coop | BIT-60.pdf | n/a | [8](evaluation/BIT-2560/coop-terms.json) | [2](evaluation/BIT-2560/reviewed-fields.json) | [6](evaluation/BIT-2560/coop-qa.json) | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
| legacy / ยังไม่ทราบ | ยังไม่ยืนยัน | หลายเล่ม ยังไม่แยก identity | n/a | n/a | n/a | n/a | ชื่อ/category/prerequisite/เงื่อนไขจบ/L1–L4 ยังไม่ครบ |
