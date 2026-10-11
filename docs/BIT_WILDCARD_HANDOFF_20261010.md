# ผล bounded wildcard batch และงานที่ยังไม่ผ่าน

## ขอบเขตและผล source review

- BIT-2565 แผนไม่สหกิจศึกษา PDF28 / หน้าเล่ม23: ตรวจ full rendered page แล้ว ตารางล่างปี3/ภาค1 มี6แถว รวม18หน่วยกิต. Plan identity ใช้ review ของ section3.1.4.1 PDF26 เดิม ไม่ยืมจากแผนสหกิจศึกษา.
- Crop original pixels `(240,1130,1570,2090)` ที่200DPI เก็บ heading ตารางล่างและทุกแถว; full PNG คงไว้สำหรับบริบท/folio. `--region-context` อยู่ใน renderer identity/segment metadata ไม่ส่งเข้า OCR prompt. เป็น page-specific experiment ไม่ใช่วิธีทั่วไปที่พิสูจน์ครบทุกเล่ม.
- Raw ใหม่ตรง6/6รหัส รวม `96644xxx`, 6/6credit patterns, 6/6ชื่อไทย และ6/6ชื่ออังกฤษเมื่อไม่นับความต่างช่องว่าง/line wrapping. ไม่ใช่ CER/WER หรือ Exact Match ทั้งหน้า. ทางเลือก `3(3-0-6) หรือ 3(2-2-5)` คงอยู่. Raw ยังสร้าง footer มหาวิทยาลัยเทคโนโลยีสุรนารีที่ source ไม่มี จึงไม่ผ่าน full-page fidelity.
- Parse ใหม่คง6แถว; isolated SQLite มี6plan rows/5catalog courses, integrity=ok และ working_db_unchanged=true. Placeholder มี raw_code=96644xxx/code_pattern=96644XXX/credits_raw ทั้งสองทางเลือก. Prerequisite ทั้ง6ยัง unknown: ตารางนี้ไม่ได้ยืนยันว่าไม่มี. Category/ctype ที่โมเดลสร้างยังไม่ source-verified.

## API และการแก้ general code

- Compound list+total เพิ่มชื่อจาก plan/course ใน selected SQLite, raw_code และ credits_raw พร้อม calculation; ไม่แตะ facts/DB/evaluation labels. Alternative groups ใช้ MIN contribution ครั้งเดียวตาม view.
- ตัวอย่าง actual isolated answer: `BIT-2565-no-coop ปี 3 ภาค 1: 18 หน่วยกิต ... 96644xxx วิชาเลือกด้านภาษาและการสื่อสาร: 3 หน่วยกิต [3(3-0-6) หรือ 3(2-2-5)]; การคำนวณ: 3 + 3 + 3 + 3 + 3 + 3 = 18 หน่วยกิต`.
- Development3uniquequestions ×2routes=6requests. Baseline หลังcompoundfix: 4 substantive correct /2irrelevant (elective-list ถามรูปแบบหน่วยกิตแต่ตอบyear total). หลังlist-vs-total routing fix: 4substantive/2technical422. SQL guard ปฏิเสธ literal `'elective'` ที่ไม่ปรากฏในคำถามไทย; repair attempts ต่อมาพบ named-parameter mismatch. ยังไม่แก้ผ่าน; ไม่ยอมรับ HTTP200 เดิมเป็นpass. Case นี้เป็นdevelopmentไม่ใช่held-out.
- Focused21tests ผ่าน แต่ไม่ยืนยัน source fidelity/ครบทุกprofile/actualbrowser. Source→raw→parse→isolatedDB→API สำเร็จเฉพาะ4requestsข้างต้น; UI/citation navigation ของbatchนี้ยังไม่ได้ตรวจ.
- Runtime files port ไป LIVE disk หลังเทียบdiff แต่ backend8000ยังเป็นprocessเดิม ไม่ restart/ไม่ claim LIVEsuccess. ต้องแก้ elective-list regression แล้ว rerun/code-lock ก่อนcontrolledrestart.

## Budget และ reconstruction

- PDF28:1newattempt สำเร็จเฉพาะเป้าหมายwildcard/fields, ไม่ retryเพิ่ม.
- PDF26/93/257:0newattemptในbatchนี้ เพราะ priorcrop/ink/header experiments ไม่แก้spelling/numberingอย่างสม่ำเสมอและไม่มีhypothesisใหม่. Failed evidenceเดิมคงไว้; ไม่แก้rawจากlabels/workingDB.
- ต่อindependent fresh fullpagePDF30: model200แต่emptyresponse,25.42s,0processed. ไม่เปลี่ยนหน้าเป็นskip/irrelevant.
- Handoffเริ่มbackgroundPDF31เวลา22:48:07+07:00ผ่านStart-Process Hidden พร้อมstdout/stderr; PID19844/basePython1744. งานจบด้วยmodel200/emptyresponse11.01s,0processed/1failed,requested31pending. Processไม่ทำงานแล้ว ณ finalcheck. ไม่ retryunchangedsettings.
- Manifestยัง317physical/include15/skip0/unreviewed302. Crop28เป็นส่วนหนึ่งของหน้า ไม่ใช่fullbookreconstruction. PDF30/31ไม่มีusableextractionจึงยังไม่parse/build.

## หลักฐาน

ทั้งหมดอยู่ใต้ [results/bit_manifest_controls_20261010](results/bit_manifest_controls_20261010):

- `bit-wildcard28-context-20261010/`: immutable raw/fullPNG/crop/manifest/model cache.
- `bit-wildcard28-parse-20261010/`: raw model calls/parsed/converted/isolated partial.db/checks.
- `bit-wildcard28-api-20261010/` และ `bit-wildcard28-api-fixed-20261010/`: actual requests/responses/SQL/logs; เก็บ historicalfailure.
- `bit-relevant30-20261010/`, `bit-relevant31-handoff-20261010/`: failedcheckpoint/fullPNG/cache/dependencies.
- `page31-background.stdout.log`, `page31-background.stderr.log`: actualindependentjoblogs.

ยังไม่วัดใหม่: all-profile regressions, gold, held-out, difficultLLM latency, UI และsource coverageนอกหน้า28. ไม่มีworkingDBwrites/backupใหม่/no publication.
