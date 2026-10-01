"""Application 1: curriculum database question answering."""

import json
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import PROJECT_ROOT, settings

# เชื่อม Lab 10 -> Lab 8B เฉพาะ Ollama client; discovery/validation อยู่ในแอปนี้
SRC_DIR = PROJECT_ROOT / "scr"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
os.environ["LAB8_OLLAMA_URL"] = settings.ollama_url
os.environ["LAB8_MODEL_TEXT"] = settings.ollama_model
from ocr_system import lab8b_curriculum_db as lab8b  # noqa: E402

from .database import CurriculumDatabase, DatabaseRegistry  # noqa: E402
from .model_service import QwenTextToSQL  # noqa: E402
from .schemas import (  # noqa: E402
    AskRequest,
    AskResponse,
    FrontendAskRequest,
    FrontendAskResponse,
    HealthResponse,
)


STATIC_DIR = Path(__file__).resolve().parent / "static"
app = FastAPI(
    title=f"{settings.app_name} — Curriculum",
    description="Qwen text-to-SQL + SQLite curriculum application",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
FRONTEND_DIR = PROJECT_ROOT / "frontend"
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
registry = DatabaseRegistry(settings.database_root)
model = QwenTextToSQL(settings, lab8b)
if settings.debug:
    logging.getLogger("curriculum_app").setLevel(logging.INFO)


def _select_databases(curriculum: str = "") -> list:
    registry.refresh()
    selected = registry.select(curriculum) if curriculum.strip() else registry.active_programs
    if not selected:
        raise HTTPException(status_code=404, detail="ไม่พบฐานข้อมูลหลักสูตรที่ระบุ")
    return selected


def _frontend_question(request: FrontendAskRequest) -> str:
    """Add the selected curriculum to the natural-language question."""
    curriculum_aliases = {
        "AIT": "AI", "AI": "AI", "DSBA": "DSBA", "IT": "IT", "BIT": "BIT"
    }
    selected = request.curriculum.strip()
    curriculum = curriculum_aliases.get(selected.upper(), selected)
    version_context = {
        "latest": "ฉบับล่าสุด 2565",
        "revised": "ฉบับปรับปรุง 2565",
        "old": "ฉบับเก่า 2560",
        "all versions": "ทั้งฉบับเก่า 2560 และฉบับปรับปรุง 2565",
    }.get(request.version, request.version)
    return f"หลักสูตร {curriculum} {version_context}: {request.question.strip()}"


def _source_pages(row: dict[str, Any]) -> list[int]:
    """Read one or more page numbers from a database result row."""
    values: list[int] = []
    if row.get("page_number") is not None:
        try:
            values.append(int(row["page_number"]))
        except (TypeError, ValueError):
            pass
    if row.get("source_pages"):
        for value in str(row["source_pages"]).replace(";", ",").split(","):
            try:
                values.append(int(value.strip()))
            except (TypeError, ValueError):
                continue
    return sorted(set(values))


def _source_book_pages(row: dict[str, Any]) -> list[int]:
    values: list[int] = []
    for key in ("printed_page_number", "source_printed_pages"):
        if row.get(key) is None:
            continue
        for value in str(row[key]).replace(";", ",").split(","):
            try:
                values.append(int(value.strip()))
            except (TypeError, ValueError):
                continue
    return sorted(set(values))


def _source_section(row: dict[str, Any], intent: str) -> str:
    """Choose a readable section title from fields returned by SQL."""
    source = row.get("_source") or {}
    context = [
        str(row.get("source_file")) if row.get("source_file") else None,
        f"พ.ศ. {source.get('curriculum_version')}" if source.get("curriculum_version") else None,
        str(source.get("plan")) if source.get("plan") else None,
    ]
    for key in ("name_th", "name_en", "category", "note", "program_id"):
        if row.get(key):
            context.append(str(row[key]))
            return " · ".join(value for value in context if value)
    curriculum = source.get("curriculum_name", "หลักสูตร")
    intent_labels = {
        "program_total_credits": "หน่วยกิตรวมของหลักสูตร",
        "semester_credits": "หน่วยกิตตามภาคการศึกษา",
        "year_credits": "หน่วยกิตตามชั้นปี",
        "course_count": "จำนวนรายวิชาในแผนการเรียน",
        "course_list": "แผนการเรียน",
        "program_years": "ระยะเวลาการศึกษา",
        "program_info": "ข้อมูลหลักสูตร",
        "course_detail": "รายละเอียดรายวิชา",
        "course_search": "รายละเอียดรายวิชา",
        "prerequisite": "วิชาบังคับก่อน",
    }
    context.append(f"{curriculum} — {intent_labels.get(intent, 'ข้อมูลจากฐานหลักสูตร')}")
    return " · ".join(value for value in context if value)


def _source_quote(row: dict[str, Any]) -> str | None:
    """Build a readable excerpt instead of exposing raw database key/value text."""
    name = row.get("name_th") or row.get("name_en")
    code = row.get("code")
    credits = row.get("credits_raw") or row.get("credits")
    if name:
        identity = str(name)
        if code and not row.get("is_placeholder"):
            identity = f"{code} {identity}"
        if row.get("is_placeholder"):
            identity += " — สล็อตวิชาเลือก (รหัสยังไม่กำหนด)"
        return f"{identity}; {credits} หน่วยกิต"[:220] if credits is not None else identity[:220]
    if row.get("total_credits") is not None:
        return f"หลักสูตรกำหนดหน่วยกิตรวม {row['total_credits']} หน่วยกิต"
    if row.get("years") is not None:
        return f"หลักสูตรกำหนดระยะเวลาศึกษา {row['years']} ปี"
    if row.get("credits") is not None and row.get("year") is not None:
        return f"ปี {row['year']} ภาคการศึกษาที่ {row.get('semester')} รวม {row['credits']} หน่วยกิต"
    return None


def _frontend_sources(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert query rows into unique page citations for the front end."""
    sources: list[dict[str, Any]] = []
    seen: set[tuple[int, int | None, str]] = set()
    for row in result.get("rows") or []:
        section = _source_section(row, str(result.get("intent") or ""))
        quote = _source_quote(row)
        pdf_pages = _source_pages(row)
        book_pages = _source_book_pages(row)
        for index, page in enumerate(pdf_pages):
            book_page = book_pages[index] if index < len(book_pages) else None
            key = (page, book_page, section)
            if key in seen:
                continue
            seen.add(key)
            sources.append({
                "page": page,
                "book_page": book_page,
                "section": section,
                "quote": quote,
            })
    return sources


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse("/frontend/")


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict:
    registry.refresh()
    queryable = registry.active_catalogs
    ollama_ready = model.available()
    return {
        "status": "ok" if queryable and ollama_ready else "degraded",
        "database_count": len(registry.databases),
        "queryable_database_count": len(queryable),
        "databases": [item.public_metadata() for item in registry.databases],
        "model": settings.ollama_model,
        "ollama_ready": ollama_ready,
        "lab8b_module": str(Path(lab8b.__file__).resolve()),
    }


@app.get("/api/databases")
def get_databases() -> list[dict]:
    registry.refresh()
    return [
        {**item.public_metadata(), "schema": item.schema_text()}
        for item in registry.databases
    ]


@app.get("/api/program")
def get_program(curriculum: str = Query(default="", max_length=100)) -> dict:
    programs = [
        {
            **(item.program or {}),
            "_source": {
                "database_path": str(item.path),
                "database_name": item.database_name,
                "curriculum_name": item.curriculum_name,
                "source_folder": item.source_folder,
            },
        }
        for item in _select_databases(curriculum)
        if item.program
    ]
    return {"programs": programs}


@app.get("/api/courses")
def get_courses(
    search: str = Query(default="", max_length=100),
    curriculum: str = Query(default="", max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    rows: list[dict] = []
    for item in _select_databases(curriculum):
        database = CurriculumDatabase(lab8b, item.path, settings.max_rows)
        for row in database.courses(search, settings.max_rows, 0):
            row["_source"] = {
                "database_path": str(item.path),
                "database_name": item.database_name,
                "curriculum_name": item.curriculum_name,
                "source_folder": item.source_folder,
            }
            rows.append(row)
    rows.sort(key=lambda row: (str(row["_source"]["curriculum_name"]), str(row.get("code", ""))))
    return rows[offset:offset + limit]


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> dict:
    try:
        return model.ask(registry, request.question)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="ติดต่อ Ollama ไม่ได้") from exc
    except (ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/ask", response_model=FrontendAskResponse)
def frontend_ask(request: FrontendAskRequest):
    """Adapter used by the standalone Week 11 front end."""
    allowed_versions = {"latest", "revised", "old", "all versions"}
    if request.version not in allowed_versions:
        return JSONResponse(status_code=400, content={"error": "ไม่รู้จักฉบับหลักสูตรที่เลือก"})
    started_at = time.perf_counter()
    try:
        result = model.ask(registry, _frontend_question(request))
        answer = result["answer"]
        return {
            "answer": answer,
            "sources": _frontend_sources(result),
            "model": settings.ollama_model,
            "latency_ms": round((time.perf_counter() - started_at) * 1000),
            "confidence": None,
        }
    except requests.RequestException:
        return JSONResponse(status_code=503, content={"error": "ติดต่อ Ollama ไม่ได้"})
    except (FileNotFoundError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
