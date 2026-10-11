# ผลตรวจแผน IT-2565 และการแก้ไขต่อเนื่อง

วันที่ 9 ตุลาคม 2026 — branch `week11_thanapat`, HEAD `37b3ad5` ไม่มี commit, push หรือ merge ในรอบนี้ รายงานนี้ไม่ใช่ checkpoint; สถานะที่ใช้ทำงานต่ออยู่ใน [PROGRESS.md](PROGRESS.md)

## ขอบเขตและตัวหาร

ใช้ `curriculum-audit` และตรวจภาพหน้าหนังสือจริง ไม่ใช้ OCR หรือคำตอบแอปเป็นเฉลยอิสระ ภาพหลักฐานและผลดิบอยู่ใน [results/it_plan_review_20261009](results/it_plan_review_20261009/)

| หลักสูตร/แผน | ภาคที่ตรวจใหม่ | ภาคสะสม | ตัวเลือกรายวิชาในแผน | รหัสจริงไม่ซ้ำ | หน่วยกิต |
|---|---:|---:|---:|---:|---:|
| IT-2565 สหกิจศึกษา | 6 | 8/8 | 54 | 47 | 129 |
| IT-2565 ไม่สหกิจศึกษา | 6 | 8/8 | 54 | 45 | 129 |
| DSBA-2565 สหกิจศึกษา | 1 ที่เคยติดขัด | 8/8 | 45 | 36 | 132 |
| DSBA-2565 ไม่สหกิจศึกษา | 0 ใช้ผลเดิม | 8/8 | 45 | 34 | 132 |

ตัวเลือกในตารางรวมทางเลือกและกลุ่มที่ใช้รหัสซ้ำ ไม่ใช่จำนวนรายวิชาที่ต้องลงทั้งหมด ห้ามรวมหน่วยกิตของหลาย specialization หรือหลายแผนเข้าด้วยกัน ภาคที่ตรวจครบไม่ใช่การตรวจ catalog, prerequisites หรือเงื่อนไขจบครบทั้งเล่ม

IT ใช้ภาพ PDF25/26/28/29/33/34/40/41/42 ที่ตรวจรอบนี้ และภาพ 35/36/37/43/44 ที่มีหลักฐานเดิม รวม 14 หน้าที่นำมาใช้ในรอบนี้ แผนทั้งสองอยู่ PDF31–44 / หน้าหนังสือ 26–39 หลักฐานหลายหน้าของแต่ละภาคบันทึก hash แยกกัน ไม่ใช้สูตรลบเลขหน้ามาทำ citation โดยไม่มีการตรวจคู่หน้า

## ข้อค้นพบจากต้นฉบับ

- PDF25 / หนังสือ20: เลือก specialization หนึ่งกลุ่ม 15 หน่วยกิต ไม่รวม software, infrastructure และ multimedia พร้อมกัน
- PDF29 / หนังสือ24: กลุ่มอาชีพของวิชาเลือกต่างจาก specialization บังคับ สามารถเลือกข้ามกลุ่มตามข้อความต้นฉบับได้
- สหกิจ 06016481 หรือ 06016482 อยู่ PDF42–43 / หนังสือ37–38 นับ 6 หน่วยกิตครั้งเดียว เงื่อนไขอนุมัติใช้หลักฐานโครงสร้างที่ตรวจไว้ ไม่สร้างสิทธิลงทะเบียนเพิ่ม
- ชั่วโมงของวิชาเลือกที่พิมพ์เป็นทางเลือกยังอยู่ใน labels ไม่ทำให้เหลือเพียง pattern เดียว
- DSBA สหกิจ ปี4/1 PDF36 / หนังสือ35 มี 06026215 โครงงาน 2 จำนวน 3 หน่วยกิต และอีกสาม elective slots รวม 12 หน่วยกิต ทั้งภาพ Poppler ใหม่และภาพ PyMuPDF เดิมมองเห็นแถวนี้ ข้อสรุปเดิมว่าแหล่งข้อมูลขาดเป็นการอ่านภาพคลาดเคลื่อน ไม่ใช่ viewer defect หรือข้อมูลที่ยืมจากแผนไม่สหกิจศึกษา

