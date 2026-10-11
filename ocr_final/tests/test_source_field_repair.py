import copy
import sqlite3
import unittest
from scripts.repair_source_fields import patch, snapshot
from scripts.migrate_study_evidence import plan_note


class SourceFieldRepairTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript("CREATE TABLE program(program_id,curriculum_version,plan,source_file); INSERT INTO program VALUES('SYN-no-coop',2560,'no-coop','SYN.pdf'); CREATE TABLE study_term(id INTEGER PRIMARY KEY,source_file,note); INSERT INTO study_term VALUES(4,'SYN.pdf','cooperative note'); CREATE TABLE protected(value); INSERT INTO protected VALUES('unchanged');")
        self.approval = {'status':'visually_verified','program_id':'SYN-no-coop','version':2560,'plan':'no-coop','source_file':'SYN.pdf','changes':[{'table':'study_term','row_id':4,'pdf_page':32,'printed_page':27,'before':{'note':'cooperative note'},'values':{'note':'project note'}}]}

    def tearDown(self):
        self.db.close()

    def test_only_approved_field_changes_and_idempotent(self):
        with self.db:
            self.assertEqual(len(patch(self.db,self.approval,'hash')),1)
            self.assertEqual(patch(self.db,self.approval,'hash'),[])
        self.assertEqual(self.db.execute('SELECT * FROM protected').fetchall(),[('unchanged',)])

    def test_source_approved_category_preserves_all_other_fields(self):
        self.db.execute('CREATE TABLE plan_item(id INTEGER PRIMARY KEY,category,credits,source_file,page_number,printed_page_number)')
        self.db.execute("INSERT INTO plan_item VALUES(31,'free elective',3,'SYN.pdf',20,15)")
        self.db.commit()
        self.approval['changes'] = [{'table':'plan_item','row_id':31,
            'pdf_page':20,'printed_page':15,'before':{'category':'free elective'},
            'values':{'category':'general education'}}]
        with self.db:
            self.assertEqual(len(patch(self.db,self.approval,'category-hash')),1)
            self.assertEqual(patch(self.db,self.approval,'category-hash'),[])
        self.assertEqual(self.db.execute('SELECT credits FROM plan_item').fetchone()[0],3)

    def test_conflict_wrong_plan_and_unauthorized_field_rollback(self):
        baseline = snapshot(self.db)
        for mutate in ('conflict','plan','field'):
            approval = copy.deepcopy(self.approval)
            if mutate=='conflict': approval['changes'][0]['before']['note']='different'
            if mutate=='plan': approval['plan']='coop'
            if mutate=='field': approval['changes'][0]['values']={'id':7}
            with self.assertRaises(ValueError),self.db:
                patch(self.db,approval,'hash')
            self.assertEqual(snapshot(self.db),baseline)

    def test_plan_specific_notes_not_borrowed(self):
        term={'note':'coop-only','note_by_plan':{'no-coop':'projects'}}
        self.assertEqual(plan_note(term,'coop'),'coop-only')
        self.assertEqual(plan_note(term,'no-coop'),'projects')

    def test_missing_source_catalog_insert_preserves_unknown_description(self):
        self.db.execute('CREATE TABLE course(code TEXT PRIMARY KEY,name_th,name_en,credits,source_file,page_number,description_th)')
        self.db.commit()
        self.approval['new_courses'] = [{'evidence':'independent synthetic source row','printed_page':27,
            'values':{'code':'00000011','name_th':'Synthetic course','name_en':'SYNTHETIC','credits':3,'source_file':'SYN.pdf','page_number':32}}]
        with self.db:
            self.assertEqual(len(patch(self.db,self.approval,'hash')),2)
            self.assertEqual(patch(self.db,self.approval,'hash'),[])
        self.assertIsNone(self.db.execute('SELECT description_th FROM course').fetchone()[0])
        self.approval['new_courses'][0]['values']['name_th']='Conflicting user edit'
        with self.assertRaisesRegex(ValueError,'Conflicting existing catalog'),self.db:
            patch(self.db,self.approval,'newhash')
