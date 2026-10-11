"""Whole bundle counting, membership and cross-page evidence boundaries."""
import sqlite3
import unittest

from scripts.native_plan_sequence import credit_total, merge_continuation
from scr.ocr_system.lab8b_curriculum_db import DDL, _plan_credits


class BundleStreamTests(unittest.TestCase):
    def test_equal_complete_bundles_count_once_without_ordinal_pairing(self):
        rows = [{'credits':3}, {'credits':2,'bundle_id':'a'}, {'credits':4,'bundle_id':'a'},
                {'credits':1,'bundle_id':'b'}, {'credits':5,'bundle_id':'b'}]
        self.assertEqual(credit_total(rows),9)
        self.assertEqual(_plan_credits(rows),9)
        rows[-1]['credits'] = 4
        for count in (credit_total,_plan_credits):
            with self.assertRaises(ValueError):count(rows)

    def test_continuation_retains_page_for_each_appended_field(self):
        before = {'page':4,'cells':['1234xxxx','ชื่อ\nNAME','3(3-0-6)'],'claims':[]}
        after = {'page':5,'printed':2,'cells':['','','หรือ 3(0-6-3)']}
        merge_continuation(before,after)
        self.assertEqual(before['claims'],[{'field':'hours','pdf_page':5,'printed_page':2,'literal':'หรือ 3(0-6-3)'}])
        self.assertIn('3(0-6-3)',before['cells'][2])
        for invalid in ({**after,'page':6},{**after,'cells':['12345678','unrelated','3(3-0-6)']}):
            with self.assertRaises(ValueError):merge_continuation(before,invalid)

    def test_sql_shared_course_memberships_are_distinct_whole_bundles(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript(DDL)
            db.execute("INSERT INTO program(program_id,name_th,total_credits,years) VALUES ('test','test',30,4)")
            db.execute("INSERT INTO course(code,name_th,credits) VALUES ('12345678','test',3)")
            for bundle, credits in [('a',[2,4]),('b',[1,5])]:
                db.execute('INSERT INTO plan_bundle VALUES (2,2,?,?,?,?,?,?)',
                    (bundle,bundle,'choose one whole group','source.pdf',1,1))
                for credit in credits:
                    cursor = db.execute("INSERT INTO plan_item(program_id,year,semester,code,credits) VALUES ('test',2,2,'12345678',?)",(credit,))
                    db.execute('INSERT INTO plan_bundle_member VALUES (?,2,2,?)',(cursor.lastrowid,bundle))
            self.assertEqual(db.execute('SELECT credits FROM v_semester_credits').fetchone()[0],6)
            self.assertEqual(db.execute('SELECT credits FROM v_total_credits').fetchone()[0],6)
            self.assertEqual(db.execute('SELECT COUNT(DISTINCT bundle_id) FROM plan_bundle_member').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM plan_item WHERE alt_group IS NOT NULL').fetchone()[0],0)
            from types import SimpleNamespace
            from lab10_fastapi.curriculum_app.query_planner import QueryPlan, deterministic_sql
            def has(table, *columns):
                return set(columns) <= {r[1] for r in db.execute('PRAGMA table_info('+table+')')}
            sql = deterministic_sql(QueryPlan('course_count',year=2,semester=2),SimpleNamespace(has=has))
            result = db.execute(sql).fetchone()
            self.assertEqual(result[0],2)
            self.assertEqual(result[1],2)
