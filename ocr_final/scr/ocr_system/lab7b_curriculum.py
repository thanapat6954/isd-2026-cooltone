#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 lab7b_curriculum.py
 Lab 7B — สกัดแผนการศึกษาจากเล่มหลักสูตร ด้วย LLM ที่รันบนเครื่องตัวเอง
================================================================================
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab7_metrics as M  # noqa: E402


# ==============================================================================
#  ส่วนที่ 0 — ค่าตั้งต้น
# ==============================================================================

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL_OCR = os.getenv("LAB7_MODEL_OCR", "scb10x/typhoon-ocr1.5-3b")
MODEL_TEXT = os.getenv("LAB7_MODEL_TEXT", "qwen3:4b")
DPI = int(os.getenv("LAB7_DPI", "150"))
REQUEST_TIMEOUT = 900

NUM_CTX = int(os.getenv("LAB7B_NUM_CTX", "16384"))
NUM_PREDICT = int(os.getenv("LAB7B_NUM_PREDICT", "8192"))
OCR_NUM_CTX = int(os.getenv("LAB7B_OCR_NUM_CTX", "8192"))
OCR_NUM_PREDICT = int(os.getenv("LAB7B_OCR_NUM_PREDICT", "2048"))

PAGES_PER_CHUNK = int(os.getenv("LAB7_CHUNK", "1"))
SKIP_BASELINE = os.getenv("LAB7_SKIP_BASELINE", "").strip() in ("1", "true", "yes")


# ==============================================================================
#  ส่วนที่ 1 — ตรวจความพร้อม / ยืนยันออฟไลน์
# ==============================================================================

def _need(mod: str, pipname: str = "") -> Any:
    try:
        return __import__(mod)
    except ImportError:
        raise SystemExit(f"\n❌ ไม่พบไลบรารี '{mod}'\n   ติดตั้ง: pip install {pipname or mod}\n")


def assert_offline() -> None:
    allowed = ("127.0.0.1", "localhost", "0.0.0.0", "::1")
    host = OLLAMA_HOST.replace("http://", "").replace("https://", "").split(":")[0]
    if host not in allowed:
        raise SystemExit(
            f"\n❌ OLLAMA_HOST = {OLLAMA_HOST} ไม่ใช่เครื่องภายใน\n"
            f"   แล็บนี้กำหนดให้รันออฟไลน์เท่านั้น  แก้โดย: unset OLLAMA_HOST\n")
    print(f"✓ ยืนยันโหมดออฟไลน์: {OLLAMA_HOST}")


def check_environment() -> bool:
    ok = True
    print("\n" + "=" * 70)
    print("  ตรวจความพร้อมของเครื่อง")
    print("=" * 70)

    if shutil.which("ollama"):
        try:
            v = subprocess.run(["ollama", "--version"], capture_output=True,
                               text=True, timeout=10).stdout.strip()
            print(f"  ✓ พบ Ollama: {v}")
        except Exception:
            print("  ✓ พบ Ollama")
    else:
        print("  ✗ ไม่พบคำสั่ง ollama")
        ok = False

    try:
        requests = _need("requests")
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        installed = [m["name"] for m in r.json().get("models", [])]
        print(f"  ✓ Ollama service ทำงานที่ {OLLAMA_HOST}")
        for tag, role in [(MODEL_OCR, "อ่านภาพ"), (MODEL_TEXT, "จัด JSON")]:
            hit = any(i == tag or i.split(":")[0] == tag for i in installed)
            print(f"  {'✓' if hit else '✗'} [{role}] {tag}"
                  + ("" if hit else f"   --> ollama pull {tag}"))
            if not hit:
                ok = False
    except Exception as e:
        print(f"  ✗ ต่อ Ollama ไม่ได้: {e}")
        ok = False

    for mod, pip in [("fitz", "pymupdf"), ("PIL", "pillow"),
                     ("requests", "requests"), ("pdfplumber", "pdfplumber"),
                     ("pythainlp", "pythainlp")]:
        try:
            __import__(mod)
            print(f"  ✓ python: {mod}")
        except ImportError:
            print(f"  ✗ python: {mod} --> pip install {pip}")
            ok = False

    print("=" * 70)
    print("  พร้อมใช้งาน ✓" if ok else "  ยังไม่พร้อม ✗")
    print("=" * 70 + "\n")
    return ok


# ==============================================================================
#  ส่วนที่ 2 — เตรียม input
# ==============================================================================

def parse_page_range(spec: str, total: int) -> list[int]:
    idx: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            idx.update(range(int(a) - 1, int(b)))
        elif part:
            idx.add(int(part) - 1)
    return sorted(i for i in idx if 0 <= i < total)


