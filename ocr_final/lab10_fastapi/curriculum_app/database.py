"""SQLite discovery, schema inspection, selection, and safe query execution."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|"
    r"pragma|vacuum|reindex|truncate|load_extension)\b",
    re.IGNORECASE,
)
COMMENT_SQL = re.compile(r"(--|/\*)")


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    primary_key: bool


@dataclass(frozen=True)
class ForeignKeyInfo:
    column: str
    target_table: str
    target_column: str


@dataclass(frozen=True)
class ObjectInfo:
    name: str
    kind: str
    columns: tuple[ColumnInfo, ...]
    foreign_keys: tuple[ForeignKeyInfo, ...] = ()


@dataclass(frozen=True)
class DatabaseInfo:
    path: Path
    relative_path: str
    database_name: str
    source_folder: str
    curriculum_name: str
    program_id: str | None
    program: dict[str, Any] | None
    objects: dict[str, ObjectInfo]
    archived: bool = False
    duplicate_of: str | None = None
    inspection_error: str | None = None

    @property
    def schema_family(self) -> str:
        if "program" in self.objects and "plan_item" in self.objects:
            return "lab8b"
        if "courses" in self.objects:
            return "legacy-course-catalog"
        return "unknown"

    @property
    def queryable(self) -> bool:
        return not self.archived and not self.duplicate_of and not self.inspection_error

    def has(self, object_name: str, *columns: str) -> bool:
        obj = self.objects.get(object_name)
        if not obj:
            return False
        actual = {column.name.casefold() for column in obj.columns}
        return all(column.casefold() in actual for column in columns)

    def schema_text(self) -> str:
        lines: list[str] = []
        for obj in sorted(self.objects.values(), key=lambda item: (item.kind, item.name)):
            columns = ", ".join(
                f"{column.name} {column.data_type or 'ANY'}"
                f"{' PRIMARY KEY' if column.primary_key else ''}"
                for column in obj.columns
            )
            lines.append(f"{obj.kind.upper()} {obj.name}({columns})")
            for fk in obj.foreign_keys:
                lines.append(
                    f"  FOREIGN KEY {fk.column} -> {fk.target_table}.{fk.target_column}"
                )
        return "\n".join(lines)

    def public_metadata(self) -> dict[str, Any]:
        return {
            "database_path": str(self.path),
            "database_name": self.database_name,
            "curriculum_name": self.curriculum_name,
            "program_id": self.program_id,
            "source_folder": self.source_folder,
            "schema_family": self.schema_family,
            "archived": self.archived,
            "duplicate_of": self.duplicate_of,
            "queryable": self.queryable,
            "inspection_error": self.inspection_error,
        }


def open_readonly(path: Path) -> sqlite3.Connection:
    """Open one SQLite file in read-only/query-only mode."""
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def inspect_database(path: Path, root: Path) -> DatabaseInfo:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    archived = any(part.casefold().startswith("_archive") for part in path.parts)
    try:
        connection = open_readonly(path)
        rows = connection.execute(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' "
            "ORDER BY type, name"
        ).fetchall()
        objects: dict[str, ObjectInfo] = {}
        for row in rows:
            name = str(row["name"])
            quoted = _quote_identifier(name)
            columns = tuple(
                ColumnInfo(str(column["name"]), str(column["type"] or ""), bool(column["pk"]))
                for column in connection.execute(f"PRAGMA table_info({quoted})")
            )
            foreign_keys: tuple[ForeignKeyInfo, ...] = ()
            if row["type"] == "table":
                foreign_keys = tuple(
                    ForeignKeyInfo(
                        str(item["from"]), str(item["table"]), str(item["to"])
                    )
                    for item in connection.execute(f"PRAGMA foreign_key_list({quoted})")
                )
            objects[name] = ObjectInfo(name, str(row["type"]), columns, foreign_keys)

        program: dict[str, Any] | None = None
        if "program" in objects:
            row = connection.execute("SELECT * FROM program LIMIT 1").fetchone()
            program = dict(row) if row else None
        connection.close()
        program_id = str(program.get("program_id")) if program and program.get("program_id") else None
        curriculum_name = program_id or ("legacy-course-catalog" if "courses" in objects else path.parent.name)
        return DatabaseInfo(
            path=path.resolve(),
            relative_path=relative,
            database_name=path.parent.name if path.parent != root else path.stem,
            source_folder=path.parent.resolve().relative_to(root.resolve()).as_posix() or ".",
            curriculum_name=curriculum_name,
            program_id=program_id,
            program=program,
            objects=objects,
            archived=archived,
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        return DatabaseInfo(
            path=path.resolve(),
            relative_path=relative,
            database_name=path.parent.name if path.parent != root else path.stem,
            source_folder=path.parent.resolve().relative_to(root.resolve()).as_posix() or ".",
            curriculum_name=path.parent.name,
            program_id=None,
            program=None,
            objects={},
            archived=archived,
            inspection_error=f"{type(exc).__name__}: {exc}",
        )


class DatabaseRegistry:
    """Discover all curriculum databases and resolve questions to active curricula."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.databases: list[DatabaseInfo] = []
        self.refresh()

    def refresh(self) -> list[DatabaseInfo]:
        ignored = {".git", ".venv", "venv", "__pycache__", "node_modules"}
        paths = [
            path for path in self.root.rglob("curriculum.db")
            if not any(part.casefold() in ignored for part in path.relative_to(self.root).parts)
        ]
        inspected = [inspect_database(path, self.root) for path in sorted(paths)]

        preferred: dict[str, DatabaseInfo] = {}
        for item in inspected:
            if item.archived or not item.program_id or item.inspection_error:
                continue
            key = item.program_id.casefold()
            current = preferred.get(key)
            score = ("/work/lab8b_" in f"/{item.relative_path.casefold()}", -len(item.relative_path))
            current_score = (
                "/work/lab8b_" in f"/{current.relative_path.casefold()}",
                -len(current.relative_path),
            ) if current else (False, -10_000)
            if current is None or score > current_score:
                preferred[key] = item

        final: list[DatabaseInfo] = []
        for item in inspected:
            winner = preferred.get(item.program_id.casefold()) if item.program_id else None
            if winner and winner.path != item.path and not item.archived:
                item = DatabaseInfo(**{**item.__dict__, "duplicate_of": winner.relative_path})
            final.append(item)
        self.databases = final
        return final

    @property
    def active_programs(self) -> list[DatabaseInfo]:
        return [
            item for item in self.databases
            if item.queryable and item.schema_family == "lab8b" and item.program_id
        ]

    @property
    def active_catalogs(self) -> list[DatabaseInfo]:
        return [item for item in self.databases if item.queryable]

    def find_path(self, path: Path) -> DatabaseInfo | None:
        resolved = path.resolve()
        return next((item for item in self.databases if item.path == resolved), None)

    def select(self, question: str, *, include_legacy: bool = False) -> list[DatabaseInfo]:
        text = question.casefold()
        compact = re.sub(r"[_‐‑‒–—-]+", " ", text)

        programs: set[str] = set()
        if re.search(r"(?<![a-z])dsba(?![a-z])", compact) or "วิทยาการข้อมูล" in text:
            programs.add("dsba")
        if (
            re.search(r"(?<![a-z])it(?![a-z])", compact)
            or "ไอที" in text
            or "เทคโนโลยีสารสนเทศ" in text
            or "information technology" in compact
        ):
            programs.add("it")
        if (
            re.search(r"(?<![a-z])ai(?![a-z])", compact)
            or "ปัญญาประดิษฐ์" in text
            or "artificial intelligence" in compact
        ):
            programs.add("ai")

        no_coop = any(token in compact for token in (
            "no coop", "non coop", "without coop", "ไม่สหกิจ", "ไม่มีสหกิจ", "แผนปกติ",
        ))
        coop = not no_coop and any(token in compact for token in (
            "coop", "cooperative", "สหกิจ",
        ))

        candidates = self.active_programs
        if programs:
            candidates = [
                item for item in candidates
                if any((item.program_id or "").casefold().startswith(program) for program in programs)
            ]
        if no_coop:
            candidates = [item for item in candidates if "no-coop" in (item.program_id or "").casefold()]
        elif coop:
            candidates = [
                item for item in candidates
                if "coop" in (item.program_id or "").casefold()
                and "no-coop" not in (item.program_id or "").casefold()
            ]

        if include_legacy and not programs:
            legacy = [
                item for item in self.active_catalogs
                if item.schema_family == "legacy-course-catalog"
            ]
            candidates = [*candidates, *legacy]
        elif not candidates and include_legacy:
            candidates = [
                item for item in self.active_catalogs
                if item.schema_family == "legacy-course-catalog"
            ]
        return sorted(candidates, key=lambda item: (item.program_id or item.curriculum_name).casefold())


class SqlValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidationResult:
    sql: str
    referenced_columns: tuple[str, ...] = ()


def _readonly_authorizer(action: int, arg1: str | None, arg2: str | None,
                         _db_name: str | None, _trigger: str | None) -> int:
    allowed = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_RECURSIVE,
    }
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY


def normalize_sql(sql: str, max_rows: int) -> str:
    statement = sql.strip().rstrip(";").strip()
    if not statement:
        raise SqlValidationError("SQL is empty")
    if ";" in statement:
        raise SqlValidationError("Only one SQL statement is allowed")
    if COMMENT_SQL.search(statement):
        raise SqlValidationError("SQL comments are not allowed")
    if not re.match(r"^(select|with)\b", statement, re.IGNORECASE):
        raise SqlValidationError("Only SELECT or WITH queries are allowed")
    if FORBIDDEN_SQL.search(statement):
        raise SqlValidationError("The SQL contains a forbidden operation")
    limit_match = re.search(r"\blimit\s+(\d+)\b", statement, re.IGNORECASE)
    if limit_match and int(limit_match.group(1)) > max_rows:
        statement = (
            statement[:limit_match.start(1)]
            + str(max_rows)
            + statement[limit_match.end(1):]
        )
    elif not limit_match:
        statement += f" LIMIT {max_rows}"
    return statement


