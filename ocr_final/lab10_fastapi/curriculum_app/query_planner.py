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
    required_only: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "year": self.year,
            "semester": self.semester,
            "course_code": self.course_code,
            "search_term": self.search_term,
            "compare": self.compare,
            "required_only": self.required_only,
        }


def _extract_number(text: str, labels: tuple[str, ...]) -> int | None:
    joined = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{joined})\s*(?:ที่\s*)?(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def normalize_course_name(value: str) -> str:
    """Normalize formatting and common Thai nominal variants, not arbitrary fuzzy matches."""
    value = re.sub(r'\s+', '', value).casefold()
    for phrase in ('การเขียนโปรแกรม', 'การสร้างโปรแกรม', 'การโปรแกรม'):
        value = value.replace(phrase, 'โปรแกรม')
    return value


def _name_sql(column: str) -> str:
    return f"normalize_course_name({column})"


def _course_fields(database: DatabaseInfo) -> str:
    fields = 'code, name_th, name_en, credits, lecture_h, lab_h, self_h, source_file, page_number'
    if database.has('plan_item', 'code', 'printed_page_number', 'source_file', 'page_number'):
        fields += (', (SELECT MIN(p.printed_page_number) FROM plan_item p WHERE p.code = course.code '
                   'AND p.source_file = course.source_file AND p.page_number = course.page_number) AS printed_page_number')
    return fields


def detect_intent(question: str) -> QueryPlan:
    text = question.strip()
    lowered = text.casefold()
    year = _extract_number(text, ("ปี", "ชั้นปี", "year"))
    semester = _extract_number(text, ("เทอม", "ภาคการศึกษา", "ภาคเรียน", "semester"))
    code_match = re.search(r"(?<!\d)(\d{8})(?!\d)", text)
    code = code_match.group(1) if code_match else None
    compare = any(word in lowered for word in ("เปรียบเทียบ", "ต่างกัน", "compare", "versus", " vs "))
    required_only = any(word in lowered for word in ("วิชาบังคับ", "required course", "core course"))

    credit_words = ("หน่วยกิต", "credit")
    total_words = ("รวมทั้งหมด", "ทั้งหมดกี่หน่วยกิต", "หน่วยกิตรวม", "total credit")
    course_count_words = ("กี่วิชา", "จำนวนวิชา", "how many course", "number of course")
    list_words = ("วิชาอะไร", "วิชาใด", "รายวิชา", "แสดงรหัส", "รหัสทั้งหมด", "course list", "which course", "what course")
    prerequisite_words = (
        "วิชาบังคับก่อน", "ต้องเรียนวิชาอะไรมาก่อน", "ต้องเรียนอะไรมาก่อน",
        "prerequisite", "เรียนก่อน", "ลงเรียน",
    )

    version_diff_words = (
        "มีในหลักสูตรเดิม", "มีในฉบับเก่า", "old curriculum",
        "ไม่มีในหลักสูตรฉบับปรับปรุง", "ไม่มีในฉบับใหม่", "not in the revised",
    )
    if any(word in lowered for word in version_diff_words):
        return QueryPlan("version_course_diff", compare=True)

    if not code and 'วิชา' in text:
        name_match = re.search(r'วิชา\s*(.+?)\s*(?:มีวิชาบังคับก่อน|ต้องเรียนอะไรมาก่อน|มีรหัสอะไร|รหัสอะไร|มีรหัส|มีกี่หน่วยกิต|กี่หน่วยกิต|มีรายละเอียด|รายละเอียด)', text)
        if name_match and name_match.group(1).strip():
            return QueryPlan('course_search', search_term=name_match.group(1).strip(), compare=compare)
    if any(word in lowered for word in prerequisite_words):
        return QueryPlan("prerequisite", year, semester, code, compare=compare, required_only=required_only)
    if year is not None and semester is not None and any(word in lowered for word in credit_words):
        return QueryPlan("semester_credits", year, semester, compare=compare, required_only=required_only)
    if year is not None and any(word in lowered for word in credit_words):
        return QueryPlan("year_credits", year, semester, compare=compare, required_only=required_only)
    if any(word in lowered for word in total_words) and any(word in lowered for word in credit_words):
        return QueryPlan("program_total_credits", compare=compare, required_only=required_only)
    if any(word in lowered for word in course_count_words):
        return QueryPlan("course_count", year, semester, compare=compare, required_only=required_only)
    if required_only and year is not None:
        return QueryPlan("course_list", year, semester, compare=compare, required_only=True)
    if year is not None and any(word in lowered for word in list_words):
        return QueryPlan("course_list", year, semester, compare=compare, required_only=required_only)
    if any(word in lowered for word in ("กี่ปี", "จำนวนปี", "how many years")):
        return QueryPlan("program_years", compare=compare, required_only=required_only)
    if (
        not code and any(word in lowered for word in ("ชื่อ", "name", "ปริญญา", "degree", "ข้อมูลหลักสูตร"))
        and any(word in lowered for word in ("หลักสูตร", "สาขา", "program", "curriculum"))
    ):
        return QueryPlan("program_info", compare=compare, required_only=required_only)
    if not code and "วิชา" in text and any(
        word in lowered for word in ("รหัสอะไร", "รหัสวิชา", "กี่หน่วยกิต", "รายละเอียด", "ข้อมูลวิชา")
    ):
        name_match = re.search(
            r"วิชา\s*(.+?)\s*(?:มีรหัสอะไร|รหัสอะไร|มีรหัส|มีกี่หน่วยกิต|กี่หน่วยกิต|มีรายละเอียด|รายละเอียด|$)",
            text,
            re.IGNORECASE,
        )
        if name_match and name_match.group(1).strip():
            return QueryPlan("course_search", search_term=name_match.group(1).strip(), compare=compare, required_only=required_only)
    if code:
        return QueryPlan("course_detail", year, semester, code, compare=compare, required_only=required_only)
    if any(word in lowered for word in list_words):
        return QueryPlan("course_list", year, semester, compare=compare, required_only=required_only)
    return QueryPlan("unknown", year, semester, code, compare=compare, required_only=required_only)


def _conditions(plan: QueryPlan, *, include_required: bool = False) -> str:
    parts: list[str] = []
    if plan.year is not None:
        parts.append(f"year = {plan.year}")
    if plan.semester is not None:
        parts.append(f"semester = {plan.semester}")
    if include_required and plan.required_only:
        parts.append("(ctype LIKE '%บังคับ%' OR LOWER(ctype) LIKE '%required%')")
    return (" WHERE " + " AND ".join(parts)) if parts else ""


def deterministic_sql(plan: QueryPlan, database: DatabaseInfo) -> str | None:
    """Return SQL only when the intent can be answered reliably from the real schema."""
    intent = plan.intent
    if intent == "version_course_diff":
        if database.has("v_plan", "code", "name_th", "credits"):
            where = " WHERE is_placeholder = 0" if database.has("v_plan", "is_placeholder") else ""
            return (
                "SELECT DISTINCT code, name_th, name_en, credits, source_file, page_number "
                f"FROM v_plan{where} ORDER BY code"
            )
        return None
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
            if database.has("v_semester_credits", "source_printed_pages"):
                fields += ", source_printed_pages"
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
        if database.has("plan_item", "id", "year", "semester", "alt_group"):
            where = _conditions(plan, include_required=True)
            return (
                "SELECT COUNT(DISTINCT COALESCE(alt_group, 'row-' || id)) AS course_count, "
                "COUNT(DISTINCT COALESCE(alt_group, 'row-' || id)) AS n_courses, "
                "GROUP_CONCAT(DISTINCT source_file) AS source_files, "
                "GROUP_CONCAT(DISTINCT page_number) AS source_pages "
                f"FROM plan_item{where}"
            )
        if database.has("courses", "id"):
            return "SELECT COUNT(*) AS course_count FROM courses"
        return None

    if intent == "course_list":
        view = 'v_study_plan' if database.has('v_study_plan', 'id', 'year', 'semester', 'code') else 'v_plan'
        if database.has(view, "year", "semester", "code", "name_th", "credits"):
            fields = [
                "year", "semester", "code", "name_th", "name_en", "credits",
                "source_file", "page_number",
            ]
            for column in (
                "id", "printed_page_number", "credits_raw", "alt_group", "alternative_index",
                "is_placeholder", "elective_type", "raw_code", "code_pattern", "category", "ctype", "note",
            ):
                if database.has(view, column):
                    fields.append(column)
            return (
                f"SELECT {', '.join(fields)} FROM {view}"
                f"{_conditions(plan, include_required=True)} ORDER BY year, semester, code"
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
                f"SELECT {_course_fields(database)} FROM course WHERE code = '{code}'"
            )
        if database.has("courses", "course_code", "course_name_th", "credits"):
            return (
                "SELECT course_code AS code, course_name_th AS name_th, "
                "course_name_en AS name_en, credits, prerequisites, source_file, page_number "
                f"FROM courses WHERE course_code = '{code}'"
            )
        return None

    if intent == "course_search" and plan.search_term:
        term = normalize_course_name(plan.search_term).replace("'", "''").replace('%', '\\%').replace('_', '\\_')
        exact = normalize_course_name(plan.search_term).replace("'", "''")
        literal = plan.search_term.replace("'", "''").replace('%', '\\%').replace('_', '\\_')
        if database.has("course", "code", "name_th", "name_en", "credits"):
            return (
                f"SELECT {_course_fields(database)} FROM course "
                f"WHERE {_name_sql('name_th')} LIKE '%{term}%' ESCAPE '\\' OR {_name_sql('name_en')} LIKE '%{term}%' ESCAPE '\\' "
                f"ORDER BY CASE WHEN name_th LIKE '%{literal}%' ESCAPE '\\' OR name_en LIKE '%{literal}%' ESCAPE '\\' THEN 0 ELSE 1 END, "
                f"CASE WHEN {_name_sql('name_th')} = '{exact}' OR {_name_sql('name_en')} = '{exact}' THEN 0 ELSE 1 END, code"
            )
        if database.has("courses", "course_code", "course_name_th", "course_name_en", "credits"):
            return (
                "SELECT course_code AS code, course_name_th AS name_th, "
                "course_name_en AS name_en, credits, prerequisites, source_file, page_number "
                "FROM courses "
                f"WHERE {_name_sql('course_name_th')} LIKE '%{term}%' ESCAPE '\\' OR {_name_sql('course_name_en')} LIKE '%{term}%' ESCAPE '\\' "
                f"ORDER BY CASE WHEN course_name_th LIKE '%{literal}%' ESCAPE '\\' OR course_name_en LIKE '%{literal}%' ESCAPE '\\' THEN 0 ELSE 1 END, "
                f"CASE WHEN {_name_sql('course_name_th')} = '{exact}' OR {_name_sql('course_name_en')} = '{exact}' THEN 0 ELSE 1 END, course_code"
            )
        return None

    if intent == "prerequisite" and plan.course_code:
        code = plan.course_code.replace("'", "''")
        if database.has("prerequisite", "code", "requires", "kind"):
            if database.has("course", "code", "name_th", "source_file", "page_number"):
                evidence = database.has("course_prerequisite_evidence", "code", "status", "source_file", "page_number", "printed_page_number")
                edge_status = "CASE WHEN p.requires IS NOT NULL THEN 'recorded_requirement' ELSE 'unknown' END"
                status = f"COALESCE(e.status, {edge_status})" if evidence else edge_status
                source = "COALESCE(e.source_file, p.source_file, c.source_file)" if evidence else "COALESCE(p.source_file,c.source_file)"
                page = "COALESCE(e.page_number, p.page_number, c.page_number)" if evidence else "COALESCE(p.page_number,c.page_number)"
                book = "e.printed_page_number" if evidence else "NULL"
                join = "LEFT JOIN course_prerequisite_evidence e ON e.code = c.code " if evidence else ""
                return (
                    f"SELECT c.code, c.name_th, p.requires, p.kind, COALESCE({status}, 'unknown') AS prerequisite_status, "
                    f"{source} AS source_file, {page} AS page_number, {book} AS printed_page_number "
                    "FROM course c LEFT JOIN prerequisite p ON p.code = c.code "
                    f"{join}WHERE c.code = '{code}'"
                )
            return (
                "SELECT code, requires, kind, source_file, page_number FROM prerequisite "
                f"WHERE code = '{code}'"
            )
        if database.has("courses", "course_code", "prerequisites"):
            return (
                "SELECT course_code AS code, prerequisites, 'unverified_legacy' AS prerequisite_status, source_file, page_number "
                f"FROM courses WHERE course_code = '{code}'"
            )
        return None

    return None