## สาเหตุและการแก้ไข

| สาเหตุ | การเปลี่ยนแปลง | หลักฐาน/ขอบเขต |
|---|---|---|
| Citation ingestion ขาด printed folio | source approval ใหม่และ migration แยกจากเฉลย evaluation | 38 citation fields ใน 2 DB; QA จาก 4/12 เป็น 12/12 โดย credit totals ถูกอยู่แล้ว 12/12 |
| OCR/relationship ingestion ชื่อไม่ตรงต้นฉบับ | names-only approved ingestion หลัง relationship migration | 4 รหัสจริง / 6 profile-course cases; เปลี่ยน 16 name fields ใน course และ plan_item; fingerprint ของ facts อื่นและ prerequisites ไม่เปลี่ยน |
| Checker อ่าน representation ไม่ครบ | fallback ชื่อ/credit pattern จาก course และตรวจ elective multiplicity/alternative groups | เก็บผล 199 และ 44 mismatches เดิมไว้; ไม่ตีความว่าเป็นจำนวนคำตอบผิด |
| UI selection ขัดกับปีที่ถาม | ตรวจ explicit year กับ metadata ของ selector; comparison และ all versions ยังใช้ได้ | browser แสดงข้อผิดพลาดภาษาไทย และตอบเฉพาะปี2560 หลังเลือกปีถูกต้อง; `/api/ask` contract เดิม |
| Manifest ไม่ได้นับ locators ที่ตรวจแล้ว | นำ approved page pairs มาใช้เมื่อ dependency hash ตรงเท่านั้น | นำ IT34/41/42 กลับเข้าขอบเขต; ไม่คัดลอกข้อเท็จจริงจาก evaluation เข้า production |

ชื่อที่แก้: 06016409 เพิ่มคำว่า “ผล” ตามต้นฉบับ, 06016423 ใช้ “การออโตเมชัน...” ตามหน้าหนังสือแทนคำแปลใน relationship เก่า และแยกชื่อไทย/English ของสหกิจ 06016481/82 ที่ OCR รวมกัน ไม่มีการประกาศว่า manual corrections เป็นการเพิ่ม OCR accuracy

## ผลที่วัดจริง

| การตรวจ | ผล | หลักฐาน |
|---|---|---|
| IT semester API + paired citation | 12/12 | `coop-fixed-qa.json`, `no-coop-fixed-qa.json` |
| IT ชื่อที่แก้ ผ่าน API จริง | 6/6 | `names-fixed-qa.json` และภาพ `name-fixed-ui.png` |
| DSBA ภาคที่ติดขัด ผ่าน API จริง | 2/2 | ผล DSBA resolved QA และ `dsba-resolved-ui.png` |
| Isolated saved-OCR rebuild | 2/2 profiles; integrity 2/2; totals 12/12; reviewed-field mismatches 0 | `rebuild-final/reconstruction.json`, `final-rebuilt-reviewed-fields.json` |
| Unit / schema / frontend | 209 / 30 / 6 ผ่าน | `shared-checks/checks.json` |
| Gold development regression | 70/70, 14 profiles × 5 | `shared-checks/gold.json` |
| Older2560 regression | 65/65, 6 profiles | `shared-checks/old2560.json` |
| SQL replay provenance | 14 profiles, changed/added fields 0, unmatched rows 0 | `shared-checks/provenance.json` |
| Version sets | 6/6 | `shared-checks/version_sets.json`; independent book accuracy ยัง n/a |
| Dependency guard | ทั้ง 7 jobs exit0 และ `dependencies_unchanged=true` | เก็บ failed guard ก่อนหน้าไว้ที่ `results/viewer_source_20261009/shared-checks/` ไม่เขียนทับ |

ผล rebuild ใช้ OCR ที่มีอยู่ ไม่ใช่ fresh relevant-page OCR; inputs ที่ป้องกันไว้ไม่เปลี่ยน (`protected_unchanged=true`) เป็นความถูกต้องของ reviewed ingestion ใน fields ที่ตรวจ ไม่ใช่ raw OCR accuracy หรือการตรวจ catalog ทั้งหมด

