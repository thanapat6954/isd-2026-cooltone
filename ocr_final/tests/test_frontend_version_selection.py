import unittest
from lab10_fastapi.curriculum_app.frontend_selection import validate_selected_year


class FrontendVersionSelectionTests(unittest.TestCase):
    def test_explicit_old_year_does_not_silently_search_latest(self):
        with self.assertRaisesRegex(ValueError,'ไม่ตรง'):
            validate_selected_year('หลักสูตร BIT 2560 ปี4เทอม2กี่หน่วยกิต',2565,'latest')
    def test_matching_year_and_no_year_remain_supported(self):
        validate_selected_year('IT 2565 วิชา06016422',2565,'latest')
        validate_selected_year('ปี2เทอม1กี่หน่วยกิต',2565,'latest')
    def test_explicit_comparison_and_all_versions_are_not_blocked(self):
        validate_selected_year('IT 2560 และ 2565 มีวิชาใดต่างกัน',2565,'all versions')
        validate_selected_year('วิชาใดมีในหลักสูตรเดิม แต่ไม่มีในหลักสูตรฉบับปรับปรุง',2565,'latest')
