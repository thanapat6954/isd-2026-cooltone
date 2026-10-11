# AI fresh reconstruction และขอบเขตส่งต่อ — 11 ตุลาคม 2569

**Mode B สำเร็จเฉพาะ AI 2566 coop academic plan ด้วย raw native PDF extraction + independent visual validation** ไม่ใช่ vision OCR accuracy improvement และยังไม่ใช่ full replacement ของ 14 catalogs Mode A ชุดเดิมและฐานข้อมูลจริงไม่ถูกเขียนทับ

## Build scope และ capabilities

| ชุด | ข้อมูลที่สร้างได้จริง | API capabilities / ข้อจำกัด |
|---|---|---|
| Bundled Mode A | reviewed snapshots 13 profiles + legacy; PDF 7 เล่ม | เปิดเว็บเดิมได้; broader source gaps ยังอยู่ ไม่มี fresh reconstruction claim |
| Fresh raw vision OCR AI23–26 | 40 printed plan rows/41 normalized options; มี defects | reject; ไม่ใช่ usable reconstruction |
| Fresh raw native AI23–26 | source code/name/credits/alternatives/placeholder/year/term/PDF+printed pages จาก source table cells | `academic_plan`, `plan_course_facts`; catalog/descriptions/rules/prerequisites/other profiles/legacy ไม่รองรับ |
| Fresh full-PDF native corpus/catalog candidates | 346 source pages, catalog candidates และ fragments รายหน้า, literal prerequisites, literal rule-heading pages | diagnostic staged SQLite; ยังไม่รับรอง catalog completeness หรือ program-rule interpretation จึง activate ไม่ได้ |
| Reviewed ingestion | corrections ที่ source-approved เมื่อ hash/association ตรง | ต้องเปิดเผยไฟล์/รายการแก้; ไม่เรียกว่า raw หรือ OCR improvement; raw outputs เก็บไว้ |

Full gate เดิมมี scope mismatch เพราะ plan-only extraction ไม่สร้าง descriptions/rules/legacy ตอนนี้แบ่ง contract explicit: full `activate` ยังคงต้องครบ 14 catalogs และ source domains/receipt ครบ; `activate-scoped` รองรับ partial ที่ประกาศ profile/capabilities ชัดเท่านั้น ไม่มี silent subset หรือ bundled fallback

## Inputs และห้าม reuse

| ประเภท | ใช้ใน raw native |
|---|---|
| Source PDFs | สำเนา PDF เดิม hash ตรง bundle; AI SHA256 `268065523712db993eec9699b106cc84c283898cd720b70ed56fe73afe80561f` |
| Code/generic config | PyMuPDF 1.28.2, code geometry/Unicode, source-recorded `PROFILES`, page selection; ไม่อ่าน metadata จาก DB |
| Generated artifacts | PNG/text/native table JSON/prediction/SQLite/manifests สร้างใหม่ใน unique staging |
| Manual source-approved corrections | **0 รายการ** ใน AI raw native; visual validation receipt เป็นการตรวจ ไม่แก้ facts |
| Evaluation | ไม่ใช้ development answers/gold/held-out เป็น build inputs; held-out ไม่เปิดอ่านเพื่อซ่อม |
| Prior DB/OCR/master | ไม่ copy เข้าตัว executor และไม่ใช้เติม fields; isolated source-only entry manifests บันทึกไฟล์ก่อน build |

`source_native.py` อ่าน table geometry จาก `find_tables()` แต่ดึงข้อความตาม PDF character order ด้วย `get_text(...clip=cell)` การใช้ `find_tables().extract()` โดยตรงจัด Thai combining characters ใหม่และทำให้ชื่อผิด จึงไม่ใช้ผลนั้นเป็นชื่อ course

## AI source defects และ root causes

ตรวจ full-page source images PDF23–26/book19–22, original raw OCR/parsed JSON และ staged SQL read-only ไม่มีการซ่อม OCR outputs เก่าทับ

