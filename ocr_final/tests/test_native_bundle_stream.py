"""Whole bundle counting, membership and cross-page evidence boundaries."""
import sqlite3
import unittest

from scripts.native_plan_sequence import credit_total, merge_continuation, whole_group_rule, parse_row, is_whole_bundle
from scr.ocr_system.lab8b_curriculum_db import DDL, _plan_credits


class BundleStreamTests(unittest.TestCase):
    def test_coop_or_overseas_choice_remains_within_each_branch(self):
        def line(text,y):return {'text':text,'bbox':[0,y,100,y+1]}
        code_text='12345678\nหรือ\n12345679'
        name_text='แขนงวิชาทดสอบ\nสหกิจศึกษา\nCOOPERATIVE EDUCATION\nสหกิจศึกษาต่างประเทศ\nOVERSEAS COOPERATIVE EDUCATION'
        raw={'cells':[code_text,name_text,'6(0-36-0)\n6(0-36-0)'],
             'positioned':[[line('12345678',20),line('12345679',60)],
                [line('แขนงวิชาทดสอบ',5),line('สหกิจศึกษา',20),line('COOPERATIVE EDUCATION',30),
                 line('สหกิจศึกษาต่างประเทศ',60),line('OVERSEAS COOPERATIVE EDUCATION',70)],
                [line('6(0-36-0)',20),line('6(0-36-0)',60)]],
             'page':2,'printed':2,'ordinal':1,
             'claims':[{'field':f,'pdf_page':2,'printed_page':2,'literal':v}
                       for f,v in zip(('code','names','hours'),[code_text,name_text,'6(0-36-0)\n6(0-36-0)'])]}
        rule={'text':'นักศึกษาจะต้องเลือกแขนงที่จะเรียน','source_file':'source.pdf','pdf_page':1,'printed_page':1}
        row=parse_row(raw,4,1,'source.pdf',rule)[0]
        self.assertEqual(list(row['course_options']),['12345678','12345679'])
        self.assertEqual(row['course_options']['12345678']['name_th'],'สหกิจศึกษา')
        self.assertEqual(row['bundle_label'],'แขนงวิชาทดสอบ')
        self.assertEqual(credit_total([row]),6)
        converted=[{'bundle_id':row['bundle_id'],'alt_group':row['alt_group'],'credits':6},
                   {'bundle_id':row['bundle_id'],'alt_group':row['alt_group'],'credits':6}]
        self.assertEqual(_plan_credits(converted),6)
        self.assertEqual(credit_total(converted),6)
        converted[1]['credits']=5
        for counter in (_plan_credits,credit_total):
            with self.assertRaisesRegex(ValueError,'unequal'):counter(converted)

    def test_sql_nested_choice_counts_one_course_and_one_branch(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript(DDL)
            db.execute("INSERT INTO program(program_id,name_th,total_credits,years) VALUES ('test','test',30,4)")
            for branch in ('a','b','c'):
                db.execute('INSERT INTO plan_bundle VALUES (4,1,?,?,?,?,?,?)',
                           (branch,branch,'choose one branch','source.pdf',1,1))
                for option in (1,2):
                    cursor=db.execute("INSERT INTO plan_item(program_id,year,semester,code,credits,alt_group) VALUES ('test',4,1,?,6,?)",
                                      (branch+str(option),branch+'-choice'))
                    db.execute('INSERT INTO plan_bundle_member VALUES (?,4,1,?)',(cursor.lastrowid,branch))
            self.assertEqual(db.execute('SELECT credits,n_courses FROM v_semester_credits').fetchone(),(6,1))

    def test_single_project_per_branch_counts_one_complete_branch(self):
        def line(text,y):return {'text':text,'bbox':[0,y,100,y+1]}
        parsed=[]
        rule={'text':'นักศึกษาจะต้องเลือกแขนงที่จะเรียน โดยความเห็นชอบของคณะฯ',
              'source_file':'source.pdf','pdf_page':1,'printed_page':1}
        for i in range(3):
            raw={'cells':[f'1234567{i}',f'แขนงวิชาทดสอบ {i}\nโครงงาน\nPROJECT','3(0-9-0)'],
                'positioned':[[line(f'1234567{i}',20)],
                              [line(f'แขนงวิชาทดสอบ {i}',5),line('โครงงาน',20),line('PROJECT',30)],
                              [line('3(0-9-0)',20)]], 'page':2,'printed':2,'claims':[]}
            self.assertTrue(is_whole_bundle(raw))
            parsed+=parse_row(raw,4,1,'source.pdf',rule)
        self.assertEqual(credit_total(parsed),3)
        self.assertEqual(len({r['bundle_id'] for r in parsed}),3)
        self.assertTrue(all(r['name_th']=='โครงงาน' for r in parsed))
        with self.assertRaisesRegex(ValueError,'rule'):
            parse_row(raw,4,1,'source.pdf',None)

    def test_old_curriculum_choice_rule_keeps_timing_and_approval(self):
        rule = 'นักศึกษาจะต้องเลือกแขนงที่จะเรียน เมื่อขึ้นปีที่ 2 ภาคการศึกษาที่ 2 โดยความเห็นชอบของคณะฯ'
        self.assertEqual(whole_group_rule('หัวข้อ\n' + rule + '\nกลุ่มวิชาทั่วไป'), rule)
        self.assertIsNone(whole_group_rule('นักศึกษาสามารถเลือกเรียนรายวิชาอื่นเป็นวิชาเลือก'))

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
