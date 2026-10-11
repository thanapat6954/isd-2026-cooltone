"""Schema-aware multi-database curriculum question answering."""

from __future__ import annotations

import json
import logging
import re
import time
from collections import OrderedDict
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field
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
from .request_budget import REQUEST_DEADLINE, check_deadline
from .sql_parameters import BoundSQL, constraint_sql
from .query_planner import meaningful_name

MODEL_CALLS = ContextVar('curriculum_model_calls', default=0)


LOGGER = logging.getLogger("curriculum_app")


class ModelUnavailableError(requests.RequestException):
    """The service exists but the configured model is missing."""

SQL_SCHEMA = {
    "type": "object",
    "properties": {"sql": {"type": "string"}, "parameters": {"anyOf": [
        {"type": "array", "items": {"type": ["string", "number", "boolean", "null"]}},
        {"type": "object", "additionalProperties": {"type": ["string", "number", "boolean", "null"]}}
    ]}},
    "required": ["sql"],
    "additionalProperties": False,
}
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}
SEARCH_SCHEMA = {
    'type': 'object', 'properties': {'terms': {'type': 'array', 'maxItems': 8,
        'items': {'type': 'string'}}}, 'required': ['terms'], 'additionalProperties': False,
}


def literal_search_terms(question, terms):
    """Only accept literal user spans, not model-invented factual filters."""
    if not isinstance(terms, list):
        return []
    terms = [re.sub(r'^(?:(?:อธิบาย|เนื้อหา|คำอธิบาย|วิชา|รายวิชา|เกี่ยวกับ)\s*)+', '', term.strip())
             for term in terms[:8] if isinstance(term, str)]
    terms = [re.sub(r'(?:ต่อกัน|มีพรีรีเคว|มีวิชาบังคับก่อน|ต้องเรียนก่อน).*$', '', term).strip() for term in terms]
    return list(dict.fromkeys(term.strip() for term in terms[:8]
        if isinstance(term, str) and 2 <= len(term.strip()) <= 100
        and term.strip().casefold() in question.casefold()
        and not re.search(r'หลักสูตร|สหกิจ|ความสัมพันธ์|พรีรีเคว|prereq|^อธิบาย|\b(?:256\d|curriculum|relationship)\b', term, re.I)
        and not re.fullmatch(r'\d{4}', term.strip())))


def literal_course_mentions(question):
    """Extract explicit name spans; database matching supplies candidate identity."""
    spans = re.findall(r'(?:รายวิชา|วิชา)\s*(.+?)(?=ต่อกัน|สัมพันธ์|เกี่ยวข้อง|มีกี่|กี่หน่วยกิต|มีพรีรีเคว|มีวิชาบังคับก่อน|ต้องเรียน|[?？]|$)', question)
    mentions = []
    for span in spans:
        for part in re.split(r'กับ|และ', span):
            part = part.strip()
            if meaningful_name(part) and not re.search(r'^(?:เลือก|บังคับ|เรียน|ชื่อ|ในหลักสูตร)', part):
                mentions.append(part)
    return literal_search_terms(question, mentions)


def relationship_coverage_gap(rows, selected):
    """Do not silently omit an evidence-empty plan from a multi-plan answer."""
    supported = {row.get('_source', {}).get('curriculum_name') for row in rows if row.get('requires')}
    missing = [item.curriculum_name for item in selected if item.curriculum_name not in supported]
    if supported and missing:
        return '\nยังไม่มีหลักฐานความสัมพันธ์ที่ตรงคำถามในผลที่ค้นจาก: ' + ', '.join(missing) + '; ไม่อนุมานว่าไม่มีวิชาบังคับก่อน และคำตอบข้างต้นไม่ครอบคลุมแผนเหล่านี้'
    return ''

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
    'credits_raw': 'รูปแบบหน่วยกิต', 'kind': 'ประเภทความสัมพันธ์ที่บันทึก', 'prerequisite_status': 'สถานะหลักฐานวิชาบังคับก่อน',
    'rule_text': 'ข้อกำหนดที่ตรวจจากเล่ม', 'regulation_year': 'ปีของข้อบังคับที่อ้าง'}


def fallback_evidence_need(question):
    """Identify required evidence types, never supply curriculum facts."""
    if re.search(r'หัวข้อสอบ|ข้อสอบ|exam topics?|assessment questions?|(?:เทอมหน้า|ภาคเรียนหน้า|next (?:term|semester)).*(?:สอน|ภาษา|teach)|(?:สอน|ภาษา).*(?:เทอมหน้า|ภาคเรียนหน้า|next (?:term|semester))', question, re.I):
        return 'teaching_assessment'
    if re.search(r'ความสัมพันธ์|เกี่ยวข้อง|เชื่อมโยง|สัมพันธ์|ต่อกัน|พรีรีเคว(?:สิท|ซิท)|relationship|relat(?:ed|ion)|prereq', question, re.I):
        return 'relationship'
    if re.search(r'รับรอง|ลงทะเบียน|เปิดสอน|จบได้|จบภายใน|guarantee|registration|offered', question, re.I):
        return 'planning_conditions'
    if re.search(r'เนื้อหา|คำอธิบาย|เรียนเกี่ยวกับ|เรียนอะไร|description|content|อธิบาย', question, re.I):
        return 'description'
    return None


def literal_database_names(question, database):
    """Recover explicitly named subjects even if topic generation drops one."""
    if not database.has('course', 'name_th', 'name_en'):
        return []
    literal = question.replace("'", "''")
    terms = []
    for column in ('name_th', 'name_en'):
        sql = (f"SELECT {column} FROM course WHERE LENGTH({column}) >= 3 "
               f"AND INSTR(LOWER('{literal}'), LOWER({column})) > 0")
        _, records = execute_readonly(database, sql, 100)
        terms.extend(row[column] for row in records)
    return list(dict.fromkeys(terms))


