# ตรวจ source chain ของ DSBA-2565 ปี4

ใช้ curriculum-audit และ PDF visual review บน week11_thanapat; ไม่ commit/push/merge ไม่เปลี่ยนworkingDB/originalOCR/evaluation/held-out. Source DSBA.pdf SHA256 `01ead4c636b04ce072064e5789332b89b678d12b9863f52a72d35a9d15b500a1` ตรวจตรงไฟล์จริง. Hashเป็นdependencyguard ไม่ใช่sourcefidelityด้วยตัวเอง.

## หลักฐานที่ตรวจจริง

PDF23/book22หัวข้อ3.1.4.1ไม่สหกิจ;PDF30/book29หัวข้อ3.1.4.2สหกิจ. ReopenPDF36/book35เพราะมีcontradictionกับชื่อalternativeในactualanswer ไม่ทำreviewทั้งเล่มซ้ำ. PDF29/book28ยืนยันไม่สหกิจYear4. Year4รวม12profile-row options/4semesters/2content pages;นับ06026259หรือ06026260เป็น6หน่วยกิตครั้งเดียว.

| แผน/ภาค | PDF/book | ตัวเลือกในตาราง | รวมที่พิมพ์ |
|---|---|---:|---:|
| สหกิจ4/1 | 36/35 | 4 | 12 |
| สหกิจ4/2 | 36/35 | 2ทางเลือก | 6 |
| ไม่สหกิจ4/1 | 29/28 | 3 | 9 |
| ไม่สหกิจ4/2 | 29/28 | 3 | 9 |

ต้นฉบับระบุ06026260ว่า “สหกิจศึกษาต่างประเทศทางวิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ” / “OVERSEA COOPERATIVE EDUCATION IN DATA SCIENCE AND BUSINESS ANALYTICS” ไม่ใช่ชื่อเดียวกับ06026259. PDF36ระบุ132หน่วยกิตทั้งหลักสูตร แต่batchนี้ตรวจYear4 ไม่ใช่sourcevalidationครบ132หน่วยกิต. หน้าYear4ไม่ยืนยันprerequisites/registration/fullgraduation.

## Root cause และ generic fix

Productionmasterมีชื่อแยกถูกต้องแล้ว. `denormalize_gt()` เลือกmasterตัวแรกสำหรับcombinedcode แล้ว `convert_lab7b()` สำเนาชื่อและprerequisiteชุดนั้นให้ทุกรหัส. ดังนั้นSQLite/courseและplan_item/actualanswer06026260ผิดทั้งThai/English. จัดเป็นsource-extraction/ingestion error ไม่ใช่retrievalwrongdatafilterหรือsourceabsence.

เพิ่มper-option master metadataเฉพาะcombinedcodesในnormalizationทั้งLab7/Lab8; converterอ่านชื่อ/description/prerequisiteแยกแต่ละoption โดยไม่hardcodecoursecode. Missingprerequisiteไม่ยืมจากoptionอื่น;single-course schedulelabelยังคงprecedenceเดิม. การรักษาข้อมูลmasterเป็นpipelinefix ไม่ได้ยืนยันว่าmasterprerequisiteทุกค่าถูกต้องจากหนังสือ และไม่แก้unknownให้เป็น “ไม่มี”.

Syntheticfocusedtests3ผ่าน: distinctnames/prereqs, missingprereqไม่borrow, single-explicitlabelunchanged; placeholderregressionsรวม13ผ่าน. Failedminimalfixturetotal6ถูกvalidatorrejectก่อน แก้fixtureconfiguredtotal30 ไม่เปลี่ยนQAgold/sourcefacts. Isolatedfirstbuildเก็บไว้;เมื่อscopeเปลี่ยนใช้newoutput `dsba-year4-source-rebuild-20261010-b` ไม่resumeincompatiblecheckpoint. SavedOCR/configuredproductionmasterbuildทั้ง2profilesexit0/protectedunchanged;ไม่ได้รันfreshOCR.

## Actual before/after

