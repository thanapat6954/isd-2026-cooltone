# BIT: การตรวจ crop และ raw extraction

ผลนี้เป็น development audit ไม่ใช่ held-out evaluation หรือการยืนยันทั้งเล่ม ใช้ curriculum-audit และตรวจภาพ source จริงโดย PDF skill; original PDF/OCR/working DB ไม่เปลี่ยน

## ขอบเขตและผล

| หน้า PDF / ในเล่ม | ก่อน | หลัง bounded experiment | ยังผิด / สถานะ |
|---|---|---|---|
| 26 / 21, BIT-2565 ไม่สหกิจศึกษา Y1S1 | raw4รหัส → parser4แถว → SQLite4แถว/11หน่วยกิต เทียบ source7แถว/18 | crop240,675,1570,1900 ที่200DPI: raw7รหัส/7credit patterns → parser7แถว → newSQLite7แถว/18 | ชื่อ96644042ใช้ “ด้วย” แทน “อย่าง”, plan headingหาย, footerนอกsourceถูกสร้าง; ไม่ใช่ full fidelity |
| 257 / 252, คำอธิบายรายวิชา | English06036148ผิด/overlapซ้ำ | singlecrop และ luminance170: overlapซ้ำหาย; 9/10 targeted fields (2courses×5fields) | COOPERERATIVE ยังผิดจาก COOPERATIVE และมี footerแต่งเติม ไม่ promote production |
| 93 / 88, หมวด7 | instruction-only ไม่ได้เนื้อหา | crop400,910,1500,1580: ได้5เงื่อนไขจบที่มีในsource | ข้อ26ถูกอ่านเป็น25 และข้อถัดไปเลื่อน1; scopeเฉพาะsection ไม่ใช่ครบหน้า; ยังไม่ ingest |

Manifestรวม317physicalpages/include15/skip0/unreviewed302 ไม่เปลี่ยน การทดลองนี้มี3uniquepagesแต่คนละ renderer/config ไม่ mergeเป็น reconstructionเดียว

## ต้นเหตุและการแก้ implementation

1. PDF26สูญรหัสตั้งแต่rawOCR: full sourceแสดง06036118/96641003/96644042 แต่ rawเดิมจับเป็นrowspanของแถวก่อนหน้า ไม่มีรหัสนั้นจริง Parserไม่ได้เป็นต้นเหตุของ3รหัสหาย
2. เพิ่ม optional crop/ink-threshold ที่เก็บ fullPNG, segmentPNG, originalcoordinates และ rendererhash; defaultsเดิมยังอยู่ ห้ามreuseincompatibleconfig
3. Qwen JSON invents “ไม่มี” ทั้งที่ studytableไม่แสดงprerequisites: generic table guardเก็บunknownแทน และกู้ malformed Englishจากraw rowเท่านั้น (ไม่ใช้gold/DB/nextcourse) ผลใหม่96644007เป็น FOUNDATION ENGLISH 1 ส่วนชื่อ96644042ยังเก็บOCRerrorตามจริง
4. เพิ่ม empty/non-Thai/instructionecho diagnostics; ไม่อ้างว่า flagผ่าน = sourcecorrect และยังตรวจภาพจริงจับspelling/footer/numberingผิดที่flagตรวจไม่ได้

Categories/typeจาก Qwen ยังไม่ได้ยืนยันกับหน้านี้ ไม่สรุปเป็นsourceverified. Prerequisiteในstudytableไม่ระบุ ไม่ใช่หลักฐานว่าหนังสือไม่มีเงื่อนไข ต้องตรวจคำอธิบายแยก

## actual API / UI

6uniquequestions×2routes=12HTTPrequests: substantivecorrect6, partial2, justifiedDBgap2, incorrect2, technical0. เป็นคำถามdevelopmentที่เปิดเผย ไม่ใช่ generalaccuracy/SLA. Raw[API/SQL/rows/timing](results/bit_manifest_controls_20261010/crop26-api-results.json) และ [source observations](results/bit_manifest_controls_20261010/crop-source-review.json)

- ถาม “วิชา06036118ชื่ออะไรและมีกี่หน่วยกิต”: จริงตอบ “การแก้ปัญหาทางด้านเทคโนโลยีสารสนเทศ (PROBLEM SOLVING IN INFORMATION TECHNOLOGY),3หน่วยกิต,L-P-S2-2-5” source26รองรับ
- ถาม “วิชา96641003ชื่ออะไรและมีกี่หน่วยกิต”: จริงตอบ “กีฬาและนันทนาการ (SPORTS AND RECREATIONAL ACTIVITIES),1หน่วยกิต,L-P-S0-3-2” source26รองรับ
- ถามรายวิชาและยอดรวมY1S1: จริงตอบ18และ7codes=credits แต่ไม่แสดงชื่อวิชา จัดpartialไม่ใช่complete
- ถาม96644042: DB/APIยังใช้ “การสื่อสารและการนำเสนอด้วยมืออาชีพ” จัดincorrectแม้เครดิตถูก/HTTP200/citationหน้าเดียวกัน
- ถามprerequisite06036118: จริงแจ้งว่าข้อมูลในDBยังไม่ยืนยัน ไม่รับรองการลงทะเบียน ไม่มีการเติมNoneจากsourceที่ไม่ระบุ

