"""SQLite evidence fixtures are synthetic and never production answer keys."""
from copy import deepcopy
import unittest
from lab10_fastapi.curriculum_app.study_plan import build_study_plan, study_plan_text


class StudyPlanTests(unittest.TestCase):
    def setUp(self):
        self.evidence = {}
        for plan, pdf, book in [('coop',41,36), ('no-coop',34,29)]:
            self.evidence['IT-2565-'+plan] = {
                'terms': [{'id':1,'source_file':'IT.pdf','version':2565,'plan':plan,
                           'program_id':'IT-'+plan,'year':2,'semester':2,'printed_total':6,
                           'note':'เลือกเพียงกลุ่มเดียว','source_sha256':'fixture',
                           'review_method':'fixture','pages':[{'pdf_page':pdf,'printed_page':book}]}],
                'tracks': {1:[{'track_id':'a','label':'กลุ่มซอฟต์แวร์','aliases':['ซอฟต์แวร์']},
                              {'track_id':'b','label':'กลุ่มเครือข่าย','aliases':['เครือข่าย']}]},
                'items': {i:{'term_id':1,'shared':i==1} for i in range(1,4)},
                'members': {1:[],2:[{'track_id':'a'}],3:[{'track_id':'b'}]}}

    def rows(self,plan='coop'):
        return [{'id':i,'code':f'{i:08}','name_th':f'วิชา {i}','credits':3,'year':2,'semester':2,
                 'source_file':'IT.pdf','page_number':41 if plan=='coop' else 34,
                 'printed_page_number':36 if plan=='coop' else 29,
                 '_source':{'program_id':'IT-'+plan,'curriculum_name':'IT-2565-'+plan,
                            'plan':plan,'curriculum_version':2565}} for i in range(1,4)]

    def build(self,rows=None,question='',**kwargs):
        return build_study_plan(rows or self.rows(),question,self.evidence,**kwargs)

    def test_separate_plan_and_tracks(self):
        payload,rows=self.build(self.rows()+self.rows('no-coop'))
        self.assertEqual(len(payload['cards']),2)
        self.assertEqual([s['title'] for s in payload['cards'][0]['sections']],['รายวิชาร่วมทุกกลุ่ม','กลุ่มซอฟต์แวร์','กลุ่มเครือข่าย'])
        self.assertEqual([r['printed_page_number'] for r in rows],[36]*3+[29]*3)
        self.assertIn('รายวิชาในภาคการศึกษานี้เหมือนกัน',' '.join(payload['cards'][0]['notes']))

    def test_track_selection_keeps_shared(self):
        _,rows=self.build(question='แขนงซอฟต์แวร์')
        self.assertEqual([r['code'] for r in rows],['00000001','00000002'])

    def test_missing_evidence_fails_loudly(self):
        payload,_=self.build(self.rows()[:2])
        self.assertIn('plan_item 3',' '.join(payload['cards'][0]['notes']))
        self.assertIsNone(payload['cards'][0]['printed_total'])

    def test_no_runtime_json_fallback(self):
        payload,_=build_study_plan(self.rows(),'',None)
        self.assertFalse(payload['cards'][0]['reviewed'])
        self.assertIsNone(payload['cards'][0]['printed_total'])

    def test_version_isolation(self):
        rows=self.rows()
        for row in rows: row['_source']['curriculum_version']=2560
        payload,_=self.build(rows)
        self.assertFalse(payload['cards'][0]['reviewed'])

    def test_general_placeholder_not_malformed(self):
        row=self.rows()[0]
        row.update(code='ELEC-SLOT-01',raw_code='90xxxxxx',name_th='วิชาเลือกเสรี 1')
        payload,_=build_study_plan([row],'',{})
        self.assertEqual(payload['cards'][0]['sections'][0]['title'],'วิชาเลือกเสรี')

    def test_multiple_track_membership_not_shared(self):
        self.evidence['IT-2565-coop']['members'][2].append({'track_id':'b'})
        payload,_=self.build()
        self.assertEqual([len(s['rows']) for s in payload['cards'][0]['sections']],[1,1,2])

    def test_no_review_preserves_raw_alternatives_and_provenance(self):
        rows=self.rows()[:1]; rows[0]['credits_raw']='3(3-0-6) หรือ 3(2-2-5)'
        payload,out=build_study_plan(rows,'',{})
        self.assertEqual(out[0]['credits_raw'],rows[0]['credits_raw'])
        self.assertEqual(out[0]['_source'],rows[0]['_source'])
        self.assertIn('หรือ 3(2-2-5)',study_plan_text(payload))

    def test_unreviewed_page_cannot_receive_facts(self):
        rows=self.rows()
        for row in rows: row['page_number']=99
        _,out=self.build(rows)
        self.assertTrue(all(not row['_study_context']['reviewed'] for row in out))

    def test_filtered_query_does_not_claim_total(self):
        payload,_=self.build(self.rows()[:1],required_only=True)
        self.assertIsNone(payload['cards'][0]['printed_total'])
        self.assertNotIn('ยังไม่ครบ',' '.join(payload['cards'][0]['notes']))

    def test_distinct_wildcards_never_collapse(self):
        rows=[dict(self.rows()[0],id=i,code='ELEC-SLOT',raw_code='xxxxxxxx',name_th=f'วิชาเลือกเสรี {i}') for i in (1,2)]
        payload,_=build_study_plan(rows,'',{})
        self.assertEqual(len(payload['cards'][0]['sections'][0]['rows']),2)

    def test_plain_text_preserves_or_alternative(self):
        rows=self.rows()[:2]
        for row in rows: row['alt_group']='pair'
        payload,_=build_study_plan(rows,'',{})
        self.assertIn('ชุดตัวเลือก “หรือ”',study_plan_text(payload))

    def test_factual_row_values_never_changed(self):
        before=self.rows(); _,after=self.build(deepcopy(before))
        for a,b in zip(before,after):
            self.assertEqual(a,{k:v for k,v in b.items() if k in a})

    def test_db_member_display_name_only(self):
        self.evidence['IT-2565-coop']['members'][2][0]['display_name_th']='ชื่อจากตาราง SQLite'
        payload,_=self.build()
        self.assertEqual(payload['cards'][0]['sections'][1]['rows'][0]['name_th'],'ชื่อจากตาราง SQLite')


if __name__=='__main__': unittest.main()
