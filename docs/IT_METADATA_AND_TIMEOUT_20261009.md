# ผลแก้ metadata IT และตรวจ timeout จริง

วันที่ 9 ตุลาคม 2026 — ใช้ `curriculum-audit` บน branch `week11_thanapat`, HEAD `37b3ad5` ไม่ commit/push/merge หรือแก้ main คง existing edits และแยก LIVE sibling ออกจาก repository application

## 1. Working IT discrepancy ปิดใน fields ที่ตรวจ

ผลเก่า `live-reviewed-fields-resolved.json` มี 44 mismatches ก่อน names-only fix จึงไม่ใช้เป็น baseline ปัจจุบัน ผลใหม่ `live-current-fields.json` มี 36 mismatches ส่วน isolated reviewed rebuild มี 0 จุด

ใช้เฉพาะ production approval `ocr_final/data/source_reviews/IT-2565-plan-corrections.json` SHA256 `70cdb618738ec716ed38e8329e5b9e0da74868dd99387c273569e38a774fb989` ไม่อ่านเฉลย evaluation เพื่อสร้าง production facts

| แผน | ภาคที่ patch | แถวที่แตะ | แหล่งต้นฉบับ |
|---|---|---:|---|
| IT-2565 สหกิจศึกษา | ปี4/1 และ4/2 | 11 | IT.pdf PDF43/44, หนังสือ38/39 |
| IT-2565 ไม่สหกิจศึกษา | ปี3/2,4/1,4/2 | 13 | IT.pdf PDF35–37, หนังสือ30–32 |

สาเหตุคือ working DB จากการกู้จำนวนหน่วยกิตเก่ายังไม่มี fidelity metadata ของแถว ไม่ใช่ elective placeholders ที่ผิดรูปแบบ

- เติม `raw_code`, `code_pattern`, `is_placeholder`, `elective_type`, `credits_raw`, ชื่อและ page pair ที่ได้รับอนุมัติแล้ว รักษา `x/X` และ alternative hour patterns ทั้งหมด
- recovered slot หนึ่งแถวต่อแผนเปลี่ยนเป็นรหัสจริง 90644042 ตามแถวต้นฉบับ รายวิชานี้มีใน catalog เดิมอยู่แล้ว ไม่มีการเพิ่มหลักสูตรหรือรายวิชาโดยเดา
- แก้ header bleed-in ของชื่อ 90643021 / 90642033 ตามหนังสือ แก้ category ของ recovered slots ให้ตรงประเภทที่ยืนยันได้
- metadata ที่แก้รอบแรก 152 ค่า แล้วปรับ elective type อีก 12 ค่าให้ใช้ convention เดิมของ parser ทุกการเปลี่ยนมี before/after ใน manifest และ source approval hash ใน review ledger
- รักษา row IDs, ปี/ภาค, จำนวนหน่วยกิตที่นับ, prerequisites, program facts และ unrelated rows ไม่แทนที่ working database ทั้งก้อน ใช้ transaction ที่ตรวจว่าฐานไม่เปลี่ยนจาก backup ก่อน apply

`repair_reviewed_plan_metadata.py` ทำ SQLite backup, staged integrity, idempotence และ unaffected-row comparison ก่อน bounded transaction ผลหลังแก้: integrity 13/13 active profiles ใน checker, semester totals28/28 (DSBA16 + IT12), reviewed-field mismatches0 ในขอบเขต labels ใหม่ ไม่ใช่ความถูกต้องทั้ง catalog

จริงใน UI: สหกิจปี4/1 แสดง6แถว รวม GE/free slots ที่มีชื่อและ credit alternatives; ไม่สหกิจปี3/2 แสดง5แถว รวม90644042 และ elective1/2 พร้อม PDF35/30 กับ36/31 ไม่มี mock response หลักฐาน screenshot/DOM อยู่ [results](results/it_metadata_timeout_20261009/)

## 2. Deadline exhaustion

ใช้ `probe_real_request_budget.py`: isolated SQLite snapshot, ephemeral HTTP server และ Ollama `qwen3:4b` จริง ไม่มี answer mocks หรือ gold input ทุก server ปิดหลัง probe การใช้ TestClient ครั้งแรกทำไม่ได้เพราะ httpx2 missing จึงใช้ HTTP server จริงโดยไม่ติดตั้ง dependency เพิ่ม