def load_pages(path: str, page_spec: str | None = None) -> list[bytes]:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"❌ ไม่พบไฟล์: {path}")

    if p.is_dir():
        image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
        files = sorted(x for x in p.iterdir() if x.suffix.lower() in image_exts)
        if not files:
            raise SystemExit(f"❌ ไม่พบไฟล์ภาพในโฟลเดอร์: {path}")
        return [x.read_bytes() for x in files]

    if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        return [p.read_bytes()]

    pymupdf = _need("pymupdf")
    doc = pymupdf.open(str(p))
    wanted = parse_page_range(page_spec, len(doc)) if page_spec else range(len(doc))

    mat = pymupdf.Matrix(DPI / 72, DPI / 72)
    pages = []
    for i in wanted:
        pix = doc[i].get_pixmap(matrix=mat)
        pages.append(pix.tobytes("png"))
    doc.close()
    return pages


def extract_pdf_text(path: str, page_spec: str | None = None) -> str:
    pdfplumber = _need("pdfplumber")
    out = []
    with pdfplumber.open(path) as pdf:
        wanted = parse_page_range(page_spec, len(pdf.pages)) if page_spec \
            else range(len(pdf.pages))
        for i in wanted:
            t = pdf.pages[i].extract_text(layout=True) or ""
            out.append(f"\n=== หน้า {i + 1} ===\n{t}")
    return "\n".join(out)


# ==============================================================================
#  ส่วนที่ 3 — JSON SCHEMA (🎯 ปรับเพิ่ม Required และ Enum)
# ==============================================================================

_S = {"type": "string"}
_SN = {"type": ["string", "null"]}

COURSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "program": _SN,
        "plan": _SN,
        "courses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": _S,
                    "name_th": _SN,
                    "name_en": _SN,
                    "credits": _SN,
                    "year": {"type": ["integer", "string", "null"]},
                    "semester": {"type": ["integer", "string", "null"]},
                    "category": {
                        "type": ["string", "null"],
                        "enum": ["หมวดวิชาศึกษาทั่วไป", "หมวดวิชาเฉพาะ", "หมวดวิชาเลือกเสรี", None],
                    },
                    "type": {
                        "type": ["string", "null"],
                        "enum": ["บังคับ", "เลือก", None],
                    },
                    "prerequisite": _SN,
                    "flexible_year_semester": _SN,
                    "note": _SN,
                    "alt_group": _SN,
                    "source_file": _SN,
                    "page_number": {"type": ["integer", "null"]},
                },
                "required": [
                    "code", "name_th", "name_en", "credits",
                    "year", "semester", "category", "type"
                ],
            },
        },
    },
    "required": ["courses"],
}


# ==============================================================================
#  ส่วนที่ 4 — PROMPT
# ==============================================================================

SYSTEM_PROMPT = """คุณคือ AI ระดับผู้เชี่ยวชาญด้านการสกัดข้อมูลโครงสร้างหลักสูตรมหาวิทยาลัยไทย
หน้าที่ของคุณคืออ่านข้อมูล OCR และแปลงเป็น JSON ที่มีความถูกต้องระดับ 100%
กฎเหล็ก (CRITICAL RULES):
1. ห้ามคิดค้นวิชาขึ้นมาเอง
2. ห้ามหยุดทำกลางคาง ห้ามละเว้นข้อมูล ห้ามใช้สัญลักษณ์ ... (ellipsis) เพื่อย่อข้อมูลเด็ดขาด
3. ต้องสกัดข้อมูลออกมา "ทุกแถว" ที่ปรากฏในเอกสาร
4. หากไม่พบข้อมูลในฟิลด์ใดให้ใช้ null (ยกเว้นมีกฎระบุไว้เป็นอย่างอื่น)"""

