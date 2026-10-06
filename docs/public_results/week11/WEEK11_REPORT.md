# ผลตรวจและส่งต่องาน week11

งานอยู่ใน branch `week11_thanapat` ยังไม่ commit/push/PR/merge และไม่แก้ main รายงานนี้แยกผลที่สังเกตจากความถูกต้องทั้งเล่ม ไม่อ้างคะแนนอาจารย์

## ผลแยกตามหลักสูตร

| profile | แถว course / plan | HIGH / MED | หน้า PDF ที่ตรวจภาพสะสม | gold regression | old development | อ้างข้อบังคับ | ยังไม่ครบ |
|---|---|---|---|---|---|---|---|
| legacy-course-catalog | 6147 / n/a | 6215 / n/a | n/a | 5/5 | n/a | n/a | ตัวตน/ต้นฉบับ/ไม่มี UI |
| AI-2566-coop | 299 / 41 | 3 / n/a | 2 | 5/5 | n/a | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| BIT-2560-coop | 38 / 42 | 2 / n/a | 6 | 5/5 | 10/10 | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| BIT-2560-no-coop | 38 / 42 | 2 / n/a | 6 | 5/5 | 10/10 | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| BIT-2565-coop | 302 / 43 | 3 / n/a | 2 | 5/5 | n/a | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| BIT-2565-no-coop | 301 / 43 | 3 / n/a | 2 | 5/5 | n/a | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| DSBA-2560-coop | 39 / 44 | 2 / n/a | 7 | 5/5 | 11/11 | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| DSBA-2560-no-coop | 38 / 44 | 2 / n/a | 7 | 5/5 | 10/10 | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| DSBA-2565-coop | 294 / 45 | 3 / n/a | 2 | 5/5 | n/a | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| DSBA-2565-no-coop | 292 / 45 | 3 / n/a | 2 | 5/5 | n/a | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| IT-2560-coop | 58 / 64 | 2 / n/a | 9 | 5/5 | 12/12 | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| IT-2560-no-coop | 58 / 64 | 2 / n/a | 9 | 5/5 | 12/12 | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| IT-2565-coop | 305 / 53 | 4 / n/a | 2 | 5/5 | n/a | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |
| IT-2565-no-coop | 303 / 53 | 3 / n/a | 2 | 5/5 | n/a | 3/3 | ชื่อ/หมวด/คำอธิบาย/prerequisite/ภาคผนวกทั้งเล่ม |

HIGH เป็นจำนวน finding รวม FAIL/NEEDS_REVIEW/SKIPPED ไม่ใช่จำนวนคำตอบผิด harness นี้ไม่มีการประเมิน MED แยกจึงเป็น n/a จำนวนหน้าคือภาพปก + academic-plan ledger รุ่นเก่า + graduation-reference pages ไม่ใช่ครบทุก field ของแต่ละหน้า

audit: 16 datasets (รวม staged DSBA อีกสองไฟล์), FAIL 1372, incomplete 4881; missing curricula `[]` exit1 จงใจ fail loudly ไม่ตีความว่าเป็นจำนวนข้อสอบผิด ดู [raw](audit_release/audit_results.json) และ audit_*.md เฉพาะ Summary/HIGH

## สาเหตุและการแก้

1. **code bug — citation:** SQL yearly aggregates ไม่มี pages และ frontend จับคู่ PDF/folio จากคนละ sorted lists เพิ่ม `page_evidence` ที่เป็นคู่จาก SQLite และไม่เดา folio เมื่อหลักฐานไม่เป็นคู่ unit/UI ทั้ง 13 profile ตรวจแล้ว; ไม่ยืนยัน citation ของทุก course/metadata
2. **code bug — startup:** เคยยอมรับ backend คนละโฟลเดอร์หรือ Ollama ที่ไม่มีโมเดล เพิ่ม root/model/DB readiness, null-model guard และ owned start/stop ด้วย PID+UTC ticks ทดสอบ refusal แล้ว PID server เดิมไม่เปลี่ยน
   แยก handoff/backups/verification folders ออกจาก runtime DB discovery และ audit เพื่อไม่เลือก snapshot เป็น production catalog ทดสอบ export bundle ใน app แล้วจำนวน active catalog คงเดิม
