# การตรวจชุด development 14 หมวด — 2026-10-09

ชุดนี้เปิดเผยเพื่อ debugging ไม่ใช่ held-out และไม่ใช้ expected answers เป็น production facts. การจัดกลุ่มด้านล่างเป็น triage ไม่ใช่การรับรองว่าคำตอบทั้งหมดถูกต้องตามหนังสือ.

Baseline: 14 wordings / 196 scoped questions / 14 reasoning categories / 392 HTTP requests.
คำถามเดียวกันที่ส่งสอง routes ไม่ใช่ reasoning task ใหม่; scope ต่างกันต้องตรวจ DB/version/plan แยก.

| หมวด | HTTP requests | HTTP200 | technical failure | unrelated program answer | ยังต้องตรวจเนื้อหา |
|---|---:|---:|---:|---:|---:|
| `semester_aggregation` | 28 | 3 | 25 | 0 | 3 |
| `shared_specialization` | 28 | 12 | 16 | 0 | 12 |
| `elective_alternatives` | 28 | 28 | 0 | 0 | 28 |
| `plans_comparison` | 28 | 3 | 25 | 0 | 3 |
| `prerequisite_logic` | 28 | 28 | 0 | 0 | 28 |
| `multi_condition` | 28 | 28 | 0 | 0 | 28 |
| `name_paraphrase` | 28 | 28 | 0 | 26 | 2 |
| `minor_typo` | 28 | 11 | 17 | 0 | 11 |
| `misleading_assumption` | 28 | 28 | 0 | 0 | 28 |
| `graduation_partial` | 28 | 28 | 0 | 0 | 28 |
| `accelerated_plan` | 28 | 3 | 25 | 0 | 3 |
| `version_comparison` | 28 | 28 | 0 | 26 | 2 |
| `unsupported_description` | 28 | 28 | 0 | 26 | 2 |
| `cross_version_trap` | 28 | 10 | 18 | 3 | 7 |

## ผลหลังแก้และข้อจำกัดที่ยังเปิด

- Baseline มี technical failures126/392 และคำตอบ program ที่ไม่เกี่ยวกับคำถาม81/392; อีก185requests ยังไม่ได้รับรองความครบถ้วนเป็นรายคำตอบ (28เป็น partial graduation rules ที่เปิดเผยข้อจำกัด). ตัวเลขนี้เป็น conservative triage ไม่ใช่ accuracy ตามหนังสือ.
- แก้ Thai written numbers/multiple semesters, minimum-credit filtering และ program-context misrouting โดยไม่เปลี่ยน SQL validator/API contract/DB/schema/held-out. แก้ renderer ให้แสดง name_en เมื่อร้องขอ และไม่คืนคำตอบว่างเมื่อ schema เก่าไม่มี fields ที่ต้องใช้.
- Rerun semester/filter56HTTP:52/56ตรง selected SQLite ตามตรวจ rows/credits/course sets; อีก4เป็น legacy ที่ไม่มี verified study-plan schema. ไม่ใช่ source-independent accuracy. [raw + DB-relative checks](results/diverse_development_20261009/after-filters/db-review.json).
- Rerun English names28HTTP:26/28ผ่าน course-set/English-name checks; legacy2ยังไม่ผ่าน. [raw](results/diverse_development_20261009/after-english/results.json), [checks](results/diverse_development_20261009/after-english/db-review.json).
- Rerun context3categories×4profiles×2routes=24HTTP:3HTTP200/16HTTP422/5HTTP504. การไม่คืน program name ที่ไม่เกี่ยวข้องไม่เท่ากับแก้ fallback ครบ; parameter placeholders, schema/filter generation, version comparison และ timeout ยังเปิด. ไม่อ้างว่า HTTP200ทั้ง3เป็น substantive passes. [raw](results/diverse_development_20261009/context-after/results.json).
- ใน live UI ตรวจ AI-2566-coop: ปี2ภาค1=18/ภาค2=19/ผลต่าง1พร้อมรายการและ PDF24/book20; filterปี2credits>=3แสดง12coursesและ12citation entries; English namesอยู่ในรายละเอียดที่เปิดได้. UI timings920/981msและ1860/1917msเป็นสอง structured requests ไม่ใช่ difficult cold/warm SLA. [comparison](results/diverse_development_20261009/after-written-number-ui.png), [English details](results/diverse_development_20261009/after-english-expanded-ui.png).