def relationship_sql(course_sql, *, paired_pages=False):
    """Require both endpoints to match the already validated subject retrieval."""
    match = re.search(r'\bFROM course WHERE (.*?)(?:\s+LIMIT \d+)?\s*$', course_sql, re.I | re.S)
    if not match:
        return None
    candidates = 'SELECT code FROM course WHERE ' + match[1]
    if paired_pages:
        return ('SELECT p.code, p.requires, p.kind, p.source_file, p.page_number, e.printed_page_number '
                'FROM prerequisite p LEFT JOIN course_prerequisite_evidence e ON p.code=e.code '
                'AND p.source_file=e.source_file AND p.page_number=e.page_number '
                f'WHERE p.code IN ({candidates}) AND p.requires IN ({candidates})')
    return ('SELECT code, requires, kind, source_file, page_number FROM prerequisite '
            f'WHERE code IN ({candidates}) AND requires IN ({candidates})')


def fallback_gap(question, rows, claims):
    """Reject evidence-type substitution even when all selected values are real."""
    need = fallback_evidence_need(question)
    if not need:
        return None
    if need == 'teaching_assessment':
        return 'ฐานข้อมูลหลักสูตรที่เลือกไม่มีหลักฐานหัวข้อสอบหรือแผนการสอนของอาจารย์ในภาคเรียนที่ถาม; ชื่อวิชา คำอธิบายหลักสูตร และหน่วยกิตไม่ยืนยันข้อมูลนี้'
    if need == 'planning_conditions':
        return 'ยังรับรองการลงทะเบียนหรือการจบตามเวลาที่ขอไม่ได้: ผลที่ดึงจาก SQLite ไม่มีข้อมูลยืนยันครบทั้งการเปิดรายวิชาในเทอมที่ต้องการ ผลการเรียนรายบุคคล และเงื่อนไขอนุญาตลงทะเบียน; ข้อกำหนดหลักสูตรที่มีไม่ใช่การรับรองสิทธิ์รายบุคคล'
    selected = []
    if isinstance(claims, list):
        for claim in claims:
            if isinstance(claim, dict) and type(claim.get('row_index')) is int and 0 <= claim['row_index'] < len(rows):
                row = rows[claim['row_index']]
                selected.extend((field, row.get(field)) for field in claim.get('fields', []) if isinstance(field, str))
    if need == 'relationship':
        # Descriptions alone do not establish a formally stated relationship.
        if not any(field in {'requires', 'prerequisites'} and value for field, value in selected):
            return 'ไม่มีหลักฐานความสัมพันธ์ระหว่างรายวิชาที่บันทึกไว้ในผลที่ดึงจาก SQLite; คำอธิบายหรือยอดรวมหลักสูตรเพียงอย่างเดียวไม่ยืนยันความสัมพันธ์'
    elif not any(field == 'description_th' and value for field, value in selected):
        return 'ผลที่ดึงจาก SQLite ไม่มีคำอธิบายรายวิชาที่ใช้ตอบคำถามเนื้อหา; ชื่อวิชา หน่วยกิต และระยะเวลาหลักสูตรไม่ทดแทนข้อมูลนี้'
    return None


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


def _parse_json_object(raw: str, schema: dict[str, Any]) -> dict[str, Any]:
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
    result: dict[str, Any] = {}
    for key in schema.get("required", []):
        field = value.get(key)
        expected = schema.get('properties', {}).get(key, {}).get('type', 'string')
        if expected == 'array' and isinstance(field, list):
            result[key] = field
            continue
        if not isinstance(field, str) or not field.strip():
            raise ValueError(f"Model response requires a non-empty string field: {key}")
        result[key] = field.strip()
    for key, definition in schema.get('properties', {}).items():
        if key in result or key not in value:
            continue
        field = value[key]
        permitted = {option.get('type') for option in definition.get('anyOf', [])}
        if permitted == {'array', 'object'} and isinstance(field, (list, dict)):
            result[key] = field
        elif definition.get('type') == 'string' and isinstance(field, str):
            result[key] = field
        else:
            raise ValueError(f'Model returned an invalid optional field: {key}')
    return result


