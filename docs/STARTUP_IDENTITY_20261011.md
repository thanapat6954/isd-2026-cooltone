# ตรวจ startup และโฟลเดอร์ที่ให้บริการจริง

## ขอบเขต

ทำงานบน `week11_thanapat` ไม่ commit/push/merge; รักษา edits เดิม ไม่หยุด server ที่มีอยู่ ไม่เปลี่ยนข้อเท็จจริงหรือเขียนทับ DB/PDF เดิม ใช้ runtime artifacts ที่เตรียมไว้ ไม่ใช้ evaluation labels ใน production

## ตัวตนของ process

| instance | โฟลเดอร์จริง | พอร์ต | listener PID / parent | readiness |
| --- | --- | --- | --- | --- |
| LIVE | `C:/Users/thana/OneDrive/เอกสาร/ocr_final` | 8000 | 33436 / 18248 | health ระบุ LIVE,14 DB,modelready=true |
| LIVE ที่ชนกับ launcher ส่งงาน | `C:/Users/thana/OneDrive/เอกสาร/ocr_final` | 8003 | 33952 / 35636 | health ระบุ LIVE,14 DB,modelready=true |
| LIVE อีก instance เดิม | `C:/Users/thana/OneDrive/เอกสาร/ocr_final` | 8010 | 5076 / 24100 | health ระบุ LIVE,14 DB,modelready=true |
| ส่งงานใน repository เริ่มใหม่รอบนี้ | `C:/Users/thana/OneDrive/เอกสาร/isd-2026-cooltone/ocr_final` | 8004 | 29032 / 13344 | health ระบุ repository app,14 DB,modelready=true |

8003 command line ของ listener: `"C:\Users\thana\AppData\Local\Python\pythoncore-3.11-64\python.exe" -m uvicorn lab10_fastapi.curriculum_app.main:app --host 127.0.0.1 --port 8003` ตัวเปิด35636ใช้ `C:/Users/thana/OneDrive/เอกสาร/ocr_final/venv/Scripts/python.exe` จึงต้องพิจารณา parent และ health ร่วมกัน ไม่ดู executable ของ listener อย่างเดียว

8004 listener command line ใช้ system Python เหมือนกันแต่ `--port 8004`; parent13344ใช้ `C:/Users/thana/OneDrive/เอกสาร/isd-2026-cooltone/ocr_final/venv/Scripts/python.exe` launcherกำหนด working directory เป็น repository app และ health `lab8b_module` เป็น `C:/Users/thana/OneDrive/เอกสาร/isd-2026-cooltone/ocr_final/scr/ocr_system/lab8b_curriculum_db.py` รายการ PID/command/health เต็มเก็บใน [raw JSON](results/startup_identity_20261011/result.json)

จาก repository app ทดลอง `scripts/start_web.ps1 -Port 8003` exit1: `Port 8003 is occupied; readiness check failed: A different application folder is serving this port.. No process was stopped.` ไม่ใช่ DB/model failure และไม่ควรฆ่า server เดิมโดยเดา

## เตรียมและเริ่มโฟลเดอร์ส่งงาน

preflightก่อนเริ่ม: ready=false,ไม่มี queryableDBs,ขาดAI.pdf (dependenciesพร้อมและโมเดลจากserviceเดิมพร้อม) แก้ด้วย `venv/Scripts/python.exe scripts/runtime_bundle.py restore --bundle ../delivery/runtime-data-20261011 --app-root . --reuse-verified-pdfs`: เพิ่ม14DB/1PDF ใช้6PDFเดิมที่hashตรง; no overwrite. `test_runtime_bundle` 5testsผ่าน รวม matching-PDF reuse/default refusal/hash-mismatch refusal/existingDB refusal. preflightหลังrestore ready=true,14profiles,missingDB/PDF0,changedPDF0,invalidDB0

`scripts/start_web.ps1 -Port 8004` exit0 และพิมพ์ `Backend ready: http://127.0.0.1:8004/frontend/` ก่อนหน้านี้8004ไม่มีlistener Logs: `ocr_final/work/web/backend-25691011-032404-417.stderr.log` Ownership record `ocr_final/work/web/process-8004.json` มี PID29032/startticks639272606444843058 รักษา instance นี้ไว้สำหรับผู้ใช้ ไม่ใช้ข้อมูลPIDเก่าหยุด process ครั้งถัดไป

## คำตอบจริงและหน้าอ้างอิง