EXTRACT_PROMPT = """ต่อไปนี้คือข้อความสกัดจากเล่มหลักสูตรมหาวิทยาลัยในประเทศไทย
จงสกัดรายวิชาและสล็อตวิชาเลือกทั้งหมด ออกมาเป็น JSON Array ตาม Schema ที่กำหนดอย่างเคร่งครัด

=== กติกาการสกัดข้อมูล ===

[1] ความสมบูรณ์และการจัดการตาราง (Zero Data Loss):
    - สกัดวิชาออกมาทีละรายการให้ครบทุกวิชา ทุกสล็อต ห้ามข้าม ห้ามเลิกทำกลางทางเด็ดขาด
    - กรณีตารางมีการควบเซลล์ (Merged Cells) ให้กระจายข้อมูลนั้นลงมายังวิชาย่อยทุกตัวให้ครบถ้วน
    - รายวิชาที่อยู่ภายใต้หัวข้อหมวดหมู่ใด ให้ถือว่าอยู่ใน category นั้นด้วย (สืบทอดหมวดหมู่ลงมา)

[2] รหัสวิชา (code) และสล็อตวิชาเลือก:
    - วิชาปกติ: คัดลอกรหัสวิชาตามเอกสาร (เช่น "06026200")
    - วิชาเลือกกลุ่ม Wildcard: ต้องคัดลอกรหัสที่มี x มาทั้งหมด ห้ามตัดทิ้ง (เช่น "06026xxx", "90644xxx")
    - วิชาเลือกที่ไม่ระบุรหัส: ให้ใช้ชื่อสล็อตเป็น code (เช่น "วิชาเลือกเสรี 1", "กลุ่มวิชาศึกษาทั่วไป")

[3] หน่วยกิต (credits):
    - ต้องระบุหน่วยกิตเสมอ ห้ามปล่อยว่าง ("") หรือ null เด็ดขาด
    - วิชาปกติต้องคัดลอกรูปแบบเต็มตามเอกสาร เช่น "3(3-0-6)" ห้ามย่อเหลือ "3"
    - หากเป็นสล็อตวิชาเลือก ให้คัดลอกรูปแบบที่พิมพ์ไว้; ใช้ "3" เฉพาะเมื่อเอกสารมีเพียงเลข 3 จริง ๆ

[4] หมวดหมู่และประเภทวิชา (category & type):
    - category: ต้องเป็นหนึ่งใน 3 ค่านี้เท่านั้น -> "หมวดวิชาศึกษาทั่วไป" | "หมวดวิชาเฉพาะ" | "หมวดวิชาเลือกเสรี"
    - type: ต้องเป็นหนึ่งใน 2 ค่านี้เท่านั้น -> "บังคับ" | "เลือก"

[5] ชั้นปีและภาคการศึกษา (year & semester):
    - หากรายการนั้นอยู่ในตารางแผนการเรียนภาคไหน ให้ใส่ year (1-4) และ semester (1-3) ตามภาคนั้นเสมอ
    - ห้ามใส่ year=null / semester=null สำหรับวิชาที่อยู่ในตารางแผนการเรียน

[6] วิชาบังคับก่อน (prerequisite):
    - ระบุรหัสวิชาบังคับก่อนตามจริง
    - หากไม่มี ให้ระบุว่า "ไม่มี" (ห้ามใส่ null)

[7] ชื่อวิชา (name_th, name_en):
    - คัดลอกตัวสะกดตามเอกสารทุกตัว ห้ามแก้คำผิดหรือปรับเป็นคำที่คิดว่าถูกกว่า
    - name_th: ชื่อวิชาภาษาไทยเท่านั้น (ห้ามมีรหัส ชื่ออังกฤษ หรือหัวข้อกลุ่มวิชาปนมา)
    - name_en: ชื่อวิชาภาษาอังกฤษ หากไม่มีพิมพ์ไว้ให้ใส่ null (ห้ามคิดคำแปลเอง)
    - ถ้าเซลล์เดียวมีชื่อไทยตามด้วยชื่ออังกฤษ ต้องแยกออกเป็นสองฟิลด์เสมอ
    - ห้ามใส่ข้อความหัวข้อ เช่น "กลุ่มวิชาที่กำหนดโดยคณะ*" หรือ "กลุ่มวิชาด้าน..." เป็นชื่อวิชา

[8] สล็อตกลุ่มวิชาเลือกหลายสาขา:
    - ถ้าหนึ่งสล็อต wildcard แสดงชื่อทางเลือกหลายกลุ่มในเซลล์เดียว ให้เก็บเป็นหนึ่งรายการ
      และคัดลอกชื่อไทยทุกบรรทัดรวมไว้ใน name_th โดยคั่นด้วย newline; ทำแบบเดียวกันกับ name_en
    - อย่าแตกชื่อทางเลือกของสล็อตเดียวออกเป็นหลายรายวิชา

=== โครงสร้าง JSON ที่ต้องการ (Output Format) ===
{{
  "courses": [
    {{
      "code": "รหัสวิชา",
      "name_th": "ชื่อวิชาภาษาไทย",
      "name_en": "ชื่อวิชาภาษาอังกฤษ หรือ null",
      "credits": "หน่วยกิต",
      "category": "หมวดหมู่ (ตามกฎข้อ 4)",
      "type": "ประเภท (ตามกฎข้อ 4)",
      "year": 1,
      "semester": 1,
      "prerequisite": "รหัสวิชาบังคับก่อน หรือ 'ไม่มี'"
    }}
  ]
}}

=== ข้อความจากเอกสาร ===
{document_text}

=== สิ้นสุดข้อความ ===
สร้างผลลัพธ์เป็น JSON เท่านั้น"""

TYPHOON_PROMPT = """Extract all text from the image accurately.
Instructions:
- Only return the clean Markdown text.
- Do not include any explanation, conversational text, or greetings.
- Transcribe every character verbatim, including apparent spelling mistakes in Thai or English. Never autocorrect.
- Render all tables strictly as standard Markdown tables (using | and -).
- Do not skip any rows or columns in the tables. Maintain the exact order."""


# ==============================================================================
#  ส่วนที่ 5 — เรียก Ollama
# ==============================================================================