3. **data-ingest gap — graduation references:** ตรวจภาพ 7 หน้า เก็บ regulation references ใน immutable `program_requirement` ทั้ง 13 profile ผ่าน source-hash guarded ingest ไม่ใช้ runtime JSON แทน SQL แยก production source-review จาก test labels แสดงข้อจำกัด appendix/3.5 ปี ไม่อนุญาตจบ/ลงทะเบียน
4. **schema migration gap:** current IT/BIT 4 profile ขาด fidelity fields เพิ่ม columns แบบ NULL unknown ทุก plan value เดิมคงอยู่ ไม่อ้างว่า column ที่เพิ่มเป็น fact ที่ตรวจแล้ว legacy คนละ schema จึงไม่ยัด columns เหล่านี้ให้ legacy
5. **OCR loss / data coverage — ยังเปิด:** ชื่อ หมวด description และ prerequisites ยังตรวจไม่ครบทุกเล่ม legacy มี 6147 page-fragment rows แต่ตัวตน/ปี/source fidelity ไม่ครบ curated fixes ไม่เพิ่ม OCR F1
6. **source ambiguity / unavailable inputs — ยังเปิด:** หน้าเกณฑ์จบอ้างภาคผนวกซึ่งยังตรวจไม่ครบ ไม่รับรองแผน 3.5 ปี/ตารางเปิดวิชา ไม่พบ source ของ AI เก่า, same-year revision หรือ dual degree; registration availability ไม่เดา

การนับ 61 changed/added fields ในรายงานก่อนแก้คือ factual57 + presentation4 ไม่ใช่ 61 คำตอบผิด ผล provenance ใหม่ต้องอ่าน raw ไม่เหมารวมทั้ง pipeline IT 06016422 ที่ตรวจไว้คืออินเทอร์เน็ตของสรรพสิ่ง IT.pdf PDF35/book30 และ42/book37 ไม่แก้ซ้ำโดยดู filename

## การยืนยันและตัวหาร

| รายการ | ผล | ความหมาย / ข้อจำกัด |
|---|---|---|
| unit | exit 0 · 126 tests | [คำสั่งและผลดิบ](checks_release/checks.json) |
| schema | exit 0 · ดู raw counts | [คำสั่งและผลดิบ](checks_release/checks.json) |
| frontend | exit 0 · ดู raw counts | [คำสั่งและผลดิบ](checks_release/checks.json) |
| gold | exit 0 · ดู raw counts | [คำสั่งและผลดิบ](checks_release/checks.json) |
| old2560 | exit 0 · ดู raw counts | [คำสั่งและผลดิบ](checks_release/checks.json) |
| provenance | exit 0 · ดู raw counts | [คำสั่งและผลดิบ](checks_release/checks.json) |
| version_sets | exit 0 · ดู raw counts | [คำสั่งและผลดิบ](checks_release/checks.json) |
| regulation reference API+/ask | 39/39 คู่คำถาม | 7 source-reviewed references; ไม่ใช่ full graduation accuracy |
| frozen historical regression | 171/180 requests, 3 runs | 60 unique cases ของ current5profiles; 3 unique failures ไม่แก้ labels |

frozen failures: DSBA-2565-coop/H07, DSBA-2565-no-coop/H07, DSBA-2565-no-coop/H08

failure มาจากเฉลย internal placeholder identifiers ไม่ตรง schema รุ่นปัจจุบัน เก็บ failures ให้ตรวจ ไม่แก้ gold เพื่อให้ผ่าน ชุดนี้ DB-derived และเคยใช้ debug แล้ว ไม่ใช่ independent held-out อิสระ อีก 9 catalogs ไม่มี frozen set รวม old6profiles/legacy/BITcurrent2 ยังไม่ประเมิน final independent coverage มี expected-abstain เพียง 2 ข้อต่อ profile จึงเป็นหลักฐานอ่อน ไม่เท่ากับ book-wide absence precision/recall

OCR CER/WER: ใช้ได้เฉพาะ transcription ที่เป็นอิสระ Field extraction correctness/completeness แยกจาก retrieval/answer/citation scores ผลรวม regression ไม่ใช่ full-book field accuracy; independent end-to-end accuracy/citation coverage ทุกหลักสูตรยัง n/a

## เวลา

