import copy
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/apply_reviewed_plan_term.py'
SPEC = importlib.util.spec_from_file_location('reviewed_term', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReviewedTermTests(unittest.TestCase):
    def setUp(self):
        self.source = {'courses': [{'code': '06036086', 'year': 4, 'semester': 1,
                                    'source_file': 'test.pdf'}]}
        self.review = {'status': 'visually_verified', 'source_file': 'test.pdf',
                       'year': 4, 'semester': 2, 'pdf_page': 30, 'credits': 3,
                       'row_count': 1, 'rows': [{'code': 'xxxxxxxx', 'name_th': 'วิชาเลือกเสรี 1',
                                               'credits': '3(3-0-6)'}]}

    def test_preserves_original_and_unknown_prerequisite(self):
        before = copy.deepcopy(self.source)
        result = MODULE.apply_review(self.source, self.review)
        self.assertEqual(self.source, before)
        self.assertEqual(len(result['courses']), 2)
        self.assertIsNone(result['courses'][1]['prerequisite'])
        self.assertEqual(result['term_totals'][0]['row_count'], 1)

    def test_refuses_unverified_or_wrong_total(self):
        self.review['status'] = 'candidate_only'
        with self.assertRaises(ValueError):
            MODULE.apply_review(self.source, self.review)
        self.review['status'] = 'visually_verified'
        self.review['credits'] = 6
        with self.assertRaises(ValueError):
            MODULE.apply_review(self.source, self.review)

    def test_repeated_application_does_not_duplicate_rows(self):
        first = MODULE.apply_review(self.source, self.review)
        second = MODULE.apply_review(first, self.review)
        self.assertEqual(first['courses'], second['courses'])
        self.assertEqual(first['term_totals'], second['term_totals'])

    def test_explicit_alternatives_count_once_and_keep_individual_labels(self):
        self.review['rows'] = [
            {'code':'06036046','name_th':'สหกิจศึกษา','credits':'6(0-35-0)','alt_group':'choice'},
            {'code':'06036047','name_th':'สหกิจศึกษาต่างประเทศ','credits':'6(0-35-0)','alt_group':'choice'}]
        self.review.update(row_count=2, credits=6, printed_page=25)
        result = MODULE.apply_review(self.source, self.review)
        self.assertEqual(result['courses'][-1]['name_th'], 'สหกิจศึกษาต่างประเทศ')
        self.assertEqual(result['courses'][-1]['printed_page_number'],25)
        self.review['rows'][1]['credits'] = '3(3-0-6)'
        with self.assertRaises(ValueError):
            MODULE.apply_review(self.source,self.review)


if __name__ == '__main__':
    unittest.main()