def ollama_chat(model: str, messages: list[dict], *, fmt: dict | None = None,
                images: list[bytes] | None = None, temperature: float = 0.0,
                retries: int = 2, think: bool | None = None,
                num_ctx: int | None = None,
                num_predict: int | None = None) -> str:
    requests = _need("requests")

    if images:
        messages = [dict(m) for m in messages]
        messages[-1]["images"] = [base64.b64encode(im).decode() for im in images]

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx or NUM_CTX,
            "num_predict": num_predict or NUM_PREDICT,
        },
    }
    if fmt is not None:
        payload["format"] = fmt
    if think is not None:
        payload["think"] = think

    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            t0 = time.time()
            r = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            body = r.json()
            content = body["message"]["content"]
            n_out = body.get("eval_count", 0)
            print(f"      ({model}: {time.time() - t0:.1f} วิ, {len(content):,} ตัวอักษร, {n_out:,} tokens)")
            if not content.strip():
                raise ValueError("โมเดลตอบว่าง")
            return content
        except Exception as e:
            last = e
            if attempt < retries:
                time.sleep(3)
    raise RuntimeError(f"เรียก {model} ไม่สำเร็จ: {last}")


def parse_json(text: str) -> dict:
    t = re.sub(r"<think>.*?</think>", "", text.strip(), flags=re.DOTALL)
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t.strip(), flags=re.MULTILINE)
    starts = [p for p in (t.find("{"), t.find("[")) if p != -1]
    if not starts:
        raise ValueError(f"ไม่พบ JSON:\n{text[:400]}")
    
    clean_str = t[min(starts):]
    try:
        obj, _ = json.JSONDecoder().raw_decode(clean_str)
        return obj
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*([}\]])", r"\1", clean_str)
        obj, _ = json.JSONDecoder().raw_decode(repaired)
        return obj


# ==============================================================================
#  ส่วนที่ 6 — การ Normalization และ รวมผลจากหลาย Chunk (🎯 Patch รวม)
# ==============================================================================

def normalize_course(c: dict) -> dict:
    """ปรับแก้และจัดรูปแบบข้อมูลวิชาให้สอดคล้องกับ Ground Truth ก่อนทำการ merge"""
    c = dict(c)
    
    # 1. จัดการ year และ semester (ถ้าเป็น '0' หรือ 0 ให้เปลี่ยนเป็น None)
    y = c.get("year")
    s = c.get("semester")
    if str(y).strip() == "0":
        c["year"] = None
    if str(s).strip() == "0":
        c["semester"] = None

    # 2. ทำความสะอาดข้อความทั่วไป
    for key in ["code", "name_th", "name_en", "credits", "category", "type", "prerequisite", "flexible_year_semester"]:
        if c.get(key) is not None:
            val = str(c[key]).strip()
            c[key] = val if val else None

    # Small local text models sometimes leave the English title or a merged-cell
    # section label inside name_th.  Only remove unambiguous material; never
    # rewrite Thai spelling because the metric must reflect the printed book.
    name_th = c.get("name_th")
    name_en = c.get("name_en")
    if not name_th and name_en and re.search(r"[ก-๙]", name_en):
        # A merged header can shift the Thai title one column to the right.
        # Moving Thai text back is deterministic and does not invent a title.
        name_th, name_en = name_en, None
        c["name_th"], c["name_en"] = name_th, name_en
    if name_th:
        name_th = re.sub(
            r"^(?:\*{0,2})?กลุ่มวิชาที่กำหนดโดยคณะ\*{0,2}\s*", "", name_th).strip()
        if name_en and name_th.endswith(name_en):
            name_th = name_th[:-len(name_en)].strip()
        else:
            english_tail = re.search(r"\s+([A-Z][A-Z0-9 '&(),./-]{3,})$", name_th)
            if english_tail:
                if not name_en:
                    c["name_en"] = english_tail.group(1).strip()
                name_th = name_th[:english_tail.start()].strip()
        c["name_th"] = name_th or None

    if code := str(c.get("code") or "").strip().lower():
        if code == "9064xxxx" and c.get("name_th"):
            lines = [x.strip() for x in str(c["name_th"]).splitlines() if x.strip()]
            preferred = next((x for x in lines if "ศึกษาทั่วไป" in x), None)
            if preferred:
                c["name_th"] = preferred

    credits = str(c.get("credits") or "")
    if credits:
        credits = re.sub(r"\s+(?=\()|(?<=\))\s+", "", credits)
        alternatives = re.findall(r"\d+\(\d+-\d+-\d+\)", credits)
        if alternatives:
            c["credits"] = " หรือ ".join(dict.fromkeys(alternatives))

    # The curriculum code families make category recovery deterministic across
    # DSBA, AI and IT; this is preferable to asking the LLM to guess a category
    # that is represented by merged headers in the source table.
    code = str(c.get("code") or "").strip().lower()
    names = " ".join(str(c.get(k) or "") for k in ("name_th", "name_en"))
    if (re.search(r"วิชาเลือกเสรี|free\s+elective", names, re.I)
            or bool(re.fullmatch(r"x+", code))):
        c["category"] = "หมวดวิชาเลือกเสรี"
        c["type"] = "เลือก"
    elif code.startswith("906"):
        c["category"] = "หมวดวิชาศึกษาทั่วไป"
    elif code.startswith("060"):
        c["category"] = "หมวดวิชาเฉพาะ"

    return c


