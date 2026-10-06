# หลักฐานสำหรับเผยแพร่บน week11_thanapat

ชุดนี้เป็นสำเนาของหลักฐานที่ README อ้างถึง ตัด absolute local paths เป็น `<REPOSITORY>`, `<LIVE_APP>`, `<TEMP>`, `<CODEX_HOME>`, `<LOCAL_USER>` เพื่อไม่เผยตำแหน่งเครื่องส่วนตัว ตัวเลข ผลทดสอบ ชื่อหลักสูตร และเนื้อหาคำตอบคงเดิม ต้นฉบับ raw evidence ยังอยู่ในเครื่องที่ `docs/results/` ไม่ได้ลบหรือทับ

เผยแพร่เฉพาะ source code, source-review approvals, tests, README, assets และหลักฐานที่เกี่ยวข้อง ไม่รวม source PDFs, `.db`, `.env`, venv, models, backups หรือ runtime bundles ไม่ถือว่าการ clone เพียงอย่างเดียวทำให้ถามได้ ต้องเตรียม data ตาม README

## ตรวจครั้งนี้

- [unit tests](publication_unit_final.log): 139/139 ผ่าน พร้อม isolated DB integration
- [schema selftest](publication_schema.log): 30/30 ผ่าน
- [frontend tests](publication_frontend.log): 6/6 ผ่าน
- [README links / PDF routes](publication_links.json): 27/27 local links และ7/7 PDF routes ผ่าน
- [unit run แรก](publication_unit_tests.log): 2 subprocess encoding errors เก็บไว้ตามจริง แก้ child Python ให้ใช้ `-X utf8` และเพิ่ม `PYTHONUTF8=1` ในคำสั่งทดสอบ ไม่แก้ production facts หรือ gold labels

เป็น observed regression/setup checks ไม่ใช่การรับรองทุกคำถามหรือ full independent book accuracy ผล audit/held-out/Appendix gaps ในรายงานยังคงเป็นข้อจำกัดเดิม เผยแพร่เฉพาะ `week11_thanapat` ไม่ merge หรือแก้ main
