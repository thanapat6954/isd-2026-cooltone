# การสร้างใหม่จาก font/table และ BIT 2565 — 11 ตุลาคม 2569

## ขอบเขตที่ยืนยัน

ทำงานบน `week11_thanapat` ใน repository `ocr_final/` เท่านั้น ไม่แก้ sibling LIVE ไม่ commit/push/merge ฐานข้อมูลใช้งานเดิม 14 ชุดและ ZIP v5 คงเดิม Full Mode B ยังไม่สำเร็จ

| Profile | Fresh reconstruction ใน batch นี้ | Activation |
|---|---|---|
| AI 2566 coop | raw native 4 หน้า /41 options; DB hash เหมือน source-verified build เดิม; declared validation ผ่าน | หลักฐาน AI activation เดิมแยกไว้ ไม่อ้างเป็น BIT pass |
| BIT 2565 no-coop | reviewed font encoding; PDF26–30/book21–25;43 rows/8 terms | first install + replacement/recovery ในสำเนาแยกผ่าน |
| BIT 2565 coop | reviewed font encoding; PDF31–35/book26–30;43 rows/8 terms (แถวสหกิจ 2 options นับ6ครั้งเดียว) | first install + replacement/recovery ในสำเนาแยกผ่าน |
| DSBA 2565 no-coop | 5/7 plan pages extracted; PDF27–28 reject shared-placeholder/multiple bilingual names | ไม่ activate |
| DSBA 2565 coop | 5/7 pages; PDF34–35 reject layout แบบเดียวกัน | ไม่ activate |
| IT 2565 no-coop | 4/7 pages; PDF34–35 specialization bundles ไม่มี OR และ PDF36 continuation ไม่มี header | ไม่ activate |
| IT 2565 coop | 5/7 pages; PDF41–42 specialization bundles | ไม่ activate |
| DSBA 2560 no-coop | ยัง blocked source page-selection review | ไม่ activate |
| DSBA 2560 coop | ยัง blocked source page-selection review | ไม่ activate |
| IT 2560 no-coop | ยัง blocked source page-selection review | ไม่ activate |
| IT 2560 coop | ยัง blocked source page-selection review | ไม่ activate |
| BIT 2560 no-coop | ยัง blocked source page-selection review | ไม่ activate |
| BIT 2560 coop | ยัง blocked source page-selection review | ไม่ activate |
| legacy mixed catalog | ยังไม่มี independently resolved curriculum/version/plan contract | ไม่ activate |

แต่ละ declared build เป็น academic-plan-only รองรับแผน/ชื่อ/หน่วยกิตที่อยู่ในแผน ไม่ใช่ catalog ทั้งเล่ม กฎจบการศึกษาและ prerequisites ยังไม่ทราบเมื่อไม่มีหลักฐานในตาราง ไม่อนุมานสิทธิลงทะเบียน `activate` full gate ยังคงบังคับครบ14 catalogs และ source-validated catalog/rules; ใช้ `activate-scoped` เฉพาะขอบเขตที่ประกาศ

## สาเหตุและ general fixes

PDF ล่าสุด DSBA/IT/BIT มี private-use Thai glyphs และ merged cells ที่ตรวจได้7 physical columns แม้มี3 semantic columns คง raw text เดิมไว้ใน `page-*.txt` Raw native route ยัง reject PUA ไม่เดา Thai

`source_native.py` อ่านขอบเขต semantic columns จาก header/cell geometry และอ่านอักขระตามลำดับเดิม ไม่ใช้รายชื่อวิชาหรือคำตอบคาดหวัง รองรับ header credit ที่แยก2บรรทัด และ total ที่ mergeข้ามคอลัมน์ ระหว่าง source review พบ group heading ปนชื่อวิชาและ connector “หรือ” ในชื่อ elective ถูกลบ: แยก heading ที่พิมพ์ชัดเป็น category และรักษา connector ภายในชื่อเดียวกัน ต้นฉบับ code case/จำนวน8อักขระยังคงเดิม

Fresh parser เรียก conversion แบบ `source_only=True` จึงไม่ใช้ development code/name lookup ของ IT specialization slots ที่มีอยู่ใน converter เดิม Fresh IT ต้องได้ความสัมพันธ์จาก PDF ก่อน; ไม่เติม mapping เพื่อให้ totals ผ่าน

