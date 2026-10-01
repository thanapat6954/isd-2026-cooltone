import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_a1_field_accuracy.py"
SPEC = importlib.util.spec_from_file_location("compare_a1_field_accuracy", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CompareA1FieldAccuracyTests(unittest.TestCase):
    def test_candidate_only_rows_are_never_scored(self):
        result = MODULE.compare([{
            "sample_id": "x",
            "program": "IT",
            "curriculum_version": 2565,
            "plan": "coop",
            "candidate": {"code": "06000001"},
            "ground_truth": {"code": "06000001"},
            "review_status": "candidate_only",
        }])
        self.assertEqual(result["approved_rows"], 0)
        self.assertIsNone(result["overall"]["fields"]["code"]["accuracy"])

    def test_approved_rows_score_direct_and_hour_fields(self):
        sample = {
            "sample_id": "x",
            "program": "IT",
            "curriculum_version": 2565,
            "plan": "coop",
            "candidate": {"code": "06000001", "credits": "3(2-2-5)"},
            "ground_truth": {"code": "06000001", "credits": "3(2-2-5)", "plan": "coop"},
            "review_status": "visually_verified",
        }
        result = MODULE.compare([sample])
        fields = result["overall"]["fields"]
        self.assertEqual(fields["code"]["accuracy"], 1.0)
        self.assertEqual(fields["lecture_hours"]["accuracy"], 1.0)
        self.assertEqual(fields["lab_hours"]["accuracy"], 1.0)
        self.assertEqual(fields["self_study_hours"]["accuracy"], 1.0)
        self.assertEqual(fields["plan"]["accuracy"], 1.0)

    def test_wrong_and_garbled_values_are_reported(self):
        sample = {
            "sample_id": "x",
            "program": "BIT",
            "curriculum_version": 2560,
            "plan": "no-coop",
            "candidate": {"name_th": "\uf700ผิด", "credits": "3(3-0-6)"},
            "ground_truth": {"name_th": "ชื่อถูก", "credits": "3(2-2-5)"},
            "review_status": "corrected_after_visual_review",
        }
        result = MODULE.compare([sample])
        self.assertEqual(result["overall"]["fields"]["name_th"]["accuracy"], 0.0)
        self.assertEqual(result["overall"]["fields"]["lecture_hours"]["accuracy"], 0.0)
        self.assertEqual(result["row_quality"]["wrong_row_count"], 1)
        self.assertEqual(result["row_quality"]["garbled_thai_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