| เงื่อนไข | /api/ask | /ask | subsequent recovery |
|---|---|---|---|
| positive budget1s ก่อนแก้ | 503 / ReadTimeout | 503 / ReadTimeout | 200 ทั้งสอง routes |
| positive budget1s หลังแก้ | 504,1068.05ms | 504,1064.13ms | 200 ทั้งสอง routes |
| positive budget1s รอบต่อ | 504,1052.31ms | 504,1040.87ms | 200 ทั้งสอง routes |

สาเหตุที่ observed คือ network/model request เกินเวลาถูกบอกว่า “ติดต่อ Ollama ไม่ได้” ทั้งที่เป็น timeout ไม่ observed builtin TimeoutError → HTTP500 ใน model probe จึงไม่อ้างว่ามี raw runtime failure แบบนั้น

เพิ่ม HTTP504 ภาษาไทยสม่ำเสมอสำหรับ builtin TimeoutError และ requests.Timeout โดยไม่เปลี่ยน request/response contract ของ `/api/ask` หรือ `/ask` เพิ่ม monotonic shared deadline สำหรับ SQLite connection wait, SQL progress handler และตรวจหลัง generation/ก่อนคืนคำตอบ Context ถูก reset เมื่อจบทุกครั้ง SQL repair ไม่ได้เริ่ม budget ใหม่

ตรวจ retrieval จริงอีกกรณี: read-only cross-join บน isolated IT snapshot, positive20ms budget → TimeoutError ที่20.14ms, context reset และ connection ปิด ไม่ใช่ mock หรือ model request (`sql-deadline.json`)

Ollama appended log ของรอบหลังมี HTTP499 และ context canceled ที่1.50–1.64s; isolated server ปิดจริง จึงมีหลักฐานว่าคำขอที่ตรวจไม่ค้างไม่สิ้นสุด ไม่ได้รับรอง resource cancellation ทุกกรณีหรือหยุด shared Ollama process โปรบชื่อ `timeout-warm` พบ `resident_before` ไม่มี model จึงเป็น warm measurement ไม่ได้

## 3. Real LLM fallback และ latency: พบปัญหาที่ยังไม่ปิด

คำถาม development ใหม่เป็น unknown intent จริง ไม่มี code/semester fact shortcut ขออธิบายความสัมพันธ์การพัฒนาซอฟต์แวร์กับระบบคอมพิวเตอร์ โดยอ้างข้อมูลในเล่ม เก็บผล budget45s สอง requests และ six real generation calls ไว้ใน `fallback-45s/result.json`

- `/api/ask` HTTP200 ใช้12954.78ms แต่ตอบ program summary129credits/4years ซึ่งไม่ตอบความสัมพันธ์ที่ถาม จึงไม่ใช่ answer-correctness pass แม้ค่ามาจาก DB จริง
- `/ask` HTTP422 ใช้4503.41ms หลัง model เพิ่ม program/year filters ที่ไม่ถูกต้องและหมด repair attempts ตัว validator ไม่ถูกลดความเข้มเพื่อให้ผ่าน
- subsequent structured recovery200 ทั้งสอง ไม่มี timeout ใน budget45s สองกรณีนี้

Latency รวม request ที่ผ่าน/ไม่ผ่านHTTP n=2: median8729.10ms, p9512954.78ms แต่ correct/complete difficult answers0/2 ใน probe นี้ ไม่ใช้ failed/irrelevant answer เป็นหลักฐาน under5s และไม่มี verified cold/warm split จึงรายงาน cold/warm แยกเป็น n/a

Root cause ที่ตรวจจาก code: `make_sql()` มี stored_hint ให้เลือก program summary สำหรับ unknown fallback และ semantic claims selector ยอมเลือก program facts ที่ไม่เกี่ยวข้อง ประเด็นนี้ยัง open ต้องแก้ retrieval/relevance แบบทั่วไปและตรวจ source evidence ไม่ hard-code คำตอบของคำถาม probe ไม่ใช้ held-out tuning