| Defect | จุดเกิด | General fix / ผลตรวจ |
|---|---|---|
| PDF25 free-elective wildcard 8 ตัวกลายเป็น 11 ตัว | OCR; parser เปลี่ยน code เป็น Thai label; SQLite raw_code หาย | native exact 8-character code matching; reject bad lengths/ambiguity; source placeholder เก็บ raw_code ตรง |
| PDF26 language wildcard และ free slot ผิดความยาว/case | OCR + parser association | เก็บตัวอักษร source ตามจริง ไม่ pad/truncate หรือเติมจาก DB |
| PDF26 สอง alternatives ได้ชื่อไทยตัวแรกซ้ำ/English รวม | OCR ทำ second Thai name หาย; parser/converter copy first association | bilingual group boundaries + ordered code/name associations; N names ต้องตรง N codes มิฉะนั้น reject |
| Invented university footer | OCR | native อ่าน source cells เท่านั้น ไม่ ingest outside-table footer; ไม่แก้โดย lookup expected text |
| OCR COOPERPERATIVE typo | OCR | source-native ชื่อจาก PDF; ไม่ใช่ regex dictionary correction หรือ OCR improvement |
| Source plan English พิมพ์ INTELLIGIENCE | ต้นฉบับ plan | เก็บตาม source ไม่ dictionary-correct; catalog appendix อาจสะกดต่าง ต้องไม่ overwrite plan silently |
| Catalog header สิ้นหน้า/English+prerequisite อยู่หน้าถัดไป | native parser รุ่นแรก | flattened page-tagged source lines; credits/code same physical line; stop ก่อน next course marker |
| Catalog description สุดท้ายรับ appendix heading มาด้วย | native boundary parser รุ่นแรก | stop ที่ generic section/appendix/group headings; เก็บ full source fragments แยกรายหน้า |

Plan printed totals ทั้ง 8 terms ตรง source: 15/19/18/19/18/13/12/6 นับแถว “หรือ” ครั้งเดียว ไม่รวม mutually exclusive alternatives Twice Native→SQLite comparison ตรวจทุก code/name/credit/hour/year/term/page/alternative index ทั้ง 41 options แผนไม่สร้าง prerequisite edges; absent prerequisite ไม่ตีความเป็น none

## Reconstruction coverage ราย profile

Bounded native attempt หนึ่งรอบทุก profile เก็บ raw failures ไม่ rerun configuration เดิมเพื่อให้ดูผ่าน Source-only candidate `20261010T221143-13ab50f151` ไม่ถูก activate

| Profile | Native plan reconstruction | Validation / activation |
|---|---|---|
| AI 2566 coop (`ai`) | 4/4 source pages; 40 printed rows → 41 options/34 projected course rows/7 placeholders/8 terms | AI-only source review + scoped activation/recovery ผ่านในสำเนาแยก |
| DSBA 2565 coop | fail native; PUA Thai font + physical 7-column table | rejected |
| DSBA 2565 no-coop | fail native; PUA Thai font + physical 7-column table | rejected |
| DSBA 2560 coop | blocked: required page selection ยังไม่ source-reviewed | ไม่เริ่ม extraction; ไม่เรียก OCR failure |
| DSBA 2560 no-coop | blocked page selection | ไม่เริ่ม extraction |
| IT 2565 coop | fail native; PUA Thai font + physical 7-column table | rejected |
| IT 2565 no-coop | fail native; PUA Thai font + physical 7-column table | rejected |
| IT 2560 coop | blocked page selection | ไม่เริ่ม extraction |
| IT 2560 no-coop | blocked page selection | ไม่เริ่ม extraction |
| BIT 2565 coop | fail native; PUA Thai font + physical 7-column table | rejected |
| BIT 2565 no-coop | fail native; PUA Thai font + physical 7-column table | rejected |
| BIT 2560 coop | blocked page selection | ไม่เริ่ม extraction |
| BIT 2560 no-coop | blocked page selection | ไม่เริ่ม extraction |
| legacy | ตรวจ independently read-only; 6,147 extracted records/1,862 distinct codes จาก AI1593/DSBA2270/IT2284 rows | ไม่มี program/version/year/plan columns จึง identity unresolved; ไม่ copy mixed catalog เป็น fresh reconstruction |

7-column geometry และ font mapping เป็นคนละปัญหา ไม่ map PUA เป็น Thai โดยเดา Course facts ห้าม hard-code ไม่ลด completeness gate เพื่อให้ profile อื่นผ่าน

