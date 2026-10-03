"""Schema-aware multi-database curriculum question answering."""

from __future__ import annotations

import json
import logging
import re
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from types import ModuleType
from typing import Any

import requests

from .config import Settings
from .database import (
    DatabaseInfo,
    DatabaseRegistry,
    SqlValidationError,
    attach_source_metadata,
    execute_readonly,
    open_readonly,
)
from .query_planner import QueryPlan, detect_intent, deterministic_sql, normalize_course_name
from .study_plan import build_study_plan, study_plan_text
from .study_evidence import read_study_evidence


LOGGER = logging.getLogger("curriculum_app")

SQL_SCHEMA = {
    "type": "object",
    "properties": {"sql": {"type": "string"}},
    "required": ["sql"],
    "additionalProperties": False,
}
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}

CLAIM_SCHEMA = {
    'type': 'object', 'properties': {'claims': {'type': 'array', 'items': {
        'type': 'object', 'properties': {'row_index': {'type': 'integer'},
        'fields': {'type': 'array', 'items': {'type': 'string'}}},
        'required': ['row_index', 'fields'], 'additionalProperties': False}}},
    'required': ['claims'], 'additionalProperties': False,
}
FACT_LABELS = {'code': 'รหัสวิชา', 'name_th': 'ชื่อภาษาไทย', 'name_en': 'ชื่อภาษาอังกฤษ',
    'credits': 'หน่วยกิต', 'years': 'ระยะเวลาศึกษา (ปี)', 'total_credits': 'หน่วยกิตรวม',
    'year': 'ชั้นปี', 'semester': 'ภาคการศึกษา', 'requires': 'วิชาบังคับก่อน',
    'prerequisites': 'ข้อมูลวิชาบังคับก่อนที่บันทึก', 'description_th': 'คำอธิบายรายวิชา',
    'lecture_h': 'ชั่วโมงบรรยาย', 'lab_h': 'ชั่วโมงปฏิบัติ', 'self_h': 'ชั่วโมงศึกษาด้วยตนเอง',
    'credits_raw': 'รูปแบบหน่วยกิต', 'prerequisite_status': 'สถานะหลักฐานวิชาบังคับก่อน'}


def render_claims(rows, claims):
    """Model selects evidence references only; never values or unrestricted prose."""
    if not isinstance(claims, list) or not claims or len(claims) > 80: return None
    lines = []
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {'row_index', 'fields'}: return None
        index, fields = claim['row_index'], claim['fields']
        if type(index) is not int or not 0 <= index < min(len(rows),80): return None
        if not isinstance(fields,list) or not fields or any(not isinstance(f,str) or f not in FACT_LABELS or f not in rows[index] or rows[index][f] is None for f in fields): return None
        source = rows[index].get('_source', {}).get('curriculum_name')
        if not source: return None
        values = [f"{FACT_LABELS[f]}: {rows[index][f]}" for f in dict.fromkeys(fields)]
        lines.append(source + ' — ' + '; '.join(values))
    return '\n'.join(dict.fromkeys(lines))


def validate_unknown_projection(sql):
    """Accept stored fields only and prevent aliases from relabeling their meaning."""
    projection = re.match(r'\s*SELECT\s+(.*?)\s+FROM\b', sql, re.I | re.S)
    if not projection or re.search(r'\b(?:UNION|study_correction)\b', sql, re.I):
        raise SqlValidationError('Unknown intent requires a single stored-column SELECT')
    compatible = {'course_code': 'code', 'course_name_th': 'name_th', 'course_name_en': 'name_en'}
    for field in projection[1].split(','):
        token = field.strip()
        if re.fullmatch(r'(?:[A-Za-z_]\w*\.)?\*', token):
            continue
        match = re.fullmatch(r'(?:[A-Za-z_]\w*\.)?([A-Za-z_]\w*)(?:\s+(?:AS\s+)?([A-Za-z_]\w*))?', token, re.I)
        if not match:
            raise SqlValidationError('Unknown intent only permits stored-column projections, not invented literals/calculations')
        source, alias = match.groups()
        if alias and alias.casefold() not in {source.casefold(), compatible.get(source.casefold())}:
            raise SqlValidationError('Unknown intent cannot relabel a stored fact with an unrelated alias')


