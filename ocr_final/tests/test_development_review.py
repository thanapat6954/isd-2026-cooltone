import unittest
from scripts.report_diverse_review import triage


class DevelopmentReviewTests(unittest.TestCase):
    def test_success_status_does_not_establish_correctness(self):
        self.assertEqual(triage({'status': 200, 'category': 'name_paraphrase', 'body': {'answer': 'some answer'}}), 'needs_substantive_review')

    def test_unrelated_program_fact_is_a_failure(self):
        case = {'status': 200, 'category': 'unsupported_description', 'body': {'answer': 'program name', 'sql': 'SELECT name_th FROM program'}}
        self.assertEqual(triage(case), 'unrelated_program_answer')

    def test_transport_failure_and_empty_answer_are_not_abstentions(self):
        self.assertEqual(triage({'status': 422, 'body': {}}), 'technical_failure')
        self.assertEqual(triage({'status': 200, 'body': {'answer': ''}}), 'empty_answer')
