"""Compound summaries retain SQLite names and alternative-safe arithmetic."""
import json
import unittest


class QualifiedCourseListIntentTests(unittest.TestCase):
    def test_qualified_course_nouns_remain_lists(self):
        from lab10_fastapi.curriculum_app.query_planner import detect_intent
        for noun in ('วิชาเลือก', 'วิชาบังคับ'):
            plan = detect_intent(f'ปี 3 ภาค 1 มี{noun}อะไรบ้าง แสดงหมวดวิชา')
            self.assertEqual(plan.intent, 'course_list')
from types import SimpleNamespace
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
from lab10_fastapi.curriculum_app.query_planner import QueryPlan, detect_intent, deterministic_sql


class CompoundTotalsTests(unittest.TestCase):
    def test_whole_bundle_breakdown_counts_one_complete_bundle(self):
        items=[['00000001',3,None,'common','3(3-0-6)',None,None]]
        for bundle,values in [('a',[2,4]),('b',[1,5])]:
            items += [['00000002',credit,None,'choice','',bundle,bundle] for credit in values]
        row={'year':2,'semester':2,'credits':9,'calculation_rows':json.dumps(items)}
        answer=QwenTextToSQL._ground_answer(QueryPlan('semester_credits'),[row],'')
        self.assertIn('3 + 6 = 9',answer)
        self.assertIn('หนึ่งชุดทั้งกลุ่ม',answer)
        self.assertNotIn('= 15',answer)
        items[-1][1]=4;row['calculation_rows']=json.dumps(items)
        answer=QwenTextToSQL._ground_answer(QueryPlan('semester_credits'),[row],'')
        self.assertIn('ยังยืนยันการคำนวณ',answer)
        self.assertNotIn('การคำนวณ:',answer)
    def test_older_study_view_reads_fidelity_from_same_sqlite_row(self):
        base = {'id', 'year', 'semester', 'code', 'name_th', 'name_en', 'credits', 'source_file', 'page_number', 'ctype'}
        schemas = {'v_study_plan': base, 'plan_item': base | {'raw_code', 'code_pattern', 'is_placeholder', 'elective_type'}}
        db = SimpleNamespace(has=lambda table, *columns: set(columns) <= schemas.get(table, set()))
        sql = deterministic_sql(QueryPlan('course_list', year=3, semester=1), db)
        for field in ('raw_code', 'code_pattern', 'is_placeholder', 'elective_type'):
            self.assertIn(f'pi.{field} FROM plan_item pi WHERE pi.id=v_study_plan.id', sql)
    def test_credit_format_list_is_not_an_aggregate_request(self):
        plan = detect_intent('ปี 3 ภาค 1 มีวิชาเลือกอะไรบ้าง แสดงรหัส ชื่อและรูปแบบหน่วยกิต')
        self.assertEqual(plan.intent, 'course_list')
        self.assertEqual(plan.semester, 1)
        self.assertTrue(plan.elective_only)
        self.assertEqual(detect_intent('ปี 3 ภาค 1 มีวิชาอะไรบ้างและรวมกี่หน่วยกิต').intent, 'semester_credits')
    def test_names_and_calculation_cannot_be_replaced_by_terse_total(self):
        rows = [{'year': 3, 'semester': 1, 'credits': 6,
                 'calculation_rows': json.dumps([
                     ['00000001', 3, None, 'ชื่อหนึ่ง'],
                     ['00000002', 3, 'choice', 'ชื่อสอง'],
                     ['00000003', 3, 'choice', 'ชื่อสาม']]),
                 '_source': {'curriculum_name': 'fixture'}}]
        answer = QwenTextToSQL._ground_answer(QueryPlan('semester_credits'), rows, '6 หน่วยกิต')
        for name in ('ชื่อหนึ่ง', 'ชื่อสอง', 'ชื่อสาม'):
            self.assertIn(name, answer)
        self.assertIn('3 + 3 = 6', answer)
        self.assertNotIn('3 + 3 + 3', answer)

    def test_older_calculation_rows_do_not_invent_names(self):
        row = {'credits': 3, 'calculation_rows': '[["ELEC-SLOT",3,null]]'}
        answer = QwenTextToSQL._ground_answer(QueryPlan('semester_credits'), [row], '')
        self.assertIn('ไม่ระบุชื่อในฐานข้อมูล', answer)
        self.assertIn('ELEC-SLOT', answer)

    def test_raw_placeholder_and_credit_alternatives_remain_visible(self):
        row = {'credits': 3, 'calculation_rows': json.dumps([
            ['99999xxx', 3, None, 'วิชาเลือก', '3(3-0-6) หรือ 3(2-2-5)']])}
        answer = QwenTextToSQL._ground_answer(QueryPlan('semester_credits'), [row], '')
        self.assertIn('99999xxx', answer)
        self.assertIn('3(3-0-6) หรือ 3(2-2-5)', answer)
