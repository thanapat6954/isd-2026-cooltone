"""Evidence must preserve actual failures and reject changed or escaping artifacts."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.archive_evaluation import archive, verify, MANIFEST


class EvaluationArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.destination = self.root/'raw', self.root/'หลักฐาน'
        self.source.mkdir()
        self.jobs = [{'name': 'metadata', 'exit_code': 0}, {'name': 'audit', 'exit_code': 1}]
        summary = {'app_root': 'synthetic fixture', 'url': 'http://example.invalid', 'suite': 'All', 'jobs': self.jobs}
        (self.source/'summary.json').write_text(json.dumps(summary), encoding='utf-8-sig')
        (self.source/'REPORT.md').write_text('Synthetic failure report, not a production result', encoding='utf-8')
        (self.source/'native.stderr.log').write_text('ข้อความไทยจาก PowerShell', encoding='utf-16')

    def test_roundtrip_preserves_failure_and_original_bytes_with_verified_zip(self):
        before = {p.name: p.read_bytes() for p in self.source.iterdir()}
        result = archive(self.source, self.destination)
        self.assertEqual(result['observed_jobs'], self.jobs)
        self.assertEqual(result['verified_files'], 3)
        for name, payload in before.items():
            self.assertEqual((self.destination/name).read_bytes(), payload)
            self.assertEqual((self.source/name).read_bytes(), payload)
        self.assertEqual(verify(self.destination), result)

    def test_changed_result_is_not_accepted_as_original_evidence(self):
        archive(self.source, self.destination)
        (self.destination/'REPORT.md').write_text('Changed score', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'changed evidence'):
            verify(self.destination)

    def test_existing_destination_and_recursive_copy_are_refused(self):
        self.destination.mkdir()
        with self.assertRaises(FileExistsError):
            archive(self.source, self.destination)
        with self.assertRaisesRegex(ValueError, 'separate'):
            archive(self.source, self.source/'nested')

    def test_manifest_cannot_read_outside_the_evidence_folder(self):
        archive(self.source, self.destination)
        path = self.destination/MANIFEST
        document = json.loads(path.read_text(encoding='utf-8'))
        document['files'][0]['path'] = '../outside.json'
        path.write_text(json.dumps(document), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'escapes'):
            verify(self.destination)

    def test_database_is_not_copied_into_a_result_bundle(self):
        (self.source/'curriculum.db').write_bytes(b'synthetic database marker')
        with self.assertRaisesRegex(ValueError, 'must not include'):
            archive(self.source, self.destination)
        self.assertFalse(self.destination.exists())
