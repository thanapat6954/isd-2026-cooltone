import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class GroundTruthLayoutTests(unittest.TestCase):
    def test_rewrite_both_path_forms_not_factual_source_names(self):
        module=load('organize_ground_truth')
        value='ROOT / "data" / "ground_truth" / "DSBA_ground_truth.json"; data/ground_truth/DSBA_ground_truth.json; source_file="DSBA_ground_truth.json"'
        rewritten=module.rewrite(value)
        self.assertIn('"source_reviews" / "DSBA-2565" / "master.json"',rewritten)
        self.assertIn('source_file="DSBA_ground_truth.json"',rewritten)

    def test_all_old_profiles_have_partial_labels_and_unique_terms(self):
        module=load('export_reviewed_term_labels')
        paths=sorted((ROOT/'data/ground_truth/evaluation').glob('*-2560/*-terms.json'))
        self.assertEqual(len(paths),6)
        self.assertEqual(sum(len(json.loads(p.read_text(encoding='utf-8'))['terms']) for p in paths),49)
        for path in paths:
            data=json.loads(path.read_text(encoding='utf-8'))
            module.validate(data)
            self.assertIn('prerequisites',data['unverified_fields'])
            altered=copy.deepcopy(data)
            altered['terms'][0]['source_file']='IT.pdf'
            with self.assertRaises(ValueError):module.validate(altered)

    def test_ingestion_and_eval_are_disjoint(self):
        module=load('organize_ground_truth')
        for target,purpose,*_ in module.LAYOUT.values():
            self.assertEqual(target.startswith('data/source_reviews/'),purpose in {'ingestion','relationships','approval'})
        runtime='\n'.join(p.read_text(encoding='utf-8') for p in (ROOT/'lab10_fastapi/curriculum_app').glob('*.py'))
        self.assertNotIn('data/ground_truth/evaluation',runtime)
        self.assertNotIn('versioned_eval_questions.json',runtime)

    def test_all_configured_flat_paths_exist_or_are_explicitly_unavailable(self):
        spec=importlib.util.spec_from_file_location('runner',ROOT/'run_lab8b.py')
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        self.assertEqual(sum(p['gt'] is None for p in runner.PROFILES.values()),8)
        for profile in runner.PROFILES.values():
            if profile['gt'] is not None:self.assertTrue(profile['gt'].is_file())

    def test_missing_source_or_duplicate_term_is_rejected(self):
        module=load('export_reviewed_term_labels')
        path=next((ROOT/'data/ground_truth/evaluation').glob('*-2560/*-terms.json'))
        data=json.loads(path.read_text(encoding='utf-8'))
        duplicated=copy.deepcopy(data)
        duplicated['terms'].append(duplicated['terms'][0])
        with self.assertRaises(ValueError):module.validate(duplicated)
        data['terms'][0]['source_sha256']=None
        with self.assertRaises(ValueError):module.validate(data)

    def test_source_qa_values_are_derived_from_ledger(self):
        module=load('export_reviewed_term_labels')
        for path in (ROOT/'data/ground_truth/evaluation').glob('*-2560/*-terms.json'):
            data=json.loads(path.read_text(encoding='utf-8'))
            qa=module.qa_labels(data)
            self.assertEqual(len(qa['groups'][0]['cases']),6)
            self.assertEqual(qa['groups'][0]['cases'][-1]['credits'],data['terms'][0]['printed_credits'])
            self.assertEqual(qa['groups'][0]['cases'][-1]['book_page'],data['terms'][0]['printed_page'])
            self.assertIn('NOT held-out',qa['purpose'])

    def test_field_labels_have_matching_approval_and_no_inferred_plan(self):
        import hashlib
        count=0
        for path in (ROOT/'data/ground_truth/evaluation').glob('*/reviewed-fields.json'):
            data=json.loads(path.read_text(encoding='utf-8'))
            self.assertIsNone(data['identity']['plan'])
            for label in data['labels']:
                evidence=label['evidence']
                self.assertEqual(hashlib.sha256((ROOT/evidence['approval']).read_bytes()).hexdigest(),evidence['approval_sha256'])
                self.assertTrue(evidence['pdf_page'])
                count+=1
        self.assertEqual(count,31)

if __name__=='__main__':unittest.main()
