# การจัดชุดข้อมูลและความครอบคลุม Ground Truth

## ขอบเขตและสถานะ

ทำงานเฉพาะ local branch `week11_thanapat` ไม่ commit/push/merge ไม่แก้ main และไม่เปลี่ยนข้อเท็จจริงใน DB การใช้ curriculum-audit ช่วยแยก source review, development และ held-out พร้อมตรวจหลักฐานก่อนย้ายไฟล์

**การจัด directory และการนำ labels เดิมที่มี approval กลับมาใช้เสร็จใน batch นี้ แต่ Ground Truth ครบทั้งเล่มยังไม่เสร็จ** การย้ายไฟล์/ผ่าน schema ไม่ใช่การยืนยันข้อมูลกับภาพหนังสือใหม่

## ชื่อเดิม → ความหมายจริง → ตำแหน่งใหม่

ดู [ตารางภาษาไทยพร้อมลิงก์ไฟล์จริง](../ocr_final/data/ground_truth/README.md) และ [catalog](../ocr_final/data/ground_truth/catalog.json)

- ตรวจและย้าย JSON เดิมใน repository 13 ไฟล์ และ live app 14 ไฟล์: SHA และ JSON payload เดิมตรงกันทุกไฟล์ ไม่มีการลบ labels
- AIT labels เดิมใช้กับ AI ผ่าน profile mapping และ approval ปก AI.pdf ที่ระบุ 2566; IT labels ใช้กับ IT.pdf รุ่น 2565 เป็นคนละหลักสูตร ไม่ใช่สหกิจ/ไม่สหกิจของหลักสูตรเดียวกัน
- AIT labels เดิมมี plan=null จึงไม่ถือว่าข้อมูลนี้พิสูจน์ว่า source book ไม่แยกแผน; coop ของ AI เป็น runtime configuration ที่ยังต้องตรวจ plan coverage ให้ครบ
- DSBA master ใช้ ingestion สองแผน ไม่ใช่ evaluation โดยอัตโนมัติ; flat DSBA/IT files ใช้ Lab 7 metrics; general-education pool ใช้ ingestion แต่ PDF provenance ยังไม่ครบ
- rules shared ยังไม่ยืนยันปี/page ราย label; versioned_eval_questions อยู่ history เฉพาะ live app และสร้างจาก DB จึงไม่ใช่ independent ground truth/held-out ส่วน scripts ที่ consume ไฟล์นั้นถูกย้าย path แล้ว
- หน้าที่/metadata/schema/counts และ references ใน code, scripts, tests, docs, checkpoints เก็บใน inventory.json ทั้งสอง root; ตรวจ recursive discovery ของ inventory และ explicit dataset paths ของ loaders แล้ว ไม่ย้าย backups เข้าบริเวณ discovery

- ตรวจ flat labels 360 แถว: identical-row duplicates 0; code/year/semester key collisions 11 เป็น review candidates ไม่ใช่เหตุให้ลบ เพราะ wildcard slots/alternatives/tracks อาจซ้ำ key โดยถูกต้อง; จำนวน missing fields เก็บราย profile ใน catalog/validation

## Labels ที่เพิ่มจากหลักฐานเดิม

- terms datasets 6 ชุด ครอบคลุม 49 semesters / 300 printed options จาก ledger ภาพที่ตรวจไว้เดิม ตรวจ source/image SHA ก่อน reuse; options ไม่เท่ากับจำนวนวิชาที่ต้องเรียน เพราะมี alternatives/tracks
- reviewed-fields datasets 5 ชุด / 31 observations ใช้เฉพาะ approval ชื่อและ prerequisite เดิม ตรวจ SHA และเก็บ PDF/book page; printed page ที่ไม่ทราบยังเป็น null ไม่เดา offset
- source-backed development L1/L2 questions 36 ข้อ แยกทั้งหกแผน 2560; expected credits/term totals มาจาก printed ledger ไม่ได้ export จาก DB ไม่เปลี่ยน protected labels และไม่เรียกชุดนี้ว่า held-out

## ความครอบคลุมทุกหลักสูตร/ปี/แผน

| profile | flat labels | reviewed terms | source QA ใน batch นี้ | สถานะที่ยังขาด |
|---|---|---|---|---|
| DSBA-2565-coop | 44 แถว | n/a | n/a | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| DSBA-2565-no-coop | 45 แถว | n/a | n/a | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| AI-2566-coop | 57 แถว | n/a | n/a | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| IT-2565-no-coop | 108 แถว | n/a | n/a | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| IT-2565-coop | 106 แถว | n/a | n/a | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| DSBA-2560-no-coop | n/a | 9 | 6/6 | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| DSBA-2560-coop | n/a | 8 | 6/6 | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| IT-2560-no-coop | n/a | 8 | 6/6 | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| IT-2560-coop | n/a | 8 | 6/6 | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| BIT-2565-no-coop | n/a | n/a | n/a | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| BIT-2565-coop | n/a | n/a | n/a | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| BIT-2560-no-coop | n/a | 8 | 6/6 | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| BIT-2560-coop | n/a | 8 | 6/6 | full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ |
| legacy | n/a | n/a | n/a | identity/ปี/แผนและ independent content labels ยังไม่ยืนยัน |

