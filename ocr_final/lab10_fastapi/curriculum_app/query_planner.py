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
    semesters: tuple[int, ...] = ()
    min_credits: int | None = None
    elective_only: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "year": self.year,
            "semester": self.semester,
            "course_code": self.course_code,
            "search_term": self.search_term,
            "compare": self.compare,
            "required_only": self.required_only,
            "semesters": self.semesters,
            "min_credits": self.min_credits,
            "elective_only": self.elective_only,
        }


def _extract_number(text: str, labels: tuple[str, ...]) -> int | None:
    numbers = _extract_numbers(text, labels)
    return numbers[0] if numbers else None


def _extract_numbers(text: str, labels: tuple[str, ...]) -> tuple[int, ...]:
    joined = "|".join(re.escape(label) for label in labels)
    words = {'หนึ่ง':1,'สอง':2,'สาม':3,'สี่':4,'ห้า':5,'หก':6}
    matches = re.findall(rf"(?:{joined})\s*(?:ที่\s*)?(\d+|{'|'.join(words)})",text,re.I)
    return tuple(dict.fromkeys(int(value) if value.isdigit() else words[value] for value in matches))


def normalize_course_name(value: str) -> str:
    """Normalize formatting and common Thai nominal variants, not arbitrary fuzzy matches."""
    value = re.sub(r'\s+', '', value).casefold()
    for word, number in (('หนึ่ง', '1'), ('สอง', '2'), ('สาม', '3'), ('สี่', '4'), ('ห้า', '5'), ('หก', '6')):
        value = re.sub(re.escape(word) + r'(?=$|กับ|และ|ต่อ|มี|ต้อง|เป็น)', number, value)
    for phrase in ('การเขียนโปรแกรม', 'การสร้างโปรแกรม', 'การโปรแกรม', 'เขียนโปรแกรม'):
        value = value.replace(phrase, 'โปรแกรม')
    return value


def meaningful_name(value: str) -> bool:
    value = value.strip()
    if value in {'เลือก', 'บังคับ', 'ทั้งหมด'}:
        return False
    return bool(value) and not re.match(r'^(?:ที่|ซึ่ง|ทุก|แต่ละ|เลือกที่|เลือกไม่|ไหน|อะไร|มีวิชา|ต้อง)', value)


def course_name_matches(value: str, term: str) -> bool:
    """Keep ordinal constraints while allowing omitted subject qualifiers.

    This returns candidates, not an asserted unique course or relationship.
    """
    name, needle = normalize_course_name(value), normalize_course_name(term)
    if not needle:
        return False
    ordinal = re.fullmatch(r'(.+?)(\d+)', needle)
    if not ordinal:
        return needle in name
    return ordinal[1] in name and bool(re.search(r'(?<!\d)' + re.escape(ordinal[2]) + r'$', name))


def _name_sql(column: str) -> str:
    return f"normalize_course_name({column})"


def _course_fields(database: DatabaseInfo) -> str:
    fields = 'code, name_th, name_en, credits, lecture_h, lab_h, self_h, source_file, page_number'
    pairs = []
    for table in ('plan_item', 'course_prerequisite_evidence', 'program_requirement'):
        if database.has(table, 'printed_page_number', 'source_file', 'page_number'):
            pairs.append(f'SELECT printed_page_number AS book_page FROM {table} '
                'WHERE source_file = course.source_file AND page_number = course.page_number '
                'AND printed_page_number > 0')
    # A folio is document/page metadata, not a plan placement or prerequisite fact.
    # Conflicting recorded pairs remain unknown rather than choosing an arbitrary MIN.
    locator = ('(SELECT CASE WHEN COUNT(DISTINCT book_page) = 1 THEN MIN(book_page) END '
               'FROM (' + ' UNION ALL '.join(pairs) + '))') if pairs else 'NULL'
    fields += ', ' + locator + ' AS printed_page_number'
    return fields