| Profile | Baseline reasoning categories | Baseline HTTP | Semester/filter DB-relative checks | English filter checks |
|---|---:|---:|---:|---:|
| legacy-course-catalog | 14 | 28 | 0/4 | 0/2 |
| AI-2566-coop | 14 | 28 | 4/4 | 2/2 |
| BIT-2560-coop | 14 | 28 | 4/4 | 2/2 |
| BIT-2560-no-coop | 14 | 28 | 4/4 | 2/2 |
| BIT-2565-coop | 14 | 28 | 4/4 | 2/2 |
| BIT-2565-no-coop | 14 | 28 | 4/4 | 2/2 |
| DSBA-2560-coop | 14 | 28 | 4/4 | 2/2 |
| DSBA-2560-no-coop | 14 | 28 | 4/4 | 2/2 |
| DSBA-2565-coop | 14 | 28 | 4/4 | 2/2 |
| DSBA-2565-no-coop | 14 | 28 | 4/4 | 2/2 |
| IT-2560-coop | 14 | 28 | 4/4 | 2/2 |
| IT-2560-no-coop | 14 | 28 | 4/4 | 2/2 |
| IT-2565-coop | 14 | 28 | 4/4 | 2/2 |
| IT-2565-no-coop | 14 | 28 | 4/4 | 2/2 |

## สาเหตุแยกตามชนิด

1. Code/retrieval: routingผิดและyear/semester Thai numbers แก้ในขอบเขตข้างต้น. Unnecessary abstentionsยังมี เช่น electives/shared specialization ที่ DB มี plan rows/study_track แต่ queryค้นชื่ออย่างผิดประเภท. `prerequisite_logic` จับคำว่า “ที่” เป็นชื่อวิชาและแสดง unrelated candidates; ต้องแก้ grammar/retrieval ไม่ใช่เพิ่ม prerequisite facts.
2. SQL/LLM: context rerunยังสร้าง `?` bindingsโดยไม่มีparameters, redundant/unsupported program filters และไม่ได้เทียบทั้งสองversion. Strict validatorยังปฏิเสธ ไม่แก้ด้วยการปล่อย SQL ที่ไม่ผ่าน.
3. Missing DB content: readonly inventoryใน [JSON](DIVERSE_DEVELOPMENT_20261009.json) พบ course.description_th nonempty0ใน13program DBs; ไม่มีหลักฐานหัวข้อสอบ/ภาษาที่อาจารย์จะใช้เทอมหน้า. Missing descriptionsแยกจาก retrieval failure; ไม่เพิ่มเนื้อหาเพื่อให้ probeผ่าน. Prerequisite edgesไม่ครบ/ไม่มีlogicoperator ไม่อนุมานว่าNONEหรือAND/OR.
4. Source ambiguity: legacy source/versionยังไม่ยืนยัน; first-machine install, independent held-out และ difficult cold/warm timingsยัง n/a. Model concurrency/coldnessของcontext/OCR batchไม่ได้ควบคุม จึงไม่ใช้ latencyนี้เป็น SLA.

## Reconstruction และ startup

- Final dependency-locked regressions:243unit/schema30/frontend6/gold70/old2560QA65/provenance14/version sets6 ผ่าน7jobs exit0/dependencies unchanged. [raw checks](results/diverse_development_20261009/checks-locked/checks.json). ไม่ทดแทน semantic review185requests หรือ held-out evaluation. Failed2unit runเดิมอยู่ `regression-after/checks.json`; restart-during-oldQA failureอยู่ `checks-restart-failed/checks.json` (connection resetขณะ restartLIVE); ไม่เปลี่ยน gold labelsเพื่อแก้ failures.

