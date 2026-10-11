import sqlite3
import unittest
from scripts.ingest_plan_page_pairs import apply_review


class PlanPagePairsTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.executescript("CREATE TABLE program(program_id TEXT,curriculum_version INTEGER,source_file TEXT); INSERT INTO program VALUES('BIT-coop',2565,'BIT-65.pdf'); CREATE TABLE plan_item(id INTEGER,code TEXT,credits INTEGER,source_file TEXT,page_number INTEGER,printed_page_number INTEGER); INSERT INTO plan_item VALUES(1,'06036100',3,'BIT-65.pdf',31,NULL);")
        self.review = {'program': 'BIT', 'version': 2565, 'source_file': 'BIT-65.pdf', 'pages': [[31,26]]}

    def test_citation_only_and_idempotent(self):
        self.assertEqual(len(apply_review(self.db, self.review, 'approved')), 1)
        self.assertEqual(apply_review(self.db, self.review, 'approved'), [])
        self.assertEqual(self.db.execute('SELECT code,credits,printed_page_number FROM plan_item').fetchone(), ('06036100',3,26))

    def test_conflicting_folio_rejected(self):
        self.db.execute('UPDATE plan_item SET printed_page_number=99')
        with self.assertRaises(ValueError):
            apply_review(self.db, self.review, 'approved')

    def test_version_mismatch_rejected(self):
        self.review['version'] = 2560
        with self.assertRaises(ValueError):
            apply_review(self.db, self.review, 'approved')

    def test_changed_approval_rejected(self):
        apply_review(self.db, self.review, 'approved')
        with self.assertRaises(ValueError):
            apply_review(self.db, self.review, 'different')
