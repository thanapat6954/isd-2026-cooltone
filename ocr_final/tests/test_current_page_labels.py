import copy
import json
import unittest
from pathlib import Path
from scripts.export_current_page_labels import validate


class CurrentPageLabelsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).resolve().parents[1] / 'data/ground_truth/evaluation/current-page-observations.json').read_text(encoding='utf-8'))

    def test_all_reviewed_profiles(self):
        for profile in self.data['profiles']:
            validate(profile)

    def test_no_double_count_alternatives(self):
        profile = copy.deepcopy(self.data['profiles'][1])
        profile['terms'][-1]['rows'][1].pop()
        with self.assertRaises(ValueError):
            validate(profile)

    def test_duplicate_semester_rejected(self):
        profile = copy.deepcopy(self.data['profiles'][0])
        profile['terms'][1]['semester'] = 1
        with self.assertRaises(ValueError):
            validate(profile)

    def test_wrong_program_total_rejected(self):
        profile = copy.deepcopy(self.data['profiles'][2])
        profile['printed_total'] = 126
        with self.assertRaises(ValueError):
            validate(profile)
