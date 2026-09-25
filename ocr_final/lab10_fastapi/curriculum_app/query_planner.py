"""Deterministic intent detection and schema-aware SQL planning."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .database import DatabaseInfo


@dataclass(frozen=True)
class QueryPlan:
    intent: str
    year: int | None = None
    semester: int | None = None
    course_code: str | None = None
    search_term: str | None = None
    compare: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "year": self.year,
            "semester": self.semester,
            "course_code": self.course_code,
            "search_term": self.search_term,
            "compare": self.compare,
        }


def _extract_number(text: str, labels: tuple[str, ...]) -> int | None:
    joined = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{joined})\s*(?:ที่\s*)?(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def detect_intent(question: str) -> QueryPlan:
    text = question.strip()
    lowered = text.casefold()
    year = _extract_number(text, ("ปี", "ชั้นปี", "year"))
    semester = _extract_number(text, ("เทอม", "ภาคการศึกษา", "semester"))
    code_match = re.search(r"(?<!\d)(\d{8})(?!\d)", text)
    code = code_match.group(1) if code_match else None
    compare = any(word in lowered for word in ("เปรียบเทียบ", "ต่างกัน", "compare", "versus", " vs "))

    credit_words = ("หน่วยกิต", "credit")
    total_words = ("รวมทั้งหมด", "ทั้งหมดกี่หน่วยกิต", "หน่วยกิตรวม", "total credit")
    course_count_words = ("กี่วิชา", "จำนวนวิชา", "how many course", "number of course")
    list_words = ("วิชาอะไร", "วิชาใด", "รายวิชา", "course list", "which course", "what course")
    prerequisite_words = (
        "วิชาบังคับก่อน", "ต้องเรียนวิชาอะไรมาก่อน", "ต้องเรียนอะไรมาก่อน",
        "prerequisite", "เรียนก่อน", "ลงเรียน",
    )

    if any(word in lowered for word in prerequisite_words):
        return QueryPlan("prerequisite", year, semester, code, compare=compare)
    if year is not None and semester is not None and any(word in lowered for word in credit_words):
        return QueryPlan("semester_credits", year, semester, compare=compare)
    if year is not None and any(word in lowered for word in credit_words):
        return QueryPlan("year_credits", year, semester, compare=compare)
    if any(word in lowered for word in total_words) and any(word in lowered for word in credit_words):
        return QueryPlan("program_total_credits", compare=compare)
    if any(word in lowered for word in course_count_words):
        return QueryPlan("course_count", year, semester, compare=compare)
    if year is not None and any(word in lowered for word in list_words):
        return QueryPlan("course_list", year, semester, compare=compare)
    if any(word in lowered for word in ("กี่ปี", "จำนวนปี", "how many years")):
        return QueryPlan("program_years", compare=compare)
    if (
        any(word in lowered for word in ("ชื่อ", "name", "ปริญญา", "degree", "ข้อมูลหลักสูตร"))
        and any(word in lowered for word in ("หลักสูตร", "สาขา", "program", "curriculum"))
    ):
        return QueryPlan("program_info", compare=compare)
    if not code and "วิชา" in text and any(
        word in lowered for word in ("รหัสอะไร", "รหัสวิชา", "กี่หน่วยกิต", "รายละเอียด", "ข้อมูลวิชา")
    ):
        name_match = re.search(
            r"วิชา\s*(.+?)\s*(?:มีรหัสอะไร|รหัสอะไร|มีรหัส|กี่หน่วยกิต|มีรายละเอียด|รายละเอียด|$)",
            text,
            re.IGNORECASE,
        )
        if name_match and name_match.group(1).strip():
            return QueryPlan("course_search", search_term=name_match.group(1).strip(), compare=compare)
    if code:
        return QueryPlan("course_detail", year, semester, code, compare=compare)
    if any(word in lowered for word in list_words):
        return QueryPlan("course_list", year, semester, compare=compare)
    return QueryPlan("unknown", year, semester, code, compare=compare)


def _conditions(plan: QueryPlan) -> str:
    parts: list[str] = []
    if plan.year is not None:
        parts.append(f"year = {plan.year}")
    if plan.semester is not None:
        parts.append(f"semester = {plan.semester}")
    return (" WHERE " + " AND ".join(parts)) if parts else ""


def deterministic_sql(plan: QueryPlan, database: DatabaseInfo) -> str | None:
    """Return SQL only when the intent can be answered reliably from the real schema."""
    intent = plan.intent
    if intent == "program_total_credits":
        if database.has("program", "program_id", "total_credits"):
            return "SELECT program_id, total_credits, source_file, page_number FROM program"
        if database.has("v_total_credits", "credits"):
            return "SELECT credits AS total_credits FROM v_total_credits"
        return None

    if intent == "program_years" and database.has("program", "program_id", "years"):
        return "SELECT program_id, years, source_file, page_number FROM program"

    if intent == "program_info" and database.has("program", "program_id", "name_th"):
        fields = ["program_id", "name_th"]
        for column in ("name_en", "degree", "total_credits", "years", "source_file", "page_number"):
            if database.has("program", column):
                fields.append(column)
        return f"SELECT {', '.join(fields)} FROM program"

    if intent == "semester_credits":
        if database.has("v_semester_credits", "year", "semester", "credits"):
            fields = "year, semester, credits"
            if database.has("v_semester_credits", "n_courses"):
                fields += ", n_courses"
            if database.has("v_semester_credits", "source_files", "source_pages"):
                fields += ", source_files, source_pages"
            return f"SELECT {fields} FROM v_semester_credits{_conditions(plan)}"
        return None

    if intent == "year_credits":
        if database.has("v_year_credits", "year", "credits"):
            fields = "year, credits"
            if database.has("v_year_credits", "n_courses"):
                fields += ", n_courses"
            return f"SELECT {fields} FROM v_year_credits{_conditions(plan)}"
        if database.has("plan_item", "year", "credits"):
            return (
                "SELECT year, SUM(credits) AS credits, COUNT(*) AS n_courses "
                f"FROM plan_item{_conditions(plan)} GROUP BY year"
            )
        return None

    if intent == "course_count":
        if database.has("plan_item", "year", "semester"):
            where = _conditions(plan)
            return f"SELECT COUNT(*) AS course_count FROM plan_item{where}"
        if database.has("courses", "id"):
            return "SELECT COUNT(*) AS course_count FROM courses"
        return None

    if intent == "course_list":
        if database.has("v_plan", "year", "semester", "code", "name_th", "credits"):
            return (
                "SELECT year, semester, code, name_th, name_en, credits, "
                "source_file, page_number FROM v_plan"
                f"{_conditions(plan)} ORDER BY year, semester, code"
            )
        if database.has("courses", "course_code", "course_name_th", "credits"):
            return (
                "SELECT course_code AS code, course_name_th AS name_th, "
                "course_name_en AS name_en, credits, source_file, page_number "
                "FROM courses ORDER BY course_code"
            )
        return None

    if intent == "course_detail" and plan.course_code:
        code = plan.course_code.replace("'", "''")
        if database.has("course", "code", "name_th", "credits"):
            return (
                "SELECT code, name_th, name_en, credits, lecture_h, lab_h, self_h, "
                f"source_file, page_number FROM course WHERE code = '{code}'"
            )
        if database.has("courses", "course_code", "course_name_th", "credits"):
            return (
                "SELECT course_code AS code, course_name_th AS name_th, "
                "course_name_en AS name_en, credits, prerequisites, source_file, page_number "
                f"FROM courses WHERE course_code = '{code}'"
            )
        return None

    if intent == "course_search" and plan.search_term:
        term = plan.search_term.replace("'", "''")
        if database.has("course", "code", "name_th", "name_en", "credits"):
            return (
                "SELECT code, name_th, name_en, credits, lecture_h, lab_h, self_h, "
                "source_file, page_number FROM course "
                f"WHERE name_th LIKE '%{term}%' OR name_en LIKE '%{term}%' "
                "ORDER BY code"
            )
        if database.has("courses", "course_code", "course_name_th", "course_name_en", "credits"):
            return (
                "SELECT course_code AS code, course_name_th AS name_th, "
                "course_name_en AS name_en, credits, prerequisites, source_file, page_number "
                "FROM courses "
                f"WHERE course_name_th LIKE '%{term}%' OR course_name_en LIKE '%{term}%' "
                "ORDER BY course_code"
            )
        return None

    if intent == "prerequisite" and plan.course_code:
        code = plan.course_code.replace("'", "''")
        if database.has("prerequisite", "code", "requires", "kind"):
            return (
                "SELECT code, requires, kind, source_file, page_number FROM prerequisite "
                f"WHERE code = '{code}'"
            )
        if database.has("courses", "course_code", "prerequisites"):
            return (
                "SELECT course_code AS code, prerequisites, source_file, page_number "
                f"FROM courses WHERE course_code = '{code}'"
            )
        return None

    return None
