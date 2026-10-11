# ชุดส่งอาจารย์ — instructor-v9

ใช้ [branch week11_thanapat](https://github.com/thanapat6954/isd-2026-cooltone/tree/week11_thanapat) หรือ [Release instructor-v9](https://github.com/thanapat6954/isd-2026-cooltone/releases/tag/instructor-v9) เลือกวิธีทดสอบด้านล่าง ชุดนี้รวมโค้ด hybrid และคู่มือสร้างใหม่แล้ว ไม่ต้อง overlay patch

## ไฟล์ที่ต้องดาวน์โหลด

| ไฟล์ | เนื้อหา |
|---|---|
| [curriculum-project.zip](https://github.com/thanapat6954/isd-2026-cooltone/releases/download/instructor-v9/curriculum-project.zip) | โค้ดและคู่มือ; ไม่รวม venv/model weights/ฐานข้อมูล |
| [runtime-data.zip](https://github.com/thanapat6954/isd-2026-cooltone/releases/download/instructor-v9/runtime-data.zip) | ฐานข้อมูล SQLite 14 snapshots และ PDF 7 เล่ม ประมาณ 1.24 GB |
| [handoff-manifest.json](https://github.com/thanapat6954/isd-2026-cooltone/releases/download/instructor-v9/handoff-manifest.json) | Commit, SHA256 และขอบเขตผลตรวจ |
| [VERIFICATION.md](https://github.com/thanapat6954/isd-2026-cooltone/releases/download/instructor-v9/VERIFICATION.md) | ผลซ้อมชุดส่งจริงและข้อจำกัด |

ถ้า clone branch แล้ว ไม่ต้องดาวน์โหลด code ZIP อีก ส่วน runtime-data.zip ต้องดาวน์โหลดจาก Release เพราะไฟล์ฐานข้อมูลและ PDF ไม่อยู่ใน Git

Runtime ZIP เป็นชุด snapshots เดิมที่ตรวจไว้ SHA256 `39018bfa21a7a36ea4f92fde8eb4db5d671745679dddc90dead38d8f23ec9f07` ไม่ได้อ้างว่าเป็นผล OCR ใหม่ของทุกเล่ม ส่วนโค้ด v9 ใช้สร้างแผนการศึกษาใหม่ได้ 13 profiles

## A — เปิดทดสอบ chatbot ทันที

ติดตั้ง Python 3.11, PowerShell 7 และ Ollama ก่อน ใช้โฟลเดอร์ใหม่ที่ว่าง เปิด PowerShell ในโฟลเดอร์ที่ดาวน์โหลด ZIP:

```powershell
Get-FileHash .\curriculum-project.zip -Algorithm SHA256
Get-FileHash .\runtime-data.zip -Algorithm SHA256
Expand-Archive .\curriculum-project.zip -DestinationPath .\curriculum-v9
Expand-Archive .\runtime-data.zip -DestinationPath .\curriculum-v9\supplied-artifacts
Set-Location -LiteralPath .\curriculum-v9\ocr_final
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-web-tested.txt
.\venv\Scripts\python.exe -m pip check
```

ตรวจ hashes ให้ตรง manifest ก่อนใช้ เปิดแอป Ollama แล้วเตรียม Qwen หากติดตั้งไว้แล้วไม่ต้องดาวน์โหลดซ้ำ:

```powershell
ollama list
ollama pull qwen3:4b
$env:CURRICULUM_OLLAMA_MODEL = 'qwen3:4b'
$env:CURRICULUM_OLLAMA_URL = 'http://127.0.0.1:11434'
.\venv\Scripts\python.exe scripts/runtime_bundle.py restore --bundle ../supplied-artifacts/runtime-data --app-root .
.\venv\Scripts\python.exe scripts/check_setup.py
.\scripts\start_web.ps1 -Port 8000
```

เปิด `http://127.0.0.1:8000/frontend/` ถ้า port ถูกใช้ให้เลือก port ว่างและเปิด URL ที่ launcher พิมพ์ เช่น `-Port 8005` ไม่ต้องรัน OCR ก่อน Mode A เลือกหลักสูตร/ฉบับ/แผนแล้วถามชื่อวิชา หน่วยกิต แผนการเรียน หรือข้อมูลที่มีหลักฐาน และเปิด citation ไปยังต้นฉบับ ข้อมูล prerequisite ที่ยังไม่ตรวจต้องตอบว่ายังไม่ทราบ

## B — สร้างใหม่จาก PDF โดยไม่ใช้ DB ที่ส่งให้

ทำในอีกโฟลเดอร์ใหม่ และใช้ code/maps v9 ครบชุด ทำตาม [คู่มือสร้างใหม่จาก PDF](../ocr_final/REBUILD_FROM_PDF.md) ซึ่งรวมติดตั้ง `requirements-rebuild.txt`, เตรียม OCR model และ restore เฉพาะต้นฉบับ:

```powershell
.\venv\Scripts\python.exe scripts/runtime_bundle.py restore --bundle ../supplied-artifacts/runtime-data --app-root . --sources-only --reuse-verified-pdfs
.\venv\Scripts\python.exe scripts/rebuild_from_pdf.py --activate
.\venv\Scripts\python.exe scripts/check_setup.py
.\scripts\start_web.ps1 -Port 8000
```

คำสั่ง default สร้างแผนการศึกษาครบ 13 profiles อ่าน native PDF ก่อนและใช้ image OCR เมื่อ native ถูกปฏิเสธ เก็บ staging/ผลดิบ ตรวจ source ก่อนเปิดใช้ และ backup ก่อนเปลี่ยน active set Health/UI ต้องระบุ `academic-plan-only` ถ้าสร้างไม่ผ่านจะเก็บ diagnostics และไม่เปิดใช้ข้อมูลที่ยังไม่ครบ

**Mode B ยังไม่เทียบเท่าข้อมูลทั้งชุดใน Mode A:** ไม่รองรับคำอธิบายรายวิชา prerequisites ข้อกำหนดหลักสูตร หรือ legacy จากการสร้างใหม่ รอบ source-only 13 profiles อ่าน native ได้ทั้งหมด จึงไม่ใช่ผล OCR ภาพทุกหน้า Source-only ต้องไม่ restore หรือใช้ DB snapshots เติมข้อมูลที่อ่านไม่ครบ

## หลักฐานและขอบเขต

ผล source-only ก่อนจัด v9: 13 profiles/source verification ผ่าน, API ตรวจหน่วยกิต 105/105 และชื่อ/หน่วยกิต 26/26 พร้อม paired PDF/book citations; image fallback DSBA PDF27 ตรวจหนึ่งหน้าได้ 6 แถว 18 หน่วยกิต ไม่ใช่ full-book OCR accuracy

Actual ZIP v9 ซ้อมแล้ว: environment ใหม่/restore14/startup/restart/70gold/52both-route+citation checks ผ่าน; unit400/schema30/frontend11 ผ่าน; สร้างจาก PDF-only ครบ13 profiles แล้วตรวจ105+26Q&A ผ่านใน274.940วินาทีสำหรับ build+verification+activation บนเครื่องนี้ ทั้ง13อ่าน native ได้ ไม่ใช้เวลานี้รับรอง OCR ภาพหรือเครื่องอาจารย์ ใช้ shared installed models โดยเปิดเผย ไม่มี model download หรือ OS installer rehearsal ใหม่

Regression ก่อนจัดชุดยังมี old2560 gold65/provenance14/version sets6 ผ่าน Read-only audit รอบ v9 ยังคง1372 findingsและ51 incomplete findings ส่วนใหญ่เป็นความครบของหลักฐาน/catalog/prerequisitesและlegacy identity จึงแยก startup success จาก full source accuracy ดู [ผลย่อ v9](public_results/instructor_v9/verification-summary.json), [รายงานแก้จาก PDF](PDF_REBUILD_REPAIR_20261011.md) และ release VERIFICATION ไม่อ้าง independent held-out ที่ยังไม่ได้ทดสอบ

หยุดด้วย `scripts/stop_web.ps1 -Port <port ที่เริ่ม>` ส่วนการ rollback อ่านจาก backup path ที่ activation พิมพ์ใน [README](../README.md#หยุด-เริ่มใหม่-และ-recovery) ไม่ลบ DB เก่าหรือหยุด Ollama/server ของโครงการอื่น
