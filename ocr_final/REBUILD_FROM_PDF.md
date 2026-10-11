# ทดสอบสร้างฐานข้อมูลใหม่จาก PDF

โค้ด hybrid ในชุด instructor-v9 รองรับ AI, DSBA, IT และ BIT ทุกฉบับและแผนที่มีต้นฉบับ รวม **13 profiles เฉพาะแผนการศึกษา** อ่าน text/table ใน PDF ก่อน ถ้าถอดไม่ได้จะเก็บผลที่ปฏิเสธไว้และใช้ OCR จากภาพ ระบบไม่อ่านฐานข้อมูลที่ส่งมา เฉลย evaluation หรือ saved OCR เพื่อสร้างข้อเท็จจริงใหม่

การสร้างนี้ยังไม่เทียบเท่า SQLite ทั้ง 14 ฐานใน runtime ZIP: ไม่รวม catalog descriptions, prerequisites, program regulations และ legacy ใช้ Mode A เมื่อทดสอบความสามารถทั้งหมดของชุดส่งเดิม ใช้โค้ด v9 คู่กับ runtime-data.zip ที่ระบุใน release manifest ไม่ต้องใช้ patch เพิ่ม

## ก่อนเลือกวิธีทดสอบ

ชุด v9 รวม `scripts/rebuild_from_pdf.py`, `scripts/hybrid_extract.py`, `scripts/source_document_ocr.py` รวมทั้ง font review และ source witness ที่ใช้ในคำสั่งใหม่ไว้แล้ว ชุด v8/commit `496dfe2` ก่อนการอัปเดตไม่มีไฟล์เหล่านี้ ให้ใช้ branch `week11_thanapat` ที่อัปเดตหรือ code ZIP v9 ทั้งชุด ไม่ผสม code/maps จากคนละรุ่น

| ทางเลือก | เริ่มจากอะไร | ผลที่รับรองแล้ว |
|---|---|---|
| เปิดชุดส่งเดิม (Mode A) | code + runtime ZIP ซึ่งมีฐานข้อมูล | เปิดใช้ SQLite snapshots; ไม่ใช่สร้างใหม่ |
| สร้างแผนใหม่ด้วย v9 | code v9 + PDF 7 เล่ม; ไม่มีฐานข้อมูลเดิม | แผนการศึกษา 13 profiles ผ่าน source verification |
| สร้างข้อมูลครบทั้งระบบ | PDF + pipeline แผน/catalog/prerequisites/rules + identity ที่ยืนยัน | ยังไม่ครบและยังไม่มีคำสั่งที่รับรองผลสำเร็จทั้งหมด |

## เริ่มจากโฟลเดอร์ใหม่

ใช้โฟลเดอร์ใหม่ที่ว่างและ code ชุดที่มีไฟล์แก้ครบตามข้างต้น วาง `runtime-data.zip` ที่ hash ตรงกับ manifest ของชุดส่งในโฟลเดอร์แม่ สำหรับขั้นตอนนี้ ZIP เป็นแหล่ง PDF เท่านั้น ฐานข้อมูลที่อยู่ใน ZIP ไม่เป็น build input ไม่ใช้โฟลเดอร์ LIVE ของผู้พัฒนา

ติดตั้ง Python 3.11, PowerShell 7 และ Ollama ตาม README หลักก่อน จากโฟลเดอร์แม่ของ `ocr_final/`:

```powershell
Expand-Archive .\runtime-data.zip -DestinationPath .\supplied-artifacts
Set-Location -LiteralPath .\ocr_final
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-rebuild.txt
.\venv\Scripts\python.exe -m pip check
```

`requirements-rebuild.txt` รวม packages สำหรับเว็บ, native PDF และ Pillow ที่ใช้กับภาพ OCR จึงต้องติดตั้งไฟล์นี้สำหรับเส้นทาง hybrid ไม่ใช่ติดตั้งเฉพาะ packages เว็บ

