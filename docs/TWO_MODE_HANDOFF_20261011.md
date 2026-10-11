# ผล handoff สองโหมด — 11 ตุลาคม 2569

## สถานะที่ยืนยันได้

**Mode A ผ่าน fresh delivery copy, dependency installation, versioned activation, API/source และ recovery. Mode B ยังไม่พร้อม full replacement:** fresh AI plan PDF23–26 สร้าง SQLite ได้ แต่ยังมี material source defects; อีก12 curriculum/plan profiles และ mixed legacy catalog ยังไม่มี fresh full reconstruction รอบนี้. ไม่อ้าง instructor-ready ครบสองโหมด

Branch `week11_thanapat`; implementation อยู่ `isd-2026-cooltone/ocr_final/`. ไม่ commit/push/merge/main/slides/video. ไม่เปลี่ยน working curriculum DBs หรือ source PDFs และไม่อ่าน held-out answers. คู่มือเริ่มเครื่องใหม่อยู่ [root README](../README.md)

## root/process identity

ตอนเริ่มรอบนี้8003 PID33952 และ8004 PID19684 รายงาน module/loaded DB paths ของ sibling LIVE. ไม่ใช้เป็น handoff proof และไม่หยุด. Repository app ตรวจใหม่บน8006; fresh-copy app ใช้8005. ทั้งสอง root ตรวจจาก `/api/health`, module filename และ14 loaded database paths. Portเป็น listener ไม่ใช่ขั้น OCR. URL/citations เป็น same-origin; defaultในคู่มือ8000 เลือกอื่นด้วย `-Port`

หลักฐาน [listeners](results/two_mode_handoff_20261011/listeners-entry.json), [health roots](results/two_mode_handoff_20261011/health-entry.json), [lifecycle](results/two_mode_handoff_20261011/lifecycle/verification.json). หลักฐานเก่าที่บอก8004เป็นrepoไม่แทน current process ownership

## Mode A — actual artifacts และ fresh environment

Physical copy ของ code และ runtime bundle14DB/7PDF; venv ใหม่และ pip uncached. ไม่ใช้ LIVE folder/venv ขณะเปิดแอป. ใช้ shared installed Ollama11434อย่างเปิดเผย; empty-store download ของ model digest เดิมจากก่อนหน้ามี evidence แยก ไม่ดาวน์โหลดซ้ำในรอบนี้

| ขั้นวัดจริง | วินาที | ผล |
|---|---:|---|
| Python3.11 fresh venv | 14.910 | exit0 |
| uncached runtime+rebuild dependencies | 25.578 | exit0; pip check0 |
| restore14DB+7PDF | 9.959 | exit0; physical copies/hash check |
| bundle → versioned candidate | 1.169 | full-set validationผ่าน |
| activate over usable set | 2.435 | whole-set backup + atomic pointer |
| activated startup | 4.295 | correct root/build/14 loaded DBs |
| recovery startup | 4.583 | previous14 snapshots usable |

เครื่องที่วัด Windows11/Python3.11.9/PowerShell7.6.5, i7-13620H/RAM15.7GiB/RTX5050 Laptop GPU. OCR tag `scb10x/typhoon-ocr1.5-3b:latest`, digest `483bac0b367b529f874880767af8b183c8d99e64c37105fbe3c5756cf0529b49`; parser/Q&A `qwen3:4b`, digest `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`. Fresh raw config150DPI/temperature0/retries0, OCR num_ctx8192/num_predict2048; prompt/render/image/model identitiesเก็บใน raw manifest

12 substantive HTTP responses: IT-2560-no-coop ระยะเวลา4ปี และ BIT-2565-no-coop06036123 CLOUD TECHNOLOGY3credits ผ่าน `/api/ask` และ `/ask` ใน bundled/activated/recovered cycles. Returned SQL/rows, loaded paths และ source info เก็บครบ. ตรวจ PDFจริง IT6/book1 และ BIT28/book23 ด้วยภาพ PyMuPDF/Poppler; supporting fieldsตรงภาพ. Browser policy blockเดิมยังมีผล: **ไม่มี new frontend click/navigation pass**, source images/APIไม่ใช่ browser proof

Origin ของ DBแต่ละฐาน/identity/counts/source references/SQLite integrity/SHA และ7PDF อยู่ [build-lineage.json](results/two_mode_handoff_20261011/build-lineage.json). DBเป็น reviewed-runtime snapshots ไม่ใช่ fresh source extraction หรือ independent ground truth; source gapsยังอยู่

