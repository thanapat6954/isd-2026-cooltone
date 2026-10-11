# ผลตรวจและ targeted repair ปี4 ใน LIVE

ใช้ curriculum-audit และตรวจภาพต้นฉบับด้วย PDF workflow บน `week11_thanapat` / `37b3ad5` ไม่ commit/push/merge. Repository กับ LIVE เป็นคนละโฟลเดอร์; ตรวจ hash ก่อน port ไม่แทนฐานข้อมูลทั้งไฟล์ ไม่แก้ original OCR หรือ held-out. รายงานนี้ supersedes ข้อความ “ยังไม่ deploy” ในรายงาน Year4 ก่อนหน้า เฉพาะรายการที่มีหลักฐาน LIVE ด้านล่าง ไม่เปลี่ยนประวัติผล isolated ให้กลายเป็น LIVE.

## ขอบเขตและสถานะแยกกัน

| หลักสูตร/แผน | ภาคปี4ที่ตรวจ | แถวตัวเลือกต่อแผน | รวม S1/S2 | PDF/หน้าในเล่ม | LIVE |
|---|---:|---:|---|---|---|
| DSBA-2565 สหกิจ | 2 | 6 | 12/6 | 36/35 | names และ term metadata; API/UI/click ผ่าน |
| DSBA-2565 ไม่สหกิจ | 2 | 6 | 9/9 | 29/28 | term metadata; API/UI/click ผ่าน |
| IT-2565 สหกิจ | 2 | 11 | 18/15 | 43/38,44/39 | ใช้ผล LIVE เดิมที่ dependency ไม่เปลี่ยน |
| IT-2565 ไม่สหกิจ | 2 | 8 | 15/9 | 37/32 | ใช้ผล LIVE เดิมที่ dependency ไม่เปลี่ยน |
| BIT-2565 สหกิจ | 2 | 7 | 15/6 | 35/30 | fields/names/metadata; API/UI/click ผ่าน |
| BIT-2565 ไม่สหกิจ | 2 | 8 | 12/12 | 29/24,30/25 | fields/minimal identity/metadata; API/UI/click ผ่าน |
| AI-2566 แผนเดียวในข้อมูล | 2 | 6 | 12/6 | 26/22 | API/UI/click ผ่าน พร้อมแสดงข้อจำกัดไม่มีแผนที่สอง |
| DSBA-2560 สหกิจ | 2 | 6 | 12/6 | 33/28,34/29 | targeted metadata; source/actual LIVE ตรวจ |
| DSBA-2560 ไม่สหกิจ | 2 | 5 | 9/6 | 29/24 | targeted metadata; ชื่อเดิมคืนตามภาพขยาย |
| BIT-2560 สหกิจ | 2 | 6 | 6/12 | 30/25 | targeted metadata; API/UI/click ผ่าน |
| BIT-2560 ไม่สหกิจ | 2 | 6 | 9/9 | 26/21 | targeted metadata; API/UI/click ผ่าน |
| IT-2560 สหกิจ | 2 | 12 | 6/18 | 39/34,40/35 | S2 metadata เพิ่มโดยไม่แก้ facts; branches เดิมคงไว้ |
| IT-2560 ไม่สหกิจ | 2 | 12 | 18/6 | 32/27,33/28 | S2 metadata และ memberships แยก 3 แขนง; note S1 ไม่ยืมสหกิจ |
| legacy catalog | n/a | n/a | n/a | ยังไม่ยืนยันเอกสาร/ฉบับ | แจ้งขอบเขต DB ไม่ประกาศว่าเล่มไม่มีแผน |

รวม 99 profile-row options / 26 ภาค / 13 profiles ใน Year4 ไม่ใช่ 99 unique courses และไม่ใช่ full-book review. ตัวเลือกสหกิจนับเพียงหนึ่งตัวเลือก; IT project branches เลือกตามแขนง ไม่บวกทุกแขนง. Categories/prerequisites/graduation ทั้งเล่มยังไม่รับรองจากตารางนี้. จำนวน unique course identities และจำนวน source-reviewed prerequisite cases ต้องอ่านหลักฐานแยก ไม่ใช้จำนวนแถวนี้แทน.

## สาเหตุและการแก้

