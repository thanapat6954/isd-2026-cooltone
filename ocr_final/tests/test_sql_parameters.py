"""Binding and constraint checks stay separate from SQL execution."""
import unittest
from types import SimpleNamespace
from lab10_fastapi.curriculum_app.sql_parameters import BoundSQL, constraint_sql
from lab10_fastapi.curriculum_app.database import SqlValidationError
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL, _parse_json_object, SQL_SCHEMA
from lab10_fastapi.curriculum_app.query_planner import detect_intent, QueryPlan


class BindingTests(unittest.TestCase):
    def test_elective_synonym_is_column_and_intent_scoped(self):
        db = SimpleNamespace(program_id='fixture')
        plan = QueryPlan('course_list', year=3, semester=1, elective_only=True)
        valid = "SELECT code FROM v_plan WHERE year=3 AND semester=1 AND ctype IN ('เลือก','elective')"
        QwenTextToSQL._validate_plan_filters('ปี 3 ภาค 1 มีวิชาเลือกอะไรบ้าง', plan, db, valid)
        for invalid_plan, sql in [(QueryPlan('course_list', year=3, semester=1), valid),
                (plan, valid + " AND name_en='elective'")]:
            with self.assertRaises(SqlValidationError):
                QwenTextToSQL._validate_plan_filters('ปี 3 ภาค 1 มีวิชาอะไรบ้าง', invalid_plan, db, sql)

    def test_surplus_bindings_are_not_silently_discarded(self):
        with self.assertRaisesRegex(SqlValidationError, 'markers=\\[\\], keys='):
            constraint_sql('SELECT code FROM course', {'code': '00000001'})
    def test_course_filter_has_field_semantics_after_binding(self):
        db = SimpleNamespace(program_id='IT-coop')
        for value in ('%2560%', '%'):
            with self.assertRaises(SqlValidationError):
                QwenTextToSQL._validate_plan_filters('หลักสูตรฉบับ 2560', QueryPlan('unknown'), db,
                    constraint_sql('SELECT code FROM course WHERE code LIKE ?', [value]))
        QwenTextToSQL._validate_plan_filters('วิชา 06016323', QueryPlan('unknown'), db,
            constraint_sql('SELECT code FROM course WHERE code=?', ['06016323']))

    def test_optional_model_bindings_survive_json_parser(self):
        value = _parse_json_object('{"sql":"SELECT code FROM course WHERE code=?","parameters":["00000001"]}', SQL_SCHEMA)
        self.assertEqual(value['parameters'], ['00000001'])
        self.assertIn("'00000001'", constraint_sql(value['sql'], value['parameters']))

    def test_invalid_optional_binding_type_rejected(self):
        with self.assertRaises(ValueError):
            _parse_json_object('{"sql":"SELECT code FROM course","parameters":"wrong"}', SQL_SCHEMA)

    def test_quotes_are_not_markers(self):
        self.assertEqual(constraint_sql("SELECT '?' WHERE code=?", ["a'b"]), "SELECT '?' WHERE code='a''b'")

    def test_named_bindings_and_repeated_marker(self):
        self.assertEqual(constraint_sql('SELECT :x, :x', {'x': 3}), 'SELECT 3, 3')

    def test_invalid_bindings_fail_closed(self):
        for sql, values in [('SELECT ?', []), ('SELECT :x', {'y': 1}), ('SELECT ?', [float('nan')]), ('SELECT ?1', [2])]:
            with self.assertRaises(SqlValidationError):
                constraint_sql(sql, values)

    def test_bound_filter_is_validated_not_hidden(self):
        db = SimpleNamespace(program_id='IT-coop')
        sql = BoundSQL('SELECT code FROM plan_item WHERE year=?', [4])
        with self.assertRaises(SqlValidationError):
            QwenTextToSQL._validate_plan_filters('ปี 2', QueryPlan('course_list', year=2), db, constraint_sql(sql, sql.parameters))

    def test_function_word_is_not_a_course_name(self):
        question = 'วิชาที่มีวิชาบังคับก่อนมากกว่าหนึ่งตัวต้องผ่านทั้งหมดหรือเลือกตัวเดียวได้'
        self.assertEqual(detect_intent(question).intent, 'prerequisite_catalog')
        self.assertNotEqual(detect_intent(question).search_term, 'ที่')

    def test_name_topic_preserved(self):
        plan = detect_intent('อยากเรียนเขียนโปรแกรม มีวิชาชื่อใกล้เคียงกันอะไรบ้าง')
        self.assertEqual(plan.intent, 'course_search')
        self.assertEqual(plan.search_term, 'เขียนโปรแกรม')

    def test_version_comparison_does_not_mix_programs(self):
        rows = [{'code': '00000001', 'name_en': 'fixture', 'credits': 3,
                 '_source': {'program_id': program, 'plan': 'coop', 'curriculum_version': year}}
                for program, year in [('IT-2560-coop', 2560), ('DSBA-coop', 2565)]]
        answer, _ = QwenTextToSQL._version_facts(rows)
        self.assertIn('ยังเปรียบเทียบไม่ได้', answer)