## safe replacement และ failure paths

| ข้อกำหนด | ผลที่ตรวจจริง |
|---|---|
| unique staging | ทุก import/rebuildสร้าง build ID ใหม่; active filesไม่ถูกเขียน |
| full-set/identity/schema/hash/provenance gate | full bundle14ผ่าน; missing/mismatched/undeclared candidates reject |
| empty/missing model/partial/raw defects | missing OCR model build reject; partialAIและ source-defective fullAI reject |
| backup/user data | SQLite backup API/integrity/hash/previous pointer; synthetic user_notes ทั้งชุดอยู่ backupและrecoverกลับได้; ไม่ migrate editsอัตโนมัติ |
| no mixed requests | backend OS consumer lockตลอด lifespan; activate/rollback rejectขณะserverใช้DB; registry pin selected set; restartสร้างcacheใหม่ |
| activation/post-pointer failure | injected after-pointer failureคืน original pointer bytes และ oldDBhashes; complete14ชุดเดิมยังอยู่ |
| shutdown/restart/recovery | stopตรวจmodule root/PID/start time/listener; actual14DBrecovery+APIผ่าน |
| occupied port | owned unrelated HTTP serverยังรันหลังlauncherreject; ผู้ทดสอบหยุดเฉพาะserverที่สร้างเอง |
| Thai missing-file/model instructions | preflight/launcherreject missingAI.pdf/missinganswer model; logsมีวิธีrestore/model pull/เลือกport |
| failed OCR preserves usable set | missingOCRmodelและsource-defectiveAIactivate exit1; active pointerไม่เปลี่ยน |

หลักฐาน [source-defect rejection](results/two_mode_handoff_20261011/reject-source-defective-activation.json), lifecycle `checks.failures`/`failed_build_kept_pointer`, [8 focused tests](results/two_mode_handoff_20261011/build-tests-final.stderr.log). Synthetic lifecycle rowsไม่ใช่ source accuracy/evaluation facts. ไม่มี stop Ollama หรือ unrelated LIVE listeners

`work/staging/<id>/` เก็บ input copies/raw/parsed/logs/validation. `work/builds/<id>/` เก็บ selected immutable set. `work/active-build.json` เป็น pointerเดียว. `work/backups/build-switch/<id>/{backup,transaction}.json` เก็บ recovery paths/hash/integrity. CLI recoveryพิมพ์ backup pathของเครื่องผู้ใช้; rootREADMEใช้ quoted commandsรองรับspaces

## Mode B — isolation และ source chain

`database_build.py rebuild` สร้าง executorใหม่ที่ไม่มี working DB, saved OCR, metadata DB, generated master หรือ evaluation/held-out inputs. InputsมีPDF, code/source-recorded profile configuration และ page-selection only. `parse_fresh_build.py` ใช้fresh markdown → parsing/normalization → SQLite. Program identity/declared metadataมาจาก `PROFILES` อย่างเปิดเผย ไม่อ้างว่า OCRสกัด metadataเหล่านี้ใหม่. Normal startupไม่เรียกpipeline

| ประเภท | ใช้/สร้างจริง |
|---|---|
| source | immutable PDF และ source/page-selection hash |
| code/configuration | generic extractor/parser/builder + recorded identity/page ranges; SHAทุกcode/config/model |
| newly generated | raw page PNG/markdown/fullmodel responses/parserJSON/SQLite/validation/logs |
| reviewed corrections | `--mode reviewed` เปิดใช้เฉพาะ named matching plan-corrections/hashguardและเก็บreviewed-inputs; raw runรอบนี้ใช้0corrections |
| validation review | independent source observations/hash receipts; ไม่มี runtime factual overlay |
| evaluation | dev goldแยกจากbuild; held-outไม่ได้อ่าน/ใช้ |

Fresh executorก่อนrunมี0DB/0OCRpred/0master/0evaluation. [One-page evidence](results/two_mode_handoff_20261011/ai-page23-evidence/build.json): rendering/OCR25.400s, parseSQLite33.171s, whole command60.638s; new12courses/13planrows. AI PDF23/book19 sourceภาพตรวจทุกrow: codes/names/patternsและplaceholder9064xxxxตรง. [4 real fresh-DB HTTP responses](results/two_mode_handoff_20261011/fresh-ai-api/api.json) คืน6/7rowsและ15/19creditsพร้อมcitation23/19. partialไม่ถูกactivate

