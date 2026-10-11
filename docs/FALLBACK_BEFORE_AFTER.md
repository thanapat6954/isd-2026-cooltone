# ผลก่อนและหลังแก้ unknown fallback

## ขอบเขตและข้อจำกัด

ใช้ real qwen3:4b ผ่าน HTTP จริงกับ SQLite สำเนา IT-2565-coop; ไม่อ่าน held-out และไม่แก้ working DB. ตัวอย่างทั้งหมดเป็น development regression ไม่ใช่ independent accuracy. ข้อมูล course 305 แถวไม่มี description_th ที่ไม่ว่าง จึงคาดหวังการแจ้งข้อจำกัด ไม่ใช่คำตอบเนื้อหาที่แต่งเพิ่ม.

แก้ generic topic extraction: รับเฉพาะ literal spans จากคำถาม สร้าง SELECT โดยโปรแกรมและใช้ SQL validator เดิม. ตัด program-summary bias; ไม่ถือคำอธิบายคล้ายกันเป็นความสัมพันธ์ที่หนังสือระบุ. Null descriptions ไม่เข้า evidence selection และบอกแถวที่ยังขาดข้อมูล.

เพิ่ม retrieval ของ prerequisite ที่ปลายทั้งสองอยู่ใน course candidates ของคำถามเดียวกัน; เป็น explicit stored edge ไม่ใช่ inference จาก description. ยังไม่ครอบคลุม relationship ชนิดอื่นหรือรับรอง completeness. Printed folios ที่ DB ไม่ได้บันทึกยังไม่ยืนยันในคำตอบ ห้ามเดา offset. รอบนี้ตรวจ fallback ของ IT-2565-coop และ IT-2560-coop รวมคำถาม ambiguous; หลักสูตรและแผนอื่นยังไม่ทดสอบ fallback ใหม่.

## ตัวอย่างจริงก่อนและหลัง

### ชุด `release-cases`

[ผลดิบ](results/fallback_relevance_20261009/release-cases/result.json)

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างการพัฒนาซอฟต์แวร์กับระบบคอมพิวเตอร์ โดยอ้างเฉพาะข้อมูลที่บันทึกไว้

คำตอบก่อนแก้:

IT-2565-coop — ชื่อภาษาไทย: เทคโนโลยีสารสนเทศ (สหกิจศึกษา); หน่วยกิตรวม: 129; ระยะเวลาศึกษา (ปี): 4

ก่อนแก้ HTTP 200; 12954.78 ms. อ้างอิง [ผลเดิม](results/it_metadata_timeout_20261009/fallback-45s/result.json).

SQL และแถวก่อนแก้:

```json
{
  "sql": "SELECT name_th, name_en, total_credits, years, source_file, page_number FROM program LIMIT 100",
  "rows": [
    {
      "name_th": "เทคโนโลยีสารสนเทศ (สหกิจศึกษา)",
      "name_en": null,
      "total_credits": 129,
      "years": 4,
      "source_file": "IT.pdf",
      "page_number": 44,
      "_source": {
        "database_path": "C:\\Users\\thana\\OneDrive\\เอกสาร\\isd-2026-cooltone\\docs\\results\\it_metadata_timeout_20261009\\fallback-45s\\app\\work\\lab8b_it_coop\\curriculum.db",
        "database_name": "lab8b_it_coop",
        "curriculum_name": "IT-2565-coop",
        "program_id": "IT-coop",
        "curriculum_version": 2565,
        "plan": "coop",
        "source_folder": "work/lab8b_it_coop"
      }
    }
  ],
  "detail": null
}
```

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ไม่มีหลักฐานความสัมพันธ์ระหว่างรายวิชาที่บันทึกไว้ในผลที่ดึงจาก SQLite; คำอธิบายหรือยอดรวมหลักสูตรเพียงอย่างเดียวไม่ยืนยันความสัมพันธ์

HTTP 200; end-to-end 944.73 ms.

SQL จริง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0) LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  },
  {
    "code": "06016417",
    "name_th": "เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์",
    "name_en": "SOFTWARE DEVELOPMENT TOOLS AND ENVIRONMENTS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 42
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 LIMIT 100",
    "row_count": 3,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  },
  {
    "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0) LIMIT 100",
    "row_count": 0,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None), ('IT.pdf', 42, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างการพัฒนาซอฟต์แวร์กับระบบคอมพิวเตอร์ โดยอ้างเฉพาะข้อมูลที่บันทึกไว้

คำตอบก่อนแก้:

not recorded

ก่อนแก้ HTTP 422; 4503.41 ms. อ้างอิง [ผลเดิม](results/it_metadata_timeout_20261009/fallback-45s/result.json).

SQL และแถวก่อนแก้:

```json
{
  "sql": null,
  "rows": null,
  "detail": null
}
```

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ไม่มีหลักฐานความสัมพันธ์ระหว่างรายวิชาที่บันทึกไว้ในผลที่ดึงจาก SQLite; คำอธิบายหรือยอดรวมหลักสูตรเพียงอย่างเดียวไม่ยืนยันความสัมพันธ์

HTTP 200; end-to-end 1098.97 ms.

SQL จริง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0) LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  },
  {
    "code": "06016417",
    "name_th": "เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์",
    "name_en": "SOFTWARE DEVELOPMENT TOOLS AND ENVIRONMENTS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 42
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100",
    "row_count": 3,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  },
  {
    "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0) LIMIT 100",
    "row_count": 0,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None), ('IT.pdf', 42, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาระบบคอมพิวเตอร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้

HTTP 200; end-to-end 916.58 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาระบบคอมพิวเตอร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้

HTTP 200; end-to-end 1230.56 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างระบบคอมพิวเตอร์กับการพัฒนาซอฟต์แวร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ไม่มีหลักฐานความสัมพันธ์ระหว่างรายวิชาที่บันทึกไว้ในผลที่ดึงจาก SQLite; คำอธิบายหรือยอดรวมหลักสูตรเพียงอย่างเดียวไม่ยืนยันความสัมพันธ์

HTTP 200; end-to-end 1036.76 ms.

SQL จริง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0) LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  },
  {
    "code": "06016417",
    "name_th": "เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์",
    "name_en": "SOFTWARE DEVELOPMENT TOOLS AND ENVIRONMENTS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 42
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 LIMIT 100",
    "row_count": 3,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  },
  {
    "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0) LIMIT 100",
    "row_count": 0,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None), ('IT.pdf', 42, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างระบบคอมพิวเตอร์กับการพัฒนาซอฟต์แวร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ไม่มีหลักฐานความสัมพันธ์ระหว่างรายวิชาที่บันทึกไว้ในผลที่ดึงจาก SQLite; คำอธิบายหรือยอดรวมหลักสูตรเพียงอย่างเดียวไม่ยืนยันความสัมพันธ์

HTTP 200; end-to-end 924.07 ms.

SQL จริง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0) LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  },
  {
    "code": "06016417",
    "name_th": "เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์",
    "name_en": "SOFTWARE DEVELOPMENT TOOLS AND ENVIRONMENTS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 42
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 LIMIT 100",
    "row_count": 3,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  },
  {
    "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0) LIMIT 100",
    "row_count": 0,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None), ('IT.pdf', 42, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาวิชาเวทมนตร์ควอนตัม

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

ยังยืนยันข้อมูลที่ถามไม่ได้จากฐานข้อมูลที่ค้น: IT-2565-coop ข้อมูลที่นำเข้าอาจไม่ครบ จึงยังสรุปไม่ได้ว่ารายวิชาหรือเงื่อนไขนี้ไม่มีในเล่มหลักสูตร — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้

HTTP 200; end-to-end 507.50 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('เวทมนตร์ควอนตัม')) > 0 OR INSTR(LOWER(name_en), LOWER('เวทมนตร์ควอนตัม')) > 0 OR INSTR(LOWER(description_th), LOWER('เวทมนตร์ควอนตัม')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('เวทมนตร์ควอนตัม')) > 0 OR INSTR(LOWER(name_en), LOWER('เวทมนตร์ควอนตัม')) > 0 OR INSTR(LOWER(description_th), LOWER('เวทมนตร์ควอนตัม')) > 0 LIMIT 100",
    "row_count": 0,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: n/a; ไม่มีหลักฐานรายวิชาที่ดึงมา

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาวิชาเวทมนตร์ควอนตัม

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

