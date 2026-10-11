# ข้อมูลสำหรับ ingestion ที่แยกจากเฉลย evaluation

ไฟล์ใน directory นี้ใช้สร้างหรือแก้ SQLite ผ่านขั้นตอน ingestion ที่มี backup และ provenance ไม่ใช่คำตอบสำหรับ evaluation และไม่ใช่ runtime factual overlay

- `DSBA-2565/master.json` คือข้อมูล master/schedule เดิมที่ใช้ clean import แยกสองแผนผ่าน `schedule_by_plan` / `applicable_plans` การย้ายไม่ได้ยืนยันทุก field กับหนังสือ
- `shared/` เก็บ approval, prerequisite review, canonical name review และ study-plan relationships โดยตรวจขอบเขตและ hash ของแต่ละ approval ก่อนนำเข้า
- `shared/general_education_ground_truth.json` เป็นข้อมูล pool ที่ production build ยังใช้ แต่ PDF provenance ยังไม่ครบ จึงยังไม่ถือว่า source-verified ทั้งไฟล์
- [program_metadata.json](program_metadata.json) และ [graduation_references.json](graduation_references.json) เป็น approvals เดิมที่เก็บไว้ในตำแหน่งเดิม ขอบเขต reference ของภาคผนวกไม่เท่ากับการยืนยันเงื่อนไขจบครบทุกข้อ

ชื่อวิชาใน evaluation หรือผล chatbot ต้องไม่ถูกนำมาแทนข้อเท็จจริงใน directory นี้โดยอัตโนมัติ เฉลยแยกอยู่ [ดัชนี evaluation](../ground_truth/README.md)

## Approval สำหรับ reconstruction รอบ 8 ตุลาคม

- [AI-2566-plan-corrections.json](AI-2566-plan-corrections.json), [BIT-2565-plan-corrections.json](BIT-2565-plan-corrections.json) และ [IT-2565-plan-corrections.json](IT-2565-plan-corrections.json): ตารางภาคที่ตรวจภาพล่าสุด ระบุ PDF/printed page และ source SHA; เฉพาะภาคที่มี approval ไม่ได้ยืนยันทุกชื่อหรือ prerequisite ในทั้งเล่ม
- [IT-2560-plan-corrections.json](IT-2560-plan-corrections.json) และ [BIT-2560-plan-corrections.json](BIT-2560-plan-corrections.json): reuse approved ingestion chains เดิม ตรวจ hash ไม่อ้างว่าเป็น source review ใหม่
- [DSBA-2560-plan-corrections.json](DSBA-2560-plan-corrections.json): แก้ความยาว placeholder เพียงช่อง code จากหลักฐานเดิม ต้องระบุ original row/source page ตรงกันเพียงแถวเดียว
- [current_plan_page_pairs.json](current_plan_page_pairs.json): คู่ PDF/printed folio สำหรับ AI/BIT ใช้ citation-only ingestion ไม่เพิ่มข้อเท็จจริงหลักสูตร

`run_lab8b.py` ใช้ approvals ผ่าน `prepare_source_ingest.py` ลง ingest copy ใหม่ ไม่แก้ `pred_vlm.json` เดิม ข้อมูลทางเลือกใช้ alt_group ร่วมและไม่บวกหน่วยกิตสองครั้ง; placeholder เป็น elective slot ไม่ใช่รหัสเสีย

## Term metadata รอบ 10 ตุลาคม

[DSBA-2565-term-metadata.json](DSBA-2565-term-metadata.json) ระบุ Year4 ทั้งสองแผนจากภาพ PDF29/book28 และPDF36/book35 พร้อมหัวข้อแผน PDF23/book22 และPDF30/book29. ใช้เพิ่ม study_term/study_item หลัง factual ingestion ไม่ใช้ prepare_source_ingest และไม่ใช่ evaluation labels. Importerต้องตรวจชื่อ/rหัส/รูปแบบหน่วยกิต/pagepairs ตรงทุกแถวก่อนเพิ่มmetadata;นับ06026259หรือ06026260ครั้งเดียว. ไม่ยืนยัน prerequisite หรือเงื่อนไขจบจากตารางนี้.
