# แอปผู้ช่วยค้นข้อมูลหลักสูตร

แอปนี้รับคำถามภาษาธรรมชาติ ตรวจหาเจตนาและหลักสูตรที่เกี่ยวข้อง ค้น `curriculum.db` ที่มีอยู่จริง ตรวจ schema ของแต่ละฐานข้อมูล สร้างและตรวจ SQL แบบ read-only แล้วให้ Qwen สรุปผลจาก rows ที่ค้นได้

## โครงสร้างที่ต้องมี

วาง `lab10_fastapi/` ไว้ที่รากโปรเจกต์เดียวกับ `scr/` และ `work/`:

```text
ocr_final/
├── lab10_fastapi/
│   └── curriculum_app/
├── scr/ocr_system/
│   └── lab8b_curriculum_db.py
└── work/
    ├── lab8b_ai/curriculum.db
    ├── lab8b_dsba_coop/curriculum.db
    ├── lab8b_dsba_no_coop/curriculum.db
    ├── lab8b_it_coop/curriculum.db
    └── lab8b_it_no_coop/curriculum.db
```

ระบบค้นทุกไฟล์ชื่อ `curriculum.db` ภายใต้รากที่กำหนดด้วย `CURRICULUM_DATABASE_ROOT` จึงไม่ต้องกำหนด path ของฐานข้อมูลทีละไฟล์

โฟลเดอร์ที่ชื่อขึ้นต้นด้วย `_archive` จะปรากฏในหน้าตรวจสอบ แต่จะไม่ถูกใช้ตอบคำถาม เพื่อไม่ให้ผลจากฐานข้อมูลรุ่นเก่าซ้ำกับฐานข้อมูลปัจจุบัน

## วิธีติดตั้งและรัน

รันจากรากโปรเจกต์ `ocr_final`:

```bash
python -m pip install -r lab10_fastapi/curriculum_app/requirements.txt
ollama pull qwen3:4b
python -m uvicorn lab10_fastapi.curriculum_app.main:app --reload --host 127.0.0.1 --port 8000
```

เปิดหน้าใช้งานที่ <http://127.0.0.1:8000/> หรือ Swagger UI ที่ <http://127.0.0.1:8000/docs>

endpoint สำหรับตรวจสถานะ:

- `/api/health` แสดงสถานะ Ollama และฐานข้อมูลทั้งหมดที่ค้นพบ
- `/api/databases` แสดง path, หลักสูตร, สถานะใช้งาน และ schema จริงของแต่ละฐานข้อมูล

## ลำดับการตอบคำถาม

1. ตรวจ intent เช่น หน่วยกิตรวม หน่วยกิตรายปี รายเทอม จำนวนวิชา รายวิชา หรือวิชาบังคับก่อน
2. เลือกฐานข้อมูลจากคำว่า `AI`, `IT`, `DSBA`, `coop`, `no-coop`, `สหกิจ` หรือ `ไม่สหกิจ`
3. หากไม่ได้ระบุหลักสูตร ระบบค้นหลักสูตรที่เกี่ยวข้องทุกฐานและเก็บผลแยกตามแหล่งที่มา
4. ใช้ SQL ที่กำหนดด้วยกฎเมื่อคำถามชัดเจน และใช้ Qwen สร้าง SQL เฉพาะกรณีที่กฎยังครอบคลุมไม่ได้
5. ตรวจ SQL กับ schema จริงด้วย SQLite ก่อนรัน และอนุญาตเฉพาะ `SELECT` หรือ `WITH`
6. หาก SQL ที่ Qwen สร้างผิด ระบบส่ง error พร้อม schema จริงกลับให้ Qwen ซ่อมได้ไม่เกินจำนวนครั้งที่กำหนด
7. เปิดฐานข้อมูลแบบ read-only ใส่ metadata ของฐานข้อมูลในทุกผลลัพธ์ แล้วให้ Qwen สรุปโดยห้ามรวมยอดข้ามหลักสูตร

## การตั้งค่า

แก้ `lab10_fastapi/curriculum_app/.env`:

```dotenv
CURRICULUM_DATABASE_ROOT=.
CURRICULUM_OLLAMA_URL=http://127.0.0.1:11434
CURRICULUM_OLLAMA_MODEL=qwen3:4b
CURRICULUM_SQL_REPAIR_ATTEMPTS=2
CURRICULUM_DEBUG=true
```

เมื่อ `CURRICULUM_DEBUG=true` คำตอบจาก `/api/ask` จะแสดง intent, ฐานข้อมูลที่ค้นพบและเลือก, schema ที่ใช้, SQL, ผล validation, rows, การซ่อม SQL และ context ที่ส่งให้ Qwen

## การทดสอบ

```bash
python -m unittest tests.test_lab10_multi_database -v
```

ชุดทดสอบครอบคลุมคำถามรายเทอม หน่วยกิตรวม IT จำนวนวิชา รายวิชาตามปีและเทอม การเลือก AI การซ่อม column ที่ไม่มีจริง การค้นหลายฐานข้อมูล และฐานข้อมูลที่มี schema ต่างกัน

## ปัญหาที่พบบ่อย

### เปิดเว็บแล้วขึ้น `ERR_CONNECTION_REFUSED`

FastAPI ยังไม่ได้รัน ให้รันคำสั่ง Uvicorn ด้านบนและเปิด Terminal ค้างไว้

### ขึ้น `No module named fastapi`

ยังไม่ได้ activate venv หรือยังไม่ได้ติดตั้ง `requirements.txt`

### ไม่พบฐานข้อมูล

ตรวจค่า `CURRICULUM_DATABASE_ROOT` และเรียก `/api/databases` เพื่อดูว่าแอปค้นพบไฟล์ใดบ้าง

### เปิดหน้าเว็บได้แต่ถามไม่ได้

เรียก `/api/health` แล้วตรวจว่า `queryable_database_count` มากกว่า `0` และ `ollama_ready` เป็น `true`