| เงื่อนไข | n | median | p95 | ข้อจำกัด |
|---|---|---|---|---|
| gold structured SQL, cache group 0 | 52 | 470.38 ms | 538.94 ms | L3/L4 ยากและ generation ยังไม่วัด |
| real UI unknown Qwen | 1 | request 11,892 ms / server 11,886 ms | n/a | ไม่ควบคุม warm/cache; >5s จึงไม่อ้าง bonus |
| OCR/parse/index/ingestion แยก stage | n/a | n/a | n/a | งาน preprocessing แยกจาก per-question แต่ยังวัดไม่ครบ |

paired_request_elapsed_ms ใน graduation tests คือ /api/ask + /ask สองคำขอ ไม่ใช้เป็น latency ของคำถามเดียว Cold backend restart ผ่านใน new venv แต่ Ollama ของผู้ใช้ยังทำงานอยู่ ไม่เรียกเป็น cold model generation

## แอปจริงและ README

- UI yearly totals 13/13 และ regulation references 13/13 ในแต่ละ selector/plan; source year/foliopairs/caveats ตรง source-reviewed subset [raw](graduation_ui.json)
- new environment ใช้โค้ด uncommitted ปัจจุบัน new Python venv และ database snapshots 14 catalogs; PDFs เป็น hardlinks ต้นฉบับที่ไม่แก้ ไม่ใช่ freshly reconstructed OCR; qwen service เดิมพร้อมอยู่ [preflight](isolated_preflight_final.json)
- desktop1280/mobile390 ไม่พบ horizontal overflow ในกรณีที่ตรวจ; idle/loading/success/missing-evidence/error ตรวจกับเว็บจริง ดู [UI](isolated_ui.json), [desktop](isolated_desktop.png), [mobile](isolated_mobile.png) และ prior UI suite ที่ frontend dependencies ไม่เปลี่ยน
- new isolated API fact/remove/failure/version counterfactuals 5/5, production hashes ไม่เปลี่ยน [raw](requirement_isolation.json)
- runtime bundle export/restore ตรวจ SHA/integrityและrefuse overwrite ไม่ใช่ GT ไม่รวม PDF/eval labels; local-only artifact ไม่ publish DB
- rollback backup dry run17/17 (13 requirement+4schema) ผ่าน isolated rollback fixtureผ่าน ไม่ได้ rollback liveDBจริง; OneDrive output lock สองครั้งตรวจ partial/stage/backup/live แล้ว resume ที่localTEMP ไม่ reset Git/ไม่ทับข้อมูลโดยเดา
- README หลักเขียนใหม่โดยคงวัตถุประสงค์/รหัสสมาชิกเดิม แยก setup/routine/rebuild ใช้relativelinks/sanitized.env; ไม่แก้ generated Lab09 EVAL หรืองาน ocr_system เดิม

ยังไม่ยืนยัน: fresh OCR/full dependency installation บนเครื่องใหม่, initial model downloads, physical phone/screen reader/OS อื่น, PDF viewer ในแอปที่ก่อนหน้านี้แสดงว่าง, program-metadata citation บางคำถาม (ITold PDF33ยังไม่ยืนยันfolio/source support), full appendix, fresh independent frozen final evaluation/seed stability/complete L1–L4 challenge

## Rubric และงานถัดไป

[requirements → implementation → evidence → gap](REQUIREMENTS.md) ยืนยัน P2 weights20/20/20/30/10, accuracy bandsตามsourceและขอบที่ไม่ชัด โบนัสรวม+10 ไม่คิดคะแนนเอง มีL1/L2 subsetsกับold/new code comparison บางส่วน L3 accelerated/graduationcheckและL4 unavailable sourcesยังn/a

ขั้นถัดไป: source-review program summary citationsและภาคผนวกที่กำหนดgraduation/prerequisites ทั้ง7booksทีละbatch → independentGT/questionmatrix → freezeheldoutที่ไม่เคยdebug → วัด retrieval/answer/completeness/citation/abstentionและcold/warmhard-questionlatencyแยกระดับ ห้ามใช้DB-derivedlabelsแทนsource GT

slides/presentation PDF/narrated video deferred ไม่มีcommit/push/merge main. ตามประกาศล่าสุดที่ผู้ใช้แจ้ง วันที่12ตุลาคมเป็นวันที่เสนอมีเงื่อนไขไม่ยืนยัน. Memoryเดียวคือ [docs/PROGRESS.md](../../PROGRESS.md)
