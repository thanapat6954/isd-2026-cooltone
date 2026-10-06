# ผลตรวจ README และการเปิดระบบ — 2026-10-07

## ขอบเขต

แก้ `README.md` ที่ repository root โดยตรง ใช้ branch `week11_thanapat` ไม่มี commit/push/PR/merge ไม่แก้ main หรือ historical `ocr_system/` งานก่อนหน้าและข้อมูลต้นฉบับคงไว้ ใช้ current uncommitted application code ไม่ใช่ checkout เก่าบน GitHub

เพิ่มคู่มือติดตั้งและเปิดหลัง restart อย่างละ10ขั้นตอน อธิบายหน้าที่โฟลเดอร์/คำสั่ง/config/data และใช้ banner/badges SVG เดิม รายงานผลก่อนหน้าตาม scope เดิม ไม่ตีความ regression เป็น independent accuracy

## ผลสังเกต

| การตรวจ | ผล | หลักฐาน |
|---|---|---|
| runtime dependencies | pip exit0; ใช้ environment ที่มีแล้ว | [startup](final/startup.json) |
| runtime bundle restore | 14 DB; source PDF 7; exit0 | [startup](final/startup.json) |
| preflight/start ครั้งแรก | exit0; ready=true; คำตอบตัวอย่างผ่าน | [preflight](final/first_preflight.json), [startup](final/startup.json) |
| หยุด backend/model ของการทดสอบแล้วเปิดใหม่ | stop/preflight/start exit0; คำตอบตัวอย่างผ่าน | [startup](final/startup.json) |
| UI จริง | เลือก IT/2560; ถามแผนไม่สหกิจศึกษา; แสดง4ปี, PDF6/หน้า1ในเล่ม; console errors/warnings=[] | [UI raw](startup_ui.json), [ภาพ](startup_ui.png) |
| citation transport | 7/7 PDF routes มี Range206 และ %PDF | [handoff](handoff.json) |
| documentation links | ตรวจ Markdown และ HTML src/href ภายใน repository | [handoff](handoff.json) |
| local GFM preview | 3ภาพโหลดได้; สารบัญไม่มี anchor ขาด | [preview raw](preview.json), [ภาพ](readme_preview.png) |
| focused tests | 12/12 ผ่านใน isolated app ที่มี DB; ไม่มี skipped | [raw output](focused_tests.log) |

backend ทดสอบใช้8001, Ollama process แยก11435, preview8002 จึงไม่รบกวน live8000/บริการโมเดลเดิม11434 โฟลเดอร์ทดสอบมีช่องว่างใน path; ข้อมูลมาจาก runtime snapshot/hardlinks ของ PDF ไม่แก้ DB production ไม่ทำ OCR ซ้ำเพื่อเปิดเว็บ

ตรวจเสร็จหยุดเฉพาะบริการชั่วคราวและปิดtabที่เปิดทดสอบแล้ว live8000 PID28104/Ollama11434 PID19364ยังอยู่ ดู [cleanup](cleanup.txt)

## ปัญหาที่พบและแก้

attemptแรก backendพร้อมแล้วแต่ helper ค้างจาก inherited output pipe ของ Windows detached child ไม่ใช่คำตอบผิด เก็บ [attemptแรก](startup.json) ไว้ แก้ `verify_readme_setup.py` ให้บันทึก stdout/stderr ลงไฟล์แล้ว rerun ในโฟลเดอร์แยกใหม่ สำเร็จ exit0

ปรับ evidence output เป็น absolute ก่อน child เปลี่ยน cwd เพื่อให้ preflight JSON อยู่กับรายงาน ไม่กระจายใต้ temp; final rehearsal หลังแก้ผ่าน exit0 ทั้งfirst/restart UI/focused tests จาก retry ใช้ app source/DB/model dependencies เดียวกัน ไม่แก้ factual answering ระหว่างสองรอบ

ปรับ `start_web.ps1` ให้ error เมื่อไม่มีvenvแนะนำ dependencies ที่ใช้เปิดเว็บจริง; `verify_handoff_runtime.py` ตรวจ HTML asset links เพิ่ม เติมขั้นตอนเปิด Ollama ก่อน `ollama pull` ใน README ไม่เปลี่ยน API หรือ factual retrieval

## รันซ้ำ

จาก `ocr_final/` ใช้ venv Python:

```powershell
.\venv\Scripts\python.exe scripts/verify_handoff_runtime.py --repository .. --url http://127.0.0.1:8000 --output ../docs/results/readme_verification/handoff.json
.\venv\Scripts\python.exe -m unittest tests.test_web_routing tests.test_week11_handoff -v
```

`verify_readme_setup.py --help` อธิบาย source-app/workspace/venv-source/bundle/pdf-folder/output ใช้โฟลเดอร์ใหม่และพอร์ต8001/11435ที่ว่าง ไม่หยุด process อื่นเอง หลังสำเร็จยังเปิด services ไว้เพื่อตรวจ browser ผู้รันต้องหยุดเฉพาะ process ของ rehearsal ตาม PID/start ticks ที่บันทึก ส่วน `preview_readme.mjs` เป็นเครื่องมือตรวจเอกสารแบบ local ใช้ marked ที่มีอยู่แล้ว ไม่ใช่ runtime dependency ของแอป

## ยังไม่ยืนยัน

ส่วน manual fallback ที่ระบุเป็นข้อจำกัดด้านล่างเป็นสถานะของรอบนี้ ภายหลังมี [ผลตรวจเพิ่มเติม](../readme_followup/REPORT.md): manual startup/browser/Ctrl+C shutdown และalternate-port guard/start/เปิดซ้ำ/stopผ่านแล้ว ข้อจำกัดfresh download/full OCR/OSอื่นยังคงเดิม

- initial downloads, full OCR dependency installation/rebuild, minimum hardware, Linux/macOS และ manual fallback แบบ foreground ไม่ได้รันใหม่ทั้งหมด
- reuse venv/model files; ไม่ใช่ completely fresh machine และไม่ใช่ cold model generation benchmark
- กด citation link จริงแล้ว แต่ browser ไม่แสดงหน้าหนังสือที่อ่านได้ จึงยืนยันเฉพาะ source label/URL/transport ไม่อ้างว่า PDF viewer ผ่าน
- Mermaid ใน preview เป็น code block; การ render บน GitHub จริงยังไม่ตรวจเพราะ publication deferred
- โค้ด/README ใหม่ยัง local; remote branch ยังเป็น commitเดิม ผู้รับ clone จะยังไม่ได้ชุดนี้
- full curriculum audit/Appendix ground truth/independent held-out/L3–L4/speed ที่ checkpoint ระบุยังไม่เสร็จ ไม่ใช้การตรวจ setup แทนผลเหล่านั้น
