# ผลตรวจหลักสูตรเก่า พ.ศ. 2560

## Summary

ตรวจทั้งหก profile ก่อนแก้ข้อมูลแล้ว โดยเก็บ baseline แยกไว้ งานแก้เฉพาะจุดผ่าน development Q&A 65/65 ข้อ แต่ยังไม่ยืนยันหนังสือทั้งเล่มหรือ held-out accuracy
HIGH/MED นับจากรายงาน audit_all ที่ยังเปิดอยู่ ไม่ใช่จำนวนคำถามที่ตอบผิด แต่ละ profile มี HIGH ด้าน prerequisite coverage และ full source fidelity
จำนวนหน้าด้านล่างหมายถึงหน้าตารางแผนการศึกษาที่ตรวจรหัส ตัวเลือก credit/hour pattern ผลรวม และเลขหน้า ไม่ใช่การตรวจทุก field/ทุกคำอธิบายรายวิชา

| profile | HIGH | MED | PDF ที่ตรวจ / หน้าในเล่ม | ภาคการศึกษาที่ตรง | หน่วยกิต DB / เล่ม | Q&A ที่ผ่าน | ยังไม่ยืนยัน |
|---|---:|---:|---|---:|---:|---:|---|
| `dsba-2560-coop` | 2 | 0 | 30, 31, 32, 33, 34 / 25, 26, 27, 28, 29 | 8/8 | 126/126 | 11/11 | ชื่อ/หมวด/type/prerequisite ครบทั้งเล่ม n/a |
| `dsba-2560-no-coop` | 2 | 0 | 25, 26, 27, 28, 29 / 20, 21, 22, 23, 24 | 9/9 | 126/126 | 10/10 | ชื่อ/หมวด/type/prerequisite ครบทั้งเล่ม n/a |
| `it-2560-coop` | 2 | 0 | 34, 35, 36, 37, 38, 39, 40 / 29, 30, 31, 32, 33, 34, 35 | 8/8 | 130/130 | 12/12 | ชื่อ/หมวด/type/prerequisite ครบทั้งเล่ม n/a |
| `it-2560-no-coop` | 2 | 0 | 27, 28, 29, 30, 31, 32, 33 / 22, 23, 24, 25, 26, 27, 28 | 8/8 | 130/130 | 12/12 | ชื่อ/หมวด/type/prerequisite ครบทั้งเล่ม n/a |
| `bit-2560-coop` | 2 | 0 | 27, 28, 29, 30 / 22, 23, 24, 25 | 8/8 | 126/126 | 10/10 | ชื่อ/หมวด/type/prerequisite ครบทั้งเล่ม n/a |
| `bit-2560-no-coop` | 2 | 0 | 23, 24, 25, 26 / 18, 19, 20, 21 | 8/8 | 126/126 | 10/10 | ชื่อ/หมวด/type/prerequisite ครบทั้งเล่ม n/a |

## HIGH

- ทุก profile: ยังตรวจคำอธิบายวิชาบังคับก่อนและ field ทั้งเล่มไม่ครบ การไม่มี prerequisite edge ไม่ใช่หลักฐานว่าไม่มีวิชาบังคับก่อน
- งานที่เคยติด IT coop PDF36/40 และ BIT coop PDF30 แก้ผ่านข้อมูล ingest ที่ตรวจแยกและสำรอง DB แล้ว ไม่แก้ frozen OCR/A0/A1/held-out

## สาเหตุและงานแก้

- code bug: แก้ name matching ภาษาไทยให้คืนตัวเลือกเมื่อกำกวม; guard อนุญาตเฉพาะรหัสที่ resolver ตรวจจาก DB แล้ว; ให้ตัวเลือกหลักสูตรชัดเจนมีลำดับก่อนคำในชื่อวิชา; แยก elective slot ที่ wildcard/เลขลำดับซ้ำ; อัปเดตชื่อใน plan_item จริง
- data-ingest bug: ย้าย IT coop ไป schema fidelity ครบหก column และคืนแถว/กลุ่มตัวเลือกผ่าน full-term reviews; บันทึก BIT PDF174 เป็นหน้า97ในเล่มหลังตรวจภาพ ไม่ใช้ offset เดา
- OCR loss: ตัวเลือก IT ขาด ชื่อเหลื่อมและหัวข้อแขนงปน; hour pattern ผิดแม้ผลรวมถูก; DSBA wildcard สั้นลงและชื่อ alternative BIT หาย แก้เฉพาะ curated ingest จึงไม่ใช่ OCR accuracy ที่ดีขึ้น
- source ambiguity: ตาราง IT แยกแขนงเป็น bundle ที่เลือกอย่างใดอย่างหนึ่ง การแสดงทุกตัวเลือกไม่ได้อนุญาตให้ผสมแขนง; ช่องว่างในชื่อ BIT06036018 อยู่ในเล่ม จึงไม่แก้

## หลักฐานและวิธีตรวจซ้ำ

- [baseline](../../docs/results/old2560_baseline.json), [เปรียบเทียบภาคการศึกษา](../../docs/results/old2560_book_terms_verified.json), [DB](../../docs/results/old2560_db_verified_v2.json)
- [development Q&A](../../docs/results/old2560_qa_complete.json), [gold เดิม](../../docs/results/old2560_existing_gold_complete.json), [version isolation](../../docs/results/old2560_version_isolation_complete.json), [tests](../../docs/results/old2560_regressions_launcher_verified.json)
- [UI ทั้งหก profile](../../docs/results/old2560_ui_observations.json), [UI ชื่อวิชา IT หลังแก้](../../docs/results/old2560_ui_final_name_question.json), [UI วิชาบังคับก่อนจากชื่อ](../../docs/results/old2560_ui_name_prerequisite.json)
- [ผลคำสั่งเปิด backend และ HTTP](../../docs/results/old2560_backend_start_verified.json), [Q&A หลัง restart](../../docs/results/old2560_backend_restart_probe.json)
- ใช้ scripts/audit_all.py, scripts/audit_old2560.py, scripts/compare_old2560_book_terms.py, scripts/run_old2560_qa.py, scripts/run_qa_gold.py และ scripts/run_version_isolation.py โดยระบุ --app-root และ --output ตาม docs/PROGRESS.md

## ค่าที่ยังไม่ได้วัด

- full field accuracy, prerequisite coverage ครบทั้งเล่ม และหลักฐานยืนยันว่าไม่มีรายวิชาจริง: n/a
- held-out accuracy/seed stability และ cold LLM latency สำหรับคำถามยาก: n/a ชุดที่ใช้แก้เป็น development probes ไม่ใช่ held-out
- version isolation ทดสอบคำถามเดียวกันใน2560/2565ทั้งหกคู่ ผลต่างของรหัสในDBไม่ใช่การรับรอง field ของเล่ม2565ครบทุกแถว
- ไม่ได้รัน OCR ใหม่ ไม่เปลี่ยน input เดิม และไม่แตะ main; การสร้าง DB ใหม่จาก OCR เดิมล้วนยังอาจ fail ตามข้อมูลที่หาย ให้ใช้ reviewed ingest และ helper ที่ระบุไว้
