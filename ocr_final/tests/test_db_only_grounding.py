"""Fail-closed claim references; no model-supplied fact values."""
import unittest
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL, render_claims, _parse_json_object, CLAIM_SCHEMA, validate_unknown_projection, normalize_redundant_program_filter
from lab10_fastapi.curriculum_app.database import SqlValidationError
from lab10_fastapi.curriculum_app.database import inspect_database
from pathlib import Path
import tempfile
import sqlite3
from lab10_fastapi.curriculum_app.query_planner import QueryPlan, detect_intent


class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'code':'00000001','name_th':'ชื่อใน DB','credits':3,
                    '_source':{'curriculum_name':'IT-2560-coop'}}]

    def test_actual_values_only(self):
        answer=render_claims(self.rows,[{'row_index':0,'fields':['code','name_th','credits']}])
        self.assertIn('IT-2560-coop',answer)
        self.assertIn('ชื่อใน DB',answer)
        self.assertIn('หน่วยกิต: 3',answer)

    def test_free_prose_never_passes_guard(self):
        for text in ['ลงทะเบียนได้แน่นอน','999 หน่วยกิต','ไม่มีวิชาบังคับก่อน','IT-2565-coop: fabricated']:
            self.assertNotEqual(QwenTextToSQL._ground_answer(QueryPlan('unknown'),self.rows,text),text)

    def test_adversarial_claims(self):
        bad=[None,[], 'ข้อความ', [{'row_index':-1,'fields':['credits']}],
             [{'row_index':True,'fields':['credits']}], [{'row_index':9,'fields':['credits']}],
             [{'row_index':0,'fields':['permission']}], [{'row_index':0,'fields':['credits'],'value':99}],
             [{'row_index':0,'fields':['_source']}], [{'row_index':0,'fields':['credits + 99']}]]
        for claim in bad:
            with self.subTest(claim=claim): self.assertIsNone(render_claims(self.rows,claim))

    def test_empty_evidence(self):
        self.assertIsNone(render_claims([], [{'row_index':0,'fields':['credits']}]))

    def test_missing_field(self):
        self.assertIsNone(render_claims(self.rows,[{'row_index':0,'fields':['requires']}]))

    def test_claim_array_parser_preserved(self):
        value=_parse_json_object('{"claims":[{"row_index":0,"fields":["credits"]}]}',CLAIM_SCHEMA)
        self.assertEqual(value['claims'][0]['fields'],['credits'])

    def test_thai_semester_synonyms(self):
        for label in ['ภาคเรียน', 'ภาคการศึกษา', 'เทอม']:
            plan = detect_intent(f'ปี 3 {label}ที่ 2 มีวิชาอะไรบ้าง')
            self.assertEqual((plan.intent, plan.year, plan.semester), ('course_list', 3, 2))

    def test_course_code_listing_is_deterministic(self):
        for phrase in ['แสดงรหัสวิชา', 'โปรดแสดงรหัสทั้งหมด']:
            plan = detect_intent(f'{phrase} ในแผนปี 3 ภาคเรียน 2')
            self.assertEqual((plan.intent, plan.year, plan.semester), ('course_list', 3, 2))

    def test_sql_cannot_invent_or_relabel_facts(self):
        for sql in ["SELECT '999' AS credits FROM course", 'SELECT credits+99 FROM course',
                    'SELECT SUM(credits) FROM course', 'SELECT COUNT(*) FROM course',
                    'SELECT credits AS name_th FROM course', 'SELECT credits name_th FROM course',
                    'SELECT NULL AS requires FROM course', 'SELECT CASE WHEN credits=3 THEN 0 END FROM course',
                    'SELECT credits FROM course UNION SELECT 999', 'SELECT * FROM study_correction']:
            with self.subTest(sql=sql), self.assertRaises(SqlValidationError):
                validate_unknown_projection(sql)

    def test_sql_preserves_stored_column_semantics(self):
        for sql in ['SELECT name_th, years, total_credits FROM program',
                    'SELECT c.code, c.credits FROM course c',
                    'SELECT course_code AS code, course_name_th AS name_th FROM courses',
                    'SELECT credits AS credits FROM course', 'SELECT p.* FROM program p']:
            validate_unknown_projection(sql)

    def test_program_filter_normalization_requires_exact_single_row(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'curriculum.db'
            connection = sqlite3.connect(path)
            try:
                connection.executescript("CREATE TABLE program(program_id TEXT, is_latest INTEGER); INSERT INTO program VALUES('IT-2560-no-coop',0);")
                connection.commit()
                database = inspect_database(path, Path(folder))
                valid = "SELECT program_id FROM program WHERE program_id='IT-2560-no-coop' LIMIT 1"
                self.assertNotIn('WHERE', normalize_redundant_program_filter(database, valid))
                like = "SELECT program_id FROM program WHERE program_id LIKE 'IT%' AND (is_latest = 0 OR is_latest IS NULL)"
                self.assertNotIn('WHERE', normalize_redundant_program_filter(database, like))
                for sql in [valid.replace('2560', '2565'), valid.replace(' LIMIT 1', " OR program_id='other'"),
                            "SELECT program_id FROM program WHERE program_id='IT-2560-no-coop' AND 1=1"]:
                    self.assertEqual(normalize_redundant_program_filter(database, sql), sql)
                connection.execute("INSERT INTO program VALUES('second',1)")
                connection.commit()
                self.assertEqual(normalize_redundant_program_filter(database, valid), valid)
            finally:
                connection.close()


if __name__=='__main__': unittest.main()
