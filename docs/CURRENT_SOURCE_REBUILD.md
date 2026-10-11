# ผลตรวจและแก้ pipeline รอบ 8 ตุลาคม 2569

ทำงานบน `week11_thanapat` จาก `37b3ad5` โดยไม่ commit/push/merge และไม่เปลี่ยน main งานนี้ใช้ curriculum-audit แยกหลักฐานจากภาพหนังสือ ข้อมูล production ingestion และ evaluation labels ออกจากกัน **ยังไม่เสร็จทั้งเจ็ดงาน**

## หลักฐานหนังสือและ labels ที่เพิ่ม

- ตรวจภาพ BIT-65.pdf PDF26–35 / หน้า21–30ในเล่ม ครบตารางทั้งสองแผน: แผนละ126หน่วยกิต
- ตรวจภาพ AI.pdf PDF23–26 / หน้า19–22ในเล่ม: ตารางรวม120หน่วยกิต มีตัวเลือกสหกิจ06046443/06046444 ไม่อนุมานว่าหน้าอื่นไม่มีแผนอีกแบบ
- ตรวจภาพ IT.pdf PDF35/36/37/43/44 / หน้า30/31/32/38/39ในเล่ม เพื่อแก้แถวตกและตารางข้ามหน้า ทั้งสองแผนรวม129หน่วยกิต
- เพิ่ม development labels ใหม่24ภาค/127ตัวเลือก และ39คำถาม L1/L2 สำหรับ AI-2566/BIT-2565ทั้งสองแผน ใช้ภาพที่ตรวจแล้ว ไม่ใช้ DB หรือคำตอบ chatbot เป็นเฉลย
- ใช้49ภาค/300ตัวเลือกของหกแผน2560ที่ตรวจไว้ก่อนหน้าโดยไม่ทำ source review ซ้ำ ไม่อ้างว่าการย้าย schema เป็น source verification ใหม่
- labels ใหม่ยังไม่ครอบคลุมความถูกต้องของทุกชื่อ หมวดวิชา prerequisite เงื่อนไขจบ L3/L4 หรือ CER/WER และไม่ใช่ held-out

รายละเอียด: [source observations](../ocr_final/data/ground_truth/evaluation/current-page-observations.json), [index datasets](../ocr_final/data/ground_truth/README.md), [ผล export](results/current_source_20261008/export.json)

## Root causes และการแก้

| ประเภท | ปัญหาที่มีหลักฐาน | การแก้และขอบเขต |
| --- | --- | --- |
| data-ingest/citation | BIT65/AI plan rows ไม่มี printed folio ทำให้39คำตอบเลขถูกแต่ source support ไม่ผ่าน | approval14คู่หน้าเข้า SQLite127แถวใน3profiles; fact fingerprint คงเดิม มี backup/staging/history |
| OCR loss/ingest | BITcoop elective ใช้รหัส96643021/96642033ซ้ำกับวิชาจริง แยก heading เป็นแถว และตก6หน่วยกิต; ITcurrentแถว elective ตก | source-reviewed complete-term inputs แยกจาก OCR เดิม รวม21ภาคที่ผ่าน printed row count/alternative-group credit validation |
| reconstruction | ITold/BIToldเคยซ่อมจาก reviewed copy แต่ build จาก OCR เดิมไม่ใช้ข้อแก้ที่ตรวจไว้ | ส่งออก10ภาคจาก approved input chains โดยตรวจ source/input SHA แล้วใช้เป็น production build approvals |
| source fidelity | AI language/free slot pattern, BIT language pattern/alternative hours, DSBA60 placeholder length รวม5จุดไม่ตรงหนังสือ | corrections จากภาพที่ตรวจแล้ว; DSBAแก้ code เพียงช่องเดียวด้วย unique-row guard ไม่ถือ placeholder เป็น malformed |
| code/latency | browser budget30s แต่ generation หลายครั้งเริ่ม budget180sใหม่ทุกครั้ง | budgetร่วมผ่าน ContextVar; health แจ้ง timeout; browserเผื่อ10s; ไม่ใช่ SLA5s |
| code/resume | OCR page ที่เสร็จสูญเมื่อหน้าถัดไปล้มเหลว; harnessเดิมนับ failed profile เป็น completed | per-page image/prompt/config hashes + checkpoint content hash; failed attempts retry ได้และเก็บ logs เดิม |
| model environment | Typhoon original nameเรียกได้หนึ่งหน้าแล้ว HTTP500; Ollamaแจ้ง untrusted mount point ที่manifest symlink | ไม่แก้ security/model files; fresh isolated runใช้ installed vision artifact ที่ original manifestอ้างถึงอย่างชัดเจน บันทึก overrideและmanifestทั้งคู่ ไม่เปลี่ยน default model ของแอป |