Fresh runใหม่จากPDF-only executorด้วยupdatedcode ทำAI23–26ทั้ง4หน้า: rendering/OCR80.895s, parsing/SQLite103.167s,40parsedentries→34catalogcourses/41planrowoptions/8terms. Integrityokและtotals15/19/18/19/18/13/12/6รวม120โดยนับ43/44 ORครั้งเดียว. **นี่ไม่ใช่ factual accuracy pass**:

- PDF25/book21 free elective placeholderเป็น8x แต่OCR11x และ parserทำraw_codeหาย; rawเพิ่มมหาวิทยาลัยสุโขทัยธรรมาธิราชที่sourceไม่มี
- PDF26/book22 language slot90644xxxกลายเป็น9064xxxx; free elective8xเป็นmixed-case7xและraw_codeหาย
- PDF26/book22 domestic/overseas06046443/44สูญเสียชื่อไทยแยก; SQLitecopyfirstThai+mergedEnglishทั้งสอง และ OCRมีCOOPERPERATIVE misspelling

ภาพเต็มPDF23–26ตรวจจริง; source findingsและrawไม่ถูกแก้. [Fresh full-plan manifest](results/two_mode_handoff_20261011/ai-full-plan-evidence/build.json), [known defects](results/two_mode_handoff_20261011/ai-full-plan-evidence/source-review-findings.json), [validation rejection](results/two_mode_handoff_20261011/ai-full-plan-evidence/validation.json). Year4 `/api/ask`/`/ask` [4responses](results/two_mode_handoff_20261011/fresh-ai-full-plan-api/api.json) ให้totals12/6ถูก แต่ placeholder/namesผิดตามSQLite จึงแยก numerical passจากsource-fidelity fail. ไม่แก้ด้วยgold/held-outหรือแอบใช้bundledDB. ไม่retry configurationนี้ซ้ำหลังพบdefects

## coverage แยกทุก curriculum/version/plan

| Profile | Mode A / development gold | Fresh Mode B รอบนี้ |
|---|---|---|
| AI-2566-coop | loaded /5of5 | plan23–26 4of4 pages→41rows; materialdefects/reject; catalog/descriptions/rulesไม่ครบ |
| DSBA-2565-coop | loaded /5of5 | not run; no raw/reviewed full claim |
| DSBA-2565-no-coop | loaded /5of5 | not run |
| DSBA-2560-coop | loaded /5of5 | not run |
| DSBA-2560-no-coop | loaded /5of5 | not run |
| IT-2565-coop | loaded /5of5 | not run |
| IT-2565-no-coop | loaded /5of5 | not run |
| IT-2560-coop | loaded /5of5 | not run |
| IT-2560-no-coop | loaded /5of5 +lifecycle example | not run |
| BIT-2565-coop | loaded /5of5 | not run; priorOCRfailuresยังมีผล |
| BIT-2565-no-coop | loaded /5of5 +lifecycle example | not run; priorOCRfailuresยังมีผล |
| BIT-2560-coop | loaded /5of5 | not run |
| BIT-2560-no-coop | loaded /5of5 | not run |
| legacy-course-catalog | loaded /5of5 | mixed6147rows/sourceAI1593+DSBA2270+IT2284; PDFsมีในชุดแต่ row/version/plan identityและfullrebuildcontractยังไม่ยืนยัน |

Reviewed replay จาก fresh AI23–26 prediction ใช้ production AI-2566-plan-corrections.json ผ่าน source/hashguard และแก้ปี4/ภาค1ตามapprovalเดิม แต่ Lab8 import exit1 ด้วย `placeholder_source_code_missing` ที่PDF25 ก่อนโหลดSQLite. [conversion findings](results/two_mode_handoff_20261011/ai-reviewed-replay/curriculum.conversion.json) และ [failure log](results/two_mode_handoff_20261011/ai-reviewed-replay/import.stderr.log). เป็น parser/ingestion replayของfreshOCRที่ระบุชัด ไม่ใช่freshOCRรอบใหม่หรือcomplete reviewed build; rawไม่ถูกแก้. Reviewed option implementationมี แต่ full reviewed ingestion/replacementยังไม่ผ่าน. ไม่ส่งDSBAmasterเป็นfreshbuildinputและไม่คัดlegacyจากworkingDBเติมfullset. Activationของfreshsetต้องผ่านsource/schema/identity/all14profilegate; ไม่มีauto-certified source-validation receipt. code/config/model/sourceเปลี่ยนจะrejectresume; successfulOCRcheckpointsใช้ได้เฉพาะmatchingdigest/image/prompt/config

