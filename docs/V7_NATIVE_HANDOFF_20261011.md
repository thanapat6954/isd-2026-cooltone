# ส่งต่อ v7: native reconstruction แยกจาก vision OCR

## ผลและขอบเขตที่ส่งจริง

Mode A: actualZIP/newvenv20.84s/uncachedpackages33.90s/restore14.91s/emptyQwenstoredownload84.76s/start5.50s/restart5.12s;14snapshots+7sourcePDFs Startupไม่รันOCR ไม่ใช้LIVE/venvเดิมเป็นdependency OS installers/เครื่องอาจารย์จริงยังไม่ได้ทดสอบ

Mode B: source-onlyจาก actualarchive, initialDB/OCR/master/coursecorrections/evaluation=0 nativePDF/table+reviewedexactfontencoding → SQLite172.033s;newvenv15.268/deps20.298s SourceimagesและfactualSQLทุกfieldตรงactualimage reviewที่ตรวจครบก่อนหน้า; PDF34boundaryตรวจภาพใหม่ ไม่มีcoursecorrections ไม่มีOCRmodelinputs ไม่มีfactsเติมหลังSQL

| Profile | PDF pages | SQL rows | Terms | Credits | Native/render seconds |
|---|---|---|---|---|---|
| it-no-coop | 31–37 | 54 | 8 | 129 | 20.446 |
| it-coop | 38–44 | 54 | 8 | 129 | 20.023 |
| dsba-no-coop | 23–29 | 45 | 8 | 132 | 1.722 |
| dsba-coop | 30–36 | 45 | 8 | 132 | 1.561 |
| dsba-2560-no-coop | 25–29 | 44 | 9 | 126 | 20.468 |
| dsba-2560-coop | 30–34 | 44 | 8 | 126 | 18.542 |
| bit-2560-no-coop | 23–26 | 42 | 8 | 126 | 18.813 |
| bit-2560-coop | 27–30 | 42 | 8 | 126 | 18.482 |
| bit-2565-no-coop | 26–30 | 43 | 8 | 126 | 18.59 |
| bit-2565-coop | 31–35 | 43 | 8 | 126 | 17.636 |

รวม56planpages/456rows/81terms;ITมีsupportingrulePDF25ด้วย Source receipts/gateครบ10profiles นี้เป็นacademic-plan-onlypartial ไม่ใช่full14/catalog/rules/prereqs/legacy ไม่อ้างAI/IT2560ว่าfreshv7rebuildผ่าน AIrawnativeที่ผ่านv6มีหลักฐาน historicalแยก

## Failures และgeneral fixes

Attemptแรก10profile:9parsed/DSBA2560coopfailเพราะPDF34มีfacultyqualificationtableหลังplan total; preserveทั้งattempt/noactivation/noimplicitreduce แก้genericnumberedsource-sectionboundaryแล้วNEWsource-onlysandboxทั้ง10ผ่าน การexcludeเป็นregionที่มีexplicitsourceheading ไม่ถือว่าunreviewedpageirrelevant

ITcode/count/bundleSQLเก็บsource-derivedwholegroups, sharedmembership,35→36และ42→43continuation,claim-specificSQLsourcepages;healthadvertiseavailable10/native/font-review/sourcecert First80HTTPnumericchecksผ่านแต่fullanswerreviewพบcalculation36ขณะที่SQLitetotal18 เก็บbadanswers แก้genericSQLbreakdowncarrybundleid/labelและrendererเลือกหนึ่งwholebundle; new80HTTPทุกprofile/สองroutes/สองcyclesผ่าน คำอธิบายจริง3+3+3+9=18 ไม่บวกทุกกลุ่ม

Runtime-fixcandidateใช้certifiedSQLที่สร้างไว้เพื่อruntimeverificationอย่างเปิดเผย ไม่ใช่freshreconstructionใหม่ ไม่มีfactsย้อนไปเป็นbuildinput

## Activation/recovery ที่ทดสอบ

Isolated14→10activate9.898s/start4.660/restart4.121/recover14start4.424;fullactivation/consumerlock/mismatch/failedOCR/partialnative reject Activepointer unchanged afterfailedbuild;injectedafterpointerfault restoreswholepointer;rollback14/usernotes/old14hashes preserved Metadata10source_validated/OCRfalse/supportingrule25; normalrecovery14startupusable SharedOllama/LIVEไม่หยุด

[Checkpoint](PROGRESS.md) ระบุactualpaths/resumecommands หลักฐานoptional `reconstruction-evidence.zip`: finalsourcebuildmanifest/receipts/rawplanimages/parsed/SQLite/hashcoverage/comparison,80APIanswers/health/failuretransactionlogs และOCRmeasurementraw/ref ตัวdevelopmentไม่ใช้production Model/service/stdout/checkpointsเดิมยังอยู่ ไม่รวมexecutorPDFcopiesซ้ำเพราะoriginalPDFอยู่runtime-data.zip; fullworkingcheckpointยังอยู่ที่pathบันทึก

## OCR และ rubric

[OCR measurement](VISION_OCR_MEASUREMENT_20261011.md):actualP2PDF4/5/7 explicitlyimageOCR+synthetic/real quantitativeevaluation Native/fontdecodingไม่ใช่OCRคะแนน Single-rowreal2codes2/2,names4/4,hours3/3,associations2/2;synthetic1row1/1,2/2,1/1,1/1 EnglishlabelCER/WER0เท่านั้น Multirowreal/syntheticomitlastrow code1/2และCER44/73/WER4/8;failurespreserved/rejectedbeforeproduction NoThaiWER/fullpage/fullbook/heldoutaccuracy/OCR→usableDBclaim

## ข้อจำกัดที่ยังเหลือ

IT2560source-onlyfont-reviewtrial0/7parsedต่อแผน:Thai2fontglyphsreviewแล้วแยก แต่supporting-rule scanไปแตะPDF17Wingdings2unreviewed ห้ามสร้างThai mappingให้symbol Legacyidentityยังunresolved Fullbookdescriptions/rules/prereqs/full14replacementยังblocked Browserpolicyบล็อกใหม่ ไม่bypassและไม่อ้างAPI/PNGเป็นbrowserclickpass Difficultgeneration/independentheldoutยังunmeasured Regression357unit/schema/frontend/70developmentgold/65oldQA/14provenance/6versionsผ่าน เป็นdevelopmentregressionไม่ใช่sourceaccuracy Read-onlyauditยังFAIL1372/incomplete51

v6ZIPและevidenceimmutable v7เปลี่ยนcode/documentsที่ตรวจแล้วและใช้runtime-dataZIPbyte-identicalเดิม Source/buildoriginmanifestอยู่ในbundleและfreshbuild ห้ามนำreviewreceipt/measurementJSONไปเป็นruntimefactoverlay