def _recover_thai_name_from_ocr_table(document_text: str, code: str) -> str | None:
    """Recover a Thai title from a simple HTML OCR row when JSON column mapping lost it."""
    if not code or not re.fullmatch(r"\d{8}", code):
        return None
    match = re.search(
        rf"<tr><td[^>]*>\s*{re.escape(code)}\s*</td>"
        rf"<td[^>]*>(.*?)</td>",
        document_text, re.I | re.S,
    )
    if not match:
        return None
    cell = re.sub(r"<br\s*/?>", "\n", match.group(1), flags=re.I)
    cell = re.sub(r"<[^>]+>|\*+", " ", cell)
    cell = re.sub(r"^\s*กลุ่มวิชาที่กำหนดโดยคณะ\s*", "", cell).strip()
    english = re.search(r"\s+[A-Z][A-Z0-9 '&(),./-]{3,}$", cell)
    if english:
        cell = cell[:english.start()].strip()
    thai_lines = [line.strip() for line in cell.splitlines() if re.search(r"[ก-๙]", line)]
    return "\n".join(thai_lines) or None


def merge_chunks(chunks: list[dict]) -> dict:
    seen: set[tuple] = set()
    courses: list[dict] = []
    term_totals: list[dict] = []
    n_dup = 0
    last_category = None  # ใช้สำหรับ Forward-fill category

    for ch in chunks:
        term_totals.extend(ch.get("term_totals") or [])
        for raw_c in ch.get("courses") or []:
            c = normalize_course(raw_c)

            # Forward-fill category กรณีโมเดลเว้นว่างในแถวถัดๆ มา
            if c.get("category"):
                last_category = c["category"]
            elif last_category:
                c["category"] = last_category

            key = (
                M.normalize(c.get("code"), "strict"),
                str(c.get("year")),
                str(c.get("semester")),
                M.normalize(c.get("name_th"), "strict"),
            )
            if key in seen:
                n_dup += 1
                continue
            seen.add(key)
            courses.append(c)

    if n_dup:
        print(f"      กรองวิชาซ้ำออก {n_dup} รายการ")

    # One source page should declare a term total once.  Keep the metadata in
    # Lab 7B output so Lab 8B can detect (and visibly represent) an OCR row that
    # was missed even though the printed table total was read correctly.
    unique_term_totals = {}
    for item in term_totals:
        key = (item.get("year"), item.get("semester"))
        unique_term_totals[key] = item

    return {
        "program": next((ch.get("program") for ch in chunks if ch.get("program")), None),
        "plan": next((ch.get("plan") for ch in chunks if ch.get("plan")), None),
        "courses": courses,
        "term_totals": list(unique_term_totals.values()),
    }


# ==============================================================================
#  ส่วนที่ 7 - 9 — PIPELINES
# ==============================================================================

def pipeline_vlm(pages: list[bytes], outdir: Path, *,
                 page_numbers: list[int] | None = None,
                 source_file: str | None = None) -> dict:
    md_pages: list[str] = []
    for i, png in enumerate(pages):
        print(f"    [ขั้น 1/2] Typhoon-OCR หน้า {i + 1}/{len(pages)}")
        md = ""
        for attempt in range(2):
            md = ollama_chat(MODEL_OCR,
                             [{"role": "user", "content": TYPHOON_PROMPT}],
                             images=[png], temperature=0.1,
                             num_ctx=OCR_NUM_CTX,
                             num_predict=OCR_NUM_PREDICT)
            meaningful = re.sub(r"[^0-9A-Za-zก-๙]+", "", md)
            if len(meaningful) >= 20:
                break
            print(f"      ! OCR หน้า {i + 1} ได้ข้อความใช้การไม่ได้; "
                  f"ลองใหม่ {attempt + 1}/2")
        else:
            raise RuntimeError(
                f"Typhoon-OCR หน้า {i + 1} คืนค่าว่าง/ขยะสองครั้ง; "
                "ยกเลิกก่อนเขียนทับ pred_vlm.json เดิม"
            )
        md_pages.append(md)

    (outdir / "intermediate_vlm.md").write_text(
        "\n\n---\n\n".join(md_pages), encoding="utf-8")

    return _text_to_json_chunked(
        md_pages, page_numbers=page_numbers, source_file=source_file)