## Reviewed encoding ที่ใช้จริง

Input เดียวที่ผ่านการ review นอกเหนือจาก page selection คือ `data/source_reviews/font_encoding/thsarabun-source-glyphs-20261011.json` เป็น font encoding เท่านั้น **ไม่มี course facts, course corrections, working-DB metadata, curated master หรือ evaluation answers** เลือก `--mode reviewed --extraction native --font-review ...` อย่าง explicit Parser ไม่อ่าน `*-plan-corrections.json` เมื่อเลือกเส้นทางนี้

ตรวจ glyph atlases จาก embedded THSarabunPSK regular/bold ทั้ง6 font ของ3PDF เทียบกับ standard glyph ใน fontเดียวกันและรูปร่าง Thai เห็นจริง FontFile stream hash ต้องตรงทุกครั้ง; Latin subset ที่ชื่อ family เหมือนกันไม่ใช่ Thai subset และไม่มี mapping จะ reject ไม่ fallback

| Private-use glyph | Unicode ที่ตรวจจากภาพ |
|---|---|
| F701/F702/F703 | 0E34/0E35/0E36 |
| F705/F70A/F713 | 0E48 |
| F706/F70B | 0E49 |
| F70C | 0E4A |
| F709/F70E | 0E4C |
| F710/F712 | 0E31/0E47 |

mapping ผูก exact font hashes ไม่ใช่ replacement dictionary ของชื่อวิชา `extract_font()` อาจคืน repaired buffer หลัง rendering จึงตรวจ immutable PDF FontFile stream แทน ข้อมูล raw/normalized และ review JSON/hash เก็บพร้อม build เป็น **reviewed native ingestion ไม่ใช่ raw automatic reconstruction หรือ OCR accuracy improvement** Runtime ใช้ facts ที่นำเข้า SQLite ไม่มี JSON factual overlay หลัง SQL

หลักฐาน: [font inventory](results/font_table_rebuild_20261011/font-inventory.json), ภาพ `*-glyphs.png` และ reproducible `font_audit.py` ในโฟลเดอร์เดียวกัน Diagnostic ใช้ fontTools ที่ติดตั้งบนเครื่องตรวจ; instructor runtime/build ใช้ PyMuPDF ตาม requirements เท่านั้น ไม่ต้องใช้ fontTools

## Fresh source และ validation

Source-only executor: `TEMP/curriculum-font-reviewed-sourceonly-t_wqdiac/ocr_final` มี code + supplied PDFs + page-selection + font review เท่านั้น ไม่มี previous DB/OCR/master/answers Candidates แต่ละ dependency change สร้างใหม่ ไม่ reuse failed outputs

- First six-profile attempt `20261010T225140-4a6a85e873` reject DSBA/IT และไม่เปลี่ยน active set; BIT parsed แต่ requested set ไม่ครบ ห้ามลดขอบเขต candidate เดิมเงียบ ๆ
- Intermediate BIT build `20261010T225323-f46c6d4aa6` เก็บไว้ก่อนแก้ heading/connector จึงไม่ใช่ final source-fidelity result
- Final BIT candidate `20261010T225425-c5f37fcdba`: cover/ทุกแถว PDF26–35 ตรวจภาพจริง รักษา name associations, codes, credits/hour alternatives, plan headings และ book-page citations `validate_sql_chain` ตรวจ source→SQLite43rowsต่อแผน exact ฟิลด์ที่กำหนด ไม่มี prerequisite edges
- no-coop SHA256 `37994352ec60322fc693efbc6c89d89ffccd4e1a0677d8148113775536ba346a`; coop `5d3f6ce2dc4958f74fd94f0cec9ce31613efceb602a6423d4f2bdd6c3d5579f0`
- Declared validation ready=true หลัง independent visual receipt; firstinstall2DB เมื่อไม่มีpreviousDBผ่าน ไม่ certify away pending pages/errors
- AI fresh raw candidate `20261010T225516-1b07bb80d3`: corrections0/4pages/DB SHA `1b0b01f08e54134ad43571ef9f883e64005fa5c8fb2252c11c346aa344a7c448`; declared validation ผ่าน Original vision OCR defects ยังเป็น rejected attempts ไม่มี unchanged OCR retry

