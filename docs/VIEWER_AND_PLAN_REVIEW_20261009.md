# ผลแก้ viewer และตรวจแผนการศึกษา 9 ตุลาคม 2569

ทำงานเฉพาะ local `week11_thanapat`/`37b3ad5` ไม่ commit/push/merge และเก็บ edits เดิม ใช้ curriculum-audit ตรวจ source โดยภาพ ไม่ถือ OCR หรือคำตอบของแอปเป็นเฉลย

## สาเหตุและสิ่งที่แก้

1. **code/integration bug:** native PDF surface ว่างทั้งที่ BIT PDF257/หน้า252 มีข้อความจริง แก้ด้วย viewer แสดง PNG จากหน้าต้นฉบับผ่าน PyMuPDF เก็บ cache ตาม source SHA/renderer version ไม่มีการสร้างข้อเท็จจริงเพิ่ม endpoint PDF เดิมและ POST /api/ask ไม่เปลี่ยน
2. **stale asset cache:** browser ยังใช้ presentation module เก่า ทำให้ citation เปิด raw PDF แก้ version imports และตรวจ actual citation click ไป viewer แล้ว
3. **data-ingest gap:** IT first-year totals ถูกต้อง แต่ printed folios เป็น null จึงไม่ผ่าน source-pair checks 4/4 แก้ source-approved citation-only ingestion 26แถวใน2DB มี backups/integrity/idempotence และ fingerprint ยืนยัน facts เดิมไม่เปลี่ยน หลังแก้ผ่าน4/4
4. **partial source-rule coverage:** BIT ข้อ26 มี source approval แยก production จาก labels เพิ่มแถว rule ลง2DBและรวม retrieval/reconstruction ได้ เกณฑ์2.00อ้างPDF93/หน้า88; English Exit numerical threshold, หมวด11และประกาศอื่นยังไม่ครบ ไม่รับรอง eligibility
5. **source ambiguity:** DSBA coop PDF36 เริ่มด้วยแถวต่อเนื่องที่รหัส/ชื่อไม่ปรากฏ PDF35 rerenderเต็มหน้าก็มีเฉพาะปี3ภาค2 จึงไม่เติมปี4ภาค1ด้วยแผนอื่น เรื่องนี้ยังเปิด ไม่ใช่การเปลี่ยนเฉลยให้ตรงแอป
6. **environment issue:** OneDrive ปฏิเสธ staged JSON replace ระหว่าง inventory/QA เก็บ `.partial` และ resume QA8กรณีที่ทำแล้วไป output นอก OneDrive โดยไม่ถามซ้ำ สำเร็จ ไม่ใช่การทดสอบ process-kill recovery ครบถ้วน

## ความครอบคลุม labels ใหม่

| profile | semesters ที่มี independent labels | profile-course options | unique concrete codes ใน profile | หน้าที่รองรับ labels | live API |
|---|---|---|---|---|---|
| DSBA-2565-no-coop | 8/8 | 45 | 34 | 7 | 8/8 |
| DSBA-2565-coop | 7/8 | 41 | 35 | 7 | 7/7 |
| IT-2565-no-coop | 2/8 | 13 | 13 | 2 | 2/2 หลัง citation fix |
| IT-2565-coop | 2/8 | 13 | 13 | 2 | 2/2 หลัง citation fix |

ตัวเลือกทางเลือกนับเป็นรายการ แต่ไม่บวก credits ทางเลือกซ้ำ elective wildcard ไม่ใช่รหัสเสีย unique ต่อ profile รวมข้าม profile ไม่ได้เพราะมีวิชาร่วมกัน Labels รอบนี้ยืนยัน code/credit pattern/semester/total/paired pages เท่านั้น ยังไม่ยืนยันชื่อ หมวดวิชา เงื่อนไขเลือก specialization และ prerequisites ทั้งเล่ม รูป DSBA14หน้าที่ตรวจไม่ได้เท่ากับการตรวจ descriptions ทั้ง403หน้า

## ผลตรวจที่สังเกตได้

