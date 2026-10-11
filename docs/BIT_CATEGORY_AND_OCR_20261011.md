# ผลตรวจหมวดวิชาและ empty OCR

## Source → approval → SQLite

ตรวจภาพ BIT PDF20/book15 section3.1.3: `96644xxx` อยู่หมวดวิชาศึกษาทั่วไป กลุ่มภาษาและการสื่อสาร9หน่วยกิต พร้อมทางเลือก `3(3-0-6)` หรือ `3(2-2-5)`. PDF19/book14 แยกหมวดเลือกเสรี6หน่วยกิตออกจากกลุ่มนี้. ไม่อนุมานหมวดจาก study-plan name. ภาพและ render hashes อยู่ [source images](results/bit_category_ocr_20261011/source).

Separate production approval [language category](../ocr_final/data/source_reviews/BIT-2565-no-coop-language-category.json) แก้เฉพาะ plan_item31.category ใน BIT-2565-no-coop จากหมวดเลือกเสรีเป็นหมวดศึกษาทั่วไป. Target row citation ยังคงPDF28/book23; supporting classification evidencePDF20/book15แยกไว้ในapproval. Fresh-ingestion table row เพิ่ม category และ approval reference โดยไม่เปลี่ยน OCR/labels หรือแผนcoop.

Attemptแรกถูก guard ปฏิเสธเพราะ supporting page ไม่ตรง target page ก่อนเขียน LIVE; backup/stage retained. [Final repair](results/bit_category_ocr_20261011/category-repair-final/result.json) เปลี่ยน1field, integrity/idempotence/unaffected facts ผ่าน. SQLite backup SHA256 `fa573126926fe976531f3149857358e1e7f2b8000c411a1215e45f61029dcaad`. ไม่ replace DB ทั้งก้อน; rollback ต้องตรวจ current value และย้อนเฉพาะ approved field จาก backup ไม่ทับ user edits.

## API, UI และ citation แยกสถานะ

คำถาม development: “หลักสูตร BIT พ.ศ.2565 แผนไม่สหกิจศึกษา ปี 3 ภาค 1 มีวิชาเลือกอะไรบ้าง แสดงหมวดวิชา”. ก่อนแก้ list parser ทั้ง2endpoints HTTP422 จาก real-model marker mismatch/program filter; [raw failures](results/bit_category_ocr_20261011/category-api-final.json). Generic qualified noun `วิชาเลือกอะไร`/`วิชาบังคับอะไร` เพิ่มเป็น list intent ไม่ hard-code curriculum facts.

หลังแก้ [2actual requests](results/bit_category_ocr_20261011/category-api-routed.json) HTTP200, SQLite rows ส่ง category ที่แก้แล้ว และ answer แสดง `96644xxx วิชาเลือกด้านภาษาและการสื่อสาร — 3 หน่วยกิต (3(3-0-6) หรือ 3(2-2-5))`. Answer prose ยังไม่แสดง broad category ที่ถามโดยตรง จึง completeness สำหรับคำถามหมวดยัง partial. Citation ที่ส่งยังPDF28/book23 ไม่ใช่หน้า structure20/book15: category-specific citation support ยังopen. ไม่อ้าง source correctness จาก HTTP200.

UIใหม่ยังblocked: browser policy ปฏิเสธ getTab ของ `http://127.0.0.1:8000/source-viewer/BIT-65.pdf?page=28`; ไม่ retry ผ่าน browserอื่นหรือ bypass. ภาพ LIVE จาก batchก่อนหน้าเป็น historical evidence เท่านั้น ไม่ใช่ UI resultใหม่.

## Empty OCR และ bounded experiment

Original PDF30/31/32 model200แต่empty ใช้ fullpage200DPI/temp0/ctx8192/predict2048เหมือนกัน. ภาพไม่ blank: PDF30/book25มี4rows/Y4S2, PDF31/book26มี7rows/Y1S1สหกิจ/18credits, PDF32/book27มี12rows/two semesters. Requests/config/image hashesมี แต่ successful response bodies/stop reasonsเดิมไม่ได้เก็บ จึงยังพิสูจน์ root cause ว่า context/vision resolution ไม่ได้.

