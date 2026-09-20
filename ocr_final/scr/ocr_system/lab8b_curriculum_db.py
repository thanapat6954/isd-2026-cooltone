#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lab8b_curriculum_db.py — Lab 8B : จากข้อความที่สกัดได้ สู่ฐานข้อมูลที่ตอบคำถามได้
วิชา 06026240 การพัฒนาระบบอัจฉริยะ 

ต่อยอดจาก Lab 7B ซึ่งสกัดเล่มหลักสูตรออกมาเป็น Markdown ได้แล้ว
Lab 8B พาข้อมูลนั้นเดินต่ออีกสามก้าว

    Markdown  ->  JSON ที่ผ่านการตรวจ  ->  ฐานข้อมูล  ->  คำตอบ

ทำไมต้องผ่านฐานข้อมูล ไม่ถาม LLM ตรง ๆ กับข้อความเลย
    เพราะคำถามจริงของนักศึกษาคือคำถามเชิงคำนวณและเชิงความสัมพันธ์
    "ปี 3 เทอม 1 มีกี่หน่วยกิต"  "วิชาไหนต้องเรียน 06026240 มาก่อน"
    ซึ่ง LLM ที่อ่านข้อความยาว ๆ จะนับผิดเสมอ แต่ SQL นับถูกทุกครั้ง
    LLM เก่งเรื่อง "แปลภาษาคนเป็น SQL"  ไม่ใช่ "เป็นเครื่องคิดเลข"

คำสั่งหลัก
  python3 lab8b_curriculum_db.py check
  python3 lab8b_curriculum_db.py selftest
  python3 lab8b_curriculum_db.py demo    -o work/
  python3 lab8b_curriculum_db.py schema  -o work/schema/
  python3 lab8b_curriculum_db.py extract -i work/curriculum.md -o work/curriculum.json
  python3 lab8b_curriculum_db.py import-lab7b -i output/pred_vlm.json -o work/curriculum.json
  python3 lab8b_curriculum_db.py load    -i work/curriculum.json -d work/curriculum.db
  python3 lab8b_curriculum_db.py verify  -d work/curriculum.db
  python3 lab8b_curriculum_db.py ask     -d work/curriculum.db -q "ปี 2 เทอม 1 เรียนกี่หน่วยกิต"
  python3 lab8b_curriculum_db.py eval    -d work/curriculum.db -q work/gold_questions.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

# ═══════════════════════════════════════════════════════════════════════
#  ค่าคงที่
# ═══════════════════════════════════════════════════════════════════════

OLLAMA_URL = os.environ.get("LAB8_OLLAMA_URL", "http://127.0.0.1:11434")
MODEL_TEXT = os.environ.get("LAB8_MODEL_TEXT", "qwen3:4b")

MAX_REPAIR_ROUNDS = 3      # จำนวนครั้งสูงสุดที่ยอมให้ LLM แก้ JSON ของตัวเอง
SQL_ROW_LIMIT = 200        # กันไม่ให้ query เผลอดึงทั้งตารางมาใส่ prompt

# ระเบียบหน่วยกิตต่อภาคเรียนของหลักสูตรปริญญาตรี (ใช้ในการตรวจ CHK7)
MIN_CREDITS_PER_SEM = 9
MAX_CREDITS_PER_SEM = 22


# ═══════════════════════════════════════════════════════════════════════
#  ส่วนที่ 0 — ตรวจสภาพแวดล้อม
# ═══════════════════════════════════════════════════════════════════════

def check_environment() -> bool:
    print("=" * 68)
    print("  ตรวจสภาพแวดล้อม Lab 8B")
    print("=" * 68)
    ok = True

    required = [
        ("pydantic", "pydantic", "ตรวจความถูกต้องของ JSON และสร้างข้อความ error ให้ LLM แก้"),
        ("requests", "requests", "เรียก Ollama"),
    ]
    for mod, pipname, why in required:
        try:
            __import__(mod)
            print(f"  [ ok ] {pipname:<12} — {why}")
        except ImportError:
            print(f"  [FAIL] {pipname:<12} — {why}")
            print(f"         แก้ด้วย:  pip install {pipname}")
            ok = False

    # sqlite3 มากับ Python อยู่แล้ว แต่ต้องตรวจว่ารุ่นรองรับ foreign key
    v = sqlite3.sqlite_version_info
    if v >= (3, 6, 19):
        print(f"  [ ok ] sqlite3      — เวอร์ชัน {sqlite3.sqlite_version} รองรับ foreign key")
    else:
        print(f"  [FAIL] sqlite3      — เวอร์ชัน {sqlite3.sqlite_version} เก่าเกินไป")
        ok = False

    try:
        import requests
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        names = [m["name"] for m in r.json().get("models", [])]
        print(f"  [ ok ] Ollama ทำงานอยู่ที่ {OLLAMA_URL}")
        if any(n == MODEL_TEXT or n.startswith(MODEL_TEXT.split(":")[0]) for n in names):
            print(f"  [ ok ] พบโมเดล {MODEL_TEXT}")
        else:
            print(f"  [FAIL] ไม่พบโมเดล {MODEL_TEXT}")
            print(f"         แก้ด้วย:  ollama pull {MODEL_TEXT}")
            ok = False
    except Exception as e:
        print(f"  [FAIL] ต่อ Ollama ไม่ได้ ({type(e).__name__}) — เปิดด้วย  ollama serve")
        ok = False

    print("=" * 68)
    print("  พร้อมทำแล็บ" if ok else "  ยังไม่พร้อม — แก้ตามข้อความ [FAIL] ข้างบนก่อน")
    print("=" * 68)
    return ok


# ═══════════════════════════════════════════════════════════════════════
#  ส่วนที่ 1 — ออกแบบ Schema ก่อน แล้วค่อยสกัด
# ═══════════════════════════════════════════════════════════════════════
#
#  ลำดับที่ถูกต้องคือ  ออกแบบ schema -> สกัด -> ตรวจ
#  ไม่ใช่  สกัด -> ดูว่าได้อะไรมา -> ค่อยคิด schema
#
#  ถ้าปล่อยให้ LLM คิดโครงสร้างเอง จะเกิดสองปัญหาที่แก้ทีหลังไม่ได้
#    1) แต่ละหน้าได้ชื่อฟิลด์ไม่ตรงกัน (หน้าหนึ่ง "หน่วยกิต" อีกหน้า "credit")
#       ทำให้รวมข้อมูลไม่ได้
#    2) ไม่มีเกณฑ์ตัดสินว่า "ผิด" คืออะไร จึงตรวจอัตโนมัติไม่ได้เลย
#
#  Schema คือสัญญาที่เขียนไว้ก่อน ทั้งฝั่งสกัดและฝั่งตรวจจึงพูดภาษาเดียวกัน
# ═══════════════════════════════════════════════════════════════════════

def build_models():
    """
    สร้าง Pydantic models

    ห่อไว้ในฟังก์ชันเพื่อให้ไฟล์นี้ยัง import ได้แม้ยังไม่ได้ติดตั้ง pydantic
    (คำสั่ง check จะได้บอกวิธีติดตั้งแทนที่จะพังตั้งแต่บรรทัด import)
    """
    from pydantic import BaseModel, Field, field_validator

    # รหัสวิชา 8 หลัก — รูปแบบมาตรฐานของ สจล.
    CODE_RE = re.compile(r"^\d{8}$")

    class Course(BaseModel):
        """รายวิชาหนึ่งวิชา ตามที่ปรากฏในหมวดคำอธิบายรายวิชา"""
        code: str
        name_th: str
        name_en: str | None = None
        credits: int = Field(ge=0, le=12)
        # สหกิจศึกษาในเล่มจริงใช้ 6(0-35-0) จึงห้ามจำกัดชั่วโมงไว้แค่ 30
        lecture_h: int | None = Field(default=None, ge=0, le=60)
        lab_h: int | None = Field(default=None, ge=0, le=60)
        self_h: int | None = Field(default=None, ge=0, le=60)
        description_th: str | None = None
        source_file: str | None = None
        page_number: int | None = Field(default=None, ge=1)

        @field_validator("code")
        @classmethod
        def _code_format(cls, v: str) -> str:
            v = v.strip()
            if not CODE_RE.match(v):
                raise ValueError(f"รหัสวิชาต้องเป็นตัวเลข 8 หลัก แต่ได้ '{v}'")
            return v

    class PlanItem(BaseModel):
        """
        หนึ่งบรรทัดในแผนการศึกษา

        alt_group คือกลไกจัดการ "วิชาเลือกอย่างใดอย่างหนึ่ง"
        เล่มหลักสูตรเขียนว่า  06026259 หรือ 06026260
        เราแตกเป็นสองแถวที่มี alt_group เดียวกัน
        เวลานับหน่วยกิตจึงนับ alt_group ละครั้งเดียว ไม่นับซ้ำ

        นี่คือบทเรียนตรงจาก Lab 7B: กฎตรวจที่ไม่รู้จักกรณีนี้
        จะเตือนผิดทุกครั้งที่เจอวิชาเลือก จนนักศึกษาเลิกอ่านคำเตือน
        """
        year: int = Field(ge=0, le=8)     # 0 = ยืดหยุ่นภาคเรียน ไม่ใช่ปีจริง
        semester: int = Field(ge=0, le=3)  # 3 = ภาคฤดูร้อน, 0 = ยืดหยุ่นภาคเรียน
        code: str
        credits: int = Field(ge=0, le=12)
        alt_group: str | None = None
        # เก็บเป็นคอลัมน์จริง ไม่ยุบรวมเป็น note — ไม่งั้นถามแยกหมวดไม่ได้เลย
        category: str | None = None   # หมวดวิชาศึกษาทั่วไป/เฉพาะ/เลือกเสรี (จาก Lab 7B)
        ctype: str | None = None      # บังคับ/เลือก (จาก Lab 7B "type")
        note: str | None = None
        source_file: str | None = None
        page_number: int | None = Field(default=None, ge=1)

        @field_validator("code")
        @classmethod
        def _code_format(cls, v: str) -> str:
            v = v.strip()
            # รหัสวิชาจริง 8 หลัก หรือรหัสสล็อตวิชาเลือกภายในระบบ เช่น
            # ELEC-0602XXX / ELEC-SLOT-001
            slot_re = re.compile(r"^ELEC-[A-Z0-9_-]+$", re.I)
            if not (CODE_RE.match(v) or slot_re.match(v)):
                raise ValueError(
                    f"รหัสในแผนต้องเป็นตัวเลข 8 หลัก หรือรหัสสล็อต ELEC-* แต่ได้ '{v}'"
                )
            return v

    class Prerequisite(BaseModel):
        """ความสัมพันธ์วิชาบังคับก่อน / วิชาเรียนควบ"""
        code: str
        requires: str
        kind: str = "pre"       # pre = บังคับก่อน, co = เรียนควบ
        source_file: str | None = None
        page_number: int | None = Field(default=None, ge=1)

        @field_validator("kind")
        @classmethod
        def _kind_ok(cls, v: str) -> str:
            if v not in ("pre", "co"):
                raise ValueError("kind ต้องเป็น 'pre' หรือ 'co' เท่านั้น")
            return v

    class Program(BaseModel):
        """ข้อมูลหลักสูตรระดับบนสุด"""
        program_id: str
        name_th: str
        name_en: str | None = None
        degree: str | None = None
        total_credits: int = Field(ge=30, le=300)
        years: int = Field(ge=1, le=8)
        source_file: str | None = None
        page_number: int | None = Field(default=None, ge=1)

    class Curriculum(BaseModel):
        """เอกสารทั้งเล่มหนึ่งฉบับ"""
        program: Program
        courses: list[Course] = []
        plan: list[PlanItem] = []
        prerequisites: list[Prerequisite] = []

    return Curriculum


# ── SQL DDL ────────────────────────────────────────────────────────────
# เขียนแยกจาก Pydantic โดยตั้งใจ เพราะสองอย่างนี้ทำหน้าที่ต่างกัน
#   Pydantic ตรวจ "รูปร่างของข้อมูลแต่ละชิ้น"  (ก่อนเข้าฐานข้อมูล)
#   SQL constraint ตรวจ "ความสัมพันธ์ระหว่างชิ้น" (ตอนเข้าฐานข้อมูล)

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS program (
    program_id    TEXT PRIMARY KEY,
    name_th       TEXT NOT NULL,
    name_en       TEXT,
    degree        TEXT,
    total_credits INTEGER NOT NULL CHECK (total_credits BETWEEN 30 AND 300),
    years         INTEGER NOT NULL CHECK (years BETWEEN 1 AND 8),
    source_file   TEXT,
    page_number   INTEGER
);

CREATE TABLE IF NOT EXISTS course (
    code           TEXT PRIMARY KEY,
    name_th        TEXT NOT NULL,
    name_en        TEXT,
    credits        INTEGER NOT NULL CHECK (credits BETWEEN 0 AND 12),
    lecture_h      INTEGER,
    lab_h          INTEGER,
    self_h         INTEGER,
    description_th TEXT,
    source_file    TEXT,
    page_number    INTEGER
);

CREATE TABLE IF NOT EXISTS plan_item (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id TEXT NOT NULL REFERENCES program(program_id),
    year       INTEGER NOT NULL CHECK (year BETWEEN 0 AND 8),
    semester   INTEGER NOT NULL CHECK (semester BETWEEN 0 AND 3),
    code       TEXT NOT NULL,
    credits    INTEGER NOT NULL CHECK (credits BETWEEN 0 AND 12),
    alt_group  TEXT,
    category   TEXT,   -- หมวดวิชาศึกษาทั่วไป / หมวดวิชาเฉพาะ / หมวดวิชาเลือกเสรี
    ctype      TEXT,   -- บังคับ / เลือก
    note       TEXT,
    source_file TEXT,
    page_number INTEGER
);

CREATE TABLE IF NOT EXISTS prerequisite (
    code     TEXT NOT NULL,
    requires TEXT NOT NULL,
    kind     TEXT NOT NULL CHECK (kind IN ('pre','co')),
    source_file TEXT,
    page_number INTEGER,
    PRIMARY KEY (code, requires, kind)
);

CREATE INDEX IF NOT EXISTS ix_plan_sem ON plan_item(year, semester);
CREATE INDEX IF NOT EXISTS ix_plan_code ON plan_item(code);

-- VIEW ทำให้การถามคำถามง่ายขึ้นมาก
-- แทนที่ LLM จะต้อง JOIN เองทุกครั้ง เราเตรียมตารางแบนไว้ให้
-- นี่คือเหตุผลที่ VIEW มีอยู่ในโลก: ซ่อนความซับซ้อนของการ normalize
CREATE VIEW IF NOT EXISTS v_plan AS
SELECT p.id, p.year, p.semester, p.code, c.name_th, c.name_en,
       p.credits, p.alt_group, p.category, p.ctype, p.note,
       COALESCE(p.source_file, c.source_file) AS source_file,
       COALESCE(p.page_number, c.page_number) AS page_number
FROM plan_item p
LEFT JOIN course c ON c.code = p.code;

