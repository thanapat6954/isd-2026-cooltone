# งานต่อจาก checkpoint: branch และ citation ของ IT-2560

## การเผยแพร่

สร้าง remote `week11_thanapat` จาก commit เดิม `d051d7c3d3e961fa6b55b1e5299acc71ab9c2ba2` ตามคำขอ ไม่ commit งานที่ยัง local ไม่เปิด PR/merge/main หลักฐานคำสั่งอยู่ใน [BRANCH.md](BRANCH.md) งานแก้ครั้งนี้และ week11 ก่อนหน้ายัง uncommitted ไม่ได้ขึ้น remote

## สาเหตุและขอบเขตการแก้

1. **data-ingest bug:** program metadata ของ IT-2560 อ้างหน้า academic plan สุดท้าย (`coop` PDF40, `no-coop` PDF33) แทนหน้าข้อมูลทั่วไป PDF33/book28 ยืนยัน 130 หน่วยกิต แต่ไม่ได้ระบุรูปแบบหลักสูตร 4 ปี จึงไม่ใช้หน้านั้นรองรับทุก metadata field
2. **code bug:** query สำหรับชื่อ/หน่วยกิตรวม/จำนวนปีไม่ส่ง `program.printed_page_number` เพิ่มการอ่าน column เฉพาะเมื่อมีค่าใน schema ไม่เดา folio ของ profile อื่น
3. **answer-evidence guard:** เก็บ correction history ใน SQLite แต่ไม่เสนอ `program_metadata_review` หรือ `before_json` เป็น schema ให้ chatbot ใช้ตอบ

ตรวจภาพ IT-60.pdf PDF6/book1 ด้วยตา: หมวดที่ 1 ข้อ 1 ระบุสาขาวิชาเทคโนโลยีสารสนเทศ ข้อ 4 ระบุ 130 หน่วยกิต ข้อ 5.1 ระบุหลักสูตรปริญญาตรี 4 ปี ภาพ/hash อยู่ [inventory.json](inventory.json) source SHA `eded877e329f1c1ede974e9a708c337f18b9443c44c158b3478d0e74dcec556d` ไม่ใช้ embedded Thai/OCR เป็นเฉลย

เพิ่ม source review สำหรับ ingestion ใน `ocr_final/data/source_reviews/program_metadata.json` แยกจาก evaluation labels ไม่ใส่คำถามหรือเฉลยใน production ข้อมูลชื่อ/หน่วยกิต/ปีเดิมต้องตรงกับภาพก่อนอนุญาตแก้ citation มี source-hash/identity/version/plan guards, backup, staging, integrity และ logical-facts SHA ไม่เปลี่ยนค่า course/plan/prerequisite/relationships

เพิ่ม `program.printed_page_number` และ immutable approval history เปลี่ยน PDF citation เป็น6/book1 สำหรับ IT2560ทั้ง2plan ผ่าน generic `scripts/ingest_program_metadata.py` และ post-build hook ใน `run_lab8b.py` ไม่แก้ original OCR/frozen labels

## หลักฐานและผลตรวจ

| scope | ผล | ข้อจำกัด |
|---|---|---|
| IT-2560-coop metadata | API 3/3, UI 3/3 | ชื่อ/130หน่วยกิต/4ปี และ PDF6/book1 เท่านั้น ไม่ใช่ตรวจทั้งเล่ม |
| IT-2560-no-coop metadata | API 3/3, UI 3/3 | ขอบเขตเดียวกัน; หลัง guard re-probe UI อีกหนึ่งข้อ |
| IT-2565 isolation | 2/2 | เลือก source IT.pdf ไม่ใช้ IT-60.pdf ไม่ใช่ metadata accuracy ทั้งเล่ม |
| metadata fixture tests | 7/7 | synthetic DB, immutable/idempotent/refusal/rollback/paired-folio/history guards |
| placeholder + metadata focused tests | 17/17 | regression ไม่ใช่ independent held-out |
| rollback dry-run | 2/2 | backup integrity/hash ถูกต้อง ไม่ restore live DB |
| read-only audit | 16 datasets, FAIL1372, incomplete4881, missing[] | exit1 ตาม coverage gaps; findings ไม่ใช่คำตอบผิด |

API paired checks รวม8/8 ใน [metadata_qa_release.json](metadata_qa_release.json) หกข้อถามทั้ง `/api/ask` และ `/ask`; สองข้อ version traps ใช้ `/api/ask` คำสั่ง rerun อยู่ด้านล่าง UI snapshots [metadata_ui.json](metadata_ui.json) และ re-probe หลัง guard [metadata_ui_release.json](metadata_ui_release.json) มีปี/plan/คำตอบ/page pair/link จริง console errors ที่ตรวจล่าสุด `[]` screenshot [metadata_ui_release.png](metadata_ui_release.png)

12/14 active catalogs อื่นมี SHA เท่าเดิม มีเพียงสอง IT2560 DB ที่เปลี่ยน citation/schema; source PDFs7/7 และ GT JSON14/14 SHA เท่าเดิม protected test JSON/OCR16files เทียบ dependencies ของ release ก่อนหน้าไม่เปลี่ยน [baseline](inventory.json), [after](inventory_after.json)

Full shared regression ผลสุดท้าย [checks_release/checks.json](checks_release/checks.json): unit133/schema30/frontend6/gold70/old2560 65/provenance14/version_sets6 ทุก job exit0; dependency hashes unchanged=true แยก raw outputs และ dependency hashes ห้ามใช้ผลก่อน guard แทนผลสุดท้าย