def detect_intent(question: str) -> QueryPlan:
    text = question.strip()
    lowered = text.casefold()
    year = _extract_number(text, ("ปี", "ชั้นปี", "year"))
    semester = _extract_number(text, ("เทอม", "ภาคการศึกษา", "ภาคเรียน", "ภาค", "semester"))
    code_match = re.search(r"(?<!\d)(\d{8})(?!\d)", text)
    code = code_match.group(1) if code_match else None
    compare = any(word in lowered for word in ("เปรียบเทียบ", "ต่างกัน", "compare", "versus", " vs "))
    required_only = bool(re.search(r'วิชาบังคับ(?!ก่อน)|required course|core course', lowered))
    elective_only = bool(re.search(r'วิชาเลือก|elective courses?', lowered))

    credit_words = ("หน่วยกิต", "credit")
    minimum = re.search(r'(?:หน่วยกิต|credits?)\s*(?:อย่างน้อย|ตั้งแต่|>=|at least)\s*(\d+)|(?:อย่างน้อย|at least)\s*(\d+)\s*(?:หน่วยกิต|credits?)',text,re.I)
    if minimum and year is not None:
        return QueryPlan('course_list',year,semester,compare=compare,required_only=required_only,
                         min_credits=int(minimum.group(1) or minimum.group(2)))
    total_words = ("รวมทั้งหมด", "ทั้งหมดกี่หน่วยกิต", "หน่วยกิตรวม", "total credit")
    course_count_words = ("กี่วิชา", "จำนวนวิชา", "how many course", "number of course")
    list_words = ("วิชาอะไร", "วิชาใด", "วิชาไหน", "วิชาเลือกอะไร", "วิชาบังคับอะไร", "รายวิชา", "แสดงรหัส", "รหัสทั้งหมด", "course list", "which course", "what course")
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
    if ('ฉบับเก่า' in text or 'ฉบับเดิม' in text) and ('ฉบับใหม่' in text or 'ฉบับปรับปรุง' in text):
        if re.search(r'เลือก.*อยู่.*(?:แทน|ใช้)', text):
            return QueryPlan('selection_clarification')
        return QueryPlan('version_fact_comparison', compare=True)
    if re.search(r'(?:ต่าง|เปรียบเทียบ|เทียบ).*แผน|แผน.*(?:ต่าง|เปรียบเทียบ|เทียบ)', text) and 'สหกิจ' in text:
        return QueryPlan('plans_comparison', year, semester, compare=True)
    topical = re.search(r'(?:อยากเรียน|สนใจเรียน|อยากรู้เรื่อง)\s*(.+?)\s*(?:มีวิชา|มีรายวิชา|มีอะไร|อะไรบ้าง)', text)
    if topical and meaningful_name(topical[1]):
        return QueryPlan('course_search', search_term=topical[1].strip(), compare=compare)

    if not code and 'วิชา' in text:
        name_match = re.search(r'วิชา\s*(.+?)\s*(?:มีวิชาบังคับก่อน|ต้องเรียนอะไรมาก่อน|มีรหัสอะไร|รหัสอะไร|มีรหัส|มีกี่หน่วยกิต|กี่หน่วยกิต|มีรายละเอียด|รายละเอียด)', text)
        if name_match and meaningful_name(name_match.group(1)):
            return QueryPlan('course_search', search_term=name_match.group(1).strip(), compare=compare)
    if any(word in lowered for word in prerequisite_words):
        if not code and re.search(r'วิชา(?:ที่|เลือก|ใด|ไหน|ทั้งหมด)|ทุกวิชา', text):
            return QueryPlan('prerequisite_catalog', search_term=text, compare=compare,
                             required_only=required_only, elective_only=elective_only)
        return QueryPlan("prerequisite", year, semester, code, compare=compare, required_only=required_only)
    if 'วิชาเลือก' in text and re.search(r'ช่อง|รหัสจริง|ทางเลือก|แบบบรรยาย|ปฏิบัติ', text):
        return QueryPlan('elective_slots', year, semester)
    if any(word in lowered for word in ('เกณฑ์การสำเร็จการศึกษา', 'เงื่อนไขจบ', 'เกณฑ์จบ', 'graduation requirements')):
        return QueryPlan('graduation_reference', compare=compare)
    if re.search(r'จบ\s*(?:ใน)?\s*(?:\d+(?:[.,]\d+)?|หนึ่ง|สอง|สาม|สี่|ห้า)\s*ปี|วางแผนจบ', text):
        return QueryPlan('study_feasibility', compare=compare)
    if year is not None and any(word in lowered for word in list_words) and not re.search(r'รวม|กี่หน่วยกิต|total|how many credits', lowered):
        return QueryPlan('course_list', year, semester, compare=compare,
                         required_only=required_only, elective_only=elective_only)
    if year is not None and semester is not None and any(word in lowered for word in credit_words):
        return QueryPlan("semester_credits", year, semester, compare=compare, required_only=required_only,
                         semesters=_extract_numbers(text,("เทอม","ภาคการศึกษา","ภาคเรียน","ภาค","semester")))
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
    focus = text.rsplit(':',1)[-1].strip() if text.startswith('หลักสูตร') and ':' in text else text
    if not code and (re.search(r'^(?:(?:ขอ|อยากทราบ|บอก|แสดง)\s*)?(?:ชื่อ|ข้อมูล|รายละเอียด)(?:ของ)?\s*(?:หลักสูตร|สาขา|ปริญญา)',focus)
                    or re.search(r'ชื่อ(?:ของ)?\s*(?:หลักสูตร|สาขา|ปริญญา)\s*(?:คือ|ว่า)?\s*อะไร',focus)
                    or re.search(r'(?:หลักสูตร|สาขา|ปริญญา)(?:นี้|\s+[A-Za-z][A-Za-z0-9-]*)?\s*(?:มี)?ชื่อ(?:ว่า)?อะไร|\bprogram name\b|\bdegree\b',focus,re.I)):
        return QueryPlan("program_info", compare=compare, required_only=required_only)
    if not code and "วิชา" in text and any(
        word in lowered for word in ("รหัสอะไร", "รหัสวิชา", "กี่หน่วยกิต", "รายละเอียด", "ข้อมูลวิชา")
    ):
        name_match = re.search(
            r"วิชา\s*(.+?)\s*(?:มีรหัสอะไร|รหัสอะไร|มีรหัส|มีกี่หน่วยกิต|กี่หน่วยกิต|มีรายละเอียด|รายละเอียด|$)",
            text,
            re.IGNORECASE,
        )
        if name_match and meaningful_name(name_match.group(1)):
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
    if len(plan.semesters) > 1:
        parts.append('semester IN ('+', '.join(str(s) for s in plan.semesters)+')')
    elif plan.semester is not None:
        parts.append(f"semester = {plan.semester}")
    if plan.min_credits is not None:
        parts.append(f'credits >= {plan.min_credits}')
    if include_required and plan.required_only:
        parts.append("(ctype LIKE '%บังคับ%' OR LOWER(ctype) LIKE '%required%')")
    return (" WHERE " + " AND ".join(parts)) if parts else ""


