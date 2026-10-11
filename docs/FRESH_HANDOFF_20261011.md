# ผลการซ้อมติดตั้งและส่งต่อ — 11 ตุลาคม 2569

## ขอบเขตและผลจริง

ใช้โค้ดที่ยังไม่ commit จาก repository บน `week11_thanapat` คัดลอกลงโฟลเดอร์แยกที่มีช่องว่างในชื่อ ไม่ใช้ LIVE sibling ขณะรัน ไม่สร้าง junction ของ venv หรือ model store ไม่เปลี่ยนข้อมูลทำงานของผู้ใช้ และไม่ publish

| ขั้นตอน | ผลที่วัดได้ | ขอบเขต |
|---|---|---|
| สร้าง venv ใหม่ด้วย Python 3.11.9 | ผ่าน 20.18 วินาที | ใช้ Python executable ที่ติดตั้งบน Windows อยู่แล้ว |
| pip --isolated / --no-cache-dir | ผ่าน 29.67 วินาที; pip check ผ่าน | ชุดเว็บ ไม่รวมชุด OCR/dev ทั้งหมด |
| restore artifacts | 14 DB + 7 PDF ผ่าน 12.70 วินาที | ตรวจ SHA256/path/SQLite integrity; ไม่ทับไฟล์เดิม |
| ดาวน์โหลด Qwen ครั้งแรก | 61.46 วินาที; store 2,497,303,285 bytes | `/api/tags` ก่อนดาวน์โหลดว่างจริง; เวลาเฉพาะเครือข่ายนี้ |
| เรียกโมเดลจริง | ส่งผล generation กลับ | probe 32 tokens จบด้วย length ไม่ใช่หลักฐานคุณภาพคำตอบหลักสูตร |
| เปิด backend ครั้งทดสอบที่สำเร็จ / restart | 4.03 / 3.47 วินาที | พอร์ต 8002; Ollama 11436 แยกจากบริการของผู้ใช้ |
| คำถามตัวอย่าง / routes | 4 requests ผ่าน: 2 คำถาม × 2 startup cycles | ตรวจเนื้อหาและหลักฐาน ไม่ใช่ HTTP200 อย่างเดียว |
| development gold | 70/70: 14 catalogs × 5 cases | รวม AI, DSBA, IT, BIT, 2560/2565 และ legacy; ไม่ใช่ held-out accuracy |
| missing model | readiness false; model request HTTP404 | ไม่ลบ model; สอง routes คืนข้อจำกัดจาก DB โดยไม่ใช้โมเดลได้ |
| DB หลัง startup/shutdown | SHA256 ทั้ง 14 ฐานไม่เปลี่ยน | ไม่ทำ OCR/rebuild ทุกครั้ง |
| focused runtime bundle tests | 4/4 ผ่าน | รวม complete PDF roundtrip และ reject corrupted PDF ก่อนเขียน DB |
| read-only audit | 14 datasets; FAIL 1,372; incomplete 51 | ชุดส่งต่อไม่รวม work/ref_text เดิม ผลต่าง scope ไม่ใช่คุณภาพดีขึ้น |

model ที่ดาวน์โหลดคือ `qwen3:4b`, Q4_K_M, digest `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` ไม่เก็บโมเดลใน ZIP ผู้รับต้องดาวน์โหลดตาม root README

## ตัวอย่างผลจริงและแหล่งอ้างอิง

| คำถาม / route | คำตอบจริง | ตรวจต้นฉบับ |
|---|---|---|
| IT old: `แผนไม่สหกิจศึกษา หลักสูตรนี้มีกี่ปี` / `/ask` | `IT-2560-no-coop: 4 ปี (ที่มา: IT-60.pdf หน้า 6)` | ภาพ PDF6 มี printed page1, ระบุหลักสูตร 2560 และหลักสูตรปริญญาตรี 4 ปี |
| `หลักสูตร BIT พ.ศ.2565 แผนไม่สหกิจศึกษา วิชารหัส 06036123 ชื่ออะไรและมีกี่หน่วยกิต` / `/api/ask` | `BIT-2565-no-coop: 06036123 เทคโนโลยีกลุ่มเมฆ (CLOUD TECHNOLOGY), 3 หน่วยกิต, L-P-S 3-0-6 (ที่มา: BIT-65.pdf หน้า 28)` | ภาพ PDF28/printed page23 ตาราง Year3/S1 มีรหัส ชื่อทั้งสองภาษา และ 3(3-0-6) ตรงกัน |

