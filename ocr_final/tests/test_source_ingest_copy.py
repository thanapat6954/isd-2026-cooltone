import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from scripts.apply_reviewed_plan_term import apply_review
from scripts.prepare_source_ingest import prepare


class SourceIngestCopyTests(unittest.TestCase):
    def test_reviewed_term_can_span_two_approved_pdf_pages(self):
        review = {'status':'visually_verified','source_file':'IT.pdf','pdf_page':36,'printed_page':31,
                  'pdf_pages':[35,36],'year':3,'semester':2,'credits':3,'row_count':1,
                  'rows':[{'code':'060164xx','credits':'3(3-0-6)','page_number':35,'printed_page_number':30}]}
        original = {'courses':[]}
        result = apply_review(original,review)
        self.assertEqual(result['courses'][0]['page_number'],35)
        self.assertEqual(result['courses'][0]['printed_page_number'],30)
        self.assertEqual(original,{'courses':[]})

    def test_unreviewed_row_page_rejected(self):
        review = {'status':'visually_verified','source_file':'IT.pdf','pdf_page':36,'printed_page':31,
                  'year':3,'semester':2,'credits':3,'row_count':1,
                  'rows':[{'code':'060164xx','credits':'3(3-0-6)','page_number':99}]}
        with self.assertRaises(ValueError):
            apply_review({'courses':[]},review)

    def test_output_must_not_overwrite_input(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'original.json'
            path.write_text('{}',encoding='utf-8')
            with self.assertRaises(ValueError):
                prepare(path,Path(folder)/'book.pdf',Path(folder)/'review.json','it-coop',path)
            self.assertEqual(path.read_text(encoding='utf-8'),'{}')

    def test_every_production_term_balances_independently(self):
        root=Path(__file__).resolve().parents[1]
        count=0
        for path in (root/'data/source_reviews').glob('*-plan-corrections.json'):
            for reviews in json.loads(path.read_text(encoding='utf-8'))['profiles'].values():
                for review in reviews:
                    if review.get('kind') == 'field_correction':
                        continue
                    apply_review({'courses':[]},review)
                    count+=1
        self.assertEqual(count,24)  # Includes the magnified DSBA-2560 no-coop Year4/S1 review.

    def test_bit_coop_page33_review_is_idempotent_and_preserves_unknowns(self):
        root = Path(__file__).resolve().parents[1]
        approvals = json.loads((root/'data/source_reviews/BIT-2565-plan-corrections.json').read_text(encoding='utf-8'))
        review = next(r for r in approvals['profiles']['bit-2565-coop'] if r['pdf_page'] == 33)
        original = {'courses':[{'code':'9664xxxx','year':3,'semester':1,'source_file':'BIT-65.pdf'}]}
        first = apply_review(original, review)
        second = apply_review(first, review)
        self.assertEqual(first['courses'], second['courses'])
        self.assertEqual(first['term_totals'], second['term_totals'])
        self.assertEqual(original['courses'][0]['code'], '9664xxxx')
        slot = next(r for r in first['courses'] if r.get('slot') == 'LANGUAGE_ELECTIVE')
        self.assertEqual(slot['code'], '96644xxx')
        self.assertIn(' หรือ ', slot['credits'])
        self.assertEqual(slot['printed_page_number'], 28)
        self.assertIsNone(slot.get('prerequisite'))
        self.assertIsNone(slot.get('category'))

    def test_field_correction_is_unique_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            pdf=root/'book.pdf'
            pdf.write_bytes(b'approved source')
            original=root/'original.json'
            data={'courses':[{'code':'90XXXXX','year':4,'semester':1,'page_number':33,'source_file':'book.pdf','name_th':'unchanged'}]}
            original.write_text(json.dumps(data),encoding='utf-8')
            review=root/'review.json'
            review.write_text(json.dumps({'source_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
                'profiles':{'profile':[{'kind':'field_correction','status':'visually_verified',
                'source_file':'book.pdf','pdf_page':33,'printed_page':28,'match':{'code':'90XXXXX','year':4,'semester':1,'source_file':'book.pdf','page_number':33},
                'changes':{'code':'90xxxxxx'}}]}}),encoding='utf-8')
            output=root/'new.json'
            prepare(original,pdf,review,'profile',output)
            self.assertEqual(json.loads(original.read_text()),data)
            self.assertEqual(json.loads(output.read_text())['courses'][0]['name_th'],'unchanged')
            self.assertEqual(json.loads(output.read_text())['courses'][0]['code'],'90xxxxxx')
            data['courses'].append(dict(data['courses'][0]))
            original.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(ValueError):
                prepare(original,pdf,review,'profile',root/'duplicate.json')
