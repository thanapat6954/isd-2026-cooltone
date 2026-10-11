# ผล reconstruction ของ BIT แบบเลือกหน้า

## ขอบเขตและผลจริง

ทำบน `week11_thanapat` โดยไม่ commit/push/merge ไม่แก้ working SQLite และไม่แก้ original OCR/held-out เครื่องมือ extraction/parser และ citation fix port เข้า LIVE แบบ targeted แล้ว สำรอง code เดิมไว้และเก็บ comment ของ LIVE ที่ต่างจาก repo ไม่ copy ทับไฟล์ทั้งก้อน

BIT-65.pdf มี 317 PDF pages: manifest เลือก include 15 หน้า, skip 0, unreviewed 302 หน้า ไม่ถือว่า unreviewed คือ irrelevant ชุดก่อนหน้ามี 12/15 checkpoints ที่สำเร็จด้าน extraction; ไม่ใช่หลักฐานว่าเนื้อหาทั้ง 12 หน้าถูกต้องทุก field

ครั้งนี้เลือกเฉพาะ PDF93/book88, PDF238/book233, PDF257/book252 ไม่รัน 12 หน้าที่เสร็จแล้วซ้ำ

| configuration | page attempts | extraction สำเร็จ | ผล |
|---|---:|---:|---|
| 200 DPI / temperature 0 / default retries 2 | 3 | 0 | HTTP500 ทุกหน้า; log เดิมยังอยู่ |
| 200 DPI / temperature 0.1 / retries 0 | 3 | 0 | `prediction aborted, token repeat limit reached` |
| 200 DPI / temperature 0 / retries 0 / 2 segments | 3 | 0 | error เดิมตั้งแต่ segment แรก จึงไม่มี merged extraction ให้ตรวจ |

เพิ่ม diagnostic 1 HTTP request บน PDF238 ที่ predict1024/temp0/200DPI พบ error body ข้างต้นด้วย จำนวน page attempts ไม่ใช่จำนวน HTTP requests เพราะ configuration แรกใช้ retries เดิม ยังไม่สรุปว่าเหตุภายใน model คืออะไรจากข้อความ error เพียงอย่างเดียว

ไม่มีการนำ failed pages ไปเป็น skip การทดลองถัดไปเปลี่ยน prompt แบบ explicit: PDF238 สำเร็จ26.8s/740tokens และ reuse เมื่อ identities ตรงครบใน all3job; PDF93/257 ยัง HTTP500 ชุดใหม่นี้ processed1/3 โดยไม่ได้รัน 12 หน้าที่เสร็จแล้วซ้ำ ไม่เรียกว่า full reconstruction

## ผลหลัง short prompt และ parser

ตรวจ PDF238/book233 กับภาพจริง: 2unique courses ×5fields(code/name_th/name_en/credits/prerequisite)=10/10 targeted cases ตรง ไม่รวมความถูกต้องข้อความ description ทั้งหน้า/categories/CER/WER ไม่ใช่การปรับคะแนน reviewed-ingestion มาอ้างว่า OCR ดีขึ้น

`parse_description_markdown.py` ได้2catalog rows ไม่มี year/semester/category ที่อนุมานเอง missing prerequisite เป็น unknown, multiple prerequisite เก็บข้อความและไม่อนุมาน AND/OR, credit alternatives คง raw string โดยไม่เลือก hours ชุดใดเอง duplicate sections fail loudly. Parsed JSON ยัง `source_verified=false` จนมีการตรวจแยก ไม่ได้ป้อน evaluation labels เข้า production

สร้าง snapshot แอปและ SQLite ใหม่ใน isolation ใช้ SQLite backup API จาก working DB แล้ว update เฉพาะ raw course fields ของ2courses ไม่แทน working DB; program/plan/prerequisite unchanged และ integrity `ok`. Prerequisite evidence ในสำเนามาจาก production approvals ที่มีอยู่แล้ว ไม่ใช่ expected answers

### Citation defect ที่พบและแก้

ก่อนแก้ credit answer ถูกต้อง แต่ book_page=null เพราะ `_course_fields` หา printed folio จาก plan_item/code เท่านั้น ไม่เห็น paired locator ของ description ใน SQLite

แก้ generic lookup ให้ใช้ recorded source-file/PDF-page pairs จาก metadata tables ใน selected DB; เมื่อคู่เลขหน้าขัดกันให้ unknown ไม่เลือก MIN อย่างไม่มีเงื่อนไข ไม่เปลี่ยน SQL validators/ไม่คำนวณ offset/ไม่ขยาย schema