@dataclass
class QueryExecution:
    database: DatabaseInfo
    sql: str
    rows: list[dict[str, Any]]
    validation_columns: tuple[str, ...]
    repair_attempts: list[dict[str, str]]
    error: str | None = None
    citation_queries: list[dict[str, Any]] = field(default_factory=list)
    parameters: Any = field(default_factory=tuple)

    def public(self) -> dict[str, Any]:
        return {
            'citation_queries': self.citation_queries,
            **self.database.public_metadata(),
            "sql": self.sql,
            "parameters": self.parameters,
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
            response = requests.get(f"{self.config.ollama_url}/api/tags", timeout=3)
            response.raise_for_status()
            models = response.json().get('models', [])
            if not isinstance(models, list):
                return False
            expected = self.config.ollama_model
            expected = expected if ':' in expected else expected + ':latest'
            return any(item.get('name', item.get('model')) == expected for item in models if isinstance(item, dict))
        except (requests.RequestException, ValueError, AttributeError):
            return False

    @staticmethod
    def _version_facts(rows):
        groups = {}
        for row in rows:
            source = row.get('_source') or {}
            code = str(row.get('code') or '')
            if not re.fullmatch(r'\d{8}', code):
                continue
            key = (str(source.get('program_id') or '').split('-')[0].casefold(), source.get('plan'))
            groups.setdefault(key, {}).setdefault(source.get('curriculum_version'), {}).setdefault(code, []).append(row)
        lines, evidence, compared = [], [], 0
        for versions in groups.values():
            years = sorted(v for v in versions if type(v) is int)
            if len(years) < 2:
                continue
            old, new = years[0], years[-1]
            common = sorted(set(versions[old]) & set(versions[new]))
            compared += len(common)
            for code in common:
                before, after = versions[old][code], versions[new][code]
                values = lambda records: sorted({(str(r.get('name_en') or ''), str(r.get('credits_raw') or r.get('credits'))) for r in records})
                if values(before) != values(after):
                    lines.append(f"{code}: {before[0].get('_source', {}).get('curriculum_name')} {values(before)} → {after[0].get('_source', {}).get('curriculum_name')} {values(after)}")
                    evidence.extend(before + after)
            if common and not evidence:
                evidence.extend(versions[old][common[0]] + versions[new][common[0]])
        if not compared:
            return 'ยังเปรียบเทียบไม่ได้: ต้องมีรหัสวิชาตรงกันจากทั้งสองฉบับของหลักสูตรและแผนเดียวกันใน SQLite', rows
        return '\n'.join(lines or ['ไม่พบความต่างของชื่ออังกฤษและหน่วยกิตในรหัสที่ตรงกันที่ค้นได้']) + f'\nตรวจเทียบ {compared} รหัสในข้อมูลที่นำเข้า ไม่ใช่การยืนยันความครบถ้วนของทั้งเล่ม', evidence

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
        deadline = REQUEST_DEADLINE.get()
        remaining = self.config.request_timeout if deadline is None else deadline - time.perf_counter()
        if remaining <= 0:
            raise TimeoutError('หมดเวลาประมวลผลคำถาม ไม่สามารถยืนยันคำตอบได้')
        try:
            MODEL_CALLS.set(MODEL_CALLS.get() + 1)
            raw = self.lab8b.ollama_generate(
            prompt,
            fmt=schema,
            timeout=min(self.config.request_timeout, remaining),
            model=self.config.ollama_model,
            num_ctx=8192,
            num_predict=512,
            )
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                raise ModelUnavailableError(f'ไม่พบ model {self.config.ollama_model} ใน Ollama; ตรวจ ollama list และดาวน์โหลด model ที่ตั้งค่าไว้ก่อน') from exc
            raise
        check_deadline()
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
        if plan.intent == 'unknown' and fallback_evidence_need(question) == 'teaching_assessment':
            # The supported schemas contain curriculum facts, not assessment or
            # term-specific instructor plans. Do not retrieve unrelated facts.
            if database.has('course', 'code', 'source_file', 'page_number'):
                return 'SELECT code, source_file, page_number FROM course WHERE 0'
            if database.has('courses', 'course_code', 'source_file', 'page_number'):
                return 'SELECT course_code AS code, source_file, page_number FROM courses WHERE 0'
            raise ValueError('Selected curriculum database is unavailable')
        if (plan.intent == 'unknown' and fallback_evidence_need(question) in {'description', 'relationship'}
                and database.schema_family == 'lab8b' and not database.has('course', 'code', 'name_th')):
            raise ValueError(f'{database.curriculum_name}: ตารางหลักฐานรายวิชา course ไม่พร้อมใช้งาน; ไม่แทนด้วยข้อมูลแผนหรือยอดรวม')
        if plan.intent == 'unknown' and fallback_evidence_need(question) == 'planning_conditions' and database.has('program_requirement', 'rule_text', 'source_file', 'page_number'):
            return 'SELECT topic, rule_text, source_file, page_number, printed_page_number FROM program_requirement'
        if plan.intent == 'unknown' and fallback_evidence_need(question) == 'planning_conditions' and database.schema_family == 'legacy-course-catalog':
            # Schema confirms the legacy catalog has no enrollment/eligibility evidence.
            return 'SELECT * FROM courses WHERE 0'
        if (plan.intent == 'unknown' and fallback_evidence_need(question) == 'relationship'
                and database.schema_family == 'legacy-course-catalog'):
            # Unidentified legacy rows must never become an unrelated first-page
            # catalog answer. Search only explicitly requested name candidates.
            terms = literal_course_mentions(question)
            predicates = [f"course_name_matches({field}, '{term.replace(chr(39), chr(39)*2)}')"
                          for term in terms for field in ('course_name_th', 'course_name_en')]
            where = ' OR '.join(predicates) if predicates else '0'
            return ('SELECT course_code AS code, course_name_th AS name_th, course_name_en AS name_en, '
                    'prerequisites, source_file, page_number FROM courses WHERE ' + where)
        if plan.intent == 'unknown' and fallback_evidence_need(question) and database.has('course', 'code', 'name_th', 'description_th'):
            # The model interprets topics; construction and version isolation remain deterministic.
            explicit = literal_course_mentions(question)
            result = {'terms': explicit} if explicit else self._chat(
                'คัดเฉพาะคำหรือวลีชื่อวิชา/หัวข้อเนื้อหาจากคำถาม ห้ามเพิ่มคำที่ไม่มีในคำถาม '
                'ไม่เลือกชื่อหลักสูตร ปี แผน คำสั่งอธิบาย หรือคำว่าความสัมพันธ์ '
                'ตอบ JSON terms ถ้าไม่ชัดเจนให้ []\nคำถาม: ' + question, SEARCH_SCHEMA)
            terms = list(dict.fromkeys(literal_database_names(question, database) + explicit + literal_search_terms(question, result.get('terms'))))
            predicates = []
            for term in terms:
                # INSTR is literal substring matching, so wildcard characters cannot widen retrieval.
                value = term.replace("'", "''")
                predicates.extend(f"course_name_matches({field}, '{value}')" for field in ('name_th', 'name_en'))
                predicates.append(f"INSTR(normalize_course_name(description_th), normalize_course_name('{value}')) > 0")
            where = ' OR '.join(predicates) if predicates else 'code IS NULL'
            return 'SELECT code, name_th, name_en, description_th, source_file, page_number FROM course WHERE ' + where
        repair = ""
        if previous_sql and error:
            repair = f"""
SQL ก่อนหน้านี้ใช้ไม่ได้: {previous_sql}
Bindings ก่อนหน้านี้: {json.dumps(getattr(previous_sql, 'parameters', ()), ensure_ascii=False)}
ข้อผิดพลาดจาก SQLite/validator: {error}
แก้ SQL และ bindings โดยใช้เฉพาะ schema จริงด้านล่าง; SQL ไม่มี marker ให้ parameters=[]; ห้ามส่งค่าที่ไม่มี marker หรือใส่ filter เพิ่มเพื่อใช้ bindings เดิม
"""
        if database.has('course', 'code', 'name_th', 'description_th'):
            stored_hint = ('คำถามเนื้อหารายวิชาใช้ course.description_th พร้อม code/name_th/source_file/page_number '
                           'ตัวอย่างรูปแบบ SELECT code, name_th, description_th, source_file, page_number FROM course '
                           'กรองชื่อหรือคำอธิบายด้วยคำที่ผู้ใช้ระบุเท่านั้น; ความสัมพันธ์ใช้ prerequisite.requires/kind เมื่อมีจริง '
                           'ห้ามใช้ program แทนเนื้อหาหรือความสัมพันธ์; หากไม่มีหลักฐานให้คืนแถวที่เกี่ยวข้องพร้อมค่าที่ขาด ไม่เดา')
        elif database.has('courses', 'course_code', 'course_name_th', 'credits'):
            stored_hint = ('ฐานนี้ไม่มี program หรือข้อมูลปี/ยอดรวมหลักสูตร เป็น catalog ที่ยังไม่ระบุฉบับแน่ชัด '
                           'เลือกหลักฐานจริงได้ด้วย SELECT course_code AS code, course_name_th AS name_th, course_name_en AS name_en, credits, source_file, page_number FROM courses LIMIT 5 '
                           'ห้ามใช้ credits AS total_credits เพราะหน่วยกิตรายวิชาไม่ใช่ยอดรวมหลักสูตร')
        else:
            stored_hint = 'เลือกเฉพาะ column จริงตาม schema ไม่เปลี่ยนความหมายด้วย alias'
        schema_text = database.schema_text()
        if plan.intent == 'unknown':
            # Keep operational review logs out of the model's factual retrieval context.
            allowed = {'course', 'courses', 'prerequisite', 'course_prerequisite_evidence',
                       'program', 'program_requirement', 'plan_item', 'v_study_plan'}
            schema_text = '\n'.join(line for line in schema_text.splitlines()
                                    if re.match(r'(?:TABLE|VIEW) (\w+)\(', line)
                                    and re.match(r'(?:TABLE|VIEW) (\w+)\(', line)[1] in allowed)
        prompt = f"""แปลงคำถามเป็น SQLite SQL สำหรับฐานข้อมูลเดียวนี้

ฐานข้อมูล: {database.curriculum_name}
แผนคำถามที่โปรแกรมตรวจพบ: {json.dumps(plan.as_dict(), ensure_ascii=False)}
schema จริง (ห้ามใช้ table หรือ column นอกเหนือจากนี้):
{schema_text}
{repair}
กติกา:
- ตอบ JSON sql พร้อม parameters เมื่อใช้ ? หรือ :name; จำนวน/ชื่อ bindings ต้องตรงทุกตัว ห้ามเดาค่าเพิ่มเติม
- parameters เป็น object ต้องใช้ :name ที่ชื่อเดียวกับทุก key ใน SQL; ห้ามใช้ ? กับ object
- parameters เป็น array ต้องใช้ ? และจำนวนสมาชิกเท่ากับจำนวน ? ตามลำดับ
- SQL ที่ใส่ค่าตรงๆ ไม่มี marker ต้องไม่มี parameters หรือใช้ [] หรือ {{}}; ห้ามคง bindings ของ SQL เก่า
- ตัวอย่าง binding syntax เท่านั้น (ไม่ใช่ table หรือ facts ให้คัดลอก): WHERE field = :value กับ {{"value": "text"}}; WHERE field = ? กับ ["text"]; WHERE field = 'text' กับ []
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
        proposal = self._chat(prompt, SQL_SCHEMA)
        return BoundSQL(_clean_model_text(proposal['sql']), proposal.get('parameters', ()))

    def summarize(
        self,
        question: str,
        plan: QueryPlan,
        rows: list[dict[str, Any]],
        executions: list[QueryExecution],
    ) -> str:
        missing_descriptions = []
        if fallback_evidence_need(question) == 'planning_conditions':
            rules = [row for row in rows if row.get('rule_text')]
            claims = [{'row_index': index, 'fields': ['rule_text']} for index in range(len(rules))]
            recorded = render_claims(rules, claims) if rules else None
            return (recorded or self._insufficient(rows)) + ' — ' + fallback_gap(question, rows, [])
        if fallback_evidence_need(question) == 'relationship':
            relationships = [row for row in rows if row.get('requires')]
            if not relationships:
                return self._insufficient(rows) + ' — ' + fallback_gap(question, rows, [])
            # A stored edge is a structured fact, not a free-text content inference.
            claims = [{'row_index': index, 'fields': [field for field in ('code', 'requires', 'kind')
                       if row.get(field) is not None]} for index, row in enumerate(relationships)]
            answer = (render_claims(relationships, claims) or self._insufficient(rows)) + ' — แสดงเฉพาะความสัมพันธ์ที่บันทึกในตาราง prerequisite ไม่ยืนยันความเชื่อมโยงเนื้อหาอื่น'
            pairs = {(row.get('code'), row.get('requires')) for row in relationships}
            if len(pairs) > 1:
                answer += '\nพบหลายคู่รายวิชาที่ตรงชื่อที่ถาม โปรดระบุรหัสหรือชื่อเต็มของคู่ที่ต้องการ ไม่เลือกคู่ใดให้โดยการเดา'
            return answer
        if fallback_evidence_need(question) == 'description':
            missing_descriptions = [str(row.get('code') or row.get('name_th') or '')
                                    for row in rows if not row.get('description_th')]
            described = [row for row in rows if row.get('description_th')]
            if not described:
                answer = self._insufficient(rows) + ' — ' + fallback_gap(question, rows, [])
                candidates = list(dict.fromkeys((str(row.get('code') or ''), str(row.get('name_th') or '')) for row in rows if row.get('code')))
                if len(candidates) > 1:
                    answer += ' — รายวิชาที่พบ: ' + '; '.join(code + ' ' + name for code, name in candidates)
                    literal = normalize_course_name(question)
                    if not any(normalize_course_name(name) in literal for _, name in candidates) and not re.search(r'ระหว่าง|กับ|และ|ทั้ง|เปรียบเทียบ|compare', question, re.I):
                        answer += ' โปรดระบุว่าต้องการรายวิชาใด; การเลือกชื่อให้ชัดยังไม่ทดแทนคำอธิบายที่ขาดในฐานข้อมูล'
                return answer
            # Null rows are not description evidence; exclude them before reference selection.
            rows = described
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
- คำถามเนื้อหาต้องอ้าง description_th ไม่ใช่ชื่อหรือหน่วยกิตอย่างเดียว
- ความสัมพันธ์ต้องมีหลักฐานความสัมพันธ์ที่บันทึกจริง ห้ามถือว่าชื่อหรือเนื้อหาคล้ายกันเป็นความสัมพันธ์ที่แหล่งข้อมูลระบุ
- ถ้ามีหลายหลักสูตร ให้รายงานแยกตาม curriculum_name ห้ามบวกยอดข้ามหลักสูตร
- ถ้าเป็นคำถามเปรียบเทียบ ให้เปรียบเทียบเฉพาะค่าที่แสดง
- ถ้าไม่มีแถวข้อมูล ให้ตอบว่าไม่พบข้อมูลนี้ในฐานข้อมูลหลักสูตร
"""
        try:
            claims = self._chat(prompt, CLAIM_SCHEMA).get('claims')
        except (ValueError, json.JSONDecodeError):
            return self._insufficient(rows)
        gap = fallback_gap(question, rows, claims)
        if gap:
            return self._insufficient(rows) + ' — ' + gap
        answer = render_claims(rows, claims) or self._insufficient(rows)
        if missing_descriptions:
            answer += ' — รายวิชาที่ดึงมาแต่ไม่มีคำอธิบายใน SQLite: ' + ', '.join(missing_descriptions)
        if fallback_evidence_need(question) == 'relationship':
            answer += ' — แสดงเฉพาะความสัมพันธ์ที่บันทึกในตาราง prerequisite ไม่ยืนยันความเชื่อมโยงเนื้อหาอื่น'
        return answer

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
        if plan.intent in {'graduation_reference', 'study_feasibility'}:
            evidence = [f"{row.get('_source', {}).get('curriculum_name', 'หลักสูตรที่เลือก')}: {row['rule_text']}"
                        for row in rows if row.get('rule_text')]
            if not evidence:
                return QwenTextToSQL._insufficient(rows)
            caveat = 'หลักฐานที่ตรวจส่วนนี้ครอบคลุมเฉพาะข้อบังคับที่อ้างหรือข้อที่ระบุ ยังไม่ได้ตรวจรายละเอียดภาคผนวกทั้งหมด จึงยังยืนยันไม่ได้ว่าแผนของผู้เรียนผ่านเงื่อนไขจบครบแล้ว'
            if plan.intent == 'study_feasibility':
                caveat += ' และยังรับรองไม่ได้ว่าจะจบตามระยะเวลาที่ถาม ต้องตรวจวิชาบังคับก่อนและการเปิดรายวิชาจริงด้วย'
            return '\n'.join(evidence) + '\n' + caveat
        if plan.intent == 'prerequisite_catalog':
            groups = {}
            for row in rows:
                key = (row.get('_source', {}).get('curriculum_name', 'หลักสูตรที่เลือก'), row.get('code'))
                if row.get('requires') or row.get('prerequisites'):
                    groups.setdefault(key, []).append(row)
            multiple = bool(re.search(r'มากกว่าหนึ่ง|หลาย|multiple', plan.search_term or '', re.I))
            lines = []
            for (curriculum, code), records in groups.items():
                requirements = sorted({str(r.get('requires') or r.get('prerequisites')) for r in records})
                if multiple and len(requirements) < 2:
                    continue
                lines.append(f"{curriculum}: {code} {records[0].get('name_th') or ''} — วิชาบังคับก่อนที่บันทึก: {', '.join(requirements)}")
            identities = ', '.join(sorted({r.get('_source', {}).get('curriculum_name', 'หลักสูตรที่เลือก') for r in rows}))
            scope = 'วิชาเลือกที่ระบุในแผนที่เลือก' if plan.elective_only else 'รายวิชาที่ตรงเงื่อนไข'
            return '\n'.join(lines or [f'{identities}: ไม่พบรายการที่ตรงเงื่อนไขในข้อมูลวิชาบังคับก่อนที่นำเข้า']) + f'\nแสดงเฉพาะความสัมพันธ์ของ{scope}ที่บันทึกใน SQLite ไม่ใช่การตรวจครบทุกวิชา ข้อมูลนี้ไม่ยืนยันความสัมพันธ์ AND/OR หรือสิทธิ์ลงทะเบียน และข้อมูลที่ขาดไม่หมายถึงไม่มีวิชาบังคับก่อน'
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
                name = row.get("name_th") or row.get("name_en") or ""
                membership = " (มีคำอธิบายในเล่ม แต่ไม่ปรากฏในตารางแผนการเรียนของฐานข้อมูลที่เลือก)" if row.get('in_selected_plan') == 0 else ""
                answers.append(f"{curriculum}: วิชา {code} {name}{membership} — {fact}")
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
            if plan.compare:
                groups = {}
                for row in rows:
                    source = row.get('_source', {}).get('curriculum_name')
                    groups.setdefault(source, {})[row.get('code')] = row.get('credits')
                for source, values in groups.items():
                    credits = list(values.values())
                    if len(credits) == 2 and all(type(value) in {int, float} for value in credits):
                        high, low = max(credits), min(credits)
                        formatted.append(f'{source}: ผลต่างหน่วยกิต = {high} - {low} = {high-low} หน่วยกิต (คำนวณจากสองรายวิชาที่ดึงมา)')
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
        if len(usable) == 1 and not usable[0].get('calculation_rows'):
            value = str(usable[0][field])
            if value in model_answer and unit in model_answer:
                return model_answer
        elif not any(row.get('calculation_rows') for row in usable):
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
            placement = f" ปี {row.get('year')} ภาค {row.get('semester')}" if plan.intent == 'semester_credits' else ''
            parts.append(f"{curriculum}{placement}: {row[field]} {unit}{citation}")
            if row.get('calculation_rows'):
                items = json.loads(row['calculation_rows'])
                has_bundles = any(len(r)>5 and r[5] for r in items)
                nested_choices = any(len(r)>5 and r[5] and r[2] for r in items)
                parts.append(('รายวิชาร่วมและตัวเลือกตามแขนง (เลือกหนึ่งแขนง): ' if nested_choices else
                              ('รายวิชาร่วมและรายวิชาในชุดทางเลือก (เลือกทั้งชุดเดียว): ' if has_bundles else 'รายการที่ใช้คำนวณ: '))+', '.join(
                    f"{r[0]} {r[3] if len(r)>3 and r[3] else 'ไม่ระบุชื่อในฐานข้อมูล'}: {r[1]} หน่วยกิต"
                    +(f" [{r[4]}]" if len(r)>4 and r[4] else '')
                    +(' (ตัวเลือกภายในแขนง)' if nested_choices and r[2] else (' (รายวิชาทางเลือก)' if r[2] else ''))
                    +(f" (ชุด {r[6] or r[5]})" if len(r)>6 and r[5] else '') for r in items))
                # Match the view: one MIN credit contribution per alternative group.
                contributions = []
                alternatives = {}
                bundles = {}
                for index, item in enumerate(items):
                    if item[1] is None:
                        continue
                    if len(item)>5 and item[5]:
                        slots = bundles.setdefault(item[5], {})
                        slot = item[2] or f'row-{index}'
                        slots.setdefault(slot, []).append(item[1])
                    elif item[2]:
                        alternatives.setdefault(item[2], []).append(item[1])
                    else:
                        contributions.append(item[1])
                contributions.extend(min(values) for values in alternatives.values())
                if bundles:
                    if any(len(set(values)) != 1 for slots in bundles.values() for values in slots.values()):
                        parts.append('หน่วยกิตของตัวเลือกภายในชุดไม่ตรงกัน จึงยังยืนยันการคำนวณจากหลักฐานนี้ไม่ได้')
                        continue
                    bundles = {key:sum(values[0] for values in slots.values()) for key,slots in bundles.items()}
                    if len(set(bundles.values())) != 1:
                        parts.append('หน่วยกิตของชุดทางเลือกไม่ตรงกัน จึงยังยืนยันการคำนวณจากหลักฐานนี้ไม่ได้')
                        continue
                    contributions.append(next(iter(bundles.values())))
                    parts.append('เลือกหนึ่งแขนง แล้วเลือกหนึ่งรายวิชาจากกลุ่มตัวเลือกภายในแขนงนั้น; นับหน่วยกิตครั้งเดียว'
                                 if nested_choices else 'นับรายวิชาร่วมบวกหนึ่งชุดทั้งกลุ่ม; ไม่รวมหลายชุดหรือสลับรายวิชาแต่ละลำดับข้ามชุด')
                if contributions:
                    parts.append('การคำนวณ: '+' + '.join(str(value) for value in contributions)
                                 +f' = {sum(contributions)} หน่วยกิต')
                parts.append('นับแต่ละกลุ่มทางเลือกเพียงหนึ่งตัวเลือก')
        if plan.intent == 'semester_credits' and len(usable) > 1:
            for curriculum in {r.get('_source',{}).get('curriculum_name') for r in usable}:
                values=[r[field] for r in usable if r.get('_source',{}).get('curriculum_name') == curriculum]
                if len(values)==2:
                    parts.append(f'{curriculum}: ผลต่าง = {max(values)} - {min(values)} = {max(values)-min(values)} หน่วยกิต')
        return "; ".join(parts)

    def _execute_one(
        self, question: str, plan: QueryPlan, database: DatabaseInfo,
        *, resolved_course_code: str | None = None,
    ) -> QueryExecution:
        sql = deterministic_sql(plan, database)
        codes = list(dict.fromkeys(re.findall(r'(?<!\d)\d{8}(?!\d)', question)))
        if sql and plan.intent == 'course_detail' and len(codes) > 1:
            values = ', '.join("'" + code + "'" for code in codes)
            sql = re.sub(r"\b(code|course_code)\s*=\s*'" + re.escape(plan.course_code) + "'",
                         lambda match: match[1] + ' IN (' + values + ')', sql, flags=re.I)
        repairs: list[dict[str, str]] = []
        if sql is None:
            sql = self.make_sql(question, plan, database)

        for attempt in range(self.config.sql_repair_attempts + 1):
            try:
                parameters = getattr(sql, 'parameters', ())
                checked_sql = constraint_sql(sql, parameters)
                if plan.intent == 'unknown':
                    validate_unknown_projection(sql)
                    if fallback_evidence_need(question) and re.search(r'\b(?:FROM|JOIN)\s+program\b', sql, re.I):
                        raise SqlValidationError('Course content/relationship questions require relevant course evidence, not program totals or duration')
                    if not parameters:
                        sql = normalize_redundant_program_filter(database, sql)
                self._validate_plan_filters(question, plan, database, checked_sql,resolved_course_code=resolved_course_code)
                validation, raw_rows = execute_readonly(database, sql, self.config.max_rows, parameters)
                if plan.intent == 'course_search':
                    # Keep every canonical-name candidate unless an exact full
                    # name resolves it. A literal substring must not hide synonyms.
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
                    parameters=parameters,
                )
            except SqlValidationError as exc:
                error = str(exc)
                repairs.append({"sql": sql, "error": error})
                LOGGER.warning(
                    "SQL rejected curriculum=%s attempt=%s sql=%r error=%s",
                    database.curriculum_name, attempt + 1, sql, error,
                )
                if attempt >= self.config.sql_repair_attempts:
                    return QueryExecution(database, sql, [], (), repairs, error, parameters=parameters)
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
        if plan.intent == 'plans_comparison':
            where_text = re.sub(r'year\s*=\s*\(SELECT MAX\(year\) FROM plan_item\)', '1=1', where_text, flags=re.I)
        # ESCAPE is syntax, not an invented user filter. Only permit our fixed
        # escape character; keep the ordinary literal guard intact.
        where_text = re.sub(r"\bESCAPE\s+'\\'", '', where_text, flags=re.I)
        # A literal being present in the question does not authorize using it
        # on an unrelated field (e.g. curriculum year as a course-code filter).
        for column, operator, literal in re.findall(
            r"\b(code|course_code)\s*(=|LIKE)\s*'((?:''|[^'])*)'", where_text, re.I
        ):
            value = literal.replace("''", "'")
            if operator.upper() == 'LIKE' and not value.strip('%_ '):
                raise SqlValidationError('Course-code filter cannot be an unconstrained wildcard')
            if re.fullmatch(r'%?25\d{2}%?', value) and re.search(r'หลักสูตร|ฉบับ|curriculum|version', question, re.I):
                raise SqlValidationError('Curriculum version cannot be used as a course-code filter')
        if plan.year is None and re.search(r"\byear\s*(?:=|<|>|\bin\b|\bbetween\b)", where_text, re.I):
            raise SqlValidationError("SQL added a year filter that the user did not request")
        if plan.semester is None and re.search(
            r"\bsemester\s*(?:=|<|>|\bin\b|\bbetween\b)", where_text, re.I
        ):
            raise SqlValidationError("SQL added a semester filter that the user did not request")
        for field, requested in (('year', plan.year), ('semester', plan.semester)):
            if requested is None:
                continue
            allowed = set(plan.semesters or (requested,)) if field == 'semester' else {requested}
            for value in re.findall(rf"\b{field}\s*=\s*'?([0-9]+)'?", where_text, re.I):
                if int(value) not in allowed:
                    raise SqlValidationError(f'SQL {field} filter contradicts the requested value')
        if where and re.search(r"\bfrom\s+program\b", sql, re.I):
            raise SqlValidationError(
                "The selected database contains one program row; filtering program is redundant"
            )
        allowed_constants = {"pre", "corequisite"}
        if plan.intent == 'elective_slots':
            allowed_constants.update({'elec-', 'x'})
        if plan.intent in {'graduation_reference', 'study_feasibility'}:
            allowed_constants.update({'graduation_reference','graduation_rule_26'})
        # Only the internal, database-backed name resolver can authorize this
        # code. Do not exempt arbitrary plan/model-added course literals.
        if resolved_course_code == plan.course_code and re.fullmatch(r'\d{8}',resolved_course_code or ''):
            allowed_constants.add(resolved_course_code.casefold())
        if plan.required_only:
            # This is a deterministic synonym expansion from the explicit
            # Thai/English "required course" intent, not a model-added filter.
            allowed_constants.add("required")
        # Authorize synonyms only inside the category predicate, not arbitrary
        # model-added description/name filters containing the same word.
        elective_spans = []
        if plan.elective_only and plan.intent in {'prerequisite_catalog', 'course_list'}:
            elective_spans = [match.span() for match in re.finditer(
                r"\b(?:LOWER\(\s*)?(?:\w+\.)?ctype\s*\)?\s*(?:=\s*'(?:เลือก|elective)'|LIKE\s*'%(?:เลือก|elective)%'|IN\s*\(\s*'(?:เลือก|elective)'(?:\s*,\s*'(?:เลือก|elective)')*\s*\))",
                where_text, re.I)]
        for literal_match in re.finditer(r"'((?:''|[^'])*)'", where_text):
            literal = literal_match[1]
            if any(start <= literal_match.start() < end for start, end in elective_spans):
                continue
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

    @staticmethod
    def _attach_page_pairs(execution):
        """Resolve citation metadata exclusively from this selected SQLite database."""
        database = execution.database
        if database.has('plan_source_claim', 'plan_item_id', 'field', 'pdf_page', 'literal'):
            for row in execution.rows:
                if type(row.get('id')) is int:
                    ids = str(row['id'])
                elif isinstance(row.get('code'),str):
                    code = row['code'].replace("'","''")
                    ids = f"SELECT id FROM plan_item WHERE code='{code}'"
                else:
                    continue
                sql = f'SELECT field,source_file,pdf_page AS page,printed_page AS book_page,literal AS quote FROM plan_source_claim WHERE plan_item_id IN ({ids})'
                validation, records = execute_readonly(database, sql, 100)
                execution.citation_queries.append({'sql':validation.sql,'rows':records})
                if database.has('plan_bundle_member', 'plan_item_id', 'bundle_id'):
                    sql = f"SELECT 'whole_bundle_rule' AS field,b.source_file,b.rule_pdf_page AS page,b.rule_printed_page AS book_page,b.rule_text AS quote FROM plan_bundle b JOIN plan_bundle_member m ON m.year=b.year AND m.semester=b.semester AND m.bundle_id=b.bundle_id WHERE m.plan_item_id IN ({ids})"
                    validation, rules = execute_readonly(database,sql,10)
                    execution.citation_queries.append({'sql':validation.sql,'rows':rules})
                    records += rules
                if records:
                    row['page_evidence'] = records
        if database.has('plan_term_source','year','semester','pdf_page'):
            for row in execution.rows:
                if type(row.get('year')) is int and 'credits' in row and 'code' not in row:
                    condition = f"year={row['year']}"
                    if type(row.get('semester')) is int:
                        condition += f" AND semester={row['semester']}"
                    sql = "SELECT 'term_total' AS field,source_file,pdf_page AS page,printed_page AS book_page,'รวม '||credits AS quote FROM plan_term_source WHERE "+condition
                    validation, records = execute_readonly(database,sql,10)
                    execution.citation_queries.append({'sql':validation.sql,'rows':records})
                    if records:
                        row['page_evidence'] = records
        for filename, page in sorted({(row.get('source_file'), row.get('page_number'))
                                      for row in execution.rows if isinstance(row.get('source_file'), str)
                                      and type(row.get('page_number')) is int}):
            pages = set()
            for table in ('plan_item', 'program', 'course_prerequisite_evidence', 'program_requirement'):
                if not database.has(table, 'source_file', 'page_number', 'printed_page_number'):
                    continue
                escaped = filename.replace("'", "''")
                sql = (f'SELECT source_file, page_number, printed_page_number FROM {table} '
                       f"WHERE source_file='{escaped}' AND page_number={page}")
                validation, records = execute_readonly(database, sql, 100)
                execution.citation_queries.append({'sql': validation.sql, 'rows': records})
                pages.update(record['printed_page_number'] for record in records
                             if type(record.get('printed_page_number')) is int and record['printed_page_number'] > 0)
            if len(pages) == 1:
                printed = next(iter(pages))
                for row in execution.rows:
                    if row.get('source_file') == filename and row.get('page_number') == page and row.get('printed_page_number') is None:
                        row['printed_page_number'] = printed

    def ask(self, registry: DatabaseRegistry, question: str) -> dict[str, Any]:
        # SQL repair and generation share one request budget, isolated per thread.
        token = REQUEST_DEADLINE.set(time.perf_counter() + self.config.request_timeout)
        model_token = MODEL_CALLS.set(0)
        try:
            check_deadline()
            result = self._ask_with_budget(registry, question)
            result['model_used'] = self.config.ollama_model if MODEL_CALLS.get() else None
            check_deadline()
            return result
        finally:
            MODEL_CALLS.reset(model_token)
            REQUEST_DEADLINE.reset(token)

    def _ask_with_budget(self, registry: DatabaseRegistry, question: str) -> dict[str, Any]:
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
        partial_scope = getattr(registry, 'build_contract', {}).get('kind') == 'academic-plan-only'
        if partial_scope:
            from .build_scope import supports_plan_question, partial_answer_notice
            if not supports_plan_question(plan, question):
                return {'question': question, 'sql': '', 'rows': [], 'answer': partial_answer_notice(),
                        'intent': plan.intent, 'selected_curricula': [], 'queries': [],
                        'debug': None, 'model_used': None, 'partial_scope': True}
        include_legacy = plan.intent in {"course_detail", "course_search", "prerequisite"}
        selected = registry.select(question, include_legacy=include_legacy,
            compare_versions=plan.intent in {'version_course_diff','version_fact_comparison'},
            compare_plans=plan.intent == 'plans_comparison')
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
        if plan.intent == 'unknown' and fallback_evidence_need(question) == 'relationship':
            related = []
            for execution in executions:
                database = execution.database
                sql = relationship_sql(execution.sql, paired_pages=database.has('course_prerequisite_evidence', 'code', 'source_file', 'page_number', 'printed_page_number'))
                if not sql or execution.error or not database.has('prerequisite', 'code', 'requires', 'kind'):
                    continue
                try:
                    validate_unknown_projection(sql)
                    parameters = execution.parameters
                    self._validate_plan_filters(question, plan, database, constraint_sql(sql, parameters))
                    validation, evidence = execute_readonly(database, sql, self.config.max_rows, parameters)
                    related.append(QueryExecution(database, validation.sql, attach_source_metadata(evidence, database), validation.referenced_columns, [], parameters=parameters))
                except SqlValidationError as exc:
                    related.append(QueryExecution(database, sql, [], (), [], str(exc)))
            executions.extend(related)
        if plan.intent in {'unknown', 'prerequisite_catalog', 'version_fact_comparison'}:
            for execution in executions:
                self._attach_page_pairs(execution)
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
        if plan.intent == 'selection_clarification':
            answer = 'คำถามขอใช้ฉบับใหม่แทนฉบับที่เลือก กรุณาเลือกฉบับที่ต้องการค้นให้ตรงกันก่อน: ' + ', '.join(item.curriculum_name for item in selected)
        elif rows and plan.intent in {'course_list', 'elective_slots', 'plans_comparison'} and all(item.database.schema_family == 'lab8b' for item in executions):
            evidence = {item.database.curriculum_name: read_study_evidence(item.database) for item in executions}
            study_plan, rows = build_study_plan(rows, question, evidence, required_only=plan.required_only,
                                               filtered_subset=plan.intent == 'elective_slots')
            # Keep limitations in the structured payload too, not only plain text.
            study_plan['notes'] = []
            if plan.intent == 'elective_slots':
                study_plan['notes'].append('รูปแบบที่มีคำว่า “หรือ” ในหน่วยกิตเป็นตัวเลือกตามค่าที่บันทึก ไม่ใช่ให้เรียนทุกรูปแบบพร้อมกัน; ส่วนที่ไม่ระบุความสัมพันธ์ยังยืนยันไม่ได้')
            if plan.intent == 'plans_comparison' and len({item.database.plan for item in executions}) < 2:
                study_plan['notes'].append('ฐานข้อมูลที่เลือกมีข้อมูลเพียงแผนเดียว จึงยังเปรียบเทียบสองแผนไม่ได้')
            if re.search(r'ทุกกลุ่ม|ร่วมทุก|กลุ่มที่เลือก', question):
                for card in study_plan['cards']:
                    if not any(section['kind'] == 'track' or section['title'] == 'รายวิชาร่วมทุกกลุ่ม' for section in card['sections']):
                        study_plan['notes'].append(f"{card['program']} {card['version']} {card['plan_label']}: ข้อมูลความสัมพันธ์กลุ่มที่ค้นยังไม่พอจะแยกวิชาร่วมทุกกลุ่มจากวิชาเฉพาะกลุ่ม รายการข้างต้นไม่ยืนยันว่าทุกกลุ่มต้องเรียนทั้งหมด")
            answer = study_plan_text(study_plan, include_english=bool(re.search(r'อังกฤษ|english', question, re.I)))
        elif rows and plan.intent == "version_course_diff":
            answer, rows = self._version_diff(rows)
        elif rows and plan.intent == 'version_fact_comparison':
            answer, rows = self._version_facts(rows)
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
            if plan.intent == 'unknown':
                gap = fallback_gap(question, [], [])
                if gap:
                    answer += ' — ' + gap
            if plan.intent == 'prerequisite_catalog':
                if plan.elective_only:
                    answer += ' — ค้นเฉพาะรายวิชาที่ฐานข้อมูลแผนที่เลือกระบุว่าเป็นวิชาเลือก ไม่ใช้วิชาบังคับอื่นแทน และยังตรวจยืนยันทุกวิชาเลือกไม่ได้'
                answer += ' — ยังไม่มีข้อมูลวิชาบังคับก่อนที่ค้นได้เพื่อประเมินจำนวนหรือความสัมพันธ์ AND/OR ไม่อนุมานว่าไม่มีวิชาบังคับก่อนหรือมีสิทธิ์ลงทะเบียน'
            if plan.intent in {'semester_credits', 'year_credits'} and any(item.schema_family == 'legacy-course-catalog' for item in selected):
                answer += ' — catalog เดิมไม่มีข้อมูลชั้นปี/ภาคการศึกษาและยังไม่ยืนยันฉบับหลักสูตร จึงคำนวณยอดตามแผนที่ถามไม่ได้ ไม่ใช้ยอดรวมทุกแถวแทนยอดภาคเรียน'
        if not answer.strip():
            searched = ', '.join(item.curriculum_name for item in selected)
            answer = f"ยังยืนยันข้อมูลที่ถามไม่ได้จากฐานข้อมูลที่ค้น: {searched} แถวที่ค้นพบไม่มี fields ที่จำเป็นสำหรับคำถามนี้ จึงไม่สามารถใช้แทนหลักฐานที่ขาดได้"
        if plan.intent == 'unknown' and fallback_evidence_need(question) == 'relationship' and rows:
            answer += relationship_coverage_gap(rows, selected)
        if partial_scope:
            from .build_scope import partial_answer_notice
            answer += '\n\n' + partial_answer_notice()
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