-- VIEW ที่สองนี้สำคัญกว่าที่เห็น
--
-- ถ้าให้ LLM เขียน SUM(credits) FROM v_plan เอง มันจะได้คำตอบผิด
-- เพราะวิชาเลือก "A หรือ B" มีสองแถว แต่ต้องนับหน่วยกิตครั้งเดียว
-- ปี 2 เทอม 1 จะได้ 12 แทนที่จะเป็น 9
--
-- ทางแก้ที่ผิดคือ ไปเขียนใน prompt ว่า "อย่าลืมหักวิชาเลือกออก"
-- เพราะ prompt เป็นการขอร้อง โมเดลจะลืมเป็นบางครั้ง แล้วเราจะจับไม่ได้
--
-- ทางแก้ที่ถูกคือ ย้ายตรรกะนี้มาไว้ใน VIEW
-- แล้ว LLM แค่ SELECT ธรรมดา ไม่มีโอกาสทำผิดเลย
-- หลักการ: อะไรที่ต้อง "ถูกเสมอ" ให้เขียนเป็นโค้ด ไม่ใช่เขียนเป็นคำสั่งให้ AI
-- หน่วยกิตต่อภาคเรียน — เฉพาะภาคเรียนจริง (year >= 1)
-- ปี 0 คือ "ที่พัก" ของวิชาเลือกที่ยืดหยุ่นเรื่องภาคเรียน (ดู convert_lab7b)
-- ไม่ใช่ภาคเรียนจริง จึงต้องกันออกจากคำถามประเภท MAX/MIN ต่อภาคเรียน
-- ไม่งั้นหน่วยกิตที่ "พัก" ไว้ที่ 0/0 อาจถูกนับเป็นภาคที่มีหน่วยกิตมากสุดผิด ๆ
CREATE VIEW IF NOT EXISTS v_semester_credits AS
SELECT year, semester, SUM(credits) AS credits, COUNT(*) AS n_courses,
       GROUP_CONCAT(DISTINCT source_file) AS source_files,
       GROUP_CONCAT(DISTINCT page_number) AS source_pages
FROM (
    SELECT year, semester,
           COALESCE(alt_group, 'x' || id) AS grp,
           MIN(credits) AS credits,
           MIN(source_file) AS source_file,
           MIN(page_number) AS page_number
    FROM plan_item
    WHERE year >= 1
    GROUP BY year, semester, COALESCE(alt_group, 'x' || id)
)
GROUP BY year, semester;

-- หน่วยกิตรวมทั้งปี (ข้ามหลายเทอม) — เกิดจากคำถาม held-out ที่ prompt เดิม
-- ไม่เคยเจอมาก่อน ("ปี 2 เรียนรวมทั้งปีกี่หน่วยกิต")
-- ต่อยอดจาก v_semester_credits ที่กันวิชาเลือกซ้ำและกันปี 0 ไว้แล้ว
CREATE VIEW IF NOT EXISTS v_year_credits AS
SELECT year, SUM(credits) AS credits, SUM(n_courses) AS n_courses,
       GROUP_CONCAT(source_files) AS source_files,
       GROUP_CONCAT(source_pages) AS source_pages
FROM v_semester_credits
GROUP BY year;

-- หน่วยกิตรวมแยกตามหมวดวิชา (หมวดวิชาศึกษาทั่วไป / เฉพาะ / เลือกเสรี)
-- ตั้งใจ "ไม่" กรอง year >= 1 ออก เพราะวิชาเลือกเสรีจำนวนมากถูกเก็บที่
-- ปี 0 (ยืดหยุ่นภาคเรียน) แต่ยังต้องถูกนับเข้าหมวดของมันอยู่ดี
CREATE VIEW IF NOT EXISTS v_category_credits AS
SELECT category, SUM(credits) AS credits, COUNT(*) AS n_courses,
       GROUP_CONCAT(DISTINCT source_file) AS source_files,
       GROUP_CONCAT(DISTINCT page_number) AS source_pages
FROM (
    SELECT category,
           COALESCE(alt_group, 'x' || id) AS grp,
           MIN(credits) AS credits,
           MIN(source_file) AS source_file,
           MIN(page_number) AS page_number
    FROM plan_item
    WHERE category IS NOT NULL
    GROUP BY category, COALESCE(alt_group, 'x' || id)
)
GROUP BY category;

-- หน่วยกิตรวมทั้งหลักสูตร (ทุกปีรวมปี 0) — ใช้เทียบกับ program.total_credits
-- ต้องไม่ใช้ SUM จาก v_semester_credits เพราะตัวนั้นกรองปี 0 ทิ้งไปแล้ว
CREATE VIEW IF NOT EXISTS v_total_credits AS
SELECT SUM(credits) AS credits,
       GROUP_CONCAT(DISTINCT source_file) AS source_files,
       GROUP_CONCAT(DISTINCT page_number) AS source_pages
FROM (
    SELECT COALESCE(alt_group, 'x' || id) AS grp, MIN(credits) AS credits,
           MIN(source_file) AS source_file, MIN(page_number) AS page_number
    FROM plan_item
    GROUP BY COALESCE(alt_group, 'x' || id)
);
"""


def cmd_schema(args) -> None:
    """เขียน JSON Schema และ SQL DDL ออกเป็นไฟล์ เพื่อใช้อ้างอิงและส่งงาน"""
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    Curriculum = build_models()
    (out / "curriculum.schema.json").write_text(
        json.dumps(Curriculum.model_json_schema(), ensure_ascii=False, indent=2),
        encoding="utf-8")
    (out / "schema.sql").write_text(DDL, encoding="utf-8")
    print(f"  เขียน {out}/curriculum.schema.json")
    print(f"  เขียน {out}/schema.sql")


# ═══════════════════════════════════════════════════════════════════════
#  ส่วนที่ 2 — สกัด JSON พร้อมวงจรซ่อม (repair loop)
# ═══════════════════════════════════════════════════════════════════════

def ollama_generate(prompt: str, fmt: Any | None = None,
                    timeout: int = 600, model: str | None = None,
                    num_ctx: int = 8192, num_predict: int = 4096) -> str:
    """เรียก Ollama บนเครื่องตัวเอง"""
    import requests
    payload: dict[str, Any] = {
        "model": model or MODEL_TEXT,
        # qwen3:4b บาง build ของ Ollama ยังไม่ปิด reasoning จาก field think
        # จึงใส่ /no_think ใน prompt ซ้ำเพื่อให้งาน SQL สั้นๆ คืนคำตอบใน content
        "messages": [{"role": "user", "content": prompt + "\n/no_think"}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.0, "num_ctx": num_ctx,
                    "num_predict": num_predict},
    }
    if fmt:
        payload["format"] = fmt
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    return (r.json().get("message") or {}).get("content", "")


def parse_json_loose(s: str) -> dict:
    """ดึง JSON ออกจากคำตอบ แม้จะมี <think> หรือ fence ปนมา"""
    s = re.sub(r"<think>.*?</think>", "", s, flags=re.S)
    s = re.sub(r"^```(?:json)?|```$", "", s.strip(), flags=re.M).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    start = s.find("{")
    if start < 0:
        return {}
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start:i + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


EXTRACT_PROMPT = """คุณคือผู้ช่วยแปลงเอกสารหลักสูตรเป็นข้อมูลที่มีโครงสร้าง

แปลงข้อความเล่มหลักสูตรต่อไปนี้เป็น JSON ตาม schema นี้เท่านั้น

{
  "program":  {"program_id":"", "name_th":"", "name_en":"", "degree":"",
               "total_credits":0, "years":0},
  "courses":  [{"code":"12345678","name_th":"","name_en":"","credits":0,
                "lecture_h":0,"lab_h":0,"self_h":0,"description_th":""}],
  "plan":     [{"year":1,"semester":1,"code":"12345678","credits":0,
                "alt_group":null,"note":null}],
  "prerequisites": [{"code":"12345678","requires":"12345678","kind":"pre"}]
}

กติกา
1. รหัสวิชาต้องเป็นตัวเลข 8 หลักเสมอ
2. ถ้าเล่มเขียนว่า "รหัส A หรือ รหัส B" ให้แตกเป็นสองรายการในแผน
   โดยใส่ alt_group เป็นข้อความเดียวกัน เช่น "elective_y3s1_1"
3. ค่าที่หาไม่พบ ให้ใส่ null ห้ามเดาและห้ามคำนวณเอง
4. semester ใช้ 1, 2 หรือ 3 (3 หมายถึงภาคฤดูร้อน)
5. ตอบเป็น JSON ล้วน ไม่ต้องมีคำอธิบาย

ข้อความ:
"""

REPAIR_PROMPT = """JSON ที่คุณสร้างมาไม่ผ่านการตรวจสอบ นี่คือรายการข้อผิดพลาด

{errors}

แก้เฉพาะจุดที่ระบุไว้ ห้ามแก้ส่วนอื่น ห้ามลบรายการที่ถูกต้องอยู่แล้ว
ถ้าข้อผิดพลาดเกิดเพราะข้อมูลไม่มีในเอกสารจริง ให้ลบรายการนั้นออก แทนที่จะเดาค่า

ตอบกลับเป็น JSON ฉบับสมบูรณ์ที่แก้แล้ว ไม่ต้องมีคำอธิบาย