## verification และข้อจำกัด

Final dependency-locked check7jobs exit0/unchangedtrue: unit335/schema30/frontend7/gold70/old2560 65/provenance14/version6. [current repository check](results/two_mode_handoff_20261011/checks-final/checks.json). Gold final structured52requests median336.49ms/p95378.51ms; ไม่ใช่OCR/coldmodel/difficultgeneration. ก่อนหน้าที่default8000ผิดหรือdependencyguardfalseเก็บไว้แต่ไม่รวมเป็นผ่าน.

Development gold70of70แยก14catalogs×5: [corrected actual8006 run](results/two_mode_handoff_20261011/gold-corrected-8006.json). Median377.88ms/p95419.78msเฉพาะ52structured first requests ไม่ใช่OCRtime/coldmodel/difficultLLM. Read-only audit14/FAIL1372/incomplete51; ไม่มีfullreferencecoverageในrepoapp จึงไม่ตีความว่าความถูกต้องดีขึ้นจากscopeต่างกับLIVE

Failed harness attemptsเก็บครบ: BITsubstringถูกจัดเป็นIT, case-sensitive English check, legacy-first mutationfixtureไม่มีprogramtable, default8000ที่ไม่มีlistener, OneDrivecheckpointPermissionError. แก้harness/propagateconfiguredURLโดยไม่แก้expectations/runtimefacts. ไม่รวมfailedrunsเป็นpassingcounts. Source/model/PDF/OCRprotectedinputsไม่ถูก overwrite

Remaining blockers: fresh reliable full ingestion12profiles, source-backedfullcatalog/descriptions/prerequisites/regulations, mixedlegacyidentity/rebuild, allprofile raw+reviewed activationจากPDF, newbrowserUI/citationclicksที่policyblocked, OSinstallersและindependentheld-out/difficult-questiongeneration latency. ชุดส่งใช้Mode Aได้ตามผลที่วัด; **ยังไม่รับรองMode B full instructor handoff**

## Actual ZIP delivery rehearsal และ final package

ชุด `delivery/instructor-handoff-20261011-v4/`: code ZIP, runtime-data ZIP14DB7PDF+lineage, SHA256/inventory manifest และ VERIFICATION.md. [actual submission proof](results/two_mode_handoff_20261011/submitted-v4/package-state.json) completedtrue/rehearsalexit0/code646filesverified. [new machine rehearsal](results/two_mode_handoff_20261011/submitted-v4/rehearsal.json) ใช้โครงการที่แตกจากZIPจริงและpathมีspaces: venv15.72s/uncachedwebdependencies19.99s/pipcheck0.70s/restore16.72s, empty `initial_tags.models=[]`, Qwen download62.31s/digest359d7dd4…f09474fae7, firstpreflight1.65s/start5.41s/stop1.92s/restartpreflight1.21s/start4.39s/stop1.76s. 2questions ×2cycles =4HTTP (IT `/ask`, BIT `/api/ask`); lifecycleก่อนหน้านี้ตรวจทั้ง2questionsผ่านทั้ง2routesครบ12HTTP. IT6/book1 sourceinfo/hash/PNG2cycles matchedsourceที่ตรวจภาพจริง; sourceBIT28/book23ตรวจในlifecycle. ไม่ใช่browserclickpass. DBhashesunchangedtrue, ownedservicesstoppedtrue, documentedCLIlist/pullexit0 (CLIpullidempotentหลังactualemptydownload). ไม่ต้องติดตั้งOCRmodelสำหรับMode A

เมื่อจบงานไม่มีowned8002/8005/8006/11436/11437listener; อื่น8003PID33952/8004PID19684/8010PID5076/11434PID12268ยังเดิม. [exit listener snapshot](results/two_mode_handoff_20261011/listeners-exit.json). ไม่มีbackgroundOCR/rebuild jobหรือworkingDBactivation

Final code ZIP เพิ่มเฉพาะ ThaiREADME/checkpoint/report และdurableproofหลังrehearsal; เก็บ ZIPที่ทดสอบจริงเป็น `curriculum-project-tested.zip`. `final-package-comparison.json` ต้องยืนยัน runtime/build/config/tests/source-review/evaluation code differences0 และdataZIPhashเดิม; ไม่อ้างว่าติดตั้งmodel/OCRซ้ำหลังdocumentation-only update. Finalarchive inventory/hash/path checksเป็นคนละหลักฐานกับrehearsalและfullsourceaccuracy