First attempt ใช้ SQL typeof literal ซึ่ง strict validator ปฏิเสธ; เก็บ 422 ทั้งสอง routesไว้ใน `isolated-citation-validator-failed` แล้วแก้ SQL โดยไม่ลด validator. ผลสุดท้าย4HTTPrequests/2wordings/2routes: answers ถูกต้องและ credit citation เป็น PDF238/book233. จริง UI แสดง3หน่วยกิต L-P-S2-2-5 และคลิกเห็นชื่อ/creditใน rendered page; raw [chain](results/bit_manifest_controls_20261010/isolated-description-chain.json), [UI](results/bit_manifest_controls_20261010/isolated-credit-answer.dom.txt), [source](results/bit_manifest_controls_20261010/isolated-source238.dom.txt)

LIVE port/restart verified แยกจาก isolated: working factsไม่เปลี่ยน, LIVEเครดิตยังอ้าง studyplanPDF31/book26 ตาม course rowเดิม ไม่อ้างว่า LIVEถูกแทนด้วย description238; LIVEprerequisite UI อ้างPDF238/book233และเห็นsourceจริง. Raw [LIVE endpoints](results/bit_manifest_controls_20261010/live-credit-citation-after.json). ไม่ใช้ 4HTTP200 เป็นคะแนนทั่วไปหรืออ้างว่าตรวจทุกprofileใหม่แล้ว

## การเปลี่ยนเครื่องมือ

- `scripts/extract_manifest_pages.py`: repeatable `--page` รับเฉพาะ reviewed include pages; `--max-pages` นับ attempts รวม failures เพื่อจำกัดงานจริง
- `LAB7B_OCR_TEMPERATURE`: default **0.1** คงเดิม ตรวจช่วง 0–2 ใช้ค่าเดียวกันใน model request และ page checkpoint
- `LAB7B_OCR_RETRIES`: default **2** คงเดิม; isolated experiment ใช้ 0 เพื่อไม่วน settings เดิมเมื่อเกิด error
- Resume ตรวจ requested scope, dependency identities และ hash ของ completed markdown/PNG ปฏิเสธผลที่เปลี่ยน ไม่ overwrite evidence
- บันทึก source, extractor, runner, image, installed model digest, prompt, renderer/version และ generation hashes; HTTP error body และเวลาของ failed attempts บันทึกแยก
- `--segments 2` เป็น experimental option ไม่ใช่ default เก็บ original PNG และ crop coordinates พร้อม overlap40px; merged text มีเครื่องหมายเตือน duplicate ไม่เข้า study-plan parsing อัตโนมัติ
- Reconstruction configuration identity เพิ่ม temperature/retries เพื่อไม่ resume ข้าม configuration

Probe257/200DPI เดิมยังเก็บไว้เป็น historical raw evidence แต่ไม่มี recorded model digest/renderer identity ครบตาม guard ใหม่ จึงไม่นำเข้า matching cache โดยสันนิษฐานว่าทุกอย่างตรงกัน

## ตรวจภาพต้นฉบับและแก้ข้อสรุปเก่า

ตรวจ rendered source images เดิมที่มี source hash ตรง BIT-65.pdf ไม่ใช้ embedded Thai text เป็นเฉลย

| PDF / book | สิ่งที่ตรวจยืนยัน | ข้อจำกัด |
|---|---|---|
| 238 / 233 | 06036100 ชื่อ **พื้นฐานทางด้านเทคโนโลยีสารสนเทศ**, 3(2-2-5), INFORMATION TECHNOLOGY FUNDAMENTALS, ไม่มี/NONE; 06036101 คณิตศาสตร์สำหรับธุรกิจ, 3(3-0-6), MATHEMATICS FOR BUSINESS, ไม่มี/NONE | ไม่ใช่ full-description transcription accuracy |
| 257 / 252 | 06036147 สหกิจศึกษา / COOPERATIVE EDUCATION และ 06036148 สหกิจศึกษาต่างประเทศ / OVERSEA COOPERATIVE EDUCATION; แต่ละวิชา 6(0-35-0) และ ไม่มี/NONE; description ต่างกันเรื่องต่างประเทศ | ไม่คัดลอก description ของ alternative หนึ่งให้อีกวิชา ไม่อนุมาน registration permission |
| 93 / 88 | หมวดการสำเร็จการศึกษาแยก curriculum GPA และ cumulative GPA ไม่ต่ำกว่า 2.00; English Exit Exam อ้างประกาศ ไม่ได้ให้ numerical threshold ในหน้านี้ | หมวด/ประกาศที่อ้างยังไม่ครบ ไม่ยืนยัน graduation eligibility รายบุคคล |