ยังยืนยันข้อมูลที่ถามไม่ได้จากฐานข้อมูลที่ค้น: IT-2565-coop ข้อมูลที่นำเข้าอาจไม่ครบ จึงยังสรุปไม่ได้ว่ารายวิชาหรือเงื่อนไขนี้ไม่มีในเล่มหลักสูตร — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้

HTTP 200; end-to-end 958.28 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('เวทมนตร์ควอนตัม')) > 0 OR INSTR(LOWER(name_en), LOWER('เวทมนตร์ควอนตัม')) > 0 OR INSTR(LOWER(description_th), LOWER('เวทมนตร์ควอนตัม')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('เวทมนตร์ควอนตัม')) > 0 OR INSTR(LOWER(name_en), LOWER('เวทมนตร์ควอนตัม')) > 0 OR INSTR(LOWER(description_th), LOWER('เวทมนตร์ควอนตัม')) > 0 LIMIT 100",
    "row_count": 0,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: n/a; ไม่มีหลักฐานรายวิชาที่ดึงมา

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

### ชุด `stored-relationship-final`

[ผลดิบ](results/fallback_relevance_20261009/stored-relationship-final/result.json)

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างโครงงาน 1 กับโครงงาน 2

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

IT-2565-coop — รหัสวิชา: 06016407; วิชาบังคับก่อน: 06016406; ประเภทความสัมพันธ์ที่บันทึก: pre — แสดงเฉพาะความสัมพันธ์ที่บันทึกในตาราง prerequisite ไม่ยืนยันความเชื่อมโยงเนื้อหาอื่น

HTTP 200; end-to-end 1055.98 ms.