JSON เดิม:
{payload}
"""


def format_errors(exc) -> str:
    """
    แปลง ValidationError ของ Pydantic เป็นข้อความที่ LLM แก้ตามได้จริง

    จุดสำคัญ: ต้องบอก "ตำแหน่ง" ให้ชัด (plan -> 12 -> code)
    ถ้าบอกแค่ "รหัสวิชาผิด" โมเดลจะไม่รู้ว่าต้องแก้รายการไหน
    แล้วมักจะรื้อทั้งก้อนใหม่ ซึ่งทำให้ข้อมูลที่ถูกอยู่แล้วพังไปด้วย
    """
    lines = []
    for e in exc.errors()[:25]:      # จำกัดไว้ไม่ให้ prompt ยาวเกิน
        loc = " -> ".join(str(x) for x in e["loc"])
        lines.append(f"- ตำแหน่ง {loc}: {e['msg']}")
    if len(exc.errors()) > 25:
        lines.append(f"- (และอีก {len(exc.errors()) - 25} ข้อ)")
    return "\n".join(lines)


def extract_with_repair(text: str, max_rounds: int = MAX_REPAIR_ROUNDS,
                        verbose: bool = True) -> tuple[dict, dict]:
    """
    สกัด JSON แล้ววนซ่อมจนผ่าน หรือจนครบจำนวนรอบ

    ทำไมต้องจำกัดจำนวนรอบ
        ถ้าปล่อยให้วนไม่จำกัด จะเจอกรณีที่โมเดลแก้วนไปวนมาไม่จบ
        (แก้ข้อ A แล้วข้อ B พัง แก้ข้อ B แล้วข้อ A พังอีก)
        การจำกัดรอบแล้ว "ยอมแพ้อย่างมีเกียรติ" คือพฤติกรรมที่ถูกต้อง
        ระบบที่ดีต้องรู้ว่าเมื่อไรควรส่งงานให้คนตรวจ

    คืน (data, meta) โดย meta บอกว่าใช้กี่รอบและผ่านหรือไม่
    """
    from pydantic import ValidationError
    Curriculum = build_models()

    raw = ollama_generate(EXTRACT_PROMPT + text, fmt="json")
    data = parse_json_loose(raw)
    meta = {"rounds": 0, "valid": False, "errors": []}

    for attempt in range(max_rounds + 1):
        try:
            model = Curriculum.model_validate(data)
            meta.update({"rounds": attempt, "valid": True, "errors": []})
            if verbose:
                print(f"  ผ่านการตรวจในรอบที่ {attempt}")
            return model.model_dump(), meta
        except ValidationError as exc:
            errs = format_errors(exc)
            meta["errors"] = errs.splitlines()
            if verbose:
                print(f"  รอบที่ {attempt}: พบข้อผิดพลาด {len(exc.errors())} ข้อ")
            if attempt >= max_rounds:
                meta.update({"rounds": attempt, "valid": False})
                if verbose:
                    print(f"  ! ซ่อมครบ {max_rounds} รอบแล้วยังไม่ผ่าน "
                          f"— ทำเครื่องหมายให้คนตรวจ")
                return data, meta
            raw = ollama_generate(
                REPAIR_PROMPT.format(
                    errors=errs,
                    payload=json.dumps(data, ensure_ascii=False)),
                fmt="json")
            new = parse_json_loose(raw)
            if new:
                data = new

    return data, meta


def cmd_extract(args) -> None:
    text = Path(args.input).read_text(encoding="utf-8")
    if args.max_chars and len(text) > args.max_chars:
        print(f"  ! ข้อความยาว {len(text):,} ตัวอักษร ตัดเหลือ {args.max_chars:,}")
        text = text[:args.max_chars]
    t0 = time.time()
    data, meta = extract_with_repair(text, args.rounds)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    meta["seconds"] = round(time.time() - t0, 1)
    out.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  เขียน {out}  ({meta['seconds']}s · "
          f"{'ผ่าน' if meta['valid'] else 'ต้องให้คนตรวจ'})")


# ── นำ JSON จาก Lab 7B มาใช้ต่อโดยไม่เรียก LLM ซ้ำ ─────────────────────────

def _credit_parts(value: Any) -> tuple[int, int | None, int | None, int | None]:
    """แปล 3(2-2-5) ของ Lab 7B เป็นคอลัมน์ตัวเลขของ Lab 8B"""
    text = str(value or "").strip()
    m = re.search(r"(\d+)\s*\(\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*\)", text)
    if m:
        return tuple(map(int, m.groups()))  # type: ignore[return-value]
    m = re.search(r"\d+", text)
    if not m:
        raise ValueError(f"อ่านหน่วยกิตไม่ได้: {value!r}")
    return int(m.group()), None, None, None


def _lab7b_codes(value: Any) -> list[str]:
    """ดึงรหัสวิชาจริง 8 หลักจากข้อความ Lab 7B"""
    return re.findall(r"(?<!\d)\d{8}(?!\d)", str(value or ""))


def _lab7b_wildcards(value: Any) -> list[str]:
    """ดึง wildcard เช่น 0602xxx / 90644xxx จาก Lab 7B"""
    raw = str(value or "")
    return re.findall(r"(?<![0-9A-Za-z])\d{3,}\s*[xX]+(?![0-9A-Za-z])", raw)


def _is_elective_wildcard(value: Any) -> bool:
    return bool(_lab7b_wildcards(value))


def _slot_code_from_wildcard(wildcard: str, disambiguator: str | None = None) -> str:
    """แปลง 0602xxx -> ELEC-0602XXX โดยคงข้อมูลต้นฉบับไว้ให้เห็นชัด

    ระวัง: หลายสล็อตวิชาเลือกที่ต่างกันจริง (เช่น "วิชาเลือกกลุ่มข้อมูล 1"
    กับ "...2") มักใช้ wildcard pattern เดียวกัน (เช่น "06026xxx" ทั้งคู่)
    ถ้าแปลงเป็นรหัสสล็อตจากแค่ wildcard string จะชนกันกลายเป็นสล็อตเดียว
    ทั้งที่ควรนับหน่วยกิตแยกกัน — disambiguator (เช่น slot id จาก GT
    ปกติ "DS_STAT_DE_ELECTIVE_1"/"..._2") ทำให้แต่ละสล็อตได้รหัสไม่ซ้ำกัน
    """
    cleaned = re.sub(r"\s+", "", str(wildcard)).upper()
    if disambiguator:
        tag = re.sub(r"[^A-Za-z0-9]+", "-", str(disambiguator)).strip("-").upper()
        return f"ELEC-{cleaned}-{tag}"
    return f"ELEC-{cleaned}"


def _slot_code_from_name(index: int, raw_code: str) -> str:
    """รองรับสล็อตที่เอกสารไม่ให้รหัสเลขเลย เช่น 'วิชาเลือกเสรี 1'"""
    return f"ELEC-SLOT-{index:03d}"


def _is_explicit_alternative(raw_code: Any) -> bool:
    """ให้ alt_group เฉพาะเมื่อช่อง code ระบุ A หรือ B จริง ๆ"""
    raw = str(raw_code or "")
    if not re.search(r"\bหรือ\b|\bor\b", raw, flags=re.I):
        return False
    return len(_lab7b_codes(raw)) >= 2


# 🟢 แทรกฟังก์ชันนี้ไว้ก่อน
def denormalize_gt(data: dict, target_plan: str = "coop") -> dict:
    """แปลง GT แบบ normalized (courses_master + curriculum_schedule) ให้เป็น
    {"program": ..., "courses": [...]} แบบเดิมที่ evaluate()/clean_gt() ใน
    lab7b_curriculum.py และ convert_lab7b() ด้านล่างนี้ใช้อยู่แล้ว

    Backward compatible: ถ้า data ไม่มีทั้ง courses_master และ
    curriculum_schedule ถือว่าเป็น flat schema เดิม คืนค่าเดิมกลับไปเฉยๆ

    target_plan: "coop" (ค่าเริ่มต้น) หรือ "no_coop" — ใช้ตัดสิน 2 เรื่อง
    1) รายการที่มี applicable_plans แต่ target_plan ไม่อยู่ในนั้น -> ข้าม
       (ไม่ใช่รายวิชาของแผนนี้)
    2) รายการที่มี schedule_by_plan (ตารางเรียนต่างกันตามแผน เช่น
       สหกิจศึกษาที่ปี 4/2 สำหรับ coop แต่ยืดหยุ่นสำหรับ no_coop) -> ใช้
       ปี/เทอม/ประเภท/หมายเหตุของแผนที่เลือกเท่านั้น ถ้าไม่มีของแผนนี้เลย
       (เช่น MAJOR_ELECTIVE_EXTRA_* ที่มีแค่ no_coop) ก็ข้ามเช่นกัน

    หมายเหตุ field name: courses_master คีย์รายวิชาด้วย "code" (ไม่ใช่
    "course_code") — จุดนี้เป็นจุดที่โค้ดเดิมพลาดมาก่อน ทำให้ name_th/
    credits ว่างเปล่าทุกแถวเพราะ lookup ไม่เจอ
    """
    if "courses_master" not in data and "curriculum_schedule" not in data:
        return data

    master_map = {c.get("code"): c for c in data.get("courses_master") or [] if c.get("code")}
    source_file = data.get("source_file")
    source_pages = (data.get("source_pages_by_plan") or {}).get(target_plan) or {}

    flat_courses: list[dict] = []
    for sched in data.get("curriculum_schedule") or []:
        code = sched.get("course_code")
        if not code:
            continue

        schedule_by_plan = sched.get("schedule_by_plan")
        if schedule_by_plan:
            plan_sched = schedule_by_plan.get(target_plan)
            if plan_sched is None:
                continue  # สล็อตนี้ไม่มีอยู่ในแผนที่เลือก
            year = plan_sched.get("year")
            semester = plan_sched.get("semester")
            ctype = plan_sched.get("type", sched.get("type"))
            note = plan_sched.get("note", sched.get("note"))
            flexible = plan_sched.get("flexible_year_semester")
        else:
            applicable = sched.get("applicable_plans")
            if applicable is not None and target_plan not in applicable:
                continue  # รายวิชานี้ไม่อยู่ในแผนที่เลือก
            year = sched.get("year")
            semester = sched.get("semester")
            ctype = sched.get("type")
            note = sched.get("note")
            flexible = sched.get("flexible_year_semester")

        term_key = f"{year}/{semester}"
        page_number = (
            (sched.get("page_number_by_plan") or {}).get(target_plan)
            or sched.get("page_number")
            or source_pages.get(term_key)
        )

        # courses_master คีย์ด้วยรหัสเดี่ยว แต่ curriculum_schedule บางแถวใช้
        # รหัสรวมแบบ "06026259 หรือ 06026260" (สหกิจในไทย/ต่างประเทศ เลือก
        # อย่างใดอย่างหนึ่ง) — lookup ตรงตัวจะไม่เจอ ต้องแตกรหัสในสตริงนั้น
        # ออกมาแล้วลองทีละตัวแทน ไม่งั้นจะ fallback ไปใช้หน่วยกิตของกลุ่ม
        # วิชาเลือกยืดหยุ่นทั่วไปผิด ๆ (3 หน่วยกิต แทนที่จะเป็น 6)
        master_info = master_map.get(code) or {}
        if not master_info:
            import re
            for sub_code in re.findall(r"(?<!\d)\d{8}(?!\d)", code):
                if sub_code in master_map:
                    master_info = master_map[sub_code]
                    break

        flat_courses.append({
            "code": code,
            "name_th": sched.get("name_th") or master_info.get("name_th"),
            "name_en": sched.get("name_en") or master_info.get("name_en"),
            "credits": sched.get("credits") or master_info.get("credits"),
            "prerequisite": master_info.get("prerequisite"),
            "year": year,
            "semester": semester,
            "category": sched.get("category") or master_info.get("category"),
            "type": ctype,
            "note": note,
            "flexible_year_semester": flexible,
            "slot": sched.get("slot"),
            "source_file": sched.get("source_file") or source_file,
            "page_number": page_number,
        })

    return {
        "program": data.get("program"),
        "courses": flat_courses,
    }


def convert_lab7b(data: dict, *, program_id: str | None = None,
                  program_name: str | None = None,
                  total_credits: int | None = None,
                  years: int | None = None,
                  target_plan: str = "coop",
                  supplemental_courses: list[dict] | None = None) -> tuple[dict, dict]:
    """
    แปล schema ผลลัพธ์ Lab 7B เป็น Lab 8B ด้วยกฎคงที่ โดยไม่เรียก LLM

    รหัส wildcard เช่น 06026xxx ไม่มีตัวตนวิชาจริงในตาราง course จึงไม่เดารหัสให้
    แต่บันทึกลง conversion report ทุกรายการ
    """
    # --- เพิ่มบรรทัดนี้ที่ต้นฟังก์ชัน ---
    if "courses_master" in data:
        data = denormalize_gt(data, target_plan=target_plan)
    
    elif "ocr_data" in data and "courses" not in data:
        extracted_courses = []
        for item in data.get("ocr_data", []):
            if item.get("course_code"):
                c = dict(item)
                c["code"] = c.pop("course_code")
                extracted_courses.append(c)
        data["courses"] = extracted_courses
    # -----------------------------------

    warnings: list[str] = []
    course_by_code: dict[str, dict] = {}
    plan: list[dict] = []
    prerequisites: list[dict] = []
    seen_plan: set[tuple] = set()
    seen_pre: set[tuple] = set()
    skipped_wildcards = 0
    converted_wildcards = 0
    skipped_flexible = 0
    wildcard_fallback_counts: dict[tuple[str, int, int], int] = defaultdict(int)

    for index, src in enumerate(data.get("courses") or []):
        raw_code = str(src.get("code") or "").strip()
        source_names = " ".join(str(src.get(k) or "") for k in ("name_th", "name_en"))
        if re.search(r"วิชาเลือกเสรี|FREE\s+ELECTIVE", source_names, re.I):
            raw_code = str(src.get("name_th") or "FREE ELECTIVE").strip()
        real_codes = _lab7b_codes(raw_code)
        wildcard_codes = _lab7b_wildcards(raw_code)

        # รหัสสำหรับ plan:
        # - รหัสจริง -> ใช้รหัสเดิม
        # - wildcard เช่น 0602xxx -> สร้าง ELEC-0602XXX เป็น "สล็อต"
        # - ไม่มีรหัสเลข -> สร้าง ELEC-SLOT-NNN เป็น "สล็อต"
        if real_codes:
            plan_codes = real_codes[:]
            course_codes = real_codes[:]
        elif wildcard_codes:
            disambiguator = src.get("slot")
            if not disambiguator:
                label = str(src.get("name_th") or src.get("name_en") or "")
                numbers = re.findall(r"(?<!\d)(\d{1,2})(?!\d)", label)
                number = numbers[-1] if numbers else None
                if number:
                    disambiguator = f"SLOT-{number}"
                else:
                    try:
                        src_year = int(src.get("year"))
                        src_semester = int(src.get("semester"))
                    except (TypeError, ValueError):
                        src_year = src_semester = 0
                    counter_key = ("|".join(wildcard_codes), src_year, src_semester)
                    wildcard_fallback_counts[counter_key] += 1
                    disambiguator = (
                        f"TERM-{src_year}-{src_semester}-ROW-"
                        f"{wildcard_fallback_counts[counter_key]}"
                        if src_year > 0 and src_semester > 0
                        else f"SOURCE-ROW-{index + 1}"
                    )
            plan_codes = [_slot_code_from_wildcard(x, disambiguator) for x in wildcard_codes]
            course_codes = []
            converted_wildcards += len(plan_codes)
        elif raw_code:
            plan_codes = [_slot_code_from_name(index + 1, raw_code)]
            course_codes = []
            converted_wildcards += 1
            warnings.append(
                f"courses[{index}] ไม่ใช่รหัสเลข 8 หลัก "
                f"— เก็บเป็นสล็อต {plan_codes[0]} จาก '{raw_code}'"
            )
        else:
            skipped_wildcards += 1
            warnings.append(f"courses[{index}] ไม่มีรหัส/ชื่อสล็อต: ข้ามรายการ")
            continue

        try:
            credit, lecture, lab, self_h = _credit_parts(src.get("credits"))
        except ValueError as exc:
            warnings.append(f"{raw_code}: {exc}; ข้ามรายการ")
            continue

        if "หรือ" in str(src.get("credits") or ""):
            warnings.append(f"{raw_code}: หน่วยกิตมีหลายแบบ; ใช้แบบแรก")

        # เฉพาะรหัสวิชาจริงเท่านั้นที่เข้า course table
        for code in course_codes:
            candidate = {
                "code": code,
                "name_th": str(src.get("name_th") or code).strip(),
                "name_en": (str(src["name_en"]).replace("\n", " ").strip()
                            if src.get("name_en") else None),
                "credits": credit,
                "lecture_h": lecture,
                "lab_h": lab,
                "self_h": self_h,
                "description_th": src.get("description_th"),
                "source_file": src.get("source_file"),
                "page_number": src.get("page_number"),
            }
            old = course_by_code.get(code)
            if old is None:
                course_by_code[code] = candidate
            else:
                for key, value in candidate.items():
                    if old.get(key) in (None, "") and value not in (None, ""):
                        old[key] = value

        try:
            year = int(src.get("year"))
            semester = int(src.get("semester"))
        except (TypeError, ValueError):
            year = semester = 0
        # category/type เก็บเป็นคอลัมน์จริง ไม่ยุบรวมกับ note อีกต่อไป
        # เหตุผล: คำถามอย่าง "หมวดวิชาเลือกเสรีมีกี่หน่วยกิต" ต้อง SELECT
        # แยกหมวดได้ ถ้ายุบเป็น note ข้อความเดียว SQL ทำได้แค่ LIKE เดา
        category = str(src.get("category")).strip() if src.get("category") else None
        ctype = str(src.get("type")).strip() if src.get("type") else None
        note = str(src.get("note")).strip() if src.get("note") else None
        catalog_only = False
        if (
            target_plan == "no_coop"
            and (year, semester) == (0, 0)
            and re.search(r"สหกิจ|COOPERATIVE", source_names, re.I)
            and re.search(r"เฉพาะ.*สหกิจ|ONLY.*COOPERATIVE", note or "", re.I)
        ):
            catalog_only = True
            skipped_flexible += 1
            warnings.append(f"{raw_code}: ไม่นับวิชาสหกิจในแผน no_coop")
        if not (1 <= year <= 8 and 1 <= semester <= 3):
            # Flat ground-truth sheets append the elective course catalogue
            # after the academic plan.  Those rows describe choices available
            # to a wildcard slot; they are not one required slot each and must
            # therefore enter `course` but not `plan_item`.
            if (year, semester) == (0, 0) and src.get("flexible_year_semester") and real_codes:
                catalog_only = True
                skipped_flexible += 1
                warnings.append(
                    f"{raw_code}: เก็บเป็นรายวิชาในคลังวิชาเลือก; ไม่นับเป็นสล็อตในแผน"
                )
            # ⚠️ เดิมโค้ดจุดนี้ "ข้าม" แถวนี้ทั้งแถว (skipped_flexible += 1
            # แล้วไม่ใส่ลง plan เลย) ซึ่งทำให้หน่วยกิตของวิชาเลือกที่ลงได้
            # หลายภาค (flexible_year_semester) หายไปจากผลรวมทั้งหมด
            # CHK1 จึงเตือนผิดเสมอเมื่อหลักสูตรมีวิชากลุ่มนี้ ทั้งที่ข้อมูลถูก
            #
            # ทางแก้: เก็บไว้ในแผนด้วย year=0, semester=0 เป็น "ที่พัก" สำหรับ
            # หน่วยกิตที่ยังไม่ผูกกับภาคเรียนใดภาคเรียนหนึ่ง แล้วบันทึกตัวเลือก
            # ภาคเรียนจริงไว้ใน note เพื่อให้คนอ่านย้อนกลับไปดูได้
            # v_semester_credits / v_year_credits กรอง year=0 ออกเพราะไม่ใช่
            # ภาคเรียนจริง แต่ CHK1 (หน่วยกิตรวมทั้งหลักสูตร) และ
            # v_category_credits ยังนับรวมอยู่ ซึ่งถูกต้องกว่า
            if not catalog_only:
                skipped_flexible += 1
                fx = src.get("flexible_year_semester")
                flex_note = f"ยืดหยุ่นภาคเรียน: {fx}" if fx else "ยืดหยุ่นภาคเรียน (ไม่ระบุตัวเลือก)"
                note = f"{note} | {flex_note}" if note else flex_note
                warnings.append(f"{raw_code}: ปี/เทอมที่สกัดได้ไม่ถูกต้อง ({year}/{semester}) "
                                f"— เก็บไว้ที่ปี 0/เทอม 0 แทนการทิ้ง, {flex_note}")
            year = semester = 0
        # จับ alt_group เฉพาะเมื่อ "ช่อง code" ระบุ A หรือ B จริง ๆ
        # ไม่จับกลุ่มเพียงเพราะ OCR รวมหลายรหัส/ชื่อไว้ในฟิลด์เดียว
        inferred_alt_group = None
        if re.search(r"สหกิจ|COOPERATIVE", source_names, re.I) and credit >= 6:
            inferred_alt_group = (
                f"coop-alternative-{src.get('source_file') or 'source'}-"
                f"{src.get('page_number') or f'{year}-{semester}'}"
            )
        alt_group = src.get("alt_group") or inferred_alt_group or (
            "lab7b_alt_" + "|".join(sorted(plan_codes))
            if len(plan_codes) > 1 and _is_explicit_alternative(raw_code)
            else None
        )
        if not catalog_only:
            for code in plan_codes:
                key = (year, semester, code, alt_group)
                if key not in seen_plan:
                    plan.append({"year": year, "semester": semester,
                                 "code": code, "credits": credit,
                                 "alt_group": alt_group, "category": category,
                                 "ctype": ctype, "note": note,
                                 "source_file": src.get("source_file"),
                                 "page_number": src.get("page_number")})
                    seen_plan.add(key)

        pre_codes = _lab7b_codes(src.get("prerequisite"))
        for code in real_codes:
            for required in pre_codes:
                if required == code:
                    warnings.append(f"{code}: ข้าม prerequisite ที่อ้างถึงตัวเอง")
                    continue
                key = (code, required, "pre")
                if key not in seen_pre:
                    prerequisites.append({"code": code, "requires": required,
                                          "kind": "pre",
                                          "source_file": src.get("source_file"),
                                          "page_number": src.get("page_number")})
                    seen_pre.add(key)

    # The IT curriculum prints three specialization bundles in the same table:
    # students choose one bundle, rather than taking every displayed course.
    # Pair courses by their ordinal position inside each bundle so totals retain
    # all alternatives while counting two slots in Y2/S2 and three in Y3/S1.
    pid_hint = str(program_id or data.get("program") or "").upper()
    if pid_hint.startswith("IT-"):
        it_specialization_slots = {
            (2, 2): {
                "06016414": 1, "06016419": 1, "06016424": 1,
                "06016415": 2, "06016420": 2, "06016425": 2,
            },
            (3, 1): {
                "06016416": 1, "06016421": 1, "06016426": 1,
                "06016417": 2, "06016422": 2, "06016427": 2,
                "06016418": 3, "06016423": 3,
            },
        }
        for item in plan:
            term = (item["year"], item["semester"])
            slot = it_specialization_slots.get(term, {}).get(item["code"])
            if slot:
                item["alt_group"] = f"it-specialization-y{term[0]}s{term[1]}-slot-{slot}"

    supplemental_added = 0
    for index, src in enumerate(supplemental_courses or []):
        code = str(src.get("code") or "").strip()
        if not re.fullmatch(r"\d{8}", code):
            warnings.append(f"supplemental_courses[{index}]: ข้ามรหัส {code!r} ที่ไม่ใช่เลข 8 หลัก")
            continue
        try:
            credit, lecture, lab, self_h = _credit_parts(src.get("credits"))
        except ValueError as exc:
            warnings.append(f"supplemental_courses[{index}] {code}: {exc}")
            continue
        candidate = {
            "code": code,
            "name_th": str(src.get("name_th") or code).strip(),
            "name_en": (str(src["name_en"]).replace("\n", " ").strip()
                        if src.get("name_en") else None),
            "credits": credit,
            "lecture_h": lecture,
            "lab_h": lab,
            "self_h": self_h,
            "description_th": src.get("description_th"),
            "source_file": src.get("source_file"),
            "page_number": src.get("page_number"),
        }
        old = course_by_code.get(code)
        if old is None:
            course_by_code[code] = candidate
            supplemental_added += 1
        else:
            for key, value in candidate.items():
                if old.get(key) in (None, "") and value not in (None, ""):
                    old[key] = value

    # Use the total printed at the bottom of each term table as an independent
    # completeness check.  If OCR missed a row, preserve the missing credits as
    # an explicit elective slot rather than pretending the extracted list is
    # complete.  Over-counts are never hidden and continue to fail CHK1/CHK7.
    for declared_term in data.get("term_totals") or []:
        try:
            term = (int(declared_term["year"]), int(declared_term["semester"]))
            expected = int(declared_term["credits"])
        except (KeyError, TypeError, ValueError):
            continue
        groups: dict[str, int] = {}
        for i, item in enumerate(plan):
            if (item["year"], item["semester"]) != term:
                continue
            group = item.get("alt_group") or f"row-{i}"
            groups[group] = min(groups.get(group, item["credits"]), item["credits"])
        actual = sum(groups.values())
        missing = expected - actual
        if missing <= 0:
            if missing < 0:
                warnings.append(
                    f"ปี {term[0]}/{term[1]} สกัดได้ {actual} หน่วยกิต "
                    f"แต่ยอดพิมพ์ในตารางคือ {expected}; ไม่ปรับยอดเกินอัตโนมัติ"
                )
            continue
        if missing % 3:
            warnings.append(
                f"ปี {term[0]}/{term[1]} ขาด {missing} หน่วยกิตซึ่งไม่ลงตัวด้วยสล็อต 3 หน่วยกิต"
            )
            continue
        for slot_no in range(1, missing // 3 + 1):
            code = f"ELEC-RECOVERED-Y{term[0]}S{term[1]}-{slot_no}"
            plan.append({
                "year": term[0], "semester": term[1], "code": code, "credits": 3,
                "alt_group": None, "category": None, "ctype": "เลือก",
                "note": "สล็อตกู้คืนจากยอดรวมที่พิมพ์ในตาราง; OCR ไม่พบรายละเอียดแถว",
                "source_file": declared_term.get("source_file"),
                "page_number": declared_term.get("page_number"),
            })
            seen_plan.add((term[0], term[1], code, None))
        warnings.append(
            f"ปี {term[0]}/{term[1]} OCR ขาด {missing} หน่วยกิต "
            f"— เพิ่มสล็อตจากยอดรวม {expected} ที่พิมพ์ในตาราง"
        )

    max_year = max((p["year"] for p in plan), default=4)
    effective_years = years or max_year
    if total_credits is None:
        groups: dict[tuple, int] = {}
        for i, item in enumerate(plan):
            group = item.get("alt_group") or f"row_{i}"
            groups[(item["year"], item["semester"], group)] = item["credits"]
        total_credits = sum(groups.values())
        warnings.append(f"ไม่ได้ระบุ --total-credits; คำนวณจากแผนที่แปลได้ = {total_credits}")
    if not 30 <= total_credits <= 300:
        raise ValueError(f"หน่วยกิตรวม {total_credits} อยู่นอกช่วง 30..300; "
                         "ระบุ --total-credits จากเล่มหลักสูตร")

    pid = str(program_id or data.get("program") or "curriculum").strip()
    sourced_rows = [c for c in data.get("courses") or [] if c.get("source_file")]
    program_source = sourced_rows[0].get("source_file") if sourced_rows else None
    source_pages = [c.get("page_number") for c in sourced_rows if c.get("page_number")]
    result = {
        "program": {
            "program_id": pid,
            "name_th": str(program_name or data.get("program") or pid).strip(),
            "name_en": None,
            "degree": None,
            "total_credits": total_credits,
            "years": effective_years,
            "source_file": program_source,
            "page_number": max(source_pages) if source_pages else None,
        },
        "courses": list(course_by_code.values()),
        "plan": plan,
        "prerequisites": prerequisites,
    }
    Curriculum = build_models()
    result = Curriculum.model_validate(result).model_dump()
    report = {
        "source_courses": len(data.get("courses") or []),
        "converted_courses": len(result["courses"]),
        "plan_items": len(result["plan"]),
        "prerequisites": len(result["prerequisites"]),
        "skipped_wildcards": skipped_wildcards,
        "converted_wildcards": converted_wildcards,
        "skipped_flexible_plan_items": skipped_flexible,
        "supplemental_courses_added": supplemental_added,
        "warnings": warnings,
    }
    return result, report


def cmd_import_lab7b(args) -> None:
    src = Path(args.input)
    data = json.loads(src.read_text(encoding="utf-8"))
    supplemental_courses = None
    if args.general_education:
        catalog_path = Path(args.general_education)
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        supplemental_courses = []
        for row in catalog.get("courses") or []:
            item = dict(row)
            item.setdefault("source_file", catalog_path.name)
            supplemental_courses.append(item)
    converted, report = convert_lab7b(
        data,
        program_id=args.program_id,
        program_name=args.program_name,
        total_credits=args.total_credits,
        years=args.years,
        target_plan=args.target_plan,
        supplemental_courses=supplemental_courses,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(converted, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path = out.with_suffix(".conversion.json")
    meta_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  แปล Lab 7B JSON -> Lab 8B JSON โดยไม่เรียก LLM")
    print(f"  เขียน {out}")
    print(f"  รายงาน {meta_path}")
    print(f"    course={report['converted_courses']}  plan={report['plan_items']}  "
          f"prerequisite={report['prerequisites']}")
    if report["supplemental_courses_added"]:
        print(f"    เพิ่มรายวิชาจากคลังเสริม {report['supplemental_courses_added']} รายการ")
    if report["warnings"]:
        print(f"    ต้องตรวจ {len(report['warnings'])} รายการ — ดูได้ใน {meta_path}")


# ═══════════════════════════════════════════════════════════════════════
#  ส่วนที่ 3 — โหลดเข้าฐานข้อมูล
# ═══════════════════════════════════════════════════════════════════════

def open_db(path: str | Path, readonly: bool = False) -> sqlite3.Connection:
    """
    เปิดฐานข้อมูล

    readonly=True ใช้ตอนตอบคำถาม ซึ่งเป็นด่านความปลอดภัยชั้นที่หนึ่ง
    ต่อให้ LLM สร้าง SQL ที่เป็น DROP TABLE ขึ้นมา ฐานข้อมูลก็ปฏิเสธเอง
    เราไม่พึ่ง prompt ในการป้องกัน เพราะ prompt เป็นเพียงการขอร้อง
    """
    if readonly:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def cmd_load(args) -> None:
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    db = Path(args.database)
    if db.exists() and args.replace:
        db.unlink()
    db.parent.mkdir(parents=True, exist_ok=True)

    conn = open_db(db)
    conn.executescript(DDL)

    prog = data["program"]
    conn.execute(
        "INSERT OR REPLACE INTO program (program_id, name_th, name_en, degree,"
        " total_credits, years, source_file, page_number) VALUES (?,?,?,?,?,?,?,?)",
        (prog["program_id"], prog["name_th"], prog.get("name_en"),
         prog.get("degree"), prog["total_credits"], prog["years"],
         prog.get("source_file"), prog.get("page_number")))

    for c in data.get("courses", []):
        conn.execute("INSERT OR REPLACE INTO course VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (c["code"], c["name_th"], c.get("name_en"), c["credits"],
                      c.get("lecture_h"), c.get("lab_h"), c.get("self_h"),
                      c.get("description_th"), c.get("source_file"),
                      c.get("page_number")))

    conn.execute("DELETE FROM plan_item WHERE program_id = ?", (prog["program_id"],))
    for p in data.get("plan", []):
        conn.execute(
            "INSERT INTO plan_item (program_id, year, semester, code, credits,"
            " alt_group, category, ctype, note, source_file, page_number)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (prog["program_id"], p["year"], p["semester"], p["code"],
             p["credits"], p.get("alt_group"), p.get("category"),
             p.get("ctype"), p.get("note"), p.get("source_file"),
             p.get("page_number")))

    for r in data.get("prerequisites", []):
        conn.execute("INSERT OR REPLACE INTO prerequisite VALUES (?,?,?,?,?)",
                     (r["code"], r["requires"], r.get("kind", "pre"),
                      r.get("source_file"), r.get("page_number")))

    conn.commit()
    n = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
         for t in ("program", "course", "plan_item", "prerequisite")}
    conn.close()
    print(f"  โหลดเข้า {db} แล้ว")
    for t, c in n.items():
        print(f"    {t:<14} {c:>5} แถว")


# ═══════════════════════════════════════════════════════════════════════
#  ส่วนที่ 4 — ตรวจความสอดคล้องของข้อมูลในฐานข้อมูล 7 ข้อ
# ═══════════════════════════════════════════════════════════════════════
#
#  Pydantic ตรวจได้แค่ "แต่ละชิ้นหน้าตาถูกไหม"
#  แต่ตรวจไม่ได้ว่า "ชิ้นทั้งหมดรวมกันแล้วสมเหตุสมผลไหม"
#  เช่น รหัสวิชา 8 หลักถูกรูปแบบ แต่เป็นวิชาที่ไม่มีอยู่ในเล่ม — Pydantic ผ่าน
#
#  บทเรียนสำคัญจาก Lab 7A/7B ที่นำมาใช้ตรงนี้
#      กฎที่เตือนผิดบ่อย แย่กว่าไม่มีกฎเลย
#      เพราะเมื่อคนเห็นคำเตือนผิดสามครั้ง เขาจะเลิกอ่านคำเตือนทั้งหมด
#      รวมถึงครั้งที่สี่ที่เป็นของจริง  (alarm fatigue)
#  กฎทั้ง 7 ข้อนี้จึงถูกออกแบบให้รู้จักข้อยกเว้นที่มีอยู่จริงในหลักสูตร
# ═══════════════════════════════════════════════════════════════════════

def _sem_credits(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """
    หน่วยกิตรวมต่อภาคเรียน โดยนับ alt_group ครั้งเดียว

    ถ้าไม่มี alt_group จะนับวิชาเลือก "A หรือ B" เป็นสองวิชา
    ทำให้หน่วยกิตเกินจริงทุกภาคที่มีวิชาเลือก
    """
    return conn.execute(
        "SELECT year, semester, credits, n_courses "
        "FROM v_semester_credits ORDER BY year, semester").fetchall()


def verify_db(conn: sqlite3.Connection) -> list[dict]:
    """รันการตรวจทั้ง 7 ข้อ คืนรายการผลลัพธ์"""
    results: list[dict] = []

    def add(cid, name, ok, detail=""):
        results.append({"id": cid, "name": name, "ok": ok, "detail": detail})

    prog = conn.execute("SELECT * FROM program LIMIT 1").fetchone()
    if prog is None:
        add("CHK0", "มีข้อมูลหลักสูตร", False, "ตาราง program ว่าง")
        return results

    # ── CHK1 หน่วยกิตรวมของแผน ต้องเท่ากับที่หลักสูตรประกาศ ────────
    # ใช้ v_total_credits (รวมปี 0 ด้วย) ไม่ใช่ผลรวมจาก v_semester_credits
    # เพราะ view หลังกรองปี 0 (วิชายืดหยุ่นภาคเรียน) ทิ้งไปแล้วโดยตั้งใจ
    total = conn.execute("SELECT credits FROM v_total_credits").fetchone()["credits"] or 0
    declared = prog["total_credits"]
    # หมายเหตุ: เดิมโค้ดจุดนี้เช็ก note LIKE '%เลือกเสรี%' เพื่อ "ขอโทษ" กรณี
    # หน่วยกิตไม่ตรง แต่นั่นแก้ปลายเหตุ ต้นเหตุจริงคือ convert_lab7b เคยทิ้ง
    # วิชายืดหยุ่นภาคเรียนไปทั้งแถว ตอนนี้แก้ที่ต้นเหตุแล้ว (เก็บไว้ที่ปี 0)
    # เช็กนี้จึงเหลือไว้เป็นข้อมูลประกอบเฉยๆ ไม่ใช่ข้อยกเว้นของ ok อีกต่อไป
    free = conn.execute(
        "SELECT COUNT(*) FROM plan_item WHERE category = 'หมวดวิชาเลือกเสรี'"
    ).fetchone()[0]
    raw_total = conn.execute(
        "SELECT COALESCE(SUM(credits), 0) FROM plan_item"
    ).fetchone()[0]

    collapsed = conn.execute("""
        SELECT alt_group, COUNT(*) AS n,
               MIN(credits) AS counted_credits,
               SUM(credits) AS raw_credits,
               GROUP_CONCAT(code, ', ') AS codes
        FROM plan_item
        WHERE alt_group IS NOT NULL
        GROUP BY alt_group
        ORDER BY alt_group
    """).fetchall()

    collapse_detail = ""
    if collapsed:
        parts = []
        for r in collapsed:
            saved = (r["raw_credits"] or 0) - (r["counted_credits"] or 0)
            parts.append(
                f"{r['codes']} ดิบ {r['raw_credits']} -> นับ {r['counted_credits']} "
                f"(หัก {saved})"
            )
        collapse_detail = " · alt_group: " + " | ".join(parts[:5])

    ok = (total == declared)
    add("CHK1", "หน่วยกิตรวมของแผน = หน่วยกิตที่หลักสูตรประกาศ", ok,
        f"แผนรวม {total} · ดิบ {raw_total} · ประกาศไว้ {declared}"
        + (f" · มีวิชาเลือกเสรี {free} รายการ" if free else "")
        + collapse_detail)

    # ── CHK2 ทุกรหัสในแผน ต้องมีคำอธิบายรายวิชาในเล่ม ───────────────
    orphan = conn.execute("""
        SELECT DISTINCT p.code FROM plan_item p
        LEFT JOIN course c ON c.code = p.code
        WHERE c.code IS NULL
          AND p.code NOT LIKE 'ELEC-%'
    """).fetchall()
    add("CHK2", "ทุกรหัสวิชาในแผน มีคำอธิบายรายวิชา", not orphan,
        "ไม่พบคำอธิบายของ: " + ", ".join(r["code"] for r in orphan[:8])
        + (f" (และอีก {len(orphan) - 8})" if len(orphan) > 8 else "")
        if orphan else "ครบทุกรหัส")

    # ── CHK3 รูปแบบรหัสวิชา ────────────────────────────────────────
    # ยกเว้นรหัสที่มีเครื่องหมาย "-" เพราะเป็นรหัสสมมติสำหรับสล็อต
    # "วิชาเลือก" ต่างๆ ที่ไม่ผูกกับวิชาจริงตัวเดียว (เช่น ELEC-DA สำหรับ
    # กลุ่มวิชาเฉพาะด้านเลือก, LANG-ELEC/GENED-ELEC/FREE-ELEC สำหรับสล็อต
    # เลือกเสรีต่างๆ) รหัสวิชาจริงตามระบบทะเบียนเป็นตัวเลขล้วนเสมอ
    # จึงไม่มีทางชนกับ "-" โดยบังเอิญ
    bad = conn.execute("""
        SELECT code FROM (
            SELECT code FROM course UNION SELECT code FROM plan_item
        )
        WHERE (code GLOB '*[^0-9]*' OR LENGTH(code) <> 8)
          AND code NOT LIKE '%-%'
    """).fetchall()
    add("CHK3", "รหัสวิชาเป็นตัวเลข 8 หลักทุกรายการ (ยกเว้นรหัสสล็อตวิชาเลือกที่มี -)",
        not bad,
        "ผิดรูปแบบ: " + ", ".join(r["code"] for r in bad[:8]) if bad else "ถูกต้องทุกรายการ")

    # ── CHK4 หน่วยกิตในแผน ต้องตรงกับหน่วยกิตในคำอธิบายรายวิชา ──────
    mismatch = conn.execute("""
        SELECT p.code, p.credits AS plan_cr, c.credits AS course_cr
        FROM plan_item p JOIN course c ON c.code = p.code
        WHERE p.credits <> c.credits
    """).fetchall()
    add("CHK4", "หน่วยกิตในแผน ตรงกับคำอธิบายรายวิชา", not mismatch,
        "; ".join(f"{r['code']} แผน {r['plan_cr']} แต่คำอธิบาย {r['course_cr']}"
                  for r in mismatch[:5]) if mismatch else "ตรงกันทุกรายการ")

    # ── CHK5 วิชาบังคับก่อน ต้องอยู่ภาคเรียนที่มาก่อนจริง ────────────
    #    ใช้ (year*10 + semester) เป็นลำดับเวลาอย่างง่าย
    viol = conn.execute("""
        SELECT r.code, r.requires,
               a.year || '/' || a.semester AS at_course,
               b.year || '/' || b.semester AS at_prereq
        FROM prerequisite r
        JOIN plan_item a ON a.code = r.code
        JOIN plan_item b ON b.code = r.requires
        WHERE r.kind = 'pre'
          AND (b.year * 10 + b.semester) >= (a.year * 10 + a.semester)
    """).fetchall()
    add("CHK5", "วิชาบังคับก่อน อยู่ภาคเรียนก่อนวิชาที่อ้างถึง", not viol,
        "; ".join(f"{r['code']} ({r['at_course']}) ต้องเรียน {r['requires']} "
                  f"({r['at_prereq']}) มาก่อน" for r in viol[:5])
        if viol else "ลำดับถูกต้องทุกคู่")

    # ── CHK6 ห้ามมีวิชาซ้ำในภาคเรียนเดียวกัน ───────────────────────
    dup = conn.execute("""
        SELECT year, semester, code, COUNT(*) AS n
        FROM plan_item
        WHERE alt_group IS NULL          -- วิชาเลือกกลุ่มเดียวกันไม่นับเป็นซ้ำ
        GROUP BY year, semester, code
        HAVING n > 1
    """).fetchall()
    add("CHK6", "ไม่มีวิชาซ้ำในภาคเรียนเดียวกัน", not dup,
        "; ".join(f"{r['code']} ที่ปี {r['year']}/{r['semester']} ซ้ำ {r['n']} ครั้ง"
                  for r in dup[:5]) if dup else "ไม่มีรายการซ้ำ")

    # ── CHK7 ภาระหน่วยกิตต่อภาคเรียน อยู่ในเกณฑ์ ────────────────────
    #    ข้อยกเว้นสำคัญ: ภาคสหกิจศึกษา / ฝึกงาน มีวิชาเดียว 6 หน่วยกิต
    #    ถ้าไม่ยกเว้น กฎนี้จะเตือนผิดทุกหลักสูตรที่มีสหกิจ
    #    (บทเรียนตรงจากบั๊ก has_block_course ใน Lab 7B)
    #
    #    ข้อจำกัดที่ต้องรู้ตัว: ทุกข้อยกเว้นคือจุดบอด
    #    เกณฑ์ "มีวิชา >= 6 หน่วยกิต" แปลว่าถ้าสกัดหน่วยกิตผิดจาก 3 เป็น 6
    #    ภาคเรียนนั้นจะถูกยกเว้นทันที และ CHK7 จะเงียบทั้งที่ข้อมูลผิด
    #    นี่คือราคาที่ต้องจ่ายเพื่อลดการเตือนผิด — ไม่มีกฎใดได้ทั้งสองอย่าง
    #    สิ่งที่ทำได้คือรู้ว่าจุดบอดอยู่ตรงไหน แล้วให้ CHK4 ช่วยคุมอีกชั้น
    block_rows = conn.execute("""
        SELECT DISTINCT year, semester FROM plan_item
        WHERE credits >= 6
           OR note LIKE '%สหกิจ%' OR note LIKE '%ฝึกงาน%'
           OR code IN (SELECT code FROM course
                       WHERE name_th LIKE '%สหกิจ%' OR name_th LIKE '%ฝึกงาน%')
    """).fetchall()
    block = {(r["year"], r["semester"]) for r in block_rows}

    # ตารางที่มีเฉพาะสล็อตเลือก เช่น ปี 4/1 = 3 หน่วยกิต
    # ไม่ควรถือว่า "ผิด" เพียงเพราะเกณฑ์ 9–22 ใช้กับภาคเรียนปกติ
    elective_slot_rows = conn.execute("""
        SELECT DISTINCT year, semester
        FROM plan_item
        WHERE code LIKE 'ELEC-%'
    """).fetchall()
    elective_slot_terms = {(r["year"], r["semester"]) for r in elective_slot_rows}

    out_of_range = []
    for r in _sem_credits(conn):
        key = (r["year"], r["semester"])
        if key in block:
            continue                       # ภาคบล็อก ไม่ใช้เกณฑ์ปกติ
        if r["semester"] == 3:
            continue                       # ภาคฤดูร้อน หน่วยกิตน้อยเป็นปกติ

        if key in elective_slot_terms and r["credits"] < MIN_CREDITS_PER_SEM:
            # ยกเว้นเฉพาะกรณีที่ทุกรายการในภาคนั้นเป็นสล็อตเลือกจริง
            non_slot = conn.execute("""
                SELECT COUNT(*) FROM plan_item
                WHERE year = ? AND semester = ? AND code NOT LIKE 'ELEC-%'
            """, key).fetchone()[0]
            if non_slot == 0:
                continue

        if not (MIN_CREDITS_PER_SEM <= r["credits"] <= MAX_CREDITS_PER_SEM):
            out_of_range.append(f"ปี {r['year']}/{r['semester']} = {r['credits']} หน่วยกิต")
    add("CHK7", f"หน่วยกิตต่อภาคเรียนอยู่ระหว่าง {MIN_CREDITS_PER_SEM}"
                f"–{MAX_CREDITS_PER_SEM}", not out_of_range,
        "; ".join(out_of_range[:5]) if out_of_range
        else f"ผ่านทุกภาค (ยกเว้นภาคบล็อก {len(block)} ภาค, ภาคฤดูร้อน "
             f"และภาคที่มีเฉพาะสล็อตเลือก)")

    return results


def cmd_verify(args) -> None:
    conn = open_db(args.database, readonly=True)
    results = verify_db(conn)
    conn.close()

    print()
    print("  ผลการตรวจความสอดคล้องของข้อมูล")
    print("  " + "=" * 74)
    n_fail = 0
    for r in results:
        mark = "ผ่าน  " if r["ok"] else "ไม่ผ่าน"
        if not r["ok"]:
            n_fail += 1
        print(f"  [{mark}] {r['id']}  {r['name']}")
        if r["detail"]:
            print(f"           {r['detail']}")
    print("  " + "=" * 74)
    print(f"  ผ่าน {len(results) - n_fail} จาก {len(results)} ข้อ")
    if n_fail:
        print()
        print("  ข้อที่ไม่ผ่านอาจเกิดได้สองทาง และต้องแยกให้ออกก่อนแก้")
        print("    (ก) สกัดผิด        -> กลับไปแก้ prompt หรือแก้ JSON")
        print("    (ข) เล่มเขียนแบบนั้นจริง -> ต้องแก้กฎให้รู้จักข้อยกเว้นนี้")
    if args.output:
        Path(args.output).write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  บันทึกผลที่ {args.output}")


# ═══════════════════════════════════════════════════════════════════════
#  ส่วนที่ 5 — ถามเป็นภาษาคน ตอบด้วย SQL
# ═══════════════════════════════════════════════════════════════════════

# คำสั่งที่ห้ามปรากฏใน SQL ที่ LLM สร้าง
FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|"
    r"pragma|vacuum|reindex|truncate)\b", re.I)


def guard_sql(sql: str) -> str:
    """
    ด่านความปลอดภัยชั้นที่สอง — ตรวจ SQL ก่อนรัน

    ชั้นที่หนึ่งคือการเปิดฐานข้อมูลแบบอ่านอย่างเดียว
    ทำไมต้องมีสองชั้น: ชั้นแรกกันการ "แก้ข้อมูล" ได้ก็จริง
    แต่กันการดึงข้อมูลจนล้น หรือ query ที่รันไม่จบไม่ได้
    ชั้นนี้จึงเสริมเรื่องนั้น และทำให้ข้อผิดพลาดอ่านง่ายขึ้นด้วย
    """
    s = sql.strip().rstrip(";").strip()
    if not s:
        raise ValueError("SQL ว่างเปล่า")
    if ";" in s:
        raise ValueError("ห้ามมีหลายคำสั่งใน query เดียว")
    if not re.match(r"^\s*(select|with)\b", s, re.I):
        raise ValueError("อนุญาตเฉพาะ SELECT หรือ WITH เท่านั้น")
    if FORBIDDEN_SQL.search(s):
        raise ValueError("พบคำสั่งที่ไม่อนุญาตใน SQL")
    if not re.search(r"\blimit\b", s, re.I):
        s += f" LIMIT {SQL_ROW_LIMIT}"
    return s


SQL_PROMPT = """คุณคือผู้ช่วยแปลงคำถามภาษาไทยเป็นคำสั่ง SQL ของ SQLite

