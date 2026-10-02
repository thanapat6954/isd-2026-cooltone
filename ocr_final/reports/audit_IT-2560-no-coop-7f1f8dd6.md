# การตรวจ IT-2560-no-coop

## Summary

ฐานข้อมูล: `work/lab8b_it_2560_no_coop/curriculum.db`; ตรวจรายวิชา 54 แถว
ผลนี้แยก PASS / FAIL / SKIPPED / NEEDS_REVIEW; ยังไม่ใช่ผลยืนยันหนังสือทั้งเล่ม

## HIGH

- NEEDS_REVIEW `prerequisite_coverage` — n/a PDF n/a : ยืนยันข้อมูลวิชาบังคับก่อนจากเล่มแล้ว 4/54 รายวิชา; การไม่มี edge ไม่ได้แปลว่าไม่มีวิชาบังคับก่อน
- NEEDS_REVIEW `code_on_cited_page` — IT-60.pdf PDF 30 06016346: ไม่พบรหัสใน embedded text ของหน้าอ้างอิง ต้องตรวจภาพหน้านี้; ยังไม่ใช่หลักฐานว่าไม่มีรายวิชา
- NEEDS_REVIEW `full_source_fidelity` — n/a PDF n/a : การค้นรหัสและหน้าไม่ได้ยืนยันชื่อ หน่วยกิต หมวดวิชา วิชาบังคับก่อน หรือเงื่อนไขจบการศึกษาทั้งเล่มอย่างอิสระ