## Catalog และ program rules ที่ขยายจริง

`rebuild --extraction native --source-documents` สร้างใหม่จาก AI PDF ทั้งเล่ม ไม่มี OCR/model calls แล้วนำเข้าตาราง `source_document_page`, `catalog_source_entry`, `catalog_source_fragment`, `program_rule_source` ใน **staged** curriculum SQLite เท่านั้น ไม่เปลี่ยน runtime course facts หรือใช้ JSON overlays

รุ่นแรก 346 pages/41 entries/8 rule heading candidates ใช้ 39.799s มี missing cross-page course และ appended appendix text จึงไม่ certified รุ่นแก้ boundaries fresh candidate `20261010T221154-1e5b98f54a`: 346 pages/43 entries/8 rule candidates, 41.050s; targeted source inspection PDF287–288 (description continuation),292 (wrapped prerequisites),303–304 (cross-page cooperative heading),305 (appendix stop),68/book64 (graduation reference)

Catalog record สหกิจมีชื่อ English ใน appendix ตรงหน้าถัดไป จึงต้องเก็บ source fragments ทั้ง header และ continuation ไม่อ้าง PDF header หน้าเดียวว่า support ทุก field Rule page68 บอกให้ดูข้อบังคับภาคผนวกและ PLOs ไม่ใช่การประเมินสิทธิจบรายบุคคล Rule candidates รวม TOC ด้วย สถานะยัง literal/unreviewed; ไม่สร้าง graduation/registration claims

**ยังขาด** source validation ของ catalog ทุก course/หมวดวิชา (รวม general education), rule clauses/continuations/conditions ทุกข้อ, runtime normalized description/prerequisite/progam-rule schema integration และ identity/scope ของ legacy Full gate reject จริง ไม่ใช่ยอมรับ candidate ด้วย integrity เพียงอย่างเดียว Fresh corpus เป็นความคืบหน้า extraction ไม่ใช่ full PDF reconstruction success

## Activation และ recovery ที่ตรวจจริง

Fresh source-only build ไม่มี DB เดิมได้ usable AI plan SQLite จากนั้น copy candidate แบบ sealed ไป isolated runtime หลัง build เสร็จจึงนำ Mode A baseline 14 DB มาใช้เป็น replacement test

- First install ลง AI declared scope โดยไม่มี previous DB ผ่าน
- Full activation ปฏิเสธ scoped AI; scoped activation over usable14 ผ่าน, backup ทั้งชุดด้วย SQLite API
- 16 real HTTP responses: 4 development questions × `/api/ask`/`/ask` × start/restart; 12 supported plan/name requests และ 4 unsupported-description refusals ตรวจ actual answers/SQL/source
- Source-info/PNG PDF25/book21 และ26/book22 ตรง source PDF; API-derived references ไม่ถือเป็น real browser navigation
- Active consumer lock reject; missing OCR model/one-page partial build ไม่เปลี่ยน pointer; activation after-pointer injected failure คืน pointer ทั้งชุด ไม่มี mixed builds
- Rollback คืน usable14 และ isolated user-added note; old DB hashes ไม่เปลี่ยน (เทียบหลังใส่ test note) Start/stop/restart หลัง activation/recovery ผ่าน หยุดเฉพาะ owned backend
- Separate LIVE8003/8004/8010 และ shared11434 ไม่ถูกหยุด/ใช้เป็น handoff evidence

รอบวัด lifecycle แรก: scoped activate4.343s/start4.780s/restart3.363s/recovered14start3.816s Failed OCR missing-model3.407s และ incomplete native4.189s นับเป็น rejection evidence ไม่ใช่ extraction success

## หลักฐานและข้อจำกัด

Raw evidence อยู่ `docs/results/fresh_ai_scope_20261011/`: entry manifests, fresh build/hash manifests, source PNGs, per-page native cells, SQLite chain reports, per-profile coverage, API/health/source responses และ lifecycle failures/recovery เอกสาร delivery ระบุ inventory ของหลักฐานที่รวมใน ZIP

