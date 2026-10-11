# ผล source reconstruction และ rubric P2 — 11 ตุลาคม 2026

ทำใน repository `ocr_final/` บน `week11_thanapat` ชุด ZIP v6 คงเดิมทั้งหมด การเปลี่ยนแปลงในรายงานนี้ยังไม่ได้ส่งเป็น ZIP ใหม่ ไม่ใช้ผลจาก sibling LIVE เป็นหลักฐาน

## แยกเส้นทางหลักฐาน

| เส้นทาง | ผลจริง | ข้อจำกัด |
|---|---|---|
| Native PDF text/table geometry | DSBA2565 สองแผนสร้าง SQLite และเปิด API ได้ | ไม่ใช่ vision OCR |
| Reviewed font decoding | ใช้ JSON mapping ผูก exact embedded-font hashes เท่านั้น | เป็น reviewed ingestion ไม่ใช่ raw automatic extraction; ไม่มี course corrections |
| Vision OCR | DSBA PDF27 table crop ใหม่ อ่านภาพด้วย Typhoon จริง | พบ material defects; reject ไม่สร้าง DB/activate |
| Source validation | ตรวจ cover + ภาพทุกหน้า DSBA plan + SQLite fields แล้วบันทึก receipt | เป็นการตรวจหลัง extraction ไม่ใช่ผลวัด OCR model accuracy |

Candidate DSBA `20261011T065808-860151f24e` สร้างใน source-only directory เริ่ม DB=0/old OCR=0/master=0/course corrections=0/evaluation=0 หลักฐาน candidate/executor/source images/manifests/receipt/SQLite ถูกเก็บครบใน [dsba-candidate-sealed](results/source_scope_20261011/dsba-candidate-sealed/build.json) ห้ามนำโฟลเดอร์หลักฐานนี้กลับไปใช้เป็น input เพื่ออ้าง fresh reconstruction ใหม่

## ผล DSBA2565 ที่สำเร็จ

| Profile | Source PDF / หน้าพิมพ์ | Native/render | Parse/SQLite | ผล |
|---|---|---|---|---|
| dsba-no-coop |23–29 /22–28|1.607s|1.157s|45 plan rows,8 terms,12 paired-name rows; source validation ผ่าน |
| dsba-coop |30–36 /29–35|1.419s|0.488s|45 plan rows,8 terms,12 paired-name rows; source validation ผ่าน |

แก้ parser ให้หนึ่ง placeholder ที่พิมพ์หลายชื่อยังเป็นหนึ่งช่องหน่วยกิต เก็บคู่ Thai/English ใน `plan_item_source_name` และคง shared hour patterns ไม่เดาจับคู่ชื่อกับชั่วโมง ตัวอย่าง PDF27/28 มีสามกลุ่มชื่อในช่องเดียว; English `ANALYSIS`/`ANALYTICS` และ ordinal ที่ source ไม่พิมพ์ยังคงตามต้นฉบับ ไม่แก้ให้เป็นชื่อที่คาดหวัง

First installation ในสำเนาแยกที่ไม่มี DB เดิม: declared activation สอง DB ผ่าน; full activation ถูก reject; `/ask` และ `/api/ask` รวม40 HTTP ครอบคลุมสองแผน/สอง cycles พร้อม SQL rows/source references PDF27/28/34/35/36 เปิด–หยุด–restart ผ่าน คำถาม description ถูกปฏิเสธตาม scope ดู [ผล API/lifecycle](results/source_scope_20261011/dsba-runtime/verification.json) ตัวเลข regression ไม่ใช้แทน source accuracy

DSBA2565 activate1.823s/start4.100s/restart3.224s ใช้ environment ที่มีอยู่ในสำเนา source-only รอบนี้ ไม่ใช่ cold installation ใหม่บนเครื่องอาจารย์ Hardware/model/configuration ของเครื่องทดสอบอยู่ใน root README

## Active-build health และ frontend

Health ประกาศ build identity/count/paths/partial contract และ method/OCR/review/source validation ต่อ profile/หน้า Frontend เลือกเฉพาะ curriculum/version ที่ queryable ในชุดปัจจุบัน หากไม่มี health ให้ selector/ปุ่มถาม disabled จน readiness ผ่าน ข้อความ partial ระบุว่าเฉพาะแผน ไม่ใช่การสร้าง14 profiles และไม่รองรับ catalog/rules/prerequisites/graduation

