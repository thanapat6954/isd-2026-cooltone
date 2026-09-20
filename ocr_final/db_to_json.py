import json
import os
import sqlite3
 
# Your `courses` table has no `program_name` column -- the only field that
# tells you which curriculum PDF a row came from is `source_file`, and its
# values are full filenames ("AI.pdf", "IT.pdf", "DSBA.pdf"), not "AIT".
# So instead of `LIKE '%AIT%'` (which would never match "AI.pdf" and would
# silently return 0 rows), map each short program label to its actual
# source_file value explicitly.
PROGRAM_SOURCE_FILES = {
    "AIT": "AI.pdf",
    "DSBA": "DSBA.pdf",
    "IT": "IT.pdf",
}
 
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
 
conn = sqlite3.connect("curriculum.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
 
for prog, source_file in PROGRAM_SOURCE_FILES.items():
    cursor.execute(
        "SELECT * FROM courses WHERE source_file = ?", (source_file,)
    )
    rows = cursor.fetchall()
    course_list = [dict(row) for row in rows]
 
    if not course_list:
        print(f"ไม่พบข้อมูลสำหรับ: {prog}")
        continue
 
    # --- บันทึกไฟล์ที่ 1: output/<PROGRAM>_fields.json ---
    fields_payload = {
        "program_code": prog,
        "total_courses": len(course_list),
        "courses": course_list,
    }
    with open(os.path.join(output_dir, f"{prog}_fields.json"), "w", encoding="utf-8") as f:
        json.dump(fields_payload, f, ensure_ascii=False, indent=4)
 
    # --- บันทึกไฟล์ที่ 2: output/<PROGRAM>_ocr.json ---
    ocr_payload = {"program": prog, "ocr_data": course_list}
    with open(os.path.join(output_dir, f"{prog}_ocr.json"), "w", encoding="utf-8") as f:
        json.dump(ocr_payload, f, ensure_ascii=False, indent=4)
 
    # --- บันทึกไฟล์ที่ 3: output/<PROGRAM>_ocr.txt ---
    # course_name_en falls back to course_name_th when the English field
    # is empty, so rows with only a Thai name still produce a usable line
    # instead of "<code> " with nothing after it.
    text_lines = [
        f"{item.get('course_code') or ''} "
        f"{item.get('course_name_en') or item.get('course_name_th') or ''}".strip()
        for item in course_list
    ]
    with open(os.path.join(output_dir, f"{prog}_ocr.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(text_lines))
 
    print(f"สร้างไฟล์สำหรับ {prog} ลงในโฟลเดอร์ {output_dir} เรียบร้อยแล้ว")
 
conn.close()
