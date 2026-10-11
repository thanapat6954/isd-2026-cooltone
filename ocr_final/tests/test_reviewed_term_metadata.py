import copy
import unittest
from scripts.ingest_reviewed_term_metadata import patch, facts
from tests import test_reviewed_plan_metadata as fixture
from scripts.repair_reviewed_plan_metadata import patch as patch_facts


class TermMetadataTests(unittest.TestCase):
    def setUp(self):
        fixture.ReviewedMetadataTests.setUp(self)
        self.db.execute('CREATE UNIQUE INDEX plan_item_identity ON plan_item(id)')
        self.approval.update(curriculum_version=2565, reviewed_on='2026-10-10',
                             source_sha256='test-source', term_metadata_years=[4],
                             profile_identity_reviews={'it-coop':{'program_id':'IT-coop','plan':'coop'}})
        patch_facts(self.db, self.approval, 'it-coop', 'test')

    def tearDown(self):
        self.db.close()

    def test_membership_total_facts_and_idempotence(self):
        before = facts(self.db)
        self.assertTrue(patch(self.db, self.approval, 'approval'))
        self.assertEqual(self.db.execute('SELECT printed_total FROM study_term').fetchone()[0], 3)
        self.assertEqual(tuple(self.db.execute('SELECT * FROM study_item').fetchone()), (7,1,1,None,None))
        self.assertEqual(tuple(self.db.execute('SELECT pdf_page,printed_page FROM study_page').fetchone()), (43,38))
        self.assertEqual(patch(self.db, self.approval, 'approval'), [])
        self.assertEqual(before, facts(self.db))

    def test_source_mismatch_is_not_hidden_by_correct_credit_total(self):
        for field, value in [('name_th','different'), ('printed_page_number',99), ('credits_raw','3(3-0-6)')]:
            old = self.db.execute(f'SELECT {field} FROM plan_item').fetchone()[0]
            self.db.execute(f'UPDATE plan_item SET {field}=?', (value,))
            with self.assertRaises(ValueError):
                patch(self.db, self.approval, 'approval')
            self.db.execute(f'UPDATE plan_item SET {field}=?', (old,))

    def test_wrong_plan_and_unapproved_term_fail(self):
        other = copy.deepcopy(self.approval)
        other['profile_identity_reviews']['it-coop']['plan'] = 'no-coop'
        with self.assertRaises(ValueError):
            patch(self.db, other, 'approval')

    def test_source_specialization_membership_preserves_facts_and_is_idempotent(self):
        before = facts(self.db)
        term = self.approval['profiles']['it-coop'][0]
        term['tracks'] = [{'id':'network', 'label':'แขนงเครือข่าย', 'aliases':['เครือข่าย']}]
        term['rows'][0]['track_ids'] = ['network']
        patch(self.db, self.approval, 'approval')
        self.assertEqual(tuple(self.db.execute('SELECT * FROM study_item').fetchone()), (7,1,0,None,None))
        self.assertEqual(tuple(self.db.execute('SELECT * FROM study_member').fetchone()), (7,'network',None,None))
        self.assertEqual(facts(self.db), before)
        self.assertEqual(patch(self.db, self.approval, 'approval'), [])

    def test_unknown_specialization_and_user_membership_conflict_fail(self):
        term = self.approval['profiles']['it-coop'][0]
        term['rows'][0]['track_ids'] = ['unapproved']
        with self.assertRaisesRegex(ValueError, 'Unapproved specialization'):
            patch(self.db, self.approval, 'approval')
        term['tracks'] = [{'id':'unapproved','label':'แขนงตัวอย่าง'}]
        patch(self.db, self.approval, 'approval')
        self.db.execute("UPDATE study_member SET display_name_th='user edit'")
        with self.assertRaisesRegex(ValueError, 'Conflicting existing specialization'):
            patch(self.db, self.approval, 'approval')

    def test_whitespace_only_hours_difference_preserves_all_alternatives(self):
        before = facts(self.db)
        term = self.approval['profiles']['it-coop'][0]
        term['rows'][0]['credits'] = term['rows'][0]['credits'].replace('(', ' (').replace('หรือ', ' หรือ ')
        self.assertTrue(patch(self.db, self.approval, 'approval'))
        self.assertEqual(facts(self.db), before)
        self.db.execute("UPDATE plan_item SET credits_raw='3(3-0-6)'")
        with self.assertRaises(ValueError):
            patch(self.db, self.approval, 'approval')

    def test_printed_alternatives_count_once_and_require_matching_relationship(self):
        self.db.execute('ALTER TABLE plan_item ADD COLUMN alt_group TEXT')
        self.db.execute("UPDATE plan_item SET alt_group='db-choice'")
        columns = [r[1] for r in self.db.execute('PRAGMA table_info(plan_item)')]
        values = list(self.db.execute('SELECT * FROM plan_item').fetchone())
        values[columns.index('id')] = 8
        values[columns.index('code')] = 'ELEC-SLOT-8'
        values[columns.index('name_th')] = 'ตัวอย่าง slot 2'
        values[columns.index('name_en')] = 'EXAMPLE SLOT 2'
        self.db.execute('INSERT INTO plan_item VALUES ('+','.join('?' for _ in values)+')',values)
        term = self.approval['profiles']['it-coop'][0]
        term['row_count'] = 2
        term['rows'][0]['alt_group'] = 'source-choice'
        term['rows'].append({**term['rows'][0], 'name_th':'ตัวอย่าง slot 2','name_en':'EXAMPLE SLOT 2'})
        self.assertTrue(patch(self.db, self.approval, 'approval'))
        self.assertEqual(self.db.execute('SELECT printed_total FROM study_term').fetchone()[0],3)
        self.db.execute("UPDATE plan_item SET alt_group='different' WHERE id=8")
        with self.assertRaises(ValueError):
            patch(self.db, self.approval, 'approval')
        other = copy.deepcopy(self.approval)
        other['profiles']['it-coop'][0]['status'] = 'unverified'
        with self.assertRaises(ValueError):
            patch(self.db, other, 'approval')