Latency ที่วัดเป็น structured warm L2: IT ไม่สหกิจ n=6 median501.19 ms / p95516.83 ms; สหกิจ n=6 median491.44 ms / p95500.52 ms; ชื่อที่แก้ n=6 median558.47 ms / p95581.08 ms; DSBA n=2 median540.04 ms / p95546.33 ms ไม่ใช่หลักฐานผ่านเกณฑ์ difficult question cold/warm <5s

## Viewer และ browser

กด citation จากผลตอบจริง เปิด viewer และดูเนื้อหาหน้าได้จริง 5/5 ไฟล์ที่เหลือ: DSBA36/35, DSBA-60 34/29, IT40/35, IT-60 28/23, BIT-60 26/21 (เลขแรก PDF / เลขหลังหนังสือ) บันทึก DOM, ขนาดภาพ, screenshot และ console ใน `viewer-browser.json` และ PNGs ไม่ใช้ HTTP200 เป็นข้อพิสูจน์การแสดงผล ผล AI และ BIT-65 ที่ dependencies ไม่เปลี่ยนใช้หลักฐานเดิม ดังนั้นครบ 7 source files ในขอบเขต representative pages ไม่ได้ตรวจ viewer ทุกหน้า

ภาพ `version-conflict-fixed-ui.png` และผล `version-conflict-fixed-ui.json` / `version-recovery-ui.json` แสดง error และ recovery จริง ไม่เพิ่ม mock response

## ขอบเขตที่ยังเปิด

- Page manifests: 7 หนังสือ / 2,322 physical pages; include86, skip0, unreviewed2,236 หน้าที่ไม่ตรวจไม่ใช่ irrelevant และไม่ตัด appendices อัตโนมัติ
- Working IT ยังมี placeholder metadata เก่า แม้ isolated rebuild fields ที่ตรวจผ่านแล้ว ต้องตรวจ diff และแก้ ingestion แบบ targeted ไม่เขียนทับ DB ทั้งก้อนโดยไม่รักษา user work
- Broad prerequisites และ logical relationships ยังไม่ครบ; missing ไม่เท่ากับ “ไม่มี”; BIT English Exit thresholds ยังไม่ยืนยัน
- Fresh relevant-page OCR ทุก profile, untouched held-out final evaluation, real unknown-LLM mutation/removal/failure provenance, difficult cold/warm latency, actual timeout exhaustion/process interruption, legacy identity และ clean first installation ยังไม่เสร็จ/บางส่วน n/a
- การตรวจ code พบว่า builtin `TimeoutError` จาก shared deadline ยังไม่มี handler โดยตรงใน `/api/ask` และ `/ask` ต้อง reproduce ด้วย positive budget และ model จริงก่อนสรุปผล runtime และแก้พร้อม regression; ยังไม่ประกาศว่าแก้แล้ว
- ไม่ทำ slides/video/publication ตามข้อกำหนด

## ไฟล์และการทำต่อ

Source observations และ exported development labels อยู่ `ocr_final/data/ground_truth/evaluation/semester-review-20261009-b/`; production approvals แยกใน `ocr_final/data/source_reviews/`. เปลี่ยน `run_lab8b.py`, manifest/export/readonly-check scripts, เพิ่ม names ingestion และ frontend selector guard พร้อม tests ที่เกี่ยวข้อง runtime changes port ไป LIVE แล้ว

Backups SQLite 4 ไฟล์เก็บใน `results/it_plan_review_20261009/backups/` แยก before-citations / before-names ทั้งสองแผน และตรวจ SHA ตรงกับ deployment manifests ห้ามนำ .db เหล่านี้ไปเผยแพร่โดยอัตโนมัติ Rollback ต้อง backup current DB และตรวจการเปลี่ยนแปลงใหม่ก่อน หยุดเฉพาะ backend ที่ยืนยัน ownership แล้ว

คำสั่งที่ทำจริงและคำสั่ง resume อยู่ [PROGRESS.md](PROGRESS.md#6-how-to-rerun--rollback) โดยตรวจ hash/dependencies ก่อนใช้ `--resume` ห้าม rerun batches ที่ผ่านแล้วโดยไม่มี dependency change