Mode A v4 actualZIP measured venv15.72s/packages19.99s/restore16.72s/model download62.31s/start5.41s/restart4.39s; ไม่ใช้ warm structured-query latency แทน OCR timing เครื่อง i7-13620H/RAM15.7GiB/RTX5050 Laptop, Windows11/Python3.11.9/PyMuPDF1.28.2 Native plan render200DPI; corpus evidence render150DPI

Browser policy บล็อก real UI/citation click รอบใหม่ ไม่ bypass ผ่าน surface/port อื่น Source PNG inspection และ API success ไม่ใช่ browser pass Independent held-out ยังไม่เปิดอ่าน/ไม่ repair จาก held-out answers Regression/gold counts เป็น development compatibility ไม่ใช่ reconstruction accuracy


## ผล final delivery ที่ตรวจเพิ่ม

Actual ZIP v5 มี code inventory1547ก่อนเพิ่ม final documentation/evidence, archive/source manifest hashes valid Data ZIP เดิม SHA256 `39018bfa21a7a36ea4f92fde8eb4db5d671745679dddc90dead38d8f23ec9f07` ไม่เปลี่ยน v4 ถูกเก็บไว้

Mode A v5: freshvenv19.17s/packages uncached24.00s/restore27.15s/empty-store Qwen download93.93s/start5.74s/restart4.32s; actual APIทั้งสอง routes/source-info/PNG/DBhashunchanged, ownedservicesstopped

Mode B actualZIP source-only folder + ownNEWvenv15.839s/dependencies19.824s: native2.975s/SQLite0.899s (wholeCLI12.496s รวม executorcopy/hashing/validation); candidate `20261010T222903-4bce9339f4` →41options/DBSHA `1b0b01f08e54134ad43571ef9f883e64005fa5c8fb2252c11c346aa344a7c448`, independent-source-imagehashesตรงทุกหน้า + manual receipt → declaredreadytrue → firstinstall1DB ไม่มี previousDB คำสั่งแรก exit1 เพราะไม่มีreceiptตาม safeguard ไม่ใช่ extractionfailure

Delivered runtime lifecycle final: sealed fresh nativeAI `20261010T221835-a4869069d3` activate over usable14 7.708s/start5.331s/restart5.022s/recovered14start4.486s;16actualHTTP supported12/refusal4, realSQL/citations, consumerlock/fullscope rejection, partialbuild keeps pointer, injectedafterpointerfailure recovery, usernote backup/restore/oldhashunchanged; ownedbackend8005stopped

Missing OCR model test reject ที่ model inventory/preflight **ก่อน OCR** (`Installed OCR model digest unavailable`), OCRfalse ไม่มี extractioncheckpoint; ไม่เรียก reconstructionattemptผ่าน Missing answering model/file มี Thai instructions และrestore originalsourcehashแล้ว OccupiedLIVE8003 rejectwrongrootโดยไม่หยุด PID33952; otherLIVE8004PID19684/8010PID5076/shared11434PID12268คงอยู่

Current checks343unit/30schema/7frontend/70gold (14profiles×5)/65old2560/14provenance/6version checks exit0/dependencyguardtrue; readonlyaudit14/FAIL1372/incomplete51 ยังเปิด ไม่ใช้ regressioncountsเป็นsourceaccuracy Independentheldoutunread/browserclickpolicyblocked

Final full-corpus candidate `20261010T221530-b3af39f6d4`:346pages/43catalogcandidates/53fragments/8ruleheading candidates, nativeplan2.019s/SQLite0.638s/corpus39.992s; fragmentsรวมheaderและcontinuationรายหน้า ยัง source-domain incomplete และfull14reject ไม่มี activation Source corpus/code/config hashทุกชุดเก็บแยก ไม่ reuse failedoutputs

Raw finalproof `docs/results/fresh_ai_scope_20261011/{submitted-v5,pdfonly-zip-build.json,pdfonly-zip-candidate,lifecycle-final,catalog-fragments-final,all-profile-coverage.json,missing-ocr-model-final,checks-final}` ZIP finalเพิ่มเฉพาะdocs/evidenceหลังrehearsal ต้องมีcomparison non-docchanges0และdatahashunchangedในdelivery VERIFICATION