ตรวจ source-info/source-page และดูภาพที่ renderer คืนจริง ไม่อ้างว่าการคืน PNG เป็นการตรวจ UI citation clicks ใน browser รอบนี้ การเปิด browser ถูก policy ปฏิเสธจากรอบก่อน ไม่ลองช่องทางอื่นเพื่อหลบ policy

## ปัญหาที่พบและแก้ระหว่างซ้อม

1. OneDrive ปฏิเสธ atomic checkpoint replacement หลังสร้าง venv สำเร็จ: เพิ่ม bounded retry และ resume เฉพาะขั้นที่สำเร็จแล้ว เก็บ error เดิม ไม่สร้าง venv/download ซ้ำโดยไม่มีเหตุผล
2. harness เข้าใจ response contract ผิด: `/ask` ไม่มี rows และ `/api/ask` ไม่มี sources; แก้ตัวตรวจให้ตรวจแต่ละ contract ตามจริง ไม่แก้ API/runtime เพื่อให้ทดสอบผ่าน
3. missing-model test เดิมคาด HTTP503 ทุกคำถาม แต่เส้นทาง SQLite-only ปัจจุบันไม่เรียก LLM: แยก model request HTTP404 ออกจาก explicit DB-gap answer; เก็บผลเดิมและผลใหม่ ไม่ตีความ HTTP200 เป็นความถูกต้องโดยอัตโนมัติ
4. bundle เดิมไม่รวม PDF: เพิ่ม `export --include-pdfs` และ restore ตรวจไฟล์ทุกชนิดก่อนเขียน พร้อม tests ไม่ต้องอ้าง path ในเครื่องผู้พัฒนา

## ชุดส่งต่อและคำสั่งตรวจซ้ำ

### ยืนยันจาก ZIP ที่จะส่งจริง

รอบที่สองเริ่มจาก ZIP ทั้งสองไฟล์ใน v2 ไม่ใช่ checkout: ตรวจ SHA256 archive และไฟล์โค้ด 471 ไฟล์ก่อนใช้ สร้าง venv อีกชุด ติดตั้ง pip โดยไม่ใช้ cache และดาวน์โหลด Qwen ลง store ว่างอีกชุด ผล rehearsal exit0, คำตอบ 2 คำถาม × 2 cycles ผ่าน, PDF6/book1 และ PDF28/book23 rendering/mapping ผ่าน, DB hashes ไม่เปลี่ยน และหยุดบริการที่ทดสอบเปิดเองแล้ว `ollama list` และ `ollama pull qwen3:4b` ผ่าน exit0 กับ store ของรอบนี้ โดย CLI pull เป็นการตรวจ idempotence หลังดาวน์โหลด ไม่ใช่การวัด download ครั้งแรกด้วย CLI

รอบ ZIP สร้าง venv 16.09 วินาที, packages 26.43 วินาที, restore 33.19 วินาที และดาวน์โหลด model 79.51 วินาที เวลาแตก ZIP/คัดลอกไฟล์ไม่รวมในเวลา restore ผลต่างจากรอบแรกแสดงว่าค่าเวลาไม่ใช่ SLA

ไม่มี `tmp/`, venv, model cache, `.env`, working DB หรือ PDF ใน code ZIP; PDF/DB อยู่ใน data ZIP เท่านั้น code ZIP 4,379,130 bytes และ data ZIP 1,241,163,129 bytes เก็บ SHA256 ใน `handoff-manifest.json` ผลรอบใหม่นี้ไม่เปลี่ยนผล gold 70 cases เพราะ runtime code ของแอปไม่เปลี่ยน

หลักฐาน: [package verification](results/submitted_handoff_20261011/package-state.json), [fresh ZIP rehearsal](results/submitted_handoff_20261011/rehearsal.json), [CLI list](results/submitted_handoff_20261011/list.stdout.log), [CLI pull](results/submitted_handoff_20261011/pull.stderr.log)