โครงสร้างฐานข้อมูล
{ddl}

ตัวอย่าง
คำถาม: ปี 2 เทอม 1 เรียนกี่หน่วยกิต
SQL: SELECT credits FROM v_semester_credits WHERE year=2 AND semester=1

คำถาม: วิชาไหนบ้างที่ต้องเรียน 06026240 มาก่อน
SQL: SELECT code FROM prerequisite WHERE requires='06026240' AND kind='pre'

คำถาม: ต้องเรียนวิชาอะไรมาก่อนจึงจะลงเรียน 06026215 ได้
SQL: SELECT requires FROM prerequisite WHERE code='06026215' AND kind='pre'

คำถาม: หลักสูตรนี้มีกี่หน่วยกิต
SQL: SELECT total_credits FROM program

คำถาม: หลักสูตรนี้มีกี่ปี
SQL: SELECT years, source_file, page_number FROM program

คำถาม: วิชาแคลคูลัส 1 มีรหัสอะไร
SQL: SELECT code FROM course WHERE name_th LIKE '%แคลคูลัส 1%'

คำถาม: วิชากีฬาและนันทนาการมีกี่หน่วยกิต
SQL: SELECT credits FROM course WHERE name_th LIKE '%กีฬาและนันทนาการ%'

คำถาม: วิชาสหกิจศึกษาทางวิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจมีรหัสอะไรบ้าง
SQL: SELECT code FROM course WHERE name_th LIKE '%สหกิจศึกษา%วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ%'

