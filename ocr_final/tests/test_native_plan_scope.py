"""Extraction ambiguity and capability boundaries, using synthetic source cells."""
import unittest
from types import SimpleNamespace

from scripts.source_native import bilingual_groups, CODE, font_decoder, shared_placeholder_names, specialization_cell, explicit_course_choice
from lab10_fastapi.curriculum_app.build_scope import contract, supports_plan_question, PLAN_CAPABILITIES


class NativeSourceTests(unittest.TestCase):
    def test_choice_can_be_printed_between_names_not_only_codes(self):
        self.assertTrue(explicit_course_choice('12345678\n12345679','ชื่อ ก\nFIRST OPTION หรือ\nชื่อ ข\nSECOND OPTION'))
        self.assertTrue(explicit_course_choice('12345678 หรือ 12345679','ชื่อ'))
        self.assertFalse(explicit_course_choice('12345678\n12345679','กลุ่มวิชา\nชื่อ ก\nFIRST OPTION\nชื่อ ข\nSECOND OPTION'))
        self.assertFalse(explicit_course_choice('12345678\n12345679','ชื่อ ก\nDESIGN OR\nIMPLEMENTATION\nชื่อ ข\nSECOND OPTION'))

    def test_geometric_group_heading_preserves_whole_bundle_and_hours(self):
        def row(text,y):return {'text':text,'bbox':[0,y,100,y+1]}
        codes=[row('12345678',20),row('12345679',40)]
        names=[row('กลุ่มวิชาด้านทดสอบ',5),row('ชื่อ ก',19),row('FIRST',30),
               row('ชื่อ ข',39),row('SECOND',50)]
        credits=[row('3(3-0-6)',20),row('3(2-2-5)',40)]
        result=specialization_cell([codes,names,credits],names)
        self.assertEqual([r['name_en'] for r in result['courses']],['FIRST','SECOND'])
        self.assertEqual(result['courses'][1]['credits'],'3(2-2-5)')
        self.assertIn('not independent OR slots',result['selection_status'])
        with self.assertRaises(ValueError):specialization_cell([codes,names,credits[:1]],names)
        with self.assertRaises(ValueError):specialization_cell([codes,names,credits],names[1:])

    def test_names_in_merged_cell_remain_associated_in_order(self):
        groups = bilingual_groups('ชื่อทางเลือก ก\nFIRST OPTION\nNAME หรือ\nชื่อทางเลือก ข\nSECOND OPTION NAME')
        self.assertEqual(groups, [{'name_th':'ชื่อทางเลือก ก','name_en':'FIRST OPTION NAME'},
                                  {'name_th':'ชื่อทางเลือก ข','name_en':'SECOND OPTION NAME'}])

    def test_older_branch_heading_is_a_whole_bundle_not_a_course_name(self):
        def line(text,y):return {'text':text,'bbox':[0,y,100,y+1]}
        codes=[line('12345678',20),line('12345679',40)]
        names=[line('แขนงวิชาทดสอบ',5),line('ชื่อ ก',20),line('FIRST',30),
               line('ชื่อ ข',40),line('SECOND',50)]
        hours=[line('3(3-0-6)',20),line('3(2-2-5)',40)]
        group=specialization_cell([codes,names,hours],names)
        self.assertEqual(group['label'],'แขนงวิชาทดสอบ')
        self.assertEqual(group['courses'][0]['name_th'],'ชื่อ ก')
        self.assertEqual(group['courses'][1]['code'],'12345679')

    def test_missing_second_name_cannot_be_copied_from_first(self):
        with self.assertRaises(ValueError):
            bilingual_groups('ชื่อ ก\nFIRST NAME\nชื่อ ข')

    def test_connector_inside_one_name_is_source_text(self):
        self.assertEqual(bilingual_groups('วิชาเลือก 1 หรือ\nกลุ่มวิชาที่ 1-4\nELECTIVE 1 OR COURSE GROUP 1-4'),
                         [{'name_th':'วิชาเลือก 1 หรือ กลุ่มวิชาที่ 1-4',
                           'name_en':'ELECTIVE 1 OR COURSE GROUP 1-4'}])

    def test_unresolved_font_identity_cannot_use_reviewed_mapping(self):
        decode=font_decoder(SimpleNamespace(),{'format':1,'kind':'reviewed-font-encoding','fonts':[]})
        page=SimpleNamespace(get_fonts=lambda **kw:[])
        with self.assertRaises(ValueError):
            decode(page,{'text':'\uf70a','font':'Unknown'})
        self.assertEqual(decode(page,{'text':'ordinary source text','font':'Unknown'}),'ordinary source text')

    def test_placeholder_lengths_are_not_padded_or_truncated(self):
        self.assertEqual(CODE.findall('xxxxxxx xxxxxxxxxxx 1234xxxx xxxxxxxx'), ['1234xxxx','xxxxxxxx'])

    def test_shared_placeholder_keeps_three_paired_labels_in_one_slot(self):
        labels=[{'name_th':f'ชื่อ {i}','name_en':f'LABEL {i}'} for i in range(3)]
        display,pairs=shared_placeholder_names(['12345xxx'],labels,['3 (3-0-6)','3 (2-2-5)'],'3 (3-0-6) หรือ 3 (2-2-5)')
        self.assertEqual(len(display),1)
        self.assertEqual(pairs,labels)
        self.assertIn('LABEL 2',display[0]['name_en'])

    def test_shared_names_cannot_be_invented_for_real_code_or_different_credits(self):
        labels=[{'name_th':'ก','name_en':'A'},{'name_th':'ข','name_en':'B'}]
        for codes,patterns,text in [(['12345678'],['3 (3-0-6)'],'3 (3-0-6)'),
                                      (['12345xxx'],['3 (3-0-6)','4 (2-2-5)'],'หรือ'),
                                      (['12345xxx'],['3 (3-0-6)','3 (2-2-5)'],'')]:
            with self.assertRaises(ValueError):shared_placeholder_names(codes,labels,patterns,text)

    def test_scope_cannot_claim_full_capabilities(self):
        invalid={'contract':{'kind':'academic-plan-only','partial':True,'profiles':['one'],
                             'capabilities':PLAN_CAPABILITIES+['program_rules']}}
        with self.assertRaises(ValueError):
            contract(invalid)
        self.assertEqual(contract(None)['expected_catalogs'],14)

    def test_scope_denies_rules_and_descriptions_even_with_course_detail_intent(self):
        plan=SimpleNamespace(intent='course_detail')
        self.assertFalse(supports_plan_question(plan,'ขอคำอธิบายรายวิชา 12345678'))
        self.assertFalse(supports_plan_question(plan,'วิชานี้มี prerequisite หรือไม่'))
        self.assertTrue(supports_plan_question(plan,'วิชา 12345678 ชื่ออะไร มีกี่หน่วยกิต'))


if __name__=='__main__':
    unittest.main()