ชุดเตรียมปัจจุบันใน `delivery/instructor-handoff-20261011-v3/` แยก `curriculum-project.zip`, `runtime-data.zip` และ `handoff-manifest.json` ไม่ได้ commit/push ส่งไฟล์ข้อมูลให้ผู้รับแยกจาก Git ตามสิทธิ์การใช้หนังสือ ไม่อ้าง license เผยแพร่หนังสือสาธารณะ ชุดก่อนหน้าเก็บเป็นประวัติ; v2/v3 ไม่รวม `ocr_final/tmp/` ที่เป็นภาพ cache จากการ review เดิม v3 เพิ่มรายงานผลจาก ZIP, หมายเหตุ lock file ใน README และ script ตรวจ ZIP ไม่เปลี่ยน runtime code/DB จาก v2 ที่ซ้อมจริง จึงใช้ผลเดิมเฉพาะ dependencies ที่ตรงกัน ไม่อ้างว่าซ้อมติดตั้งจากศูนย์รอบสาม

แตก code ZIP ที่ root ของโฟลเดอร์งาน แล้วแตก data ZIP ลง `supplied-artifacts/` จะได้ `supplied-artifacts/runtime-data/manifest.json` ทำตาม root README ตั้งแต่ venv, packages, .env, model, restore และ startup ไม่ต้องมี LIVE sibling

จาก `ocr_final/` ผู้ทดสอบที่มี artifacts และโปรแกรมพร้อม ใช้ script ต่อไปนี้กับ workspace/output ใหม่เสมอ:

```powershell
py -3.11 scripts/verify_fresh_handoff.py --project-root .. --workspace "$env:LOCALAPPDATA/Temp/curriculum-fresh-new" --bundle ../supplied-artifacts/runtime-data --output ../docs/results/fresh-new/rehearsal.json
```

script แยก model store และบริการพอร์ต 11436/8002 ไม่ลบ models ของผู้ใช้ `--resume` ใช้ได้เฉพาะ workspace ของรอบเดิมหลังตรวจว่าไม่มีงาน/บริการเดิมทำงานแล้ว ไม่ใช้ข้าม source/code/artifact identities ที่เปลี่ยน

## สิ่งที่ยังไม่ยืนยัน

- ตัวติดตั้ง Python/PowerShell/Ollama บน Windows เปล่า, เครื่องอาจารย์จริง, Linux/macOS และเครื่องไม่มี GPU
- browser UI/citation navigation รอบใหม่นี้; มีเพียง server-rendered pages ที่ตรวจภาพจริงสองไฟล์
- minimum hardware และเวลา download บนเครือข่ายอื่น; ไม่วัด difficult-question p95 หรือ cold/warm model accuracy จาก readiness probe
- full reconstruction, source fidelity ทั้งเล่ม, held-out final evaluation และปัญหา retrieval/ingestion ใน checkpoint ยังไม่เสร็จ
- ไม่มีคำรับรองว่าทุกคำถามตอบครบหรือข้อมูลทุกหลักสูตรถูกต้อง; audit ยังมี findings จริง

## หลักฐานดิบ

- [rehearsal state และคำตอบทั้งสองรอบ](results/fresh_handoff_20261011/rehearsal.json)
- [development gold 70 cases](results/fresh_handoff_20261011/supplemental2/gold.json)
- [missing-model behavior](results/fresh_handoff_20261011/supplemental2/missing-model.json)
- [supplemental state และ DB hash check](results/fresh_handoff_20261011/supplemental2/state.json)
- [ภาพ IT PDF6](results/fresh_handoff_20261011/first-citation.png)
- [ภาพ BIT PDF28](results/fresh_handoff_20261011/supplemental2/bit-citation.png)
- [ผล audit](results/fresh_handoff_20261011/supplemental2/audit/audit_results.json)

raw evidence มี paths ของ isolated test เพื่อให้ตรวจ provenance ได้ root README ใช้ relative paths/ตัวอย่างที่ผู้รับเปลี่ยนเอง ไม่ใช้ paths เหล่านี้เป็น runtime dependencies
