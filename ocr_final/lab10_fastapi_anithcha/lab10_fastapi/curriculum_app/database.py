"""Curriculum DB adapter that reuses Lab 8B database functions across all curriculum databases."""

import sqlite3
from pathlib import Path
from types import ModuleType
from typing import List, Dict, Any, Optional, Tuple


class CurriculumDatabase:
    def __init__(self, lab8b: Optional[ModuleType] = None, path: Optional[Path] = None, max_rows: int = 100):
        self.lab8b = lab8b
        self.raw_path = Path(path) if path else None
        self.max_rows = max_rows

    def _get_db_paths(self) -> List[Path]:
        """
        สแกนค้นหาไฟล์ curriculum.db ในโฟลเดอร์ work ทั้งหมด แบบรองรับ Path ที่มีเว้นวรรค
        """
        base_dir = Path(__file__).resolve().parent  # .../lab10_fastapi/curriculum_app
        found: List[Path] = []

        # 1. รายชื่อไดเรกทอรีเป้าหมายที่คาดว่าจะเจอโฟลเดอร์ work
        search_dirs = [
            base_dir / "work",
            base_dir,
            base_dir.parent / "work",
            base_dir.parent,
            Path.cwd() / "work",
            Path.cwd(),
        ]

        if self.raw_path:
            rp = self.raw_path
            search_dirs.insert(0, rp if rp.is_absolute() else base_dir / rp)
            search_dirs.insert(0, rp if rp.is_absolute() else Path.cwd() / rp)

        # 2. ค้นหาไฟล์ curriculum.db
        for s_dir in search_dirs:
            try:
                if s_dir.exists():
                    if s_dir.is_file() and s_dir.name == "curriculum.db":
                        resolved = s_dir.resolve()
                        if resolved not in found:
                            found.append(resolved)
                    elif s_dir.is_dir():
                        for f in s_dir.rglob("curriculum.db"):
                            if f.is_file() and ".venv" not in f.parts and "__pycache__" not in f.parts:
                                resolved = f.resolve()
                                if resolved not in found:
                                    found.append(resolved)
            except Exception:
                continue

        return found

    def available(self) -> bool:
        """เช็คว่ามีฐานข้อมูลอย่างน้อย 1 ไฟล์พร้อมใช้งานหรือไม่"""
        paths = self._get_db_paths()
        if not paths:
            return False
        
        # ทดสอบลองเปิดไฟล์ว่าอ่านได้จริงหรือไม่
        for p in paths:
            try:
                conn = self._open_conn(p, readonly=True)
                conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                conn.close()
                return True
            except Exception:
                continue
        return False

    def _require_db(self) -> List[Path]:
        paths = self._get_db_paths()
        if not paths:
            raise FileNotFoundError("ไม่พบไฟล์ curriculum.db ในโฟลเดอร์ใต้ work/ เลยสักไฟล์")
        return paths

    def _open_conn(self, db_path: Path, readonly: bool = True):
        """เปิด Connection โดยส่งเป็น String Path ตรงๆ เพื่อป้องกันปัญหา Space/URI"""
        if self.lab8b and hasattr(self.lab8b, "open_db"):
            try:
                return self.lab8b.open_db(db_path, readonly=readonly)
            except TypeError:
                return self.lab8b.open_db(db_path)
        
        # ใช้ String Path ตรงๆ ไม่ใช้ uri=True เพื่อเลี่ยงปัญหาชื่อโฟลเดอร์มีเว้นวรรค
        conn = sqlite3.connect(str(db_path.resolve()))
        conn.row_factory = sqlite3.Row
        return conn

    def program(self) -> dict | None:
        """ดึงข้อมูลหลักสูตรภาพรวมจาก DB ที่พบ"""
        paths = self._require_db()
        for db_path in paths:
            try:
                conn = self._open_conn(db_path, readonly=True)
                try:
                    row = conn.execute("SELECT * FROM program LIMIT 1").fetchone()
                    if row:
                        res = dict(row)
                        if "program_name" not in res and "name_th" in res:
                            res["program_name"] = res["name_th"]
                        return res
                finally:
                    conn.close()
            except Exception:
                continue
        return None

    def courses(self, search: str = "", limit: int = 50, offset: int = 0) -> list[dict]:
        """ดึงรายวิชาจากทุกฐานข้อมูลในโฟลเดอร์ย่อยใต้ work/ มารวมกัน (คัดวิชาซ้ำออก)"""
        paths = self._require_db()
        limit = min(max(limit, 1), self.max_rows)
        offset = max(offset, 0)

        all_courses = []
        seen_codes = set()

        sql = "SELECT * FROM course"
        params: list[object] = []
        if search.strip():
            sql += " WHERE code LIKE ? OR name_th LIKE ? OR name_en LIKE ?"
            pattern = f"%{search.strip()}%"
            params.extend([pattern, pattern, pattern])
        sql += " ORDER BY code"

        for db_path in paths:
            try:
                conn = self._open_conn(db_path, readonly=True)
                try:
                    rows = conn.execute(sql, params).fetchall()
                    for row in rows:
                        d = dict(row)
                        code = d.get("code") or d.get("course_id")
                        if code and code not in seen_codes:
                            seen_codes.add(code)
                            d["code"] = code
                            d["course_id"] = code
                            all_courses.append(d)
                finally:
                    conn.close()
            except Exception:
                continue

        return all_courses[offset : offset + limit]

    def create_course(self, course: dict) -> dict:
        """เพิ่ม/อัปเดตวิชาลงในทุกฐานข้อมูลที่มีอยู่"""
        paths = self._get_db_paths()
        if not paths:
            root = Path(__file__).resolve().parent
            target = root / "work" / "lab8b_it_coop" / "curriculum.db"
            target.parent.mkdir(parents=True, exist_ok=True)
            paths = [target]

        columns = (
            "code", "name_th", "name_en", "credits", "lecture_h", "lab_h",
            "self_h", "description_th",
        )
        code_val = course.get("code") or course.get("course_id") or "99999999"
        course["code"] = code_val
        course["course_id"] = code_val

        for db_path in paths:
            try:
                conn = self._open_conn(db_path, readonly=False)
                try:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS course (
                            code TEXT PRIMARY KEY,
                            name_th TEXT,
                            name_en TEXT,
                            credits INTEGER,
                            lecture_h INTEGER DEFAULT 0,
                            lab_h INTEGER DEFAULT 0,
                            self_h INTEGER DEFAULT 0,
                            description_th TEXT
                        )
                    """)
                    conn.execute(
                        "INSERT OR REPLACE INTO course VALUES (?,?,?,?,?,?,?,?)",
                        tuple(course.get(col) for col in columns),
                    )
                    conn.commit()
                finally:
                    conn.close()
            except Exception:
                continue

        return course

    def query_from_model(self, sql: str) -> tuple[str, list[dict]]:
        """รันคำสั่ง SQL บนทุกฐานข้อมูล แล้วนำข้อมูลมารวมกัน"""
        paths = self._require_db()

        if self.lab8b and hasattr(self.lab8b, "guard_sql"):
            safe_sql = self.lab8b.guard_sql(sql)
        else:
            safe_sql = sql

        all_rows = []
        seen_tuples = set()

        for db_path in paths:
            try:
                conn = self._open_conn(db_path, readonly=True)
                try:
                    rows = [dict(r) for r in conn.execute(safe_sql).fetchall()]
                    for r in rows:
                        r_tuple = tuple(sorted((k, str(v)) for k, v in r.items()))
                        if r_tuple not in seen_tuples:
                            seen_tuples.add(r_tuple)
                            all_rows.append(r)
                finally:
                    conn.close()
            except Exception:
                continue

        return safe_sql, all_rows[: self.max_rows]


SQL_SCHEMA_CONTEXT = """
program(program_id, name_th, name_en, degree, total_credits, years)
course(code, name_th, name_en, credits, lecture_h, lab_h, self_h, description_th)
plan_item(id, program_id, year, semester, code, credits, alt_group, note)
prerequisite(code, requires, kind)
v_plan(id, year, semester, code, name_th, name_en, credits, alt_group, note)
v_semester_credits(year, semester, credits, n_courses)
""".strip()