- Actual browser: BIT257/252 และ AI292/288 แสดงภาพจริง; กด citation จากคำตอบ AI แล้วเปิดภาพถูกหน้า; BIT93/88 จาก graduation answer แสดงจริง; nextBIT258 ไม่เดา printed folio; invalid999แสดงข้อผิดพลาดและเปลี่ยนกลับ257สำเร็จ มี JSON/PNG ไม่ถือ HTTP200เป็นหลักฐานการแสดงผล
- Isolated saved-OCR reconstruction4/4 profiles, integrity4/4, partial semester totals20/20 และ code/hour-pattern discrepancies0; protected hashes unchanged การสร้างใหม่นี้ไม่ใช่ fresh OCR และไม่วัด raw extraction improvement
- Real rebuilt API BIT13+13 และ IT2+2 ผ่าน30/30 เป็น development L1/L2 ไม่ใช่ independent held-out หรือ challenge latency
- Final live-backed unit196ผ่าน, frontend6ผ่าน; shared checks unit195/schema30/frontend6/gold70/old65/provenance14/version pairs6 ผ่านก่อนเพิ่ม unit อีกหนึ่งตัว Global dependency guard ของ batch นั้น **ไม่ผ่าน** เพราะ `test_partial_plan_labels.py` เปลี่ยนระหว่างงาน (runtime/DB unchanged ระหว่าง checks) เก็บผล failed guard ไว้ ไม่เรียก batch นี้ว่า dependency-locked final pass
- Live DSBA structured L2: no-coop n8 median727.96ms/p95816.62ms; coop n7 median771.46ms/p95895.05ms. IT หลังแก้ coop n2 median741.25ms/p95745.40ms; no-coop n2 median826.66ms/p95841.54ms เป็น request ใน process/model ที่ทำงานแล้ว ไม่ใช่ cold/hard LLM bonus
- Read-only audit ก่อน BIT/IT ingest:16datasets FAIL1372/incomplete4881 ยังไม่ใช่จำนวนคำตอบผิดทั้งหมด และยังต้อง audit รอบถัดไปหลัง labels ขยาย

## Page selection และสิ่งที่ยังไม่ครบ

Manifests7เล่ม [summary](../ocr_final/data/source_reviews/page_selection/summary.json):2322physical pages,77include,0skip,2245unreviewed ตาม locators ที่มี hash-matched visual approvals ไม่ใช่ทั้งหมดที่เคย review และยังไม่ใช่ final selection สำหรับ full relevant-page reconstruction ไม่ auto-skip appendices; skip ต้องมีภาพยืนยัน blank/irrelevant พร้อมเหตุผล ไม่ถือหน้าที่ไม่ตรวจว่าไม่เกี่ยวข้อง

ยังขาด12ITsemesters, DSBAcoopปี4ภาค1 source evidence, complete names/categories/specialization rules, broad prerequisite coverage/AND-OR evidence, program-summary folios, fresh relevant-page reconstructionครบทุกprofile, untouched held-out, realLLM fallback provenance, difficult/cold latency, actual timeout exhaustion/process interruption, legacy identity และ clean installation ไม่สรุปเจ็ด workstreams ว่าเสร็จ

## หลักฐานและการกู้คืน

- Raw results/screenshots: [viewer_source_20261009](results/viewer_source_20261009/)
- Labels/index: [ground truth index](../ocr_final/data/ground_truth/README.md)
- Approved production rules: [BIT clause26](../ocr_final/data/source_reviews/BIT-2565-graduation-rule-26.json); [IT folios](../ocr_final/data/source_reviews/IT-2565-page-pairs-20261009.json)
- Verified backups4ไฟล์อยู่ `docs/results/viewer_source_20261009/backups/` พร้อม original SHA ใน deployment manifests ไม่ควรเผยแพร่ DB backups ใน Git
- ก่อน rollback ให้หยุดเฉพาะ backend ของงานนี้ ทำ SQLite backup ของ current DB อีกครั้ง ตรวจ hash/integrity และ newer changes ก่อน restore snapshot ที่เลือก ไม่ได้ rollback อัตโนมัติ
- Exact next action/rerun commands: [authoritative checkpoint](PROGRESS.md)