จริงใช้frontendในisolatedapp ส่งBIT/latest/no-coop เปิดcitationลิงก์ PDF26/book21 และเห็นตารางในviewer; [DOM](results/bit_manifest_controls_20261010/crop26-ui-answer.txt), [answer screenshot](results/bit_manifest_controls_20261010/crop26-ui-answer.png), [source screenshot](results/bit_manifest_controls_20261010/crop26-ui-source.png). Full-page source screenshotล้มเหลวแต่viewport capture/scrollเห็นเนื้อหาจริง; ไม่ใช้HTTP200แทนvisible proof

FreshpartialDBใช้programmetadataจากworkingDBแบบread-onlyเท่านั้น ไม่ใช่freshwholeprogram. Names/codes/creditsจากrawOCR; sourcefoliomappingจากverifiedmanifest. DBintegrityokและworkinghashunchanged. ไม่คัดลอกdescription/prerequisiteจากรายวิชาอื่นหรือlabels

## หลักฐาน / ทำซ้ำ

- [raw26/fullPNG/cropPNG/config](results/bit_manifest_controls_20261010/tablecrop26/manifest-extraction.json)
- [ก่อน parserguard](results/bit_manifest_controls_20261010/crop26-parse-before/parse-build.json) / [หลังguard/newDB](results/bit_manifest_controls_20261010/crop26-parse-fixed/parse-build.json)
- [257singlecrop](results/bit_manifest_controls_20261010/singlecrop257/manifest-extraction.json) / [ink170](results/bit_manifest_controls_20261010/ink257/manifest-extraction.json)
- [93crop](results/bit_manifest_controls_20261010/graduationcrop93/manifest-extraction.json)
- read-only audit_all:16datasets,FAIL1372,incomplete4881,missingcurricula[]; existingcoveragefindingsไม่ได้หายไปเพราะcropfix. [reports](results/bit_manifest_controls_20261010/crop-audit/)

จากrepo ocr_final ใช้LIVEvenv Python `-m scripts.parse_raw_plan_job --raw-job <savedraw> --source-pdf <originalPDF> --metadata-db <readonlyworkingDB> --output <newisolatedoutput> --plan no_coop`; ไม่ใช้evaluationinputs. `-m scripts.probe_partial_plan --database <newpartialDB> --source-pdf <originalPDF> --questions ../docs/results/bit_manifest_controls_20261010/crop26-questions.json --output <newisolatedAPIoutput>` เก็บbackendPIDในJSON ต้องstopเฉพาะownedprocessหลังbrowser

ยังไม่ verified: sourcefulltextCER/WER, categories/type, completeplanheading, all15relevantpages, allprofilefreshbuild, untouchedheldout, difficultLLMcold/warmtiming, realfirstmachineinstall. ไม่เปลี่ยนworkingDBจากrawที่ยังผิด; production correctionต้องมีapprovalแยก

## การต่อ batch / regression

Dependency-locked7jobs exit0/guardtrue:313unit/30schema/7frontend/70gold (14profiles×5)/65oldQA/14provenance/6version sets. [Raw checks](results/bit_manifest_controls_20261010/crop-shared-checks/checks.json) ไม่ใช่sourceaccuracyทั้งเล่มหรือheldoutผลใหม่. Repo/LIVE runnerSHA71413600054a28ccaa9eaedabdafff122898c33526d694485a6cae78b72b734f; parser SHAต่างเพียงexistingcommentที่preserve ไม่ใช้hashเท่ากันเป็นข้ออ้างsourcefidelity

Header-only257 crop250,900,1490,1135 ยังสะกดผิดเดิม [retained attempt](results/bit_manifest_controls_20261010/header257/manifest-extraction.json). หยุดretryunchangedconfig ไม่แก้rawด้วยdictionary/modelknowledge/workinganswer

ต่อfreshincludePDF28/book23 และPDF29/book24:2pages/4semesters/20printedrows (6+6+4+4), totals18/18/12/12. [Independent observations](results/bit_manifest_controls_20261010/plan28-29-source-observations.json), [raw](results/bit_manifest_controls_20261010/plan28-29/manifest-extraction.json). พบwildcard96644xxx→9664xxxx และ two distinct Year4rows merged codecell06036146/96642033. Placeholderไม่malformedแต่codepattern/relationshipผิด. Parsing/buildต่อในisolateddirectory ไม่ใช้observationsเป็นinput; ดูCURRENT checkpointสำหรับผลล่าสุด ไม่อ้างfullreconstructionจาก2pagesนี้

Isolatedbackend36516/port53476 stopped หลังUI; temporarytabs62/63closed. LIVE8000ไม่ได้restartหรือเปลี่ยนDBจากrawที่ผิด

## ปิด defect row association PDF29