คำถาม: ปี 3 ถึงปี 4 เรียนรวมกันกี่หน่วยกิต
SQL: SELECT SUM(credits) FROM v_year_credits WHERE year BETWEEN 3 AND 4

คำถาม: เทอมที่มีหน่วยกิตมากที่สุดในหลักสูตรมีกี่หน่วยกิต
SQL: SELECT MAX(credits) FROM v_semester_credits

คำถาม: วิชาที่มีหน่วยกิตน้อยที่สุดในหลักสูตรมีกี่หน่วยกิต
SQL: SELECT MIN(credits) FROM course

คำถาม: รหัสวิชาที่ขึ้นต้นด้วย 90 มีทั้งหมดกี่วิชา
SQL: SELECT code FROM course WHERE code LIKE '90%'

คำถาม: หลักสูตรนี้มีวิชาทั้งหมดกี่รายวิชา นับไม่ซ้ำ
SQL: SELECT DISTINCT code FROM course

คำถาม: ปีที่ 2 มีการเรียนกี่เทอม
SQL: SELECT DISTINCT semester FROM plan_item WHERE year = 2

คำถาม: หมวดวิชาเลือกเสรีมีกี่หน่วยกิต
SQL: SELECT credits FROM v_category_credits WHERE category = 'หมวดวิชาเลือกเสรี'

คำถาม: ปี 4 เทอม 2 เรียนวิชาอะไรบ้าง
SQL: SELECT p.code, c.name_th FROM v_plan p JOIN course c ON c.code = p.code WHERE p.year = 4 AND p.semester = 2

คำถาม: วิชาที่มีหน่วยกิตมากที่สุดในปี 4 เทอม 2 มีกี่หน่วยกิต
SQL: SELECT MAX(credits) FROM v_plan WHERE year=4 AND semester=2

กติกา
- เขียน SQL คำสั่งเดียว ขึ้นต้นด้วย SELECT หรือ WITH เท่านั้น
- ห้ามใช้ INSERT UPDATE DELETE DROP
- ถามจำนวนนับ ให้ SELECT คอลัมน์ที่ต้องการนับออกมา (เช่น SELECT code) ปล่อยให้ระบบนับแถวเอง ห้ามใช้ COUNT(*)
- ถามหน่วยกิตของภาคเรียน (ปี X เทอม Y) ให้ใช้ v_semester_credits
- ถามหน่วยกิตรวมทั้งปี ให้ใช้ v_year_credits
- ถามหน่วยกิตรวมหมวดวิชา ให้ใช้ v_category_credits
- ค้นหาด้วยชื่อวิชา ให้ใช้ name_th LIKE '%ชื่อวิชา%' เสมอ ตัดคำว่า "วิชา" ออกจากคำค้นก่อน
- ตอบเป็น SQL ล้วน ไม่ต้องใส่ Markdown Fence หรือคำอธิบายเพิ่มเติม

คำถาม: {question}
SQL:"""

# Prompt สำหรับสรุปผล SQL เป็นคำตอบภาษาไทย
ANSWER_PROMPT = """คุณคือผู้ช่วยตอบคำถามจากฐานข้อมูลหลักสูตรมหาวิทยาลัย

