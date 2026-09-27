# Lab 10 — FastAPI Curriculum Assistant

เว็บสำหรับถามข้อมูลหลักสูตร โดยใช้ Qwen ผ่าน Ollama แปลงคำถามเป็น SQL อ่านข้อมูลจาก SQLite และสรุปคำตอบเป็นภาษาไทย

## สิ่งที่อยู่ใน repository

```text
lab10_fastapi_github/
├── lab10_fastapi/
│   ├── __init__.py
│   └── curriculum_app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── model_service.py
│       ├── schemas.py
│       ├── .env.example
│       └── static/index.html
├── work/
│   ├── lab8b_ai/curriculum.db
│   ├── lab8b_dsba_coop/curriculum.db
│   ├── lab8b_dsba_no_coop/curriculum.db
│   ├── lab8b_it_coop/curriculum.db
│   └── lab8b_it_no_coop/curriculum.db
├── .gitignore
├── requirements.txt
└── README.md
```

ไฟล์ผลประเมิน ไฟล์ประมวลผลระหว่างทาง virtual environment และข้อมูลที่ซ้ำกันไม่ได้รวมไว้ เพราะไม่จำเป็นต่อการรันเว็บ

## วิธีติดตั้งบน Windows PowerShell

เปิด Terminal ที่โฟลเดอร์ repository แล้วรัน:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item lab10_fastapi\curriculum_app\.env.example lab10_fastapi\curriculum_app\.env
```

ติดตั้งและเปิด Ollama จากนั้นดาวน์โหลดโมเดล:

```powershell
ollama pull qwen3:4b
```

## วิธีรัน

```powershell
python -m uvicorn lab10_fastapi.curriculum_app.main:app --reload --host 127.0.0.1 --port 8000
```

เปิดใช้งานที่:

- หน้าเว็บ: http://127.0.0.1:8000/
- API documentation: http://127.0.0.1:8000/docs
- ตรวจสถานะ: http://127.0.0.1:8000/api/health

## การตั้งค่า

ค่าตัวอย่างอยู่ใน `lab10_fastapi/curriculum_app/.env.example` โดยค่าเริ่มต้นจะค้นหาฐานข้อมูลทุกไฟล์ใต้โฟลเดอร์ `work/`

```dotenv
CURRICULUM_APP_NAME=Curriculum Book Assistant
CURRICULUM_DB_PATH=work
CURRICULUM_OLLAMA_URL=http://127.0.0.1:11434
CURRICULUM_OLLAMA_MODEL=qwen3:4b
CURRICULUM_REQUEST_TIMEOUT=180
CURRICULUM_MAX_ROWS=100
```

ไฟล์ `.env` ถูกกำหนดไว้ใน `.gitignore` จึงไม่ถูกอัปโหลดขึ้น GitHub

## อัปโหลดขึ้น GitHub

สร้าง repository เปล่าบน GitHub ก่อน แล้วรันคำสั่งต่อไปนี้จากโฟลเดอร์นี้ โดยเปลี่ยน URL ให้เป็น repository ของตนเอง:

```powershell
git init
git add .
git commit -m "Add FastAPI curriculum assistant"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```
