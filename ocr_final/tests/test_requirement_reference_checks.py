"""Synthetic reference mutations must fail the verifier; no production answer labels."""
import unittest

from scripts.requirement_reference_checks import expected_references, references_match, frontend_references_match


class ReferenceChecksTests(unittest.TestCase):
    def setUp(self):
        self.label = {'program': 'FIXTURE', 'version': 1, 'regulation_year': 2,
                      'source_file': 'fixture.pdf', 'page': 10, 'book_page': 5}
        self.review = {'program': 'FIXTURE', 'version': 1, 'regulation_year': 2,
                       'source_file': 'fixture.pdf', 'pdf_page': 20, 'book_page': 15,
                       'rule_text': 'Synthetic approved partial rule', 'section': 'Fixture clause',
                       'review_scope': 'partial_rules'}
        self.expected = expected_references(self.label, [self.review])

    def test_baseline_and_approved_addition_both_required_in_any_order(self):
        self.assertTrue(references_match(list(reversed(self.expected)), self.expected))
        self.assertFalse(references_match(self.expected[:1], self.expected))
        self.assertFalse(references_match([self.expected[1]], self.expected))

    def test_duplicates_unapproved_pages_and_changed_text_fail(self):
        for mutation in ({**self.expected[1], 'page_number': 21},
                         {**self.expected[1], 'rule_text': 'Unapproved invented rule'}, self.expected[0]):
            self.assertFalse(references_match([self.expected[0], mutation], self.expected))
        self.assertFalse(references_match(self.expected + [self.expected[1]], self.expected))

    def test_other_curriculum_or_version_review_cannot_expand_expectations(self):
        self.assertEqual(len(expected_references(self.label, [{**self.review, 'version': 9}])), 1)
        self.assertEqual(len(expected_references(self.label, [{**self.review, 'program': 'OTHER'}])), 1)

    def test_frontend_must_cite_every_approved_page_and_printed_page(self):
        sources = [{'page': 10, 'book_page': 5, 'section': 'fixture.pdf baseline'},
                   {'page': 20, 'book_page': 15, 'section': 'fixture.pdf clause'}]
        self.assertTrue(frontend_references_match(sources, self.expected))
        self.assertFalse(frontend_references_match(sources[:1], self.expected))
        self.assertFalse(frontend_references_match([sources[0], {**sources[1], 'book_page': 14}], self.expected))