ทดสอบ health จริงกับ sealed BIT2 ในสำเนาแยก [active-bit-integrity-final](results/source_scope_20261011/active-bit-integrity-final/verification.json) ทั้งสอง profile ระบุ native/font-review/OCR=false/source validated=true Health ตรวจ actual DB file hash เพิ่ม: DBที่ถูกแก้หลังreceiptไม่คงsource_validated=true; focusedtestsจำลองhash/source/review-fields mismatchผ่าน Node DOM tests ตรวจ selector/disabled state เป็น synthetic DOM ไม่ใช่ browser-click pass Browser policy เดิมบล็อกการใช้งานรอบใหม่ ไม่ใช้ API หรือ PNG แทนการคลิกจริง

## IT2565: source fragments ยังไม่ใช่ reconstructed database

PDF25/หน้าพิมพ์20 ระบุให้เลือกหนึ่งกลุ่มวิชา ตรวจภาพ source แล้ว PDF34/35 และ41/42 พิมพ์ specialization groups เป็น merged cells Parser เดิมถือ group heading เป็นส่วนหนึ่งของชื่อและปฏิเสธ multiple codes ที่ไม่มี “หรือ” ใน code cell

เพิ่ม geometric group-cell decoder แยก heading จากชื่อด้วยตำแหน่งก่อน code แรก ไม่ใช้ course-code/name lookup Fresh source-only diagnostic ได้12 groups/30 course occurrences รักษา paired names/hour patterns รวมรหัสเดียวที่ปรากฏมากกว่าหนึ่ง bundle ดู [source fragments](results/source_scope_20261011/it-group-fragments/inspection.json) **ยังไม่ ingest/activate** เพราะต้องเก็บ whole-bundle coupling ใน SQLite และห้ามนำ ordinal credit slots ไปสื่อว่าเลือกข้ามกลุ่มได้อิสระ

PDF35→36 มี continuation: ชั่วโมง “หรือ3(0-6-3)” บนหน้า36 เป็นส่วนต่อของ placeholder หน้า35 ไม่มี table header ใหม่ ต้องรักษา term/plan boundaries และ citation ของแต่ละ claim ก่อนใช้ อีกแผนมี co-op table ต่อข้าม42→43 การขาด total/header ไม่ใช่ empty/irrelevant page ไม่ rerun unchanged failed full extraction

## การเลือกหน้าและ first native attempt ของ2560

ตรวจ actual cover/plan heading/table images32หน้าใน6 profiles ผูกsource/image hashes แล้วอนุมัติ **page relevance เท่านั้น** [approval](../ocr_final/data/source_reviews/shared/old-plan-page-selection-20261011.json) ไม่มีหน้าใหม่ถูก skip; unreviewed pages อื่นยัง pending ไม่ถือเป็น irrelevant

| Profile | Selected PDF pages | First isolated result | Activation |
|---|---|---|---|
| DSBA2560 no-coop |25–29|5/5 native pages → staged SQLite; ยังไม่ตรวจทุก fact|ไม่ผ่าน source receipt |
| DSBA2560 coop |30–34|4/5; PDF34 alternative relation อยู่ใน name cell ไม่ใช่ code cell|reject |
| IT2560 no-coop |27–33|0/7; exact embedded fonts ไม่มี approved mapping|reject |
| IT2560 coop |34–40|0/7; exact embedded fonts ไม่มี approved mapping|reject |
| BIT2560 no-coop |23–26|4/4 native pages → staged SQLite; ยังไม่ตรวจทุก fact|ไม่ผ่าน source receipt |
| BIT2560 coop |27–30|4/4 native pages → staged SQLite; ยังไม่ตรวจทุก fact|ไม่ผ่าน source receipt |

ชุดที่ขอครบ6 profiles ถูก reject ไม่ลดเป็น3โดยอัตโนมัติ ไม่รับรอง staged rows ว่า source faithful และไม่แทนที่ old usable databases ดู [summary](results/source_scope_20261011/old-build-summary.json) กับ [source-only inputs](results/source_scope_20261011/old-source-sandbox.json)

**รอบแก้ไขที่สำเร็จแยกจาก attempt แรก:** generic parser ตรวจ “หรือ/OR” ที่ boundary ระหว่าง English label แรกกับ Thai label ถัดไปได้ ไม่ตีความ connector กลางชื่อเป็น row choice ไม่มี course-code/name lookup สร้าง source-only directory ใหม่/candidate `20261011T072115-872c2be28e` ขอเฉพาะ `dsba-2560-coop` ชัดเจน:5/5pages →44SQLite rows/8terms/0material defects; cover+PDF30–34/หน้าพิมพ์25–29 ทุกcode/name/hour/placeholder/alternative/plan/citation ตรวจภาพเทียบSQLiteแล้ว source receipt/declared validationผ่าน ฐานข้อมูลSHA `41c20bacf57cc07f611ffd3bb9b8510b014db3023cb98fbe837447fe107a6dee` [sealed evidence](results/source_scope_20261011/old-dsba-candidate-sealed/build.json)

