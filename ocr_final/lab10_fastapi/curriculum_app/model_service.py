"""Schema-aware multi-database curriculum question answering."""

from __future__ import annotations

import json
import logging
import re
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
)
from .query_planner import QueryPlan, detect_intent, deterministic_sql


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

    def available(self) -> bool:
        try:
            return requests.get(f"{self.config.ollama_url}/api/tags", timeout=3).ok
        except requests.RequestException:
            return False

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
        prompt = f"""ตอบคำถามเป็นภาษาไทยจากผลฐานข้อมูลเท่านั้น
คำถาม: {question}
intent: {plan.intent}
แหล่งข้อมูล: {json.dumps(sources, ensure_ascii=False)}
ผลฐานข้อมูล: {json.dumps(rows[:80], ensure_ascii=False)}

กติกา:
- ตอบ JSON ที่มี key ชื่อ answer
- ห้ามเพิ่มข้อมูลที่ไม่มีในผลฐานข้อมูล
- ถ้ามีหลายหลักสูตร ให้รายงานแยกตาม curriculum_name ห้ามบวกยอดข้ามหลักสูตร
- ถ้าเป็นคำถามเปรียบเทียบ ให้เปรียบเทียบเฉพาะค่าที่แสดง
- ถ้าไม่มีแถวข้อมูล ให้ตอบว่าไม่พบข้อมูลนี้ในฐานข้อมูลหลักสูตร
"""
        return self._chat(prompt, ANSWER_SCHEMA)["answer"].strip()

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
        if plan.intent == "course_list":
            expected_codes = {str(row.get("code")) for row in rows if row.get("code")}
            expected_curricula = {
                str(row.get("_source", {}).get("curriculum_name"))
                for row in rows if row.get("_source", {}).get("curriculum_name")
            }
            answer_folded = model_answer.casefold()
            if (
                expected_codes
                and all(code.casefold() in answer_folded for code in expected_codes)
                and all(name.casefold() in answer_folded for name in expected_curricula)
            ):
                return model_answer
            grouped: dict[str, list[str]] = {}
            for row in rows:
                curriculum = str(row.get("_source", {}).get("curriculum_name", "หลักสูตร"))
                code = str(row.get("code") or "ไม่ระบุรหัส")
                name = str(row.get("name_th") or row.get("name_en") or "ไม่ระบุชื่อ")
                credits = f" ({row['credits']} หน่วยกิต)" if row.get("credits") is not None else ""
                grouped.setdefault(curriculum, []).append(f"{code} {name}{credits}")
            return "\n".join(
                f"{curriculum}: " + ", ".join(items)
                for curriculum, items in grouped.items()
            )

        if plan.intent in {"course_detail", "course_search", "prerequisite"}:
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
            return "\n".join(
                f"{row.get('_source', {}).get('curriculum_name', 'หลักสูตร')}: "
                + ", ".join(
                    f"{key}={value}" for key, value in row.items()
                    if key != "_source" and value is not None
                )
                for row in rows
            )

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
        self, question: str, plan: QueryPlan, database: DatabaseInfo
    ) -> QueryExecution:
        sql = deterministic_sql(plan, database)
        repairs: list[dict[str, str]] = []
        if sql is None:
            sql = self.make_sql(question, plan, database)

        for attempt in range(self.config.sql_repair_attempts + 1):
            try:
                self._validate_plan_filters(question, plan, database, sql)
                validation, raw_rows = execute_readonly(database, sql, self.config.max_rows)
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
        question: str, plan: QueryPlan, database: DatabaseInfo, sql: str
    ) -> None:
        """Reject filters that contradict or exceed the detected user constraints."""
        where = re.search(r"\bwhere\b(.*?)(?:\bgroup\b|\border\b|\blimit\b|$)", sql, re.I | re.S)
        where_text = where.group(1) if where else ""
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
        for literal in re.findall(r"'((?:''|[^'])*)'", where_text):
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
        registry.refresh()
        plan = detect_intent(question)
        include_legacy = plan.intent in {"course_detail", "course_search", "prerequisite"}
        selected = registry.select(question, include_legacy=include_legacy)
        if not selected:
            raise ValueError("ไม่พบฐานข้อมูลหลักสูตรที่ตรงกับคำถาม")

        LOGGER.info("question=%r intent=%s", question, plan.as_dict())
        LOGGER.info(
            "discovered=%s selected=%s",
            [item.relative_path for item in registry.databases],
            [item.relative_path for item in selected],
        )
        executions = [self._execute_one(question, plan, database) for database in selected]
        rows = [row for execution in executions for row in execution.rows]
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

        if rows:
            model_answer = self.summarize(question, plan, rows, executions)
            answer = self._ground_answer(plan, rows, model_answer)
        else:
            answer = "ไม่พบข้อมูลนี้ในฐานข้อมูลหลักสูตร"
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
        }
        return {
            "question": question,
            "intent": plan.intent,
            "selected_curricula": [item.curriculum_name for item in selected],
            "sql": next(iter(sql_map.values())) if len(sql_map) == 1 else json.dumps(sql_map, ensure_ascii=False),
            "queries": [execution.public() for execution in executions],
            "rows": rows,
            "answer": answer,
            "debug": debug if self.config.debug else None,
        }
