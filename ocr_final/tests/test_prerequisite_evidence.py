"""Observable regressions for missing evidence versus explicitly reviewed NONE."""
import hashlib
import json
import subprocess
import sys
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from contextlib import closing
from pathlib import Path

from lab10_fastapi.curriculum_app.config import settings
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, inspect_database, open_readonly
from lab10_fastapi.curriculum_app.main import _frontend_question, _source_quote
from lab10_fastapi.curriculum_app.schemas import FrontendAskRequest
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
from scripts.audit_all import audit_dataset
from scripts.ingest_prerequisite_reviews import EVIDENCE_DDL
from lab10_fastapi.curriculum_app.query_planner import detect_intent


class NoModel:
    def ollama_generate(self, *args, **kwargs):
        raise AssertionError('Structured prerequisite cases must not need model SQL')


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'work/lab8b_dsba_coop/curriculum.db'
        self.path.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.executescript('''
                CREATE TABLE program(program_id TEXT, name_th TEXT, total_credits INTEGER, years INTEGER,
                    curriculum_version INTEGER, is_latest INTEGER, plan TEXT);
                INSERT INTO program VALUES('DSBA-coop','DSBA',132,4,2565,1,'coop');
                CREATE TABLE course(code TEXT PRIMARY KEY, name_th TEXT, name_en TEXT, credits INTEGER,
                    source_file TEXT, page_number INTEGER, lecture_h INTEGER, lab_h INTEGER,self_h INTEGER);
                INSERT INTO course VALUES('06066302','การเขียนโปรแกรมเว็บ','WEB PROGRAMMING',3,'DSBA.pdf',32,2,2,5);
                CREATE TABLE prerequisite(code TEXT, requires TEXT, kind TEXT, source_file TEXT,page_number INTEGER);
                CREATE TABLE plan_item(code TEXT, year INTEGER,semester INTEGER);
            ''')
        self.assistant = QwenTextToSQL(replace(settings, debug=True), NoModel())
        self.registry = DatabaseRegistry(self.root)
        self.question = 'หลักสูตร DSBA 2565 สหกิจ วิชา 06066302 มีวิชาบังคับก่อนอะไร ถ้ายังไม่ผ่านลงทะเบียนได้หรือไม่'

    def test_existing_course_unknown_is_not_absent_or_none(self):
        result = self.assistant.ask(self.registry, self.question)
        self.assertEqual(result['rows'][0]['code'], '06066302')
        self.assertIn('ข้อมูลวิชาบังคับก่อนยังไม่ยืนยัน', result['answer'])
        self.assertNotIn('เอกสารระบุว่าไม่มี', result['answer'])
        self.assertIn('ยังสรุปไม่ได้', result['answer'])
        self.assertIn('หลักฐานยืนยันรายวิชาเท่านั้น', _source_quote(result['rows'][0]))

    def test_verified_none_cites_description_and_retains_registration_uncertainty(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.executescript(EVIDENCE_DDL)
            connection.execute('INSERT INTO course_prerequisite_evidence VALUES(?,?,?,?,?,?,?)',
                ('06066302','explicit_none','DSBA.pdf',319,318,'test','visual'))
            connection.commit()
        result = self.assistant.ask(self.registry, self.question)
        row = result['rows'][0]
        self.assertIn('เอกสารระบุว่าไม่มีวิชาบังคับก่อน', result['answer'])
        self.assertIn('ยังสรุปไม่ได้', result['answer'])
        self.assertEqual((row['source_file'],row['page_number'],row['printed_page_number']),('DSBA.pdf',319,318))

    def test_actual_required_edge_is_not_rendered_as_none(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute('INSERT INTO prerequisite VALUES(?,?,?,?,?)',('06066302','06066301','pre','DSBA.pdf',319))
            connection.commit()
        result = self.assistant.ask(self.registry,self.question)
        self.assertIn('วิชาบังคับก่อนที่ระบุคือ 06066301',result['answer'])
        self.assertNotIn('เอกสารระบุว่าไม่มี',result['answer'])

    def test_empty_results_name_identity_and_do_not_assert_book_absence(self):
        result = self.assistant.ask(self.registry,'หลักสูตร DSBA 2565 สหกิจ วิชา 09999999 มีรายละเอียดอะไร')
        self.assertIn('DSBA-2565-coop', result['answer'])
        self.assertIn('จึงยังสรุปไม่ได้', result['answer'])

    def test_unknown_requested_version_does_not_fall_back(self):
        self.assertEqual(self.registry.select('หลักสูตร DSBA ฉบับเก่า 2560 วิชา 06066302',include_legacy=True),[])

    def test_ai_current_ui_does_not_invent_a_year(self):
        question = _frontend_question(FrontendAskRequest(question='วิชาอะไร',curriculum='AIT',version='latest'))
        self.assertIn('AI ฉบับปัจจุบัน',question)
        self.assertNotIn('2565',question)

    def test_course_name_in_explicit_curriculum_is_not_program_info(self):
        plan = detect_intent('หลักสูตร IT 2560 สหกิจ: วิชา 06016323 ชื่อวิชาอะไร')
        self.assertEqual(plan.intent,'course_detail')

    def test_thai_no_coop_does_not_select_coop(self):
        self.assertEqual(self.registry.select('หลักสูตร DSBA 2565 ไม่เข้าร่วมสหกิจ'),[])

    def test_existing_edge_remains_visible_with_partial_evidence_table(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.executescript(EVIDENCE_DDL)
            connection.execute('INSERT INTO prerequisite VALUES(?,?,?,?,?)',('06066302','06066301','pre','DSBA.pdf',319))
            connection.commit()
        result = self.assistant.ask(self.registry,self.question)
        self.assertIn('วิชาบังคับก่อนที่ระบุคือ 06066301',result['answer'])

    def test_explicit_other_book_year_is_not_ignored(self):
        self.assertEqual(self.registry.select('หลักสูตร DSBA 2566 สหกิจ'),[])

    def test_latest_uses_stored_flag_not_assumed_year(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute('UPDATE program SET curriculum_version=2566')
            connection.commit()
        self.registry.refresh()
        selected = self.registry.select('หลักสูตร DSBA ฉบับล่าสุด สหกิจ')
        self.assertEqual([item.curriculum_version for item in selected],[2566])

    def test_readonly_diagnostics_reject_writes(self):
        connection = open_readonly(self.path)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute('DELETE FROM course')
        finally:
            connection.close()

    def test_audit_uses_real_retrieval_and_does_not_modify_database(self):
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        result = audit_dataset(self.path,self.root,{})
        self.assertEqual(result['retrieval'],{'tested':1,'misses':0,'scope':'Actual application SQL validation/execution path; not LLM/API/UI scoring'})
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)
        self.assertIn('SKIPPED',{item['status'] for item in result['findings']})

    def test_cache_reports_current_request_latency(self):
        first = self.assistant.ask(self.registry,self.question)
        second = self.assistant.ask(self.registry,self.question)
        self.assertFalse(first['cache_hit'])
        self.assertTrue(second['cache_hit'])
        self.assertTrue(second['debug']['cache_hit'])
        self.assertEqual(set(second['debug']['timing_ms']),{'total'})

    def run_ingest(self, review):
        source_dir = self.root/'data/input'
        source_dir.mkdir(parents=True,exist_ok=True)
        source_bytes = b'Unit test fixture, not official source evidence'
        (source_dir/'DSBA.pdf').write_bytes(source_bytes)
        document = {'source_file':'DSBA.pdf','program':'DSBA','curriculum_version':2565,
            'sha256':hashlib.sha256(source_bytes).hexdigest(),'review_status':'visually_verified',
            'codes':['06066302'],'status':'explicit_none','page_number':319,'printed_page_number':318,**review}
        review_path = self.root/'reviews.json'
        review_path.write_text(json.dumps({'documents':[document]}),encoding='utf-8')
        output = self.root/'ingest.json'
        process = subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve().parents[1]/'scripts/ingest_prerequisite_reviews.py'),
            '--app-root',str(self.root),'--reviews',str(review_path),'--output',str(output),'--database',str(self.path),'--apply'],
            capture_output=True,text=True,encoding='utf-8',timeout=20)
        return process,output

    def test_review_ingest_backs_up_original_before_named_correction(self):
        process,output = self.run_ingest({'name_th_by_code':{'06066302':'ชื่อที่ตรวจจากเล่ม'}})
        self.assertEqual(process.returncode,0,process.stderr)
        update = json.loads(output.read_text(encoding='utf-8'))['updates'][0]
        backup_path = self.root/update['backup']
        self.assertEqual(update['backup_sha256'],hashlib.sha256(backup_path.read_bytes()).hexdigest())
        # SQLite backup preserves logical data, not necessarily file-header bytes.
        with closing(open_readonly(backup_path)) as backup:
            self.assertEqual(backup.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(backup.execute('SELECT name_th FROM course').fetchone()[0],'การเขียนโปรแกรมเว็บ')
            self.assertEqual(backup.execute('SELECT count(*) FROM prerequisite').fetchone()[0],0)
        result = self.assistant.ask(self.registry,self.question)
        self.assertEqual(result['rows'][0]['name_th'],'ชื่อที่ตรวจจากเล่ม')
        self.assertEqual(result['rows'][0]['prerequisite_status'],'explicit_none')

    def test_conflicting_none_review_cannot_remove_existing_requirement(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute('INSERT INTO prerequisite VALUES(?,?,?,?,?)',('06066302','06066301','pre','DSBA.pdf',319))
            connection.commit()
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        process,_ = self.run_ingest({})
        self.assertNotEqual(process.returncode,0)
        self.assertIn('no destructive overwrite',process.stderr)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)

    def test_changed_source_blocks_review_without_modifying_database(self):
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        process,_ = self.run_ingest({'sha256':'incorrect'})
        self.assertNotEqual(process.returncode,0)
        self.assertIn('Source changed',process.stderr)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)


if __name__ == '__main__':
    unittest.main()
