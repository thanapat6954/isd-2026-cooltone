"""Real SQLite lifecycle and failure isolation; no factual expectations altered."""
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts.database_build import activation, import_bundle, read, rebuild, rollback, sha, validate, write
from lab10_fastapi.curriculum_app.database import DatabaseRegistry
from lab10_fastapi.curriculum_app.build_store import consumer_lock


class BuildSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Path(self.temp.name)/'app'
        self.bundle = Path(self.temp.name)/'bundle'
        self.bundle.mkdir()
        records = []
        from run_lab8b import PROFILES
        for name, profile in PROFILES.items():
            path = self.bundle/'work'/profile['out'].name/'curriculum.db'
            path.parent.mkdir(parents=True)
            with closing(sqlite3.connect(path)) as db:
                db.executescript('''CREATE TABLE program (program_id TEXT, curriculum_version INT, plan TEXT, name_th TEXT);
                    CREATE TABLE course (code TEXT); CREATE TABLE prerequisite (code TEXT);
                    CREATE TABLE plan_item (raw_code TEXT, code_pattern TEXT, is_placeholder INT,
                        alternative_index INT, printed_page_number INT); INSERT INTO course VALUES ('source-fixture');
                    INSERT INTO plan_item VALUES ('source-fixture', NULL, 0, NULL, 1);''')
                db.execute('INSERT INTO program VALUES (?,?,?,?)', (profile['program_id'], profile['curriculum_version'], profile['target_plan'].replace('_','-'), 'test-only'))
                db.commit()
            records.append({'path': path.relative_to(self.bundle).as_posix(), 'sha256':sha(path),
                            'profile': name, 'version':profile['curriculum_version'], 'plan':profile['target_plan'].replace('_','-')})
        legacy = self.bundle/'curriculum.db'
        with closing(sqlite3.connect(legacy)) as db:
            db.executescript("CREATE TABLE courses (course_code TEXT); INSERT INTO courses VALUES ('test-only');")
        records.append({'path':'curriculum.db','sha256':sha(legacy),'profile':'legacy-course-catalog','version':None,'plan':None})
        write(self.bundle/'manifest.json', {'format':1,'databases':records,'source_pdfs':[], 'scope':'synthetic lifecycle test, no accuracy evidence'})
        self.app.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_first_install_switch_rollback_and_user_data_backup(self):
        first = import_bundle(self.bundle, self.app)
        activation(self.app, first)
        registry = DatabaseRegistry(self.app)
        self.assertEqual(len(registry.active_catalogs),14)
        pinned = registry.build_id
        active = registry.active_catalogs[0].path
        with closing(sqlite3.connect(active)) as db:
            db.execute('CREATE TABLE user_notes (note TEXT)')
            db.execute("INSERT INTO user_notes VALUES ('preserve this')")
            db.commit()
        second = import_bundle(self.bundle, self.app)
        result = activation(self.app, second)
        self.assertEqual(registry.build_id, pinned)
        registry.refresh()
        self.assertEqual(registry.active_catalogs[0].path, active)
        backup = Path(result['backup'])
        files = list(backup.rglob('curriculum.db'))
        self.assertTrue(any(self.has_note(p) for p in files))
        recovered = rollback(self.app, backup)
        self.assertEqual(recovered['database_count'],14)
        self.assertTrue(self.has_note(DatabaseRegistry(self.app).active_catalogs[0].path))

    @staticmethod
    def has_note(path):
        with closing(sqlite3.connect(path)) as db:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='user_notes'").fetchone()
            return bool(exists and db.execute('SELECT note FROM user_notes').fetchone()[0]=='preserve this')

    def test_consumers_block_switch(self):
        candidate = import_bundle(self.bundle,self.app)
        with consumer_lock(self.app):
            with self.assertRaisesRegex(RuntimeError, 'stop_web'):
                activation(self.app,candidate)
        self.assertFalse((self.app/'work/active-build.json').exists())

    def test_partial_and_mismatch_rejected(self):
        candidate = import_bundle(self.bundle,self.app)
        item = read(candidate/'build.json')['databases'][0]
        (candidate/item['path']).unlink()
        self.assertFalse(validate(candidate,self.app)['ready'])
        with self.assertRaises(ValueError):
            activation(self.app,candidate)
        self.assertFalse((self.app/'work/active-build.json').exists())

    def test_same_identity_different_sqlite_hash_rejected(self):
        candidate = import_bundle(self.bundle,self.app)
        manifest = read(candidate/'build.json')
        item = manifest['databases'][0]
        with closing(sqlite3.connect(candidate/item['path'])) as db:
            db.execute('UPDATE program SET curriculum_version=9999')
            db.commit()
        item['sha256']=sha(candidate/item['path'])
        write(candidate/'build.json',manifest)
        self.assertFalse(validate(candidate,self.app)['ready'])

    def test_failure_after_pointer_restores_previous_whole_set(self):
        activation(self.app,import_bundle(self.bundle,self.app))
        pointer = (self.app/'work/active-build.json').read_bytes()
        candidate = import_bundle(self.bundle,self.app)
        def fail(stage):
            if stage=='after-pointer':
                raise RuntimeError('simulated post-activation failure')
        with self.assertRaisesRegex(RuntimeError,'simulated'):
            activation(self.app,candidate,failure_hook=fail)
        self.assertEqual((self.app/'work/active-build.json').read_bytes(),pointer)
        self.assertEqual(len(DatabaseRegistry(self.app).active_catalogs),14)

    def test_undeclared_sqlite_rejected(self):
        candidate = import_bundle(self.bundle,self.app)
        (candidate/'executor').mkdir()
        shutil.copyfile(candidate/'curriculum.db',candidate/'executor'/'curriculum.db')
        self.assertFalse(validate(candidate,self.app)['ready'])

    def test_raw_without_source_review_rejected(self):
        candidate = import_bundle(self.bundle,self.app)
        manifest=read(candidate/'build.json')
        manifest['origin']='fresh-raw'
        for row in manifest['databases']:
            row['extraction']='example.extraction.json'
        write(candidate/'example.extraction.json',{'status':'parsed','pages':[1],'pending_pages':[], 'material_defects':[], 'artifacts':[]})
        write(candidate/'build.json',manifest)
        self.assertFalse(validate(candidate,self.app)['ready'])

    def test_resume_rejects_changed_configuration_without_touching_checkpoint(self):
        with patch.dict('os.environ',{'LAB7_MODEL_OCR':'test-model-one:latest'}):
            candidate=rebuild(self.app,['ai'],'raw',1,10)
        before=(candidate/'build.json').read_bytes()
        with patch.dict('os.environ',{'LAB7_MODEL_OCR':'test-model-two:latest'}):
            with self.assertRaisesRegex(ValueError,'configuration'):
                rebuild(self.app,['ai'],'raw',1,10,resume=candidate)
        self.assertEqual((candidate/'build.json').read_bytes(),before)


if __name__=='__main__':
    unittest.main()