## Activation/API/recovery

ทดสอบ destructive/failure paths ใน `TEMP/curriculum-bit-scope-runtime-sfm37c85/ocr_final` เท่านั้น own newvenv15.154s/uncached dependencies22.402s DB14baseline คัดลอก **หลัง** fresh candidate สร้าง/ตรวจแล้ว ใช้ baseline เพื่อทดสอบ replacement ไม่เป็น build input

[lifecycle-complete/verification.json](results/font_table_rebuild_20261011/lifecycle-complete/verification.json) completed=true:

- full-activate ของpartial reject; explicit scoped activationเปลี่ยน14→2 พร้อมbackup/hash/integrity/user-added table; immutable build instance suffix `-lifecycle-final` เป็น sealed candidate copy ไม่สร้าง facts ใหม่
-40HTTP:2plans×5questions×2routes×2cycles;32supported/8unsupported-description refusals ตรวจ actual SQLrows/APIanswers/frontend citations; explicit plan selection ถูกต้อง Year4no-coop24/coop21โดยไม่นับ6credit alternativesซ้ำ
- source-info/PNG PDF28/30/33/35 ยืนยันbook page23/25/28/30 และ source hash; browser policy ยัง blocked จึงไม่ใช่ browser-click/navigation pass
- active consumer lock reject; missing OCR modelก่อนextractionและpartial1page build failเก็บpointerเดิม ไม่เติมจากbundle
- injected after-pointerfailureคืนwholepointer; shutdown/restartหลังactivationผ่าน; rollbackคืน14DBพร้อมusernote; alloldfilehashesunchangedหลังisolatednote; recovered14startupผ่านและownedbackendหยุดแล้ว

Test harness รอบแรกใช้ response-field assertionไม่ตรงAPI และรอบถัดมี reused probe paths/incorrect recovery-count assertion เก็บทุกfailure/log พร้อมrecoveryไว้ `lifecycle*` ผล successful ใช้ **lifecycle-complete เท่านั้น** ไม่ตีความ harnessfailเป็น OCR defect และไม่ลบหลักฐาน

## ผลวัดและข้อจำกัด

Windows11/Python3.11.9/PowerShell7.6.5/PyMuPDF1.28.2; i7-13620H/RAM15.7GiB/RTX5050Laptop; shared Ollama0.19.7/qwen3:4b ใช้เฉพาะanswering tests Native buildไม่ใช้model; ไม่ใช่minimumhardware และไม่ได้วัดOCR-timeจากwarmSQL

| Stage ที่วัด | seconds |
|---|---:|
| BIT no-coop native/render/encoding/table | 8.838 |
| no-coop normalize/SQLite | 0.621 |
| BIT coop native/render/encoding/table | 8.766 |
| coop normalize/SQLite | 0.540 |
| activate/start/restart/recovered14start | 7.077/4.698/3.849/3.969 |
| missingmodel reject/partialnative reject | 6.644/10.120 |

Manual glyph/field-review timeไม่ได้วัดจึงไม่รวมเป็นautomatic build time ยังไม่ได้สร้างfullcatalog/programrules/legacy และไม่ใช่ independent held-out evaluation

Regression:345unit/30schema/7frontend/70developmentgold(14×5)/65old2560/14provenance/6versionchecksผ่าน dependencyguard=true ขณะจบ checks ไม่มีการเปลี่ยนfacts Audit14datasetsยังFAIL1372/incomplete51/reference/prerequisite coverage gaps; exit1 **ไม่ใช่ sourceaccuracy pass** หลังchecksแก้เฉพาะpackage evidence inclusion/docs ไม่เปลี่ยนruntime/extraction code

## ขั้นต่อไป

DSBA: source oneplaceholder/multiple-name cellต้องเก็บpaired namesและshared hour alternativesโดยไม่เพิ่ม3slotหรือเดาว่าpatternใดเป็นของชื่อใด IT: อ่านspecialization bundles/selection scopeจากsource และ continuation cell/pages; freshconversionไม่ใช้hardcodeddevelopmentmapping Old2560: review cover/planpage selectionsจริง Legacy: resolve document corpus/program-version-plan independently; ห้ามcopy mixedcatalog ตั้งidentityเอง ModeA14snapshotและoldZIPยังใช้ได้ระหว่างทำงานนี้

