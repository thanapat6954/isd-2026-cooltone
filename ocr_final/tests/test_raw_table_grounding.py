import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('raw_table_lab7', Path(__file__).resolve().parents[1]/'scr/ocr_system/lab7b_curriculum.py')
lab7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab7)


class RawTableGroundingTests(unittest.TestCase):
    def test_multiple_codes_in_rowspan_split_without_borrowed_names(self):
        text = '<table><tr><td rowspan="2">12345678 87654321</td><td>FIRST COURSE</td><td>3(0-9-0)</td></tr><tr><td>SECOND COURSE</td><td>3(3-0-6)</td></tr></table>'
        result = lab7.normalize_merged_code_cells(text)
        self.assertIn('<td>12345678</td><td>FIRST COURSE', result)
        self.assertIn('<td>87654321</td><td>SECOND COURSE', result)
        self.assertEqual(result.count('<tr>'), 2)
        self.assertEqual(lab7.normalize_merged_code_cells(result), result)

    def test_alternatives_and_incomplete_groups_are_not_split(self):
        for codes, following in [('12345678 หรือ 87654321', '<tr><td>SECOND</td><td>3(3-0-6)</td></tr>'), ('12345678 87654321', '')]:
            text = f'<tr><td rowspan="2">{codes}</td><td>FIRST</td><td>3(0-9-0)</td></tr>{following}'
            self.assertEqual(lab7.normalize_merged_code_cells(text), text)
    def test_invalid_english_and_invented_none_use_only_raw_row(self):
        text = 'ปีที่ 1 ภาคการศึกษาที่ 1<table><tr><td>12345678</td><td>ชื่อไทย FOUNDATION ENGLISH 1</td><td>3(3-0-6)</td></tr></table>'
        row = {'code': '12345678', 'name_en': '3(3-0-6', 'prerequisite': 'ไม่มี'}
        lab7._ground_plan_table_fields(row, text)
        self.assertEqual(row['name_en'], 'FOUNDATION ENGLISH 1')
        self.assertIsNone(row['prerequisite'])

    def test_never_borrows_next_course_title_or_infers_missing_title(self):
        text = 'ปีที่ 1 ภาคการศึกษาที่ 1<table><td>12345678</td><td>ชื่อไทย</td><td>87654321</td><td>OTHER COURSE</td></table>'
        row = {'code': '12345678', 'name_en': '3(3-0-6)'}
        lab7._ground_plan_table_fields(row, text)
        self.assertIsNone(row['name_en'])

    def test_explicit_prerequisite_and_valid_title_preserved(self):
        row = {'code': '12345678', 'name_en': 'COURSE TITLE', 'prerequisite': '87654321'}
        lab7._ground_plan_table_fields(row, 'ปีที่ 1 ภาคการศึกษาที่ 1<table>วิชาบังคับก่อน</table>')
        self.assertEqual(row['prerequisite'], '87654321')
        self.assertEqual(row['name_en'], 'COURSE TITLE')