1. **Ingestion:** combined code ใช้ master ตัวแรกกับทุก alternative. แก้ generic per-option metadata และ missing-master guard; ไม่ยืมชื่อ/description/prerequisite จาก option อื่น. DSBA-2565 ต่างประเทศและ AI-2566 ต่างประเทศแยกชื่อแล้ว.
2. **Stale LIVE fields:** BIT-2565 39 coop / 52 no-coop field changes (รวม minimal course identity insert 1), names 1 field, term metadata 13/14 inserts. ไม่เติม description หรือ prerequisite ลง course ใหม่. AI names 6 / placeholder fields 5 / metadata 12. Source-approved repairs ไม่ใช่ OCR accuracy gain.
3. **Comparison metadata:** plan_item ถูกตรวจภาคเรียนแล้ว แต่ study_term/study_item ไม่ครบ จึงไม่มี printed totals ในคำตอบ. เติม metadata แบบ exact-row/source/version/page/alternative guards. Older BIT 12+12 inserts; DSBA 12+11 inserts และ approval history ใหม่ 2; IT S2 9+13 inserts. Generic importer เพิ่ม source-approved specialization membership พร้อม conflict/idempotence tests ไม่ flatten สามแขนงเป็นรายวิชาร่วม.
4. **Presentation:** generic elective grouping ให้ชื่อที่ระบุ humanity/general education มาก่อน broad category; raw stored category บางแถวยัง stale ไม่ถือว่าได้รับการแก้ทุก field. Structured notes แสดง single-plan/evidence limitations เหนือ cards จริง ไม่ซ่อนใน plain answer.

## Combined alternatives: ตรวจแยก ไม่คัดลอกข้ามวิชา

| เอกสาร | Codes ที่ตรวจแยก | PDF / printed page | สิ่งที่ยืนยันจาก source | ข้อจำกัด |
|---|---|---|---|---|
| DSBA.pdf | 06026259,06026260 | 341/340,342/341 | ชื่อ domestic/foreign, description แยกและ continuation ของ60, explicit ไม่มี ทั้งสอง | ไม่อ้าง description/prerequisite ingestion หรือ API coverage จาก names-only repair |
| AI.pdf | 06046443,06046444 | 303/299,304/300 | ชื่อ/description domestic/foreign แยก, explicit ไม่มี ทั้งสอง | plan English ใช้ TECHNOLOGY; ไม่แทนด้วย label จากอีก section |
| BIT-65.pdf | 06036147,06036148 | 257/252 | descriptions แยก domestic/foreign, explicit ไม่มี ทั้งสอง | PDF274/book269 เป็น comparison appendix ไม่ใช่ description |
| BIT-60.pdf | 06036046,06036047 | 188/111 | descriptions และชื่อแยก, explicit ไม่มี ทั้งสอง | folio ไม่คำนวณ offset; 188/111 เป็นคู่ที่อ่านจริง |
| DSBA-60.pdf | 06026130,06026131 | 190/185 | descriptions/title แยก, explicit ไม่มี ทั้งสอง | description 6(0-36-0) แต่ plan34/book29 6(0-35-0); คง source-section conflict |
| IT-60.pdf | 06016393,06016394 | 267/262 | ชื่อและ description แต่ละวิชา, explicit ไม่มี ทั้งสอง | foreign description ใช้ถ้อยคำทั่วไป ไม่เพิ่มความหมาย abroad ที่ไม่ได้ระบุใน description |
| IT-60.pdf | 06016395,06016396 | 268/263 | ชื่อและ description แต่ละวิชา, explicit ไม่มี ทั้งสอง | plan title มี wording variant; ไม่ยืมชื่อจากอีก section |
| IT-60.pdf | 06016397,06016398 | 269/264 | ชื่อและ description แต่ละวิชา, explicit ไม่มี ทั้งสอง | ไม่เปลี่ยน missing DB content เป็น no prerequisite อัตโนมัติ |

รวม 16 unique alternative course identities / 10 description pages. เป็น source observations ไม่ใช่คะแนน OCR ไม่ใช่ held-out และไม่ใช่หลักฐานว่า runtime ตอบ prerequisite ครบ 16 วิชา. Missing database content remains unknown จนมี separately approved production ingestion.

## Actual answers และ chain evidence

คำถาม development เดิมหนึ่ง wording: “ถ้าไม่ไปสหกิจ ปีสุดท้ายต้องเรียนต่างจากแผนสหกิจอย่างไร แยกภาคเรียนและหน่วยกิตของแต่ละแผน”. Original [28-request evidence](results/it_year4_source_chain_20261010/plans-all.json) คงไว้. Current [12 old-profile requests](results/year4_live_port_20261010/older-year4-final-live.json) มี executed SQL, parameters, retrieved rows, answer, citations และ elapsed time; HTTP200 ไม่ใช้แทน semantic pass. มี 6 scoped questions / 1 reasoning category / 12 requests ไม่ใช่ 12 reasoning tasks.

