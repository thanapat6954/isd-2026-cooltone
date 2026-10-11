import sqlite3
from types import SimpleNamespace
import unittest
from lab10_fastapi.curriculum_app.query_planner import _course_fields


class CoursePagePairsTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript('''CREATE TABLE course(code,name_th,name_en,credits,lecture_h,lab_h,self_h,source_file,page_number);
            INSERT INTO course VALUES ('00000001','synthetic','SYNTHETIC',3,3,0,6,'synthetic.pdf',10);
            CREATE TABLE plan_item(source_file,page_number,printed_page_number);
            CREATE TABLE course_prerequisite_evidence(source_file,page_number,printed_page_number);
        ''')
        self.info = SimpleNamespace(has=lambda table,*columns: table in ('plan_item','course_prerequisite_evidence'))

    def tearDown(self):
        self.db.close()

    def printed(self):
        return self.db.execute('SELECT '+_course_fields(self.info)+' FROM course').fetchone()[-1]

    def test_description_folio_from_exact_stored_pair(self):
        self.db.execute("INSERT INTO course_prerequisite_evidence VALUES ('synthetic.pdf',10,5)")
        self.assertEqual(self.printed(), 5)

    def test_other_file_or_page_cannot_supply_folio(self):
        self.db.executemany('INSERT INTO course_prerequisite_evidence VALUES (?,?,?)',
            [('other.pdf',10,5),('synthetic.pdf',11,6)])
        self.assertIsNone(self.printed())

    def test_conflicting_pairs_are_unknown(self):
        self.db.execute("INSERT INTO course_prerequisite_evidence VALUES ('synthetic.pdf',10,5)")
        self.db.execute("INSERT INTO plan_item VALUES ('synthetic.pdf',10,6)")
        self.assertIsNone(self.printed())

    def test_course_lookup_does_not_touch_single_row_program(self):
        info = SimpleNamespace(has=lambda table,*columns: True)
        self.assertNotIn('FROM program WHERE', _course_fields(info))