SQL จริง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016406",
    "name_th": "โครงงาน 1",
    "name_en": "PROJECT 1",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 43
  },
  {
    "code": "06016407",
    "name_th": "โครงงาน 2",
    "name_en": "PROJECT 2",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 44
  },
  {
    "code": "06016407",
    "requires": "06016406",
    "kind": "pre",
    "source_file": "IT.pdf",
    "page_number": 326,
    "printed_page_number": null
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  },
  {
    "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) LIMIT 100",
    "row_count": 1,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 43, None), ('IT.pdf', 44, None), ('IT.pdf', 326, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: ตอบ explicit edge ที่มีใน SQLite (06016407 → 06016406, kind=pre) ไม่แทนด้วย description หรือ program summary. เป็น substantive DB-backed answer ของความสัมพันธ์ชนิดนี้เท่านั้น ไม่ใช่การยืนยันเงื่อนไขอื่น; PDF326 ระบุจาก stored edge แต่ printed folio NULL จึง citation ยังไม่ครบ. ไม่ได้ตรวจ book page ใหม่ในชุดนี้.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างโครงงาน 1 กับโครงงาน 2

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

IT-2565-coop — รหัสวิชา: 06016407; วิชาบังคับก่อน: 06016406; ประเภทความสัมพันธ์ที่บันทึก: pre — แสดงเฉพาะความสัมพันธ์ที่บันทึกในตาราง prerequisite ไม่ยืนยันความเชื่อมโยงเนื้อหาอื่น

HTTP 200; end-to-end 981.29 ms.

SQL จริง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016406",
    "name_th": "โครงงาน 1",
    "name_en": "PROJECT 1",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 43
  },
  {
    "code": "06016407",
    "name_th": "โครงงาน 2",
    "name_en": "PROJECT 2",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 44
  },
  {
    "code": "06016407",
    "requires": "06016406",
    "kind": "pre",
    "source_file": "IT.pdf",
    "page_number": 326,
    "printed_page_number": null
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  },
  {
    "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) LIMIT 100",
    "row_count": 1,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 43, None), ('IT.pdf', 44, None), ('IT.pdf', 326, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: ตอบ explicit edge ที่มีใน SQLite (06016407 → 06016406, kind=pre) ไม่แทนด้วย description หรือ program summary. เป็น substantive DB-backed answer ของความสัมพันธ์ชนิดนี้เท่านั้น ไม่ใช่การยืนยันเงื่อนไขอื่น; PDF326 ระบุจาก stored edge แต่ printed folio NULL จึง citation ยังไม่ครบ. ไม่ได้ตรวจ book page ใหม่ในชุดนี้.

### ชุด `citation-pairs`

[ผลดิบ](results/fallback_relevance_20261009/citation-pairs/result.json)

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างโครงงาน 1 กับโครงงาน 2

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

IT-2565-coop — รหัสวิชา: 06016407; วิชาบังคับก่อน: 06016406; ประเภทความสัมพันธ์ที่บันทึก: pre — แสดงเฉพาะความสัมพันธ์ที่บันทึกในตาราง prerequisite ไม่ยืนยันความเชื่อมโยงเนื้อหาอื่น

HTTP 200; end-to-end 1122.10 ms.

SQL จริง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016406",
    "name_th": "โครงงาน 1",
    "name_en": "PROJECT 1",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 43,
    "printed_page_number": 38
  },
  {
    "code": "06016407",
    "name_th": "โครงงาน 2",
    "name_en": "PROJECT 2",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 44,
    "printed_page_number": 39
  },
  {
    "code": "06016407",
    "requires": "06016406",
    "kind": "pre",
    "source_file": "IT.pdf",
    "page_number": 326,
    "printed_page_number": null
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": [
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": []
      }
    ]
  },
  {
    "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) LIMIT 100",
    "row_count": 1,
    "error": null,
    "repair_attempts": [],
    "citation_queries": [
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=326 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=326 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 326,
            "printed_page_number": null
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=326 LIMIT 100",
        "rows": []
      }
    ]
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 43, 38), ('IT.pdf', 44, 39), ('IT.pdf', 326, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: ตอบ explicit edge ที่มีใน SQLite (06016407 → 06016406, kind=pre) ไม่แทนด้วย description หรือ program summary. เป็น substantive DB-backed answer ของความสัมพันธ์ชนิดนี้เท่านั้น ไม่ใช่การยืนยันเงื่อนไขอื่น; PDF326 ระบุจาก stored edge แต่ printed folio NULL จึง citation ยังไม่ครบ. ไม่ได้ตรวจ book page ใหม่ในชุดนี้.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างโครงงาน 1 กับโครงงาน 2

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

IT-2565-coop — รหัสวิชา: 06016407; วิชาบังคับก่อน: 06016406; ประเภทความสัมพันธ์ที่บันทึก: pre — แสดงเฉพาะความสัมพันธ์ที่บันทึกในตาราง prerequisite ไม่ยืนยันความเชื่อมโยงเนื้อหาอื่น

HTTP 200; end-to-end 929.57 ms.

SQL จริง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016406",
    "name_th": "โครงงาน 1",
    "name_en": "PROJECT 1",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 43,
    "printed_page_number": 38
  },
  {
    "code": "06016407",
    "name_th": "โครงงาน 2",
    "name_en": "PROJECT 2",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 44,
    "printed_page_number": 39
  },
  {
    "code": "06016407",
    "requires": "06016406",
    "kind": "pre",
    "source_file": "IT.pdf",
    "page_number": 326,
    "printed_page_number": null
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": [
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": []
      }
    ]
  },
  {
    "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 1')) > 0 OR INSTR(LOWER(name_th), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน 2')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน 2')) > 0) LIMIT 100",
    "row_count": 1,
    "error": null,
    "repair_attempts": [],
    "citation_queries": [
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=326 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=326 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 326,
            "printed_page_number": null
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=326 LIMIT 100",
        "rows": []
      }
    ]
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 43, 38), ('IT.pdf', 44, 39), ('IT.pdf', 326, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: ตอบ explicit edge ที่มีใน SQLite (06016407 → 06016406, kind=pre) ไม่แทนด้วย description หรือ program summary. เป็น substantive DB-backed answer ของความสัมพันธ์ชนิดนี้เท่านั้น ไม่ใช่การยืนยันเงื่อนไขอื่น; PDF326 ระบุจาก stored edge แต่ printed folio NULL จึง citation ยังไม่ครบ. ไม่ได้ตรวจ book page ใหม่ในชุดนี้.

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างการพัฒนาซอฟต์แวร์กับระบบคอมพิวเตอร์ โดยอ้างเฉพาะข้อมูลที่บันทึกไว้

คำตอบก่อนแก้:

IT-2565-coop — ชื่อภาษาไทย: เทคโนโลยีสารสนเทศ (สหกิจศึกษา); หน่วยกิตรวม: 129; ระยะเวลาศึกษา (ปี): 4

ก่อนแก้ HTTP 200; 12954.78 ms. อ้างอิง [ผลเดิม](results/it_metadata_timeout_20261009/fallback-45s/result.json).

SQL และแถวก่อนแก้:

```json
{
  "sql": "SELECT name_th, name_en, total_credits, years, source_file, page_number FROM program LIMIT 100",
  "rows": [
    {
      "name_th": "เทคโนโลยีสารสนเทศ (สหกิจศึกษา)",
      "name_en": null,
      "total_credits": 129,
      "years": 4,
      "source_file": "IT.pdf",
      "page_number": 44,
      "_source": {
        "database_path": "C:\\Users\\thana\\OneDrive\\เอกสาร\\isd-2026-cooltone\\docs\\results\\it_metadata_timeout_20261009\\fallback-45s\\app\\work\\lab8b_it_coop\\curriculum.db",
        "database_name": "lab8b_it_coop",
        "curriculum_name": "IT-2565-coop",
        "program_id": "IT-coop",
        "curriculum_version": 2565,
        "plan": "coop",
        "source_folder": "work/lab8b_it_coop"
      }
    }
  ],
  "detail": null
}
```

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ไม่มีหลักฐานความสัมพันธ์ระหว่างรายวิชาที่บันทึกไว้ในผลที่ดึงจาก SQLite; คำอธิบายหรือยอดรวมหลักสูตรเพียงอย่างเดียวไม่ยืนยันความสัมพันธ์

HTTP 200; end-to-end 892.28 ms.

SQL จริง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0) LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 38,
    "printed_page_number": 33
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "printed_page_number": 36
  },
  {
    "code": "06016417",
    "name_th": "เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์",
    "name_en": "SOFTWARE DEVELOPMENT TOOLS AND ENVIRONMENTS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "printed_page_number": 37
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 LIMIT 100",
    "row_count": 3,
    "error": null,
    "repair_attempts": [],
    "citation_queries": [
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=38 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=38 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=38 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=41 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=41 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=41 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=42 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=42 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=42 LIMIT 100",
        "rows": []
      }
    ]
  },
  {
    "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(name_en), LOWER('ข้อมูลที่บันทึกไว้')) > 0 OR INSTR(LOWER(description_th), LOWER('ข้อมูลที่บันทึกไว้')) > 0) LIMIT 100",
    "row_count": 0,
    "error": null,
    "repair_attempts": [],
    "citation_queries": []
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, 33), ('IT.pdf', 41, 36), ('IT.pdf', 42, 37)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายความสัมพันธ์ระหว่างการพัฒนาซอฟต์แวร์กับระบบคอมพิวเตอร์ โดยอ้างเฉพาะข้อมูลที่บันทึกไว้

คำตอบก่อนแก้:

not recorded

ก่อนแก้ HTTP 422; 4503.41 ms. อ้างอิง [ผลเดิม](results/it_metadata_timeout_20261009/fallback-45s/result.json).

SQL และแถวก่อนแก้:

```json
{
  "sql": null,
  "rows": null,
  "detail": null
}
```

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ไม่มีหลักฐานความสัมพันธ์ระหว่างรายวิชาที่บันทึกไว้ในผลที่ดึงจาก SQLite; คำอธิบายหรือยอดรวมหลักสูตรเพียงอย่างเดียวไม่ยืนยันความสัมพันธ์

HTTP 200; end-to-end 1080.52 ms.

SQL จริง:

```sql
SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0) LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 38,
    "printed_page_number": 33
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "printed_page_number": 36
  },
  {
    "code": "06016417",
    "name_th": "เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์",
    "name_en": "SOFTWARE DEVELOPMENT TOOLS AND ENVIRONMENTS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "printed_page_number": 37
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100",
    "row_count": 3,
    "error": null,
    "repair_attempts": [],
    "citation_queries": [
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=38 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          },
          {
            "source_file": "IT.pdf",
            "page_number": 38,
            "printed_page_number": 33
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=38 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=38 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=41 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          },
          {
            "source_file": "IT.pdf",
            "page_number": 41,
            "printed_page_number": 36
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=41 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=41 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=42 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          },
          {
            "source_file": "IT.pdf",
            "page_number": 42,
            "printed_page_number": 37
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=42 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=42 LIMIT 100",
        "rows": []
      }
    ]
  },
  {
    "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0) LIMIT 100",
    "row_count": 0,
    "error": null,
    "repair_attempts": [],
    "citation_queries": []
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, 33), ('IT.pdf', 41, 36), ('IT.pdf', 42, 37)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

### ชุด `ambiguous`

[ผลดิบ](results/fallback_relevance_20261009/ambiguous/result.json)

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาโครงงาน

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้ — รายวิชาที่พบ: 06016406 โครงงาน 1; 06016407 โครงงาน 2 โปรดระบุว่าต้องการรายวิชาใด; การเลือกชื่อให้ชัดยังไม่ทดแทนคำอธิบายที่ขาดในฐานข้อมูล

HTTP 200; end-to-end 1030.56 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016406",
    "name_th": "โครงงาน 1",
    "name_en": "PROJECT 1",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 43,
    "printed_page_number": 38
  },
  {
    "code": "06016407",
    "name_th": "โครงงาน 2",
    "name_en": "PROJECT 2",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 44,
    "printed_page_number": 39
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": [
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": []
      }
    ]
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 43, 38), ('IT.pdf', 44, 39)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาโครงงาน

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้ — รายวิชาที่พบ: 06016406 โครงงาน 1; 06016407 โครงงาน 2 โปรดระบุว่าต้องการรายวิชาใด; การเลือกชื่อให้ชัดยังไม่ทดแทนคำอธิบายที่ขาดในฐานข้อมูล

HTTP 200; end-to-end 1183.26 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016406",
    "name_th": "โครงงาน 1",
    "name_en": "PROJECT 1",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 43,
    "printed_page_number": 38
  },
  {
    "code": "06016407",
    "name_th": "โครงงาน 2",
    "name_en": "PROJECT 2",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 44,
    "printed_page_number": 39
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('โครงงาน')) > 0 OR INSTR(LOWER(name_en), LOWER('โครงงาน')) > 0 OR INSTR(LOWER(description_th), LOWER('โครงงาน')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": [
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          },
          {
            "source_file": "IT.pdf",
            "page_number": 43,
            "printed_page_number": 38
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=43 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM plan_item WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": [
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          },
          {
            "source_file": "IT.pdf",
            "page_number": 44,
            "printed_page_number": 39
          }
        ]
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM course_prerequisite_evidence WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": []
      },
      {
        "sql": "SELECT source_file, page_number, printed_page_number FROM program_requirement WHERE source_file='IT.pdf' AND page_number=44 LIMIT 100",
        "rows": []
      }
    ]
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 43, 38), ('IT.pdf', 44, 39)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

### ชุด `mutation-final-A`

[ผลดิบ](results/fallback_relevance_20261009/mutation-final-A/result.json)

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาระบบคอมพิวเตอร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

IT-2565-coop — คำอธิบายรายวิชา: ISOLATED_EVIDENCE_A — รายวิชาที่ดึงมาแต่ไม่มีคำอธิบายใน SQLite: 06016412

HTTP 200; end-to-end 2590.60 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": "ISOLATED_EVIDENCE_A",
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: เป็น synthetic provenance probe ใน DB สำเนา ไม่ใช่ curriculum fact. ตรวจว่า marker A/B เปลี่ยนตาม DB จริงและระบุ description ที่ขาด; ไม่อ้าง completeness หรือ book-supported accuracy ของ marker.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาระบบคอมพิวเตอร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

IT-2565-coop — คำอธิบายรายวิชา: ISOLATED_EVIDENCE_A — รายวิชาที่ดึงมาแต่ไม่มีคำอธิบายใน SQLite: 06016412

HTTP 200; end-to-end 2659.17 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": "ISOLATED_EVIDENCE_A",
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: เป็น synthetic provenance probe ใน DB สำเนา ไม่ใช่ curriculum fact. ตรวจว่า marker A/B เปลี่ยนตาม DB จริงและระบุ description ที่ขาด; ไม่อ้าง completeness หรือ book-supported accuracy ของ marker.

### ชุด `mutation-final-B`

[ผลดิบ](results/fallback_relevance_20261009/mutation-final-B/result.json)

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาระบบคอมพิวเตอร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

IT-2565-coop — คำอธิบายรายวิชา: ISOLATED_EVIDENCE_B — รายวิชาที่ดึงมาแต่ไม่มีคำอธิบายใน SQLite: 06016412

HTTP 200; end-to-end 2163.43 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": "ISOLATED_EVIDENCE_B",
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: เป็น synthetic provenance probe ใน DB สำเนา ไม่ใช่ curriculum fact. ตรวจว่า marker A/B เปลี่ยนตาม DB จริงและระบุ description ที่ขาด; ไม่อ้าง completeness หรือ book-supported accuracy ของ marker.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาระบบคอมพิวเตอร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

IT-2565-coop — คำอธิบายรายวิชา: ISOLATED_EVIDENCE_B — รายวิชาที่ดึงมาแต่ไม่มีคำอธิบายใน SQLite: 06016412

HTTP 200; end-to-end 2473.41 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": "ISOLATED_EVIDENCE_B",
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: เป็น synthetic provenance probe ใน DB สำเนา ไม่ใช่ curriculum fact. ตรวจว่า marker A/B เปลี่ยนตาม DB จริงและระบุ description ที่ขาด; ไม่อ้าง completeness หรือ book-supported accuracy ของ marker.

### ชุด `removal-final`

[ผลดิบ](results/fallback_relevance_20261009/removal-final/result.json)

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาระบบคอมพิวเตอร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้

HTTP 200; end-to-end 1371.22 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาระบบคอมพิวเตอร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้

HTTP 200; end-to-end 1233.88 ms.

SQL จริง:

```sql
SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "code": "06016411",
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 38
  },
  {
    "code": "06016412",
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "description_th": null,
    "source_file": "IT.pdf",
    "page_number": 41
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 LIMIT 100",
    "row_count": 2,
    "error": null,
    "repair_attempts": [],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, None), ('IT.pdf', 41, None)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

### ชุด `retrieval-failure`

[ผลดิบ](results/fallback_relevance_20261009/retrieval-failure/result.json)

#### `/api/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาระบบคอมพิวเตอร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2565-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้

HTTP 200; end-to-end 12126.67 ms.

SQL จริง:

