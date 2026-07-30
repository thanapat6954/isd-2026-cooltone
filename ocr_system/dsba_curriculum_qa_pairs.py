"""
Generate Q&A pairs CSV from DSBA curriculum ground truth.

Produces questions that can be answered from the DSBA academic plan (coop),
with answers referencing the curriculum page/section (year/semester)
and regulation clauses where applicable.

Usage:
    python dsba_curriculum_qa_pairs.py [input_json] [output_csv]

Defaults:
    input  = data/input/DSBA_academic_plan_coop.json
    output = dsba_curriculum_qa_pairs.csv
"""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def _norm(text):
    """Collapse whitespace/newlines into single space."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _credits_total(credit_str):
    """Extract the leading number from a credit string like '3(3-0-6)'."""
    m = re.match(r"(\d+)", str(credit_str))
    return int(m.group(1)) if m else 0


def _page_ref(year, semester, flexible=None):
    """Build a page/section reference string."""
    y = str(year) if year not in (None, 0, "0") else ""
    s = str(semester) if semester not in (None, 0, "0") else ""
    if y and s:
        return f"แผนการศึกษา ปีที่ {y} ภาคเรียนที่ {s}"
    if flexible:
        return f"กลุ่มวิชาเลือก (ลงได้ในภาคเรียน {_norm(flexible)})"
    return "ตารางวิชาเลือกเฉพาะ (Elective Pool)"


def generate_qa_pairs(data):
    """Generate all Q&A pairs from the GT data. Returns list of dicts."""
    program = data.get("program", "DSBA")
    plan = data.get("plan", "coop")
    source = data.get("source", "")

    courses = []
    for c in data.get("courses", []):
        code = str(c.get("code", "")).strip()
        if not code or code.startswith("หมายเหตุ"):
            continue
        courses.append(c)

    qa = []
    q_id = 0

    def add(question, answer, category, page_ref, regulation=None):
        nonlocal q_id
        q_id += 1
        qa.append({
            "qa_id": q_id,
            "question": question,
            "answer": answer,
            "category": category,
            "page_section_ref": page_ref,
            "regulation_clause": regulation or "",
            "curriculum_program": program,
            "plan": plan,
            "ground_truth_source": source,
        })

    # ──────────────────────────────────────────────
    # 1. OVERALL CURRICULUM STRUCTURE
    # ──────────────────────────────────────────────
    # Count by category
    cat_counts = defaultdict(int)
    cat_credits = defaultdict(int)
    for c in courses:
        cat = _norm(c.get("category")) or "ไม่ระบุ"
        cat_counts[cat] += 1
        cat_credits[cat] += _credits_total(c.get("credits", "0"))

    required = [c for c in courses if _norm(c.get("type")) == "บังคับ"]
    elective = [c for c in courses if _norm(c.get("type")) == "เลือก"]

    # Scheduled courses (year != 0)
    scheduled = [c for c in courses if c.get("year") not in (None, 0, "0")]
    total_scheduled_credits = sum(_credits_total(c.get("credits", "0")) for c in scheduled)

    add(
        f"หลักสูตร {program} (แผน {plan}) มีรายวิชาในแผนการศึกษาทั้งหมดกี่รายวิชา?",
        f"{len(scheduled)} รายวิชาในแผนการศึกษา (ไม่รวมกลุ่มวิชาเลือกเฉพาะสาขาในตาราง Elective Pool อีก {len(courses) - len(scheduled)} รายวิชา, รวมทั้งหมด {len(courses)} รายวิชา)",
        "Curriculum Structure",
        "ภาพรวมโครงสร้างหลักสูตร",
        "ข้อบังคับฯ ว่าด้วยการศึกษาระดับปริญญาตรี — โครงสร้างหลักสูตร",
    )

    add(
        f"หลักสูตร {program} (แผน {plan}) มีวิชาบังคับกี่รายวิชา?",
        f"{len(required)} รายวิชาบังคับ",
        "Curriculum Structure",
        "ภาพรวมโครงสร้างหลักสูตร",
    )

    add(
        f"หลักสูตร {program} (แผน {plan}) มีวิชาเลือกทั้งหมดกี่รายวิชา?",
        f"{len(elective)} รายวิชาเลือก (รวมวิชาเลือกเฉพาะสาขา วิชาเลือกศึกษาทั่วไป และวิชาเลือกเสรี)",
        "Curriculum Structure",
        "ภาพรวมโครงสร้างหลักสูตร",
    )

    # Per-category summary
    for cat, cnt in sorted(cat_counts.items()):
        add(
            f"หลักสูตร {program} มีรายวิชาใน{cat}กี่รายวิชา?",
            f"{cnt} รายวิชา",
            "Curriculum Structure",
            "ภาพรวมโครงสร้างหลักสูตร",
        )

    # ──────────────────────────────────────────────
    # 2. PER-YEAR/SEMESTER QUESTIONS
    # ──────────────────────────────────────────────
    by_ys = defaultdict(list)
    for c in courses:
        y = c.get("year")
        s = c.get("semester")
        if y not in (None, 0, "0") and s not in (None, 0, "0"):
            by_ys[(int(y), int(s))].append(c)

    for (y, s), cs in sorted(by_ys.items()):
        names = ", ".join(
            f"{_norm(c.get('code'))} {_norm(c.get('name_th'))}" for c in cs
        )
        total_cr = sum(_credits_total(c.get("credits", "0")) for c in cs)
        ref = f"แผนการศึกษา ปีที่ {y} ภาคเรียนที่ {s}"

        add(
            f"ปีที่ {y} ภาคเรียนที่ {s} ของหลักสูตร {program} ต้องเรียนกี่วิชา?",
            f"{len(cs)} รายวิชา รวม {total_cr} หน่วยกิต",
            "Study Plan",
            ref,
        )

        add(
            f"รายวิชาที่ต้องเรียนในปีที่ {y} ภาคเรียนที่ {s} ของหลักสูตร {program} มีอะไรบ้าง?",
            names,
            "Study Plan",
            ref,
        )

        add(
            f"ปีที่ {y} ภาคเรียนที่ {s} ของหลักสูตร {program} รวมกี่หน่วยกิต?",
            f"{total_cr} หน่วยกิต",
            "Study Plan",
            ref,
        )

    # ──────────────────────────────────────────────
    # 3. PER-COURSE QUESTIONS (scheduled courses only)
    # ──────────────────────────────────────────────
    for c in scheduled:
        code = _norm(c.get("code"))
        name_th = _norm(c.get("name_th"))
        name_en = _norm(c.get("name_en"))
        credits = _norm(c.get("credits"))
        cat = _norm(c.get("category"))
        ctype = _norm(c.get("type"))
        prereq = _norm(c.get("prerequisite"))
        ref = _page_ref(c.get("year"), c.get("semester"), c.get("flexible_year_semester"))

        # Skip placeholder codes for individual questions
        if "x" in code.lower():
            continue

        # What is this course?
        add(
            f"รายวิชา {code} คือวิชาอะไร?",
            f"{name_th} ({name_en}), {credits} หน่วยกิต, {cat} — {ctype}",
            "Course Detail",
            ref,
        )

        # Credits
        add(
            f"รายวิชา {code} {name_th} มีกี่หน่วยกิต?",
            f"{credits}",
            "Course Detail",
            ref,
        )

        # English name
        if name_en:
            add(
                f"ชื่อภาษาอังกฤษของรายวิชา {code} {name_th} คืออะไร?",
                name_en,
                "Course Detail",
                ref,
            )

        # Prerequisite
        if prereq and prereq != "ไม่มี":
            # Find prereq name
            prereq_name = ""
            for pc in courses:
                if _norm(pc.get("code")) == prereq:
                    prereq_name = _norm(pc.get("name_th"))
                    break
            answer = f"{prereq}"
            if prereq_name:
                answer += f" ({prereq_name})"
            add(
                f"รายวิชา {code} {name_th} มีวิชาบังคับก่อน (prerequisite) หรือไม่? ถ้ามีคือวิชาอะไร?",
                f"มี — {answer}",
                "Prerequisite",
                ref,
                "ข้อบังคับฯ — เกณฑ์การลงทะเบียน: ต้องผ่านวิชาบังคับก่อนตามที่หลักสูตรกำหนด",
            )

        # Category & type
        add(
            f"รายวิชา {code} {name_th} อยู่ในหมวดหมู่ใด?",
            f"{cat}, ประเภท: {ctype}",
            "Course Classification",
            ref,
        )

    # ──────────────────────────────────────────────
    # 4. PREREQUISITE CHAIN QUESTIONS
    # ──────────────────────────────────────────────
    prereq_courses = [
        c for c in courses
        if _norm(c.get("prerequisite")) not in ("", "ไม่มี")
        and "x" not in str(c.get("code")).lower()
    ]
    if prereq_courses:
        prereq_list = "; ".join(
            f"{_norm(c.get('code'))} {_norm(c.get('name_th'))} ← ต้องผ่าน {_norm(c.get('prerequisite'))}"
            for c in prereq_courses
        )
        add(
            f"รายวิชาใดบ้างในหลักสูตร {program} ที่มีวิชาบังคับก่อน (prerequisite)?",
            prereq_list,
            "Prerequisite",
            "ภาพรวมแผนการศึกษา",
            "ข้อบังคับฯ — เกณฑ์การลงทะเบียน: ต้องผ่านวิชาบังคับก่อนตามที่หลักสูตรกำหนด",
        )

    # ──────────────────────────────────────────────
    # 5. ELECTIVE POOL QUESTIONS
    # ──────────────────────────────────────────────
    elective_pool = [
        c for c in courses
        if c.get("year") in (None, 0, "0") and _norm(c.get("type")) == "เลือก"
    ]

    # Group by sub-group
    ds_electives = []
    stat_electives = []
    de_electives = []
    ba_electives = []
    other_electives = []

    for c in elective_pool:
        name_th = _norm(c.get("name_th") or "")
        code = _norm(c.get("code"))
        if "วิทยาการข้อมูล" in name_th or code.startswith("06026") and any(
            kw in name_th for kw in ["ปัญญาประดิษฐ์", "เรียนรู้", "ประมวลผล", "เหมือง", "ค้นคืน",
                                      "คอมพิวเตอร์วิชัน", "ภาพ", "หัวข้อพิเศษทางวิทยาการ", "ปฏิบัติการพิเศษทางวิทยาการ"]
        ):
            ds_electives.append(c)
        elif any(kw in name_th for kw in ["สถิติ", "อนุกรมเวลา", "เบย์", "สโตแคสติก", "หลายตัวแปร",
                                           "การออกแบบการทดลอง", "หัวข้อพิเศษทางการวิเคราะห์", "ปฏิบัติการพิเศษทางการวิเคราะห์"]):
            stat_electives.append(c)
        elif any(kw in name_th for kw in ["ไปป์ไลน์", "อัจฉริยะ", "การดำเนินงานการเรียนรู้", "กลุ่มเมฆ",
                                           "ฐานข้อมูลขั้นสูง", "บำรุงรักษา", "กระจาย",
                                           "หัวข้อพิเศษทางวิศวกรรม", "ปฏิบัติการพิเศษทางวิศวกรรม"]):
            de_electives.append(c)
        elif any(kw in name_th for kw in ["ธุรกิจ", "บัญชี", "การเงิน", "การตลาด", "สุขภาพ", "คลินิก",
                                           "ปฏิบัติการ", "กลยุทธ์", "เครือข่ายสังคม"]):
            ba_electives.append(c)
        else:
            ds_electives.append(c)  # Default to DS group

    add(
        f"หลักสูตร {program} มีวิชาเลือกเฉพาะสาขาให้เลือกทั้งหมดกี่รายวิชา?",
        f"{len(elective_pool)} รายวิชาในกลุ่มวิชาเลือกเฉพาะสาขา",
        "Elective Courses",
        "ตารางวิชาเลือกเฉพาะสาขา (Elective Pool)",
    )

    # DS electives
    if ds_electives:
        ds_names = ", ".join(f"{_norm(c.get('code'))} {_norm(c.get('name_th'))}" for c in ds_electives)
        add(
            f"กลุ่มวิชาเลือกทางวิทยาการข้อมูล (Data Science) ในหลักสูตร {program} มีวิชาอะไรบ้าง?",
            ds_names,
            "Elective Courses",
            "ตารางวิชาเลือก — กลุ่มวิทยาการข้อมูล",
        )

    # Stat electives
    if stat_electives:
        stat_names = ", ".join(f"{_norm(c.get('code'))} {_norm(c.get('name_th'))}" for c in stat_electives)
        add(
            f"กลุ่มวิชาเลือกทางการวิเคราะห์เชิงสถิติ (Statistical Analytics) ในหลักสูตร {program} มีวิชาอะไรบ้าง?",
            stat_names,
            "Elective Courses",
            "ตารางวิชาเลือก — กลุ่มการวิเคราะห์เชิงสถิติ",
        )

    # DE electives
    if de_electives:
        de_names = ", ".join(f"{_norm(c.get('code'))} {_norm(c.get('name_th'))}" for c in de_electives)
        add(
            f"กลุ่มวิชาเลือกทางวิศวกรรมข้อมูล (Data Engineering) ในหลักสูตร {program} มีวิชาอะไรบ้าง?",
            de_names,
            "Elective Courses",
            "ตารางวิชาเลือก — กลุ่มวิศวกรรมข้อมูล",
        )

    # BA electives
    if ba_electives:
        ba_names = ", ".join(f"{_norm(c.get('code'))} {_norm(c.get('name_th'))}" for c in ba_electives)
        add(
            f"กลุ่มวิชาเลือกทางธุรกิจ/ประยุกต์ ในหลักสูตร {program} มีวิชาอะไรบ้าง?",
            ba_names,
            "Elective Courses",
            "ตารางวิชาเลือก — กลุ่มธุรกิจ/ประยุกต์",
        )

    # ──────────────────────────────────────────────
    # 6. GENERAL EDUCATION QUESTIONS
    # ──────────────────────────────────────────────
    ge_courses = [c for c in courses if "ศึกษาทั่วไป" in _norm(c.get("category", ""))]
    ge_required = [c for c in ge_courses if _norm(c.get("type")) == "บังคับ"]
    ge_elective = [c for c in ge_courses if _norm(c.get("type")) == "เลือก"]

    add(
        f"หลักสูตร {program} มีรายวิชาศึกษาทั่วไปทั้งหมดกี่รายวิชา?",
        f"{len(ge_courses)} รายวิชา (บังคับ {len(ge_required)}, เลือก {len(ge_elective)})",
        "General Education",
        "แผนการศึกษา — หมวดวิชาศึกษาทั่วไป",
    )

    ge_names = ", ".join(f"{_norm(c.get('code'))} {_norm(c.get('name_th'))}" for c in ge_required)
    add(
        f"รายวิชาศึกษาทั่วไปบังคับของหลักสูตร {program} มีอะไรบ้าง?",
        ge_names,
        "General Education",
        "แผนการศึกษา — หมวดวิชาศึกษาทั่วไป",
    )

    # ──────────────────────────────────────────────
    # 7. COOP EDUCATION QUESTIONS
    # ──────────────────────────────────────────────
    coop_courses = [
        c for c in courses
        if "สหกิจ" in _norm(c.get("name_th", ""))
    ]
    if coop_courses:
        coop_info = "; ".join(
            f"{_norm(c.get('code'))} {_norm(c.get('name_th'))} {_norm(c.get('credits'))} หน่วยกิต"
            for c in coop_courses
        )
        add(
            f"หลักสูตร {program} (แผน {plan}) มีรายวิชาสหกิจศึกษาอะไรบ้าง?",
            coop_info,
            "Cooperative Education",
            "แผนการศึกษา ปีที่ 4 ภาคเรียนที่ 2 / ตารางวิชาเลือก",
            "ข้อบังคับฯ — เกณฑ์การสำเร็จการศึกษา: สำหรับแผนสหกิจต้องผ่านรายวิชาสหกิจศึกษา",
        )

        # Find the scheduled coop
        sched_coop = [c for c in coop_courses if c.get("year") not in (None, 0, "0")]
        if sched_coop:
            sc = sched_coop[0]
            add(
                f"สหกิจศึกษาของหลักสูตร {program} (แผน {plan}) อยู่ในปีและภาคเรียนใด?",
                f"ปีที่ {sc.get('year')} ภาคเรียนที่ {sc.get('semester')} — {_norm(sc.get('credits'))} หน่วยกิต",
                "Cooperative Education",
                _page_ref(sc.get("year"), sc.get("semester")),
                "ข้อบังคับฯ — เกณฑ์การสำเร็จการศึกษา",
            )

        add(
            f"สหกิจศึกษาของหลักสูตร {program} มีกี่หน่วยกิต?",
            f"{_norm(sched_coop[0].get('credits'))} หน่วยกิต" if sched_coop else "6(0-35-0) หน่วยกิต",
            "Cooperative Education",
            "แผนการศึกษา ปีที่ 4 ภาคเรียนที่ 2",
            "ข้อบังคับฯ — เกณฑ์การสำเร็จการศึกษา",
        )

    # ──────────────────────────────────────────────
    # 8. PROJECT (CAPSTONE) QUESTIONS
    # ──────────────────────────────────────────────
    project_courses = [
        c for c in courses
        if "โครงงาน" in _norm(c.get("name_th", ""))
        and "x" not in str(c.get("code")).lower()
    ]
    if project_courses:
        proj_info = "; ".join(
            f"{_norm(c.get('code'))} {_norm(c.get('name_th'))} ปี {c.get('year')}/{c.get('semester')} {_norm(c.get('credits'))}"
            for c in project_courses
        )
        add(
            f"หลักสูตร {program} มีรายวิชาโครงงาน (Project) กี่รายวิชา?",
            f"{len(project_courses)} รายวิชา: {proj_info}",
            "Capstone Project",
            "แผนการศึกษา — วิชาโครงงาน",
        )

        for pc in project_courses:
            prereq = _norm(pc.get("prerequisite"))
            if prereq and prereq != "ไม่มี":
                prereq_name = ""
                for other in courses:
                    if _norm(other.get("code")) == prereq:
                        prereq_name = _norm(other.get("name_th"))
                        break
                add(
                    f"รายวิชา {_norm(pc.get('code'))} {_norm(pc.get('name_th'))} ต้องผ่านวิชาอะไรก่อน?",
                    f"{prereq} ({prereq_name})" if prereq_name else prereq,
                    "Capstone Project",
                    _page_ref(pc.get("year"), pc.get("semester")),
                    "ข้อบังคับฯ — เกณฑ์การลงทะเบียน: วิชาบังคับก่อน",
                )

    # ──────────────────────────────────────────────
    # 9. FREE ELECTIVE QUESTIONS
    # ──────────────────────────────────────────────
    free_electives = [c for c in courses if "เลือกเสรี" in _norm(c.get("category", ""))]
    if free_electives:
        total_free_cr = sum(_credits_total(c.get("credits", "0")) for c in free_electives)
        add(
            f"หลักสูตร {program} ต้องลงวิชาเลือกเสรีกี่รายวิชา รวมกี่หน่วยกิต?",
            f"{len(free_electives)} รายวิชา รวม {total_free_cr} หน่วยกิต",
            "Free Electives",
            "แผนการศึกษา ปีที่ 4 ภาคเรียนที่ 1",
            "ข้อบังคับฯ — โครงสร้างหลักสูตร: หมวดวิชาเลือกเสรี",
        )

    # ──────────────────────────────────────────────
    # 10. SPECIFIC COURSE LOOKUP QUESTIONS
    # ──────────────────────────────────────────────
    # When to study specific subjects
    key_subjects = {
        "วิทยาการข้อมูล": "พื้นฐานวิทยาการข้อมูล",
        "Machine Learning": "การเรียนรู้ของเครื่องเชิงประยุกต์",
        "Big Data": "ระบบข้อมูลมหัต",
        "Data Visualization": "การแสดงข้อมูลด้วยแผนภาพ",
        "Data Warehousing": "การสร้างคลังข้อมูล",
    }
    for keyword, expected_name in key_subjects.items():
        for c in scheduled:
            if expected_name in _norm(c.get("name_th", "")):
                add(
                    f"รายวิชา {expected_name} ของหลักสูตร {program} เรียนในปีและภาคเรียนใด?",
                    f"ปีที่ {c.get('year')} ภาคเรียนที่ {c.get('semester')}, รหัสวิชา {_norm(c.get('code'))}, {_norm(c.get('credits'))} หน่วยกิต",
                    "Course Detail",
                    _page_ref(c.get("year"), c.get("semester")),
                )
                break

    # ──────────────────────────────────────────────
    # 11. SPECIAL NOTES / FACULTY-DESIGNATED COURSES
    # ──────────────────────────────────────────────
    noted_courses = [c for c in courses if _norm(c.get("note"))]
    if noted_courses:
        for nc in noted_courses:
            note = _norm(nc.get("note"))
            if "กำหนดโดยคณะ" in note:
                add(
                    f"รายวิชา {_norm(nc.get('code'))} {_norm(nc.get('name_th'))} มีเงื่อนไขพิเศษอะไร?",
                    f"หมายเหตุ: {note}",
                    "Special Notes",
                    _page_ref(nc.get("year"), nc.get("semester")),
                )
            elif "สหกิจ" in note:
                add(
                    f"รายวิชา {_norm(nc.get('code'))} {_norm(nc.get('name_th'))} มีเงื่อนไขพิเศษอะไร?",
                    f"หมายเหตุ: {note}",
                    "Special Notes",
                    _page_ref(nc.get("year"), nc.get("semester"), nc.get("flexible_year_semester")),
                    "ข้อบังคับฯ — เกณฑ์การสำเร็จการศึกษา (แผนสหกิจ)",
                )

    # ──────────────────────────────────────────────
    # 12. YEAR-LEVEL SUMMARY QUESTIONS
    # ──────────────────────────────────────────────
    by_year = defaultdict(list)
    for c in scheduled:
        by_year[int(c.get("year"))].append(c)

    for y in sorted(by_year.keys()):
        yr_courses = by_year[y]
        yr_credits = sum(_credits_total(c.get("credits", "0")) for c in yr_courses)
        yr_required = len([c for c in yr_courses if _norm(c.get("type")) == "บังคับ"])
        yr_elective = len([c for c in yr_courses if _norm(c.get("type")) == "เลือก"])
        add(
            f"ปีที่ {y} ของหลักสูตร {program} ต้องเรียนรวมกี่หน่วยกิต?",
            f"รวม {yr_credits} หน่วยกิต ({len(yr_courses)} รายวิชา: บังคับ {yr_required}, เลือก {yr_elective})",
            "Year Summary",
            f"แผนการศึกษา ปีที่ {y}",
        )

    return qa


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    base_dir = Path(__file__).resolve().parent
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else base_dir / "data" / "input" / "DSBA_academic_plan_coop.json"
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else base_dir / "dsba_curriculum_qa_pairs.csv"

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    qa_pairs = generate_qa_pairs(data)

    fieldnames = [
        "qa_id",
        "question",
        "answer",
        "category",
        "page_section_ref",
        "regulation_clause",
        "curriculum_program",
        "plan",
        "ground_truth_source",
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(qa_pairs)

    print(f"[OK] Generated {len(qa_pairs)} Q&A pairs")
    print(f"  Input : {input_path}")
    print(f"  Output: {output_path}")

    # Summary by category
    cats = defaultdict(int)
    for q in qa_pairs:
        cats[q["category"]] += 1
    print(f"\n  Q&A pairs by category:")
    for cat, cnt in sorted(cats.items()):
        print(f"    {cat}: {cnt}")

    regs = [q for q in qa_pairs if q["regulation_clause"]]
    print(f"\n  Q&A pairs with regulation references: {len(regs)}")


if __name__ == "__main__":
    main()
