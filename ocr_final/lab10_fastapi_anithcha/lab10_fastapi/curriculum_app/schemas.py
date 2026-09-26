"""Curriculum App HTTP request and response schemas."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class AskResponse(BaseModel):
    question: str
    sql: str
    rows: list[dict[str, Any]]
    answer: str


class CourseCreate(BaseModel):
    code: str = Field(pattern=r"^\d{8}$")
    name_th: str = Field(min_length=1, max_length=300)
    name_en: Optional[str] = Field(default=None, max_length=300)
    credits: int = Field(ge=0, le=12)
    lecture_h: Optional[int] = Field(default=0, ge=0, le=60)
    lab_h: Optional[int] = Field(default=0, ge=0, le=60)
    self_h: Optional[int] = Field(default=0, ge=0, le=60)
    description_th: Optional[str] = None


class CourseResponse(CourseCreate):
    class Config:
        from_attributes = True


class ProgramResponse(BaseModel):
    program_id: Optional[str] = None
    name_th: Optional[str] = None
    name_en: Optional[str] = None
    degree: Optional[str] = None
    total_credits: Optional[int] = None
    years: Optional[int] = None

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    database: str
    database_ready: bool
    model: str
    ollama_ready: bool
    lab8b_module: str