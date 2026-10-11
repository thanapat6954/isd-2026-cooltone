"""Combined schedule codes must not copy one option's identity to the others."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('master_option_lab8', ROOT/'scr/ocr_system/lab8b_curriculum_db.py')
LAB8 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LAB8
SPEC.loader.exec_module(LAB8)


class MasterAlternativeTests(unittest.TestCase):
    def fixture(self):
        return {'program':'Synthetic', 'courses_master':[
            {'code':'12345678','name_th':'ตัวเลือกหนึ่ง','name_en':'FIRST OPTION',
             'credits':'6(0-35-0)','prerequisite':'11111111'},
            {'code':'87654321','name_th':'ตัวเลือกสอง','name_en':'SECOND OPTION',
             'credits':'6(0-35-0)','prerequisite':'22222222'}],
            'curriculum_schedule':[{'course_code':'12345678 หรือ 87654321',
                'year':4,'semester':2,'applicable_plans':['coop']}]}

    def test_each_option_retains_names_prerequisites_and_shared_group(self):
        source = self.fixture()
        original = copy.deepcopy(source)
        result, _ = LAB8.convert_lab7b(source, program_id='SYNTHETIC', years=4, total_credits=30)
        self.assertEqual(source, original)
        courses = {r['code']:r for r in result['courses']}
        plan = {r['code']:r for r in result['plan']}
        for row in source['courses_master']:
            for field in ('name_th','name_en'):
                self.assertEqual(courses[row['code']][field],row[field])
                self.assertEqual(plan[row['code']][field],row[field])
        self.assertEqual(plan['12345678']['alt_group'],plan['87654321']['alt_group'])
        self.assertEqual({(r['code'],r['requires']) for r in result['prerequisites']},
                         {('12345678','11111111'),('87654321','22222222')})

    def test_missing_second_prerequisite_is_not_borrowed_from_first(self):
        source = self.fixture()
        source['courses_master'][1]['prerequisite'] = None
        result, _ = LAB8.convert_lab7b(source, program_id='SYNTHETIC', years=4, total_credits=30)
        self.assertEqual([r['code'] for r in result['prerequisites']],['12345678'])

    def test_single_master_row_still_denormalizes(self):
        source = self.fixture()
        source['curriculum_schedule'][0]['course_code'] = '12345678'
        source['curriculum_schedule'][0]['name_en'] = 'EXPLICIT SCHEDULE NAME'
        result, _ = LAB8.convert_lab7b(source, program_id='SYNTHETIC', years=4, total_credits=30)
        self.assertEqual(result['plan'][0]['name_en'],'EXPLICIT SCHEDULE NAME')

    def test_missing_alternative_master_does_not_borrow_any_identity(self):
        source = self.fixture()
        source['courses_master'].pop()
        source['courses_master'][0]['description_th'] = 'First option only'
        result, _ = LAB8.convert_lab7b(source, program_id='SYNTHETIC', years=4, total_credits=30)
        second = next(r for r in result['courses'] if r['code'] == '87654321')
        self.assertEqual(second['name_th'], '87654321')
        self.assertIsNone(second['name_en'])
        self.assertIsNone(second['description_th'])
        self.assertEqual([r['code'] for r in result['prerequisites']], ['12345678'])
        second_plan = next(r for r in result['plan'] if r['code'] == '87654321')
        self.assertIsNone(second_plan['name_th'])


if __name__ == '__main__':
    unittest.main()