def _text_to_json_chunked(md_pages: list[str], *,
                          page_numbers: list[int] | None = None,
                          source_file: str | None = None) -> dict:
    chunks: list[dict] = []
    n_chunks = (len(md_pages) + PAGES_PER_CHUNK - 1) // PAGES_PER_CHUNK

    for ci in range(n_chunks):
        part = md_pages[ci * PAGES_PER_CHUNK:(ci + 1) * PAGES_PER_CHUNK]
        print(f"    [ขั้น 2/2] จัด JSON ก้อนที่ {ci + 1}/{n_chunks} ({len(part)} หน้า)")
        try:
            document_text = "\n\n".join(part)
            heading_re = re.compile(r"ปีที่\s*\d+\s*ภาคการศึกษาที่\s*\d+")
            headings = list(heading_re.finditer(document_text))
            extraction_parts = [document_text]
            if len(headings) > 1:
                extraction_parts = [
                    document_text[match.start():(headings[i + 1].start()
                                                  if i + 1 < len(headings)
                                                  else len(document_text))]
                    for i, match in enumerate(headings)
                ]
            d = {"courses": [], "term_totals": []}
            for extraction_part in extraction_parts:
                raw = ollama_chat(
                    MODEL_TEXT,
                    [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": EXTRACT_PROMPT.format(
                         document_text=extraction_part)}],
                    fmt=COURSE_SCHEMA,
                    think=False,
                    num_ctx=NUM_CTX,
                    num_predict=NUM_PREDICT,
                )
                extracted = parse_json(raw)
                d["courses"].extend(extracted.get("courses") or [])
                term_match = heading_re.search(extraction_part)
                # A final page can also print the whole-program grand total
                # after the term table.  The term's own first "รวม" is the
                # relevant value; using the last occurrence can mistake 129
                # programme credits for one semester's credits.
                total_at = extraction_part.find("รวม")
                total_tail = (
                    re.sub(r"<[^>]+>", " ", extraction_part[total_at + 3:])
                    if total_at >= 0 else ""
                )
                total_match = re.search(r"(?<!\d)(\d{1,3})(?!\d)", total_tail)
                if term_match and total_match:
                    year, semester = map(int, re.findall(r"\d+", term_match.group(0)))
                    d["term_totals"].append({
                        "year": year,
                        "semester": semester,
                        "credits": int(total_match.group(1)),
                    })
            # Each extraction chunk corresponds to known source pages.  Keep only
            # terms that are actually headed on those pages, and let elective rows
            # with missing 0/0 terms inherit the nearest valid table heading.
            allowed_terms = {
                (int(y), int(s))
                for y, s in re.findall(
                    r"ปีที่\s*(\d+)\s*ภาคการศึกษาที่\s*(\d+)", document_text)
            }
            active_term = next(iter(allowed_terms)) if len(allowed_terms) == 1 else None
            repaired_courses = []
            chunk_pages = (page_numbers or [])[ci * PAGES_PER_CHUNK:(ci + 1) * PAGES_PER_CHUNK]
            source_page = chunk_pages[0] if chunk_pages else None
            for term_total in d["term_totals"]:
                term_total["source_file"] = source_file
                term_total["page_number"] = source_page
            for course in d.get("courses") or []:
                try:
                    term = (int(course.get("year")), int(course.get("semester")))
                except (TypeError, ValueError):
                    term = (0, 0)
                if allowed_terms and term != (0, 0):
                    if term not in allowed_terms:
                        active_term = None
                        continue
                    active_term = term
                elif term == (0, 0) and active_term:
                    course["year"], course["semester"] = active_term
                    course["flexible_year_semester"] = None
                elif allowed_terms and term == (0, 0):
                    continue
                course["source_file"] = source_file
                course["page_number"] = source_page
                preview = normalize_course(course)
                if not preview.get("name_th"):
                    recovered_name = _recover_thai_name_from_ocr_table(
                        document_text, str(course.get("code") or "").strip())
                    if recovered_name:
                        course["name_th"] = recovered_name
                        if re.search(r"[ก-๙]", str(course.get("name_en") or "")):
                            course["name_en"] = None
                names = " ".join(str(course.get(k) or "") for k in ("name_th", "name_en"))
                if re.search(r"วิชาเลือกเสรี|FREE\s+ELECTIVE", names, re.I):
                    course["code"] = course.get("name_th") or "FREE ELECTIVE"
                repaired_courses.append(course)
            coop_rows = [
                course for course in repaired_courses
                if re.search(r"สหกิจ|COOPERATIVE", " ".join(
                    str(course.get(k) or "") for k in ("name_th", "name_en")), re.I)
                and re.match(r"^6(?:\D|$)", str(course.get("credits") or ""))
            ]
            if len(coop_rows) >= 2:
                group = f"coop-alternative-{source_file or 'source'}-{source_page or ci + 1}"
                for course in coop_rows:
                    course["alt_group"] = group
            d["courses"] = repaired_courses
            chunks.append(d)
        except Exception as e:
            print(f"      ❌ ก้อนที่ {ci + 1} ล้มเหลว: {e}")

    return merge_chunks(chunks)


def pipeline_text(pdf_path: str, page_spec: str | None) -> dict:
    text = extract_pdf_text(pdf_path, page_spec)
    pages_text = re.split(r"\n=== หน้า \d+ ===\n", text)
    pages_text = [p for p in pages_text if p.strip()]
    if not pages_text:
        return {}
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        indices = list(parse_page_range(page_spec, len(pdf.pages))) if page_spec else list(range(len(pdf.pages)))
    return _text_to_json_chunked(
        pages_text, page_numbers=[i + 1 for i in indices],
        source_file=Path(pdf_path).name)


# ==============================================================================
#  ส่วนที่ 10 — ตรวจความสอดคล้องภายใน (🎯 ปรับแก้ Regex Match)
# ==============================================================================

