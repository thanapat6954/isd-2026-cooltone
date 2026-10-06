"""Regression checks for wrapped PowerShell verification output."""
import unittest
from scripts.verify_launcher_commands import normalize_cli_output


class LauncherVerificationTests(unittest.TestCase):
    def test_error_margin_and_wrap_do_not_hide_preservation_message(self):
        value = '| Different folder. No process\r\n     | was stopped.\r\n'
        self.assertIn('No process was stopped', normalize_cli_output(value))

    def test_plain_startup_output_is_preserved(self):
        value = 'Backend already running, database and configured model ready:'
        self.assertEqual(value, normalize_cli_output(value))

    def test_empty_output_is_not_a_success_message(self):
        self.assertEqual('', normalize_cli_output(' \r\n'))


if __name__ == '__main__':
    unittest.main()