## ผลการตรวจและข้อจำกัด

- unit 149/149, schema 30/30 (ไม่ผ่าน 0), frontend 6/6; logs เก็บแยกจาก source data
- existing gold 70/70 ครอบคลุมทุก catalog ตามชุดเดิม; legacy เป็น safety/uncertainty checks ไม่ใช่ book-content accuracy
- new source-backed development 36/36; ไม่ใช่ generalization score หรือชุด frozen ใหม่
- actual browser 13/13 profile metadata responses แสดง curriculum/version/plan ตรงกับที่เลือก; console warnings/errors 0; ยังมี 11/13 program-total responses ที่ printed page ไม่ยืนยัน จึงไม่อ้าง citation ครบ
- runtime DB fingerprints 18/18, runtime code 9/9, source PDF 7/7 คงเดิม; protected tracked JSON expectations ไม่มี diff
- ingestion identity/name/prerequisite loaders ใช้ default paths ใหม่ได้ใน dry run exit0 โดยไม่ --apply และไม่เปลี่ยน DB; ไม่ได้ rebuild production DB ทั้งหมดใน batch นี้
- readonly audit ก่อน/หลังยัง 16 datasets, FAIL1372 / incomplete4881, exit1; ไม่ถือเป็นจำนวนคำตอบผิดหรือผลผ่าน การจัด folder ไม่แก้ legacy/source coverage ที่ยังเปิดอยู่
- first gold run เริ่มขณะ backend หยุด เก็บ failure ไว้แล้ว หลังเปิดจริง rerun ผ่าน; source QA ครั้งแรก runner ตรวจ printed page ของ aggregate ไม่เป็น จึงแก้ paired page_evidence checker พร้อม tests โดยไม่แก้ expected values
- OneDrive result replacement error ถูกเก็บไว้พร้อม partial; รอบใหม่ใช้ temporary local output แล้ว copy ผลกลับ ไม่ทับ evidence ที่ล้มเหลว ไม่พบ git lock/index failure

## การลบและ recovery

- ไม่ลบไฟล์ข้อมูลที่พิสูจน์ไม่ได้ว่าเกินความจำเป็น; files เดิมเป็น relocation ไม่ใช่ discard เก็บสำเนา SHA ตรงกันภายนอก active discovery ใน docs/results/dataset_organization/{repository,live}/recovery/
- migration_final.json ระบุ old/intermediate/new paths และ recovery; original inventories ไม่ถูกแก้ย้อนหลัง Recovery consumers อยู่ในสำเนาเดิม; หากย้อนกลับ ต้องคืน paths และ consumers พร้อมกัน ไม่แตะ DB
- historical report IDs/ชื่อเดิมใน prose เก็บเพื่อเทียบผลย้อนหลัง และใช้ index เป็น migration mapping; ACTION_ITEMS_STATUS เปลี่ยนเฉพาะ path ของ pool ใหม่

## วิธีตรวจซ้ำ

จาก repository root ใช้ environment ตาม README (source PDFs/runtime DBs ไม่อยู่ Git):

```powershell
python ocr_final/scripts/validate_dataset_layout.py --app-root ocr_final --output validation.json
# Local pre/post preservation checks additionally use --migration <migration_final.json>
python ocr_final/scripts/run_qa_gold.py --app-root <LIVE_APP> --runs 1 --output gold.json
python ocr_final/scripts/run_qa_gold.py --app-root <LIVE_APP> --gold ocr_final/data/ground_truth/evaluation/IT-2560/coop-qa.json --runs 1 --output it_old_source.json
# Repeat the last command for all six *-2560/*-qa.json files.
python ocr_final/scripts/audit_all.py --app-root <LIVE_APP> --out reports
```

Raw evidence: docs/results/dataset_organization/ (inventory, migration manifests, validation, preservation, audit, gold, local_qa, UI JSON/PNG, logs) เป็น local evidence ยังไม่ publish

## งานที่ยังต้องทำ

- เริ่ม BIT-2565 rendered academic-plan pages 26–35 เพื่อสร้าง flat/field labels ทั้งสองแผน แล้วตรวจ AI-2566 pages 23–26 เพื่อยืนยัน plan coverage ไม่ใช้ filename/DB เป็น GT
- เติม names/categories/elective/track relationships/prerequisites/graduation conditions ที่ยังขาดจากภาพหนังสือทุกเวอร์ชัน รวม legacy identity; approvals/labels ใหม่ต้องมี page/hash และ review scope
- independent L3/L4 และ frozen held-out ใหม่ยัง n/a; ไม่มีหลักฐาน same-year revision/dual-degree เพิ่ม จึงไม่แต่ง rules หรือ registration permissions
- ตัว validator ผ่านไม่ได้แปลว่า source verification ครบ; dataset schema เดิมเก็บ byte-identical และใช้ catalog เป็น metadata/coverage mapping ไม่เปลี่ยนรูปแบบเฉลยย้อนหลัง
