"""Capture a read-only baseline of the live curriculum SQLite databases.

This audit intentionally does not import product code.  It inspects SQLite files
as deployed so schema gaps and user-visible placeholder rows cannot be hidden by
conversion-time reports.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_PLAN_ITEM_COLUMNS = {
    "is_placeholder",
    "raw_code",
    "code_pattern",
    "elective_type",
    "alternative_index",
    "printed_page_number",
}


def _rows(connection: sqlite3.Connection, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    connection.row_factory = sqlite3.Row
    return [dict(row) for row in connection.execute(sql, parameters).fetchall()]


def inspect_database(path: Path, app_root: Path) -> dict[str, Any]:
    profile = path.parent.name.removeprefix("lab8b_").replace("_", "-")
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            )
        }
        if "plan_item" not in tables:
            return {
                "profile": profile,
                "database": str(path.relative_to(app_root)).replace("\\", "/"),
                "error": "plan_item table is absent",
            }

        plan_columns = [row[1] for row in connection.execute("PRAGMA table_info(plan_item)")]
        view_columns = (
            [row[1] for row in connection.execute("PRAGMA table_info(v_plan)")]
            if "v_plan" in tables
            else []
        )
        programs = _rows(connection, "SELECT * FROM program ORDER BY program_id") if "program" in tables else []

        term_source = "v_plan" if "v_plan" in tables else "plan_item"
        term_rows = _rows(
            connection,
            f"""
            SELECT year, semester,
                   COUNT(*) AS stored_rows,
                   SUM(credits) AS raw_credit_sum,
                   SUM(CASE WHEN alt_group IS NULL THEN credits ELSE 0 END)
                     + COALESCE((
                         SELECT SUM(group_credit) FROM (
                             SELECT MIN(p2.credits) AS group_credit
                             FROM plan_item p2
                             WHERE p2.year = p.year AND p2.semester = p.semester
                               AND p2.alt_group IS NOT NULL
                             GROUP BY p2.alt_group
                         )
                       ), 0) AS counted_credit_sum,
                   SUM(CASE WHEN code LIKE 'ELEC-%' THEN 1 ELSE 0 END) AS synthetic_rows,
                   SUM(CASE WHEN code LIKE 'ELEC-%' AND (name_th IS NULL OR TRIM(name_th) = '')
                            THEN 1 ELSE 0 END) AS synthetic_rows_missing_thai_name,
                   GROUP_CONCAT(DISTINCT page_number) AS pdf_pages
            FROM {term_source} p
            GROUP BY year, semester
            ORDER BY year, semester
            """,
        )
        placeholders = _rows(
            connection,
            f"""
            SELECT year, semester, code, name_th, name_en, credits, alt_group,
                   category, ctype, note, source_file, page_number
            FROM {term_source}
            WHERE code LIKE 'ELEC-%'
            ORDER BY year, semester, code
            """,
        )
        alternatives = _rows(
            connection,
            f"""
            SELECT year, semester, alt_group, COUNT(*) AS rows_in_group,
                   GROUP_CONCAT(code, ' | ') AS codes,
                   MIN(credits) AS counted_credits,
                   GROUP_CONCAT(DISTINCT page_number) AS pdf_pages
            FROM {term_source}
            WHERE alt_group IS NOT NULL
            GROUP BY year, semester, alt_group
            ORDER BY year, semester, alt_group
            """,
        )
        target_term = _rows(
            connection,
            f"""
            SELECT year, semester, code, name_th, name_en, credits, alt_group,
                   category, ctype, note, source_file, page_number
            FROM {term_source}
            WHERE year = 4 AND semester = 2
            ORDER BY code
            """,
        )

    return {
        "profile": profile,
        "database": str(path.relative_to(app_root)).replace("\\", "/"),
        "size_bytes": path.stat().st_size,
        "program_rows": programs,
        "plan_item_columns": plan_columns,
        "v_plan_columns": view_columns,
        "required_columns_missing": sorted(REQUIRED_PLAN_ITEM_COLUMNS - set(plan_columns)),
        "terms": term_rows,
        "placeholder_summary": {
            "rows": len(placeholders),
            "missing_thai_name": sum(not str(row.get("name_th") or "").strip() for row in placeholders),
            "missing_english_name": sum(not str(row.get("name_en") or "").strip() for row in placeholders),
        },
        "placeholder_rows": placeholders,
        "alternative_groups": alternatives,
        "year_4_semester_2": target_term,
    }


def build_baseline(app_root: Path) -> dict[str, Any]:
    databases = sorted((app_root / "work").glob("lab8b_*/curriculum.db"))
    inspected = [inspect_database(path, app_root) for path in databases]
    return {
        "kind": "read_only_live_database_baseline",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "application_root": str(app_root),
        "database_count": len(inspected),
        "profiles": inspected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = build_baseline(args.app_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"inspected {result['database_count']} databases -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