**แก้ข้อสรุปรายงานเก่า:** [REVIEW.md](results/diverse_closure_20261010/bit-experiments/REVIEW.md) ระบุว่า OCR เติม “ด้าน” แต่ภาพและ raw probe238 แสดงคำเดียวกันคือ “พื้นฐานทางด้าน...” ข้อสรุป mismatch นี้จึงถอน และไม่ควรใช้ตัวเลข 19/20 ของรายงานนั้นต่อโดยไม่ทบทวน denominator/รายการตรวจ ไม่แก้ raw output เพื่อทำให้คะแนนดีขึ้น ไม่มี CER/WER ใหม่หรือการอ้าง accuracy ทั้งหน้า

Production approvals อยู่ `ocr_final/data/source_reviews/description_prerequisites_20261008.json` แยกจาก evaluation; read-only ตรวจ LIVE BIT2565 ทั้งสอง plans พบ explicit_none evidence ของ 4 courses ข้างต้นแล้ว จึงไม่ repair ซ้ำหรือแทน DB จาก failed OCR

## หลักฐานและสิ่งที่ยังทำไม่ได้

- [temperature0 checkpoint](results/bit_manifest_controls_20261010/temperature0/manifest-extraction.json)
- [temperature0.1 checkpoint](results/bit_manifest_controls_20261010/temperature01/manifest-extraction.json)
- [segmentation checkpoint](results/bit_manifest_controls_20261010/segments2/manifest-extraction.json)
- [diagnostic error body](results/bit_manifest_controls_20261010/diagnostic-predict1024.json)
- [focused tests](results/bit_manifest_controls_20261010/focused-tests-final.txt): 12 tests ผ่าน รวม failed-page budget, include selection, coordinate overlap, temperature cache invalidation และ altered completed content

Verified empty-model-store:0models/readinessfalse/HTTP404/ownedservice stopped/originalmodelsunchanged; [raw](results/bit_manifest_controls_20261010/empty-model-store.json). ใช้ Ollama executable ที่ติดตั้งอยู่แล้ว จึงไม่ใช่ first-machine installation ทั้งหมด

Focusedหลังcitation/parser:27tests/0skipped ผ่าน; [raw](results/bit_manifest_controls_20261010/citation-fix-tests-final.txt). Shared locked runก่อนcitationchange:296unit+7jobs0/guardtrue อยู่ `checks`; เป็น historical ไม่ถือว่า guardหลังruntimeport. ต้องใช้ latest locked runถัดไปสำหรับ current code

ยังไม่ได้: PDF93/257 recovery/chain, full-page OCR accuracy, independent held-out assessment, controlled difficult-question latency, actual process-kill recovery และ first-machine installation ไม่ใช้ unit tests หรือ justified abstention แทนผลเหล่านี้

ขั้นต่อไปไม่ retry configuration เดิม: ตรวจ model/runtime decoding ที่มี token-repeat abort หรือทดลอง prompt ที่แตกต่างจริงแบบจำกัด; ทำ recovery/setup ที่เป็นอิสระต่อไปโดยคงชุดเดิมและไม่ใช้ held-out answers

## ผลล่าสุด: short prompt ร่วมกับ segmentation และ recovery

ข้อสรุปด้านบนที่ระบุว่า 93/257 ยัง HTTP500 เป็นผล historical ของ full-page/default-prompt configurations ไม่ใช่ผลล่าสุด

| PDF / หน้าในเล่ม | transport ล่าสุด | source fidelity หลังดูภาพจริง | การนำไปใช้ |
|---|---|---|---|
| 93 / 88 | 2 segments สำเร็จ | ทั้งสอง segments คืนคำสั่งการถอดข้อความ ไม่ใช่ข้อบังคับในภาพ; ไม่มี graduation-rule extraction ที่ใช้ได้ | เก็บ raw failure ห้ามนับเป็นหน้าที่ถอดถูกหรือป้อน DB |
| 238 / 233 | full-page short prompt สำเร็จ | 2 courses × 5 fields = 10/10 targeted; ไม่ใช่ full-description/CER/WER | isolated chain เท่านั้น |
| 257 / 252 | 2 segments สำเร็จ | 2 courses × 5 fields = 9/10 targeted: code, Thai name, English name, credit pattern, prerequisite; 06036148 เป็น `OVERSEA COOPERERATIVE EDUCATION` แต่ภาพเป็น `OVERSEA COOPERATIVE EDUCATION`; description ซ้ำตรง overlap | parser เก็บ raw error ไม่แก้ให้ดูดีและไม่ส่งเข้า working DB |