def normalize_redundant_program_filter(database, sql):
    """Remove only a proven tautology on the selected single-program database."""
    match = re.fullmatch(
        r"(\s*SELECT\s+.+?\s+FROM\s+program(?:\s+(?:AS\s+)?(?!WHERE\b)[A-Za-z_]\w*)?)"
        r"\s+WHERE\s+(.+?)"
        r"\s*((?:ORDER\s+BY|LIMIT)\b.*?)?\s*;?", sql, re.I | re.S)
    if not match or not database.has('program', 'program_id'):
        return sql
    identity = r'(?:[A-Za-z_]\w*\.)?(?:program_id|plan|curriculum_version|is_latest)'
    atom = identity + r"\s*(?:(?:=|LIKE)\s*(?:'(?:''|[^'])*'|-?\d+)|IS\s+(?:NOT\s+)?NULL)"
    residue = re.sub(atom, '', match[2], flags=re.I)
    if re.sub(r'\b(?:AND|OR|NOT)\b|[\s()]', '', residue, flags=re.I):
        return sql
    connection = open_readonly(database.path)
    try:
        ids = [row[0] for row in connection.execute('SELECT program_id FROM program LIMIT 2')]
    finally:
        connection.close()
    if len(ids) != 1:
        return sql
    for value in re.findall(r"\bprogram_id\s*=\s*'((?:''|[^'])*)'", match[2], re.I):
        if value.replace("''", "'") != ids[0]:
            return sql
    normalized = match[1] + (' ' + match[3] if match[3] else '')
    # The actual safe SELECTs must return the same nonempty stored values.
    # False predicates, invalid columns and unproven identity filters stay rejected.
    _, filtered = execute_readonly(database, sql, 2)
    _, unfiltered = execute_readonly(database, normalized, 2)
    return normalized if filtered and filtered == unfiltered else sql


