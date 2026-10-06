"""Regression tests for actual model readiness and paired SQLite citations."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from dataclasses import replace

from lab10_fastapi.curriculum_app.config import settings
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, execute_readonly
from lab10_fastapi.curriculum_app.main import _frontend_sources, _source_quote
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
from lab10_fastapi.curriculum_app.query_planner import QueryPlan, deterministic_sql


class ReadinessAndCitationTests(unittest.TestCase):
    def test_running_ollama_without_configured_model_is_not_ready(self):
        service = QwenTextToSQL(replace(settings, ollama_model='qwen3:4b'), Mock())
        response = Mock()
        response.json.return_value = {'models': [{'name': 'unrelated:latest'}]}
        with patch('lab10_fastapi.curriculum_app.model_service.requests.get', return_value=response):
            self.assertFalse(service.available())
            response.json.return_value = {'models': [{'name': 'qwen3:4b'}]}
            self.assertTrue(service.available())

    def test_null_models_is_not_ready(self):
        response = Mock()
        response.json.return_value = {'models': None}
        with patch('lab10_fastapi.curriculum_app.model_service.requests.get', return_value=response):
            self.assertFalse(QwenTextToSQL(settings, Mock()).available())

    def test_invalid_tags_response_is_not_ready(self):
        service = QwenTextToSQL(settings, Mock())
        response = Mock()
        response.json.return_value = []
        with patch('lab10_fastapi.curriculum_app.model_service.requests.get', return_value=response):
            self.assertFalse(service.available())

    def test_pairing_is_preserved_across_nonmonotonic_appendix_folios(self):
        row = {'year': 2, 'credits': 36, 'source_pages': '200,30', 'source_printed_pages': '10,25',
               'page_evidence': json.dumps([
                   {'source_file': 'IT-60.pdf', 'page': 200, 'book_page': 10},
                   {'source_file': 'IT-60.pdf', 'page': 30, 'book_page': 25}])}
        result = _frontend_sources({'intent': 'year_credits', 'rows': [row]})
        self.assertEqual([(r['page'], r['book_page']) for r in result], [(200, 10), (30, 25)])
        self.assertTrue(all(r['section'].startswith('IT-60.pdf') for r in result))
        self.assertNotIn('None', result[0]['quote'])

    def test_unpaired_lists_do_not_fabricate_printed_pages(self):
        row = {'source_pages': '30,200', 'source_printed_pages': '25,10'}
        result = _frontend_sources({'rows': [row]})
        self.assertEqual([(r['page'], r['book_page']) for r in result], [(30, None), (200, None)])

    def test_bad_evidence_does_not_make_clickable_invalid_pages(self):
        row = {'page_evidence': json.dumps([{'page': -1}, {'page': '12'}, {'page': 12, 'book_page': 'x'}])}
        self.assertEqual(_frontend_sources({'rows': [row]})[0]['book_page'], None)
        self.assertEqual(len(_frontend_sources({'rows': [row]})), 1)

    def test_year_quote_is_not_a_semester_quote(self):
        self.assertEqual(_source_quote({'year': 2, 'credits': 36}), 'ปี 2 ทั้งปี รวม 36 หน่วยกิต')

    def test_all_live_programs_year_sql_preserves_database_page_pairs(self):
        registry = DatabaseRegistry(Path(os.getenv('CURRICULUM_TEST_ROOT', str(settings.database_root))))
        if not registry.active_programs:
            self.skipTest('Generated databases required for live read-only integration')
        for database in registry.active_programs:
            with self.subTest(profile=database.curriculum_name):
                sql = deterministic_sql(QueryPlan('year_credits', year=2), database)
                _, rows = execute_readonly(database, sql)
                self.assertTrue(rows)
                self.assertIn('page_evidence', rows[0])
                self.assertTrue(_frontend_sources({'intent': 'year_credits', 'rows': rows}))


if __name__ == '__main__':
    unittest.main()
