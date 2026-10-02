# การตรวจ DSBA-2560-coop

## Summary

ฐานข้อมูล: `work/lab8b_dsba_2560_coop/curriculum.db`; ตรวจรายวิชา 39 แถว
ผลนี้แยก PASS / FAIL / SKIPPED / NEEDS_REVIEW; ยังไม่ใช่ผลยืนยันหนังสือทั้งเล่ม

## HIGH

- NEEDS_REVIEW `prerequisite_coverage` — n/a PDF n/a : ยืนยันข้อมูลวิชาบังคับก่อนจากเล่มแล้ว 5/39 รายวิชา; การไม่มี edge ไม่ได้แปลว่าไม่มีวิชาบังคับก่อน
- NEEDS_REVIEW `full_source_fidelity` — n/a PDF n/a : การค้นรหัสและหน้าไม่ได้ยืนยันชื่อ หน่วยกิต หมวดวิชา วิชาบังคับก่อน หรือเงื่อนไขจบการศึกษาทั้งเล่มอย่างอิสระ
