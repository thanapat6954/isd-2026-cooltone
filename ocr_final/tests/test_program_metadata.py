"""Isolated synthetic facts; production source reviews are not evaluation labels."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from lab10_fastapi.curriculum_app.database import DatabaseRegistry, execute_readonly
from lab10_fastapi.curriculum_app.query_planner import QueryPlan, deterministic_sql
from scripts.ingest_program_metadata import apply_review, facts
from scripts.ingest_program_requirements import snapshot


class ProgramMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root/'work/lab8b_it_2560_coop/curriculum.db'
        self.path.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.path)) as c, c:
            c.executescript('''CREATE TABLE program(program_id TEXT, name_th TEXT, total_credits INTEGER,
              years INTEGER, curriculum_version INTEGER, plan TEXT, source_file TEXT, page_number INTEGER);
              INSERT INTO program VALUES('IT-coop','Fixture (สหกิจศึกษา)',17,5,2560,'coop','fixture.pdf',40);
              CREATE TABLE course(code TEXT); INSERT INTO course VALUES('00000001');
              CREATE TABLE plan_item(code TEXT); INSERT INTO plan_item VALUES('00000001');
              CREATE TABLE prerequisite(code TEXT, requires TEXT);''')
        self.db = DatabaseRegistry(self.root).active_programs[0]
        self.review = {'program': 'IT', 'version': 2560, 'plans': ['coop', 'no-coop'], 'source_file': 'fixture.pdf',
            'name_th_base': 'Fixture', 'total_credits': 17, 'years': 5, 'pdf_page': 6, 'book_page': 1,
            'review_status': 'visually_verified', 'scope': 'citation_only_existing_facts'}

    def apply(self, review=None):
        with closing(sqlite3.connect(self.path)) as c, c:
            return apply_review(c, self.db, review or self.review, 'fixture hash')

    def test_citation_only_preserves_all_facts_and_records_original(self):
        with closing(sqlite3.connect(self.path)) as c:
            before = facts(c)
        self.assertTrue(self.apply())
        with closing(sqlite3.connect(self.path)) as c:
            self.assertEqual(before, facts(c))
            self.assertEqual(c.execute('SELECT page_number,printed_page_number FROM program').fetchone(), (6, 1))
            self.assertIn('"page_number": 40', c.execute('SELECT before_json FROM program_metadata_review').fetchone()[0])

    def test_idempotent_and_conflicting_approval_refused(self):
        self.apply()
        self.assertFalse(self.apply())
        with self.assertRaisesRegex(ValueError, 'no automatic overwrite'):
            self.apply({**self.review, 'pdf_page': 7})

    def test_changed_facts_refused_without_partial_schema(self):
        with self.assertRaisesRegex(ValueError, 'Existing facts differ'):
            self.apply({**self.review, 'years': 9})
        with closing(sqlite3.connect(self.path)) as c:
            self.assertNotIn('printed_page_number', [r[1] for r in c.execute('PRAGMA table_info(program)')])

    def test_wrong_version_and_wrong_plan_refused(self):
        for review in ({**self.review, 'version': 2565}, {**self.review, 'plans': ['no-coop']}):
            with self.assertRaisesRegex(ValueError, 'identity/version/plan'):
                self.apply(review)

    def test_unverified_or_invalid_pages_refused(self):
        for review in ({**self.review, 'review_status': 'unverified'}, {**self.review, 'book_page': 0}):
            with self.assertRaisesRegex(ValueError, 'unverified'):
                self.apply(review)

    def test_all_program_queries_include_paired_folios_only_when_stored(self):
        for intent in ('program_info', 'program_total_credits', 'program_years'):
            self.assertNotIn('printed_page_number', deterministic_sql(QueryPlan(intent), self.db))
        self.apply()
        db = DatabaseRegistry(self.root).active_programs[0]
        self.assertNotIn('program_metadata_review', db.objects)
        self.assertNotIn('before_json', db.schema_text())
        for intent in ('program_info', 'program_total_credits', 'program_years'):
            _, rows = execute_readonly(db, deterministic_sql(QueryPlan(intent), db))
            self.assertEqual((rows[0]['page_number'], rows[0]['printed_page_number']), (6, 1))

    def test_backup_restore_recovers_original_schema_and_facts(self):
        backup, isolated = self.root/'backup.db', self.root/'isolated.db'
        snapshot(self.path, backup)
        self.apply()
        snapshot(backup, isolated)
        with closing(sqlite3.connect(isolated)) as c:
            self.assertEqual(c.execute('SELECT years,page_number FROM program').fetchone(), (5, 40))
            self.assertNotIn('printed_page_number', [r[1] for r in c.execute('PRAGMA table_info(program)')])
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0], 'ok')


if __name__ == '__main__':
    unittest.main()
