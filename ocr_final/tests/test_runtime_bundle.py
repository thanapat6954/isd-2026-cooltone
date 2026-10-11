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
    def test_sources_only_does_not_read_or_install_snapshots(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bundle = root/'bundle'
            (bundle/'data/input').mkdir(parents=True)
            pdf = bundle/'data/input/SYN.pdf'
            pdf.write_bytes(b'%PDF-test-only')
            from scripts.runtime_bundle import sha
            manifest = {'format':1,'includes_source_pdfs':True,
                        'databases':[{'path':'missing/curriculum.db','sha256':'unread'}],
                        'source_pdfs':[{'path':'data/input/SYN.pdf','sha256':sha(pdf)}]}
            (bundle/'manifest.json').write_text(json.dumps(manifest))
            result = restore_bundle(bundle,root/'target',sources_only=True)
            self.assertEqual(result['restored'],0)
            self.assertEqual(result['pdfs_restored'],1)
            self.assertEqual(list((root/'target').rglob('*.db')),[])
            pdf.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                restore_bundle(bundle,root/'bad',sources_only=True)
            self.assertFalse((root/'bad').exists())

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

    def test_complete_bundle_copies_pdfs_and_refuses_corruption_before_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            app = root/'source'
            (app/'data/input').mkdir(parents=True)
            (app/'data/input/SYN.pdf').write_bytes(b'%PDF-synthetic-test-only')
            with closing(sqlite3.connect(app/'curriculum.db')) as db:
                db.execute('CREATE TABLE courses(course_code)')
                db.commit()
            export_bundle(app, root/'bundle', include_pdfs=True)
            result = restore_bundle(root/'bundle', root/'target')
            self.assertEqual(result['pdfs_restored'], 1)
            self.assertEqual((root/'target/data/input/SYN.pdf').read_bytes(), b'%PDF-synthetic-test-only')
            (root/'bundle/data/input/SYN.pdf').write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                restore_bundle(root/'bundle', root/'new')
            self.assertFalse((root/'new').exists())

    def test_unsafe_paths_rejected(self):
        for path in ('../outside', 'C:/outside', 'work\\escape', ''):
            with self.subTest(path=path), self.assertRaises(ValueError):
                within(Path.cwd(), path)

    def test_reuse_pdfs_requires_matching_hash_and_preserves_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'source'
            (source/'data/input').mkdir(parents=True)
            (source/'data/input/SYN.pdf').write_bytes(b'%PDF-test-only')
            with closing(sqlite3.connect(source/'curriculum.db')) as db:
                db.execute('CREATE TABLE courses(course_code)')
                db.commit()
            export_bundle(source, root/'bundle', include_pdfs=True)
            target = root/'target'
            (target/'data/input').mkdir(parents=True)
            pdf = target/'data/input/SYN.pdf'
            pdf.write_bytes(b'%PDF-test-only')
            with self.assertRaises(FileExistsError):
                restore_bundle(root/'bundle', target)
            self.assertFalse((target/'curriculum.db').exists())
            pdf.write_bytes(b'different-user-source')
            with self.assertRaises(FileExistsError):
                restore_bundle(root/'bundle', target, reuse_verified_pdfs=True)
            self.assertFalse((target/'curriculum.db').exists())
            pdf.write_bytes(b'%PDF-test-only')
            result = restore_bundle(root/'bundle', target, reuse_verified_pdfs=True)
            self.assertEqual(result['pdfs_reused'], ['data/input/SYN.pdf'])
            self.assertEqual(result['pdfs_restored'], 0)
            self.assertEqual(pdf.read_bytes(), b'%PDF-test-only')
            with self.assertRaises(FileExistsError):
                restore_bundle(root/'bundle', target, reuse_verified_pdfs=True)