production approvals อยู่ [data/source_reviews](../ocr_final/data/source_reviews/); expected answers ไม่เข้า runtime prompts/lookups การแก้ reviewed ingest ไม่ใช่ OCR accuracy gain

## Reconstruction และ API/UI ที่สังเกตจริง

saved-OCR/configured source ingestion → DB ใหม่ใน isolated output ผ่าน13/13, integrity13/13 และทุก DB มี fidelity columnsทั้งหก โปรดทราบ DSBA2565ยังใช้ source-reviewed master ตาม configuration ไม่ใช่ OCR-only import

| profile | ภาคที่มี independent partial labels | total/checked pattern | UI identity + paired citations |
| --- | ---: | --- | --- |
| AI-2566-coop | 8 | 8/8; mismatch0 | ผ่าน |
| BIT-2565-coop | 8 | 8/8; mismatch0 | ผ่าน |
| BIT-2565-no-coop | 8 | 8/8; mismatch0 | ผ่าน |
| DSBA-2565-coop | n/a | n/a | ผ่าน |
| DSBA-2565-no-coop | n/a | n/a | ผ่าน |
| IT-2565-coop | n/a | n/a | ผ่าน |
| IT-2565-no-coop | n/a | n/a | ผ่าน |
| DSBA-2560-coop | 8 | 8/8; mismatch0 | ผ่าน |
| DSBA-2560-no-coop | 9 | 9/9; mismatch0 | ผ่าน |
| IT-2560-coop | 8 | 8/8; mismatch0 | ผ่าน |
| IT-2560-no-coop | 8 | 8/8; mismatch0 | ผ่าน |
| BIT-2560-coop | 8 | 8/8; mismatch0 | ผ่าน |
| BIT-2560-no-coop | 8 | 8/8; mismatch0 | ผ่าน |
| legacy | n/a | ไม่ rebuild; identity ยังไม่ยืนยัน | ไม่อยู่ใน selector ตามระบบเดิม |

รวม73/73ภาคและ checked code/hour-pattern mismatch0 จาก partial labels ไม่เท่ากับความถูกต้องทุก field ทุกเล่ม UIตรวจ13profilesจริงบน isolated8003: selection, rendered first-term answer, paired folios, console errors0; ไม่ได้ตรวจทุกคำถามทุก UI stateในรอบนี้

- isolated rebuilt API: AI/BIT39/39development cases, old2560 65/65, graduation-reference disclosure39/39 ไม่ใช่ full graduation eligibility
- fresh AI: OCR4หน้าใหม่ → Qwen JSON → approved ingestion → DB สำเร็จ174.63s; source comparison8/8ภาค/mismatch0; API13/13 และ UIแสดง4แถว Y4S1 พร้อม90644xxx/xxxxxxxxและPDF26/book22ถูกต้อง
- shared regressionหลัง final guard:168unit/30schema/6frontend/70gold/65old/provenance14/version6 ผ่านและ dependency hashes คงเดิม ณเวลารัน; repo-only unit155ผ่านและ skipped2integration suites เพราะไม่มี local DB ไม่เอาสองจำนวนนี้มารวม
- provenance14catalogs: changed/added non-SQL fields0, unmatched rows0; ไม่รับประกันทุกคำถามหรือทุกช่องในหนังสือ
- final live-backed gold L1/L2 successful timing n52 median535.78ms/p95571.12ms; freshAI structured13ข้อ median28.18ms/p9544.76ms ไม่ใช่ cold/hard LLM benchmark

freshAI logsแยก model calls ได้: OCR4callsรวม70.9s, Qwen JSON8callsรวม96.6s (ผลบวกเวลาที่ logปัดหนึ่งตำแหน่ง) ที่เหลือเป็น overheadหลายขั้น ไม่รายงานเป็น build-only latency และไม่รวม preprocessing174.63sเข้ากับ latencyต่อคำถาม