def _page_evidence(database: DatabaseInfo, where: str) -> str:
    """Keep PDF/printed folios together; separate GROUP_CONCATs lose pairing."""
    if not database.has('plan_item', 'source_file', 'page_number'):
        return ''
    book = 'printed_page_number' if database.has('plan_item', 'printed_page_number') else 'NULL'
    return (
        ", (SELECT JSON_GROUP_ARRAY(JSON_OBJECT('source_file', source_file, "
        "'page', page_number, 'book_page', book_page)) FROM "
        f"(SELECT DISTINCT source_file, page_number, {book} AS book_page "
        f"FROM plan_item{where})) AS page_evidence"
    )


def deterministic_sql(plan: QueryPlan, database: DatabaseInfo) -> str | None:
    """Return SQL only when the intent can be answered reliably from the real schema."""
    intent = plan.intent
    if (database.has('courses', 'course_code') and not database.has('courses', 'year', 'semester')
            and intent in {'semester_credits', 'year_credits'}):
        # A catalog without placement fields cannot answer a term/year total.
        # Empty evidence prevents model SQL from manufacturing placement.
        return 'SELECT course_code AS code FROM courses LIMIT 0'
    if intent in {'graduation_reference', 'study_feasibility'}:
        if database.has('program_requirement', 'rule_text', 'regulation_year', 'source_file', 'page_number', 'printed_page_number'):
            return ('SELECT r.rule_text, r.regulation_year, r.source_file, r.page_number, '
                    'r.printed_page_number, r.section, r.review_scope FROM program_requirement r '
                    'JOIN program p ON r.program_id=p.program_id AND r.curriculum_version=p.curriculum_version AND r.plan=p.plan '
                    "WHERE r.topic IN ('graduation_reference','graduation_rule_26')")
        # No source-reviewed rules: empty evidence, not a model-generated grant.
        if database.has('course', 'code'):
            return 'SELECT code FROM course LIMIT 0'
        if database.has('courses', 'course_code'):
            return 'SELECT course_code AS code FROM courses LIMIT 0'
        return None
    if intent == 'selection_clarification':
        return 'SELECT code FROM course LIMIT 0' if database.has('course','code') else 'SELECT course_code AS code FROM courses LIMIT 0'
    if intent == 'prerequisite_catalog':
        if database.has('prerequisite','code','requires','kind') and database.has('course','code','name_th'):
            scope = ''
            if plan.elective_only or plan.required_only:
                # Restrict relationships to explicit selected-plan classifications.
                # Missing classification is not proof of elective membership.
                if not database.has('plan_item', 'code', 'ctype'):
                    scope = ' WHERE 0'
                else:
                    thai, english = ('เลือก', 'elective') if plan.elective_only else ('บังคับ', 'required')
                    scope = (" WHERE EXISTS (SELECT 1 FROM plan_item pi WHERE pi.code=p.code "
                             f"AND (pi.ctype LIKE '%{thai}%' OR LOWER(pi.ctype) LIKE '%{english}%'))")
            return ('SELECT p.code,c.name_th,p.requires,p.kind,p.source_file,p.page_number '
                    'FROM prerequisite p JOIN course c ON p.code=c.code' + scope + ' ORDER BY p.code,p.requires')
        if plan.elective_only or plan.required_only:
            # Legacy catalogs lacking plan classifications cannot establish scope.
            return 'SELECT course_code AS code FROM courses LIMIT 0' if database.has('courses','course_code') else None
        return 'SELECT course_code AS code, prerequisites, source_file, page_number FROM courses' if database.has('courses','prerequisites') else None
    if intent in {"version_course_diff", 'version_fact_comparison'}:
        if database.has("v_plan", "code", "name_th", "credits"):
            where = " WHERE is_placeholder = 0" if database.has("v_plan", "is_placeholder") else ""
            return (
                "SELECT DISTINCT code, name_th, name_en, credits, source_file, page_number "
                f"FROM v_plan{where} ORDER BY code"
            )
        return 'SELECT course_code AS code FROM courses LIMIT 0' if database.has('courses', 'course_code') else None
    if intent == "program_total_credits":
        if database.has("program", "program_id", "total_credits"):
            book = ", printed_page_number" if database.has("program", "printed_page_number") else ""
            return f"SELECT program_id, total_credits, source_file, page_number{book} FROM program"
        if database.has("v_total_credits", "credits"):
            return "SELECT credits AS total_credits FROM v_total_credits"
        return None

    if intent == "program_years" and database.has("program", "program_id", "years"):
        book = ", printed_page_number" if database.has("program", "printed_page_number") else ""
        return f"SELECT program_id, years, source_file, page_number{book} FROM program"

    if intent == "program_info" and database.has("program", "program_id", "name_th"):
        fields = ["program_id", "name_th"]
        for column in ("name_en", "degree", "total_credits", "years", "source_file", "page_number", "printed_page_number"):
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
            fields += _page_evidence(database, ' WHERE year = v_semester_credits.year AND semester = v_semester_credits.semester')
            if database.has('plan_item','code','credits','alt_group','year','semester'):
                name = 'NULL'
                code = 'COALESCE(p.raw_code,p.code)' if database.has('plan_item', 'raw_code') else 'p.code'
                pattern = 'p.credits_raw' if database.has('plan_item', 'credits_raw') else 'NULL'
                join = ''
                if database.has('course', 'code', 'name_th', 'name_en'):
                    join = ' LEFT JOIN course c ON c.code=p.code'
                    name = 'COALESCE(c.name_th,c.name_en)'
                    if database.has('plan_item', 'name_th', 'name_en'):
                        name = 'COALESCE(p.name_th,p.name_en,c.name_th,c.name_en)'
                bundle = ''
                if database.has('plan_bundle_member','plan_item_id','bundle_id') and database.has('plan_bundle','bundle_id','year','semester','label'):
                    join += (' LEFT JOIN plan_bundle_member bm ON bm.plan_item_id=p.id'
                             ' LEFT JOIN plan_bundle b ON b.bundle_id=bm.bundle_id AND b.year=bm.year AND b.semester=bm.semester')
                    bundle = ',bm.bundle_id,b.label'
                fields += (f", (SELECT JSON_GROUP_ARRAY(JSON_ARRAY({code},p.credits,p.alt_group,{name},{pattern}{bundle})) "
                           f"FROM plan_item p{join} WHERE p.year=v_semester_credits.year AND p.semester=v_semester_credits.semester) AS calculation_rows")
            return f"SELECT {fields} FROM v_semester_credits{_conditions(plan)}"
        return None

    if intent == "year_credits":
        if database.has("v_year_credits", "year", "credits"):
            fields = "year, credits"
            if database.has("v_year_credits", "n_courses"):
                fields += ", n_courses"
            for column in ('source_files', 'source_pages', 'source_printed_pages'):
                if database.has('v_year_credits', column):
                    fields += ', ' + column
            fields += _page_evidence(database, ' WHERE year = v_year_credits.year')
            return f"SELECT {fields} FROM v_year_credits{_conditions(plan)}"
        if database.has("plan_item", "year", "credits"):
            return (
                "SELECT year, SUM(credits) AS credits, COUNT(*) AS n_courses "
                f"FROM plan_item{_conditions(plan)} GROUP BY year"
            )
        return None

    if intent == "course_count":
        if database.has('plan_bundle_member','plan_item_id') and database.has('v_semester_credits','n_courses') and not plan.required_only and not plan.elective_only:
            where = _conditions(plan)
            return ("SELECT SUM(n_courses) AS course_count,SUM(n_courses) AS n_courses, "
                    "GROUP_CONCAT(source_files) AS source_files,GROUP_CONCAT(source_pages) AS source_pages "
                    + _page_evidence(database,where) + ' FROM v_semester_credits' + where)
        if database.has("plan_item", "id", "year", "semester", "alt_group"):
            where = _conditions(plan, include_required=True)
            return (
                "SELECT COUNT(DISTINCT COALESCE(alt_group, 'row-' || id)) AS course_count, "
                "COUNT(DISTINCT COALESCE(alt_group, 'row-' || id)) AS n_courses, "
                "GROUP_CONCAT(DISTINCT source_file) AS source_files, "
                "GROUP_CONCAT(DISTINCT page_number) AS source_pages "
                + _page_evidence(database, where) + ' '
                +
                f"FROM plan_item{where}"
            )
        if database.has("courses", "id"):
            return "SELECT COUNT(*) AS course_count FROM courses"
        return None

    if intent in {"course_list", 'elective_slots', 'plans_comparison'}:
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
                elif (view == 'v_study_plan' and column in {'raw_code', 'code_pattern', 'is_placeholder', 'elective_type'}
                      and database.has(view, 'id') and database.has('plan_item', 'id', column)):
                    # Older evidence views omitted fidelity fields. Retrieve them
                    # by the same plan row ID, from SQLite only, without overlays.
                    fields.append(f'(SELECT pi.{column} FROM plan_item pi WHERE pi.id=v_study_plan.id) AS {column}')
            conditions = _conditions(plan, include_required=True)
            if plan.elective_only:
                if not database.has(view, 'ctype'):
                    return None
                conditions += (' AND ' if conditions else ' WHERE ') + "ctype IN ('เลือก','elective')"
            if intent == 'elective_slots':
                filters = ["code LIKE 'ELEC-%'", "LOWER(code) LIKE '%x%'"]
                if database.has(view, 'is_placeholder'):
                    filters.append('is_placeholder=1')
                if database.has(view, 'code_pattern'):
                    filters.append("LOWER(code_pattern) LIKE '%x%'")
                conditions += (' AND ' if conditions else ' WHERE ') + '('+' OR '.join(filters)+')'
            if intent == 'plans_comparison' and plan.year is None:
                conditions += (' AND ' if conditions else ' WHERE ') + 'year=(SELECT MAX(year) FROM plan_item)'
            return (
                f"SELECT {', '.join(fields)} FROM {view}"
                f"{conditions} ORDER BY year, semester, code"
            )
        if database.has("courses", "course_code", "course_name_th", "credits"):
            if plan.year is not None or intent != 'course_list':
                return 'SELECT course_code AS code FROM courses LIMIT 0'
            return (
                "SELECT course_code AS code, course_name_th AS name_th, "
                "course_name_en AS name_en, credits, source_file, page_number "
                "FROM courses WHERE course_code IS NOT NULL AND TRIM(course_code) <> '' ORDER BY course_code"
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
                membership = "CASE WHEN pi.code IS NULL THEN 0 ELSE 1 END" if database.has('plan_item','code') else "NULL"
                if database.has('plan_item','code'):
                    join += "LEFT JOIN (SELECT DISTINCT code FROM plan_item) pi ON pi.code=c.code "
                return (
                    f"SELECT c.code, c.name_th, p.requires, p.kind, {membership} AS in_selected_plan, COALESCE({status}, 'unknown') AS prerequisite_status, "
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
