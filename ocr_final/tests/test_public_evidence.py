"""Public report copies redact paths without changing factual numeric fields."""
import unittest
from scripts.export_public_evidence import redact, sanitize_json


class PublicEvidenceTests(unittest.TestCase):
    def test_nested_numbers_and_original_objects_are_preserved(self):
        original = {'count': 14, 'passed': True, 'rows': [{'page': 6, 'path': 'C:/Users/thana/AppData/Local/Temp/run'}]}
        result = sanitize_json(original)
        self.assertEqual(result['count'], 14)
        self.assertTrue(result['passed'])
        self.assertEqual(result['rows'][0]['page'], 6)
        self.assertEqual(result['rows'][0]['path'], '<TEMP>/run')
        self.assertIn('C:/Users', original['rows'][0]['path'])

    def test_windows_and_escaped_paths_are_redacted(self):
        for value in ('C:\\Users\\thana\\file', 'C:\\\\Users\\\\thana\\\\file'):
            self.assertNotIn('thana', redact(value))

    def test_thai_course_name_is_unchanged(self):
        self.assertEqual(redact('วิชาการเขียนโปรแกรม'), 'วิชาการเขียนโปรแกรม')


if __name__ == '__main__':
    unittest.main()
