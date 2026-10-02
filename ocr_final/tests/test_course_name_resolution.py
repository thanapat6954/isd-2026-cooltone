"""Name-only matching must clarify ambiguity without leaking another version."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from lab10_fastapi.curriculum_app.config import settings
from lab10_fastapi.curriculum_app.database import DatabaseRegistry
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
from lab10_fastapi.curriculum_app.query_planner import detect_intent, normalize_course_name


class NoModel:
    def ollama_generate(self,*args,**kwargs):
        raise AssertionError('Name retrieval must not manufacture model SQL')


class CourseNameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for version in (2560,2565):
            p=self.root/f'work/lab8b_it_{version}_coop/curriculum.db'
            p.parent.mkdir(parents=True)
            with closing(sqlite3.connect(p)) as db:
                db.executescript('''CREATE TABLE program(program_id TEXT,name_th TEXT,total_credits INTEGER,years INTEGER,curriculum_version INTEGER,is_latest INTEGER,plan TEXT);
                CREATE TABLE course(code TEXT PRIMARY KEY,name_th TEXT,name_en TEXT,credits INTEGER,lecture_h INTEGER,lab_h INTEGER,self_h INTEGER,source_file TEXT,page_number INTEGER);
                CREATE TABLE plan_item(code TEXT,source_file TEXT,page_number INTEGER,printed_page_number INTEGER);
                CREATE TABLE prerequisite(code TEXT,requires TEXT,kind TEXT,source_file TEXT,page_number INTEGER);''')
                db.execute('INSERT INTO program VALUES(?,?,?,?,?,?,?)',('IT-coop','IT',130,4,version,int(version==2565),'coop'))
                for code,name in ((f'{version}0001','การสร้างโปรแกรมคอมพิวเตอร์'),(f'{version}0002','การโปรแกรมอุปกรณ์เคลื่อนที่')):
                    db.execute('INSERT INTO course VALUES(?,?,?,?,?,?,?,?,?)',(code,name,None,3,2,2,5,'IT-60.pdf' if version==2560 else 'IT.pdf',35))
                    db.execute('INSERT INTO plan_item VALUES(?,?,?,?)',(code,'IT-60.pdf' if version==2560 else 'IT.pdf',35,30))
                db.commit()
        self.registry=DatabaseRegistry(self.root)
        self.assistant=QwenTextToSQL(replace(settings,debug=True),NoModel())

    def ask(self,name):
        return self.assistant.ask(self.registry,f'หลักสูตร IT 2560 สหกิจ: วิชา{name}มีกี่หน่วยกิต')

    def test_common_nominal_variant_lists_candidates_not_an_answer(self):
        result=self.ask('การเขียนโปรแกรม')
        self.assertEqual({r['code'] for r in result['rows']},{'25600001','25600002'})
        self.assertIn('โปรดระบุรหัสวิชา',result['answer'])
        self.assertNotIn('25650001',result['answer'])

    def test_exact_match_preferred_and_book_page_has_same_pdf_provenance(self):
        result=self.ask('การเขียนโปรแกรมคอมพิวเตอร์')
        self.assertEqual(len(result['rows']),1)
        self.assertEqual(result['rows'][0]['printed_page_number'],30)
        self.assertIn('3 หน่วยกิต',result['answer'])

    def test_nonexistent_course_not_replaced_with_close_candidate(self):
        result=self.ask('การแพทย์ฉุกเฉิน')
        self.assertFalse(result['rows'])
        self.assertIn('IT-2560-coop',result['answer'])
        self.assertIn('จึงยังสรุปไม่ได้',result['answer'])

    def test_wildcard_is_not_search_operator(self):
        self.assertFalse(self.ask('%')['rows'])

    def test_name_prerequisite_detected_without_code(self):
        self.assertEqual(detect_intent('วิชาการโปรแกรมอุปกรณ์เคลื่อนที่มีวิชาบังคับก่อนอะไร').intent,'course_search')
        self.assertEqual(normalize_course_name('การสร้าง โปรแกรม'),'โปรแกรม')

    def test_unique_name_can_resolve_prerequisite_without_relaxing_filter_guard(self):
        from lab10_fastapi.curriculum_app.database import SqlValidationError
        from lab10_fastapi.curriculum_app.query_planner import QueryPlan
        p=self.root/'work/lab8b_it_2560_coop/curriculum.db'
        with closing(sqlite3.connect(p)) as db:
            db.execute('INSERT INTO prerequisite VALUES(?,?,?,?,?)',('25600002','25600001','pre','IT-60.pdf',35))
            db.commit()
        self.registry.refresh()
        result=self.assistant.ask(self.registry,'หลักสูตร IT 2560 สหกิจ: วิชาการโปรแกรมอุปกรณ์เคลื่อนที่มีวิชาบังคับก่อนอะไร')
        self.assertEqual(result['rows'][0]['requires'],'25600001')
        info=self.registry.select('หลักสูตร IT 2560 สหกิจ')[0]
        plan=QueryPlan('prerequisite',course_code='25600002')
        with self.assertRaises(SqlValidationError):
            self.assistant._validate_plan_filters('วิชาการแพทย์มีวิชาบังคับก่อนอะไร',plan,info,"SELECT code FROM course WHERE code='25600002'")
        with self.assertRaises(SqlValidationError):
            self.assistant._validate_plan_filters('วิชาการแพทย์มีวิชาบังคับก่อนอะไร',plan,info,"SELECT code FROM course WHERE code='25600002'",resolved_course_code='25600001')

    def test_incidental_course_name_does_not_select_another_program(self):
        self.assertEqual(len(self.registry.select('หลักสูตร IT 2560 สหกิจ: วิชาพื้นฐานวิทยาการข้อมูลมีกี่หน่วยกิต')),1)

    def test_review_ingest_updates_actual_plan_name_columns(self):
        from scripts.ingest_name_reviews import changes
        p=self.root/'work/lab8b_it_2560_coop/curriculum.db'
        with closing(sqlite3.connect(p)) as db:
            db.row_factory=sqlite3.Row
            db.execute('ALTER TABLE plan_item ADD COLUMN name_th TEXT')
            db.execute('ALTER TABLE plan_item ADD COLUMN name_en TEXT')
            rows=changes(db,[{'source_file':'IT-60.pdf','pdf_page':35,'printed_page':30,
                             'rows':[{'code':'25600001','name_th':'การสร้างโปรแกรมคอมพิวเตอร์','name_en':None}]}])
            self.assertTrue(rows)
            self.assertIn('plan_labels_before',rows[0])