- Raw OCRแยก descriptions/regulationsจากstudy-plan normalization; new manifest-aware wrapperยังไม่ได้verify end-to-endทุกprofile. Page hashes/source/model/configตรงก่อนreuse, ไม่overwrite working DB.
- BIT-65 manifest15include/0skip/302unreviewed: raw12uniqueprocessed (PDF26–35,77,87),5ใช้fresh baseline checkpoints และ7freshต่อเนื่อง;หลังownedprocesskillมีresumeผ่านหลายหน้าแต่full recoveryยังไม่ผ่าน. PDF93failed model500; actual error body “prediction aborted, token repeat limit reached”. [original kill/resume](results/manifest_bit_recovery_20261009/recovery.json), [error body](results/manifest_bit_recovery_20261009/page93-error-body.json).
- ต่อ independent pagesในoutputใหม่ด้วยmatching page checkpoints: PDF93/238/257ยังmodel500ทั้ง3; processed12/pending3/failed3/skip0/unreviewed302/source unchanged. ไม่ตีความfailedเป็นirrelevantและไม่ปรับsecurity/model files. [state](results/manifest_bit_remaining_20261009/manifest-extraction.json).
- Raw textเหล่านี้ยังไม่ได้score CER/WER/field accuracyด้วยindependent transcription; source-reviewed fixesไม่ใช่OCR improvements. Manifestsทั้ง7เล่ม87include/2322physical/0skip/2235unreviewed ไม่ใช่full-book review.
- Missing-model readinessfalse/2routes503/models unchangedผ่านก่อนและหลังprecise error fix; Thai root READMEบอกขั้นตอนpull/startและfirst-machine limitation. ไม่มีการดาวน์โหลด/ลบinstalled modelในverificationนี้.
- Failed OneDrive write และ failed restart-during-checks preserved; activejobsรันในTEMPแล้วcopy JSON/logกลับrepo. NoGitlockfailure/no commit/push/merge. Working databases/held-out/source PDFs unchanged.

## ตัวอย่างก่อน–หลังจากผลจริง

ไม่ปรับถ้อยคำคำตอบจริงให้ดูดีขึ้น; SQL/rows เต็มอยู่ใน raw JSON. ก่อนหรือหลังที่ไม่มีบันทึกระบุว่า not recorded.

### `semester_aggregation` — AI-2566-coop

หลักสูตร AI 2566 สหกิจ: ปีสอง เทอมหนึ่งกับเทอมสอง หน่วยกิตเท่ากันไหม แสดงรายการที่ใช้รวมและวิธีคิดด้วย

ก่อนแก้

```text
ไม่สามารถค้นฐานข้อมูลได้: AI-2566-coop: Unknown intent only permits stored-column projections, not invented literals/calculations
```

HTTP 422; end-to-end 9675.29 ms; raw case `AI-2566-coop-0-/api/ask`.

หลังแก้

```text
AI-2566-coop ปี 2 ภาค 1: 18 หน่วยกิต (ที่มา: AI.pdf หน้า 24); รายการที่ใช้คำนวณ: 06066300=3, 06046405=3, 06046406=3, 06046409=3, 06046413=3, 90641009=3; นับแต่ละกลุ่มทางเลือกเพียงหนึ่งตัวเลือก; ยอดรวมจากแถว semester ใน SQLite; AI-2566-coop ปี 2 ภาค 2: 19 หน่วยกิต (ที่มา: AI.pdf หน้า 24); รายการที่ใช้คำนวณ: 06046407=3, 06046408=3, 06046410=3, 06046412=3, 06046411=3, 90641010=3, 90641005=1; นับแต่ละกลุ่มทางเลือกเพียงหนึ่งตัวเลือก; ยอดรวมจากแถว semester ใน SQLite; AI-2566-coop: ผลต่าง = 19 - 18 = 1 หน่วยกิต
```

HTTP 200; end-to-end 54.50 ms; raw case `AI-2566-coop-0-/api/ask`.

### `multi_condition` — AI-2566-coop

หลักสูตร AI 2566 สหกิจ: ขอวิชาบังคับที่อยู่ปี 2 หน่วยกิตอย่างน้อย 3 และแสดงชื่ออังกฤษกับแหล่งอ้างอิง

ก่อนแก้

```text
AI-2566-coop: 37 หน่วยกิต (ที่มา: AI.pdf,AI.pdf หน้า 24,24)
```

HTTP 200; end-to-end 56.77 ms; raw case `AI-2566-coop-5-/api/ask`.

หลังแก้

