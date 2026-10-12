# รัน Evaluation ด้วยไฟล์ PowerShell

ใช้โค้ดชุดไฟนอลบน main (นำจาก week11_thanapat) กับฐานข้อมูล 14 snapshots จาก runtime-data.zip (Mode A) ติดตั้ง Python venv/requirements-web-tested.txt, Node.js และเตรียม Ollama ตามคู่มือ INSTRUCTOR_V9.md ก่อน

เริ่มจาก ZIP ให้ทำตาม [คู่มือแตก ZIP และจัดโฟลเดอร์](https://github.com/thanapat6954/isd-2026-cooltone/blob/main/docs/INSTRUCTOR_ZIP_SETUP.md) (ไฟล์ docs/INSTRUCTOR_ZIP_SETUP.md ใน Code ZIP) มีเส้นทางก่อน/หลัง restore และแยก ZIP ของโค้ด ฐานข้อมูล และหลักฐานผลทดสอบ

ติดตั้ง dependency ของชุดทดสอบเพิ่มหนึ่งครั้งใน venv นี้:

```powershell
.\venv\Scripts\python.exe -m pip install -r .\requirements-evaluation-tested.txt
```

ตัวรันตรวจ TestClient ก่อนเริ่มชุดทดสอบ ถ้าขาด dependency จะแจ้งคำสั่งติดตั้งทันที

จากโฟลเดอร์ ocr_final รัน:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_evaluation.ps1
```

ไฟล์จะเปิด backend ของโฟลเดอร์นี้บน port 8026 ถ้า port ว่าง หากมี backend ที่ตรงกับโฟลเดอร์นี้อยู่แล้วจะใช้ตัวนั้น และหยุดเฉพาะ backend ที่ไฟล์เปิดเองหลังจบ ไม่หยุด Ollama

ไฟล์ค้นหา Node.js จาก PATH ปัจจุบัน, PATH ที่ตั้งไว้ใน Windows, ตำแหน่งติดตั้งทั่วไป และ runtime ของ Codex ที่มีอยู่ในเครื่องตามลำดับ แล้วเพิ่มตำแหน่งที่พบให้เฉพาะ process นี้และโปรแกรมลูก ไม่เปลี่ยน PATH ถาวร ไม่ต้องเปิด VS Code ใหม่ หากใช้ตำแหน่งอื่นระบุ executable ได้ด้วย `-NodePath 'C:\path\to\node.exe'` ต้องเป็น Node.js 18 ขึ้นไป

หากต้องการตรวจแค่ Node และการเปิด/หยุด backend ก่อนเริ่มชุดทดสอบ ให้เติม `-CheckOnly` โหมดนี้ไม่รัน Evaluation suites และไม่ถือว่า tests ผ่าน ไฟล์ PowerShell ที่มีข้อความไทยต้องบันทึกเป็น UTF-8 with BOM เพื่อรองรับ Windows PowerShell 5.1

ขณะทดสอบสคริปต์เขียน checkpoints ใน NEW TEMP เพื่อหลีกเลี่ยง WinError 5 ที่พบขณะ replace ไฟล์ใต้ OneDrive เมื่อทดสอบและหยุด backend เสร็จแล้ว จะคัดลอกทุกไฟล์แบบไม่แก้ผลไปไว้ใน **ocr_final/evaluation_runs/evaluation-วันเวลา-id/** โดยอัตโนมัติ แต่ละรอบเป็นโฟลเดอร์ใหม่ ไม่เขียนทับผลเก่า และเก็บรอบที่มี failures ด้วย

ท้ายคำสั่งแสดง `Results:` เป็นโฟลเดอร์หลักฐานในโครงการ, `Read:` เป็น REPORT.md และ `Send:` เป็น evaluation-evidence.zip เก็บ working results ใน TEMP ไว้ด้วย หากคัดลอกหลักฐานไม่สำเร็จจะรายงาน failure พร้อมตำแหน่งผลเดิม ไม่อ้างว่าเก็บสำเร็จ

```text
ocr_final/evaluation_runs/evaluation-วันเวลา-id/
├── REPORT.md                 สรุปผลจริง รวม failures/ข้อจำกัด
├── summary.json              คำสั่ง/scope/exit codes ของแต่ละชุด
├── health.json               app root/build/database set ที่ทดสอบ
├── checks/                   unit/schema/frontend/gold/old/provenance/version JSON + logs
├── metadata.json             คำถาม/คำตอบ/หลักฐานรายข้อ
├── graduation.json
├── counterfactual.json        disposable DB checks + production hash guard
├── audit/                    findings หากเลือก All
├── *.stdout.log, *.stderr.log
├── EVIDENCE_MANIFEST.json     รายการไฟล์ ขนาด SHA256 และ scope เดิม
├── EVIDENCE_README.md         อธิบายหลักฐานและการตรวจ
├── SHA256SUMS.txt             hash ของ ZIP และ manifest
└── evaluation-evidence.zip    ไฟล์ทั้งหมดสำหรับส่งอาจารย์ ไม่มี DB/PDF
```

ตรวจความตรงกันของไฟล์และ ZIP ได้ด้วย:

```powershell
.\venv\Scripts\python.exe scripts/archive_evaluation.py verify --evidence .\evaluation_runs\<ชื่อรอบจริง>
```

ส่ง ZIP ผลทดสอบพร้อม SHA256SUMS.txt หรือส่งทั้งโฟลเดอร์ให้อาจารย์ได้ JSON มีคำตอบและ citations จริงให้อ่าน ไม่ใช่เพียงตัวเลขในรายงาน Hash ตรวจว่าไฟล์ไม่เปลี่ยนหลังเก็บ ไม่ใช่การรับรองความถูกต้องทั้งเล่ม อาจารย์รันคำสั่งเดิมเพื่อสร้างหลักฐานรอบของตนเองได้

Git เก็บเฉพาะ [ตัวอย่างหลักฐานที่ระบุรอบ](https://github.com/thanapat6954/isd-2026-cooltone/blob/main/ocr_final/evaluation_evidence/README.md) ส่วน evaluation_runs ของผู้ใช้แต่ละเครื่องไม่ถูก commit อัตโนมัติ จำนวน Unit tests อาจต่างกันตามไฟล์ tests/เวอร์ชัน packages ในเครื่อง ให้ใช้ counts/command/dependency hashes ที่รอบนั้นบันทึกไว้

ถ้าต้องการรันเฉพาะชุดทดสอบพฤติกรรมระบบ (รวม Metadata, Graduation และ Counterfactual) ใช้:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_evaluation.ps1 -Suite Regression
```

Regression ไม่รัน source coverage audit จึงไม่ใช่การรับรองฐานข้อมูลทั้งเล่ม ใช้คำสั่งแรกเพื่อเก็บทุกชุด Audit ที่รันเสร็จแต่พบ findings จะแสดงจำนวน FAIL/incomplete แยกจากข้อผิดพลาดในการรัน และยังคง exit code ที่ไม่ผ่านไว้

เลือก port หรือโฟลเดอร์ผลใหม่ได้:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_evaluation.ps1 -Port 8027 -OutputDir C:\Temp\curriculum-results-01
```

OutputDir คือที่เขียนผลระหว่างรัน ต้องยังไม่มีอยู่ เพื่อรักษาผลเก่าไว้ ส่วน EvidenceDir คือโฟลเดอร์หลักฐานหลังรันจบ หากไม่ระบุจะเก็บใน evaluation_runs ของโครงการ หากต้องการกำหนดเอง เติม `-EvidenceDir 'C:\path\to\ocr_final\evaluation_runs\round-01'` และต้องยังไม่มีโฟลเดอร์นั้น หาก API/model/หน่วยความจำมีปัญหา ชุดหลักอาจหยุดก่อนครบ แต่ Metadata, Graduation และ Audit จะยังถูกเรียกและบันทึกสถานะแยกกัน ไม่ใส่คะแนนสำเร็จแทนชุดที่ไม่ครบ Exit code 1 หมายถึงมีชุดไม่ผ่านหรือยังไม่ได้ตรวจ อ่านผลในแฟ้มก่อนสรุป

Counterfactual ใช้สำเนา SQLite ชั่วคราว กำหนด database_root ก่อน lifespan เริ่ม และตรวจว่า production hashes ไม่เปลี่ยน ส่วน Graduation คงการตรวจ reference เดิม เพิ่มการตรวจทุกแถวของกฎเพิ่มเติมกับ source review ที่อนุมัติพร้อม hash ของ PDF UI ต้องตรวจผ่าน browser จริง และผล Graduation reference ไม่ใช่รับรองสิทธิ์จบ สคริปต์นี้ไม่ทำ OCR/rebuild/ซ่อม production DB หรือแก้เฉลย