Current LIVE UI แสดง BIT-2560 totals6/12และ9/9, DSBA-2560 totals12/6และ9/6, IT-2560 totals6/18และ18/6 พร้อมแยกแขนง. หลักฐาน [BIT UI](results/year4_live_port_20261010/bit-old-live-ui.jpg), [DSBA UI ก่อนคืนคำพิเศษ—historical](results/year4_live_port_20261010/dsba-old-live-ui.jpg), [IT UI](results/year4_live_port_20261010/it-old-final-live-ui.jpg). DSBA intermediate answer ไม่ใช้เป็น final name evidence; ใช้ final JSON หลัง restoration และ source detail. LIVE BIT-2565 [current JSON](results/year4_live_port_20261010/bit-current-live-after.json) / [UI](results/year4_live_port_20261010/bit-current-live-ui.jpg); AI [UI notes](results/year4_live_port_20261010/ai-live-ui-after-notes.jpg).

Citation clicks source content: [BIT30 ready](results/year4_live_port_20261010/bit-old-source30-ready.jpg), [BIT26](results/year4_live_port_20261010/bit-old-source26.jpg), [DSBA34](results/year4_live_port_20261010/dsba-old-source34.jpg), [DSBA29](results/year4_live_port_20261010/dsba-old-source29.jpg), [DSBA33](results/year4_live_port_20261010/dsba-old-source33.jpg). Screenshot ที่ยัง loading ไม่ถือว่าผ่าน. Raw source renders + SHA/config manifests อยู่ `results/year4_live_port_20261010/alternative-source-renders` และ `older-term-source-renders`.

## การอ่าน source ที่ผิดและแนวทางที่ไม่ใช้

- การอ่าน DSBA no-coop elective label ครั้งแรกตัด “พิเศษ” ผิด. [ภาพขยาย](results/year4_live_port_20261010/dsba-old-elective-detail.png) ยืนยันคำนี้จริง; คืน original value ด้วย guarded transaction 1 field + backup, ไม่แทน DB. [Restoration evidence](results/year4_live_port_20261010/dsba-old-name-restoration-live/result.json); approval แรกเปลี่ยน status เป็น retracted และเก็บ [original approval](results/year4_live_port_20261010/retracted-dsba-name-approval.json). ทั้งสอง history ไม่ลบ. Production rebuild approval และ metadata กลับตรง source แล้ว.
- Hypothesis ว่า process-order ทำให้ rendering สูญหาย **ไม่ reproduced**: 8 output PNGs byte-identical กับ fresh-process experiment. [Rejected diagnosis](results/year4_live_port_20261010/render-diagnosis-rejected.json). ลบเฉพาะ experimental module/tests ที่สร้างเองและยังไม่ port; ไม่ลบ source/evidence/user edits. ห้ามอ้างว่าได้แก้ runtime renderer จาก experiment นี้.
- Unit inventory assertion 23 terms failed เมื่อ approval เพิ่มเป็น24; เก็บ failed checks แยกจาก run ใหม่. เปลี่ยน test-only inventory count ไม่เปลี่ยน QA labels หรือ curriculum facts.

## Backups และ rollback

ทุก targeted batch มี `before.db`/`stage.db`/`result.json` ใน `results/year4_live_port_20261010/*-live/`; names-only batchesใช้ `manifest.json` กับ `backups/`. SQLite backup API, integrity/FK, staged idempotence, live guarded replay และ unaffected facts ผ่านตาม raw records. ไม่ใช้ copying stage→whole working DB.

Rollback ต้องตรวจ current before/after guards แล้ว reverse เฉพาะ fields หรือ metadata rows ที่ batch เพิ่ม ภายใน transaction; สำหรับ approved metadata ลบ child memberships/pages/approval records ก่อน term เฉพาะ IDs ที่ manifest ระบุและไม่มี user edits/dependent contentใหม่. Backup ใช้ตรวจ/กู้ข้อมูลเฉพาะส่วน ไม่ restore ทั้งไฟล์ทับงานใหม่. ถ้า guard ไม่ตรงให้หยุดเพราะ conflict ไม่เดา.

## งานที่ยังไม่ปิด

88 pending cases ต้อง reconcile จาก current results แยก source fidelity/DB consistency/completeness/citation support; unrelated facts ใน misleading-assumption batch เป็น actionable retrieval finding ไม่ใช่ justified abstention. ส่วน source fidelity ของ legacy และ full graduation constraints ยัง n/a. Held-out untouched, fresh relevant-page reconstruction, real-LLM provenance, controlled cold/warm difficult latency, kill recovery, clean first-machine model installation และ broad prerequisites ยังเปิด. ไม่มีการรับรองคะแนนอาจารย์หรือความถูกต้องทุกคำถามจากจำนวน regression tests.
