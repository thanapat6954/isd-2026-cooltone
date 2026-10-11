"""Evidence-type guards are generic and do not encode probe answers."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from lab10_fastapi.curriculum_app.query_planner import QueryPlan, deterministic_sql
from lab10_fastapi.curriculum_app.model_service import fallback_evidence_need, fallback_gap, literal_search_terms, literal_database_names, relationship_sql, QwenTextToSQL


class FallbackRelevanceTests(unittest.TestCase):
    def test_catalog_without_placement_never_generates_semester_totals(self):
        db = SimpleNamespace(has=lambda table, *columns: table == 'courses' and columns == ('course_code',))
        for intent in ('semester_credits', 'year_credits'):
            self.assertIn('LIMIT 0', deterministic_sql(QueryPlan(intent, year=2, semester=1), db))

    def test_empty_selected_plan_is_disclosed_without_claiming_absence(self):
        from lab10_fastapi.curriculum_app.model_service import relationship_coverage_gap
        selected = [SimpleNamespace(curriculum_name='fixture-coop'), SimpleNamespace(curriculum_name='fixture-no-coop')]
        rows = [{'requires': '00000001', '_source': {'curriculum_name': 'fixture-no-coop'}}]
        gap = relationship_coverage_gap(rows, selected)
        self.assertIn('fixture-coop', gap)
        self.assertIn('ไม่อนุมาน', gap)
        rows.append({'requires': '00000002', '_source': {'curriculum_name': 'fixture-coop'}})
        self.assertEqual(relationship_coverage_gap(rows, selected), '')

    def test_model_usage_is_request_local_not_inferred_from_intent(self):
        from lab10_fastapi.curriculum_app.model_service import MODEL_CALLS
        model = QwenTextToSQL.__new__(QwenTextToSQL)
        model.config = SimpleNamespace(request_timeout=60, ollama_model='fixture-model')
        def generated(*args):
            MODEL_CALLS.set(MODEL_CALLS.get() + 1)
            return {'cache_hit': False}
        with patch.object(model, '_ask_with_budget', side_effect=generated):
            self.assertEqual(model.ask(None, 'fixture')['model_used'], 'fixture-model')
        with patch.object(model, '_ask_with_budget', return_value={'cache_hit': True}):
            self.assertIsNone(model.ask(None, 'fixture')['model_used'])
        self.assertEqual(MODEL_CALLS.get(), 0)

    def test_multiple_stored_pairs_require_clarification(self):
        model = QwenTextToSQL.__new__(QwenTextToSQL)
        rows = [{'code': code, 'requires': required, 'kind': 'pre', '_source': {'curriculum_name': 'TEST'}}
                for code, required in [('00000002', '00000001'), ('00000004', '00000003')]]
        answer = model.summarize('รายวิชาสองตัวนี้ต่อกันยังไง', QueryPlan('unknown'), rows, [])
        self.assertIn('00000002', answer)
        self.assertIn('00000004', answer)
        self.assertIn('โปรดระบุ', answer)

    def test_explicit_conjoined_mentions_do_not_depend_on_model_topic_sampling(self):
        from lab10_fastapi.curriculum_app.model_service import literal_course_mentions
        self.assertEqual(literal_course_mentions('วิชาโครงงานหนึ่งกับโครงงานสองต่อกันยังไง มีพรีรีเควสิทมั้ย'), ['โครงงานหนึ่ง', 'โครงงานสอง'])
        self.assertEqual(literal_course_mentions('วิชาที่ต้องเรียนก่อนมีอะไรบ้าง'), [])

    def test_ordinal_candidates_keep_number_and_do_not_assert_relationship(self):
        from lab10_fastapi.curriculum_app.query_planner import course_name_matches
        self.assertTrue(course_name_matches('โครงงานปัญญาประดิษฐ์ 1', 'โครงงานหนึ่ง'))
        self.assertFalse(course_name_matches('โครงงานปัญญาประดิษฐ์ 2', 'โครงงานหนึ่ง'))
        self.assertFalse(course_name_matches('โครงงาน 11', 'โครงงานหนึ่ง'))
        self.assertEqual(literal_search_terms('โครงงานสองต่อกันยังไง มีพรีรีเควสิทมั้ย', ['โครงงานสองต่อกัน', 'พรีรีเควสิท']), ['โครงงานสอง'])

    def test_informal_sequence_and_prerequisite_are_relationship_requests(self):
        for question in ('วิชาสองตัวนี้ต่อกันยังไง', 'มีพรีรีเควสิทมั้ย', 'course prereq chain'):
            self.assertEqual(fallback_evidence_need(question), 'relationship')

    def test_written_course_ordinals_match_digits_without_changing_other_names(self):
        from lab10_fastapi.curriculum_app.query_planner import normalize_course_name
        self.assertEqual(normalize_course_name('โครงงานหนึ่ง'), normalize_course_name('โครงงาน 1'))
        self.assertEqual(normalize_course_name('โครงงานสอง'), normalize_course_name('โครงงาน 2'))
        self.assertEqual(normalize_course_name('ข้อมูลเบื้องต้น'), 'ข้อมูลเบื้องต้น')

    def test_future_teaching_and_assessment_do_not_retrieve_unrelated_facts(self):
        model = QwenTextToSQL.__new__(QwenTextToSQL)
        db = SimpleNamespace(has=lambda table, *columns: table == 'course')
        for question in ('ขอหัวข้อสอบ', 'ภาษาอะไรที่อาจารย์จะสอนเทอมหน้า', 'exam topics for next semester'):
            self.assertEqual(fallback_evidence_need(question), 'teaching_assessment')
            self.assertIn('WHERE 0', model.make_sql(question, QueryPlan('unknown'), db))
            self.assertIn('ไม่มีหลักฐาน', fallback_gap(question, [], []))

    def test_current_course_description_is_not_a_future_teaching_request(self):
        self.assertEqual(fallback_evidence_need('อธิบายเนื้อหาวิชาภาษาโปรแกรม'), 'description')

    def test_missing_course_table_is_a_technical_failure_not_unrelated_evidence(self):
        model = QwenTextToSQL.__new__(QwenTextToSQL)
        database = SimpleNamespace(has=lambda *args: False, schema_family='lab8b', curriculum_name='TEST')
        with self.assertRaisesRegex(ValueError, 'course'):
            model.make_sql('อธิบายเนื้อหาวิชา', QueryPlan('unknown'), database)

    def test_comparison_returns_both_requested_codes_and_traceable_delta(self):
        model = QwenTextToSQL.__new__(QwenTextToSQL)
        rows = [{'code': code, 'name_th': 'fixture', 'credits': credit, '_source': {'curriculum_name': 'TEST'}}
                for code, credit in [('00000001', 3), ('00000002', 6)]]
        answer = model._ground_answer(QueryPlan('course_detail', compare=True), rows, '')
        self.assertIn('00000001', answer)
        self.assertIn('00000002', answer)
        self.assertIn('6 - 3 = 3', answer)

    def test_legacy_catalog_list_excludes_uncoded_ocr_fragments(self):
        database = SimpleNamespace(has=lambda table, *columns: table == 'courses')
        sql = deterministic_sql(QueryPlan('course_list'), database)
        self.assertIn('course_code IS NOT NULL', sql)
        self.assertIn("TRIM(course_code) <> ''", sql)

    def test_explicit_database_names_survive_missing_model_topic(self):
        database = SimpleNamespace(has=lambda *args: True)
        with patch('lab10_fastapi.curriculum_app.model_service.execute_readonly', side_effect=[(None, [{'name_th': 'แคลคูลัส 1'}, {'name_th': 'แคลคูลัส 2'}]), (None, [])]):
            self.assertEqual(literal_database_names('แคลคูลัส 2กับแคลคูลัส 1', database), ['แคลคูลัส 1', 'แคลคูลัส 2'])

    def test_planning_guarantee_cannot_use_unrelated_names(self):
        model = QwenTextToSQL.__new__(QwenTextToSQL)
        rows = [{'name_th': 'unrelated fixture', '_source': {'curriculum_name': 'TEST'}}]
        answer = model.summarize('รับรองการลงทะเบียนได้แน่นอน', SimpleNamespace(intent='unknown'), rows, [])
        self.assertNotIn('unrelated fixture', answer)
        self.assertIn('ยังรับรอง', answer)

    def test_program_summary_cannot_answer_content(self):
        rows = [{'total_credits': 129, 'years': 4}]
        self.assertIsNotNone(fallback_gap('อธิบายเนื้อหาวิชา', rows, [{'row_index': 0, 'fields': ['total_credits', 'years']}]))

    def test_description_is_required_not_course_name(self):
        rows = [{'name_th': 'ชื่อ', 'description_th': 'ข้อความจากฐาน'}]
        self.assertIsNotNone(fallback_gap('course content', rows, [{'row_index': 0, 'fields': ['name_th']}]))
        self.assertIsNone(fallback_gap('course content', rows, [{'row_index': 0, 'fields': ['description_th']}]))

    def test_description_does_not_assert_relationship(self):
        rows = [{'description_th': 'ข้อความจากฐาน'}]
        self.assertIsNotNone(fallback_gap('ความสัมพันธ์ของรายวิชา', rows, [{'row_index': 0, 'fields': ['description_th']}]))

    def test_missing_relation_is_not_none(self):
        self.assertIsNotNone(fallback_gap('related courses', [{'requires': None}], [{'row_index': 0, 'fields': ['requires']}]))

    def test_no_guard_on_direct_fact(self):
        self.assertIsNone(fallback_evidence_need('วิชา 12345678 มีกี่หน่วยกิต'))

    def test_only_literal_topics_not_model_filters(self):
        question = 'หลักสูตร IT 2565 สหกิจ อธิบายระบบคอมพิวเตอร์'
        self.assertEqual(literal_search_terms(question, ['ระบบคอมพิวเตอร์', 'ไม่อยู่ในคำถาม', '2565', 'สหกิจ', 'หลักสูตร IT 2565']), ['ระบบคอมพิวเตอร์'])

    def test_relationship_requires_both_matched_endpoints(self):
        sql = relationship_sql("SELECT code FROM course WHERE INSTR(name_th, 'หัวข้อ') > 0 LIMIT 100")
        self.assertIn('code IN (SELECT code FROM course', sql)
        self.assertIn('AND requires IN (SELECT code FROM course', sql)
        self.assertNotIn('LIMIT 100', sql)
        self.assertIsNone(relationship_sql('SELECT years FROM program'))

    def test_page_pair_comes_from_selected_database(self):
        database = SimpleNamespace(has=lambda table, *columns: table == 'plan_item')
        execution = SimpleNamespace(database=database, rows=[{'source_file': 'book.pdf', 'page_number': 34}], citation_queries=[])
        with patch('lab10_fastapi.curriculum_app.model_service.execute_readonly', return_value=(SimpleNamespace(sql='validated'), [{'printed_page_number': 29}])) as query:
            QwenTextToSQL._attach_page_pairs(execution)
        self.assertIs(query.call_args.args[0], database)
        self.assertEqual(execution.rows[0]['printed_page_number'], 29)
        self.assertEqual(len(execution.citation_queries), 1)

    def test_conflicting_folios_remain_unknown(self):
        database = SimpleNamespace(has=lambda table, *columns: table == 'plan_item')
        execution = SimpleNamespace(database=database, rows=[{'source_file': 'book.pdf', 'page_number': 34}], citation_queries=[])
        with patch('lab10_fastapi.curriculum_app.model_service.execute_readonly', return_value=(SimpleNamespace(sql='validated'), [{'printed_page_number': 29}, {'printed_page_number': 30}])):
            QwenTextToSQL._attach_page_pairs(execution)
        self.assertNotIn('printed_page_number', execution.rows[0])

    def test_ambiguous_content_lists_database_candidates(self):
        model = QwenTextToSQL.__new__(QwenTextToSQL)
        rows = [{'code': '00000001', 'name_th': 'โครงงาน 1', 'description_th': None, '_source': {'curriculum_name': 'TEST'}},
                {'code': '00000002', 'name_th': 'โครงงาน 2', 'description_th': None, '_source': {'curriculum_name': 'TEST'}}]
        answer = model.summarize('อธิบายเนื้อหาโครงงาน', SimpleNamespace(intent='unknown'), rows, [])
        self.assertIn('00000001 โครงงาน 1', answer)
        self.assertIn('00000002 โครงงาน 2', answer)
        self.assertIn('โปรดระบุ', answer)
        self.assertIn('คำอธิบายที่ขาด', answer)


if __name__ == '__main__':
    unittest.main()
