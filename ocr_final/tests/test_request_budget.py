import unittest
from types import SimpleNamespace
from unittest.mock import patch
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL, REQUEST_DEADLINE


class RequestBudgetTests(unittest.TestCase):
    def service(self):
        model = object.__new__(QwenTextToSQL)
        model.config = SimpleNamespace(request_timeout=180, ollama_model='test')
        model.lab8b = SimpleNamespace(ollama_generate=lambda *a, **kw: '{}')
        return model

    def test_remaining_budget_not_reset_per_generation(self):
        model = self.service()
        calls = []
        model.lab8b.ollama_generate = lambda *a, **kw: calls.append(kw['timeout']) or '{}'
        token = REQUEST_DEADLINE.set(100)
        try:
            with patch('lab10_fastapi.curriculum_app.model_service.time.perf_counter', side_effect=[20, 20, 70, 70]):
                model._chat('one', {})
                model._chat('two', {})
            self.assertEqual(calls, [80, 30])
        finally:
            REQUEST_DEADLINE.reset(token)

    def test_expired_budget_cannot_generate(self):
        token = REQUEST_DEADLINE.set(10)
        try:
            with patch('lab10_fastapi.curriculum_app.model_service.time.perf_counter', return_value=20):
                with self.assertRaises(TimeoutError):
                    self.service()._chat('question', {})
        finally:
            REQUEST_DEADLINE.reset(token)

    def test_budget_reset_on_error(self):
        model = self.service()
        model._ask_with_budget = lambda *a: (_ for _ in ()).throw(ValueError('test'))
        with self.assertRaises(ValueError):
            model.ask(None, 'question')
        self.assertIsNone(REQUEST_DEADLINE.get())

    def test_generation_returned_after_deadline_is_not_accepted(self):
        token = REQUEST_DEADLINE.set(10)
        try:
            with patch('lab10_fastapi.curriculum_app.model_service.time.perf_counter', side_effect=[9,11]):
                with self.assertRaises(TimeoutError):self.service()._chat('question',{})
        finally:REQUEST_DEADLINE.reset(token)

    def test_expired_retrieval_cannot_open_sqlite(self):
        from pathlib import Path
        from lab10_fastapi.curriculum_app.database import open_readonly
        token = REQUEST_DEADLINE.set(0)
        try:
            with self.assertRaises(TimeoutError):open_readonly(Path('missing-is-not-the-cause.db'))
        finally:REQUEST_DEADLINE.reset(token)
