# การตรวจ IT-2565-coop

## Summary

ฐานข้อมูล: `work/lab8b_it_coop/curriculum.db`; ตรวจรายวิชา 305 แถว
ผลนี้แยก PASS / FAIL / SKIPPED / NEEDS_REVIEW; ยังไม่ใช่ผลยืนยันหนังสือทั้งเล่ม

## HIGH

- NEEDS_REVIEW `prerequisite_coverage` — n/a PDF n/a : ยืนยันข้อมูลวิชาบังคับก่อนจากเล่มแล้ว 4/305 รายวิชา; การไม่มี edge ไม่ได้แปลว่าไม่มีวิชาบังคับก่อน
- FAIL `fidelity_schema` — n/a PDF n/a : ยังไม่มีคอลัมน์: alternative_index, is_placeholder, printed_page_number, raw_code
- NEEDS_REVIEW `code_on_cited_page` — IT.pdf PDF 43 06016481: ไม่พบรหัสใน embedded text ของหน้าอ้างอิง ต้องตรวจภาพหน้านี้; ยังไม่ใช่หลักฐานว่าไม่มีรายวิชา
- SKIPPED `reference_coverage` — general_education_ground_truth.json PDF n/a : ยังไม่มี reference ที่จับคู่ชื่อแหล่งข้อมูลตรงกันสำหรับ general_education_ground_truth.json
- NEEDS_REVIEW `full_source_fidelity` — n/a PDF n/a : การค้นรหัสและหน้าไม่ได้ยืนยันชื่อ หน่วยกิต หมวดวิชา วิชาบังคับก่อน หรือเงื่อนไขจบการศึกษาทั้งเล่มอย่างอิสระ
