import unittest
from unittest.mock import patch
import requests
from fastapi import HTTPException
from lab10_fastapi.curriculum_app import main
from lab10_fastapi.curriculum_app.schemas import AskRequest,FrontendAskRequest


class TimeoutContractTests(unittest.TestCase):
    def test_unknown_intent_does_not_falsely_claim_model_use(self):
        value = {'answer': 'fixture', 'intent': 'unknown', 'rows': [], 'queries': []}
        with patch.object(main.model, 'ask', return_value=value):
            response = main.frontend_ask(FrontendAskRequest(question='fixture',curriculum='IT',version='latest'))
        self.assertEqual(response['model'], 'SQLite (deterministic renderer)')
        value['model_used'] = 'fixture-model'
        with patch.object(main.model, 'ask', return_value=value):
            response = main.frontend_ask(FrontendAskRequest(question='fixture',curriculum='IT',version='latest'))
        self.assertIn('fixture-model', response['model'])

    def test_both_timeout_types_have_consistent_route_responses(self):
        for error in (TimeoutError('expired'),requests.ReadTimeout('expired')):
            with self.subTest(error=type(error).__name__),patch.object(main.model,'ask',side_effect=error):
                with self.assertRaises(HTTPException) as found:main.ask(AskRequest(question='หลักสูตร IT'))
                self.assertEqual(found.exception.status_code,504)
                response=main.frontend_ask(FrontendAskRequest(question='หลักสูตร IT',curriculum='IT',version='latest'))
                self.assertEqual(response.status_code,504)
                self.assertIn('หมดเวลา',response.body.decode())
