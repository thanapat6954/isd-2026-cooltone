"""Selected-plan classifications must constrain catalog relationships."""
from contextlib import closing
import sqlite3
import tempfile
from pathlib import Path
import unittest

from lab10_fastapi.curriculum_app.database import inspect_database
from lab10_fastapi.curriculum_app.query_planner import detect_intent, deterministic_sql
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL


class CatalogScopeTests(unittest.TestCase):
    def test_prerequisite_word_is_not_required_course_scope(self):
        plan = detect_intent('ช่วยยืนยันว่าทุกวิชาเลือกไม่มีวิชาบังคับก่อน')
        self.assertEqual(plan.intent, 'prerequisite_catalog')
        self.assertTrue(plan.elective_only)
        self.assertFalse(plan.required_only)

    def test_selected_classification_filters_edges_without_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'curriculum.db'
            with closing(sqlite3.connect(path)) as db:
                db.executescript('''
                    CREATE TABLE program(program_id TEXT, curriculum_version INT, plan TEXT);
                    INSERT INTO program VALUES('fixture-coop',2560,'coop');
                    CREATE TABLE course(code TEXT, name_th TEXT);
                    CREATE TABLE prerequisite(code TEXT, requires TEXT, kind TEXT, source_file TEXT,page_number INT);
                    CREATE TABLE plan_item(code TEXT,ctype TEXT);
                    INSERT INTO course VALUES('00000001','required'),('00000002','elective'),('00000003','unknown');
                    INSERT INTO plan_item VALUES('00000001','บังคับ'),('00000002','เลือก'),('00000002','เลือก'),('00000003',NULL);
                    INSERT INTO prerequisite VALUES
                      ('00000001','00000009','pre','source.pdf',1),
                      ('00000002','00000008','pre','source.pdf',2),
                      ('00000003','00000007','pre','source.pdf',3);
                ''')
                db.commit()
                plan = detect_intent('ทุกวิชาเลือกมีวิชาบังคับก่อนอะไรบ้าง')
                info = inspect_database(path, Path(directory))
                sql = deterministic_sql(plan, info)
                rows = db.execute(sql).fetchall()
                self.assertEqual([row[0] for row in rows], ['00000002'])
                QwenTextToSQL._validate_plan_filters('ทุกวิชาเลือกมีวิชาบังคับก่อนอะไรบ้าง', plan, info, sql)

    def test_renderer_rejects_blanket_none_and_names_selected_identity(self):
        plan = detect_intent('ทุกวิชาเลือกไม่มีวิชาบังคับก่อนใช่ไหม')
        rows = [{'code':'00000002','name_th':'fixture', 'requires':'00000008',
                 '_source':{'curriculum_name':'fixture-2560-no-coop'}}]
        answer = QwenTextToSQL._ground_answer(plan, rows, 'unsupported model answer')
        self.assertIn('fixture-2560-no-coop', answer)
        self.assertIn('00000008', answer)
        self.assertIn('ไม่ใช่การตรวจครบทุกวิชา', answer)
        self.assertIn('ข้อมูลที่ขาดไม่หมายถึงไม่มี', answer)
        self.assertNotIn('unsupported model answer', answer)


if __name__ == '__main__':
    unittest.main()