## Actual ZIP v6

Storage เคยเต็มทำให้ download และ copy candidate installation หยุดก่อน active pointer ผู้ใช้เพิ่มพื้นที่ (ตรวจ53.27GB) ไม่มีการลบ cache ที่ automatic approval ปฏิเสธ ไม่แตะ DB/PDF เดิม Resume เฉพาะขั้นที่ไม่เสร็จ และตรวจ code hashes ตรง

- [Mode A actual ZIP](results/font_table_rebuild_20261011/submitted-v6/rehearsal.json): ownvenv16.00s/uncachedpackages20.46s/restore12.98s/resumeddownload39.99s/start6.57s/restart5.33s; ทั้งสอง API/real answers/citations/sourcePNG ผ่าน DBunchanged/servicesoff CLI list/pull idempotence ผ่าน [package-state](results/font_table_rebuild_20261011/submitted-v6/package-state.json)
- [Source-only actual ZIP](results/font_table_rebuild_20261011/pdfonly-v6/verification.json): initialDBcount0/code+BITPDF+page-selection+fontencodingreview เท่านั้น ownvenv14.601s/deps26.038s native9.946/14.369s SQLite1.154/1.571s; freshbuild34.818s initialexit1เพราะยังไม่มี independent receipt ไม่ใช่ extraction failure candidate20261010T230913-bd70f012c9/43rows36courses8termsต่อแผน exact DBhashesตรง Source images12cover/pages hashตรงภาพที่ตรวจจริง; receiptเป็นvalidationไม่แก้ facts
- Storage failure เก็บ partialinstalleddirectory และ first-activation.json ไว้ ไม่มีpointer/previousDB; activationครั้งถัดใช้ sealedcandidate activationidentity `-storage-resume` facts/source/dependencyเหมือนเดิม ไม่ rerun extraction [firstinstall-verified](results/font_table_rebuild_20261011/pdfonly-v6/firstinstall-verified/verification.json) completed=true/8HTTPทั้งสองแผน/routes/startrestart และ2DB ก่อนนั้น harnesscapturePIPE timeoutหลังsuccessfulactivation แก้ใช้filelogs/หยุดเฉพาะownedbackend/verify samebuild ไม่ลบfailedproof
- [Actual ZIP replacement lifecycle](results/font_table_rebuild_20261011/actual-zip-lifecycle/verification.json) completed=true:40HTTP/fullgate/consumer/missingmodel/partialbuildreject/wholepointerfailure recovery/usernote/rollback14/oldhashunchanged/startshutdownrestart ผ่าน activated3.817s/start5.680s/restart5.137s/recovered14start5.181s baselineDBใช้เฉพาะlifecycleหลังsourceconstructionเสร็จ ไม่มีbaseline factsเป็นbuildinput

ทั้งหมดเป็น declared academic-plan-only สอง BIT2565 profiles/source-reviewed font decoding ไม่ใช่ raw vision OCR/full catalogs/rules/legacy success Browser policyยัง blocked ไม่มีbypass/newclickpass Independentheldoutไม่ใช้ซ่อม ทำ final archiveเฉพาะdocs/evidenceพร้อม non-documentation comparison ก่อนส่ง

Actual ZIP error checks: [launcher](results/font_table_rebuild_20261011/actual-zip-launcher-verified/verification.json) passed/alternate8006/idempotentstart/normalstop/occupiedLIVE8003preservedและDBhashunchanged; oldharness Englishmessage assertion failureเก็บไว้ ไม่ใช่launcherfailure [missingmodel](results/font_table_rebuild_20261011/actual-zip-missing-model.json) passed/real404/modelsunchanged/API gapตอบตามSQLite และ [missingPDF](results/font_table_rebuild_20261011/actual-zip-missing-file/verification.json) rejectพร้อมThaiinstructions/restore exactPDFhash ไม่มีownedlistenersค้าง
