# ผล Evaluation ที่รันจริง

Application: C:\Users\thana\OneDrive\เอกสาร\ocr_final
Backend: http://127.0.0.1:8026
Suite: All

| ชุด | สถานะ | Exit code |
|---|---|---:|
| checks | ผ่าน | 0 |
| metadata | ผ่าน | 0 |
| graduation | ผ่าน | 0 |
| counterfactual | ผ่าน | 0 |
| audit | ตรวจเสร็จ; พบ FAIL 1372 / incomplete 4881 (ยังไม่รับรองข้อมูลครบ) | 1 |
| owned-backend-cleanup | หยุดแล้ว | 0 |

## รายละเอียดชุดหลัก

| ชุด | จำนวนที่รายงาน | Exit code |
|---|---|---:|
| unit | 230 tests | 0 |
| schema | 30 pass / 0 fail | 0 |
| frontend | 11 tests | 0 |
| gold | ดู JSON รายข้อ | 0 |
| old2560 | ดู JSON รายข้อ | 0 |
| provenance | ดู JSON รายข้อ | 0 |
| version_sets | ดู JSON รายข้อ | 0 |

ดูจำนวน tests และ stdout/stderr ใน checks/checks.json; เมื่อ main runner หยุด ชุดถัดไปยังไม่ได้ตรวจ

- gold : ผ่าน 70 / เก็บผลได้ 70 ข้อ; มี final summary: True

- old2560 : ผ่าน 65 / เก็บผลได้ 65 ข้อ; มี final summary: True

- metadata : ผ่าน 8 / เก็บผลได้ 8 ข้อ; มี final summary: True

- graduation : ผ่าน 39 / เก็บผลได้ 39 ข้อ; มี final summary: True

- counterfactual : ผ่าน 5 / เก็บผลได้ 5 ข้อ; มี final summary: True

## ขอบเขตและข้อจำกัด

- Counterfactual ตรวจ SQLite copies ชั่วคราวและยืนยัน production hashes ไม่เปลี่ยน; ดูผลจริงใน counterfactual.json
- UI 6/6 และ 13/13 ต้องตรวจผ่าน browser จริง แฟ้มนี้ยังไม่ตรวจ UI
- Gold มี missing-evidence/uncertainty cases ไม่ใช่ accuracy ทั้งหนังสือ
- Graduation ตรวจ reference เดิมและทุกแถวเพิ่มเติมกับ source review ที่อนุมัติ ไม่ใช่รับรองสิทธิ์จบ
- Audit findings ไม่ใช่จำนวนคำตอบผิด; ดู audit/ และ audit.stdout.log
- ไม่เปลี่ยน DB, source PDFs, OCR หรือเฉลย และไม่ทำ commit/push
