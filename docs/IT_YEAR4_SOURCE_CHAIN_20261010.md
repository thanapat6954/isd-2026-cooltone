# ตรวจ source chain ของ IT-2565 ปี4

## ขอบเขตที่ตรวจจากภาพจริง

วันที่10ตุลาคม2026 บน `week11_thanapat`; ไม่ commit/push/merge. ใช้ curriculum-audit และ PDF workflow อ่านภาพ ไม่ใช้ embedded Thai text หรือคำตอบแอปเป็นเฉลย. Source SHA256 `aca97dc8b57308b30355e74e384c042d27d005310c6b4a9b72ecf79514543afa` ใช้ตรวจ dependency เท่านั้น ไม่ใช่ข้อพิสูจน์ความถูกต้องของเนื้อหา.

| สิ่งที่สังเกตอิสระจากภาพ | PDF page | printed page | หลักฐานภาพ |
|---|---:|---:|---|
| ปกเทคโนโลยีสารสนเทศ ปรับปรุง2565 | 1 | I | [ปก](results/week11/source_pages/IT-aca97dc8b573-001.png) |
| 3.1.4.1 แผนที่ไม่เข้าโครงการสหกิจ | 31 | 26 | [หัวข้อ](results/viewer_source_20261009/source_pages/IT-aca97dc8b573-031.png) |
| 3.1.4.2 แผนสำหรับโครงการสหกิจ | 38 | 33 | [หัวข้อ](results/viewer_source_20261009/source_pages/IT-aca97dc8b573-038.png) |
| ไม่สหกิจ ปี4/1: 06016406 โครงงาน1;060164xx วิชาเลือกทางเทคโนโลยีสารสนเทศ3;90643021 ผู้ประกอบการสมัยใหม่;9064xxxx GE1;xxxxxxxx เลือกเสรี1 รวม15 | 37 | 32 | [ตาราง](results/current_source_20261008/source_pages/IT-aca97dc8b573-037.png) |
| ไม่สหกิจ ปี4/2:06016407 โครงงาน2;9064xxxx GE2;xxxxxxxx เลือกเสรี2 รวม9 | 37 | 32 | ภาพเดียวกัน |
| สหกิจ ปี4/1:06016406 โครงงาน1;060164xx วิชาเลือกทางเทคโนโลยีสารสนเทศ1;90643021;9064xxxx GE1;xxxxxxxx เลือกเสรี1/2 รวม18 | 43 | 38 | [ตาราง](results/current_source_20261008/source_pages/IT-aca97dc8b573-043.png) |
| สหกิจ ปี4/2:06016407;06066100 การบริหารโครงการเทคโนโลยีสารสนเทศ;90642033 กฎหมายสำหรับคนรุ่นใหม่;90644042 การสื่อสารและการนำเสนออย่างมืออาชีพ;9064xxxx GE2 รวม15 | 44 | 39 | [ตาราง](results/current_source_20261008/source_pages/IT-aca97dc8b573-044.png) |

ตรวจชื่อไทย/English รหัส หน่วยกิตและชั่วโมงทุกแถว Year4: 19profile-row cases/4ภาค/3content pages. โครงงานเป็น3(0-9-0); IT elective เป็น3(3-0-6) หรือ3(2-2-5) หรือ3(0-6-3); GE3(3-0-6); free3(x-x-x). ชั่วโมง alternative ไม่ใช่สามรายวิชาต้องรวม9หน่วยกิต. Faculty requirement เป็นหัวข้อของ90643021/90642033/90644042 ไม่ให้ปนในชื่อ. หน้านี้ไม่มี specialization branches ในYear4; ไม่ได้ใช้ตารางYear4เพื่อยืนยัน prerequisite หรือสิทธิลงทะเบียน.

PDF43 เริ่มด้วย continuation ของสหกิจ06016482จากภาคก่อน แต่หัวข้อปี4/1เริ่มหลังแถวรวม6 จึงไม่นำ continuation มารวม18อีก. ความถูกต้องเต็มรูปของภาคก่อนใช้ review เดิม42–43 ไม่ประกาศว่าได้รับการตรวจใหม่ทั้งหมดในรอบนี้.