```sql
SELECT v_study_plan.name_th, v_study_plan.name_en, v_study_plan.code, v_study_plan.credits, v_study_plan.alt_group, v_study_plan.category, v_study_plan.ctype, v_study_plan.note, v_study_plan.source_file, v_study_plan.page_number, v_study_plan.credits_raw, v_study_plan.printed_page_number FROM v_study_plan LIMIT 100
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[
  {
    "name_th": "คณิตศาสตร์สำหรับเทคโนโลยีสารสนเทศ",
    "name_en": "MATHEMATICS FOR INFORMATION TECHNOLOGY",
    "code": "06016401",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 38,
    "credits_raw": null,
    "printed_page_number": 33
  },
  {
    "name_th": "พื้นฐานทางด้านเทคโนโลยีสารสนเทศ",
    "name_en": "INFORMATION TECHNOLOGY FUNDAMENTALS",
    "code": "06016402",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 38,
    "credits_raw": null,
    "printed_page_number": 33
  },
  {
    "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
    "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
    "code": "06016411",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 38,
    "credits_raw": null,
    "printed_page_number": 33
  },
  {
    "name_th": "การแก้ปัญหาและการโปรแกรมคอมพิวเตอร์",
    "name_en": "PROBLEM SOLVING AND COMPUTER PROGRAMMING",
    "code": "06066303",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 38,
    "credits_raw": null,
    "printed_page_number": 33
  },
  {
    "name_th": "โรงเรียนสร้างเสน่ห์",
    "name_en": "CHARM SCHOOL",
    "code": "90641001",
    "credits": 2,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 38,
    "credits_raw": null,
    "printed_page_number": 33
  },
  {
    "name_th": "กีฬาและนันทนาการ",
    "name_en": "SPORTS AND RECREATIONAL ACTIVITIES",
    "code": "90641003",
    "credits": 1,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 38,
    "credits_raw": null,
    "printed_page_number": 33
  },
  {
    "name_th": "ภาษาอังกฤษพื้นฐาน 1",
    "name_en": "FOUNDATION ENGLISH 1",
    "code": "90644007",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 38,
    "credits_raw": null,
    "printed_page_number": 33
  },
  {
    "name_th": "การสร้างโปรแกรมเชิงวัตถุ",
    "name_en": "OBJECT-ORIENTED PROGRAMMING",
    "code": "06016408",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 39,
    "credits_raw": null,
    "printed_page_number": 34
  },
  {
    "name_th": "ความน่าจะเป็นและสถิติ",
    "name_en": "PROBABILITY AND STATISTICS",
    "code": "06066001",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 39,
    "credits_raw": null,
    "printed_page_number": 34
  },
  {
    "name_th": "พื้นฐานทางธุรกิจสำหรับเทคโนโลยีสารสนเทศ",
    "name_en": "BUSINESS FUNDAMENTALS FOR INFORMATION TECHNOLOGY",
    "code": "06066101",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 39,
    "credits_raw": null,
    "printed_page_number": 34
  },
  {
    "name_th": "โครงสร้างข้อมูลและอัลกอริทึม",
    "name_en": "DATA STRUCTURES AND ALGORITHMS",
    "code": "06066301",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 39,
    "credits_raw": null,
    "printed_page_number": 34
  },
  {
    "name_th": "ความฉลาดทางดิจิทัล",
    "name_en": "DIGITAL INTELLIGENCE QUOTIENT",
    "code": "90641002",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 39,
    "credits_raw": null,
    "printed_page_number": 34
  },
  {
    "name_th": "ภาษาอังกฤษพื้นฐาน 2",
    "name_en": "FOUNDATION ENGLISH 2",
    "code": "90644008",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 39,
    "credits_raw": null,
    "printed_page_number": 34
  },
  {
    "name_th": "เทคโนโลยีสื่อประสม",
    "name_en": "MULTIMEDIA TECHNOLOGY",
    "code": "06016403",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 40,
    "credits_raw": null,
    "printed_page_number": 35
  },
  {
    "name_th": "การประมวลผลทางกายภาพ",
    "name_en": "PHYSICAL COMPUTING",
    "code": "06016409",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 40,
    "credits_raw": null,
    "printed_page_number": 35
  },
  {
    "name_th": "ระบบเครือข่ายเบื้องต้น",
    "name_en": "INTRODUCTION TO NETWORK SYSTEMS",
    "code": "06016413",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 40,
    "credits_raw": null,
    "printed_page_number": 35
  },
  {
    "name_th": "คณิตศาสตร์ไม่ต่อเนื่อง",
    "name_en": "DISCRETE MATHEMATICS",
    "code": "06066000",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 40,
    "credits_raw": null,
    "printed_page_number": 35
  },
  {
    "name_th": "แนวคิดระบบฐานข้อมูล",
    "name_en": "DATABASE SYSTEM CONCEPTS",
    "code": "06066300",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 40,
    "credits_raw": null,
    "printed_page_number": 35
  },
  {
    "name_th": "การวิเคราะห์และออกแบบระบบสารสนเทศ",
    "name_en": "INFORMATION SYSTEM ANALYSIS AND DESIGN",
    "code": "06066304",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 40,
    "credits_raw": null,
    "printed_page_number": 35
  },
  {
    "name_th": "พื้นฐานความมั่นคงปลอดภัยไซเบอร์",
    "name_en": "CYBERSECURITY FUNDAMENTALS",
    "code": "06016405",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 36
  },
  {
    "name_th": "วิศวกรรมซอฟต์แวร์",
    "name_en": "SOFTWARE ENGINEERING",
    "code": "06016410",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 36
  },
  {
    "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
    "name_en": "COMPUTER ORGANIZATION AND OPERATING SYSTEM",
    "code": "06016412",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 36
  },
  {
    "name_th": "การเขียนโปรแกรมเว็บพื้นฐาน",
    "name_en": "FUNDAMENTAL WEB PROGRAMMING",
    "code": "06066302",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 36
  },
  {
    "name_th": "ระบบฐานข้อมูลแบบโนเอสคิวแอล",
    "name_en": "NOSQL DATABASE SYSTEMS",
    "code": "06016414",
    "credits": 3,
    "alt_group": "it-specialization-y2s2-slot-1",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 36
  },
  {
    "name_th": "การเขียนโปรแกรมเชิงฟังก์ชัน",
    "name_en": "FUNCTIONAL PROGRAMMING",
    "code": "06016415",
    "credits": 3,
    "alt_group": "it-specialization-y2s2-slot-2",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 36
  },
  {
    "name_th": "โครงสร้างพื้นฐานเครือข่ายการสื่อสาร",
    "name_en": "COMMUNICATION NETWORK INFRASTRUCTURE",
    "code": "06016419",
    "credits": 3,
    "alt_group": "it-specialization-y2s2-slot-1",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 36
  },
  {
    "name_th": "ระบบโครงสร้างพื้นฐานและการบริการ",
    "name_en": "INFRASTRUCTURE SYSTEMS AND SERVICES",
    "code": "06016420",
    "credits": 3,
    "alt_group": "it-specialization-y2s2-slot-2",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 36
  },
  {
    "name_th": "การออกแบบส่วนต่อประสานกับมนุษย์",
    "name_en": "HUMAN INTERFACE DESIGN",
    "code": "06016424",
    "credits": 3,
    "alt_group": "it-specialization-y2s2-slot-1",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 36
  },
  {
    "name_th": "พื้นฐานการออกแบบทัศนศิลป์สำหรับสื่อปฏิสัมพันธ์",
    "name_en": "VISUAL DESIGN FUNDAMENTALS FOR INTERACTIVE MEDIA",
    "code": "06016425",
    "credits": 3,
    "alt_group": "it-specialization-y2s2-slot-2",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 41,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 36
  },
  {
    "name_th": "เทคโนโลยีกลุ่มเมฆ",
    "name_en": "CLOUD COMPUTING",
    "code": "06016404",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 37
  },
  {
    "name_th": "ระบบสารสนเทศเพื่อการจัดการ",
    "name_en": "MANAGEMENT INFORMATION SYSTEMS",
    "code": "06066102",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 37
  },
  {
    "name_th": "วิชาเลือกหมวดภาษาและการสื่อสาร",
    "name_en": null,
    "code": "ELEC-90644XXX-TERM-3-1-ROW-1",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 37
  },
  {
    "name_th": "วิศวกรรมความต้องการ",
    "name_en": "REQUIREMENT ENGINEERING",
    "code": "06016416",
    "credits": 3,
    "alt_group": "it-specialization-y3s1-slot-1",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 37
  },
  {
    "name_th": "เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์",
    "name_en": "SOFTWARE DEVELOPMENT TOOLS AND ENVIRONMENTS",
    "code": "06016417",
    "credits": 3,
    "alt_group": "it-specialization-y3s1-slot-2",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 37
  },
  {
    "name_th": "การพัฒนาเว็บฝั่งเซิร์ฟเวอร์",
    "name_en": "SERVER-SIDE WEB DEVELOPMENT",
    "code": "06016418",
    "credits": 3,
    "alt_group": "it-specialization-y3s1-slot-3",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 37
  },
  {
    "name_th": "ความมั่นคงปลอดภัยโครงสร้างพื้นฐานทางเทคโนโลยีสารสนเทศ",
    "name_en": "INFORMATION TECHNOLOGY INFRASTRUCTURE SECURITY",
    "code": "06016421",
    "credits": 3,
    "alt_group": "it-specialization-y3s1-slot-1",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 37
  },
  {
    "name_th": "อินเทอร์เน็ตของสรรพสิ่ง",
    "name_en": "INTERNET OF THINGS",
    "code": "06016422",
    "credits": 3,
    "alt_group": "it-specialization-y3s1-slot-2",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 37
  },
  {
    "name_th": "การออโตเมชันและโครงสร้างพื้นฐานที่สามารถโปรแกรมได้",
    "name_en": "INFRASTRUCTURE PROGRAMMABILITY AND AUTOMATION",
    "code": "06016423",
    "credits": 3,
    "alt_group": "it-specialization-y3s1-slot-3",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 37
  },
  {
    "name_th": "คอมพิวเตอร์กราฟิกส์และแอนิเมชัน",
    "name_en": "COMPUTER GRAPHICS AND ANIMATION",
    "code": "06016426",
    "credits": 3,
    "alt_group": "it-specialization-y3s1-slot-1",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 37
  },
  {
    "name_th": "การออกแบบและพัฒนาเกมเบื้องต้น",
    "name_en": "INTRODUCTION TO GAME DESIGN AND DEVELOPMENT",
    "code": "06016427",
    "credits": 3,
    "alt_group": "it-specialization-y3s1-slot-2",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 42,
    "credits_raw": "3(2-2-5)",
    "printed_page_number": 37
  },
  {
    "name_th": "สหกิจศึกษา",
    "name_en": "COOPERATIVE EDUCATION",
    "code": "06016481",
    "credits": 6,
    "alt_group": "coop-alternative-IT.pdf-43",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 43,
    "credits_raw": null,
    "printed_page_number": 38
  },
  {
    "name_th": "สหกิจศึกษาต่างประเทศ",
    "name_en": "OVERSEA COOPERATIVE EDUCATION",
    "code": "06016482",
    "credits": 6,
    "alt_group": "coop-alternative-IT.pdf-43",
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 43,
    "credits_raw": null,
    "printed_page_number": 38
  },
  {
    "name_th": "โครงงาน 1",
    "name_en": "PROJECT 1",
    "code": "06016406",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 43,
    "credits_raw": "3(0-9-0)",
    "printed_page_number": 38
  },
  {
    "name_th": "วิชาเลือกทางเทคโนโลยีสารสนเทศ 1",
    "name_en": "ELECTIVE COURSE IN INFORMATION TECHNOLOGY 1",
    "code": "ELEC-060164XX-SLOT-1",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 43,
    "credits_raw": "3(3-0-6) หรือ 3(2-2-5) หรือ 3(0-6-3)",
    "printed_page_number": 38
  },
  {
    "name_th": "ผู้ประกอบการสมัยใหม่",
    "name_en": "MODERN ENTREPRENEURS",
    "code": "90643021",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 43,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 38
  },
  {
    "name_th": "วิชาเลือกเสรี 1",
    "name_en": "FREE ELECTIVE COURSE 1",
    "code": "ELEC-SLOT-045",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเลือกเสรี",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 43,
    "credits_raw": "3(x-x-x)",
    "printed_page_number": 38
  },
  {
    "name_th": "โครงงาน 2",
    "name_en": "PROJECT 2",
    "code": "06016407",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 44,
    "credits_raw": "3(0-9-0)",
    "printed_page_number": 39
  },
  {
    "name_th": "การบริหารโครงการเทคโนโลยีสารสนเทศ",
    "name_en": "INFORMATION TECHNOLOGY PROJECT MANAGEMENT",
    "code": "06066100",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเฉพาะ",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 44,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 39
  },
  {
    "name_th": "กฎหมายสำหรับคนรุ่นใหม่",
    "name_en": "LAW FOR NEW GENERATION",
    "code": "90642033",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "บังคับ",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 44,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 39
  },
  {
    "name_th": "วิชาเลือกหมวดวิชาศึกษาทั่วไป 2",
    "name_en": "ELECTIVE COURSE IN GENERAL EDUCATION 2",
    "code": "ELEC-9064XXXX-SLOT-2",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "เลือก",
    "note": null,
    "source_file": "IT.pdf",
    "page_number": 44,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 39
  },
  {
    "name_th": "วิชาเลือกหมวดวิชาศึกษาทั่วไป 1",
    "name_en": "ELECTIVE COURSE IN GENERAL EDUCATION 1",
    "code": "ELEC-RECOVERED-Y4S1-1",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "เลือก",
    "note": "แถวที่ยืนยันจากภาพตารางต้นฉบับ",
    "source_file": "IT.pdf",
    "page_number": 43,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 38
  },
  {
    "name_th": "วิชาเลือกเสรี 2",
    "name_en": "FREE ELECTIVE COURSE 2",
    "code": "ELEC-RECOVERED-Y4S1-2",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาเลือกเสรี",
    "ctype": "เลือก",
    "note": "แถวที่ยืนยันจากภาพตารางต้นฉบับ",
    "source_file": "IT.pdf",
    "page_number": 43,
    "credits_raw": "3(x-x-x)",
    "printed_page_number": 38
  },
  {
    "name_th": "การสื่อสารและการนำเสนออย่างมืออาชีพ",
    "name_en": "PROFESSIONAL COMMUNICATION AND PRESENTATION",
    "code": "90644042",
    "credits": 3,
    "alt_group": null,
    "category": "หมวดวิชาศึกษาทั่วไป",
    "ctype": "บังคับ",
    "note": "แถวที่ยืนยันจากภาพตารางต้นฉบับ",
    "source_file": "IT.pdf",
    "page_number": 44,
    "credits_raw": "3(3-0-6)",
    "printed_page_number": 39
  }
]
```

