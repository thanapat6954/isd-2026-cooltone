# ส่งต่ออาจารย์ — instructor-v8

ใช้ GitHub branch `week11_thanapat` และ [Release instructor-v8](https://github.com/thanapat6954/isd-2026-cooltone/releases/tag/instructor-v8) โค้ด/commit/hash ระบุใน release handoff-manifest ไม่ต้องมี sibling LIVE หรือไฟล์จากบัญชีผู้พัฒนา

## Final implementation

| ขั้นตอน | Entry point ที่ใช้จริง |
|---|---|
| เปิด/หยุดเว็บ | `ocr_final/scripts/start_web.ps1`, `stop_web.ps1` |
| Backend/frontend | `ocr_final/lab10_fastapi/curriculum_app/`, `frontend/` |
| Restore runtime | `scripts/runtime_bundle.py restore` |
| Reconstruct/validate/activate/rollback | `scripts/database_build.py` |
| Native decoding/sequence parser | `scripts/source_native.py`, `native_plan_sequence.py`, `parse_fresh_build.py` |
| Image-only OCR | `scripts/extract_manifest_pages.py` + `scr/ocr_system/lab7b_curriculum.py` |
| SQLite/schema/query | `scr/ocr_system/lab8b_curriculum_db.py`; `run_lab8b.py` profile registry |

Lab7/Lab8 filenamesยังเก็บเพราะใช้จริง ไม่ใช่oldduplicate RemovedEasyOCRcatalog3files `curriculum_ocr.py`, `curriculum_engine.py`, `db_to_json.py`; `reconstruct_isolated.py` เลิกcopyunusedfilesเหล่านี้ Removedroot `ocr_system/` จากsubmittedGit; localinputs/rawoutputsยังอยู่เดิม ไม่ลบsourcePDF/evaluation/evidence Oldcodeเก็บในGit history ไม่มีmultipleprimary startup paths

## ขอบเขตที่มีหลักฐาน

ModeA14catalogsnapshots/7PDF;13identifiedplanprofiles+legacycatalog identityunresolved RuntimeSQL-only; structuredsources/pagepairs หลักฐานไม่ครบให้uncertainty ไม่ใช้JSONfacts overlays

ModeBfreshnative source-validatedสิบprofiles: IT2565two54/54rows; DSBA2565two45/45; DSBA2560two44/44 (no-coop9terms); BIT2560two42/42; BIT2565two43/43. รวม456rows56planpages81terms/172.033secondsในv7 pipeline/sourceinputsคงเดิม Reviewedfontencodingไม่ใช่visionOCR ไม่มีcoursecorrectionfactsในการfreshbatch นี้ Scoped14→10/80HTTP/failedbuild/mismatch/fault/recoveryuserdata ผ่านตาม [รายงาน native](V7_NATIVE_HANDOFF_20261011.md)

VisionOCRselecteddevelopmentrows2real+1syntheticผ่านcode/name/hour/association แต่multirowยังdefect ไม่ถือfullOCRDB/fullbook/heldoutaccuracy; [OCR measurement](VISION_OCR_MEASUREMENT_20261011.md) P2rubricrequirementimageOCRยังมีช่องว่าง ไม่ใช้nativeแทน

IT2560supportingWingdings/sourcecert, fullcatalog/rules/prereqs/legacy/full14reconstructionยังblocked Audit1372fail51incompleteเป็นknownbookcoverage/findings ไม่ใช่startupfailure Independentheldoutยังไม่ทดสอบใหม่ Browserclickblockedโดยpolicy ไม่bypass; source-route/PNG/APIchecksไม่ใช่browserpass

## Verification / evidence

Localcorrect-root357unit/30schema/11frontendผ่านหลังcleanup Removedimplementationdependencytraceเก็บrawlocal `docs/results/final_delivery_20261011/` ครั้งแรกunitจากwrongcwdfailedimportscripts26errors เก็บfailureไม่แก้testsเพื่อpass แล้วรันจากocr_finalถูกต้อง

Final downloadverificationต้องใช้exactremotecommit + releasebundle +newvenv/cache-freepipcheck +installedsharedQwenserviceโดยเปิดเผยreuse ไม่downloadmodelซ้ำ Coldmodeldownloadproofv7ยังคงเดิม Testall14APIcatalogs/bothroutes/startrestart/sourcehash/viewerasset/missingfile/model/occupiedportโดยownedprocesschecks; evidenceและผลวัดแนบreleaseVERIFICATION/manifestเมื่อเสร็จ ไม่อ้างuntestedOSinstaller/independentheldout/fullbookaccuracy

## Artifact ownership

Runtime14SQLiteเป็นrevieweddevelopment snapshots originอยู่build-lineage.json;7PDFเป็นsourcecurricula hashlistedmanifest เก็บcopyrightเจ้าของต้นฉบับไม่อ้างopenlicense ชุดส่งต่อเผยแพร่ตามexplicitauthorizationผู้ส่ง ไม่มีmodelweights/venv/secretsในGitหรือcodeZIP ReleaseassetsแยกจากGit blobs; runtime ZIP1.241GBไม่commitเข้าGit

v6/v7sealedไม่แก้; v8ใช้runtimebundleเดิมSHA39018bfa21a7a36ea4f92fde8eb4db5d671745679dddc90dead38d8f23ec9f07 Cfree18.0GBก่อนfinalpublish ใช้onefreshworkspaceและsharedmodel ไม่retryrejectedcachedelete

## ผล fresh remote download ที่เสร็จจริง

โค้ดremote427bb7aในisolatedTEMPworkspace +newPython3.11venv17.701s/pipcachefree24.721s/pipcheck0.741s ActualGitHubruntimeassetdownload139.065s/SHAตรง/restore2.680s/preflight1.706s SharedinstalledQwen3:4b/11434ใช้โดยเปิดเผย ไม่downloadmodelซ้ำ

Startup5.330s/restart4.561s;13selectableprofilesทั้งสองroutes/สองcycles52recordedchecks +development70/70 (L1/L2factual52, missing-evidence18แยก ไม่countasfactual). SQLgrounding/answerfield/sourcepairs/frontendassets/source-infoSHA/sourceviewerPNGผ่าน;actual11PDFpageimages/13selectedclaimsตรวจด้วยตาแล้ว ไม่ใช่fullbookcertification. Missingfile/model/occupiedportusefulThai/DBhashunchanged/ownedbackendstopผ่าน legacyfivecasesเป็นuncertaintychecks ไม่อ้างsourceidentityresolved

ตัวverifierแรกผิดcoverageassert14substantiveprofiles แก้ให้matchidentifiedSQLiteprofiles13 อันนี้testharnessfixไม่แก้runtimefacts Guardfailurerawยังเก็บ ผลสุดท้าย [portable summary](public_results/final_delivery/verification-summary.json). Read-onlyauditfresh14/FAIL1372/incomplete51คงเดิม Summary/HIGHreviewแล้ว

v7native/runtime/source13criticalmodulesไม่มีcontentchangeนอกจากline-endingnormalization จึงpreservefreshnative10และreal14→10activation/recoveryproof ไม่rebuildผ่านซ้ำเพียงเพื่อเปลี่ยนpackaging Detailedfailure/rawlogsยังอยู่localcheckpoint;releaseevidenceoptional ไม่จำเป็นเปิดแอป
