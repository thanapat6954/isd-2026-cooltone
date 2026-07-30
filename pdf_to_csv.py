"""
Extract the subject (course) list from the KMITL curriculum PDF
("ภาคผนวก จ - คำอธิบายรายวิชา" / Course Description appendix)
and save it as a CSV file.

Each course entry in the PDF looks like:

    06026200         CALCULUS 1 (Thai name)                    3(3-0-6)
                      CALCULUS 1 (English name)
                      วิชาบังคับกอน : ไมมี
                      PREREQUISITE : None
                      <Thai description ...>
                      <English description ...>

This script pulls out, for every course:
    - course_code      e.g. 06026200
    - name_thai        Thai course title
    - name_english     English course title
    - credit_hours     raw credit string, e.g. 3(3-0-6)
    - credits          the total credit number, e.g. 3
    - lecture_hours / lab_hours / self_study_hours  (parsed from the
      "(L-P-S)" breakdown when present)
    - prerequisite_en  English prerequisite line (or "None")

Usage:
    python pdf_to_csv.py input.pdf output.csv
"""

import csv
import re
import subprocess
import sys


# Matches a course header line, e.g.:
#   06026200         CALCULUS 1                         3(3-0-6)
COURSE_HEADER_RE = re.compile(
    r"^\s*(?P<code>\d{7,8})\s+(?P<name>.+?)\s+(?P<credits>\d+\(\d+-\d+-\d+\))\s*$"
)

# A line that is entirely uppercase Latin letters/punctuation/digits (the
# English name line that follows the Thai header).
ENGLISH_LINE_RE = re.compile(r"^[A-Z0-9 .,\-\(\)/&']+$")

PREREQ_EN_RE = re.compile(r"^\s*PREREQUISITE\s*:\s*(.+)$", re.IGNORECASE)


def extract_text(pdf_path: str) -> str:
    """
    Extract full text from the PDF using poppler's `pdftotext -layout`,
    which preserves the column layout much better than pure-Python
    libraries for this particular document (keeps course code, name, and
    credit hours on a single, cleanly spaced line).

    We capture raw bytes and decode as UTF-8 ourselves (rather than
    letting subprocess decode with the OS default encoding) because on
    Windows the default locale encoding (cp1252) cannot represent the
    Thai characters `pdftotext` outputs, raising a UnicodeDecodeError.
    """
    result = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", "-layout", pdf_path, "-"],
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def find_description_section(lines):
    """
    Narrow down to the 'course description' appendix, identified by the
    Thai heading 'คำอธิบายรายวิชา' (Course Description). Returns the
    start/end line indices (Python slice indices).
    """
    start = None
    for i, line in enumerate(lines):
        if "คำอธิบายรายวิชา" in line:
            # There are two occurrences: a section title/cover page, and the
            # actual heading right before the first course entry. We want
            # the LAST one before course codes start appearing, so keep
            # scanning and remember the most recent match until we hit the
            # first real course header.
            start = i

    if start is None:
        return 0, len(lines)

    return start, len(lines)


def parse_courses(full_text: str):
    lines = full_text.split("\n")
    start, end = find_description_section(lines)
    section_lines = lines[start:end]

    courses = []
    current = None
    # Track whether we've just captured a Thai header and are expecting the
    # English name on the following non-empty line(s).
    expect_english_name = False
    name_buffer = []

    def flush():
        nonlocal current
        if current is not None:
            current["name_english"] = " ".join(name_buffer).strip()
            courses.append(current)
        current = None

    for raw_line in section_lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        header_match = COURSE_HEADER_RE.match(line)
        if header_match:
            # Save the previous course before starting a new one.
            flush()
            name_buffer.clear()

            code = header_match.group("code")
            thai_name = header_match.group("name").strip()
            credit_str = header_match.group("credits").strip()

            total_credits = None
            lecture = lab = self_study = None
            m = re.match(r"(\d+)\((\d+)-(\d+)-(\d+)\)", credit_str)
            if m:
                total_credits, lecture, lab, self_study = m.groups()

            current = {
                "course_code": code,
                "name_thai": thai_name,
                "name_english": "",
                "credit_hours": credit_str,
                "credits": total_credits,
                "lecture_hours": lecture,
                "lab_hours": lab,
                "self_study_hours": self_study,
                "prerequisite_en": "",
            }
            expect_english_name = True
            continue

        if current is None:
            continue

        # Capture the prerequisite (English) line if present.
        prereq_match = PREREQ_EN_RE.match(stripped)
        if prereq_match:
            current["prerequisite_en"] = prereq_match.group(1).strip()
            expect_english_name = False
            continue

        # While we haven't hit the prerequisite lines yet, any non-empty
        # line following the header is part of the (possibly wrapped)
        # English course name.
        if expect_english_name:
            if not stripped:
                continue
            if stripped.startswith("วิชาบังคับ") or stripped.upper().startswith("PREREQUISITE"):
                expect_english_name = False
                continue
            # Skip stray Thai continuation lines (e.g. a Thai title that
            # wraps onto a second line before the English name begins) —
            # only keep lines that are (mostly) Latin script.
            if re.search(r"[\u0E00-\u0E7F]", stripped):
                continue
            name_buffer.append(stripped)

    flush()
    return courses


def write_csv(courses, out_path):
    fieldnames = [
        "course_code",
        "name_thai",
        "name_english",
        "credit_hours",
        "credits",
        "lecture_hours",
        "lab_hours",
        "self_study_hours",
        "prerequisite_en",
    ]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in courses:
            writer.writerow(c)


def main():
    if len(sys.argv) != 3:
        print("Usage: python pdf_to_csv.py <input.pdf> <output.csv>")
        sys.exit(1)

    pdf_path, csv_path = sys.argv[1], sys.argv[2]

    print(f"Reading {pdf_path} ...")
    full_text = extract_text(pdf_path)

    print("Parsing course list ...")
    courses = parse_courses(full_text)
    print(f"Found {len(courses)} courses.")

    write_csv(courses, csv_path)
    print(f"Saved CSV to {csv_path}")


if __name__ == "__main__":
    main()