รายละเอียด query ที่ execute จริง:

```json
[
  {
    "sql": "SELECT v_study_plan.name_th, v_study_plan.name_en, v_study_plan.code, v_study_plan.credits, v_study_plan.alt_group, v_study_plan.category, v_study_plan.ctype, v_study_plan.note, v_study_plan.source_file, v_study_plan.page_number, v_study_plan.credits_raw, v_study_plan.printed_page_number FROM v_study_plan LIMIT 100",
    "row_count": 53,
    "error": null,
    "repair_attempts": [
      {
        "sql": "SELECT v_study_plan.name_th, v_study_plan.name_en, v_study_plan.code, v_study_plan.credits, v_study_plan.alt_group, v_study_plan.category, v_study_plan.ctype, v_study_plan.note, v_study_plan.source_file, v_study_plan.page_number, v_study_plan.credits_raw, v_study_plan.printed_page_number FROM v_study_plan WHERE v_study_plan.program_id = 'IT-2565-coop'",
        "error": "SQL added a filter value not present in the question: 'IT-2565-coop'"
      }
    ],
    "citation_queries": null
  }
]
```

PDF / หน้าในเล่มจากผลดิบ: [('IT.pdf', 38, 33), ('IT.pdf', 38, 33), ('IT.pdf', 38, 33), ('IT.pdf', 38, 33), ('IT.pdf', 38, 33), ('IT.pdf', 38, 33), ('IT.pdf', 38, 33), ('IT.pdf', 39, 34), ('IT.pdf', 39, 34), ('IT.pdf', 39, 34), ('IT.pdf', 39, 34), ('IT.pdf', 39, 34), ('IT.pdf', 39, 34), ('IT.pdf', 40, 35), ('IT.pdf', 40, 35), ('IT.pdf', 40, 35), ('IT.pdf', 40, 35), ('IT.pdf', 40, 35), ('IT.pdf', 40, 35), ('IT.pdf', 41, 36), ('IT.pdf', 41, 36), ('IT.pdf', 41, 36), ('IT.pdf', 41, 36), ('IT.pdf', 41, 36), ('IT.pdf', 41, 36), ('IT.pdf', 41, 36), ('IT.pdf', 41, 36), ('IT.pdf', 41, 36), ('IT.pdf', 41, 36), ('IT.pdf', 42, 37), ('IT.pdf', 42, 37), ('IT.pdf', 42, 37), ('IT.pdf', 42, 37), ('IT.pdf', 42, 37), ('IT.pdf', 42, 37), ('IT.pdf', 42, 37), ('IT.pdf', 42, 37), ('IT.pdf', 42, 37), ('IT.pdf', 42, 37), ('IT.pdf', 42, 37), ('IT.pdf', 43, 38), ('IT.pdf', 43, 38), ('IT.pdf', 43, 38), ('IT.pdf', 43, 38), ('IT.pdf', 43, 38), ('IT.pdf', 43, 38), ('IT.pdf', 44, 39), ('IT.pdf', 44, 39), ('IT.pdf', 44, 39), ('IT.pdf', 44, 39), ('IT.pdf', 43, 38), ('IT.pdf', 43, 38), ('IT.pdf', 44, 39)]

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.