Mutation/removal/failure provenance สำหรับ unknown LLM จริงยังไม่ครบ แม้ shared SQL replay14profiles ได้ non-SQL changed/added fields0 ห้ามตีความว่า replay ครอบคลุม real fallback ทุกกรณี

## 4. ขยาย source prerequisite coverage

ใช้ PDF skill ตรวจภาพครบ AI.pdf PDF288 / หนังสือ284 :codex-file-citation{path="C:/Users/thana/OneDrive/เอกสาร/ocr_final/data/input/AI.pdf" purpose="source"}

06046402 พีชคณิตเชิงเส้น และ06066000 คณิตศาสตร์ไม่ต่อเนื่อง พิมพ์ “วิชาบังคับก่อน : ไม่มี / PREREQUISITE : None” ทั้งสองรายวิชา ไม่ใช่การเดาจาก missing field ไม่มี prerequisites หลายตัวให้ต้องอนุมาน AND/OR ในหน้านี้

Production approval ใหม่ `AI-2566-prerequisites-20261009.json` เก็บ PDF SHA และ rendered image SHA; development2QA อยู่ `data/ground_truth/evaluation/AI-2566/prerequisites-20261009.json` แยกออกจาก production ingestion และ untouched held-out

Ingest1DB มี SQLite backup/integrity; ไม่มี name changes/catalog additions; QA2/2 รวม paired citation และห้าม grant registration จาก NONE statement UI06046402 แสดงเอกสารระบุว่าไม่มี prerequisite, ข้อจำกัดสิทธิลงทะเบียน และ PDF288/book284 จริง Coverage AI prerequisite source-approved เพิ่มจาก5เป็น7/299 unique courses ไม่ใช่ครอบคลุมทั้งหมด

Manifest now87include /0skip /2235unreviewed จาก2322physicalpages/7books; AI9include หน้าที่ไม่ตรวจไม่ถูกตัดทิ้ง ไม่มี source PDF/OCR/held-out เดิมถูกแก้

## 5. Regression และ evidence retention

- Final shared locked run: unit215/schema30/frontend6/gold70/old2560QA65/SQL provenance14profiles/version sets6 ทั้ง7jobs exit0, `dependencies_unchanged=true`
- Focused new/updated tests9ผ่าน: metadata preservation/rejection/idempotence, timeout route mapping, exhausted retrieval, late generation และ context reset
- Read-only audit16datasets ยัง FAIL1372/incomplete4881 เช่นเดิม; missing curricula=[] ไม่ใช่จำนวนคำตอบผิด และไม่อ้างว่าปิด book-wide audit
- OneDrive atomic result-write ของ final attempt เกิด WinError5 ก่อน tests เก็บ attempt เดิม ไม่ retry target เดิม ใช้ TEMP output ใหม่จนจบแล้ว copy raw results durably เข้า `shared-checks-complete/`
- Previous failed dependency guard และก่อน/หลัง timeout outputs คงเดิม ไม่เขียนทับ

Backups ใน `results/it_metadata_timeout_20261009/{applied,options-applied}/` ทั้งสอง IT snapshots และ `AI-before-prerequisites.db` (SHA `b24187bb2cbc00f42ff4ec5a6f7c53e2f4cbef487f67888da3d4e96302ccdb4d`) พร้อม manifests ไม่ส่ง DBs ขึ้น GitHub โดยอัตโนมัติ Rollback ต้อง snapshot working DB ใหม่ก่อน ตรวจ newer user changes และ integrity ไม่ blind restore

## 6. สิ่งที่ยังไม่เสร็จ

Unknown fallback relevance/retrieval, broader prerequisite/conditions ทุก version, independent mutation/removal provenance, fresh relevant-page OCR/reconstruction ทุกprofile, untouched held-out final assessment, process-kill recovery, legacy identity และ clean installation ยังไม่ครบ Difficult cold/warm latency และความถูกต้องทุกคำถามไม่รับรอง Missing AI-old/same-year revisions/dual-degree/English Exit thresholds คง unknown ไม่มี slides/video/publication

คำสั่งและ exact NEXT ACTION อยู่ [PROGRESS.md](PROGRESS.md); รายงานนี้ไม่ใช่ memory file ที่สอง
