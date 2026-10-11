# ตัวอย่างหลักฐาน Evaluation ที่เก็บจริง

[example-20261012-044635](example-20261012-044635/REPORT.md) เป็นรอบที่ผู้ใช้รัน All เองเมื่อ 2026-10-12 เวลา 04:46 บนโฟลเดอร์ LIVE ocr_final ก่อนเพิ่มตัวเก็บหลักฐานอัตโนมัติใน branch นี้ คัดลอกจากผลจริงโดยไม่แก้คะแนน คำตอบ paths หรือ failure status และเก็บ JSON/logs/audit รายข้อครบ ไม่ใช่รายงานสรุปที่เขียนขึ้นแทนการรัน

| ชุด | ผลที่บันทึกไว้ |
|---|---:|
| Unit / Schema / Frontend | 230 / 30 / 11 ผ่าน |
| Gold / Older2560 | 70/70 / 65/65 |
| Metadata / Graduation / Counterfactual | 8/8 / 39/39 / 5/5 |
| Provenance / Version sets | 14 profiles / 6 checks ผ่าน |
| Audit | FAIL1372 / incomplete4881; execution errors0; ยังไม่ผ่าน source completeness |

อ่าน [summary.json](example-20261012-044635/summary.json), [คำตอบ Metadata](example-20261012-044635/metadata.json), [Graduation](example-20261012-044635/graduation.json), [checks/checks.json](example-20261012-044635/checks/checks.json) และ [Audit](example-20261012-044635/audit/audit_results.json) เพื่อดูคำถาม คำตอบ citations และ raw logs พร้อมขอบเขตจริง Source/build/input file hashes ของรอบนั้นอยู่ใน checks/checks.json ไม่ได้อ้างว่าเป็นการทดสอบ clean clone ของ commit ที่เผยแพร่ภายหลัง

ดาวน์โหลด [ZIP หลักฐาน](example-20261012-044635/evaluation-evidence.zip) คู่กับ [SHA256SUMS.txt](example-20261012-044635/SHA256SUMS.txt) หรือใช้ทั้งโฟลเดอร์จาก Code ZIP แล้วตรวจจาก ocr_final:

```powershell
.\venv\Scripts\python.exe scripts/archive_evaluation.py verify --evidence .\evaluation_evidence\example-20261012-044635
```

ทุกไฟล์เดิมมีขนาด/SHA256 ใน [EVIDENCE_MANIFEST.json](example-20261012-044635/EVIDENCE_MANIFEST.json) ตรวจทั้ง raw files และ ZIP entries ได้ การแตก ZIP ต้องคัดลอก ZIP ต้นฉบับและ SHA256SUMS.txt ไว้ในโฟลเดอร์ที่แตกก่อน verify ตาม [คู่มือ ZIP](https://github.com/thanapat6954/isd-2026-cooltone/blob/week11_thanapat/docs/INSTRUCTOR_ZIP_SETUP.md)

ตัวอย่างนี้ยังไม่ใช่ full-book accuracy, independent held-out score หรือ UI6/6/13/13 และไม่รับรองสิทธิ์จบ/ลงทะเบียน จำนวน Unit tests ของ branch ล่าสุดอาจมากกว่า 230 เพราะมี tests เพิ่มภายหลัง ให้ใช้จำนวนและ dependency hashes ที่รอบนั้นบันทึกไว้

อาจารย์สร้างหลักฐานของเครื่องตนเองได้ด้วย run_evaluation.ps1 ผลใหม่จะอยู่ใน evaluation_runs/evaluation-วันเวลา-id ไม่เขียนทับตัวอย่างนี้และไม่ commit/push อัตโนมัติ ดู [คู่มือรัน](../RUN_EVALUATION.md)