| คำถามจริง | route | คำตอบจริง | HTTP / ms | หน้าอ้างอิงที่ตรวจภาพ |
| --- | --- | --- | --- | --- |
| IT พ.ศ.2560 แผนไม่สหกิจศึกษา หลักสูตรนี้มีกี่ปี | /api/ask | IT-2560-no-coop: 4 ปี (ที่มา: IT-60.pdf หน้า 6) | 200 / 463.42 | PDF6 / หน้าเล่ม1 |
| คำถาม IT เดียวกัน | /ask | IT-2560-no-coop: 4 ปี (ที่มา: IT-60.pdf หน้า 6) | 200 / 438.37 | PDF6 / หน้าเล่ม1 |
| BIT พ.ศ.2565 แผนไม่สหกิจศึกษา วิชารหัส 06036123 ชื่ออะไรและมีกี่หน่วยกิต | /api/ask | BIT-2565-no-coop: 06036123 เทคโนโลยีกลุ่มเมฆ (CLOUD TECHNOLOGY), 3 หน่วยกิต, L-P-S 3-0-6 (ที่มา: BIT-65.pdf หน้า 28) | 200 / 749.48 | PDF28 / หน้าเล่ม23 |
| คำถาม BIT เดียวกัน | /ask | คำตอบเหมือน route /api/ask ตาม raw JSON | 200 / 432.54 | PDF28 / หน้าเล่ม23 |

ตรวจภาพจาก `/api/source-page` ของ8004จริง: [IT6](results/startup_identity_20261011/IT-60.pdf-6.png) แสดงหลักสูตรปรับปรุง2560,หน้าเล่ม1,ข้อ5.1หลักสูตรปริญญาตรี4ปี; [BIT28](results/startup_identity_20261011/BIT-65.pdf-28.png) หน้าเล่ม23 แสดง06036123/ชื่อไทยและอังกฤษ/3(3-0-6). `/api/source-info` ตรงbook_pageทั้ง2รายการ; SQL/rows/คำตอบ/source SHAและruntimehashเก็บในrawJSON DBhashหลังทดสอบตรงก่อนทดสอบทั้งหมด ไม่ใช่source verificationครบทุกหลักสูตร

การตรวจ source fidelity รอบนี้จำกัด claims ข้างต้น ภาพ IT6รองรับระยะเวลาที่ใช้ทั้งหลักสูตร ไม่ได้ใช้หน้านี้พิสูจน์ความต่างระหว่างแผน BIT28เป็นหลักฐานชื่อ/credits ไม่ใช่graduation eligibility

## ข้อจำกัดและการแก้ข้อความกล่าวอ้าง

- คำตอบก่อนหน้าที่ว่า8000ทำงาน ยืนยัน LIVE readiness ณเวลานั้นเท่านั้น ไม่ยืนยันrepositoryหรือhandofffolderเริ่มได้ ข้อความว่า8003ไม่มีlistenerเป็นผลตรวจเก่า; ปัจจุบันมีLIVE listener33952แล้ว
- ผล fresh-copy/actual-ZIP ก่อนหน้าเป็นคนละโฟลเดอร์และprocess ไม่ถูกนำมานับเป็นผลของ8004 ผลเก่ายังเก็บไว้ตามเดิม
- รอบนี้ใช้venvที่มีอยู่และOllama11434เดิม ไม่ใช่fresh-first-machine installation ไม่ใช่real-LLM generation/latency benchmark คำตอบ4requestsเป็น structured paths/2uniquequestions
- frontendHTTP200/serverPNGและการตรวจภาพไม่ใช่visible browser/citation-click pass; browser actionยังblocked ไม่ bypass ไม่กล่าวอ้างUIใหม่
- ตัวเก็บprocessครั้งแรกมีcp874 UnicodeDecodeError จึงเก็บprocessใหม่ด้วยUTF8โดยไม่ยิงคำถามซ้ำ `--refresh-process-identity` มีบันทึกในrawJSON; API/citationผลเดิมรักษาไว้ ไม่ใช้การ rerun เพิ่ม n
- local handoffZIPv3เดิมยังเป็นsnapshotก่อนแก้docs/helperรอบนี้ ไม่ได้repackageหรือpublishอัตโนมัติ

## รันซ้ำและหยุด

จากrepository app: `venv/Scripts/python.exe scripts/verify_startup_identity.py --app-root . --port 8004 --output ../docs/results/<NEW-directory>` ใช้outputใหม่ ตรวจrootก่อนAPIทุกครั้ง; เก็บคำถามdevelopmentไม่ใช่held-out. ตรวจสถานะด้วย `/api/health` และprocess ownership record; หยุดเฉพาะowned8004ด้วย `scripts/stop_web.ps1 -Port 8004` บริการ8000/8003/8010/11434เดิมไม่ถูกหยุด