def validate_sql(database: DatabaseInfo, sql: str, max_rows: int = 100) -> ValidationResult:
    statement = normalize_sql(sql, max_rows)
    references: list[str] = []

    def authorizer(action: int, arg1: str | None, arg2: str | None,
                   db_name: str | None, trigger: str | None) -> int:
        if action == sqlite3.SQLITE_READ and arg1:
            references.append(f"{arg1}.{arg2}" if arg2 else arg1)
        return _readonly_authorizer(action, arg1, arg2, db_name, trigger)

    connection: sqlite3.Connection | None = None
    try:
        connection = open_readonly(database.path)
        connection.set_authorizer(authorizer)
        connection.execute("EXPLAIN QUERY PLAN " + statement).fetchall()
    except sqlite3.Error as exc:
        raise SqlValidationError(str(exc)) from exc
    finally:
        if connection is not None:
            connection.close()
    return ValidationResult(statement, tuple(sorted(set(references))))


def execute_readonly(database: DatabaseInfo, sql: str, max_rows: int = 100) -> tuple[ValidationResult, list[dict[str, Any]]]:
    validation = validate_sql(database, sql, max_rows)
    connection: sqlite3.Connection | None = None
    try:
        connection = open_readonly(database.path)
        connection.set_authorizer(_readonly_authorizer)
        steps = 0

        def progress() -> int:
            nonlocal steps
            steps += 1
            return 1 if steps > 20_000 else 0

        connection.set_progress_handler(progress, 1_000)
        rows = [dict(row) for row in connection.execute(validation.sql).fetchmany(max_rows)]
        return validation, rows
    except sqlite3.Error as exc:
        raise SqlValidationError(str(exc)) from exc
    finally:
        if connection is not None:
            connection.close()


class CurriculumDatabase:
    """Backward-compatible adapter for the CRUD endpoints using one selected database."""

    def __init__(self, lab8b: Any, path: Path, max_rows: int = 100):
        del lab8b
        root = path.resolve().parents[2] if len(path.resolve().parents) > 2 else path.parent
        self.info = inspect_database(path.resolve(), root)
        self.path = path.resolve()
        self.max_rows = max_rows

    def _require_db(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"ไม่พบฐานข้อมูล: {self.path}")

    def program(self) -> dict[str, Any] | None:
        self._require_db()
        connection = open_readonly(self.path)
        try:
            row = connection.execute("SELECT * FROM program LIMIT 1").fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def courses(self, search: str = "", limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        self._require_db()
        limit = min(max(limit, 1), self.max_rows)
        offset = max(offset, 0)
        sql = "SELECT * FROM course"
        params: list[Any] = []
        if search.strip():
            sql += " WHERE code LIKE ? OR name_th LIKE ? OR name_en LIKE ?"
            pattern = f"%{search.strip()}%"
            params.extend([pattern, pattern, pattern])
        sql += " ORDER BY code LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        connection = open_readonly(self.path)
        try:
            return [dict(row) for row in connection.execute(sql, params).fetchall()]
        finally:
            connection.close()

def attach_source_metadata(rows: Iterable[dict[str, Any]], database: DatabaseInfo) -> list[dict[str, Any]]:
    metadata = {
        "database_path": str(database.path),
        "database_name": database.database_name,
        "curriculum_name": database.curriculum_name,
        "source_folder": database.source_folder,
    }
    return [{**row, "_source": metadata} for row in rows]
