# ผล source-chain และการแก้ Year4 รอบ 10 ตุลาคม

Branch week11_thanapat/HEAD37b3ad5; ไม่มีcommit/push/merge/main/slides/video. ใช้curriculum-auditต่อจากcheckpointจริงและเก็บงานที่ยังทำงานหลังinterrupt ไม่rerunเพื่อresumeโดยไม่มีdependencychange. งานนี้เป็นYear4comparison taskเดิม ไม่ใช่การขยายquestion setหรือheld-out evaluation.

| Profile | Profile-row options | ภาคที่ตรวจ | Content PDF/book | ผลที่สังเกต |
|---|---:|---:|---|---|
| IT-2565-coop | 11 | 2 | 43/38,44/39 | LIVE totals18/15และrowclaimsตรงภาพ;repairก่อนresumeนี้ |
| IT-2565-no-coop | 8 | 2 | 37/32 | LIVE totals15/9และrowclaimsตรงภาพ |
| BIT-2565-coop | 7 | 2 | 35/30 | isolated totals15/6;6-creditORไม่บวกซ้ำ |
| BIT-2565-no-coop | 8 | 2 | 29/24,30/25 | isolated totals12/12;elective/free labels/optionsครบ |
| DSBA-2565-coop | 6 | 2 | 36/35 | isolated totals12/6;overseacourseชื่อแยกถูก |
| DSBA-2565-no-coop | 6 | 2 | 29/28 | isolated totals9/9;slotsยังคงความหมาย |

รวม46profile-row options/12semesters/8contentpages/14unique real coursecodes ไม่รวมplaceholder;ไม่ใช่46uniquecourses. Sourceidentityheadings/coverใช้แยกplan/yearนอกcontentpagecount. SpecificYear4rowclaimsตรวจnames/codes/credits/options/pagepairs ไม่รับรองcategoriesทุกแบบ/prerequisites/fullgraduation/fullbook.

Actualverificationใช้1wording/1reasoningtask/6scopedquestions/12latestHTTPทั้งสองendpoints ไม่เรียก12distincttasks. Sourcecitationclicks8contentpagesเห็นภาพจริง ไม่ใช้validPDFURLหรือHTTP200แทนviewerproof. ITอยู่LIVE;BIT/DSBAอยู่isolatedbuild ไม่claimproductiondeploy. ExistingworkingBIT/DSBAstalefacts/metadataยังต้องtargeteddeploymentภายใต้คำสั่งอนุญาต ไม่overwriteworkingDBในงานรอบนี้.

## Root causes และหลักฐาน

- **Source-approved metadata omission:** semester checksอ่านplan_item แต่comparisonใช้study_term/study_item จึงผ่านcreditscheckขณะที่printedtotalไม่ปรากฏ. Genericmetadata-onlyimporterตรวจsourceidentity/rowfacts/alternatives/pagepairsก่อนสร้างrelationships;backup/idempotence/integrity/factsunchanged.
- **Stale BIT ingestion และmissing production term:** currentparserเก็บfieldsได้ แต่workingDBเก่ายังขาดplaceholdernames/patterns. เพิ่มindependentapprovalของno-coop4/2 และisolatedrebuildผ่าน ไม่แก้originalOCR/evaluation.
- **Generic combined-master identity loss:** normalizationเลือกmasterของoptionแรกและcopyให้ทุกoption. เพิ่มper-optionnames/description/prerequisiteโดยไม่hardcodecodes;missingprereqไม่borrowและsingle-explicitlabelunchanged. SourceDSBA36ระบุoverseanameตรงกับproductionmasterที่มีอยู่แล้ว.
- **Dependencyguardcoveragegap:** เพิ่มsource_reviewJSON/build/evaluation dependenciesของrepoและLIVE แยกจากproductionanswering;fileaddition/deletioninvalidate. ผลguardเก่ายังคงไว้ ไม่อ้างcoverageที่ไม่ได้hash.

รายละเอียด/actualSQL/rows/answers/screenshots/backups: [IT](IT_YEAR4_SOURCE_CHAIN_20261010.md), [BIT](BIT_YEAR4_SOURCE_CHAIN_20261010.md), [DSBA](DSBA_YEAR4_SOURCE_CHAIN_20261010.md). Final [checks](results/dsba_year4_source_chain_20261010/checks-final/checks.json):275unit/30schema/6frontend/70gold/65oldQA/14provenance/6version sets,7jobs exit0/expandeddependenciesunchangedtrue. เป็นregressions ไม่ใช่overallsourceaccuracyหรือuntouchedheld-outscore.

## ยังไม่วัดหรือยังไม่ปิด

Year4source-chainของอีก8/14profiles (หก2560,AIหนึ่งแผน,legacy) ยังไม่ได้ปิดในbatchนี้;reuseverifiedA1ก่อนreviewใหม่. Mixed392matrix/88pendingเดิมยังไม่reconcile;isolatedsuccessไม่ลดproductionfailurecountโดยอัตโนมัติ. RawOCR CER/WERใหม่, fullrelevantmanifestreconstruction, broaderconditions/prereqs, independentheld-out, controlleddifficultLLMcold/warmmedian/p95, recovery, legacyidentity และfirst-machinemodelinstallเป็นn/a/open. ไม่อ้างความถูกต้องครบจากunitcountหรือjustifiedabstention.

SavedOCR/configuredproductionmasterreconstructionแยกจากfreshOCR. SourcePDFs/OCR/held-out/workingDBไม่เปลี่ยนในresumeนี้;แก้code/buildinputsในrepositoryและเก็บisolatedsnapshots. Owned8005/8006หยุดแล้ว;LIVE8000และOllamaคงไว้. ResumeจากCURRENTที่ด้านบน [PROGRESS.md](PROGRESS.md) เท่านั้น.