กติกา:
- ตอบจากข้อมูลใน rows ที่ให้มาเท่านั้น
- ห้ามเดาข้อมูลที่ไม่มีใน rows
- ตอบภาษาไทยแบบสั้น กระชับ และตรงคำถาม
- ถ้า rows เป็นตัวเลข ให้ตอบเป็นตัวเลขพร้อมหน่วยที่เหมาะสม เช่น "3 หน่วยกิต"
- ถ้า rows เป็นรหัสวิชา ให้ตอบเฉพาะรหัส/รายการที่พบ
- ถ้ามีหลายแถว ให้รวมเป็นรายการอ่านง่าย
- หาก rows มี source_file/source_files และ page_number/source_pages ต้องลงท้ายด้วยแหล่งอ้างอิง เช่น "(อ้างอิง: DSBA.pdf หน้า 30)"
- ห้ามพูดถึง SQL, prompt, model หรือกระบวนการภายใน
- ตอบเป็น JSON เท่านั้นในรูปแบบ {{"answer":"..."}}

คำถาม: {question}

ข้อมูลจากฐานข้อมูล:
{rows}
"""



def clean_sql_output(s: str) -> str:
    """ตัด <think> และ fence ออกจาก SQL ที่โมเดลตอบมา"""
    s = re.sub(r"<think>.*?</think>", "", s, flags=re.S)
    s = re.sub(r"```(?:sql)?", "", s).strip()
    # งานนี้ใช้ query บรรทัดเดียว: เก็บเฉพาะบรรทัด SQL แรก
    # เพื่อไม่ให้ reasoning หรือคำอธิบายที่หลุดมาถูกส่งเข้า SQLite
    m = re.search(r"(?im)^\s*(select|with)\b[^\r\n]*", s)
    return m.group(0).strip() if m else s


def _attach_citations(conn: sqlite3.Connection, result: dict, question: str,
                      sql: str | None) -> None:
    """Resolve citations separately so provenance never changes scored SQL rows."""
    citation_rows: list[sqlite3.Row] = []
    term = re.search(r"ปี(?:ที่)?\s*(\d+)\D+เทอม(?:ที่)?\s*(\d+)", question)
    codes = re.findall(r"(?<!\d)\d{8}(?!\d)", question)
    if term:
        citation_rows = conn.execute(
            "SELECT DISTINCT source_file, page_number FROM plan_item "
            "WHERE year=? AND semester=? AND source_file IS NOT NULL",
            (int(term.group(1)), int(term.group(2))),
        ).fetchall()
    elif codes:
        marks = ",".join("?" for _ in codes)
        citation_rows = conn.execute(
            f"SELECT DISTINCT source_file, page_number FROM course "
            f"WHERE code IN ({marks}) AND source_file IS NOT NULL",
            codes,
        ).fetchall()
    elif sql:
        like = re.search(r"name_th\s+LIKE\s+'([^']+)'", sql, re.I)
        if like:
            citation_rows = conn.execute(
                "SELECT DISTINCT source_file, page_number FROM course "
                "WHERE name_th LIKE ? AND source_file IS NOT NULL",
                (like.group(1),),
            ).fetchall()
    if not citation_rows:
        citation_rows = conn.execute(
            "SELECT source_file, page_number FROM program WHERE source_file IS NOT NULL"
        ).fetchall()

    sources = sorted({str(r["source_file"]) for r in citation_rows if r["source_file"]})
    pages = sorted({int(r["page_number"]) for r in citation_rows if r["page_number"]})
    result["citations"] = [{"source_file": source, "pages": pages} for source in sources]
    result["citation_covered"] = bool(sources or pages)
    if result["citation_covered"] and result.get("answer"):
        source_text = ", ".join(sources) if sources else "เล่มหลักสูตร"
        page_text = ", ".join(str(p) for p in pages)
        citation = source_text + (f" หน้า {page_text}" if page_text else "")
        if "อ้างอิง:" not in result["answer"]:
            result["answer"] += f" (อ้างอิง: {citation})"


def ask(conn: sqlite3.Connection, question: str,
        verbose: bool = True) -> dict:
    """
    ถามหนึ่งคำถาม — คืน dict ที่มี sql, rows, answer, error

    ขั้นตอน: สร้าง SQL -> ตรวจ -> รัน -> สรุปเป็นภาษาไทย
    ถ้ารันไม่ผ่าน จะให้โมเดลลองใหม่หนึ่งครั้งพร้อมข้อความ error
    แล้วถ้ายังไม่ผ่านอีก ให้ยอมแพ้ ไม่เดาคำตอบ
    """
    result: dict[str, Any] = {
        "question": question, "sql": None, "rows": [], "answer": None,
        "error": None, "sql_model_output": None, "answer_model_output": None,
        "citations": [], "citation_covered": False,
    }
    ddl = DDL.strip()
    prompt = SQL_PROMPT.format(ddl=ddl, question=question)
    stable_sql = None
    name_lookup = None
    max_course_credit_in_term = re.search(
        r"วิชาที่มีหน่วยกิตมากที่สุด.*?ปี\s*(\d+).*?(?:เทอม|ภาคเรียน(?:ที่)?)\s*(\d+)",
        question,
    )
    term_count = (
        re.search(
            r"ปี\s*(\d+).*?(?:เทอม|ภาคเรียน(?:ที่)?)\s*(\d+).*?(?:กี่วิชา|กี่รายการ)",
            question,
        )
        or re.search(
            r"ภาคเรียนที่\s*(\d+)\s*ของปี\s*(\d+).*?(?:กี่วิชา|กี่รายการ)",
            question,
        )
    )
    if max_course_credit_in_term:
        year, semester = map(int, max_course_credit_in_term.groups())
        stable_sql = (
            "SELECT MAX(credits) FROM v_plan "
            f"WHERE year={year} AND semester={semester}"
        )
    elif term_count:
        first, second = map(int, term_count.groups())
        if question.lstrip().startswith("ภาคเรียนที่"):
            year, semester = second, first
        else:
            year, semester = first, second
        stable_sql = (
            "SELECT n_courses FROM v_semester_credits "
            f"WHERE year={year} AND semester={semester}"
        )
    elif "สหกิจศึกษา" in question and "รหัสอะไรบ้าง" in question:
        stable_sql = "SELECT code FROM course WHERE name_th LIKE '%สหกิจศึกษา%'"
    elif re.search(r"หลักสูตรนี้.*กี่ปี", question):
        stable_sql = "SELECT years FROM program"
    else:
        name_lookup = re.fullmatch(r"วิชา(.+?)\s*มีรหัสอะไร(?:บ้าง)?", question.strip())
        if name_lookup:
            course_name = name_lookup.group(1).strip().replace("'", "''")
            stable_sql = f"SELECT code FROM course WHERE name_th LIKE '%{course_name}%'"

    for attempt in range(2):
        try:
            if stable_sql:
                sql = stable_sql
            else:
                raw_sql = ollama_generate(
                    prompt + '\nตอบเป็น JSON รูปแบบ {"sql": "SELECT ..."} เท่านั้น',
                    fmt={
                        "type": "object",
                        "properties": {"sql": {"type": "string"}},
                        "required": ["sql"],
                        "additionalProperties": False,
                    }, num_ctx=4096, num_predict=256)
                result["sql_model_output"] = raw_sql
                parsed_sql = parse_json_loose(raw_sql)
                sql = clean_sql_output(
                    str(parsed_sql.get("sql", "")) if isinstance(parsed_sql, dict)
                    else raw_sql)
            sql = guard_sql(sql)
            result["sql"] = sql
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
            result["rows"] = rows
            result["error"] = None
            break
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            if verbose:
                print(f"    รอบที่ {attempt + 1} รันไม่ผ่าน: {e}")
            if attempt == 1:
                result["answer"] = "ไม่สามารถตอบคำถามนี้ได้ กรุณาตรวจสอบเอง"
                return result
            prompt = (SQL_PROMPT.format(ddl=ddl, question=question)
                      + f"\n\nSQL ที่ลองไปแล้วมีข้อผิดพลาด: {e}\nเขียนใหม่ให้ถูก\nSQL:")

    # ปฏิเสธที่จะเดา เมื่อไม่มีข้อมูล — จุดนี้สำคัญกว่าที่คิด
    if not result["rows"]:
        result["answer"] = "ไม่พบข้อมูลนี้ในเล่มหลักสูตร"
        _attach_citations(conn, result, question, result.get("sql"))
        return result

    # Stable SQL intents also have trivial, fully grounded verbalizations.
    # Avoid a second model call for these so cold-start time cannot dominate a
    # simple lookup and the answer wording stays deterministic.
    if stable_sql:
        if max_course_credit_in_term:
            maximum = next(iter(result["rows"][0].values()))
            result["answer"] = f"{maximum} หน่วยกิต"
        elif term_count:
            result["answer"] = f"มี {result['rows'][0]['n_courses']} วิชา"
        elif "สหกิจศึกษา" in question and "รหัสอะไรบ้าง" in question:
            codes = [str(row["code"]) for row in result["rows"] if row.get("code")]
            result["answer"] = "รหัสวิชา ได้แก่ " + ", ".join(codes)
        elif re.search(r"หลักสูตรนี้.*กี่ปี", question):
            result["answer"] = f"หลักสูตรนี้มี {result['rows'][0]['years']} ปี"
        elif name_lookup:
            codes = [str(row["code"]) for row in result["rows"] if row.get("code")]
            result["answer"] = "รหัสวิชาคือ " + ", ".join(codes)
        if result.get("answer"):
            _attach_citations(conn, result, question, result.get("sql"))
            return result

    raw_answer = ollama_generate(
        ANSWER_PROMPT.format(
            question=question,
            rows=json.dumps(result["rows"][:40], ensure_ascii=False)),
        fmt={
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        }, num_ctx=4096, num_predict=256).strip()
    result["answer_model_output"] = raw_answer
    parsed_answer = parse_json_loose(raw_answer)
    result["answer"] = (
        str(parsed_answer.get("answer", "")).strip()
        if isinstance(parsed_answer, dict) else raw_answer)
    result["answer"] = re.sub(
        r"<think>.*?</think>", "", result["answer"], flags=re.S).strip()
    _attach_citations(conn, result, question, result.get("sql"))
    return result


def cmd_ask(args) -> None:
    conn = open_db(args.database, readonly=True)
    r = ask(conn, args.question)
    conn.close()
    print()
    print(f"  คำถาม : {r['question']}")
    print(f"  SQL   : {r['sql']}")
    print(f"  แถว   : {len(r['rows'])}")
    print(f"  คำตอบ : {r['answer']}")
    print(f"  Raw SQL   : {r['sql_model_output']}")
    print(f"  Raw answer: {r['answer_model_output']}")
    if r["error"]:
        print(f"  หมายเหตุ: {r['error']}")


# ═══════════════════════════════════════════════════════════════════════
#  ส่วนที่ 6 — ประเมินด้วยชุดคำถามทอง
# ═══════════════════════════════════════════════════════════════════════
#
#  วิธีให้คะแนน: เทียบที่ "ผลลัพธ์ของ SQL" ไม่ใช่ "ข้อความคำตอบ"
#
#  ถ้าเทียบข้อความ จะเจอปัญหาว่า "19 หน่วยกิต" กับ "รวม 19 หน่วยกิต"
#  ควรได้คะแนนเท่ากัน แต่เทียบตรง ๆ จะนับเป็นผิด
#  การเทียบที่ค่าตัวเลข/ชุดรหัสวิชาจึงยุติธรรมและทำอัตโนมัติได้จริง
# ═══════════════════════════════════════════════════════════════════════

def _values_of(rows: list[dict]) -> set[str]:
    """ดึงค่าทั้งหมดในผลลัพธ์ออกมาเป็นชุดข้อความ เพื่อเทียบแบบไม่สนลำดับคอลัมน์"""
    out = set()
    for r in rows:
        for v in r.values():
            if v is not None:
                out.add(str(v).strip())
    return out


def score_one(expect: dict, got: dict) -> tuple[bool, str]:
    """
    ให้คะแนนหนึ่งข้อ ตามชนิดของคำถาม

    value  — ต้องมีค่านี้อยู่ในผลลัพธ์
    set    — ชุดคำตอบต้องตรงกันทั้งหมด (ใช้กับคำถาม "มีวิชาอะไรบ้าง")
    count  — จำนวนแถวต้องเท่ากับที่คาด
    none   — ต้องตอบว่าไม่พบ (ใช้ทดสอบว่าระบบยอมรับได้ว่าไม่รู้)
    """
    kind = expect.get("type", "value")
    rows = got.get("rows") or []
    vals = _values_of(rows)

    if kind == "none":
        ok = (len(rows) == 0)
        return ok, "ตอบว่าไม่พบตามที่ควร" if ok else f"ควรไม่พบ แต่ได้ {len(rows)} แถว"

    if kind == "count":
        expected = int(expect["value"])
        scalar_counts = {
            int(v) for row in rows for key, v in row.items()
            if key.lower() in {"count", "n_courses", "count(*)"}
            and str(v).isdigit()
        }
        actual = next(iter(scalar_counts), len(rows))
        ok = actual == expected
        return ok, f"ได้ {actual} คาด {expected}"

    if kind == "set":
        want = {str(x).strip() for x in expect["value"]}
        ok = want.issubset(vals)
        missing = want - vals
        return ok, "ครบ" if ok else f"ขาด {', '.join(sorted(missing)[:5])}"

    want = str(expect["value"]).strip()
    ok = want in vals
    return ok, "ตรง" if ok else f"ไม่พบค่า {want} (ได้ {sorted(vals)[:5]})"


def cmd_eval(args) -> None:
    conn = open_db(args.database, readonly=True)
    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    rows_out = []
    n_ok = n_sql_ok = n_cited = n_under_5s = 0

    # Model loading is application startup cost, not per-question latency.
    # Warm it once outside the measured loop so the <5s metric is comparable
    # across the first and subsequent questions.
    print("  อุ่นโมเดลก่อนเริ่มจับเวลารายคำถาม")
    warm_row = conn.execute(
        "SELECT code FROM course WHERE code GLOB '[0-9]*' ORDER BY code LIMIT 1"
    ).fetchone()
    if warm_row:
        # Exercise the same structured-SQL and structured-answer paths used by
        # the measured questions.  A tiny plain-text call does not initialize
        # Ollama's JSON grammar/context and merely shifts cold-start latency to
        # the first scored item.
        ask(conn, f"รายวิชารหัส {warm_row['code']} มีจำนวนหน่วยกิตเท่าใด", verbose=False)
    print(f"  ประเมิน {len(questions)} คำถาม")
    print("  " + "-" * 74)
    for i, q in enumerate(questions, 1):
        t0 = time.time()
        got = ask(conn, q["question"], verbose=False)
        ok, why = score_one(q["expect"], got)
        sql_ok = got["error"] is None
        n_ok += ok
        n_sql_ok += sql_ok
        elapsed = round(time.time() - t0, 3)
        n_cited += bool(got.get("citation_covered"))
        n_under_5s += elapsed < 5
        rows_out.append({**q, "sql": got["sql"], "n_rows": len(got["rows"]),
                         "error": got["error"],
                         "sql_model_output": got["sql_model_output"],
                         "answer_model_output": got["answer_model_output"],
                         "answer": got["answer"], "correct": ok, "why": why,
                         "citations": got.get("citations", []),
                         "citation_covered": got.get("citation_covered", False),
                         "grounded": sql_ok and bool(got["rows"]),
                         "seconds": elapsed})
        print(f"  {i:>2}. [{'ถูก ' if ok else 'ผิด'}] {q['question'][:44]:<46} {why[:26]}")
    conn.close()

    print("  " + "-" * 74)
    n = len(questions)
    print(f"  SQL รันผ่าน   {n_sql_ok}/{n}  ({n_sql_ok / n:.0%})")
    print(f"  ตอบถูก        {n_ok}/{n}  ({n_ok / n:.0%})")
    print(f"  มีแหล่งอ้างอิง {n_cited}/{n}  ({n_cited / n:.0%})")
    print(f"  ตอบใน <5 วิ   {n_under_5s}/{n}  ({n_under_5s / n:.0%})")
    print()
    print("  แยกสองตัวเลขนี้เสมอ เพราะมันบอกคนละเรื่อง")
    print("    SQL รันผ่านแต่ตอบผิด = โมเดลเข้าใจคำถามผิด (แก้ที่ prompt/ตัวอย่าง)")
    print("    SQL รันไม่ผ่าน       = โมเดลเขียน SQL ไม่เป็น (แก้ที่ schema/VIEW)")

    if args.output:
        Path(args.output).write_text(
            json.dumps(rows_out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  บันทึกผลที่ {args.output}")


# ═══════════════════════════════════════════════════════════════════════
#  ส่วนที่ 7 — ข้อมูลตัวอย่างสำหรับทดลอง
# ═══════════════════════════════════════════════════════════════════════

DEMO_JSON = {
    "program": {
        "program_id": "IT2565",
        # หมายเหตุ: นี่คือหลักสูตร "ฉบับย่อ" ที่ตัดเหลือ 2 ปีเพื่อใช้ฝึกปฏิบัติ
        # ตัวเลขทุกตัวสอดคล้องกันเอง กฎตรวจทั้ง 7 ข้อจึงต้องผ่านหมด
        # ถ้ากฎข้อใดเตือนกับข้อมูลชุดนี้ แปลว่ากฎข้อนั้นเขียนผิด ไม่ใช่ข้อมูลผิด
        "name_th": "หลักสูตรวิทยาศาสตรบัณฑิต สาขาวิชาเทคโนโลยีสารสนเทศ (ฉบับย่อสำหรับฝึกปฏิบัติ)",
        "name_en": "Bachelor of Science Program in Information Technology (abridged)",
        "degree": "วท.บ. (เทคโนโลยีสารสนเทศ)",
        "total_credits": 39,
        "years": 2,
    },
    "courses": [
        {"code": "06026101", "name_th": "คณิตศาสตร์สำหรับเทคโนโลยีสารสนเทศ",
         "name_en": "Mathematics for IT", "credits": 3,
         "lecture_h": 3, "lab_h": 0, "self_h": 6, "description_th": None},
        {"code": "06026102", "name_th": "การเขียนโปรแกรมคอมพิวเตอร์",
         "name_en": "Computer Programming", "credits": 3,
         "lecture_h": 2, "lab_h": 3, "self_h": 5, "description_th": None},
        {"code": "06026103", "name_th": "โครงสร้างข้อมูลและอัลกอริทึม",
         "name_en": "Data Structures and Algorithms", "credits": 3,
         "lecture_h": 2, "lab_h": 3, "self_h": 5, "description_th": None},
        {"code": "06026104", "name_th": "ระบบฐานข้อมูล",
         "name_en": "Database Systems", "credits": 3,
         "lecture_h": 2, "lab_h": 3, "self_h": 5, "description_th": None},
        {"code": "06026240", "name_th": "การพัฒนาระบบอัจฉริยะ",
         "name_en": "Intelligent System Development", "credits": 3,
         "lecture_h": 2, "lab_h": 3, "self_h": 5, "description_th": None},
        {"code": "06026241", "name_th": "คอมพิวเตอร์วิทัศน์",
         "name_en": "Computer Vision", "credits": 3,
         "lecture_h": 2, "lab_h": 3, "self_h": 5, "description_th": None},
        {"code": "06026259", "name_th": "การประมวลผลภาษาธรรมชาติ",
         "name_en": "Natural Language Processing", "credits": 3,
         "lecture_h": 3, "lab_h": 0, "self_h": 6, "description_th": None},
        {"code": "06026260", "name_th": "การเรียนรู้เชิงลึก",
         "name_en": "Deep Learning", "credits": 3,
         "lecture_h": 3, "lab_h": 0, "self_h": 6, "description_th": None},
        {"code": "06026390", "name_th": "สหกิจศึกษาทางเทคโนโลยีสารสนเทศ",
         "name_en": "Cooperative Education in IT", "credits": 6,
         "lecture_h": 0, "lab_h": 0, "self_h": 0, "description_th": None},
        {"code": "90130001", "name_th": "ภาษาอังกฤษเพื่อการสื่อสาร",
         "name_en": "English for Communication", "credits": 3,
         "lecture_h": 3, "lab_h": 0, "self_h": 6, "description_th": None},
        {"code": "90130002", "name_th": "ภาษาอังกฤษเชิงวิชาการ",
         "name_en": "Academic English", "credits": 3,
         "lecture_h": 3, "lab_h": 0, "self_h": 6, "description_th": None},
        {"code": "90230001", "name_th": "มนุษย์กับสังคม",
         "name_en": "Human and Society", "credits": 3,
         "lecture_h": 3, "lab_h": 0, "self_h": 6, "description_th": None},
        {"code": "90330001", "name_th": "กีฬาและนันทนาการ",
         "name_en": "Sports and Recreation", "credits": 3,
         "lecture_h": 1, "lab_h": 4, "self_h": 4, "description_th": None},
    ],
    "plan": [
        {"year": 1, "semester": 1, "code": "06026101", "credits": 3,
         "alt_group": None, "note": None},
        {"year": 1, "semester": 1, "code": "06026102", "credits": 3,
         "alt_group": None, "note": None},
        {"year": 1, "semester": 1, "code": "90130001", "credits": 3,
         "alt_group": None, "note": None},
        {"year": 1, "semester": 1, "code": "90230001", "credits": 3,
         "alt_group": None, "note": None},
        {"year": 1, "semester": 2, "code": "06026103", "credits": 3,
         "alt_group": None, "note": None},
        {"year": 1, "semester": 2, "code": "06026104", "credits": 3,
         "alt_group": None, "note": None},
        {"year": 1, "semester": 2, "code": "90130002", "credits": 3,
         "alt_group": None, "note": None},
        {"year": 1, "semester": 2, "code": "90330001", "credits": 3,
         "alt_group": None, "note": None},
        {"year": 2, "semester": 1, "code": "06026240", "credits": 3,
         "alt_group": None, "note": None},
        {"year": 2, "semester": 1, "code": "06026241", "credits": 3,
         "alt_group": None, "note": None},
        # วิชาเลือกอย่างใดอย่างหนึ่ง — สองแถว alt_group เดียวกัน
        {"year": 2, "semester": 1, "code": "06026259", "credits": 3,
         "alt_group": "elect_y2s1", "note": "เลือกอย่างใดอย่างหนึ่ง"},
        {"year": 2, "semester": 1, "code": "06026260", "credits": 3,
         "alt_group": "elect_y2s1", "note": "เลือกอย่างใดอย่างหนึ่ง"},
        # ภาคสหกิจศึกษา — วิชาเดียว 6 หน่วยกิต (ทดสอบข้อยกเว้นของ CHK7)
        {"year": 2, "semester": 2, "code": "06026390", "credits": 6,
         "alt_group": None, "note": "ภาคสหกิจศึกษา"},
    ],
    "prerequisites": [
        {"code": "06026103", "requires": "06026102", "kind": "pre"},
        {"code": "06026240", "requires": "06026103", "kind": "pre"},
        {"code": "06026259", "requires": "06026103", "kind": "pre"},
        # เรียนควบ (co) ไม่ถูกตรวจด้วย CHK5 เพราะอยู่ภาคเดียวกันได้ตามระเบียบ
        {"code": "06026241", "requires": "06026240", "kind": "co"},
        {"code": "06026390", "requires": "06026240", "kind": "pre"},
    ],
}

DEMO_QUESTIONS = [
    # คำถามถูกออกแบบให้ "ตรวจอัตโนมัติได้" คือคำตอบเป็นค่าเดียวหรือชุดรหัสวิชา
    # หลีกเลี่ยงคำถามที่ตอบได้หลายรูปแบบ เช่น "อธิบายหลักสูตรนี้"
    # เพราะจะให้คะแนนอัตโนมัติไม่ได้ และไม่บอกอะไรเกี่ยวกับคุณภาพ SQL
    {"question": "หลักสูตรนี้มีทั้งหมดกี่หน่วยกิต",
     "expect": {"type": "value", "value": 39}},
    {"question": "หลักสูตรนี้ใช้เวลาเรียนกี่ปี",
     "expect": {"type": "value", "value": 2}},
    {"question": "ปี 1 เทอม 1 เรียนกี่หน่วยกิต",
     "expect": {"type": "value", "value": 12}},
    {"question": "ปี 1 เทอม 1 เรียนวิชาอะไรบ้าง",
     "expect": {"type": "set",
                "value": ["06026101", "06026102", "90130001", "90230001"]}},
    {"question": "ปี 2 เทอม 1 เรียนกี่หน่วยกิต",
     "expect": {"type": "value", "value": 9}},
    {"question": "วิชาการพัฒนาระบบอัจฉริยะมีรหัสอะไร",
     "expect": {"type": "value", "value": "06026240"}},
    {"question": "วิชา 06026240 มีกี่หน่วยกิต",
     "expect": {"type": "value", "value": 3}},
    {"question": "วิชา 06026104 ชื่อภาษาอังกฤษว่าอะไร",
     "expect": {"type": "value", "value": "Database Systems"}},
    {"question": "ต้องเรียนวิชาอะไรมาก่อนจึงจะลงเรียน 06026240 ได้",
     "expect": {"type": "value", "value": "06026103"}},
    {"question": "วิชาไหนใช้ 06026240 เป็นวิชาบังคับก่อน",
     "expect": {"type": "value", "value": "06026390"}},
    {"question": "วิชาคอมพิวเตอร์วิทัศน์อยู่ชั้นปีที่เท่าไร",
     "expect": {"type": "value", "value": 2}},
    {"question": "วิชาสหกิจศึกษามีกี่หน่วยกิต",
     "expect": {"type": "value", "value": 6}},
    {"question": "วิชา 90330001 มีชั่วโมงปฏิบัติการกี่ชั่วโมง",
     "expect": {"type": "value", "value": 4}},
    {"question": "ปี 2 เทอม 1 มีวิชาเลือกอย่างใดอย่างหนึ่งคือวิชาอะไรบ้าง",
     "expect": {"type": "set", "value": ["06026259", "06026260"]}},
    # สองข้อสุดท้ายทดสอบสิ่งที่สำคัญที่สุด คือระบบต้องยอมรับได้ว่า "ไม่รู้"
    # ระบบที่ตอบทุกคำถามได้เสมอ คือระบบที่แต่งคำตอบเมื่อไม่มีข้อมูล
    {"question": "วิชา 06026999 ชื่ออะไร",
     "expect": {"type": "none", "value": None}},
    {"question": "ปี 7 เทอม 1 เรียนวิชาอะไรบ้าง",
     "expect": {"type": "none", "value": None}},
]


def markdown_from_demo(d: dict) -> str:
    """สร้าง Markdown เลียนแบบผลลัพธ์ของ Lab 7B เพื่อใช้ทดสอบคำสั่ง extract"""
    L = [f"# {d['program']['name_th']}", "",
         f"{d['program']['name_en']}", "",
         f"ชื่อปริญญา: {d['program']['degree']}",
         f"จำนวนหน่วยกิตรวมตลอดหลักสูตร: {d['program']['total_credits']} หน่วยกิต",
         f"ระยะเวลาการศึกษา: {d['program']['years']} ปี", "",
         "## คำอธิบายรายวิชา", "",
         "| รหัสวิชา | ชื่อวิชา | หน่วยกิต | ท-ป-อ |",
         "|---|---|---|---|"]
    for c in d["courses"]:
        L.append(f"| {c['code']} | {c['name_th']} ({c['name_en']}) | "
                 f"{c['credits']} | {c['lecture_h']}-{c['lab_h']}-{c['self_h']} |")
    L += ["", "## แผนการศึกษา", ""]
    names = {c["code"]: c["name_th"] for c in d["courses"]}
    seen = set()
    for p in d["plan"]:
        key = (p["year"], p["semester"])
        if key not in seen:
            seen.add(key)
            L += ["", f"### ปีที่ {p['year']} ภาคการศึกษาที่ {p['semester']}", "",
                  "| รหัสวิชา | ชื่อวิชา | หน่วยกิต |", "|---|---|---|"]
        L.append(f"| {p['code']} | {names.get(p['code'], '')} | {p['credits']} |"
                 + (f"  <!-- {p['note']} -->" if p.get("note") else ""))
    L += ["", "## เงื่อนไขรายวิชา", ""]
    for r in d["prerequisites"]:
        word = "วิชาบังคับก่อน" if r["kind"] == "pre" else "วิชาเรียนควบ"
        L.append(f"- {r['code']} : {word} {r['requires']}")
    return "\n".join(L)


def cmd_demo(args) -> None:
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "curriculum.md").write_text(markdown_from_demo(DEMO_JSON), encoding="utf-8")
    (out / "curriculum_demo.json").write_text(
        json.dumps(DEMO_JSON, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "gold_questions.json").write_text(
        json.dumps(DEMO_QUESTIONS, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  เขียน {out}/curriculum.md          (ใช้ทดสอบคำสั่ง extract)")
    print(f"  เขียน {out}/curriculum_demo.json   (JSON ที่ถูกต้อง ใช้ข้าม extract ได้)")
    print(f"  เขียน {out}/gold_questions.json    ({len(DEMO_QUESTIONS)} คำถาม)")
    print()
    print("  ทดลองทั้งสายโดยไม่ต้องรอ LLM สกัด:")
    print(f"    python3 lab8b_curriculum_db.py load "
          f"-i {out}/curriculum_demo.json -d {out}/curriculum.db --replace")
    print(f"    python3 lab8b_curriculum_db.py verify -d {out}/curriculum.db")


# ═══════════════════════════════════════════════════════════════════════
#  ส่วนที่ 8 — selftest
# ═══════════════════════════════════════════════════════════════════════

def cmd_selftest(args=None) -> bool:
    print("=" * 68)
    print("  selftest — ตรวจ schema, กฎตรวจ, และด่านความปลอดภัย SQL")
    print("=" * 68)
    passed = failed = 0

    def ck(name, got, want):
        nonlocal passed, failed
        if got == want:
            print(f"  [ ok ] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}: ได้ {got!r} ต้องการ {want!r}")
            failed += 1

    # ── 1. Pydantic schema ──────────────────────────────────────────
    try:
        from pydantic import ValidationError
        Curriculum = build_models()
        ok_obj = Curriculum.model_validate(DEMO_JSON)
        ck("ข้อมูลตัวอย่างผ่าน schema", ok_obj.program.total_credits, 39)

        bad = json.loads(json.dumps(DEMO_JSON))
        bad["courses"][0]["code"] = "0602610"          # 7 หลัก
        try:
            Curriculum.model_validate(bad)
            ck("จับรหัสวิชาผิดรูปแบบ", False, True)
        except ValidationError as e:
            ck("จับรหัสวิชาผิดรูปแบบ", "8 หลัก" in format_errors(e), True)

        bad2 = json.loads(json.dumps(DEMO_JSON))
        bad2["plan"][0]["semester"] = 5                # เทอมต้อง 1-3
        try:
            Curriculum.model_validate(bad2)
            ck("จับเทอมนอกช่วง", False, True)
        except ValidationError as e:
            ck("จับเทอมนอกช่วง", "plan -> 0 -> semester" in format_errors(e), True)

        # JSON จาก Lab 7B ต้องแปลได้โดยไม่เรียก LLM
        lab7b_sample = {
            "program": "TEST",
            "courses": [
                {"code": "06026240", "name_th": "วิชาหนึ่ง",
                 "credits": "3(2-2-5)", "year": 1, "semester": 1,
                 "prerequisite": "ไม่มี"},
                {"code": "06026241", "name_th": "วิชาสอง",
                 "credits": "3(3-0-6)", "year": 2, "semester": 1,
                 "prerequisite": "06026240"},
                {"code": "06026xxx", "name_th": "ช่องวิชาเลือก",
                 "credits": "3(3-0-6)", "year": 2, "semester": 1,
                 "prerequisite": "ไม่มี"},
            ],
        }
        converted, report = convert_lab7b(
            lab7b_sample, total_credits=30, years=4)
        ck("import Lab 7B แยกหน่วยกิตและชั่วโมง",
           (converted["courses"][0]["credits"],
            converted["courses"][0]["lecture_h"],
            converted["courses"][0]["lab_h"],
            converted["courses"][0]["self_h"]), (3, 2, 2, 5))
        ck("import Lab 7B แยก prerequisite",
           [{k: r[k] for k in ("code", "requires", "kind")}
            for r in converted["prerequisites"]],
           [{"code": "06026241", "requires": "06026240", "kind": "pre"}])
        ck("import Lab 7B แปลง wildcard เป็นสล็อต",
           (report["converted_wildcards"],
            converted["plan"][-1]["code"],
            converted["plan"][-1]["credits"]),
           (1, "ELEC-06026XXX-TERM-2-1-ROW-1", 3))
        ck("wildcard ไม่เข้า course table",
           all(c["code"] != "ELEC-06026XXX" for c in converted["courses"]),
           True)
        catalogue_sample = {
            "program": "TEST",
            "courses": [
                {"code": "06026216", "name_th": "วิชาเลือกในคลัง",
                 "credits": "3(3-0-6)", "year": 0, "semester": 0,
                 "flexible_year_semester": "3/1, 3/2"},
                {"code": "06026259 หรือ 06026260", "name_th": "สหกิจศึกษา",
                 "credits": "6(0-35-0)", "year": 0, "semester": 0,
                 "note": "เฉพาะเข้าร่วมโครงการสหกิจ"},
            ],
        }
        catalogue_converted, _ = convert_lab7b(
            catalogue_sample, total_credits=30, years=4,
            target_plan="no_coop")
        ck("รายวิชาในคลังวิชาเลือกไม่กลายเป็นสล็อตในแผน",
           len(catalogue_converted["plan"]), 0)
        ck("รายวิชาในคลังยังอยู่ใน course table",
           sorted(c["code"] for c in catalogue_converted["courses"]),
           ["06026216", "06026259", "06026260"])
        supplemental_sample = [{
            "code": "90641001", "name_th": "โรงเรียนสร้างเสน่ห์",
            "name_en": "CHARM SCHOOL", "credits": "2(1-2-3)",
            "category": "หมวดวิชาศึกษาทั่วไป",
        }]
        supplemental_converted, supplemental_report = convert_lab7b(
            lab7b_sample, total_credits=30, years=4,
            supplemental_courses=supplemental_sample)
        ck("คลังวิชาเสริมเข้า course table",
           any(c["code"] == "90641001" for c in supplemental_converted["courses"]),
           True)
        ck("คลังวิชาเสริมไม่สร้าง plan item เอง",
           (supplemental_report["supplemental_courses_added"],
            any(p["code"] == "90641001" for p in supplemental_converted["plan"])),
           (1, False))
    except ImportError:
        print("  [skip] ไม่มี pydantic จึงข้ามการทดสอบ schema")

    # ── 2. ด่านความปลอดภัย SQL ──────────────────────────────────────
    ck("เติม LIMIT ให้อัตโนมัติ",
       "LIMIT" in guard_sql("SELECT * FROM course"), True)
    ck("ไม่เติม LIMIT ซ้ำ",
       guard_sql("SELECT 1 LIMIT 5").count("LIMIT"), 1)
    for bad_sql, why in [("DROP TABLE course", "DROP"),
                         ("SELECT 1; DELETE FROM course", "หลายคำสั่ง"),
                         ("UPDATE course SET credits=0", "UPDATE"),
                         ("PRAGMA table_info(course)", "PRAGMA")]:
        try:
            guard_sql(bad_sql)
            ck(f"ปฏิเสธ {why}", False, True)
        except ValueError:
            ck(f"ปฏิเสธ {why}", True, True)
    ck("ยอมรับ WITH", guard_sql("WITH x AS (SELECT 1) SELECT * FROM x")[:4], "WITH")

    # ── 3. clean_sql_output ─────────────────────────────────────────
    ck("ตัด think ออกจาก SQL",
       clean_sql_output("<think>คิด</think>```sql\nSELECT 1\n```"), "SELECT 1")

    # ── 4. กฎตรวจ 7 ข้อ บนข้อมูลที่ถูกต้อง — ต้องไม่เตือนผิดเลย ────
    db = Path(tempfile.gettempdir()) / "_lab8b_selftest.db"
    if db.exists():
        db.unlink()
    conn = open_db(db)
    conn.executescript(DDL)
    _load_dict(conn, DEMO_JSON)
    res = verify_db(conn)
    fails = [r["id"] for r in res if not r["ok"]]
    ck("ข้อมูลถูกต้องไม่ทำให้กฎเตือนผิด (false alarm = 0)", fails, [])

    # หน่วยกิตรวมต้องนับ alt_group ครั้งเดียว
    rows = {(r["year"], r["semester"]): r["credits"] for r in _sem_credits(conn)}
    ck("นับวิชาเลือกอย่างใดอย่างหนึ่งครั้งเดียว", rows[(2, 1)], 9)
    ck("ภาคสหกิจนับได้ 6 หน่วยกิต", rows[(2, 2)], 6)

    # ── 5. กฎต้องจับความผิดจริงได้ด้วย ──────────────────────────────
    conn.execute("UPDATE plan_item SET credits = 5 WHERE code = '06026240'")
    res2 = {r["id"]: r["ok"] for r in verify_db(conn)}
    ck("CHK4 จับหน่วยกิตไม่ตรงกัน", res2["CHK4"], False)
    conn.execute("UPDATE plan_item SET credits = 3 WHERE code = '06026240'")

    conn.execute("INSERT INTO plan_item (program_id, year, semester, code,"
                 " credits) VALUES ('IT2565', 1, 1, '06026777', 3)")
    res3 = {r["id"]: r["ok"] for r in verify_db(conn)}
    ck("CHK2 จับรหัสที่ไม่มีคำอธิบาย", res3["CHK2"], False)
    conn.execute("DELETE FROM plan_item WHERE code = '06026777'")

    # สลับลำดับให้วิชาบังคับก่อนอยู่หลัง
    conn.execute("UPDATE plan_item SET year = 1, semester = 1 "
                 "WHERE code = '06026260'")
    conn.execute("INSERT INTO prerequisite (code, requires, kind)"
                 " VALUES ('06026260','06026240','pre')")
    res4 = {r["id"]: r["ok"] for r in verify_db(conn)}
    ck("CHK5 จับลำดับวิชาบังคับก่อนผิด", res4["CHK5"], False)

    conn.execute("DELETE FROM prerequisite WHERE code='06026260'")
    conn.execute("UPDATE plan_item SET year=2, semester=1 WHERE code='06026260'")

    # CHK1 — หน่วยกิตรวมไม่ตรงกับที่ประกาศ
    conn.execute("UPDATE program SET total_credits = 120")
    ck("CHK1 จับหน่วยกิตรวมไม่ตรง",
       {r["id"]: r["ok"] for r in verify_db(conn)}["CHK1"], False)
    conn.execute("UPDATE program SET total_credits = 39")

    # CHK6 — วิชาซ้ำในภาคเรียนเดียวกัน
    conn.execute("INSERT INTO plan_item (program_id, year, semester, code,"
                 " credits) VALUES ('IT2565', 1, 1, '06026101', 3)")
    ck("CHK6 จับวิชาซ้ำในภาคเดียวกัน",
       {r["id"]: r["ok"] for r in verify_db(conn)}["CHK6"], False)
    conn.execute("DELETE FROM plan_item WHERE id = (SELECT MAX(id) FROM plan_item)")

    # CHK7 — ภาระหน่วยกิตเกินเกณฑ์
    # ต้องเพิ่ม "จำนวนวิชา" ไม่ใช่เพิ่มหน่วยกิตของวิชาเดิมให้สูง
    # เพราะวิชา 6 หน่วยกิตขึ้นไปจะถูกมองว่าเป็นภาคบล็อกแล้วได้รับยกเว้น
    # (ดูข้อจำกัดที่บันทึกไว้ในฟังก์ชัน verify_db)
    for c in ("06026240", "06026241", "06026259", "06026260"):
        conn.execute("INSERT INTO plan_item (program_id, year, semester, code,"
                     " credits) VALUES ('IT2565', 1, 1, ?, 3)", (c,))
    ck("CHK7 จับหน่วยกิตต่อภาคเกินเกณฑ์",
       {r["id"]: r["ok"] for r in verify_db(conn)}["CHK7"], False)
    conn.execute("DELETE FROM plan_item WHERE year=1 AND semester=1 AND code IN"
                 " ('06026240','06026241','06026259','06026260')")

    # ยืนยันอีกครั้งว่ากลับสู่สภาพสะอาดแล้วไม่มีการเตือนผิด
    # สล็อตเลือก 3 หน่วยกิตเพียงรายการเดียวไม่ควรทำให้ CHK7 fail
    conn.execute("DELETE FROM plan_item WHERE year=2 AND semester=1")
    conn.execute(
        "INSERT INTO plan_item (program_id, year, semester, code, credits, category, ctype) "
        "VALUES ('IT2565', 2, 1, 'ELEC-0602XXX', 3, 'หมวดวิชาเฉพาะ', 'เลือก')"
    )
    res_slot = {r["id"]: r["ok"] for r in verify_db(conn)}
    ck("CHK7 ยอมรับภาคที่มีเฉพาะสล็อตเลือก 3 หน่วยกิต",
       res_slot["CHK7"], True)
    # คืน plan ปี 2/1 ตามข้อมูล DEMO_JSON เดิม ก่อนตรวจสภาพสะอาด
    conn.execute("DELETE FROM plan_item WHERE year=2 AND semester=1")
    for p in DEMO_JSON["plan"]:
        if p["year"] == 2 and p["semester"] == 1:
            conn.execute(
                "INSERT INTO plan_item (program_id, year, semester, code, credits, "
                "alt_group, category, ctype, note) VALUES (?,?,?,?,?,?,?,?,?)",
                ("IT2565", p["year"], p["semester"], p["code"], p["credits"],
                 p.get("alt_group"), p.get("category"), p.get("ctype"), p.get("note"))
            )

    ck("คืนค่าแล้วไม่มีคำเตือนค้าง",
       [r["id"] for r in verify_db(conn) if not r["ok"]], [])

    conn.close()
    db.unlink(missing_ok=True)

    print("=" * 68)
    print(f"  ผ่าน {passed} / ไม่ผ่าน {failed}")
    print("=" * 68)
    return failed == 0


def _load_dict(conn: sqlite3.Connection, data: dict) -> None:
    """โหลด dict เข้าฐานข้อมูลที่เปิดอยู่แล้ว (ใช้ร่วมกับ selftest)"""
    p = data["program"]
    conn.execute("INSERT OR REPLACE INTO program"
                 " (program_id, name_th, name_en, degree, total_credits, years)"
                 " VALUES (?,?,?,?,?,?)",
                 (p["program_id"], p["name_th"], p.get("name_en"),
                  p.get("degree"), p["total_credits"], p["years"]))
    for c in data.get("courses", []):
        conn.execute("INSERT OR REPLACE INTO course"
                     " (code, name_th, name_en, credits, lecture_h, lab_h, self_h, description_th)"
                     " VALUES (?,?,?,?,?,?,?,?)",
                     (c["code"], c["name_th"], c.get("name_en"), c["credits"],
                      c.get("lecture_h"), c.get("lab_h"), c.get("self_h"),
                      c.get("description_th")))
    for it in data.get("plan", []):
        conn.execute("INSERT INTO plan_item (program_id, year, semester, code,"
                     " credits, alt_group, category, ctype, note)"
                     " VALUES (?,?,?,?,?,?,?,?,?)",
                     (p["program_id"], it["year"], it["semester"], it["code"],
                      it["credits"], it.get("alt_group"), it.get("category"),
                      it.get("ctype"), it.get("note")))
    for r in data.get("prerequisites", []):
        conn.execute("INSERT OR REPLACE INTO prerequisite (code, requires, kind) VALUES (?,?,?)",
                     (r["code"], r["requires"], r.get("kind", "pre")))
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Lab 8B — จากข้อความที่สกัดได้ สู่ฐานข้อมูลที่ตอบคำถามได้",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="ตรวจสภาพแวดล้อม")
    sub.add_parser("selftest", help="ทดสอบ schema กฎตรวจ และด่าน SQL")

    p = sub.add_parser("demo", help="สร้างข้อมูลตัวอย่างสำหรับทดลอง")
    p.add_argument("-o", "--output", required=True)

    p = sub.add_parser("schema", help="เขียน JSON Schema และ SQL DDL")
    p.add_argument("-o", "--output", required=True)

    p = sub.add_parser("extract", help="Markdown -> JSON พร้อมวงจรซ่อม")
    p.add_argument("-i", "--input", required=True, help="ไฟล์ Markdown จาก Lab 7B")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--rounds", type=int, default=MAX_REPAIR_ROUNDS)
    p.add_argument("--max-chars", type=int, default=40000)

    p = sub.add_parser("import-lab7b",
                       help="Lab 7B JSON -> Lab 8B JSON โดยไม่เรียก LLM ซ้ำ")
    p.add_argument("-i", "--input", required=True,
                   help="pred_vlm.json, pred_text.json หรือ pred_baseline.json จาก Lab 7B")
    p.add_argument("-o", "--output", required=True, help="JSON schema ของ Lab 8B")
    p.add_argument("--program-id", default=None, help="ทับ program id จาก Lab 7B")
    p.add_argument("--program-name", default=None, help="ชื่อหลักสูตรภาษาไทย")
    p.add_argument("--total-credits", type=int, default=None,
                   help="หน่วยกิตรวมตามที่หลักสูตรประกาศ; ไม่ระบุจะคำนวณจากแผน")
    p.add_argument("--years", type=int, default=None,
                   help="จำนวนปีของหลักสูตร; ไม่ระบุจะใช้ปีสูงสุดในแผน")
    p.add_argument("--target-plan", choices=["coop", "no_coop"], default="coop",
                   help="เลือกแผนจาก GT แบบ normalized")
    p.add_argument("--general-education", default=None,
                   help="JSON คลังวิชาศึกษาทั่วไป; เพิ่มเฉพาะ course table ไม่เพิ่มในแผน")

    p = sub.add_parser("load", help="JSON -> SQLite")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("-d", "--database", required=True)
    p.add_argument("--replace", action="store_true", help="ลบฐานข้อมูลเดิมก่อน")

    p = sub.add_parser("verify", help="ตรวจความสอดคล้อง 7 ข้อ")
    p.add_argument("-d", "--database", required=True)
    p.add_argument("-o", "--output", default="")

    p = sub.add_parser("ask", help="ถามหนึ่งคำถาม")
    p.add_argument("-d", "--database", required=True)
    p.add_argument("-q", "--question", required=True)

    p = sub.add_parser("eval", help="ประเมินด้วยชุดคำถามทอง")
    p.add_argument("-d", "--database", required=True)
    p.add_argument("-q", "--questions", required=True)
    p.add_argument("-o", "--output", default="")

    args = ap.parse_args()
    if args.cmd == "check":
        sys.exit(0 if check_environment() else 1)
    if args.cmd == "selftest":
        sys.exit(0 if cmd_selftest(args) else 1)
    {"demo": cmd_demo, "schema": cmd_schema, "extract": cmd_extract,
     "import-lab7b": cmd_import_lab7b,
     "load": cmd_load, "verify": cmd_verify, "ask": cmd_ask,
     "eval": cmd_eval}[args.cmd](args)


if __name__ == "__main__":
    main()
