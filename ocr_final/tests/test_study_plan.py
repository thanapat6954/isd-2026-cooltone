"""Relationship fixtures use source data, never production question answers."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from lab10_fastapi.curriculum_app.study_plan import build_study_plan, review_fingerprint, study_plan_text


class StudyPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'data/input').mkdir(parents=True)
        (self.root / 'data/ground_truth').mkdir(parents=True)
        self.pdf = self.root / 'data/input/IT.pdf'
        self.pdf.write_bytes(b'fixture source')
        self.review = {'sources': {'IT.pdf': hashlib.sha256(self.pdf.read_bytes()).hexdigest()},
            'review_method': 'fixture', 'track_sets': {'t': [
                {'id': 'a', 'label': 'กลุ่มซอฟต์แวร์', 'aliases': ['ซอฟต์แวร์']},
                {'id': 'b', 'label': 'กลุ่มเครือข่าย', 'aliases': ['เครือข่าย']}]},
            'terms': [{'source_file': 'IT.pdf', 'version': 2565, 'year': 2, 'semester': 2,
                'pages': {'coop': [[41, 36]], 'no-coop': [[34, 29]]}, 'track_set': 't',
                'shared_codes': ['00000001'], 'track_codes': {'a': ['00000002'], 'b': ['00000003']},
                'printed_total': 6, 'note': 'เลือกเพียงกลุ่มเดียว'}]}
        self.save()

    def save(self):
        (self.root / 'data/ground_truth/study_plan_relationships.json').write_text(json.dumps(self.review), encoding='utf-8')

    def rows(self, plan='coop'):
        return [{'code': f'{i:08}', 'name_th': f'วิชา {i}', 'credits': 3, 'year': 2, 'semester': 2,
                 'source_file': 'IT.pdf', 'page_number': 41 if plan == 'coop' else 34,
                 '_source': {'program_id': 'IT-' + plan, 'curriculum_name': 'IT-2565-' + plan,
                             'plan': plan, 'curriculum_version': 2565}} for i in range(1,4)]

    def test_separate_plan_and_tracks(self):
        payload, rows = build_study_plan(self.rows() + self.rows('no-coop'), '', self.root)
        self.assertEqual(len(payload['cards']), 2)
        self.assertEqual([s['title'] for s in payload['cards'][0]['sections']], ['รายวิชาร่วมทุกกลุ่ม', 'กลุ่มซอฟต์แวร์', 'กลุ่มเครือข่าย'])
        self.assertEqual([r['printed_page_number'] for r in rows], [36]*3 + [29]*3)
        self.assertIn('รายวิชาในภาคการศึกษานี้เหมือนกัน', ' '.join(payload['cards'][0]['notes']))
        self.assertNotIn('IT-2565-coop:', study_plan_text(payload))

    def test_track_selection_keeps_shared(self):
        payload, rows = build_study_plan(self.rows(), 'แขนงซอฟต์แวร์', self.root)
        self.assertEqual([r['code'] for r in rows], ['00000001', '00000002'])
        self.assertEqual(len(payload['cards'][0]['sections']), 2)

    def test_missing_review_members_fail_loudly(self):
        payload, _ = build_study_plan(self.rows()[:2], '', self.root)
        self.assertIn('00000003', ' '.join(payload['cards'][0]['notes']))

    def test_source_hash_mismatch_does_not_apply(self):
        before = review_fingerprint(self.root)
        self.pdf.write_bytes(b'changed source')
        payload, rows = build_study_plan(self.rows(), '', self.root)
        self.assertFalse(payload['cards'][0]['reviewed'])
        self.assertNotIn('printed_page_number', rows[0])
        self.assertNotEqual(before, review_fingerprint(self.root))

    def test_version_isolation(self):
        rows = self.rows()
        for row in rows: row['_source']['curriculum_version'] = 2560
        payload, rows = build_study_plan(rows, '', self.root)
        self.assertFalse(payload['cards'][0]['reviewed'])

    def test_general_placeholder_not_malformed(self):
        rows = self.rows()[:1]
        rows[0].update(code='ELEC-SLOT-01', raw_code='90xxxxxx', name_th='วิชาเลือกเสรี 1')
        payload, _ = build_study_plan(rows, '', self.root)
        self.assertEqual(payload['cards'][0]['sections'][0]['title'], 'วิชาเลือกเสรี')

    def test_multiple_track_membership_not_shared(self):
        self.review['terms'][0]['track_codes']['b'].append('00000002')
        self.save()
        payload, _ = build_study_plan(self.rows(), '', self.root)
        sections = payload['cards'][0]['sections']
        self.assertEqual([len(s['rows']) for s in sections], [1, 1, 2])

    def test_no_review_preserves_raw_alternatives_and_provenance(self):
        (self.root / 'data/ground_truth/study_plan_relationships.json').unlink()
        rows = self.rows()[:1]
        rows[0].update(credits_raw='3(3-0-6) หรือ 3(2-2-5)', alt_group='pair', category='เลือก')
        payload, annotated = build_study_plan(rows, '', self.root)
        self.assertEqual(annotated[0]['credits_raw'], rows[0]['credits_raw'])
        self.assertEqual(annotated[0]['_source'], rows[0]['_source'])
        self.assertIn('หรือ 3(2-2-5)', study_plan_text(payload))

    def test_unreviewed_page_cannot_receive_review_facts(self):
        rows = self.rows()
        for row in rows: row['page_number'] = 99
        payload, annotated = build_study_plan(rows, '', self.root)
        self.assertTrue(all(not row['_study_context']['reviewed'] for row in annotated))
        self.assertTrue(all(section['kind'] != 'track' for section in payload['cards'][0]['sections']))

    def test_filtered_required_query_does_not_claim_complete_term(self):
        payload, _ = build_study_plan(self.rows()[:1], '', self.root, required_only=True)
        self.assertIsNone(payload['cards'][0]['printed_total'])
        self.assertNotIn('ยังขาด', ' '.join(payload['cards'][0]['notes']))

    def test_distinct_wildcard_slots_never_collapse(self):
        rows = self.rows()[:1] * 2
        rows = [dict(r, code='ELEC-SLOT', raw_code='xxxxxxxx', name_th=f'วิชาเลือกเสรี {i}') for i, r in enumerate(rows, 1)]
        payload, _ = build_study_plan(rows, '', self.root)
        self.assertEqual(len(payload['cards'][0]['sections'][0]['rows']), 2)

    def test_plain_text_preserves_or_alternative(self):
        rows = self.rows()[:2]
        for row in rows: row['alt_group'] = 'pair'
        self.review['terms'] = []; self.save()
        payload, _ = build_study_plan(rows, '', self.root)
        self.assertIn('ชุดตัวเลือก “หรือ”', study_plan_text(payload))


if __name__ == '__main__': unittest.main()
