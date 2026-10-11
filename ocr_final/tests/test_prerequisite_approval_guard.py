import sqlite3
import unittest
from scripts.ingest_prerequisite_reviews import validate_existing,EVIDENCE_DDL,catalog_additions


class PrerequisiteApprovalGuardTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE prerequisite(code TEXT, requires TEXT)')
        self.db.executescript(EVIDENCE_DDL)
        self.review={'status':'required','requires':['06046400'],'source_file':'AI.pdf','page_number':287,'printed_page_number':283,'sha256':'source'}
    def tearDown(self):self.db.close()
    def test_verified_addition_is_allowed(self):
        validate_existing(self.db,self.review,['06046401'],{'06046400','06046401'})
    def test_orphan_is_rejected(self):
        with self.assertRaises(ValueError):validate_existing(self.db,self.review,['06046401'],{'06046401'})
    def test_review_for_absent_course_does_not_apply(self):
        validate_existing(self.db,self.review,[],{'06036100'})
    def test_conflicting_existing_edge_is_rejected(self):
        self.db.execute('INSERT INTO prerequisite VALUES (?,?)',('06046401','06046402'))
        with self.assertRaises(ValueError):validate_existing(self.db,self.review,['06046401'],{'06046400','06046401','06046402'})
    def test_conflicting_approval_is_rejected(self):
        self.db.execute('INSERT INTO course_prerequisite_evidence VALUES (?,?,?,?,?,?,?)',('06046401','explicit_none','AI.pdf',287,283,'source','visual'))
        with self.assertRaises(ValueError):validate_existing(self.db,self.review,['06046401'],{'06046400','06046401'})
    def test_catalog_additions_require_complete_source_fields(self):
        self.review['course_fields_by_code']={'06046401':{'name_th':'x'}}
        self.review['codes']=['06046401']
        with self.assertRaises(ValueError):catalog_additions(self.review,set())
    def test_catalog_addition_does_not_overwrite_existing_course(self):
        self.review['codes']=['06046401']
        self.review['course_fields_by_code']={'06046401':{'name_th':'x','name_en':'X','credits':3,'lecture_h':3,'lab_h':0,'self_h':6}}
        self.assertEqual(catalog_additions(self.review,{'06046401'}),{})
        self.assertEqual(set(catalog_additions(self.review,set())),{'06046401'})
