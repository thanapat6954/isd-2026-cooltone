"""Application 1: curriculum database question answering."""

import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
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
from .schemas import AskRequest, AskResponse, HealthResponse  # noqa: E402


STATIC_DIR = Path(__file__).resolve().parent / "static"
app = FastAPI(
    title=f"{settings.app_name} — Curriculum",
    description="Qwen text-to-SQL + SQLite curriculum application",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
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


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


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