คำถามเดิม: “ถ้าไม่ไปสหกิจ ปีสุดท้ายต้องเรียนต่างจากแผนสหกิจอย่างไร แยกภาคเรียนและหน่วยกิตของแต่ละแผน”. ก่อนแก้ใน [plans-all](results/it_year4_source_chain_20261010/plans-all.json) ชื่อ06026259/60เหมือนกัน. หลังแก้ใน [actual4responses](results/dsba_year4_source_chain_20261010/after.json) แยกชื่อสหกิจต่างประเทศถูกแล้ว พร้อมSQL/parameters/rows/trace;1reasoningcategory/1wording/2scopedquestions/4HTTP. Status200ทั้ง4แต่ไม่เรียกcompletecomparisonpass เพราะprintedterm totalsยังขาด.

Measuredrequesttimes75.96/36.22/36.23/20.92msเป็นisolatedstructuredprobes ไม่ใช่controlledcold/warmLLMlatency. [ActualUI](results/dsba_year4_source_chain_20261010/ui-answer.jpg)/[DOM](results/dsba_year4_source_chain_20261010/ui-answer-dom.txt) แสดงdistinctalternativeชื่อและ12citations. กด06026260citationแล้ว [viewerจริง](results/dsba_year4_source_chain_20261010/ui-source36.jpg) แสดงPDF36/book35และspecificoverseacoursepassage;browserwarn/error=[].

| มิติ | สถานะ |
|---|---|
| DB consistency | isolatedbuildผ่าน2/2;workingDBunchanged |
| Source fidelity | Year4names/codes/credits/options/plan/pagepairsตรวจ12rowoptions/4terms/2contentpages |
| Answer completeness | final4HTTP/ทั้ง2routes และactualUIแสดง12/6/9/9ครบตามตาราง; scopedYear4comparisonผ่าน ไม่ใช่overallaccuracy |
| Citation support | specific06026260claimผ่านactualclickPDF36/book35;ไม่มีnewclaimว่าทุกsourcepageverified |

ยังไม่deployworkingDB. Prerequisites/catalog/held-out/fullfreshOCR/L3L4/controlledlatency/legacy/first-machineinstallยังเปิดตามcheckpoint. ผลregressionล่าสุดต้องอ่านdependencysetของแต่ละrun ไม่อ้างว่าตรงruntimeใหม่โดยไม่ตรวจhash.

## ปิด semester-total metadata ใน isolated build

เพิ่ม `data/source_reviews/DSBA-2565-term-metadata.json` เป็นproductionterm-onlyapprovalจากrenderedtable/identityheadingsโดยตรง ไม่ใช้dev expectedanswers. Buildเรียกmetadataimporterแยกจากfactualpreparation จึงไม่แก้originalmasterหรือOCR. Metadata12insertsต่อDB (24รวม2DB ไม่ใช่24คำตอบผิด),backup/integrity/idempotence/unchangedfactsผ่าน2/2. [reconstruction](results/dsba_year4_source_chain_20261010/reconstruction-metadata.json), [final4APIresponses](results/dsba_year4_source_chain_20261010/after-metadata.json), [finalUI](results/dsba_year4_source_chain_20261010/ui-final.jpg)/[DOM](results/dsba_year4_source_chain_20261010/ui-final-dom.txt). กดnon-coopcitationแล้ว [PDF29/book28](results/dsba_year4_source_chain_20261010/ui-source29.jpg) เห็น9/9จริง;coopPDF36/book35เห็น12/6และOR6ไม่บวกซ้ำ. ทั้ง2contentpagesรองรับYear4claimsที่ตรวจ;ไม่ได้ใช้ตารางนี้รับรองprerequisite.

[names-lockedchecks](results/dsba_year4_source_chain_20261010/checks-names/checks.json):275unit/30schema/6frontend/70gold/65oldQA/14provenance/6version setsผ่าน7jobsและexpandedguardtrue ก่อนเพิ่มterm-onlyapproval/builddiscovery. ไม่claimcurrentdependencysetเหมือนเดิมหลังเพิ่มไฟล์. RuntimeAPI/answercodeไม่เปลี่ยนในmetadatafinalstep;buildCLIและfinalAPI/UIใช้newisolatedDBจริง. WorkingDSBAยังไม่deploy;originalOCR/held-out/sourcePDFunchanged.

Finalหลังterm-onlyapproval/builddiscovery: [checks-final](results/dsba_year4_source_chain_20261010/checks-final/checks.json) ทั้ง7jobs exit0/275unit/expandeddependenciesunchangedtrue. ไม่ใช่held-outaccuracyหรือการverifyprerequisitesทั้งเล่ม.
