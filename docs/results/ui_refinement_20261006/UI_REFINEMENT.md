# ผลปรับหน้าค้นข้อมูลหลักสูตร

วันที่ 6 ตุลาคม 2026 บน branch `audit/curriculum-challenge` ใช้ Impeccable สำหรับ layout, typeset, adapt, harden และ polish โดยคง frontend เดิม ภาษาไทย และสีเขียว ไม่แก้ backend, retrieval, API หรือข้อมูลหลักสูตร

## สิ่งที่เปลี่ยน

- พื้นที่คำตอบ desktop จากประมาณ 576px เป็น 849px; พื้นที่ชื่อวิชามือถือจากประมาณ 130px เป็น 318px ที่ viewport 390px
- ใช้ Noto Sans Thai แบบ self-hosted พร้อม OFL license แทนการพึ่ง Thai fallback ที่แสดงผลไม่สม่ำเสมอ
- จัด mobile course rows ให้ชื่อเต็มความกว้าง แยกแผนและกลุ่มวิชาด้วยหัวข้อกับเส้นแบ่ง คงทุกแถว รหัสที่มีเลขศูนย์นำหน้า ตัวเลือก หน่วยกิต รายละเอียด และ citation
- แสดงหลักสูตร/ฉบับ/คำถามของคำตอบที่ได้รับ ไม่เปลี่ยนตาม selector ที่ผู้ใช้เลือกภายหลัง
- citation ระบุ PDF page กับ printed book page แยกกัน และสร้าง link เฉพาะ recorded filename ที่ endpoint อนุญาต ไม่เดาชื่อไฟล์
- เพิ่ม focus ring, skip link, ลิงก์ข้ามไปคำตอบ, validation ใกล้ช่องกรอก, retry และ Thai IME/duplicate-submit guard; ปิดปุ่มตัวอย่างขณะ loading
- บันทึกแนวทางใช้ซ้ำใน `ocr_final/DESIGN.md` และเพิ่ม presentation helper tests กับ release verifier

## ผลตรวจจริง

| รายการ | ผล | หลักฐาน |
| --- | --- | --- |
| existing unit tests | 108/108 | unit_schema.json |
| schema selftests | 30/30 | unit_schema.json |
| frontend helper/contract tests | 6/6 | release_checks.json |
| gold Q&A ทั้ง 14 profiles | 70/70; development regression ไม่ใช่ held-out accuracy | gold.json |
| selector/submission ที่มีใน UI | 10/10 combinations: AIT latest; DSBA/IT/BIT latest, old, all versions | ui_checks.json |
| idle/loading/success/insufficient/error | ตรวจจริง รวม network disconnect/retry และ timeout 30 วินาที | ui_checks.json และภาพสถานะ |
| long answer | L3 DSBA เปรียบเทียบฉบับ 3,156 ตัวอักษร พร้อม 79 sources; แสดงบนมือถือโดยไม่ล้นแนวนอน | ui_checks.json, long_answer_mobile.jpg |
| table content | 20/20 rows ของ IT latest Y2S2 ตรงกับ API ในรหัส/ชื่อ/หน่วยกิต | release_checks.json |
| responsive | viewport 320/390/768/1280px; ไม่มี horizontal overflow ในจุดที่ตรวจ | ui_checks.json |
| keyboard | Enter ส่ง, Shift+Enter ขึ้นบรรทัดใหม่, details เปิดด้วย Enter, focus ring, examples เติมคำถาม, history จำกัด 5 ข้อ | ui_checks.json |
| PDF routes | 7/7 ไฟล์ตอบ 200/206 และเริ่มด้วย %PDF; URL ใช้ page ที่บันทึกจริง | release_checks.json |
| contrast จาก computed colors | body 16.29:1; muted 6.26:1; link 10.54:1; primary button 7.41:1 | release_checks.json |
| deployment | 9/9 code/design/test/asset files live-repo hash ตรงกัน | release_checks.json |
| preservation | backend code, gold และ 18 registered DB files hash ตรงกับผล verified ก่อนหน้า และยังตรงหลังทดสอบ | release_checks.json |
| design detector | exit 0, findings [] | design_scan.json; คำสั่ง `impeccable.cmd detect --json frontend` |
| audit entry | exit 1; 16 datasets, 1,376 FAIL, 4,881 incomplete, missing curricula=[]; ตรงกับข้อจำกัดเดิม ไม่ใช่ UI regression | audit_reports/audit_results.json; อ่านรายงานเฉพาะ Summary/HIGH |

## ภาพก่อนและหลัง

- ก่อน: before_desktop.jpg, before_plan_desktop.jpg, before_mobile.jpg
- หลัง: after_idle_desktop.jpg, after_plan_desktop.jpg, after_plan_mobile.jpg
- เพิ่มเติม: insufficient_desktop.jpg, validation_desktop.jpg, network_error_desktop.jpg, loading_desktop.jpg, timeout_desktop.jpg, long_answer_mobile.jpg

## ข้อจำกัดที่ยังไม่ยืนยัน

- In-app PDF viewer เป็นหน้าว่าง (citation_pdf_viewer.jpg) จึงยืนยันได้เพียง URL ที่เปิดและ HTTP/PDF signature ยังไม่ยืนยันการ render หน้าที่อ้างอิงใน viewer นี้
- ไม่ทดสอบ physical phone, screen reader, browser zoom 200% จริง หรือ OS reduced-motion setting; มี CSS reduced-motion/forced-colors และ unit checks แต่ไม่ใช่ผลตรวจ OS
- open-ended model request หลัง restart ถึง timeout 30 วินาที ตรวจการแจ้งข้อผิดพลาดและรักษาคำถามได้ แต่ไม่ได้ยืนยันคำตอบของ model สำหรับคำถามนั้น ไม่แก้ backend นอกขอบเขต
- legacy ยังไม่มี selector ใน UI; gold มี safety checks ไม่ใช่ accuracy ของเนื้อหา legacy ทั้งเล่ม
- full-book/prerequisite/aggregate citation fidelity และ source-blocked L4 ยังเป็นงาน audit เดิม; ไม่อ้างว่าผล UI ทำให้ข้อจำกัดเหล่านี้หายไป

## วิธีตรวจซ้ำ

จาก app root ใช้ Python environment เดิม:

```powershell
.\scripts\start_web.ps1
python -m unittest discover -s tests -v
python scr/ocr_system/lab8b_curriculum_db.py selftest
node --test tests/test_frontend_presentation.mjs
```

เปิด `http://127.0.0.1:8000/frontend/` ตรวจ selectors, คำถามตัวอย่าง, plan rows, citation links และ network recovery โดยใช้ server จริง ไม่เปิด mock mode

คำสั่ง gold/audit และ paths ของผลอยู่ใน `docs/PROGRESS.md` ตัว verifier ใช้ `python scripts/verify_ui_refinement.py --help`; ต้องมี browser observations จริงก่อน ไม่สร้างภาพหรือผล UI จำลอง Backend หลังตรวจ recovery คือ PID26340; log live `work/web/backend-25691006-032256-323.stderr.log`