Native/render8.969s +parse/SQLite0.626s (ไม่ใช่ OCR) หลังปิด source construction/validation จึงคัดลอก14DB baseline เข้า **สำเนาทดสอบเท่านั้น** เพื่อทดสอบreplacement ไม่เป็นpipelineinput Explicit14→1 activationผ่าน1.397s,20HTTP `/ask`+`/api/ask`/สองcycles,sourcePDF30/33/34;start4.790s/restart3.630s/recovery14start3.660s Fullgate/consumerlock/missingOCRmodel/partialbuild reject; previouspointer unchanged; injected after-pointerfailureคืนpointer;rollbackคืน14DB/usernote/oldhashesครบ ดู [lifecycle](results/source_scope_20261011/old-dsba-lifecycle/verification.json) สิ่งที่สำเร็จนี้ไม่รวมoldอีก5profiles/whole catalog/prerequisites/program rules

## Vision OCR รอบใหม่: transport สำเร็จแต่ source fidelity ไม่ผ่าน

DSBA PDF27/หน้าพิมพ์26 ปี3/S1 crop table ที่200DPI, Typhoon `scb10x/typhoon-ocr1.5-3b:latest` digest483bac…, temperature0/retries0/context8192/output budget4096 บน shared Ollama เดิม ภาพเท่านั้น + generic transcription prompt ไม่มี native text/course facts/evaluation inputs ระยะ model call207.9s/693 generated tokens; raw output1407characters

เมื่อเทียบภาพต้นฉบับ: codeถูก5/6 printed row occurrences; `9064xxxx` ถูกอ่านเป็น `9064xxxxx` (เพิ่มx), ชั่วโมง `90644042` source3(3-0-6) ถูกอ่านเป็น3(2-2-5); general-education shared hours ขาด association; HTML rowspan4แทน3ชื่อทำให้แถวต่อคลาด แม้ Thai/English labelsส่วนใหญ่และ total18ออกมา ห้ามนับเป็น reconstructed DB success ไม่ส่งเข้า parser/activation เก็บ [raw/response/dependency manifest](results/source_scope_20261011/dsba27-vision-rejected/manifest-extraction.json) อาการเหล่านี้อยู่ใน OCR/layout transcription ไม่ใช่ renderer เพราะภาพ input/source table ชัดเจน ไม่แก้ด้วยเติม DB/master หรือ expected answers และไม่ retry unchanged configuration

## Rubric จริง: explicit กับการตีความ

ใช้ `ch1_Introduction (1).pdf`42หน้า SHA256 `2544eabb0c81ada2a2a6dfa67bf13376112b88564a0ae9ce4a27c88f06e5c9a4` สำเนา byte-identical [P2 course PDF](references/P2-course-introduction.pdf) ไม่อนุมานจากรายงานเก่า

| ข้อกำหนด explicit | PDF page |
|---|---|
| P2 ทำ OCR, ใช้ LLM ตอบคำถามง่าย–ยาก, Database/RAG เก็บข้อมูลจำเป็น |4|
| Database/RAG20, image-reading OCR20, accuracy20, LLM30, app/docs10 |5|
| อ่านข้อมูลจากภาพด้วย CV/LLM-OCR; วัดคุณภาพเชิงตัวเลขทั้งภาพจำลองและจริง; คำตอบถูกพร้อมหน้า/หัวข้ออ้างอิง |5|
| L4 multiple versions และ difficult question <5s รวมretrieval+generate; bonus capped+10 |7|

**การตีความ:** OCRเป็นส่วน explicit ไม่มี native waiver ในหน้าที่ตรวจ Native/font-decoding จึงรายงานเป็นเส้นทาง reconstruction แยก ไม่อ้างเป็น20คะแนน OCR ไม่อ้าง manual/source review เป็น OCR improvement การทดลองภาพจริงที่ reject ข้างต้นแสดง path OCR จริง แต่ยังไม่ทำให้เกณฑ์ด้าน accuracy/ภาพจำลองครบ หรือให้สิทธิ self-award คะแนน Warm structured-query timing ไม่ใช่ difficult-generation latency ดู [บันทึกอ่าน rubric](results/source_scope_20261011/rubric/REVIEW.md) พร้อมภาพPDF4/5/7

## Coverage รวมและสิ่งที่ยังขาด