## สาเหตุที่ semester checks ผ่าน แต่ comparison metadata ขาด

`prepare_source_ingest.py` รับ production `IT-2565-plan-corrections.json` → import/load และ targeted metadata repairก่อนหน้า → `plan_item` มี19แถวYear4พร้อมรหัส/ชื่อ/pattern/page pairs. `migrate_study_evidence.py` อ่าน `shared/study_plan_relationships.json` ซึ่งมี IT เฉพาะYear2/S2และYear3/S1. จึงไม่มีYear4ใน `study_term`, `study_page`, `study_item`.

Semester checksก่อนหน้าเทียบ plan rows/totals/folios ไม่ได้ยืนยันว่า comparison evidence metadataครบ; `study_plan.py` แสดง printed_total เฉพาะเมื่อเจอterm reviewและmembership จึงไม่มีtotalในคำตอบcomparisonแม้rowsถูก. จัดเป็น **source-approved ingestion metadata omission (ประเภท1)** ไม่ใช่ missing source หรือแผนกลับด้าน. การตรวจนี้ไม่เปลี่ยน expected answers ให้ตรงแอป.

## การแก้แบบจำกัดขอบเขต

เพิ่ม profile identity/metadata-year approval ใน production review และ `ingest_reviewed_term_metadata.py`. ตรวจ identity/version/source hash/rowcount/ชื่อไทยEnglish/code-pattern/ชั่วโมง/PDF+folioตรงทุกแถวก่อนสร้างterm/membership. ไม่แก้ course/plan_item/prerequisite/alternative facts; mismatches fail loudly. ไม่อ่าน evaluation labels. Buildเรียก importerหลังnames/citationsพร้อมbackup; working repairsเป็น transactionเฉพาะmetadata ไม่แทนDBทั้งก้อน.

Isolated2DB: changes17/14, integrity/idempotence/facts unchangedผ่าน. Focused tests3ผ่าน. ค่าจำนวนchangesเป็น metadata inserts ไม่ใช่31คำตอบผิดหรือOCRaccuracy.

## สถานะการตรวจแยกกัน

| มิติ | ขอบเขต | สถานะ |
|---|---|---|
| Source fidelity | Year4รหัส/ชื่อ/credits/options/term/page mapping/plan identity19แถว | ตรวจภาพแล้ว; categoriesทั้งหมด/prerequisites/registrationไม่ได้ยืนยันจากหน้าเหล่านี้ |
| DB consistency | isolatedmetadata2DB/4terms | integrity/idempotence/unchanged facts ผ่าน |
| Answer completeness | before4/after4HTTP ทั้ง2routes; 19row cases/4terms | ตรวจชื่อ/options/total18,15,15,9ตรงภาพ; specific Year4 comparison ผ่าน ไม่ใช่ทุกคำถาม |
| Citation support | specificYear4claimsและrealbrowserclick | 3/3content pages43,44,37เห็นตารางจริงกับbook38,39,32; 19citationsในUI |

หลักฐาน actualSQL/rows/answers: [before](results/it_year4_source_chain_20261010/before.json), [after](results/it_year4_source_chain_20261010/after.json), [UI](results/it_year4_source_chain_20261010/ui-answer.jpg), [citation43](results/it_year4_source_chain_20261010/ui-source43.jpg), [citation44](results/it_year4_source_chain_20261010/ui-source44.jpg), [citation37](results/it_year4_source_chain_20261010/ui-source37.jpg). Saved-OCR reconstruction2profiles exit0/protectedunchanged; ไม่ใช่freshOCRหรือOCRaccuracygain. [locked checks](results/it_year4_source_chain_20261010/checks/checks.json):269unit/30schema/6frontend/70gold/65oldQA/14provenance/6version setsผ่าน7jobs; guardเดิมไม่ครอบคลุมproductionapprovalJSON จึงไม่ใช้ยืนยันcoverageเกินรายการhashที่บันทึก.

งานallcurricula/versionsและheld-out/reconstruction/installation/legacyยังเปิดตาม PROGRESS; ไม่มีการอ้างผลITนี้เป็นความถูกต้องของทุกคำถาม.