```text
AI พ.ศ. 2566 — ปี 2 ภาคการศึกษาที่ 1 — แผนสหกิจศึกษา
รายวิชาตามข้อมูลที่นำเข้า
- 06046405 การเรียนรู้ของเครื่องเชิงความน่าจะเป็น (PROBABILISTIC MACHINE LEARNING) — 3 หน่วยกิต
- 06046406 พื้นฐานการเรียนรู้เชิงลึก (FUNDAMENTALS OF DEEP LEARNING) — 3 หน่วยกิต
- 06046409 คอมพิวเตอร์วิทัศน์เบื้องต้น (INTRODUCTION TO COMPUTER VISION) — 3 หน่วยกิต
- 06046413 ปัญญาประดิษฐ์และอินเทอร์เน็ตประสานสรรพสิ่ง (ARTIFICIAL INTELLIGENCE AND INTERNET OF THING) — 3 หน่วยกิต
- 06066300 แนวคิดระบบฐานข้อมูล (DATABASE SYSTEM CONCEPTS) — 3 หน่วยกิต
วิชาศึกษาทั่วไป
- 90641009 ทักษะการสื่อสารภาษาอังกฤษระหว่างวัฒนธรรม 1 (INTERCULTURAL COMMUNICATION SKILLS IN ENGLISH 1) — 3 หน่วยกิต
AI พ.ศ. 2566 — ปี 2 ภาคการศึกษาที่ 2 — แผนสหกิจศึกษา
รายวิชาตามข้อมูลที่นำเข้า
- 06046407 พื้นฐานวิทยาการข้อมูล (FUNDAMENTALS OF DATA SCIENCE) — 3 หน่วยกิต
- 06046408 การแสดงข้อมูลด้วยแผนภาพ (DATA VISUALIZATION) — 3 หน่วยกิต
- 06046410 การประมวลผลภาษาธรรมชาติเบื้องต้น (INTRODUCTION TO NATURAL LANGUAGE PROCESSING) — 3 หน่วยกิต
- 06046411 การวิเคราะห์และเพิ่มประสิทธิภาพเครือข่าย (NETWORK ANALYSIS AND OPTIMIZATION) — 3 หน่วยกิต
- 06046412 การเพิ่มประสิทธิภาพโครงข่ายประสาทเทียม (NEURAL NETWORK OPTIMIZATION) — 3 หน่วยกิต
วิชาศึกษาทั่วไป
- 90641010 ทักษะการสื่อสารภาษาอังกฤษระหว่างวัฒนธรรม 2 (INTERCULTURAL COMMUNICATION SKILLS IN ENGLISH 2) — 3 หน่วยกิต
```

HTTP 200; end-to-end 53.54 ms; raw case `AI-2566-coop-0-/api/ask`.

### `name_paraphrase` — AI-2566-coop

หลักสูตร AI 2566 สหกิจ: อยากเรียนเขียนโปรแกรม มีวิชาชื่อใกล้เคียงกันอะไรบ้าง ถ้าหลายตัวให้ช่วยแยกให้เลือก ไม่ต้องเดาว่าหมายถึงตัวไหน

ก่อนแก้

```text
AI: เทคโนโลยีปัญญาประดิษฐ์ (ที่มา: AI.pdf หน้า 26)
```

HTTP 200; end-to-end 79.18 ms; raw case `AI-2566-coop-6-/api/ask`.

หลังแก้

```text
ไม่สามารถค้นฐานข้อมูลได้: AI-2566-coop: Incorrect number of bindings supplied. The current statement uses 2, and there are 0 supplied.
```

HTTP 422; end-to-end 7162.17 ms; raw case `AI-2566-coop-0-/api/ask`.

### `unsupported_description` — AI-2566-coop

หลักสูตร AI 2566 สหกิจ: ขอตัวอย่างหัวข้อสอบและภาษาโปรแกรมที่อาจารย์จะใช้สอนเทอมหน้า โดยอ้างเฉพาะข้อมูลหลักสูตรที่บันทึก

ก่อนแก้

```text
AI: เทคโนโลยีปัญญาประดิษฐ์ (ที่มา: AI.pdf หน้า 26)
```

HTTP 200; end-to-end 74.35 ms; raw case `AI-2566-coop-12-/api/ask`.

หลังแก้

```text
ไม่สามารถค้นฐานข้อมูลได้: AI-2566-coop: SQL added a filter value not present in the question: 'AI-2566-coop'
```

HTTP 422; end-to-end 5070.63 ms; raw case `AI-2566-coop-2-/api/ask`.
