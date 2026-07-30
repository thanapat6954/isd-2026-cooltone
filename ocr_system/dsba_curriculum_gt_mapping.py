"""
Convert DSBA curriculum ground truth JSON (DSBA_academic_plan_coop.json)
to a flat CSV mapping file for evaluation and comparison.

Usage:
    python dsba_curriculum_gt_mapping.py [input_json] [output_csv]

Defaults:
    input  = data/input/DSBA_academic_plan_coop.json
    output = dsba_curriculum_gt_mapping.csv
"""

import csv
import json
import re
import sys
from pathlib import Path


def _normalise_text(text: str | None) -> str:
    """Collapse newlines and extra whitespace into single spaces."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _elective_group(code: str, category: str | None, course_type: str | None, name_th: str | None) -> str:
    """Derive the elective sub-group from code pattern and Thai name."""
    if course_type and course_type.strip() == "บังคับ":
        return "บังคับ (Required)"

    name = name_th or ""

    # Free electives
    if category and "เลือกเสรี" in category:
        return "วิชาเลือกเสรี (Free Elective)"

    # General education electives
    if code.startswith("9064") and "x" in code.lower():
        return "ศึกษาทั่วไปเลือก (GE Elective)"

    # Specific elective groups detected by Thai name
    if "วิทยาการข้อมูล" in name and "เลือก" in name:
        return "เลือกกลุ่มวิทยาการข้อมูล (Data Science Elective)"
    if "การวิเคราะห์เชิงสถิติ" in name and "เลือก" in name:
        return "เลือกกลุ่มการวิเคราะห์เชิงสถิติ (Statistical Analytics Elective)"
    if "วิศวกรรมข้อมูล" in name and "เลือก" in name:
        return "เลือกกลุ่มวิศวกรรมข้อมูล (Data Engineering Elective)"
    if "ภาษาและการสื่อสาร" in name:
        return "เลือกภาษาและการสื่อสาร (Language Elective)"

    # Elective courses listed in the elective pool (year=0, semester=0)
    if course_type and "เลือก" in course_type:
        return "วิชาเลือกเฉพาะ (Major Elective)"

    return ""


def _year_semester_display(year, semester, flexible: str | None) -> str:
    """Build a human-readable year/semester string."""
    y = str(year) if year not in (None, 0, "0") else ""
    s = str(semester) if semester not in (None, 0, "0") else ""

    if y and s:
        display = f"{y}/{s}"
    elif flexible:
        display = f"Flexible: {_normalise_text(flexible)}"
    else:
        display = "Elective Pool"
    return display


def convert_dsba_gt_to_csv(input_path: Path, output_path: Path) -> int:
    """Read the JSON GT and write a flat CSV. Returns number of rows written."""
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    program = data.get("program", "DSBA")
    plan = data.get("plan", "coop")
    source = data.get("source", "")

    fieldnames = [
        "row_number",
        "code",
        "name_th",
        "name_en",
        "credits",
        "year",
        "semester",
        "year_semester_display",
        "category",
        "type",
        "elective_group",
        "prerequisite",
        "flexible_year_semester",
        "note",
        "program",
        "plan",
        "ground_truth_source",
    ]

    rows = []
    row_num = 0
    for course in data.get("courses", []):
        code = str(course.get("code", "")).strip()

        # Skip the trailing note entry that is not a real course
        if not code or code.startswith("หมายเหตุ"):
            continue

        row_num += 1

        name_th = _normalise_text(course.get("name_th"))
        name_en = _normalise_text(course.get("name_en"))
        credits = _normalise_text(course.get("credits"))
        category = _normalise_text(course.get("category"))
        course_type = _normalise_text(course.get("type"))
        prerequisite = _normalise_text(course.get("prerequisite"))
        flexible = _normalise_text(course.get("flexible_year_semester"))
        note = _normalise_text(course.get("note"))

        year = course.get("year")
        semester = course.get("semester")

        rows.append({
            "row_number": row_num,
            "code": code,
            "name_th": name_th,
            "name_en": name_en,
            "credits": credits,
            "year": year if year not in (None, 0, "0") else "",
            "semester": semester if semester not in (None, 0, "0") else "",
            "year_semester_display": _year_semester_display(year, semester, flexible),
            "category": category,
            "type": course_type,
            "elective_group": _elective_group(code, category, course_type, course.get("name_th")),
            "prerequisite": prerequisite,
            "flexible_year_semester": flexible,
            "note": note,
            "program": program,
            "plan": plan,
            "ground_truth_source": source,
        })

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main() -> None:
    # Ensure console can print Thai text on Windows
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    base_dir = Path(__file__).resolve().parent

    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else base_dir / "data" / "input" / "DSBA_academic_plan_coop.json"
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else base_dir / "dsba_curriculum_gt_mapping.csv"

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    count = convert_dsba_gt_to_csv(input_path, output_path)

    print(f"[OK] Converted {count} courses from DSBA GT to CSV")
    print(f"  Input : {input_path}")
    print(f"  Output: {output_path}")

    # Print a quick summary
    with output_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        categories = {}
        types = {}
        for row in reader:
            cat = row["category"] or "(none)"
            typ = row["type"] or "(none)"
            categories[cat] = categories.get(cat, 0) + 1
            types[typ] = types.get(typ, 0) + 1

    print(f"\n  Summary by category:")
    for cat, cnt in sorted(categories.items()):
        print(f"    {cat}: {cnt}")

    print(f"\n  Summary by type:")
    for typ, cnt in sorted(types.items()):
        print(f"    {typ}: {cnt}")


if __name__ == "__main__":
    main()
