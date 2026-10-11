import copy
import json
from pathlib import Path
import unittest
from scripts.export_partial_plan_labels import validate_partial, page_proofs


class PartialPlanLabelsTests(unittest.TestCase):
    def test_remaining_it_terms_balance_without_summing_tracks(self):
        path=Path(__file__).resolve().parents[1]/'data/ground_truth/evaluation/IT-2565/semester-observations-20261009-b.json'
        data=json.loads(path.read_text(encoding='utf-8'))
        for profile in data['profiles']:
            validate_partial(profile)
            self.assertEqual(len(profile['terms']),6)
            self.assertEqual(sum(t['printed_credits'] for t in profile['terms'])+36,129)
        self.assertEqual(data['specialization_groups']['multimedia']['year3_codes'][-1],'06016418')
        self.assertIn('ONE complete',data['counting_rule'])

    def test_multi_page_proof_never_guesses_offset(self):
        with self.assertRaisesRegex(ValueError,'printed folio'):
            page_proofs({'source_file':'IT.pdf','source_sha256':'hash'},
                        {'pdf_page':43,'printed_page':38,'pdf_pages':[42,43]},Path('missing-images'))

    def setUp(self):
        self.data=json.loads((Path(__file__).resolve().parents[1]/'data/ground_truth/evaluation/DSBA-2565/study-plan-observations-20261009.json').read_text(encoding='utf-8'))

    def test_reviewed_terms_balance_without_filling_unknown(self):
        for profile in self.data['profiles']:validate_partial(profile)
        self.assertEqual([len(p['terms']) for p in self.data['profiles']],[8,7])
        self.assertIsNone(self.data['profiles'][1]['printed_total'])

    def test_alternatives_not_counted_twice(self):
        profile=copy.deepcopy(self.data['profiles'][1])
        profile['terms'][-1]['rows'][1].pop()
        with self.assertRaises(ValueError):validate_partial(profile)

    def test_wrong_total_fails(self):
        profile=copy.deepcopy(self.data['profiles'][0])
        profile['printed_total']=135
        with self.assertRaises(ValueError):validate_partial(profile)

    def test_it_plan_identity_is_explicit_and_partial(self):
        path=Path(__file__).resolve().parents[1]/'data/ground_truth/evaluation/IT-2565/study-plan-observations-20261009.json'
        data=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual({p['plan'] for p in data['profiles']},{'coop','no-coop'})
        for profile in data['profiles']:
            validate_partial(profile)
            self.assertIsNone(profile['printed_total'])
            self.assertEqual(len(profile['terms']),2)
