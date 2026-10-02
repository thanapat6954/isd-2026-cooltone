# การตรวจ AI-coop

## Summary

ฐานข้อมูล: `work/lab8b_ai/curriculum.db`; ตรวจรายวิชา 299 แถว
ผลนี้แยก PASS / FAIL / SKIPPED / NEEDS_REVIEW; ยังไม่ใช่ผลยืนยันหนังสือทั้งเล่ม

## HIGH

- NEEDS_REVIEW `prerequisite_coverage` — n/a PDF n/a : 0/299 courses have explicit source-reviewed prerequisite status; no edge does not mean no prerequisite
- SKIPPED `reference_coverage` — general_education_ground_truth.json PDF n/a : No exact source-file reference mapping for general_education_ground_truth.json
- NEEDS_REVIEW `full_source_fidelity` — n/a PDF n/a : Code/page locator checks do not independently validate names, credits, categories, prerequisites or graduation rules across the full book
