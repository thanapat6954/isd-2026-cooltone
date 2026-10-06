"""Synthetic isolated fixtures; never production facts or evaluation answers."""
from dataclasses import replace
from contextlib import closing
import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

from lab10_fastapi.curriculum_app.config import settings
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, execute_readonly
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
from lab10_fastapi.curriculum_app.query_planner import detect_intent, deterministic_sql
from scripts.ingest_program_requirements import insert_review, snapshot


class NoModel:
    def ollama_generate(self, *args, **kwargs):
        raise AssertionError('Source-reviewed structured intent must not fabricate model facts')


class RequirementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root/'work/lab8b_dsba_2560_coop/curriculum.db'
        self.path.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.executescript('''CREATE TABLE program(program_id TEXT,curriculum_version INTEGER,plan TEXT,source_file TEXT);
            INSERT INTO program VALUES('DSBA-coop',2560,'coop','DSBA-60.pdf');
            CREATE TABLE course(code TEXT PRIMARY KEY);
            CREATE TABLE plan_item(id INTEGER PRIMARY KEY,code TEXT,year INTEGER,semester INTEGER);
            CREATE TABLE prerequisite(code TEXT,requires TEXT);
            INSERT INTO course VALUES('00000001');''')
        self.registry = DatabaseRegistry(self.root)
        self.db = self.registry.active_programs[0]
        self.review = {'rule_text': 'Synthetic reference, not a graduation permission', 'regulation_year': 2559,
                       'source_file': 'DSBA-60.pdf', 'sha256': 'synthetic fixture', 'pdf_page': 60,
                       'book_page': 55, 'section': 'Fixture only', 'review_scope': 'reference_only'}
        self.model = QwenTextToSQL(replace(settings, database_root=self.root), NoModel())

    def ingest(self, db=None, review=None):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            return insert_review(connection, db or self.db, review or self.review, 'fixture only', 'fixture hash')

    def test_recognizes_requirements_and_accelerated_planning_without_question_ids(self):
        self.assertEqual(detect_intent('เกณฑ์การสำเร็จการศึกษามีอะไรบ้าง').intent, 'graduation_reference')
        self.assertEqual(detect_intent('แผนนี้ครบเงื่อนไขจบไหม').intent, 'graduation_reference')
        self.assertEqual(detect_intent('อยากจบใน 3.5 ปี ทำได้ไหม').intent, 'study_feasibility')

    def test_missing_rules_are_scoped_uncertainty_without_model_call(self):
        result = self.model.ask(self.registry, 'หลักสูตร DSBA 2560 สหกิจ: เงื่อนไขจบมีอะไรบ้าง')
        self.assertEqual(result['rows'], [])
        self.assertIn('DSBA-2560-coop', result['answer'])
        self.assertIn('จึงยังสรุปไม่ได้', result['answer'])

    def test_immutable_review_is_idempotent_and_conflict_fails(self):
        self.assertTrue(self.ingest())
        self.assertFalse(self.ingest())
        with self.assertRaisesRegex(ValueError, 'no automatic overwrite'):
            self.ingest(review={**self.review, 'rule_text': 'unsafe different fact'})
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM program_requirement').fetchone()[0], 1)

    def test_wrong_version_rules_never_join_selected_program(self):
        self.ingest()
        other = SimpleNamespace(program_id='DSBA-coop', curriculum_version=2565, plan='coop')
        self.ingest(db=other, review={**self.review, 'regulation_year': 2564})
        self.registry.refresh()
        db = self.registry.active_programs[0]
        _, rows = execute_readonly(db, deterministic_sql(detect_intent('เงื่อนไขจบมีอะไรบ้าง'), db))
        self.assertEqual([row['regulation_year'] for row in rows], [2559])

    def test_source_rule_is_not_an_enrollment_or_acceleration_grant(self):
        self.ingest()
        result = self.model.ask(self.registry, 'หลักสูตร DSBA 2560 สหกิจ: อยากจบใน 3.5 ปี ทำได้ไหม')
        self.assertIn(self.review['rule_text'], result['answer'])
        self.assertIn('ยังรับรองไม่ได้', result['answer'])
        self.assertEqual(result['rows'][0]['printed_page_number'], 55)
        self.assertNotIn('ลงทะเบียนได้แน่นอน', result['answer'])

    def test_backup_preserves_original_and_isolated_rollback_recovers_it(self):
        backup, isolated = self.root/'backup.db', self.root/'isolated.db'
        snapshot(self.path, backup)
        self.ingest()
        snapshot(self.path, isolated)
        snapshot(backup, isolated)
        with closing(sqlite3.connect(isolated)) as connection:
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(connection.execute('SELECT count(*) FROM course').fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT count(*) FROM sqlite_master WHERE name='program_requirement'").fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
