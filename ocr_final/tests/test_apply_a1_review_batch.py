import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "apply_a1_review_batch.py"
SPEC = importlib.util.spec_from_file_location("apply_a1_review_batch", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ApplyA1ReviewBatchTests(unittest.TestCase):
    def test_applies_verified_fields_and_override(self):
        review = {"samples": [{
            "sample_id": "x",
            "plan": "coop",
            "candidate": {"code": "1", "name_th": "bad"},
            "ground_truth": {"code": None, "name_th": None, "prerequisite": None},
            "review_status": "candidate_only",
        }]}
        batch = {
            "batch_id": "b",
            "copy_candidate_fields": ["code", "name_th"],
            "verified_fields": ["code", "name_th", "plan", "prerequisite"],
            "items": [{
                "sample_id": "x",
                "prerequisite": "2",
                "overrides": {"name_th": "good"},
                "evidence": ["book p.1"],
            }],
        }
        result = MODULE.apply_batch(review, batch)["samples"][0]
        self.assertEqual(result["ground_truth"]["code"], "1")
        self.assertEqual(result["ground_truth"]["name_th"], "good")
        self.assertEqual(result["ground_truth"]["plan"], "coop")
        self.assertEqual(result["ground_truth"]["prerequisite"], "2")
        self.assertEqual(result["review_status"], "corrected_after_visual_review")

    def test_rejects_unknown_sample(self):
        with self.assertRaises(ValueError):
            MODULE.apply_batch(
                {"samples": []},
                {"batch_id": "b", "items": [{"sample_id": "missing"}]},
            )


if __name__ == "__main__":
    unittest.main()
