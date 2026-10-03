# การตรวจ BIT-2565-coop

## Summary

ฐานข้อมูล: `work/lab8b_bit_2565_coop/curriculum.db`; ตรวจรายวิชา 302 แถว
ผลนี้แยก PASS / FAIL / SKIPPED / NEEDS_REVIEW; ยังไม่ใช่ผลยืนยันหนังสือทั้งเล่ม

## HIGH

- NEEDS_REVIEW `prerequisite_coverage` — n/a PDF n/a : ยืนยันข้อมูลวิชาบังคับก่อนจากเล่มแล้ว 0/302 รายวิชา; การไม่มี edge ไม่ได้แปลว่าไม่มีวิชาบังคับก่อน
- FAIL `fidelity_schema` — n/a PDF n/a : ยังไม่มีคอลัมน์: alternative_index, is_placeholder, raw_code
- SKIPPED `reference_coverage` — general_education_ground_truth.json PDF n/a : ยังไม่มี reference ที่จับคู่ชื่อแหล่งข้อมูลตรงกันสำหรับ general_education_ground_truth.json
- NEEDS_REVIEW `full_source_fidelity` — n/a PDF n/a : การค้นรหัสและหน้าไม่ได้ยืนยันชื่อ หน่วยกิต หมวดวิชา วิชาบังคับก่อน หรือเงื่อนไขจบการศึกษาทั้งเล่มอย่างอิสระ
