"""Qwen text-to-SQL adapter that reuses Lab 8B's Ollama helper."""

import json
import re
from types import ModuleType
from typing import Any, Optional

import requests

from .config import Settings
from .database import CurriculumDatabase, SQL_SCHEMA_CONTEXT

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


class QwenTextToSQL:
    def __init__(self, settings: Settings, lab8b: Optional[ModuleType] = None):
        self.settings = settings
        self.lab8b = lab8b
        self.ollama_url = getattr(settings, "ollama_url", "http://127.0.0.1:11434")
        self.model = getattr(settings, "ollama_model", "qwen3:4b")

    def available(self) -> bool:
        try:
            res = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            return res.status_code == 200
        except Exception:
            return False

    def _chat(self, prompt: str, schema: Optional[dict] = None) -> dict:
        if self.lab8b and hasattr(self.lab8b, "ollama_generate"):
            try:
                raw = self.lab8b.ollama_generate(
                    prompt,
                    fmt=schema,
                    timeout=getattr(self.settings, "request_timeout", 180),
                    model=self.model,
                    num_ctx=4096,
                    num_predict=256,
                )
                if hasattr(self.lab8b, "parse_json_loose"):
                    return self.lab8b.parse_json_loose(raw)
                return json.loads(raw)
            except Exception:
                pass

        url = f"{self.ollama_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if schema:
            payload["format"] = schema

        try:
            res = requests.post(url, json=payload, timeout=180)
            res.raise_for_status()
            content = res.json().get("message", {}).get("content", "")
            if isinstance(content, str):
                try:
                    return json.loads(content)
                except Exception:
                    return {"sql": content.strip(), "answer": content.strip()}
            return res.json()
        except Exception as e:
            return {"error": str(e), "sql": "", "answer": ""}

    def make_sql(self, question: str) -> str:
        prompt = f"""แปลงคำถามเป็น SQLite SQL จาก schema นี้
{SQL_SCHEMA_CONTEXT}

กติกา:
- ตอบ SELECT หรือ WITH คำสั่งเดียว
- ถามหน่วยกิตรายเทอมให้ใช้ v_semester_credits
- ถามรายวิชาตามแผนให้ใช้ v_plan
- ห้ามแก้ไขฐานข้อมูล

ตัวอย่าง:
คำถาม: หลักสูตรนี้มีกี่หน่วยกิต
SQL: SELECT total_credits FROM program
คำถาม: ต้องเรียนวิชาอะไรมาก่อนจึงจะลงเรียน 06026215 ได้
SQL: SELECT requires FROM prerequisite WHERE code='06026215' AND kind='pre'

คำถาม: {question}
ตอบ JSON ที่มี key ชื่อ sql"""
        res = self._chat(prompt, SQL_SCHEMA)
        sql = str(res.get("sql", "")).strip()
        return re.sub(r"^```(?:sql)?|```$", "", sql, flags=re.MULTILINE).strip()

    def summarize(self, question: str, rows: list[dict[str, Any]]) -> str:
        prompt = f"""ตอบภาษาไทยจากผลฐานข้อมูลเท่านั้น
คำถาม: {question}
ผลฐานข้อมูล: {json.dumps(rows[:40], ensure_ascii=False)}
ตอบ JSON ที่มี key ชื่อ answer และห้ามเพิ่มข้อมูลที่ไม่มีในผล"""
        res = self._chat(prompt, ANSWER_SCHEMA)
        return str(res.get("answer", "")).strip()

    def ask(self, database: CurriculumDatabase, question: str) -> dict:
        sql, rows = database.query_from_model(self.make_sql(question))
        answer = self.summarize(question, rows) if rows else "ไม่พบข้อมูลนี้ในฐานข้อมูลหลักสูตร"
        return {"question": question, "sql": sql, "rows": rows, "answer": answer}