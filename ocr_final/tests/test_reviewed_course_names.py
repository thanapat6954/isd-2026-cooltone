import sqlite3
import unittest
from scripts.ingest_source_course_names import apply_names,non_name_fingerprint,deploy_names


class ReviewedCourseNamesTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript("CREATE TABLE program(program_id,curriculum_version,source_file,plan); INSERT INTO program VALUES('IT-coop',2565,'IT.pdf','coop'); CREATE TABLE course(code,name_th,name_en,credits); INSERT INTO course VALUES('06016481','merged','merged',6); CREATE TABLE plan_item(code,name_th,name_en,year,semester); INSERT INTO plan_item VALUES('06016481',NULL,NULL,3,2); CREATE TABLE prerequisite(code,requires); INSERT INTO prerequisite VALUES('06016481','unchanged');")
        self.review={'review_status':'visually_verified','program':'IT','version':2565,'source_file':'IT.pdf','reviews':[{'plan':'coop','code':'06016481','pdf_page':42,'printed_page':37,'names':{'name_th':'สหกิจศึกษา','name_en':'COOPERATIVE EDUCATION'}}]}
    def tearDown(self):self.db.close()
    def test_source_names_only_and_idempotent(self):
        before=non_name_fingerprint(self.db)
        self.assertEqual(len(apply_names(self.db,self.review,'approval')),4)
        self.assertEqual(apply_names(self.db,self.review,'approval'),[])
        self.assertEqual(non_name_fingerprint(self.db),before)
        self.assertEqual(self.db.execute('SELECT requires FROM prerequisite').fetchone()[0],'unchanged')
    def test_unverified_and_wrong_identity_rejected(self):
        for change in ({'review_status':'unverified'},{'version':2560}):
            with self.assertRaises(ValueError):apply_names(self.db,{**self.review,**change},'approval')
    def test_missing_course_and_non_name_fact_rejected(self):
        self.review['reviews'][0]['names']={'credits':3}
        with self.assertRaises(ValueError):apply_names(self.db,self.review,'approval')

    def test_transactional_deployment_guards_and_rollback(self):
        before=non_name_fingerprint(self.db)
        names=[tuple(r) for table in ('course','plan_item') for r in self.db.execute(f'SELECT ?,rowid,name_th,name_en FROM {table} ORDER BY rowid',(table,))]
        stage=sqlite3.connect(':memory:')
        self.db.backup(stage)
        changes=apply_names(stage,self.review,'approval')
        stage.close()
        with self.db:
            deploy_names(self.db,self.review,'approval',changes,before,names)
        self.assertEqual(non_name_fingerprint(self.db),before)
        current=[tuple(r) for table in ('course','plan_item') for r in self.db.execute(f'SELECT ?,rowid,name_th,name_en FROM {table} ORDER BY rowid',(table,))]
        with self.assertRaises(ValueError),self.db:
            deploy_names(self.db,self.review,'approval',[],before,names)
        self.assertEqual(current,[tuple(r) for table in ('course','plan_item') for r in self.db.execute(f'SELECT ?,rowid,name_th,name_en FROM {table} ORDER BY rowid',(table,))])
        with self.assertRaises(ValueError),self.db:
            deploy_names(self.db,self.review,'different-approval',[{'impossible':True}],before,current)
        self.assertEqual(self.db.execute('SELECT name_th FROM course').fetchone()[0],'สหกิจศึกษา')
        self.review['reviews'][0]['names']={'name_th':'name'};self.review['reviews'][0]['code']='00000000'
        with self.assertRaises(ValueError):apply_names(self.db,self.review,'approval')
