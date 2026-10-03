# การตรวจแหล่งข้อมูลของคำตอบ

ตรวจวันที่ 2026-10-04 บน branch `audit/curriculum-challenge`

## Summary

ยังยืนยันไม่ได้ว่าคำตอบใช้ DB เท่านั้น เพราะพบข้อมูลเพิ่มเติมหลังค้น SQL และเส้นทาง unknown ยังรับข้อความ LLM ที่ไม่อยู่ในแถวข้อมูลได้ การตรวจครั้งนี้ไม่แก้ production code, DB, OCR หรือ held-out

ผล live `POST /api/ask` ได้ HTTP 200 จำนวน 14/14 profile ครอบคลุม AI, DSBA, IT, BIT ทุกฉบับ/แผนที่ใช้งานและ legacy โดยใช้คำถามแผนการเรียนปี 3 ภาคการศึกษาที่ 1 สำหรับ 13 profile และคำถามหน่วยกิตสำหรับ legacy ไม่ใช่ผล gold accuracy หรือการตรวจหนังสือทั้งเล่ม

replay SQL ผ่าน SQLite `mode=ro` และ `query_only` พบ 61 ค่า-field ที่เปลี่ยนหรือเพิ่มใน 4 profile ได้แก่ DSBA-2565-coop, DSBA-2565-no-coop, IT-2565-coop และ IT-2565-no-coop ตัวเลขนี้รวมชื่อ รูปแบบหน่วยกิตและหน้าหนังสือ ไม่ใช่จำนวนคำตอบผิดหรือจำนวนข้อเท็จจริงที่แต่งขึ้น อีก 10 profile ไม่พบความต่างในค่า-field ของแถวสำหรับคำถามที่ทดสอบ แต่ยังสรุปไม่ได้ว่าทุกคำถามใช้ DB เท่านั้น เพราะ grouping และ printed_total บางส่วนอ่านจาก JSON

หลักฐานดิบ: [ผลตรวจ](../../docs/results/db_only_provenance_verified_20261004.json) ผลก่อนเพิ่ม frontend probe และก่อนแยก legacy DB copy ออกจากการเทียบ production files เก็บไว้ใน db_only_provenance_20261004.json และ db_only_provenance_final_20261004.json ไม่ได้เปลี่ยน production dependencies ระหว่างการตรวจ

## HIGH

1. `course_list` อ่าน `data/ground_truth/study_plan_relationships.json` แล้วแทนชื่อ/รูปแบบหน่วยกิต เพิ่ม printed_page_number, กลุ่มวิชาและ printed_total หลังค้น DB ข้อมูลนี้ผ่าน source-review และ SHA256 guard ตาม implementation เดิม แต่เป็นแหล่งเพิ่มเติมจาก JSON ไม่ใช่ค่าที่ดึงจาก SQLite เท่านั้น ตัวอย่าง IT-2565-coop รหัส 06016422: SQL ให้ชื่อ “ความมั่นคงปลอดภัยโครงสร้างพื้นฐานทางเทคโนโลยีสารสนเทศ” แต่ API ให้ “อินเทอร์เน็ตของสรรพสิ่ง”; credits_raw = 3(2-2-5) และ printed_page_number = 37 เพิ่มจาก overlay การตรวจนี้ไม่ตัดสินว่าชื่อฝั่งใดถูกตามหนังสือ
2. เส้นทาง unknown ส่งผล DB ให้ Qwen พร้อมคำสั่งห้ามเพิ่มข้อมูล แต่ `_ground_answer` คืนข้อความ model โดยไม่ตรวจค่าทั้งหมดเมื่อมี curriculum เดียว ทดสอบ guard ด้วยข้อความ `SYNTHETIC_UNSUPPORTED_FACT_999` ที่ไม่มีในแถวข้อมูล: ข้อความผ่านออกมา ข้อความนี้ใช้เฉพาะการทดสอบในเครื่อง ไม่ส่งให้ server และไม่ใช่หลักฐานว่า live LLM เคยตอบข้อความนี้จริง
3. live `/ask` แสดง model = `SQL (database-backed)` สำหรับคำถามแผนการเรียน IT ล่าสุด แม้มี JSON overlay จึงไม่ควรใช้ป้ายนี้เป็นหลักฐานว่าข้อมูลทั้งหมดมาจาก DB

## ขอบเขตและงานต่อไป

- SHA256 ของ DB ที่ใช้งาน 14 ไฟล์ รวม production dependencies ที่ตรวจ ไม่เปลี่ยนระหว่าง probe
- `audit_all.py` exit 1: 16 datasets, FAIL 1376, incomplete 4881, missing curricula = [] ตรงกับ checkpoint เดิม ไม่ใช่ข้อสรุปว่าคำตอบผิด 1376 ข้อ รายงานอยู่ใน `docs/results/db_only_audit_reports_20261004/audit_*.md`
- diagnostic runner exit 1 เพราะพบเงื่อนไข DB-only ไม่ผ่าน ไม่ใช่ crash; `py_compile` exit 0
- ไม่รัน gold, held-out หรือ regression suite เดิมซ้ำ เพราะไม่ได้แก้ production dependencies ผลเดิมยังเป็นผลเดิม ไม่ใช่การยืนยันใหม่ครั้งนี้ ไม่ตรวจ UI ใหม่และไม่อ้างว่าแก้ UI แล้ว
- ถ้าต้องบังคับ DB-only ต้อง back up ก่อนนำ source-reviewed facts/relationships เข้า schema และ build SQLite จากนั้นเลิก overlay ตอนตอบ และปิดหรือจำกัดข้อความ LLM ให้แสดงเฉพาะ field ที่ดึงได้ การแก้นี้ยังไม่ได้ทำในคำขอตรวจครั้งนี้
- ความถูกต้องของทุก field เทียบหนังสือ และอัตรา hallucination ของ live unknown questions: n/a

## วิธีรันซ้ำ

จาก repository root:

```powershell
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/audit_answer_provenance.py --app-root 'C:/Users/thana/OneDrive/เอกสาร/ocr_final' --output docs/results/new_provenance.json
.\ocr_final\venv\Scripts\python.exe ocr_final/scripts/audit_all.py --app-root 'C:/Users/thana/OneDrive/เอกสาร/ocr_final' --out docs/results/new_provenance_audit_reports
```