VALID_CATEGORIES = {"หมวดวิชาศึกษาทั่วไป", "หมวดวิชาเฉพาะ", "หมวดวิชาเลือกเสรี"}
VALID_TYPES = {"บังคับ", "เลือก"}
CREDIT_RE = re.compile(r"^\d+\(\d+-\d+-\d+\)$")


def verify_internal(data: dict) -> dict:
    issues: list[str] = []
    courses = data.get("courses") or []
    credits_by_term: dict[str, int] = defaultdict(int)

    for c in courses:
        code = c.get("code")
        cr = c.get("credits") or ""
        y, s = str(c.get("year")), str(c.get("semester"))

        if c.get("category") and c["category"] not in VALID_CATEGORIES:
            issues.append(f"category ไม่ถูกต้อง: {code} -> {c['category']!r}")
        if c.get("type") and c["type"] not in VALID_TYPES:
            issues.append(f"type ไม่ถูกต้อง: {code} -> {c['type']!r}")

        # Fix 🎯: strip ข้อมูลกระทันหันก่อน match ป้องกันนับหน่วยกิตเป็น 0
        m = re.match(r"(\d+)\s*\(", cr.strip())
        if m and y not in ("0", "None") and s not in ("0", "None"):
            n_credit = int(m.group(1))
            credits_by_term[f"{y}/{s}"] += n_credit

    return {
        "ok": len(issues) == 0,
        "n_courses": len(courses),
        "credits_by_term": dict(sorted(credits_by_term.items())),
        "total_credits_fixed_terms": sum(credits_by_term.values()),
        "issues": issues,
    }


# ==============================================================================
#  ส่วนที่ 11 — ประเมินผลเทียบ GROUND TRUTH
# ==============================================================================

def clean_gt(gt: dict) -> list[dict]:
    named = [c for c in (gt.get("courses") or []) if c.get("name_th")]
    # Flat GT files also contain year=0 course-catalog descriptions.  Lab 7B is
    # run on academic-plan page ranges, so counting those unseen catalogue rows
    # as OCR misses understates recall.  Evaluate the matching plan slice when
    # it is present, while retaining compatibility with catalogue-only GT files.
    planned = []
    for course in named:
        try:
            if int(course.get("year")) >= 1 and int(course.get("semester")) >= 1:
                planned.append(course)
        except (TypeError, ValueError):
            continue
    return planned or named


def key_strict(c: dict) -> str:
    return "|".join([
        M.normalize(c.get("code"), "strict"),
        M.normalize(c.get("year"), "strict"),
        M.normalize(c.get("semester"), "strict"),
        M.normalize(c.get("name_th"), "strict"),
    ])


def key_loose(c: dict) -> str:
    return "|".join([
        M.normalize(c.get("code"), "strict"),
        M.normalize(c.get("year"), "strict"),
    ])


def evaluate(pred: dict, gt: dict) -> tuple[dict, dict]:
    S = M.FieldStat
    stats: dict[str, M.FieldStat] = {
        "code":      S("รหัสวิชา"),
        "name_th":   S("ชื่อวิชา (ไทย) ⭐"),
        "name_en":   S("ชื่อวิชา (อังกฤษ) ⭐"),
        "credits":   S("หน่วยกิต"),
        "year_sem":  S("ปี/ภาค"),
        "category":  S("หมวดวิชา"),
        "ctype":     S("บังคับ/เลือก"),
        "prereq":    S("วิชาบังคับก่อน"),
        "flexible":  S("ปี/ภาคยืดหยุ่น"),
    }

    g_courses = clean_gt(gt)
    p_courses = pred.get("courses") or []

    align = M.align_multipass(g_courses, p_courses, [key_strict, key_loose])

    for g, p in align.matched:
        k = f"{g.get('code')}"
        stats["code"].add(g.get("code"), p.get("code"), k, track_wer=False)
        stats["name_th"].add(g.get("name_th"), p.get("name_th"), k, track_wer=True)
        stats["name_en"].add(g.get("name_en"), p.get("name_en"), k, track_wer=True)
        stats["credits"].add(g.get("credits"), p.get("credits"), k, track_wer=False)
        stats["year_sem"].add(f"{g.get('year')}/{g.get('semester')}",
                              f"{p.get('year')}/{p.get('semester')}", k, track_wer=False)
        stats["category"].add(g.get("category"), p.get("category"), k, track_wer=False)
        stats["ctype"].add(g.get("type"), p.get("type"), k, track_wer=False)
        stats["prereq"].add(g.get("prerequisite"), p.get("prerequisite"), k, track_wer=False)
        stats["flexible"].add(g.get("flexible_year_semester"), p.get("flexible_year_semester"), k, track_wer=False)

    align_summary = {
        "matched": len(align.matched),
        "missed": len(align.missed),
        "spurious": len(align.spurious),
        "precision": round(align.precision, 4),
        "recall": round(align.recall, 4),
        "f1": round(align.f1, 4),
        "gt_total": len(g_courses),
        "pred_total": len(p_courses),
    }
    return stats, align_summary

