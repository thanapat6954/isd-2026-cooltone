"""Runtime handoff artifacts must not overwrite data or become evaluation labels."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from scripts.runtime_bundle import export_bundle, restore_bundle, within
from lab10_fastapi.curriculum_app.database import DatabaseRegistry


class RuntimeBundleTests(unittest.TestCase):
    def test_roundtrip_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'source'
            source.mkdir()
            db = source/'curriculum.db'
            with closing(sqlite3.connect(db)) as con:
                con.execute('CREATE TABLE courses (course_code TEXT)')
                con.execute("INSERT INTO courses VALUES ('TEST_ONLY')")
                con.commit()
            result = export_bundle(source, root/'bundle')
            self.assertEqual(result['databases'][0]['integrity'], 'ok')
            self.assertIn('NOT independent', result['scope'])
            export_bundle(source, source/'work/handoff/runtime-data')
            self.assertEqual(len(DatabaseRegistry(source).active_catalogs), 1)
            target = root/'new'
            self.assertEqual(restore_bundle(root/'bundle', target)['restored'], 1)
            with self.assertRaises(FileExistsError):
                restore_bundle(root/'bundle', target)
            with self.assertRaises(FileExistsError):
                export_bundle(source, root/'bundle')

    def test_all_paths_validated_before_any_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root/'bundle'
            bundle.mkdir()
            manifest = {'format': 1, 'databases': [{'path': '../escape/curriculum.db', 'sha256': 'x'}]}
            (bundle/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                restore_bundle(bundle, root/'target')
            self.assertFalse((root/'target').exists())

    def test_unsafe_paths_rejected(self):
        for path in ('../outside', 'C:/outside', 'work\\escape', ''):
            with self.subTest(path=path), self.assertRaises(ValueError):
                within(Path.cwd(), path)