ไม่มี alternatives ใน course-description headers ของ PDF257; ไม่ใช้หน้านี้พิสูจน์การเลือกแผนสหกิจ/ไม่สหกิจหรือ permissions. ข้อความแต่ละ course แยกกันชัดเจน: ต่างประเทศระบุใน description ของ 06036148; การตกลง project กับคณะ/หน่วยงานและการนำเสนอต่อกรรมการมีในทั้งสอง descriptions. Category/term ไม่อยู่ใน headers นี้จึงไม่สร้างค่าขึ้นมา

Raw [short-segments2](results/bit_manifest_controls_20261010/short-segments2/manifest-extraction.json) และ [parsed257](results/bit_manifest_controls_20261010/page257-parsed-raw.json) แยกจาก production approvals/evaluation labels. ผล 9/10 ไม่ใช่ความแม่นยำทั้งหมดของ OCR หรือหลักสูตร; ยังมี 302/317 physical pages ที่ manifest ระบุ unreviewed และ 0 skip

### ตรวจผ่าน SQLite และ UI จริง

[isolated257 chain](results/bit_manifest_controls_20261010/isolated-description257-chain.json): working DB ใช้ read-only backup API แล้วเปลี่ยนเฉพาะ 2 raw course rows ในสำเนา; integrity `ok`, program/plan/prerequisite และ working DB hash คงเดิม. 4 unique wordings × 2 endpoints = 8 HTTP requests/8 HTTP200 แต่ **6 substantive correct / 2 source-incorrect** ใน scope ที่ตรวจ: name+credit ของ 06036147 และ prerequisites ของทั้งสองวิชาถูก; name+credit ของ 06036148 ผิด English name ทั้งสอง endpoints. ไม่มี technical failure ใน 8 requests นี้ ไม่ใช่ held-out accuracy

ตัวอย่างจริงจาก UI ของสำเนา BIT-2565-coop:

- คำถาม: `หลักสูตร BIT พ.ศ.2565 แผนสหกิจศึกษา วิชา 06036148 ชื่อภาษาอังกฤษว่าอะไรและมีกี่หน่วยกิต`
- คำตอบจริง: `BIT-2565-coop: 06036148 สหกิจศึกษาต่างประเทศ (OVERSEA COOPERERATIVE EDUCATION), 6 หน่วยกิต, L-P-S 0-35-0 (ที่มา: BIT-65.pdf หน้า 257)`
- DB consistency ผ่าน: UI ถ่ายทอด raw SQLite row ไม่เสริมแก้ชื่อจาก model knowledge
- Source fidelity ไม่ผ่าน English name; Answer completeness ครบสิ่งที่ถามแต่มีค่าผิด; citation navigation เปิดภาพ PDF257/book252 จริง แต่ภาพไม่สนับสนุน spelling ที่ผิด จึงไม่ถือว่า citation support ผ่านสำหรับ English name
- [actual answer](results/bit_manifest_controls_20261010/isolated257-answer.dom.txt), [screenshot](results/bit_manifest_controls_20261010/isolated257-answer.png), [visible source](results/bit_manifest_controls_20261010/isolated257-source.png). SQL/rows/timings เก็บใน chain JSON ไม่แก้ actual outputs

ไม่ได้ซ่อม working data ด้วย raw outputs นี้: production prerequisites explicit_none ของทั้งสอง courses มี separate source approval อยู่ก่อนแล้ว ไม่สร้าง approval จาก parser/evaluation labels

### Actual process interruption

เก็บ failed attempts [cache/atomic-write](results/bit_manifest_controls_20261010/recovery-cache-failed/recovery.json) และ [newline hash](results/bit_manifest_controls_20261010/recovery-newline-failed/recovery.json). พบ Windows `write_text` แปลง LF เป็น CRLF แต่ record ใช้ hash ของ memory LF; resume จึงปฏิเสธไฟล์ของตนเอง. อีกกรณี concurrent reader ทำให้ atomic replacement ถูก deny ชั่วครู่ และ venv launcher ไม่ใช่ PID ของ worker จริง