#### `/ask` — IT / พ.ศ. 2565 / สหกิจศึกษา

คำถามจริง:

หลักสูตร IT 2565 สหกิจ อธิบายเนื้อหาระบบคอมพิวเตอร์

คำตอบก่อนแก้:

not recorded

คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):

not recorded

HTTP 422; end-to-end 7716.48 ms.

SQL จริง:

```sql
not recorded
```

แถวหลักฐานจริง (ไม่รวม metadata ของ process):

```json
[]
```

รายละเอียด query ที่ execute จริง:

```json
[]
```

PDF / หน้าในเล่มจากผลดิบ: n/a; ไม่มีหลักฐานรายวิชาที่ดึงมา

หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.

การประเมิน: request ล้มเหลว ไม่ใช่คำตอบสำเร็จ; ไม่มี unsupported factual answer แต่ recovery/error handling ยังต้องตรวจเพิ่ม.

## เวลาและจำนวนตัวอย่าง

release-cases: n=8; substantive successes=0, abstentions=8, HTTP failures=0, timeouts=0; median 951.50 ms. stored-relationship-final มี substantive DB-backed answer2requestsแต่ printed folioยังขาด. ไม่รายงาน reliable p95 หรือ general accuracy. ไม่มี forced cold-load และไม่ได้ยืนยัน warm residency ทุก request; cold/warm แยกอย่างน่าเชื่อถือยัง n/a.

## การแยกฉบับเก่าใน LIVE

[ผลดิบ](results/fallback_relevance_20261009/live-old-paired.json)

### `/api/ask` — IT / พ.ศ. 2560 / สหกิจศึกษา

หลักสูตร IT 2560 สหกิจ อธิบายความสัมพันธ์ระหว่างระบบคอมพิวเตอร์กับการพัฒนาซอฟต์แวร์

ก่อนแก้: not recorded

คำตอบจริง:

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2560-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ไม่มีหลักฐานความสัมพันธ์ระหว่างรายวิชาที่บันทึกไว้ในผลที่ดึงจาก SQLite; คำอธิบายหรือยอดรวมหลักสูตรเพียงอย่างเดียวไม่ยืนยันความสัมพันธ์

HTTP 200; 1647.89 ms.

SQL/rows/sources จริงจาก response (key ที่ไม่มีคือ not recorded):

```json
{
  "sql": "SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code AND p.source_file=e.source_file AND p.page_number=e.page_number WHERE p.code IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0) AND p.requires IN (SELECT code FROM course WHERE INSTR(LOWER(name_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_en), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(description_th), LOWER('ระบบคอมพิวเตอร์')) > 0 OR INSTR(LOWER(name_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(name_en), LOWER('การพัฒนาซอฟต์แวร์')) > 0 OR INSTR(LOWER(description_th), LOWER('การพัฒนาซอฟต์แวร์')) > 0) LIMIT 100",
  "rows": [
    {
      "code": "06016319",
      "name_th": "ระบบคอมพิวเตอร์เบื้องต้น",
      "name_en": "INTRODUCTION TO COMPUTER SYSTEMS",
      "description_th": null,
      "source_file": "IT-60.pdf",
      "page_number": 34,
      "_source": {
        "database_path": "C:\\Users\\thana\\OneDrive\\เอกสาร\\ocr_final\\work\\lab8b_it_2560_coop\\curriculum.db",
        "database_name": "lab8b_it_2560_coop",
        "curriculum_name": "IT-2560-coop",
        "program_id": "IT-coop",
        "curriculum_version": 2560,
        "plan": "coop",
        "source_folder": "work/lab8b_it_2560_coop"
      },
      "printed_page_number": 29
    },
    {
      "code": "06016320",
      "name_th": "โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
      "name_en": "COMPUTER SYSTEMS ORGANIZATION AND OPERATING SYSTEM",
      "description_th": null,
      "source_file": "IT-60.pdf",
      "page_number": 35,
      "_source": {
        "database_path": "C:\\Users\\thana\\OneDrive\\เอกสาร\\ocr_final\\work\\lab8b_it_2560_coop\\curriculum.db",
        "database_name": "lab8b_it_2560_coop",
        "curriculum_name": "IT-2560-coop",
        "program_id": "IT-coop",
        "curriculum_version": 2560,
        "plan": "coop",
        "source_folder": "work/lab8b_it_2560_coop"
      },
      "printed_page_number": 30
    },
    {
      "code": "06016328",
      "name_th": "เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์",
      "name_en": "SOFTWARE DEVELOPMENT TOOLS AND ENVIRONMENTS",
      "description_th": null,
      "source_file": "IT-60.pdf",
      "page_number": 38,
      "_source": {
        "database_path": "C:\\Users\\thana\\OneDrive\\เอกสาร\\ocr_final\\work\\lab8b_it_2560_coop\\curriculum.db",
        "database_name": "lab8b_it_2560_coop",
        "curriculum_name": "IT-2560-coop",
        "program_id": "IT-coop",
        "curriculum_version": 2560,
        "plan": "coop",
        "source_folder": "work/lab8b_it_2560_coop"
      },
      "printed_page_number": 33
    }
  ],
  "sources": "not recorded",
  "selected_curricula": [
    "IT-2560-coop"
  ]
}
```

เป็น scoped abstention; APIเลือก IT-2560-coop และ frontend sources เป็น IT-60.pdf/2560 เท่านั้น. คู่ PDF/printed page อยู่ในผลดิบด้านบน มาจาก selected SQLite ไม่เดา offset. ไม่ได้ตรวจ completeness/source correctness ทุกแถวใหม่จาก book.

