# IT whole-bundle และ source review ของหลักสูตร 2560 — 11 ตุลาคม 2026

## ผลที่ตรวจจากต้นฉบับจริง

เป็น **native PDF text/table extraction + reviewed font decoding** ไม่ใช่ vision OCR ไม่มี course corrections, saved OCR, working DB metadata, master หรือ evaluation เป็น build input ทุก sandbox เริ่ม DB=0 ตรวจภาพปกและทุกหน้าเทียบ SQLite ก่อน receipt ไม่ใช้ receipt เติมข้อเท็จจริงหลัง SQL

| Profile | PDF / หน้าเล่ม | แถว SQLite / terms | ผล |
|---|---|---|---|
| IT2565 no-coop | 31–37 / 26–32 + กฎ PDF25/20 | 54 / 8 | source-certified + scoped activation + API/restart |
| IT2565 coop | 38–44 / 33–39 + กฎ PDF25/20 | 54 / 8 | source-certified + scoped activation + API/restart |
| DSBA2560 no-coop | 25–29 / 20–24 | 44 / **9** | source-certified + scoped activation + API/restart |
| BIT2560 no-coop | 23–26 / 18–21 | 42 / 8 | source-certified + scoped activation + API/restart |
| BIT2560 coop | 27–30 / 22–25 | 42 / 8 | source-certified + scoped activation + API/restart |
| DSBA2560 coop | 30–34 / 25–29 | 44 / 8 | scoped source/API/lifecycle ผ่านรอบก่อน; ไม่ rerun batch เดิม |
| IT2560 ทั้งสองแผน | page relevance ตรวจแล้ว | 0 certified | Thai font2ชุดตรวจglyphแล้วในreviewแยก; supporting-rule scan ติดWingdings2 PDF17; ห้ามเดาsymbol/คัดลอกDBเติม |

## General fixes และหลักฐาน

SQLite เก็บ `plan_bundle`, `plan_bundle_member`, `plan_source_claim`, `plan_term_source` กลุ่ม specialization มาจาก geometry/ข้อความใน source ไม่ใช้ course map กฎเลือกทั้งกลุ่มมาจาก PDF25/หน้าเล่ม20 รหัสร่วมอยู่ได้หลายกลุ่มโดยแต่ละ membership เป็นคนละแถว ไม่แปลงเป็น independent ordinal choices ไม่อนุมานสิทธิลงทะเบียน

PDF35→36 เก็บ code/name จาก35และ hour continuation จาก36; PDF42→43 แยก Thai name/code แรกจาก42, English continuation/alternative code จาก43 รวมทั้ง provenance ของแต่ละ claim และ printed total จาก43 รายวิชาทางเลือกนับหนึ่งทางเลือก; specialization นับหนึ่งชุดทั้งกลุ่ม Credits129ทั้งสองแผน ไม่มีการบวกกลุ่มที่เลือกแทนกัน

DSBA2560 no-coop PDF28/หน้าเล่ม23 มีปี3/ภาค3 จริง: เก็บ9termsและ126credits การตรวจ scoped plan ต้องมี8regulartermsครบ; extra term ต้องตรง source-backed totals และ native artifact→SQL chain ครบ ไม่ลด full14 gate ไม่แก้คำสะกด/ชื่อผิดในต้นฉบับโดยพลการ

## Runtime และ recovery แยกจาก extraction

IT source-only release candidate `20261011T081312-474565cd16`: sourceimages/raw/factualSQLiteเท่ากับรอบ visual review ที่ตรวจครบ108แถว; SQL choice count แก้แล้วและ execute-test ผ่าน 32 HTTP จริงทั้ง `/ask` และ `/api/ask` สองแผน/สอง cycles ตรวจ6วิชาใน bundle terms และ1วิชาสหกิจทางเลือก ทั้ง source links/health เห็นเพียง2profiles Startup4.045s/restart3.514s/activation2.259s

Older3 candidate `20261011T081428-b7edc90daf`: ปก2เล่ม/plan13หน้า/all128rows ตรวจครบ 32HTTP ทั้งสองroutes/สองcycles รวมภาค3และสหกิจทางเลือก Startup5.866s/restart3.452s/activation4.928s ต้องระบุ partial3profiles

IT isolated14→2 lifecycle รอบก่อน: full gate reject, consumer lock, failedOCR/partialbuild รักษา pointer/hash, faultหลังpointerคืนทั้งชุด, rollback14คืนusernote/oldhashครบ สำเนา fixture ที่ขาดPDF4เล่มทำให้ startup rejectพร้อมคำแนะนำ แล้วคืนPDFหลังสร้างและcertifyเท่านั้น recovery14startupผ่าน หลักฐานเหล่านี้ไม่ใช่ fresh reconstruction ของ14profiles

ข้อผิดพลาดระหว่าง verification เก็บไว้: missing isolated venv, double comma ใน deterministic count SQL (แก้ทั่วไป+test executeจริง), extra-term validator Row/tuple mismatch (แก้+test Row factory) ไม่ลบ diagnostic failure

หลักฐานใน `docs/results/source_scope_20261011/`: `it-release-review.json`, `it-release-runtime/verification.json`, `it-lifecycle-verified/verification.json`, `old-field-review/review.json`, `old-three-runtime/verification.json`, sealed candidates และ raw input/parsed/SQLite/receipt ทุกขั้น ไม่มี held-out score

## ขอบเขตและข้อจำกัด

Academic-plan-only รองรับรายวิชาในแผน/หน่วยกิต/placeholder/alternatives/citations ไม่รับรอง catalog descriptions/prerequisites/graduation/full book Legacy identity ยัง unresolved Full replacement ยัง blocked UI/health จำกัดavailableprofilesและแสดง scope Native source certification ไม่ใช่ OCR accuracy Regression/source audit แยกกัน; browser policyยังบล็อกclickใหม่ APIและPNGไม่ใช่browserpass