แก้ generically: เขียน Markdown เป็น UTF-8 bytes/hash ของ stored bytes, atomic replacement retry แบบ bounded 5 attempts แล้ว fail loudly, probe ใช้ base worker โดยตรง. เพิ่ม regression tests ไม่ลด identity guard. [fixed recovery](results/bit_manifest_controls_20261010/recovery-fixed/recovery.json) แสดง actual kill ระหว่าง257 หลัง93 checkpoint, resume exit0, 2 unique processed / 2 requested, pending13/15, source unchanged. ไม่ใช่คุณภาพ OCR pass และยังไม่ได้พิสูจน์ยกเลิก remote model computation ทุกกรณี

Focused19testsผ่านหลัง diagnostics; [output](results/bit_manifest_controls_20261010/recovery-focused-tests.txt). Latest locked run [checks-final3](results/bit_manifest_controls_20261010/checks-final3/checks.json): **307 unit**,30schema,7frontend,70gold,65oldQA,14provenance,6version sets; 7 jobs exit0/dependencies unchanged. เป็น regression scopes ไม่ใช่ source accuracy/untouched held-out assessment. Failed68/70 และ final2 เก็บแยก ไม่เขียนทับ

## เริ่ม fresh study-plan continuation แยกจาก description/regulations

New strong-identity job [plan-first2](results/bit_manifest_controls_20261010/plan-first2/manifest-extraction.json) ใช้ short prompt/200DPI/temp0/retries0/segments1 และ max2 attempts; original12 checkpoints เก็บไว้แต่ไม่ reuse เพราะ identities ไม่ครบตาม guard ใหม่. PDF26/27 สำเร็จ transport2/2 แต่หยุดตาม budget: processed2/15 include, pending13, unreviewed302, skip0; exit1 ระบุ partial ตาม `--continue-on-error` ไม่ใช่ failed transport

ตรวจภาพ source เทียบ claim ใหม่โดยใช้ independent development observations เดิมที่ไม่เปลี่ยน ไม่ทำ Year4 reviews ซ้ำ:

| PDF / หน้าในเล่ม / แผน | scope | raw extraction / parsed SQLite | source fidelity |
|---|---|---|---|
| 26 / 21 / ไม่สหกิจศึกษา | Y1S1,7rows,18credits | HTML ใช้ erroneous rowspans เหลือ4unique codes; Qwen parser และ DB เก็บ4rows/11credits | ไม่ผ่าน:06036118/96641003/96644042หาย ไม่เติมจาก model knowledge |
| 27 / 22 / ต่อเนื่องแผนไม่สหกิจศึกษา | Y1S2และY2S1,6rows/18creditsแต่ละภาค | 12codes/12credit patterns ตรงภาพ; parser/DB 12rows | ผ่านเฉพาะ code/credit/semester fields ที่ตรวจ; English `NON-AccountANTS` เป็น capitalization discrepancy; ไม่อ้าง accuracy ทุก field |

[parse/build](results/bit_manifest_controls_20261010/plan-parse-first2/parse-build.json) ใช้ rawMD เท่านั้น ไม่มี production approvals หรือ evaluation answers เป็น inputs; Qwen3:4b actual installed digestบันทึก,120s/request/retries0, per-page JSON checkpoints. SQLite **สร้างใหม่** ไม่แทน working DB;16course/16plan/0prereq/integrityok และ working hash unchanged. Program metadata จาก working DB read-only แยกและระบุว่าไม่ใช่ whole-program fresh extraction

Structural CHK2–CHK7 ผ่าน แต่ CHK1 ไม่ผ่าน47vs126เพราะเป็น partial book; ตัวเลขนี้ไม่ควรตีความเป็น error79credits จากหนังสือที่ยังไม่ประมวลผล. Independent source comparison [source-check](results/bit_manifest_controls_20261010/plan-first2-source-check.json) แสดง2/3reviewedsemestersผ่าน และ Y1S1ผิด7credits/3missingrows แม้ CHK7 ผ่าน11creditsใน allowed range. จึงห้ามรับ DB ใหม่เป็น source-faithful จาก structural checks เพียงอย่างเดียว; case นี้เป็น OCR loss ที่ส่งต่อ parser ไม่ใช่ source-level absence

Raw extractionยังไม่พร้อมแทน source-reviewed working data; source-approved production corrections เดิมแยกไว้ ไม่แก้ raw หรือ labels เพื่อกลบผล. Untouched held-out, difficult cold/warm latency, all-profile relevant-page reconstruction และ first-machine installation ยังไม่ครบ; legacy source identity และ referenced English Exit thresholds ยังมี evidence gaps