### `/ask` — IT / พ.ศ. 2560 / สหกิจศึกษา

หลักสูตร IT 2560 สหกิจ อธิบายความสัมพันธ์ระหว่างระบบคอมพิวเตอร์กับการพัฒนาซอฟต์แวร์

ก่อนแก้: not recorded

คำตอบจริง:

หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน IT-2560-coop จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก — ไม่มีหลักฐานความสัมพันธ์ระหว่างรายวิชาที่บันทึกไว้ในผลที่ดึงจาก SQLite; คำอธิบายหรือยอดรวมหลักสูตรเพียงอย่างเดียวไม่ยืนยันความสัมพันธ์

HTTP 200; 518.49 ms.

SQL/rows/sources จริงจาก response (key ที่ไม่มีคือ not recorded):

```json
{
  "sql": "not recorded",
  "rows": "not recorded",
  "sources": [
    {
      "page": 34,
      "book_page": 29,
      "section": "IT-60.pdf · พ.ศ. 2560 · แผนสหกิจศึกษา · ระบบคอมพิวเตอร์เบื้องต้น",
      "quote": "06016319 ระบบคอมพิวเตอร์เบื้องต้น"
    },
    {
      "page": 35,
      "book_page": 30,
      "section": "IT-60.pdf · พ.ศ. 2560 · แผนสหกิจศึกษา · โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ",
      "quote": "06016320 โครงสร้างระบบคอมพิวเตอร์และระบบปฏิบัติการ"
    },
    {
      "page": 38,
      "book_page": 33,
      "section": "IT-60.pdf · พ.ศ. 2560 · แผนสหกิจศึกษา · เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์",
      "quote": "06016328 เครื่องมือและสภาพแวดล้อมสำหรับการพัฒนาซอฟต์แวร์"
    }
  ],
  "selected_curricula": "not recorded"
}
```

เป็น scoped abstention; APIเลือก IT-2560-coop และ frontend sources เป็น IT-60.pdf/2560 เท่านั้น. คู่ PDF/printed page อยู่ในผลดิบด้านบน มาจาก selected SQLite ไม่เดา offset. ไม่ได้ตรวจ completeness/source correctness ทุกแถวใหม่จาก book.

## หลังแก้การดึง paired citation metadata

[ผลดิบ LIVE ทั้งสองroutes](results/fallback_relevance_20261009/live-old-paired.json)

ดึงคู่หน้าจาก selected SQLite เท่านั้น มี raw citation_queries ไม่ใช้ global-profile lookup หรือ offset. source-viewer ที่เปิดจาก actual citationclick แสดง IT-60.pdf PDF34/book29 และเห็นรายวิชา06016319บนภาพ. [ภาพ](results/fallback_relevance_20261009/live-citation.png) / [DOM](results/fallback_relevance_20261009/live-citation.txt).

citation-pairs: DB-backed pairs IT2565 PDF38/book33,41/36,42/37 และ Project1 PDF43/book38,Project2 PDF44/book39. Edge PDF326 ไม่มี paired folioใน selectedDB จึงยัง n/a; ไม่อ้างว่า book-verified ใหม่จากการ lookup. Ambiguous content case แสดง candidate โครงงาน1/2และขอเลือก พร้อมบอกว่า descriptionsยังขาด.

## ตรวจ supporting source แยกจากข้อมูลที่ใช้ตอบ

ตรวจ rendered IT.pdf PDF326 / หน้าในเล่ม325 โดยอ่าน folioจากภาพ ไม่คำนวณoffset. เห็นข้อความวิชาบังคับก่อนของโครงงาน2เป็นโครงงาน1 ยืนยัน substantive edge ที่อยู่ในSQLiteด้วย source image. [ภาพจริง](results/fallback_relevance_20261009/IT-326-viewer.png) / [บันทึก](results/fallback_relevance_20261009/source-check.json).

การตรวจภาพนี้ไม่เติม facts หรือ folioเข้าAPI ไม่เพิ่ม schema ไม่แก้ DB. หน้าในเล่มของ edge ยัง NULL ใน selectedSQLite จึง UIยังบอกว่ายังไม่ยืนยัน แม้รายงานนี้ตรวจfoliovisuallyแล้ว. Reviewนี้เป็น development evidence ไม่ใช่ production approval/held-out label.

## หลักฐาน UI และผลที่ยังเปิด

[UI clarification ล่าสุด](results/fallback_relevance_20261009/live-ambiguous-ui.png) / [DOM](results/fallback_relevance_20261009/live-ambiguous-ui.txt): actual LIVE คำถามโครงงานที่กำกวม แสดง06016406/06016407 ขอระบุรายวิชา และบอกว่า descriptionsยังขาด; PDF43/book38 และ44/book39. รอบนี้ server6054ms/end-to-end6064ms เป็น scoped abstention ไม่ผ่าน5s แม้ HTTP200. จึงไม่อ้าง reliable latency SLA จากชุดเร็วกว่าเดิม.

[UI คู่หน้าเก่า](results/fallback_relevance_20261009/live-old-paired-ui.png) / [DOM](results/fallback_relevance_20261009/live-old-paired-ui.txt): PDF34/book29,35/30,38/33 จาก selected IT-2560-coop SQLite; viewerเปิดจริงและเห็นภาพ. ไม่มี2565sourcesในตัวอย่างนี้.

[ภาพ UI isolated](results/fallback_relevance_20261009/ui-current.png) และ [DOM](results/fallback_relevance_20261009/ui-current.txt): IT/latest, loading→insufficient-evidence, citation3แหล่ง; server3890ms/end-to-end3914ms ตาม UI. ต่อมา restart verified LIVE backendด้วย stop_web/start_web; ไม่หยุด Ollama ไม่แก้ DB. หลักฐาน LIVE ใหม่แยกเป็น live-relationship-ui.png/txt และ live-gap-ui.png/txt ในโฟลเดอร์ผลเดียวกัน. Printed folios ที่ NULL คงแจ้งว่ายังไม่ยืนยัน. Citation navigation รอบนี้ต้องอ้าง screenshot/DOM ต้นฉบับที่บันทึกจริงเท่านั้น.

คง failed attempts initial/narrow-schema/literal-topics และ mutation-A/B/A2/B2 ไว้ ไม่ลบผลที่ไม่ผ่าน. Mutation A2/B2 เคย abstain แม้มี marker เพราะ model เลือก null row; ไม่ถือเป็น provenance pass.

ข้อจำกัดข้างต้นเป็นสถานะก่อน bounded batch รอบถัดไป. ผลใหม่ทุก14catalogs, ตัวอย่างจริงก่อน/หลัง, SQL/rows, same-process cache/recovery, clean installation และ fresh BIT rebuild อยู่ใน [รายงานรอบต่อเนื่อง](PROFILE_DEVELOPMENT_20261009.md). คง actual outputs และ failed results เดิมไว้ ไม่แก้ย้อนหลังให้ดูเหมือนผ่าน. Untouched held-out, broader source coverage, difficult cold/warm latency และ legacy identityยังไม่ปิด. Unit/schema/frontend/gold/old2560/provenance/version_sets เป็นคนละscope ห้ามบวกเป็น accuracy เดียว
