# ตรวจ source chain ของ BIT-2565 ปี4

ทำงานบน week11_thanapat โดยไม่ commit/push/merge. ใช้ curriculum-audit และอ่านภาพจริง ไม่ใช้ OCR หรือคำตอบแอปเป็นเฉลย. RuntimeคำตอบมาจากSQLiteในisolatedoutputเท่านั้น; ไม่เปลี่ยนworkingBITDB และไม่ใช้held-out/evaluation labelsเติมproduction.

## Source fidelity ที่ตรวจ

Source BIT-65.pdf SHA256 `f7f8fba36276f772c757762a1e48879af8b54c3fe8ab3325e8f96996268891bc`. ปกPDF1ยืนยันหลักสูตรนานาชาติปรับปรุง2565; หัวข้อPDF26/book21ระบุไม่สหกิจ และPDF31/book26ระบุสหกิจ. ตรวจ15profile-row options/4ภาค/3content pages โดยแยกcontinuedYear3/S2ออกจากYear4.

| แผน/ภาค | หลักฐาน PDF/book | แถวตัวเลือก | รวมที่พิมพ์ |
|---|---|---:|---:|
| ไม่สหกิจ4/1 | 29/24 | 4 | 12 |
| ไม่สหกิจ4/2 | 30/25 | 4 | 12 |
| สหกิจ4/1 | 35/30 | 5 | 15 |
| สหกิจ4/2 | 35/30 | 2ทางเลือก | 6 |

06036147สหกิจศึกษาหรือ06036148สหกิจศึกษาต่างประเทศเป็น6(0-35-0)หนึ่งกลุ่ม ไม่บวกเป็น12. 06036xxxวิชาเลือก1/2หรือกลุ่มวิชาที่1–4มีชั่วโมง3(3-0-6)หรือ3(2-2-5); retainedเป็นทางเลือก ไม่อนุมานรายละเอียดแต่ละกลุ่มจากตารางนี้. Free slotsและGE slotsยังเป็นplaceholderที่ถูกต้อง. โครงงาน06036146ต้องมีเลข2;Facultyheadingไม่ใช่ส่วนชื่อกฎหมาย.

## สาเหตุและการแก้

Workingplan_itemมีชื่อ/pattern/credits_rawขาด แม้productionreviewมีข้อมูลส่วนใหญ่แล้ว: **stale source-reviewed ingestion** ไม่ใช่ข้อพิสูจน์ว่าsourceขาดหรือcurrentparserลบข้อมูล. Currentconverter/loadpreservefieldsได้ในfreshbuild. Productionapprovalเดิมยังขาดไม่สหกิจ4/2 จึงเพิ่มtermจากภาพPDF30/book25พร้อมidentityapprovalแยกจากdevelopment observations.

Metadata importerตรวจsourceidentity/hash/ชื่อ/code-pattern/credits/pagepairs/rowcountก่อนสร้างstudy_term/study_item. เพิ่มgenericexplicit-alt_groupvalidationและนับchoiceครั้งเดียว. Strict mismatchยังfail loudly;ไม่แก้expectedQAanswers. Freshconfigured savedOCRbuildในisolatedoutput2profiles exit0 (8.35/8.00วินาที)/protectedunchangedtrue. ไม่ใช่freshOCRและไม่เรียกreviewedingestionว่าOCRaccuracyimprovement.

## Actual API/UI และหลักฐาน

คำถามเดิม: “ถ้าไม่ไปสหกิจ ปีสุดท้ายต้องเรียนต่างจากแผนสหกิจอย่างไร แยกภาคเรียนและหน่วยกิตของแต่ละแผน” โดยscopedcurriculum/version/planในrawJSON. เป็น1reasoning task/2scopedquestions/4HTTP requestsผ่านสองendpoints ไม่ใช่4งานคิดต่างกัน.

- ก่อนแก้: [recorded28-requestbatch](results/it_year4_source_chain_20261010/plans-all.json) มีชื่อplaceholder “เลือกจากรายวิชาในหมวดนี้ (ยังไม่ยืนยันชื่อหมวดจากข้อมูลที่นำเข้า)” และไม่แสดงprintedtotal. ไม่สร้างbeforeoutputใหม่ขึ้นเอง.
- หลังแก้: [actual4responsesพร้อมSQL/parameters/retrievedrows](results/bit_year4_source_chain_20261010/after.json) แสดงชื่อ/optionsและtotals15/6กับ12/12ครบตรงภาพ. เวลา50.68/20.94/36.55/40.17msเป็นstructuredisolatedprobes ไม่ใช่controlledcold/warmLLMbenchmark.
- [UIจริง](results/bit_year4_source_chain_20261010/ui-answer.jpg) แสดง15rowoptions/4sectionsกับcitations; [DOM](results/bit_year4_source_chain_20261010/ui-answer-dom.txt). กดcitationsแล้วเห็นPDF35/book30,PDF30/book25,PDF29/book24จริง: [35](results/bit_year4_source_chain_20261010/ui-source35.jpg), [30](results/bit_year4_source_chain_20261010/ui-source30.jpg), [29](results/bit_year4_source_chain_20261010/ui-source29.jpg). Browserwarn/error=[]ในrawevidence.

| มิติ | ผลตรวจ |
|---|---|
| DB consistency | isolatedbuild2/2ผ่าน; metadata/fidelityguardsไม่เปลี่ยนworkingDB |
| Source fidelity | 15rowoptions/4terms/3contentpagesตรวจชื่อรหัสหน่วยกิตoptions/plan/pagepairs;ไม่ครอบคลุมทุกหมวด/เงื่อนไข |
| Answer completeness | comparison taskเดียวทั้ง2routesครบYear4ตามภาพ;ไม่ใช่overallaccuracy |
| Citation support | specificYear4claimsและclickedcontentpages3/3ตรงต้นฉบับ |

[checksก่อนขยายdependencyguard](results/bit_year4_source_chain_20261010/checks/checks.json):270unit/30schema/6frontend/70gold/65oldQA/14provenance/6versionsผ่าน7jobs. Guardนี้ยังไม่ครอบคลุมproductionapprovalJSONและfileaddition;ผลใหม่ต้องแยกoutput. Prerequisites/registration/fullgraduation/L3L4/held-out/freshOCRยังไม่verifiedจากbatchนี้. WorkingBITยังstaleจนมีtargeteddeploymentที่ไม่overwriteภายหลัง; isolatedsuccessไม่เท่ากับproductiondeployment.