ก่อน:Qwenอ่านcodecellรวมเป็นหนึ่งcourse; converterสร้างสองplanrowsแต่คัดลอกname/3(0-9-0)ของprojectให้law96642033ด้วย แม้4semester totals18/18/12/12และDBintegrityผ่าน เป็นextraction/normalizationerrorไม่ใช่sourceambiguity

แก้generic `normalize_merged_code_cells`: splitเฉพาะN8digitcodesในrowspanNกับNrowsที่มีname/creditcellsชัดเจน; ไม่splitprintedหรือ/ORหรือincompletegroup ไม่ใช้expectedanswer/workingDB/schemafactsเพิ่ม. Raworiginalยังเก็บเดิม; transformedtextใช้เฉพาะparser. ทดสอบidempotenceและnegativecases

หลัง:[newparse/build](results/bit_manifest_controls_20261010/plan28-29-parse-rowfix/parse-build.json) ได้20sourceplanrows/17uniquecourseDBentries (3electivesเป็นplaceholderplanrows) เทียบ4semesters. Two repairedcourses×4fields(code/name_th/name_en/credits_raw)=8/8 targetedตรงภาพPDF29/book24; ไม่อ้าง20rowsครบทุกfield. 06036146 PROJECT IN BUSINESS INFORMATION TECHNOLOGY 2 /3(0-9-0);96642033 LAW FOR NEW GENERATION /3(3-0-6) เป็นสองรายวิชาแยก ไม่alternative

[Isolated actual4requests](results/bit_manifest_controls_20261010/rowfix29-api-results.json):2questions×2routes substantivecorrect4/4,technical0; [actualUI](results/bit_manifest_controls_20261010/rowfix29-ui-answer.txt) / [source](results/bit_manifest_controls_20261010/rowfix29-ui-source.png). LIVEworkingDBมีสองรายวิชานี้ถูกต้องอยู่แล้ว (read-onlyconfirmationหลังsourceinspection) จึงไม่repairDB; [LIVE4recordedrequests](results/bit_manifest_controls_20261010/rowfix29-live-confirmation.json) และ [LIVEUI](results/bit_manifest_controls_20261010/rowfix29-live-ui-answer.txt) / [LIVEcitation29book24](results/bit_manifest_controls_20261010/rowfix29-live-ui-source.png) ถูกต้องในscopeนี้. ก่อนAPIของwrongisolatedDBไม่recorded; ไม่แต่งbeforeanswer ใช้actualstoredrowfailureเป็นbeforeevidence

Latest dependency-lockedchecksหลังrowspanfix:[315unit/30schema/7frontend/70gold/65oldQA/14provenance/6version sets](results/bit_manifest_controls_20261010/rowfix-shared-checks/checks.json),7jobs0/guardtrue. Earlier313resultsretained ไม่claimเป็นcurrenthash. Repo parserSHA3b5e5a7cb15be45da3685bd50d155eefafb6df1c1a91c90924c9a52e42c0d983; LIVE4bb8131193763847beeb5c986f7c87b0abe79958e6f918f15abc5c608235cc7c (existingcommentpreserved). No workingDBwrite/commit/push/merge

Pending:28Y3S1wildcardpatternยังผิด;26ชื่อThai/heading/footer,257English/footer,93numberingยังผิด. FullOCRtextaccuracy/conditions/descriptioncoverage/allprofilesreconstruction/heldout/difficultLLMlatency/firstmachineinstallationยังไม่complete. NEXTtargetedcrop28lowertermภายใต้newrendereridentity แล้ว source→parse→newDB→actualanswers ไม่เติมdigitsจากlabels

ทดลองmateriallydifferentเพิ่มเติม:[fullink93](results/bit_manifest_controls_20261010/fullink93/manifest-extraction.json) กลับinstruction-only ไม่มีThai; genericflagsจับinstruction_echo/noThaiได้. [tableink26](results/bit_manifest_controls_20261010/tableink26/manifest-extraction.json) ยังคง7codes/creditsแต่ชื่อผิดเดิมและต่อท้ายinstructions; flagsจับinstructionechoได้ แม้codecountครบ. Retainoutputs/configs ไม่mergeกับsuccessfulcolorcrop26 ไม่claimqualityผ่าน/ไม่ingest. ไม่มีownedOCR/parser/checkjobsค้าง; LIVE8000/Ollamaยังอยู่ ไม่มีcommit/push/merge

ไฟล์implementationที่แก้: repo/LIVE scripts/extract_manifest_pages.py และ scr/ocr_system/lab7b_curriculum.py; new repo scripts/parse_raw_plan_job.py, scripts/probe_partial_plan.py; tests/test_manifest_extraction.py, tests/test_raw_table_grounding.py; report/rawresults/checkpoint. Helpersสำหรับisolatedexperimentอยู่repoและdocumentedcommandsเริ่มจากrepo ocr_final ไม่ใช่duplicateLIVE. Source-reviewedproductionapprovals/heldout/workingDBไม่เปลี่ยน. ไม่มีDBbackupใหม่เพราะไม่มีworkingDBwrite; freshpartialoutputsและbeforeoutputsเก็บdurableครบ
