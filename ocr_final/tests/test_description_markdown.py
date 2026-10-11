import unittest
from scripts.parse_description_markdown import parse_descriptions


class DescriptionMarkdownTests(unittest.TestCase):
    def test_missing_prerequisite_is_unknown_and_no_plan_is_invented(self):
        row = parse_descriptions('00000001 ตัวอย่าง 3(2-2-5)\nEXAMPLE COURSE\n', 'synthetic.pdf', 5)[0]
        self.assertEqual(row['prerequisite_status'], 'unknown')
        self.assertIsNone(row['prerequisite_logic'])
        self.assertNotIn('semester', row)
        self.assertFalse(row['source_verified'])

    def test_none_and_multiple_prerequisites_remain_distinct(self):
        for raw, status in [('NONE', 'explicit_none'), ('00000002 and 00000003', 'required')]:
            row = parse_descriptions('00000001 ตัวอย่าง 3(2-2-5)\nEXAMPLE\nPREREQUISITE : '+raw+'\nคำอธิบาย\nEnglish description', 'synthetic.pdf', 5, 1)[0]
            self.assertEqual(row['prerequisite_status'], status)
            self.assertIsNone(row['prerequisite_logic'])
            self.assertEqual(row['description_th'], 'คำอธิบาย')
            self.assertEqual(row['printed_page_number'], 1)

    def test_alternatives_preserved_without_selecting_hours(self):
        row = parse_descriptions('00000001 ตัวอย่าง 3(3-0-6) หรือ 3(2-2-5)\nEXAMPLE', 'synthetic.pdf', 5)[0]
        self.assertIn('หรือ', row['credits_raw'])
        self.assertIsNone(row['credits'])

    def test_duplicate_sections_fail_loudly(self):
        with self.assertRaises(ValueError):
            parse_descriptions(('00000001 ตัวอย่าง 3(3-0-6)\nEXAMPLE\n')*2, 'synthetic.pdf', 5)
