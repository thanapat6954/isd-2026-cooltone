"""Dependency guards must detect production inputs and file-set changes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_handoff_checks import dependency_snapshot


class HandoffDependencyTests(unittest.TestCase):
    def test_source_review_edit_addition_and_deletion_invalidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app, repo = root / 'live', root / 'repo'
            review = app / 'data/source_reviews/shared/rules.json'
            review.parent.mkdir(parents=True)
            review.write_text('{}', encoding='utf-8')
            with patch('scripts.run_handoff_checks.DatabaseRegistry') as registry:
                registry.return_value.databases = []
                original = dependency_snapshot(app, repo)
                self.assertIn(str(review.resolve()), original)
                review.write_text('{"reviewed":true}', encoding='utf-8')
                changed = dependency_snapshot(app, repo)
                self.assertNotEqual(original, changed)
                added = repo / 'data/source_reviews/new.json'
                added.parent.mkdir(parents=True)
                added.write_text('{}', encoding='utf-8')
                self.assertNotEqual(changed, dependency_snapshot(app, repo))
                review.unlink()
                self.assertNotIn(str(review.resolve()), dependency_snapshot(app, repo))

    def test_build_configuration_and_evaluation_are_locked_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app, repo = root / 'live', root / 'repo'
            files = [app / 'run_lab8b.py', repo / 'requirements.txt',
                     repo / 'data/ground_truth/evaluation/labels.json']
            for item in files:
                item.parent.mkdir(parents=True, exist_ok=True)
                item.write_text('{}', encoding='utf-8')
            with patch('scripts.run_handoff_checks.DatabaseRegistry') as registry:
                registry.return_value.databases = []
                snapshot = dependency_snapshot(app, repo)
                self.assertEqual(set(snapshot), {str(item.resolve()) for item in files})


if __name__ == '__main__':
    unittest.main()
