# ส่วนติดต่อผู้ใช้และ API

ใช้ HTML/CSS/JavaScript เดิม ภาษาไทยและสีเขียว ไม่มี build step เว็บจริงเปิดจาก `/frontend/` ของ FastAPI ตาม [README หลัก](../../README.md) ไม่เปิด mock และไม่ต้องใช้ static server อีกตัว

## Contract ที่คงไว้

`POST /ask`:

```json
{"question":"แผนไม่สหกิจศึกษา ปี 2 เรียนกี่หน่วยกิต","curriculum":"IT","version":"old"}
```

`curriculum`: `AIT`, `DSBA`, `IT`, `BIT`; `version`: `latest`, `old`, `all versions` ตามตัวเลือกจริง AIT มีเฉพาะฉบับปัจจุบัน 2566 DSBA/IT/BIT ฉบับล่าสุด 2565/เก่า 2560 แผนระบุในคำถาม ค่า response ยึด [schemas.py](../lab10_fastapi/curriculum_app/schemas.py): `answer`, `sources`, `model`, `latency_ms` และ optional study-plan/metadata sources มี PDF page กับ printed page แยกกัน ไม่เดา folio หากยังไม่ตรวจ

`POST /api/ask` รับ `question` และคืน `question`, `sql`, `rows`, `answer` พร้อม metadata เดิม ไม่เปลี่ยน contract เพื่อให้ UI ทดสอบผ่าน Error ของ FastAPI มี `detail` ที่ renderer แสดงอย่างปลอดภัย

## สถานะที่ต้องตรวจ

- idle: ตัวเลือกและคำถามตัวอย่างพร้อมใช้
- loading: ปิด controls ป้องกัน submit ซ้ำ; Enter ไม่ submit ระหว่าง Thai IME
- success: คำตอบครบ, แยกแผน/track/alternatives, source links และ timing
- insufficient-evidence: แสดงชื่อฉบับที่ค้น ไม่สรุปว่าหนังสือไม่มีข้อมูล
- error: validation/network/backend/timeout มีวิธีแก้และ retry

คำตอบใช้ `textContent` และ source links allowlist ไม่มี key ใน frontend history อยู่เฉพาะ session ไม่ใช่ฐานข้อมูลคำตอบ breakpoint หลัก 1040px แสดง panels แบบซ้อนเพื่อให้ตารางอ่านได้; mobile ใช้ course labels ที่ไม่ถูกบีบ ดู [design decisions](../DESIGN.md) และ [wireframe](wireframe.md)
