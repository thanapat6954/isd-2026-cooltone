import copy
import sqlite3
import unittest
from scripts.repair_reviewed_plan_metadata import patch


class ReviewedMetadataTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript('''CREATE TABLE program(program_id,curriculum_version,source_file,plan);
            INSERT INTO program VALUES ('IT-coop',2565,'IT.pdf','coop');
            CREATE TABLE course(code,name_th,name_en);
            CREATE TABLE plan_item(id,year,semester,code,credits,name_th,name_en,credits_raw,raw_code,is_placeholder,code_pattern,source_file,page_number,printed_page_number,elective_type,category,ctype,note);
            INSERT INTO plan_item(id,year,semester,code,credits,category) VALUES(7,4,1,'ELEC-SLOT-7',3,'หมวดวิชาเลือกเสรี');''')
        self.approval={'profiles':{'it-coop':[{'status':'visually_verified','source_file':'IT.pdf','year':4,'semester':1,'row_count':1,'credits':3,'pdf_page':43,'printed_page':38,'rows':[{'code':'xxxxxxxx','name_th':'ตัวอย่าง slot','name_en':'EXAMPLE SLOT','credits':'3(x-x-x)'}]}]}}
    def tearDown(self):
        self.db.close()
    def test_placeholder_id_credits_and_code_preserved_and_idempotent(self):
        self.assertTrue(patch(self.db,self.approval,'it-coop','test'))
        self.assertEqual(tuple(self.db.execute('SELECT id,credits,code,raw_code,is_placeholder FROM plan_item').fetchone()),(7,3,'ELEC-SLOT-7','xxxxxxxx',1))
        self.assertEqual(patch(self.db,self.approval,'it-coop','test'),[])
    def test_wrong_identity_and_unapproved_data_rejected(self):
        self.db.execute('UPDATE program SET curriculum_version=2560')
        with self.assertRaises(ValueError):patch(self.db,self.approval,'it-coop','test')
        self.db.execute('UPDATE program SET curriculum_version=2565')
        other=copy.deepcopy(self.approval);other['profiles']['it-coop'][0]['status']='unverified'
        with self.assertRaises(ValueError):patch(self.db,other,'it-coop','test')
    def test_credit_mismatch_refuses_repair(self):
        self.db.execute('UPDATE plan_item SET credits=6')
        with self.assertRaises(ValueError):patch(self.db,self.approval,'it-coop','test')
