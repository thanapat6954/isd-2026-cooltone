# แตก ZIP จัดโฟลเดอร์ และรันทดสอบบนเครื่องอาจารย์

ตัวอย่างนี้ใช้โฟลเดอร์ใหม่ **C:\CurriculumDemo** ซึ่งอยู่นอก OneDrive ใช้ Windows PowerShell 5.1 ได้ หากเลือกตำแหน่งอื่น ให้เปลี่ยนค่า demoRoot ในคำสั่ง โค้ด ฐานข้อมูล และผลทดสอบอยู่ใต้โครงการเดียวกันหลังทำครบ

## 1. ดาวน์โหลด ZIP สองไฟล์สำหรับเปิดระบบ

| ZIP | ดาวน์โหลด | หน้าที่ |
|---|---|---|
| isd-2026-cooltone-week11_thanapat.zip | [โค้ดล่าสุด branch week11_thanapat](https://github.com/thanapat6954/isd-2026-cooltone/archive/refs/heads/week11_thanapat.zip) หรือ GitHub → Code → Download ZIP | โค้ด คู่มือ tests และตัวอย่างหลักฐาน Evaluation ที่บันทึกไว้ |
| runtime-data.zip | [ฐานข้อมูลจาก instructor-v9](https://github.com/thanapat6954/isd-2026-cooltone/releases/download/instructor-v9/runtime-data.zip) | SQLite 14 snapshots + PDF ต้นฉบับ 7 เล่ม; ประมาณ 1.24 GB |

โค้ด Evaluation ที่ปรับใหม่อยู่ใน branch week11_thanapat ให้ใช้ Code ZIP ลิงก์ข้างบน คู่มือ/โค้ดภายใน curriculum-project.zip ของ release v9 เป็น snapshot ก่อนเพิ่มตัวรันเก็บหลักฐานนี้ ส่วน runtime-data.zip ใช้ไฟล์เดิมได้เพราะรอบนี้ไม่ได้แก้ DB/PDF

ZIP ผลทดสอบ evaluation-evidence.zip เป็นไฟล์ที่สร้าง **หลังทดสอบ** สำหรับอ่าน/ส่งหลักฐาน ไม่ใช้แทน Code ZIP หรือ runtime-data.zip

## 2. แตกโค้ดก่อน แล้วแตก runtime ZIP ใต้โครงการ

เก็บ ZIP ที่ดาวน์โหลดทั้งสองไฟล์ไว้ใน Downloads เปิด PowerShell แล้วรันทีละบรรทัด ถ้าไฟล์ดาวน์โหลดอยู่ที่อื่น ให้เปลี่ยน zipFolder:

```powershell
$zipFolder = "$env:USERPROFILE\Downloads"
$demoRoot = 'C:\CurriculumDemo'
Expand-Archive -LiteralPath "$zipFolder\isd-2026-cooltone-week11_thanapat.zip" -DestinationPath $demoRoot
$projectRoot = Join-Path $demoRoot 'isd-2026-cooltone-week11_thanapat'
Expand-Archive -LiteralPath "$zipFolder\runtime-data.zip" -DestinationPath (Join-Path $projectRoot 'supplied-artifacts')
Set-Location -LiteralPath (Join-Path $projectRoot 'ocr_final')
```

เลือก demoRoot ใหม่ที่ยังไม่มีโครงการเก่า เพื่อไม่เขียนทับงานหรือฐานข้อมูลเดิม หากแตกด้วย File Explorer ให้ได้โครงสร้างเดียวกับด้านล่าง ตรวจว่ามี manifest.json ตรง **supplied-artifacts\runtime-data\manifest.json** อย่าแตก runtime ZIP ซ้อนเป็น runtime-data\runtime-data และอย่าวาง DB ทั้งหมดรวมไว้ในโฟลเดอร์เดียว

หลังแตก ZIP แต่ก่อน restore:

```text
C:\CurriculumDemo\
└── isd-2026-cooltone-week11_thanapat\    projectRoot
    ├── README.md
    ├── docs\INSTRUCTOR_ZIP_SETUP.md
    ├── supplied-artifacts\
    │   └── runtime-data\
    │       ├── manifest.json
    │       ├── build-lineage.json
    │       ├── data\input\             PDF ที่บรรจุมา
    │       ├── curriculum.db            legacy snapshot
    │       └── work\lab8b_*\           snapshots แยกหลักสูตร/ฉบับ/แผน
    └── ocr_final\                      เปิด PowerShell ที่นี่เพื่อรัน
        ├── scripts\
        ├── frontend\
        ├── lab10_fastapi\
        ├── tests\
        └── evaluation_evidence\        ตัวอย่างผลเดิมที่ระบุ scope
```

ตรวจตำแหน่งก่อนทำต่อ:

```powershell
Get-Location
Test-Path .\scripts\runtime_bundle.py
Test-Path ..\supplied-artifacts\runtime-data\manifest.json
```

สอง Test-Path ต้องเป็น True หาก False ให้แก้ตำแหน่งที่แตกหรือ Set-Location ก่อนติดตั้ง/restore

## 3. สร้าง venv ติดตั้ง packages และเตรียมบริการ

ติดตั้ง Python 3.11, Node.js สำหรับ frontend tests และ Ollama ก่อน จาก ocr_final รัน:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r .\requirements-web-tested.txt
.\venv\Scripts\python.exe -m pip install -r .\requirements-evaluation-tested.txt
.\venv\Scripts\python.exe -m pip check
node --version
```

ตัวรันรองรับ Node.js 18 ขึ้นไปและทดสอบ Node.js 24.19.0 ถ้ามี Node ในเครื่องแต่ PATH เก่ายังไม่พบ ตัวรันจะลอง PATH ที่ตั้งใน Windows และตำแหน่งติดตั้งทั่วไปด้วย หรือกำหนด -NodePath เป็น executable จริง ไม่จำเป็นต้อง activate venv เพราะคำสั่งใช้ python.exe ของโครงการโดยตรง

เปิด Ollama และเตรียม model สำหรับตอบ:

```powershell
ollama list
ollama pull qwen3:4b
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

ถ้ามี qwen3:4b อยู่แล้ว ไม่ต้อง pull ซ้ำ Mode A ใช้ DB ที่ส่งให้ ไม่รัน OCR และไม่ต้องดาวน์โหลด OCR model

## 4. Restore DB/PDF ไปยังตำแหน่งที่แอปใช้

ยังอยู่ใน ocr_final รัน:

```powershell
.\venv\Scripts\python.exe scripts/runtime_bundle.py restore --bundle ..\supplied-artifacts\runtime-data --app-root .
.\venv\Scripts\python.exe scripts/check_setup.py
```

Restore ตรวจ manifest, hashes และ SQLite integrity ก่อนวางไฟล์ และไม่เขียนทับ DB เดิม หากรัน restore แล้วมี DB อยู่ ให้ใช้สำเนาโครงการใหม่เพื่อเริ่มใหม่ ไม่ลบ DB เก่าเป็นทางลัด

หลัง restore ต้องมี:

```text
ocr_final\
├── venv\Scripts\python.exe
├── curriculum.db                        legacy
├── data\input\
│   ├── AI.pdf
│   ├── DSBA.pdf
│   ├── DSBA-60.pdf
│   ├── IT.pdf
│   ├── IT-60.pdf
│   ├── BIT-65.pdf
│   └── BIT-60.pdf
├── work\lab8b_*\curriculum.db          อีก 13 profiles ตาม manifest
├── scripts\run_evaluation.ps1
└── evaluation_evidence\                ตัวอย่างหลักฐานเดิม
```

ในผล check_setup ต้องมี ready: true, missing_profile_databases: [], missing_source_pdfs: [], invalid_databases: [] และ model_installed_and_service_ready: true หากยังไม่พร้อมให้อ่านรายการที่ขาด ไม่ใช้รายงานตัวอย่างแทนผลเครื่องนี้

## 5. รัน Evaluation และดูหลักฐานของเครื่องนี้

รันทุกชุด รวม read-only Audit:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_evaluation.ps1
```

หรือรันเฉพาะ Regression (ชุดทดสอบระบบ รวม Metadata/Graduation/Counterfactual):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_evaluation.ps1 -Suite Regression
```

ตัวรันเปิด backend บน port 8026 เมื่อว่างและหยุดเฉพาะ backend ที่เปิดเอง หาก port มีโปรแกรมอื่นใช้ เลือก port ว่างด้วย -Port 8029 การทดสอบเขียน checkpoints ชั่วคราวใน TEMP และเมื่อจบคัดลอกผลจริงทั้งหมดมาเก็บในโครงการโดยไม่แก้คะแนน คำตอบ หรือ failures

```text
ocr_final\evaluation_runs\evaluation-วันเวลา-id\
├── REPORT.md                    อ่านสรุป
├── summary.json                 scope/คำสั่ง/exit code
├── health.json                  app/database set ที่รัน
├── checks\                     ผลรายคำถาม + stdout/stderr ของชุดหลัก
├── metadata.json
├── graduation.json
├── counterfactual.json
├── audit\                      findings ถ้าเลือก All
├── *.stdout.log, *.stderr.log
├── EVIDENCE_MANIFEST.json        file sizes/hashes + scope/job status เดิม
├── EVIDENCE_README.md
├── SHA256SUMS.txt
└── evaluation-evidence.zip       ส่งหลักฐานผลทดสอบ
```

ท้ายคำสั่งแสดง Results/Read/Send เป็นเส้นทางจริงของรอบนั้น ทุกครั้งได้โฟลเดอร์ใหม่ ไม่เขียนทับตัวอย่างหรือผลเก่า ตัวรันไม่ commit/push ผลของอาจารย์เอง

All อาจ exit1 เพราะ Audit พบปัญหา legacy/source coverage แม้ Regression ผ่านครบ ต้องอ่าน summary และ findings ผลที่ผู้พัฒนาบันทึก 2026-10-12 มี Audit FAIL1372/incomplete4881; ไม่ใช่ 1372 คำตอบแชตผิด ไม่ทำเครื่องหมายข้อมูลครบเพื่อให้รายงานเขียว รายละเอียดอยู่ [คู่มือ Evaluation](../ocr_final/RUN_EVALUATION.md)

## 6. แตก ZIP ผลทดสอบเพื่ออ่านและตรวจ

evaluation-evidence.zip ภายในรอบนั้นมีไฟล์ผลที่ root ของ ZIP หากส่งให้คนอื่น ให้ส่ง ZIP พร้อม SHA256SUMS.txt แตก ZIP ลง **โฟลเดอร์ใหม่ของรอบนั้น** เช่น:

```powershell
Expand-Archive -LiteralPath 'C:\path\to\evaluation-evidence.zip' -DestinationPath 'C:\CurriculumEvidence\round-01'
Copy-Item -LiteralPath 'C:\path\to\evaluation-evidence.zip','C:\path\to\SHA256SUMS.txt' -Destination 'C:\CurriculumEvidence\round-01'
.\venv\Scripts\python.exe scripts/archive_evaluation.py verify --evidence 'C:\CurriculumEvidence\round-01'
```

คำสั่ง verify ตรวจทุก raw file, manifest checksum, ZIP checksum, ZIP inventory/CRC และ hash ทุก entry ให้ตรงกับไฟล์ที่บันทึกไว้ อ่าน REPORT.md กับ JSON/logs ในโฟลเดอร์ที่แตกได้เลย SHA256 ยืนยันความตรงกันของไฟล์ ไม่ได้ยืนยัน facts ทั้งเล่ม การสร้างหลักฐานใหม่ให้ทำขั้นตอน 5 บนเครื่องอาจารย์

## 7. ถ้าต้องการเริ่มจาก PDF ใหม่

ขั้นตอนข้างบนคือ Mode A ทดสอบ DB ที่ส่งให้ หากทดสอบ reconstruction ให้ใช้ [REBUILD_FROM_PDF.md](../ocr_final/REBUILD_FROM_PDF.md) แยกต่างหาก: restore --sources-only → hybrid rebuild → source validation → scoped activation ผลที่รองรับเป็น 13 academic plans ไม่ใช่ full catalog/prerequisites/rules/legacy และไม่ใช่ vision OCR ทุกหน้า ห้ามนำคะแนน Regression ของ DB เดิมไปอ้างเป็นคะแนน DB ที่สร้างใหม่