เปิดบริการ Ollama และเตรียมโมเดล หากมีบริการและโมเดลตรงชื่ออยู่แล้วไม่ต้องเปิดบริการซ้ำหรือดาวน์โหลดซ้ำ:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
ollama list
ollama pull qwen3:4b
ollama pull scb10x/typhoon-ocr1.5-3b:latest
$env:CURRICULUM_OLLAMA_MODEL = 'qwen3:4b'
$env:CURRICULUM_OLLAMA_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
$env:LAB7_MODEL_OCR = 'scb10x/typhoon-ocr1.5-3b:latest'
```

Qwen ใช้สำหรับ answering; Typhoon ใช้เมื่อ native extraction ถูกปฏิเสธ รันเฉพาะ `ollama pull` ของโมเดลที่ยังไม่มี การทดสอบ 13 plans รอบที่ผ่านมาอ่าน native ได้ทั้งหมด จึงไม่ใช่การรับรองเวลาของ OCR ทั้งเล่มหรือการดาวน์โหลดโมเดลบนเครื่องอาจารย์ ระบบต้องหยุดและแจ้งข้อผิดพลาดเมื่อ fallback ใช้งานไม่ได้

## เตรียมต้นฉบับ

ใช้ environment ที่ติดตั้ง dependencies ตามคู่มือโครงการแล้ว และมี PDF ต้นฉบับทั้ง 7 เล่มใน `data/input/` หากเริ่มจาก code ZIP ที่ยังไม่มี PDF ให้แตก runtime ZIP ตามคู่มือ แล้วดึงเฉพาะ PDF โดยไม่ติดตั้งฐานข้อมูล:

```powershell
.\venv\Scripts\python.exe scripts/runtime_bundle.py restore --bundle ../supplied-artifacts/runtime-data --app-root . --sources-only --reuse-verified-pdfs
```

คำสั่งนี้ตรวจ SHA256 ของ PDF ก่อนเขียน และไม่อ่านหรือนำเข้า SQLite snapshots หาก PDF ที่มีอยู่ต่างจากต้นฉบับจะหยุดและเก็บไฟล์เดิมไว้

## สร้างและเปิดใช้

หยุด backend ของโฟลเดอร์ที่จะเปลี่ยนฐานข้อมูลก่อน เช่น backend ที่เริ่มด้วย `start_web.ps1` ให้หยุดด้วย `stop_web.ps1` และใช้ port เดียวกัน จากนั้นรันใน `ocr_final/`:

```powershell
.\venv\Scripts\python.exe scripts/rebuild_from_pdf.py --activate
.\venv\Scripts\python.exe scripts/check_setup.py
.\scripts\start_web.ps1
```

ค่าเริ่มต้นสร้างครบ 13 profiles ใน staging ใหม่ ถ้าต้องการตรวจผลก่อนเปิดใช้ ให้ตัด `--activate` ออก คำสั่งจะแสดง candidate path และ `ready` เมื่อข้อมูลผ่านการตรวจ หากเลือกทดลองหนึ่งโปรไฟล์ ใช้ `--profiles ai` และฐานข้อมูลที่เปิดใช้จะมีเฉพาะขอบเขตที่เลือก

ก่อนเปิดใช้ ระบบตรวจ source PDF, coverage, รหัส ชื่อไทย/อังกฤษ ชั่วโมงเรียน ตัวเลือก รายวิชา placeholder หน่วยกิตและเลขหน้า เทียบ fingerprint จากการตรวจหน้าหนังสือที่รับรองไว้ พร้อมตรวจ SQLite และภาพต้นฉบับ Fingerprint ใช้ **หลังสร้างเพื่อการตรวจสอบเท่านั้น** ไม่ถูกส่งเข้า extraction หรือ ingest การเปลี่ยน PDF/ข้อมูล/ภาพที่ทำให้ไม่ตรงจะถูกปฏิเสธและเก็บ staging ไว้ ต้องตรวจต้นฉบับใหม่ ไม่แก้ข้อมูลให้ตรงเฉลย

`--activate` สร้าง backup และเปลี่ยน active pointer เมื่อผ่านครบเท่านั้น ผลลัพธ์ระบุ backup และคำสั่ง rollback หน้าเว็บแสดงขอบเขต 13 profiles และข้อจำกัดของข้อมูล คำถามนอกแผนการศึกษาต้องไม่ถูกตีความว่าหนังสือไม่มีข้อมูลนั้น

หลังเปิดเว็บ ดู `/api/health` ให้ `database_root` เป็นโฟลเดอร์ใหม่นี้และ `build_contract.kind` เป็น `academic-plan-only` จำนวน profiles ต้องตรงที่ขอสร้าง `check_setup.py` ผ่านในกรณีนี้หมายถึงชุดแผนที่ประกาศพร้อมใช้ ไม่ได้หมายถึง catalog/rules หรือฐานข้อมูลทั้ง 14 ชุดสร้างครบ ทดสอบคำถามแผน ชื่อวิชา หน่วยกิต และเปิด citation ไปยัง PDF page จริง รวมทั้งคำถาม prerequisite/description ที่ต้องแจ้งข้อจำกัด

ถ้ารันล้มเหลว ให้เก็บ candidate path, `build.json`, logs และ raw outputs ใน staging เดิมไว้ `rebuild_from_pdf.py` ยังไม่มีตัวเลือก `--resume`; เรียกใหม่จะสร้าง candidate ใหม่ ไม่ทำต่อจาก candidate เดิมโดยอัตโนมัติ เครื่องมือ extraction บางตัวมี resume ที่ตรวจ source/code/model/config hashes และต้องใช้ตามคู่มือของเครื่องมือนั้น ห้ามลบฐานข้อมูลเดิมหรือถือว่า output ที่ไม่ครบเป็นผลสำเร็จ

## เกณฑ์ก่อนเรียกว่าสร้างครบระบบ

ความครบต้องวัดจากข้อมูลและคำตอบที่ตรงต้นฉบับ ไม่ใช้เพียงจำนวน `.db`, HTTP 200 หรือ SQLite integrity และไม่จำเป็นต้องมี SHA256 ของไฟล์ฐานข้อมูลตรงกับ snapshot เก่า เพราะ metadata และลำดับการสร้างอาจต่างกัน ต้องตรวจข้อเท็จจริง ความสัมพันธ์ ฉบับ/แผน และ citations ที่ใช้จริง

1. **ต้นฉบับและ identity:** ตรวจ PDF 7 เล่มและ mapping ของ 13 profiles ทุกฉบับ/แผน ส่วน legacy ที่เป็น mixed catalog ต้องยืนยันที่มาก่อน ไม่ตั้งฉบับหรือแผนจากชื่อไฟล์
2. **Extraction ครบขอบเขต:** แผนการศึกษาผ่านแล้ว แต่ต้องอ่าน catalog และข้อกำหนดที่เกี่ยวข้องให้ครบ รวมตารางสแกน แถวต่อข้ามหน้า และหน้าที่ native มีเฉพาะ header/footer ต้องมีรายการหน้าค้างที่ตรวจสอบได้
3. **Catalog และความสัมพันธ์:** เก็บคำอธิบายไทย/อังกฤษ หน่วยกิต ชั่วโมง และ prerequisite พร้อม source page แยก “ไม่มีวิชาบังคับก่อน” ที่ต้นฉบับระบุจาก “ยังอ่าน/ตรวจไม่ครบ” รักษา AND/OR และไม่อนุมานสิทธิลงทะเบียน
4. **ตรวจและเปิดใช้:** ตรวจจากต้นฉบับอย่างเป็นอิสระก่อนออก receipt และผ่าน full validation จึง activate แบบ full ได้ จนถึงตอนนั้นคง contract `academic-plan-only`; ไม่เติมส่วนขาดจาก bundled DB หรือ evaluation answers
5. **ซ้อมจากชุดที่จะส่งจริง:** เริ่มจากโฟลเดอร์ใหม่และไม่มีฐานข้อมูล/old OCR สร้างใหม่ ตรวจ gold Q&A แยกฉบับและแผน เปิด UI และ citations จริง ทดสอบ interruption/recovery แล้วบันทึกเวลาติดตั้งและเวลาสร้างแยกกัน ชุดที่เผยแพร่ต้องมี code/maps/dependencies/commands รุ่นเดียวกับที่ซ้อม

สถานะล่าสุดก่อนปรับคู่มือ: native catalog ได้ 469 literal candidates จาก 7 เล่ม และเทียบ prerequisite/name ที่เคยตรวจต้นฉบับไว้ได้ 29/29 แต่ยังไม่ใช่ catalog ที่ตรวจครบหรือเปิดใช้ใหม่ ส่วน OCR ตาราง AI PDF240 ยังติด memory allocation และผล header วนซ้ำ งานถัดไปจึงต้องแก้ context/ขนาดภาพและตรวจทุกแถว ก่อน ingestion/certification ของ catalog ดู [รายงานหลักฐาน](../docs/PDF_REBUILD_REPAIR_20261011.md) การเพิ่มคำสั่งหรือคู่มือไม่ทำให้ข้อจำกัดเหล่านี้ผ่านเอง

## ผลที่ตรวจแล้ว

- สร้างจาก PDF ต้นฉบับครบ 13 profiles แล้วตรวจ source → SQLite ผ่านทั้งหมด โดยรอบนี้ทั้ง 13 อ่าน native PDF ได้ด้วย font encoding ที่ตรวจรับรองไว้
- gold Q&A สำหรับฐานข้อมูลสร้างใหม่ 105/105 ข้อ ผ่านหน่วยกิตและการอ้างอิงทุกแผน ข้อสอบชุดนี้เป็น development/source-backed regression ไม่ใช่ held-out หรือความถูกต้องทั้งเล่ม
- ทดสอบ fallback จริงหนึ่งหน้า DSBA PDF27 โดยไม่ให้ font mapping: native ถูกปฏิเสธ → image OCR → parser ได้ 6 แถว 18 หน่วยกิต และชื่อ/ชั่วโมงตรงภาพต้นฉบับ ผลนี้ยังไม่รับรอง OCR จากภาพทุกหน้า
- IT2560 สหกิจปี4ภาค1 นับ 6 หน่วยกิต: เลือกหนึ่งแขนงแล้วเลือกหนึ่งรายวิชาภายในแขนง เก็บทั้งสหกิจในประเทศและต่างประเทศ ไม่รวมทุกตัวเลือกเป็น 36 หน่วยกิต

เวลารันขึ้นกับ PDF และเครื่อง Native extraction เร็วกว่าการ OCR จากภาพมาก ส่วน OCR อาจใช้หลายนาทีต่อหน้า ไม่รับรองเวลารันเครื่องใหม่หรือการติดตั้งโมเดลครั้งแรก

## ตรวจส่วน catalog ที่ยังไม่ครบ

เครื่องมือส่วนนี้รวมใน code v9 เพื่อเก็บ diagnostics แต่ยังไม่เปิดใช้ catalog ใหม่กับ chatbot คำสั่งด้านล่างตรวจว่าแต่ละหน้ามี native text ที่อ่านเนื้อหาจริงได้หรือยังต้องใช้ OCR/review โดยไม่สร้างหรือเปลี่ยนฐานข้อมูล:

```powershell
.\venv\Scripts\python.exe scripts/source_catalog.py --pdf data/input/AI.pdf --font-review data/source_reviews/font_encoding/all-reviewed-source-glyphs-20261011.json --coverage-only --output work/ai-source-coverage-new
```

ต้องใช้ output directory ใหม่เสมอ ผลระบุ PDF page และเหตุผลที่ native อ่านไม่ครบ เช่น glyph ที่ยังไม่ตรวจ หรือตารางเป็นภาพ แม้มี native header/footer การทดลอง extraction ด้วย `--source-documents` ยังเป็น staging diagnostic และถูกปฏิเสธ full activation จนกว่า catalog/rules/legacy จะมี source verification ครบ

`scripts/source_document_ocr.py` เก็บ hybrid transcription ของหน้าที่ระบุพร้อม raw image/HTTP response/checkpoints แต่ยังไม่แปลงเป็น catalog ที่รับรองแล้ว ผลว่าง ผลวนซ้ำจน token limit และ RAM allocation failure เป็น failure ที่ต้องเก็บไว้และแก้สาเหตุ ไม่ถือว่าหนังสือไม่มีวิชานั้น