## การแก้และไฟล์

- `ocr_final/lab10_fastapi/curriculum_app/database.py`: ไม่ expose history ใหม่ใน runtime schema
- `ocr_final/lab10_fastapi/curriculum_app/query_planner.py`: อ่าน paired program folio เมื่อมี column
- `ocr_final/scripts/ingest_program_metadata.py`, `data/source_reviews/program_metadata.json`, `run_lab8b.py`: source-approved citation ingestion และ rebuild hook
- `ocr_final/scripts/verify_program_metadata.py`, `tests/test_program_metadata.py`: development/regression checks ไม่แตะ frozen inputs
- port reviewed `tests/test_placeholder_fidelity.py` จาก repo ไป live ที่เคยใช้ test/UI wording รุ่นเก่า ไม่เปลี่ยน production facts เพื่อเอาใจ test

implementation ทุกไฟล์ข้างต้น port ลง live application แล้ว งานที่มีอยู่ก่อนหน้าคงไว้ ไม่มี commit ใหม่

## สำรองและย้อนกลับ

สำรอง live DB ก่อนแก้ที่ `work/backups/program-metadata/20261006T182740174826/` พร้อม stages/history และ hashes ใน [metadata_ingest.json](metadata_ingest.json) ย้อนกลับต้องหยุดเฉพาะ verified backend ก่อน จาก repo `ocr_final/`:

```powershell
python scripts/rollback_db_only.py --app-root '<live-app>' --backups '../docs/results/week11_continuation/metadata_ingest.json' --profile IT-2560-coop --output '<local-result>/rollback-coop.json'
```

คำสั่งด้านบนเป็น dry-run ใช้ `--apply` เฉพาะเมื่อจำเป็นต้องย้อนกลับจริง script สำรอง current DB ก่อน restore ใช้ `IT-2560-no-coop` สำหรับอีก plan โค้ดอ่าน printed column แบบ optional จึงรองรับ schema เดิมเมื่อ restore ไม่ restore live ในการทดสอบนี้

runtime bundle ใหม่ `work/handoff/runtime-data-week11-metadata-20261007/` มี14SQLite snapshots+manifest ไม่รวม PDF/gold และไม่อยู่ Git/discovery; bundle เก่ายังเก็บไว้แต่ไม่มี citation repair ล่าสุดสอง IT DB ไม่เรียก artifact นี้ว่า independent GT

## วิธีรันซ้ำ

จาก repo `ocr_final/` ใช้ Python ของ live venv หาก checkout ไม่มี venv ระบุ `--app-root` เป็น live folder ให้ชัด ไม่รัน test suite จากสำเนา live ที่ยังมี historical tests บางไฟล์:

```powershell
python scripts/verify_program_metadata.py --output '<new-local-result>/metadata.json'
python scripts/run_handoff_checks.py --app-root '<live-app>' --output '<new-local-result>/checks'
python scripts/audit_all.py --app-root '<live-app>' --out '<new-local-result>/audit'
python scripts/ingest_program_metadata.py --app-root '<live-app>' --output '<new-local-result>/staged.json'
```

ingest คำสั่งสุดท้ายตรวจ/backup/stage เท่านั้น ไม่ deploy เว้นแต่เพิ่ม `--apply`; รองรับ idempotence และปฏิเสธ conflict ไม่แก้ metadata fact ที่ไม่ตรงภาพโดยอัตโนมัติ

## ผลแรกที่ไม่ผ่านและข้อจำกัด

- [checks_live_stale/checks.json](checks_live_stale/checks.json): live suite รุ่นเก่า80tests/1failure เพราะคาดคำ UI เก่า “สล็อตวิชาเลือก” แทน “รายการวิชาเลือก” ตรวจ diff และ port reviewed test จาก repo ไม่แก้คำตอบ factual
- [metadata_qa_first.json](metadata_qa_first.json): verifier รุ่นแรกคาด `sources.url` ทั้งที่ API contract ส่ง `section/page/book_page` และ frontend สร้าง link เอง แก้ verifier ให้ใช้ contract จริง แล้วตรวจ href ผ่าน UI ไม่เพิ่ม field ให้ API เพื่อให้ test ผ่าน
- full graduation Appendixก ทั้ง7books, independent full-field/held-out ทุกversion, legacy identity, L3 accelerated/graduation completeness, L4 same-year/dual-degree ยังเปิด ไม่แก้ labels เพื่อเพิ่มคะแนน
- final frozen regression ไม่รันใหม่ใน batchนี้ ผล171/180จาก batchก่อนหน้าเป็น historical ไม่ใช่ final accuracy หลังแก้ metadata; speed challenge ยังไม่ยืนยัน
- visible PDF viewer ยัง n/a จากข้อจำกัดเดิม ตรวจชื่อ/link/page pair จริง แต่ไม่อ้างว่า viewer แสดงเนื้อหาครบ
- ไม่ redo49terms/A0/A1/ปก ไม่สร้าง slides/PDF presentation/video

NEXT ACTION: source-review Appendixก graduation/prerequisite constraints ทั้ง7booksทีละbatchโดยมี approvals และ independent labelsแยก; เริ่ม IT-2560 จาก table-of-contents locator แต่ต้องตัดสินจากภาพจริง รักษา frozen input ไม่ใช้คำตอบแอปเป็น GT