เพิ่ม sanitized request/options/image hashes และ response JSON ใน extraction runner (ไม่เก็บ base64 images ซ้ำ). New generic overlapping-two-halves PDF30 ทดลอง1page/2segments. Aliasเก่าไม่ติดตั้งแล้ว; installednameใหม่มี digestเดิม483bac..., ไม่ลบ model. New configuration/outputsแยก [segments30-installed-name](results/bit_category_ocr_20261011/segments30-installed-name/manifest-extraction.json).

Actual calls18.2s/7.1s, stop reason stop,431/250outputtokens; recovered1821chars. Source check: names4/4 และcreditpatterns4/4ปรากฏ, exactplaceholdercodes2/4เท่านั้น (free elective X codesสั้นผิด), alternatives2/2ปรากฏ, row associationsผิดจากrowspan,126mis-taggedเป็นpageและมี invented sealdescription. ไม่ใช่ full-page fidelity. ไม่ parse/build/promote; raw errorsยังอยู่. ไม่ rerun successfulPDF28หรือ unchangedPDF31. Segmentationช่วย transport ในหนึ่งpageแต่ยังไม่ general solution across books.

## Real-LLM bindings และข้อจำกัด

[Original real-Qwen repair](results/bit_category_ocr_20261011/sql-binding-real.json):2callsยังผลิต objectคู่กับ? และ surplusbindingsกับliteralSQL; strictvalidationปฏิเสธจริง. เพิ่ม generic binding syntax examples ใน prompt โดยไม่ทิ้งparameters/คลายvalidator.

[New real call](results/bit_category_ocr_20261011/sql-binding-explicit-syntax.json): matching `:year/:semester`+namedkeys execute readonlyได้ใน1282.96ms. แต่ omitted elective filter คืน6rowsแทน1elective จึงผ่านbindingเท่านั้น ไม่ผ่าน relevance/completeness. Findingยังopen; ไม่อ้าง fallbackทั้งหมดถูกต้องจาก1call. Helperเป็นdiagnosticไม่อ่านgold/held-out และไม่เขียนDB.

## Verification และ installation

- 54focusedtestsผ่าน; [latest gold](results/bit_category_ocr_20261011/gold-final.json)70/70developmentcases across14profiles. ไม่ใช่ held-out/generalaccuracy.
- Read-only audit16datasets/FAIL1372/incomplete4881ยังเดิม; prerequisite4/304 BITno-coop/fullsourcefidelityยังopen. [audit reports](results/bit_category_ocr_20261011/audit).
- [LIVE setup](results/bit_category_ocr_20261011/live-setup.json)14profilesพร้อม/modelพร้อม; [missing-model test](results/bit_category_ocr_20261011/live-missing-model.json)readyfalseจริง โดยไม่ลบexistingmodels. Repository-onlysetupไม่มีDB/PDFที่ต้องจัดเตรียมจึงreadyfalse ไม่เรียกclean-first-machineinstallผ่าน.
- RootREADMEเพิ่ม explicit installed OCR model selection; ยังไม่ทดสอบ fresh model download/first-machineinstall. [Independent evaluation protocol](INDEPENDENT_EVALUATION_PROTOCOL.md) แยกใหม่จากdevelopment; ไม่สร้าง frozen answers จาก exposedcases.

ยังค้าง category prose/supporting citation, realLLM mandatory-filter semantics, reconstruction field fidelity, source-grounded frozen evaluation, broader conditions/prerequisites, controlled difficult latency/recovery และ legacy identity. Latest next action ใช้ [PROGRESS.md](PROGRESS.md) เท่านั้น. Branchweek11_thanapat/no commit/push/merge/slides/video.