def _clean_model_text(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("Model response must be text")
    cleaned = re.sub(
        r"<think\b[^>]*>.*?</think\s*>", "", text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    if re.search(r"<think\b", cleaned, flags=re.IGNORECASE):
        raise ValueError("Model response contains an unclosed <think> block")
    fenced = re.fullmatch(
        r"\s*```(?:json|sql)?\s*(.*?)\s*```\s*", cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return (fenced.group(1) if fenced else cleaned).strip()


def _parse_json_object(raw: str, schema: dict[str, Any]) -> dict[str, str]:
    text = _clean_model_text(raw)
    if not text:
        raise ValueError("Model returned an empty response")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = None
        decoder = json.JSONDecoder()
        for position, character in enumerate(text):
            if character != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(text[position:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                value = candidate
                break
    if not isinstance(value, dict):
        raise ValueError("Model did not return a valid JSON object")
    result: dict[str, str] = {}
    for key in schema.get("required", []):
        field = value.get(key)
        expected = schema.get('properties', {}).get(key, {}).get('type', 'string')
        if expected == 'array' and isinstance(field, list):
            result[key] = field
            continue
        if not isinstance(field, str) or not field.strip():
            raise ValueError(f"Model response requires a non-empty string field: {key}")
        result[key] = field.strip()
    return result


@dataclass
class QueryExecution:
    database: DatabaseInfo
    sql: str
    rows: list[dict[str, Any]]
    validation_columns: tuple[str, ...]
    repair_attempts: list[dict[str, str]]
    error: str | None = None

    def public(self) -> dict[str, Any]:
        return {
            **self.database.public_metadata(),
            "sql": self.sql,
            "validation": "passed" if not self.error else "failed",
            "referenced_columns": list(self.validation_columns),
            "row_count": len(self.rows),
            "repair_attempts": self.repair_attempts,
            "error": self.error,
            "schema_used": self.database.schema_text(),
        }


class QwenTextToSQL:
    """Orchestrates planning, database selection, SQL safety, repair, and summarization."""

    def __init__(self, config: Settings, lab8b: ModuleType):
        self.config = config
        self.lab8b = lab8b
        self._answer_cache: OrderedDict[tuple[object, ...], dict[str, Any]] = OrderedDict()

    def available(self) -> bool:
        try:
            return requests.get(f"{self.config.ollama_url}/api/tags", timeout=3).ok
        except requests.RequestException:
            return False

    @staticmethod
    def _version_diff(rows: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """Compute 2560-minus-2565 course sets in code, never in the LLM."""
        by_plan_version: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
        for row in rows:
            source = row.get("_source") or {}
            version = source.get("curriculum_version")
            plan = str(source.get("plan") or "both")
            code = row.get("code")
            if version not in {2560, 2565} or not code:
                continue
            by_plan_version.setdefault((plan, int(version)), {})[str(code)] = row

        lines: list[str] = []
        relevant: list[dict[str, Any]] = []
        plans = sorted({plan for plan, _version in by_plan_version})
        for plan in plans:
            old = by_plan_version.get((plan, 2560), {})
            revised = by_plan_version.get((plan, 2565), {})
            if not old or not revised:
                continue
            removed = sorted(set(old) - set(revised))
            label = {"coop": "แผนสหกิจ", "no-coop": "แผนไม่สหกิจ", "both": "ทั้งสองแผน"}.get(plan, plan)
            # Keep evidence from both versions so the response can cite the
            # compared 2560 and 2565 source pages, including an empty diff.
            relevant.extend([next(iter(old.values())), next(iter(revised.values()))])
            if not removed:
                lines.append(f"{label}: ไม่พบรายวิชาที่มีในฉบับ 2560 แต่ไม่มีในฉบับ 2565")
                continue
            courses = []
            for code in removed:
                row = old[code]
                if row not in relevant:
                    relevant.append(row)
                name = row.get("name_th") or row.get("name_en") or "ไม่ระบุชื่อ"
                courses.append(f"{code} {name}")
            lines.append(f"{label}: " + ", ".join(courses))

        if not lines:
            return (
                "ยังเปรียบเทียบไม่ได้ เพราะฐานข้อมูลต้องมีทั้งฉบับ 2560 และ 2565 "
                "ของแผนเดียวกัน",
                [],
            )
        return "รายวิชาที่มีในฉบับ 2560 แต่ไม่มีในฉบับ 2565 — " + "\n".join(lines), relevant

    def _chat(self, prompt: str, schema: dict[str, Any]) -> dict[str, str]:
        raw = self.lab8b.ollama_generate(
            prompt,
            fmt=schema,
            timeout=self.config.request_timeout,
            model=self.config.ollama_model,
            num_ctx=8192,
            num_predict=512,
        )
        return _parse_json_object(raw, schema)

    def make_sql(
        self,
        question: str,
        plan: QueryPlan,
        database: DatabaseInfo,
        *,
        previous_sql: str | None = None,
        error: str | None = None,
    ) -> str:
        repair = ""
        if previous_sql and error:
            repair = f"""
SQL ก่อนหน้านี้ใช้ไม่ได้: {previous_sql}
ข้อผิดพลาดจาก SQLite/validator: {error}
แก้ SQL โดยใช้เฉพาะ schema จริงด้านล่าง
"""
        if database.has('program', 'name_th', 'total_credits', 'years'):
            stored_hint = 'ข้อมูลหลักสูตรบันทึกใน program: SELECT name_th, name_en, total_credits, years, source_file, page_number FROM program ไม่ใส่ WHERE'
        elif database.has('courses', 'course_code', 'course_name_th', 'credits'):
            stored_hint = ('ฐานนี้ไม่มี program หรือข้อมูลปี/ยอดรวมหลักสูตร เป็น catalog ที่ยังไม่ระบุฉบับแน่ชัด '
                           'เลือกหลักฐานจริงได้ด้วย SELECT course_code AS code, course_name_th AS name_th, course_name_en AS name_en, credits, source_file, page_number FROM courses LIMIT 5 '
                           'ห้ามใช้ credits AS total_credits เพราะหน่วยกิตรายวิชาไม่ใช่ยอดรวมหลักสูตร')
        else:
            stored_hint = 'เลือกเฉพาะ column จริงตาม schema ไม่เปลี่ยนความหมายด้วย alias'
        prompt = f"""แปลงคำถามเป็น SQLite SQL สำหรับฐานข้อมูลเดียวนี้

ฐานข้อมูล: {database.curriculum_name}
แผนคำถามที่โปรแกรมตรวจพบ: {json.dumps(plan.as_dict(), ensure_ascii=False)}
schema จริง (ห้ามใช้ table หรือ column นอกเหนือจากนี้):
{database.schema_text()}
{repair}
กติกา:
- ตอบ JSON ที่มี key ชื่อ sql เท่านั้น
- ใช้ SELECT หรือ WITH เพียงคำสั่งเดียวและเป็น read-only
- ใช้เฉพาะ table, view และ column ที่ปรากฏใน schema จริง
- ห้ามสร้างเงื่อนไข year, semester, program หรือ course ที่ผู้ใช้ไม่ได้ระบุ
- ถ้าถามยอดรวมหลักสูตร ให้ใช้ program.total_credits เมื่อมี column นี้
- ถามจำนวนให้ใช้ COUNT และถามผลรวมให้ใช้ค่ารวมที่เหมาะสม
- อย่ารวมข้อมูลข้ามหลักสูตร ฐานข้อมูลนี้จะถูกรวมผลภายหลังโดยโปรแกรม
- ฐานข้อมูลถูกเลือกหลักสูตรและฉบับแล้ว ห้ามใส่ WHERE program_id และห้ามกรองตาราง program
- เมื่อ intent เป็น unknown ให้ SELECT เฉพาะ column ที่บันทึกจริง ห้าม COUNT, SUM, literal, CASE หรือคำนวณใน SELECT
- คำแนะนำจาก schema ของฐานนี้: {stored_hint}

คำถาม: {question}
"""
        return _clean_model_text(self._chat(prompt, SQL_SCHEMA)["sql"])

    def summarize(
        self,
        question: str,
        plan: QueryPlan,
        rows: list[dict[str, Any]],
        executions: list[QueryExecution],
    ) -> str:
        sources = [
            {
                "curriculum_name": item.database.curriculum_name,
                "source_folder": item.database.source_folder,
                "row_count": len(item.rows),
                "error": item.error,
            }
            for item in executions
        ]
        prompt = f"""เลือกเฉพาะหลักฐานฐานข้อมูลที่ตอบคำถามได้
คำถาม: {question}
intent: {plan.intent}
แหล่งข้อมูล: {json.dumps(sources, ensure_ascii=False)}
ผลฐานข้อมูล: {json.dumps(rows[:80], ensure_ascii=False)}

กติกา:
- ตอบ JSON key claims เป็นรายการ {{"row_index": เลขแถวเริ่มที่ 0, "fields": [ชื่อ field]}}
- ห้ามส่งค่าหรือข้อความคำตอบเอง ระบบจะแสดงค่าจากแถวที่อ้างเท่านั้น
- field ที่อนุญาต: {', '.join(FACT_LABELS)}
- ถ้าหลักฐานไม่พอให้ claims เป็น [] ห้ามเดาหรืออนุมานสิทธิ์ลงทะเบียน
- ถ้ามีหลายหลักสูตร ให้รายงานแยกตาม curriculum_name ห้ามบวกยอดข้ามหลักสูตร
- ถ้าเป็นคำถามเปรียบเทียบ ให้เปรียบเทียบเฉพาะค่าที่แสดง
- ถ้าไม่มีแถวข้อมูล ให้ตอบว่าไม่พบข้อมูลนี้ในฐานข้อมูลหลักสูตร
"""
        try:
            claims = self._chat(prompt, CLAIM_SCHEMA).get('claims')
        except (ValueError, json.JSONDecodeError):
            return self._insufficient(rows)
        return render_claims(rows, claims) or self._insufficient(rows)

    @staticmethod
    def _insufficient(rows):
        identities = sorted({str(r.get('_source', {}).get('curriculum_name', 'หลักสูตรที่เลือก')) for r in rows})
        return 'หลักฐานจาก SQLite ยังไม่พอที่จะยืนยันคำตอบนี้ใน ' + ', '.join(identities) + ' จึงไม่เพิ่มข้อมูลหรือสรุปเงื่อนไขที่ไม่ได้บันทึก'

    @staticmethod
    def _ground_answer(
        plan: QueryPlan, rows: list[dict[str, Any]], model_answer: str
    ) -> str:
        """Enforce values, completeness, and source identity in the final answer."""
        value_fields = {
            "program_total_credits": ("total_credits", "หน่วยกิต"),
            "semester_credits": ("credits", "หน่วยกิต"),
            "year_credits": ("credits", "หน่วยกิต"),
            "course_count": ("course_count", "วิชา"),
            "program_years": ("years", "ปี"),
        }
        field_and_unit = value_fields.get(plan.intent)
        if not rows:
            return model_answer
        if plan.intent == 'unknown':
            # Free text cannot be made safe by checking one number or marker.
            # Only the structured reference renderer in summarize may answer.
            return QwenTextToSQL._insufficient(rows)
        if plan.intent == "course_list":
            grouped: dict[str, list[dict[str, Any]]] = {}
            for row in rows:
                curriculum = str(row.get("_source", {}).get("curriculum_name", "หลักสูตร"))
                grouped.setdefault(curriculum, []).append(row)

            answers: list[str] = []
            for curriculum, curriculum_rows in grouped.items():
                fixed: list[str] = []
                placeholders: list[str] = []
                alternative_rows: dict[str, list[dict[str, Any]]] = {}
                ordinary_rows: list[dict[str, Any]] = []
                for row in curriculum_rows:
                    if row.get("alt_group"):
                        alternative_rows.setdefault(str(row["alt_group"]), []).append(row)
                    else:
                        ordinary_rows.append(row)

                def format_row(row: dict[str, Any], *, include_code: bool = True) -> str:
                    name_th = str(row.get("name_th") or row.get("name_en") or "ไม่ระบุชื่อ")
                    english = (
                        f" ({row['name_en']})"
                        if row.get("name_en") and row.get("name_en") != name_th else ""
                    )
                    credits = row.get("credits_raw") or row.get("credits")
                    credit_text = f", {credits} หน่วยกิต" if credits is not None else ""
                    code_text = f"{row.get('code')} " if include_code and row.get("code") else ""
                    return f"{code_text}{name_th}{english}{credit_text}"

                for row in ordinary_rows:
                    if row.get("is_placeholder"):
                        kind = str(row.get("elective_type") or "elective_slot")
                        kind_label = {
                            "free_elective": "วิชาเลือกเสรี (นักศึกษาเลือกจากรายวิชาที่หลักสูตรอนุญาต)",
                            "humanities_elective": "วิชาเลือกด้านมนุษยศาสตร์",
                            "social_science_elective": "วิชาเลือกด้านสังคมศาสตร์",
                            "language_elective": "วิชาเลือกด้านภาษา",
                            "science_math_elective": "วิชาเลือกด้านวิทยาศาสตร์และคณิตศาสตร์",
                            "major_elective": "วิชาเลือกในสาขา",
                            "unresolved_elective": "วิชาเลือกที่ต้องตรวจจากเล่มหลักสูตร",
                        }.get(kind, "วิชาเลือก")
                        placeholders.append(
                            f"{format_row(row, include_code=False)} — รหัสยังไม่กำหนด; "
                            f"เป็นสล็อต{kind_label}"
                        )
                    else:
                        fixed.append(format_row(row))

                for alternatives in alternative_rows.values():
                    alternatives.sort(key=lambda item: int(item.get("alternative_index") or 999))
                    target = placeholders if any(row.get("is_placeholder") for row in alternatives) else fixed
                    target.append("ตัวเลือกอย่างใดอย่างหนึ่ง: " + " หรือ ".join(
                        format_row(row, include_code=not bool(row.get("is_placeholder")))
                        for row in alternatives
                    ))

                sections = [f"{curriculum}:"]
                if fixed:
                    sections.append("รายวิชาที่กำหนด: " + "; ".join(fixed))
                if placeholders:
                    sections.append("สล็อตวิชาเลือก: " + "; ".join(placeholders))
                answers.append("\n".join(sections))
            return "\n".join(answers)

        if plan.intent == "prerequisite":
            answers = []
            for row in rows:
                curriculum = row.get("_source", {}).get("curriculum_name", "หลักสูตรที่เลือก")
                code = row.get("code")
                status = row.get("prerequisite_status", "unknown")
                requirement = row.get("requires") or row.get("prerequisites")
                if status == "explicit_none":
                    fact = "เอกสารระบุว่าไม่มีวิชาบังคับก่อน"
                elif requirement and status in {"required", "recorded_requirement"}:
                    fact = f"วิชาบังคับก่อนที่ระบุคือ {requirement}"
                else:
                    fact = "มีรายวิชานี้ในฐานข้อมูล แต่ข้อมูลวิชาบังคับก่อนยังไม่ยืนยันจากคำอธิบายรายวิชาในเล่มหลักสูตร"
                answers.append(f"{curriculum}: วิชา {code} — {fact}")
            answers.append("ยังสรุปไม่ได้ว่าสามารถลงทะเบียนเมื่อยังไม่ผ่านวิชาบังคับก่อนได้หรือไม่ เพราะยังไม่มีหลักฐานข้อยกเว้นการลงทะเบียนที่ตรวจยืนยัน ต้องตรวจข้อบังคับหรือสอบถามฝ่ายทะเบียน")
            return "\n".join(dict.fromkeys(answers))

        if plan.intent in {"course_detail", "course_search"}:
            if plan.intent == 'course_search' and len({row.get('code') for row in rows}) > 1:
                candidates = '\n'.join(dict.fromkeys(
                    f"{row.get('_source', {}).get('curriculum_name', 'หลักสูตร')}: {row.get('code')} {row.get('name_th') or row.get('name_en')}"
                    for row in rows))
                return f"พบหลายรายวิชาที่ตรงกับชื่อที่ค้น โปรดระบุรหัสวิชาที่ต้องการก่อนตอบรายละเอียด:\n{candidates}"
            expected = {
                str(value)
                for row in rows
                for key, value in row.items()
                if key in {"code", "requires"} and value
            }
            curricula = {
                str(row.get("_source", {}).get("curriculum_name"))
                for row in rows if row.get("_source", {}).get("curriculum_name")
            }
            if (
                expected
                and all(value in model_answer for value in expected)
                and (
                    len(curricula) <= 1
                    or all(name.casefold() in model_answer.casefold() for name in curricula)
                )
            ):
                return model_answer
            formatted: list[str] = []
            for row in rows:
                source = row.get("_source", {})
                curriculum = source.get("curriculum_name", "หลักสูตร")
                citation = ""
                if row.get("source_file") and row.get("page_number") is not None:
                    citation = f" (ที่มา: {row['source_file']} หน้า {row['page_number']})"
                if plan.intent == "prerequisite":
                    requirement = row.get("requires") or row.get("prerequisites") or "ไม่ระบุ"
                    formatted.append(f"{curriculum}: วิชา {row.get('code')} ต้องผ่าน {requirement}{citation}")
                    continue
                name = row.get("name_th") or row.get("name_en") or "ไม่ระบุชื่อ"
                english = f" ({row['name_en']})" if row.get("name_en") else ""
                credits = f", {row['credits']} หน่วยกิต" if row.get("credits") is not None else ""
                hours = ""
                if any(row.get(key) is not None for key in ("lecture_h", "lab_h", "self_h")):
                    hours = (
                        f", L-P-S {row.get('lecture_h', '-')}-"
                        f"{row.get('lab_h', '-')}-{row.get('self_h', '-')}"
                    )
                formatted.append(
                    f"{curriculum}: {row.get('code', 'ไม่ระบุรหัส')} {name}{english}{credits}{hours}{citation}"
                )
            return "\n".join(formatted)

        if plan.intent == "program_info":
            expected_names = {
                str(row.get("name_th") or row.get("name_en") or row.get("program_id"))
                for row in rows
            }
            if expected_names and all(name in model_answer for name in expected_names):
                return model_answer
            return "; ".join(
                f"{row.get('program_id')}: {row.get('name_th') or row.get('name_en') or 'ไม่ระบุชื่อ'}"
                + (
                    f" (ที่มา: {row.get('source_file')} หน้า {row.get('page_number')})"
                    if row.get("source_file") and row.get("page_number") is not None else ""
                )
                for row in rows
            )

        if not field_and_unit:
            curricula = {
                str(row.get("_source", {}).get("curriculum_name"))
                for row in rows if row.get("_source", {}).get("curriculum_name")
            }
            if len(curricula) <= 1 or all(
                name.casefold() in model_answer.casefold() for name in curricula
            ):
                return model_answer
            return "; ".join(
                f"{row.get('_source', {}).get('curriculum_name', 'หลักสูตร')}: "
                + ", ".join(
                    f"{key}={value}" for key, value in row.items()
                    if key != "_source" and value is not None
                )
                for row in rows
            )
        field, unit = field_and_unit
        usable = [row for row in rows if row.get(field) is not None]
        if not usable:
            return model_answer

        # A single terse answer is acceptable only if it contains the grounded value.
        if len(usable) == 1:
            value = str(usable[0][field])
            if value in model_answer and unit in model_answer:
                return model_answer
        else:
            names = [str(row.get("_source", {}).get("curriculum_name", "")) for row in usable]
            if all(name and name.casefold() in model_answer.casefold() for name in names):
                return model_answer

        parts: list[str] = []
        for row in usable:
            source = row.get("_source", {})
            curriculum = source.get("curriculum_name", "หลักสูตร")
            citation = ""
            if row.get("source_file") and row.get("page_number") is not None:
                citation = f" (ที่มา: {row['source_file']} หน้า {row['page_number']})"
            elif row.get("source_files") or row.get("source_pages"):
                source_files = row.get("source_files") or "เอกสารหลักสูตร"
                source_pages = row.get("source_pages")
                citation = f" (ที่มา: {source_files}{f' หน้า {source_pages}' if source_pages else ''})"
            parts.append(f"{curriculum}: {row[field]} {unit}{citation}")
        return "; ".join(parts)

    def _execute_one(
        self, question: str, plan: QueryPlan, database: DatabaseInfo,
        *, resolved_course_code: str | None = None,
    ) -> QueryExecution:
        sql = deterministic_sql(plan, database)
        repairs: list[dict[str, str]] = []
        if sql is None:
            sql = self.make_sql(question, plan, database)

        for attempt in range(self.config.sql_repair_attempts + 1):
            try:
                if plan.intent == 'unknown':
                    validate_unknown_projection(sql)
                    sql = normalize_redundant_program_filter(database, sql)
                self._validate_plan_filters(question, plan, database, sql,resolved_course_code=resolved_course_code)
                validation, raw_rows = execute_readonly(database, sql, self.config.max_rows)
                if plan.intent == 'course_search':
                    literal_term = re.sub(r'\s+', '', plan.search_term or '').casefold()
                    literal = [row for row in raw_rows if any(literal_term in re.sub(r'\s+', '',str(row.get(key) or '')).casefold() for key in ('name_th','name_en'))]
                    raw_rows = literal or raw_rows
                    exact = [row for row in raw_rows if any(
                        normalize_course_name(str(row.get(key) or '')) == normalize_course_name(plan.search_term or '')
                        for key in ('name_th', 'name_en'))]
                    raw_rows = exact or raw_rows
                return QueryExecution(
                    database=database,
                    sql=validation.sql,
                    rows=attach_source_metadata(raw_rows, database),
                    validation_columns=validation.referenced_columns,
                    repair_attempts=repairs,
                )
            except SqlValidationError as exc:
                error = str(exc)
                repairs.append({"sql": sql, "error": error})
                LOGGER.warning(
                    "SQL rejected curriculum=%s attempt=%s sql=%r error=%s",
                    database.curriculum_name, attempt + 1, sql, error,
                )
                if attempt >= self.config.sql_repair_attempts:
                    return QueryExecution(database, sql, [], (), repairs, error)
                # A deterministic query failing indicates a schema edge case; the real
                # schema and SQLite error are then handed to Qwen for bounded repair.
                sql = self.make_sql(
                    question, plan, database, previous_sql=sql, error=error
                )
        raise AssertionError("unreachable SQL repair loop")

    @staticmethod
    def _validate_plan_filters(
        question: str, plan: QueryPlan, database: DatabaseInfo, sql: str,
        resolved_course_code: str | None = None,
    ) -> None:
        """Reject filters that contradict or exceed the detected user constraints."""
        where = re.search(r"\bwhere\b(.*?)(?:\bgroup\b|\border\b|\blimit\b|$)", sql, re.I | re.S)
        where_text = where.group(1) if where else ""
        # ESCAPE is syntax, not an invented user filter. Only permit our fixed
        # escape character; keep the ordinary literal guard intact.
        where_text = re.sub(r"\bESCAPE\s+'\\'", '', where_text, flags=re.I)
        if plan.year is None and re.search(r"\byear\s*(?:=|<|>|\bin\b|\bbetween\b)", where_text, re.I):
            raise SqlValidationError("SQL added a year filter that the user did not request")
        if plan.semester is None and re.search(
            r"\bsemester\s*(?:=|<|>|\bin\b|\bbetween\b)", where_text, re.I
        ):
            raise SqlValidationError("SQL added a semester filter that the user did not request")
        if where and re.search(r"\bfrom\s+program\b", sql, re.I):
            raise SqlValidationError(
                "The selected database contains one program row; filtering program is redundant"
            )
        allowed_constants = {"pre", "corequisite"}
        # Only the internal, database-backed name resolver can authorize this
        # code. Do not exempt arbitrary plan/model-added course literals.
        if resolved_course_code == plan.course_code and re.fullmatch(r'\d{8}',resolved_course_code or ''):
            allowed_constants.add(resolved_course_code.casefold())
        if plan.required_only:
            # This is a deterministic synonym expansion from the explicit
            # Thai/English "required course" intent, not a model-added filter.
            allowed_constants.add("required")
        for literal in re.findall(r"'((?:''|[^'])*)'", where_text):
            if plan.intent == 'course_search' and plan.search_term:
                pattern = '%' + normalize_course_name(plan.search_term).replace('%', '\\%').replace('_', '\\_') + '%'
                if literal.replace("''", "'") == pattern:
                    continue
            value = literal.replace("''", "'").strip("% ")
            if not value or value.casefold() in allowed_constants:
                continue
            if value.casefold() not in question.casefold():
                raise SqlValidationError(
                    f"SQL added a filter value not present in the question: {value!r}"
                )
        for identifier in re.findall(
            r"\bprogram_id\s*=\s*'((?:''|[^'])*)'", sql, re.I
        ):
            actual = database.program_id
            if actual and identifier.replace("''", "'").casefold() != actual.casefold():
                raise SqlValidationError(
                    f"SQL filtered program_id={identifier!r}, but this database contains {actual!r}"
                )

    def ask(self, registry: DatabaseRegistry, question: str) -> dict[str, Any]:
        started = time.perf_counter()
        registry.refresh()
        fingerprint = tuple(
            (str(item.path), item.path.stat().st_mtime_ns, item.path.stat().st_size,
             (item.path.with_name(item.path.name+'-wal').stat().st_mtime_ns if item.path.with_name(item.path.name+'-wal').exists() else None))
            for item in registry.databases if item.path.is_file()
        )
        cache_key: tuple[object, ...] = (question.strip().casefold(), fingerprint)
        cached = self._answer_cache.get(cache_key)
        if cached is not None:
            self._answer_cache.move_to_end(cache_key)
            result = deepcopy(cached)
            result['cache_hit'] = True
            if result.get('debug'):
                result['debug']['timing_ms'] = {'total': round((time.perf_counter() - started) * 1000, 2)}
                result['debug']['cache_hit'] = True
            return result
        plan = detect_intent(question)
        include_legacy = plan.intent in {"course_detail", "course_search", "prerequisite"}
        selected = registry.select(question, include_legacy=include_legacy)
        if not selected:
            raise ValueError("ไม่พบฐานข้อมูลหลักสูตรที่ตรงกับคำถาม")
        planned = time.perf_counter()

        LOGGER.info("question=%r intent=%s", question, plan.as_dict())
        LOGGER.info(
            "discovered=%s selected=%s",
            [item.relative_path for item in registry.databases],
            [item.relative_path for item in selected],
        )
        executions = [self._execute_one(question, plan, database) for database in selected]
        if plan.intent == 'course_search' and any(word in question.casefold() for word in ('วิชาบังคับก่อน', 'prerequisite', 'ต้องเรียนอะไรมาก่อน')):
            codes = {row.get('code') for execution in executions for row in execution.rows}
            if len(codes) == 1:
                plan = QueryPlan('prerequisite', course_code=next(iter(codes)))
                executions = [self._execute_one(question, plan, database, resolved_course_code=plan.course_code) for database in selected]
        rows = [row for execution in executions for row in execution.rows]
        retrieved = time.perf_counter()
        LOGGER.info(
            "executions=%s",
            [
                {
                    "curriculum": execution.database.curriculum_name,
                    "sql": execution.sql,
                    "rows": execution.rows,
                    "error": execution.error,
                    "repairs": execution.repair_attempts,
                }
                for execution in executions
            ],
        )
        if not rows and all(execution.error for execution in executions):
            errors = "; ".join(
                f"{execution.database.curriculum_name}: {execution.error}"
                for execution in executions
            )
            raise ValueError(f"ไม่สามารถค้นฐานข้อมูลได้: {errors}")

        study_plan = None
        if rows and plan.intent == 'course_list':
            evidence = {item.database.curriculum_name: read_study_evidence(item.database) for item in executions}
            study_plan, rows = build_study_plan(rows, question, evidence, required_only=plan.required_only)
            answer = study_plan_text(study_plan)
        elif rows and plan.intent == "version_course_diff":
            answer, rows = self._version_diff(rows)
        elif rows and plan.intent != "unknown":
            # Structured intents are rendered from database rows directly.
            # Qwen is reserved for genuinely ambiguous questions, which keeps
            # numbers deterministic and removes avoidable generation latency.
            answer = self._ground_answer(plan, rows, "")
        elif rows:
            answer = self.summarize(question, plan, rows, executions)
        else:
            searched = ", ".join(item.curriculum_name for item in selected)
            answer = f"ยังยืนยันข้อมูลที่ถามไม่ได้จากฐานข้อมูลที่ค้น: {searched} ข้อมูลที่นำเข้าอาจไม่ครบ จึงยังสรุปไม่ได้ว่ารายวิชาหรือเงื่อนไขนี้ไม่มีในเล่มหลักสูตร"
        formatted = time.perf_counter()
        sql_map = {
            execution.database.curriculum_name: execution.sql for execution in executions
        }
        debug = {
            "question": question,
            "intent": plan.as_dict(),
            "discovered_databases": [item.public_metadata() for item in registry.databases],
            "selected_databases": [item.public_metadata() for item in selected],
            "queries": [execution.public() for execution in executions],
            "raw_rows": rows,
            "final_context": rows[:80],
            "timing_ms": {
                "query_parse_and_selection": round((planned - started) * 1000, 2),
                "sql_retrieval": round((retrieved - planned) * 1000, 2),
                "generation_and_formatting": round((formatted - retrieved) * 1000, 2),
                "total": round((formatted - started) * 1000, 2),
            },
        }
        result = {
            "study_plan": study_plan,
            "cache_hit": False,
            "question": question,
            "intent": plan.intent,
            "selected_curricula": [item.curriculum_name for item in selected],
            "sql": next(iter(sql_map.values())) if len(sql_map) == 1 else json.dumps(sql_map, ensure_ascii=False),
            "queries": [execution.public() for execution in executions],
            "rows": rows,
            "answer": answer,
            "debug": debug if self.config.debug else None,
        }
        self._answer_cache[cache_key] = deepcopy(result)
        self._answer_cache.move_to_end(cache_key)
        while len(self._answer_cache) > 128:
            self._answer_cache.popitem(last=False)
        return result
