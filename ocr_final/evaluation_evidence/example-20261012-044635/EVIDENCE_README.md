# หลักฐาน Evaluation รอบนี้

REPORT.md คือสรุปผลจริง JSON เก็บผลรายคำถาม/คำตอบ/แหล่งอ้างอิงและสถานะ tests ส่วน logs เก็บ stdout/stderr และ audit/ เก็บ findings หากรอบนี้รัน Audit

ไฟล์เดิมถูกคัดลอกหลังรันจบโดยไม่แก้คำตอบ คะแนน หรือ path ของเครื่องที่รัน EVIDENCE_MANIFEST.json บันทึกขนาดและ SHA256 ของทุกไฟล์ รวมทั้ง scope/job exit codes ไม่มี DB/PDF/model weights ใน ZIP นี้

ส่ง evaluation-evidence.zip พร้อม SHA256SUMS.txt ให้อาจารย์ได้ หรือส่งทั้งโฟลเดอร์ หากต้องการตรวจ ZIP หลังแตก ให้คัดลอก ZIP ต้นฉบับและ SHA256SUMS.txt เข้าโฟลเดอร์ที่แตกด้วย แล้วรันจาก ocr_final:

```powershell
.\venv\Scripts\python.exe scripts/archive_evaluation.py verify --evidence <เส้นทางโฟลเดอร์หลักฐาน>
```

SHA256 ยืนยันว่าไฟล์ยังตรงกับชุดที่บันทึก ไม่ได้พิสูจน์ว่า facts ทั้งเล่มถูกต้อง การยืนยันซ้ำต้องรันโค้ดกับข้อมูลที่ประกาศ scope เอง Failed/incomplete findings และการไม่ตรวจ UI จริงยังคงแสดงตามผลเดิม