# 🟢 แทรกฟังก์ชันนี้ไว้ก่อน def main()
def denormalize_gt(data: dict, target_plan: str = "coop") -> dict:
    """แปลง GT แบบ normalized (courses_master + curriculum_schedule) ให้เป็น
    {"program": ..., "courses": [...]} แบบเดิมที่ evaluate()/clean_gt() ใช้อยู่

    Backward compatible: ถ้าไม่มีทั้ง courses_master และ curriculum_schedule
    ถือว่าเป็น flat schema เดิม คืนค่าเดิมกลับไปเฉยๆ

    target_plan: "coop" (ค่าเริ่มต้น) หรือ "no_coop" — ดูรายละเอียดเดียวกับ
    denormalize_gt() ใน lab8b_curriculum_db.py (โค้ดชุดนี้เหมือนกันทุก
    ตัวอักษร เพื่อให้ผลการ evaluate ที่นี่กับผล import-lab7b ฝั่ง Lab 8B
    ตรงกันเสมอ ไม่ใช่คนละตรรกะที่ค่อย ๆ เพี้ยนออกจากกันทีหลัง)

    หมายเหตุ field name: courses_master คีย์รายวิชาด้วย "code" (ไม่ใช่
    "course_code"), ส่วน curriculum_schedule กรองด้วย "applicable_plans"/
    "schedule_by_plan" (ไม่ใช่ "plan") — จุดนี้เป็นจุดที่โค้ดเดิมพลาดมาก่อน
    ทำให้ name_th/credits ว่างเปล่าทุกแถวเพราะ lookup ไม่เจอ
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

        # curriculum_schedule บางแถวใช้รหัสรวม เช่น "06026259 หรือ 06026260"
        # ซึ่งไม่ตรงกับคีย์เดี่ยวใน courses_master ตรง ๆ ต้องลองแตกรหัสย่อย
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


# ==============================================================================
#  ส่วนที่ 12 — MAIN
# ==============================================================================

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", help="ไฟล์เล่มหลักสูตร (.pdf/.png)")
    ap.add_argument("-g", "--gt", help="ไฟล์ ground truth (.json)")
    ap.add_argument("-o", "--out", default="output")
    ap.add_argument("-p", "--pipeline", default="vlm", choices=["all", "text", "vlm"])
    ap.add_argument("--pages", help='เลือกเฉพาะบางหน้า เช่น "30-36"')
    ap.add_argument("--target-plan", choices=["coop", "no_coop"], default=None,
                    help="แผนที่ใช้เมื่อ GT เป็น normalized; ไม่ระบุจะเดาจากชื่อไฟล์")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.check:
        sys.exit(0 if check_environment() else 1)

    # Auto-pages guard (🎯 ปรับเพิ่มตรวจสอบชื่อ Ground truth)
    if not args.pages and args.gt:
        gt_name = args.gt.lower()
        if "coop" in gt_name:
            args.pages = "30-36"
            print("💡 [Auto] ตรวจพบ Ground Truth สหกิจศึกษา: เลือกหน้า 30-36 อัตโนมัติ")
        elif "no_coop" in gt_name:
            args.pages = "23-29"
            print("💡 [Auto] ตรวจพบ Ground Truth ปกติ: เลือกหน้า 23-29 อัตโนมัติ")

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    assert_offline()
    pages = load_pages(args.input, args.pages)
    page_numbers = None
    if Path(args.input).suffix.lower() == ".pdf":
        pymupdf = _need("pymupdf")
        with pymupdf.open(args.input) as doc:
            indices = list(parse_page_range(args.pages, len(doc))) if args.pages else list(range(len(doc)))
        page_numbers = [i + 1 for i in indices]

    data = (pipeline_vlm(
        pages, outdir, page_numbers=page_numbers,
        source_file=Path(args.input).name)
        if args.pipeline == "vlm" else pipeline_text(args.input, args.pages))
    pred_path = outdir / f"pred_{args.pipeline}.json"
    pred_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  เขียน {pred_path}")

    internal_check = verify_internal(data)
    (outdir / "internal_check.json").write_text(
        json.dumps(internal_check, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.gt:
        gt = json.loads(Path(args.gt).read_text(encoding="utf-8"))
        if "courses_master" in gt:
            plan_type = args.target_plan or ("no_coop" if "no_coop" in args.gt.lower() else "coop")
            gt = denormalize_gt(gt, target_plan=plan_type)
        stats, align = evaluate(data, gt)
        M.print_table(stats, f"PIPELINE = {args.pipeline}")
        print(f"\n  จับคู่วิชา: เจอ {align['matched']}/{align['gt_total']} "
              f"| ตก {align['missed']} | แต่งเกิน {align['spurious']}   "
              f"P={align['precision']:.3f} R={align['recall']:.3f} F1={align['f1']:.3f}")
        evaluation = M.stats_to_dict(stats)
        evaluation["alignment"] = align
        evaluation["internal_check"] = internal_check
        (outdir / "evaluation.json").write_text(
            json.dumps({args.pipeline: evaluation}, ensure_ascii=False, indent=2),
            encoding="utf-8")


if __name__ == "__main__":
    main()
    