| Curriculum/version/plan | Required plan PDF pages | ผล reconstruction ที่แยก scope |
|---|---|---|
| AI2566 coop |23–26|nativeเดิม4/4,41options; source/API/scoped lifecycleผ่าน; vision attempt reject |
| DSBA2565 no-coop |23–29|reviewed native7/7,45rows; source/firstinstall/API/restartผ่านรอบนี้ |
| DSBA2565 coop |30–36|reviewed native7/7,45rows; source/firstinstall/API/restartผ่านรอบนี้ |
| IT2565 no-coop |31–37|full attemptเดิม4/7 reject; newPDF34/35group fragmentsเท่านั้น; continuation35→36ยังขาด |
| IT2565 coop |38–44|full attemptเดิม5/7 reject; newPDF41/42group fragmentsเท่านั้น; continuation42→43ยังขาด |
| BIT2565 no-coop |26–30|reviewed native5/5,43rows; v6source/firstinstall/replacement/recoveryผ่านเดิม |
| BIT2565 coop |31–35|reviewed native5/5,43rows; v6source/firstinstall/replacement/recoveryผ่านเดิม |
| DSBA2560 no-coop |25–29|5/5parsed/staged; sourceทุกfield/activationยังไม่ผ่าน |
| DSBA2560 coop |30–34|ใหม่5/5,44rows; source/isolated14→1replacement/API/recoveryผ่าน |
| IT2560 no-coop |27–33|0/7native; unapprovedfont hash; reject |
| IT2560 coop |34–40|0/7native; unapprovedfont hash; reject |
| BIT2560 no-coop |23–26|4/4parsed/staged; sourceทุกfield/activationยังไม่ผ่าน |
| BIT2560 coop |27–30|4/4parsed/staged; sourceทุกfield/activationยังไม่ผ่าน |
| legacy mixed catalog |ไม่มีsource/identity/planที่ยืนยันแยก|ไม่มีfreshreconstruction; fullsetblocked; ห้ามคัดลอกmixedDBมาสร้างidentity |

AI2566หนึ่งprofileผ่าน native plan scope เดิม; BIT2565สองprofilesผ่าน reviewed native ในv6; DSBA2565สองprofilesผ่าน reviewed native source+API รอบนี้; DSBA2560coopหนึ่งprofileผ่าน source+replacement/API/recovery รอบแก้ไขใหม่; IT2565สองprofilesยัง source fragments/continuation blocked; old2560อีก5profilesยังไม่มี source-certified activation; legacyหนึ่งcatalogยัง unresolved identity ห้ามคัดลอกmixed catalogเพื่อสร้างidentityใหม่ รวม14 runtime catalogsไม่ได้เท่ากับ14 source reconstructions

Full replacement ยังต้อง source-backed catalog descriptions/program rules/required coverage และ legacy identity ไม่ลด gate Academic-plan-only ไม่ตอบ catalog/prerequisite/graduation ที่ขาด evidence Working14DB/PDF/v6 unchanged; held-outไม่อ่านหรือใช้ซ่อม Runtime factual answersมาจาก SQLite เท่านั้น Source-reviewed correctionsเป็นbuild inputsที่เปิดเผย ไม่ใช่ factualJSON overlayหลังSQL

## Verification และ dependency boundaries

Locked run:350unit/30schema/11frontend/70developmentgold(14×5)/65old2560/14provenance/6versionchecksผ่านและdependenciesไม่เปลี่ยนระหว่างrun หลังจากนั้นแก้ `source_native.py`/หนึ่งsource parser test และhealth provenance file-hash guard/test: final351unitผ่าน,30schemaผ่านก่อนhealth-onlychange/schema codeไม่เปลี่ยน, newDSBA2560coop source/lifecycleและfinalBIT2healthผ่าน ไม่รันgoldเดิมซ้ำเพราะanswering/retrieval code/DB/PDF/evaluation inputsไม่เปลี่ยน [dependency guard](results/source_scope_20261011/final-dependency-guard.json) Held-outไม่ได้อ่านเพื่อซ่อม ไม่มี independent held-out score ใหม่

Read-onlyauditยังFAIL1372/incomplete51 โดยเฉพาะprerequisite/source coverageและlegacy identity ข้อสรุปเหล่านี้ไม่ได้ถูกปิดด้วยregressionpass [audit evidence](results/source_scope_20261011/current-checks/audit/audit_results.json) Browserpolicyblockยังคงอยู่; ไม่มีnewbrowserclickpass All owned8005/8006stopped และunrelatedLIVE8003/8004/8010/shared11434ไม่หยุดหรือใช้เป็นhandoffproof SHAของcode/dataZIPv6ยังตรงทุกbyte [archive hash evidence](results/source_scope_20261011/v6-after-hashes.json) ไม่มีv7/commit/push/merge