หลักฐาน: [rebuild manifest](results/current_source_20261008/reconstruction-release/reconstruction.json), [source comparison](results/current_source_20261008/rebuilt_labels_release.json), [UI13profiles](results/current_source_20261008/rebuilt_ui.json), [freshAI manifest](results/current_source_20261008/fresh-ai/reconstruction.json), [freshAI comparison](results/current_source_20261008/fresh_ai_labels.json), [freshAI API](results/current_source_20261008/current-fresh-aiqa.json), [freshAI UI](results/current_source_20261008/fresh_ai_ui.json), [shared raw](results/current_source_20261008/checks-final-guard/checks.json), [final unit](results/current_source_20261008/current-source-20261008-unit-live-final.log)

## สถานะเจ็ดงานที่เหลือ

รอบ descriptions/ingestion ที่ทำต่อจากรายงานนี้: [ผลล่าสุด](SOURCE_DESCRIPTION_CONTINUATION.md) ยืนยัน9unique course facts/13profile-course cases พร้อม live API13/13, unit179 และ source-approved catalog scope โดยไม่เพิ่มแผน no-coop ไม่มี freshOCR/full-book/held-out completion ใหม่; ตารางงานคงค้างด้านล่างยังใช้ได้ ยกเว้น partial AI/BIT prerequisite coverage ที่เพิ่มตามรายงานใหม่

| งาน | ผลที่ยืนยัน | ยังขาด |
| --- | --- | --- |
| reconstruction | isolated saved-OCR13/13; freshAI1profileสำเร็จ | freshOCRอีก12profiles, reproducibilityเมื่อ generation เปลี่ยน และ legacy rebuild |
| citations |127plan folios,13UI paired references,7PDF transportที่ตรวจไว้ | program summary11/13foliosยังไม่ครบ; visible PDF viewerยังn/a |
| broad source Q&A/L3–L4 | current39/old65development +39reference disclosure | ทุกชื่อ/prerequisite/category/graduation, independent planning/comparison; sourceไม่มี AIold/same-yearrevision/dual-degree ที่ยืนยัน |
| untouched held-out | frozen inputsไม่เปลี่ยน | independent coverageข้ามทุกเล่ม; ชุดเคยdebugไม่กลายเป็นheld-outเพราะรันซ้ำ |
| timeout/performance | budget shared +3focused tests +health/client integration | exhaustionจริง, cold/warm hard generation median/p95; ไม่อ้างโบนัส<5s |
| legacy | retained6147stored fragments; safety regression5ข้อผ่าน | identity/year/source context และ faithful parser/retrieval; ไม่ถือ safety pass เป็นlegacy QA correctness |
| setup/handoff | rootREADME safe isolated commands; actual reconstructed runtime/UI | freshinstall/reboot/modelcold รอบใหม่นี้ยังn/a; prior freshvenvเป็นหลักฐานคนละbatch ไม่ใช่ freshOCRทุกเล่ม |

audit liveเดิมยัง exit1:16datasets, FAIL1372/incomplete4881 อ่านเฉพาะ Summary/HIGH; จำนวนนี้ไม่ใช่ wrong answers และไม่ลบทิ้งเพื่อให้ผลดูดี ข้อมูล prerequisiteยังมี coverageต่ำมาก การไม่มี edgeไม่ใช่หลักฐานว่าไม่มี prerequisite

## ความปลอดภัยและการส่งต่องาน

- isolated rebuild/fresh jobs ตรวจ hash ของ working DB/OCR/PDF และ protected_unchanged=true ไม่ deploy DB ที่ rebuild ทับ working databases
- citation-only deploymentมี recoverable SQLite backups/integrity/fact fingerprint; backup manifestอยู่ `<TEMP>/current-plan-pairs-20261008-deploy-closed/manifest.json` ของเครื่องที่ทำงาน ไม่ใช้ pathนี้เป็นคำสั่งติดตั้ง
- original failed runs/logs และ page checkpointsยังเก็บใน isolated TEMP; อย่าลบก่อนประเมินการ resume
- README rootแก้คำอธิบาย timeoutและเพิ่ม reconstruction commands ไม่แก้ generated EVAL/Lab09ด้วยมือ ไม่สร้าง slides/video ไม่ publication
- checkpointและคำสั่ง resume: [docs/PROGRESS.md](PROGRESS.md)

ขั้นถัดไปคือ independent source review ของชื่อ/prerequisite/เงื่อนไขจบ ไม่ใช่ปรับ gold ให้ตรงผลแอป และต้องทดสอบ remaining fresh profiles ใน outputใหม่โดยไม่ใช้ labelsเป็น production facts
