import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "make_eval_summary.py"
ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("make_eval_summary", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class EvalSummaryTests(unittest.TestCase):
    def test_missing_nodes_are_na_not_zero(self):
        data = {"degraded": {"heldout": {"correct": 1, "total": 2, "mean_seconds": 1.013}}}
        text = MODULE.generate(data)
        self.assertIn("1/2 (50.0%)", text)
        self.assertIn("n/a", text)
        self.assertNotIn("OCR F1 | 0.0%", text)
        MODULE.audit(text, data)

    def test_injection_is_idempotent(self):
        data = {"demo": {"heldout": {"correct": 1, "total": 1, "accuracy": 1.0}}}
        section = MODULE.generate(data)
        once = MODULE.inject("# Project\n", section)
        twice = MODULE.inject(once, section)
        self.assertEqual(once, twice)
        self.assertEqual(once.count(MODULE.START), 1)
        self.assertEqual(once.count(MODULE.END), 1)

    def test_null_is_not_converted_to_zero(self):
        self.assertEqual(MODULE.pct(None), "n/a")
        self.assertEqual(MODULE.number(None), "n/a")
        self.assertEqual(MODULE.get({"x": None}, "x", "y"), None)

    def test_generated_prose_uses_thai_wording(self):
        data = {"demo": {"heldout": {"correct": 1, "total": 1, "accuracy": 1.0}}}
        text = MODULE.generate(data)
        for banned in (
            "System Capabilities", "Current Vulnerabilities", "Executive Summary",
            "Real Error Samples", "Known Issues & Next Steps", "To update this summary",
        ):
            self.assertNotIn(banned, text)
        self.assertIn(MODULE.STRINGS["section_title"], text)
        self.assertIn(MODULE.STRINGS["rerun"], text)

    def test_recorded_error_patterns_and_splits(self):
        data = json.loads((ROOT / "work" / "robustness_summary.json").read_text(encoding="utf-8"))
        text = MODULE.generate(data)
        self.assertIn("row misalignment 3/21", text)
        self.assertIn("`it-coop/06016422`", text)
        self.assertIn("`it-no-coop/06016422`", text)
        self.assertIn("`it-no-coop/06016423`", text)
        self.assertIn("truncation / merged row / label bleed-in 4/21", text)
        self.assertIn("`ai/06046443 หรือ 06046444`", text)
        self.assertIn("`it-coop/06016421`", text)
        self.assertIn("ระดับการสะกด 14/21", text)
        self.assertIn("pred=None", text)
        self.assertIn("4/25", text)
        self.assertIn("other 1/25", text)
        self.assertIn("`dsba-no-coop/9064xxxx`", text)
        self.assertIn("รวม 25/25 รายการ", text)
        self.assertIn("ถูกตัดเหลือเพียงรูปแบบเดียว 10/13", text)
        self.assertIn("wrong pattern 3/13", text)
        self.assertEqual(text.count("JSON เก็บได้ไม่เกิน 5 รายการต่อ attribute ต่อ profile"), 1)

    def test_tldr_uses_top_ranked_issue(self):
        data = json.loads((ROOT / "work" / "robustness_summary.json").read_text(encoding="utf-8"))
        text = MODULE.generate(data)
        lines = text.splitlines()
        tldr = next(line for line in lines if line.startswith("- **จุดที่ต้องปรับปรุง:**"))
        section8 = next(line for line in lines if line.startswith("1. **"))
        self.assertIn("`prereq`", tldr)
        self.assertIn("`prereq`", section8)
        self.assertIn("หัวข้อ 8", tldr)
        self.assertLessEqual(len(tldr.splitlines()), 2)

    def test_ground_truth_review_candidates_are_cautious(self):
        data = json.loads((ROOT / "work" / "robustness_summary.json").read_text(encoding="utf-8"))
        text = MODULE.generate(data)
        for case in (
            "dsba-coop/06026205", "dsba-coop/06066304", "dsba-coop/90641001",
            "it-coop/06066301", "it-coop/06016412",
            "it-no-coop/06066301", "it-no-coop/06016412",
        ):
            self.assertIn(case, text)
        self.assertIn("ต้องตรวจด้วยตนเองกับ source PDF", text)
        self.assertIn("หาก OCR ถูกต้อง ให้แก้ GT แล้วรัน evaluation ใหม่", text)
        self.assertIn("ยังไม่สรุปว่า GT ผิด", text)
        no_coop_samples = data["dsba-no-coop"]["ocr"]["attributes"]["name_th"]["error_samples"]
        self.assertFalse(any(
            MODULE.is_gt_review_candidate("dsba-no-coop", sample)
            for sample in no_coop_samples
        ))
        self.assertIn("Ground-truth review candidates:** `name_th` จำนวน 7 รายการ", text)

    def test_profiles_heading_is_numbered(self):
        data = json.loads((ROOT / "work" / "robustness_summary.json").read_text(encoding="utf-8"))
        text = MODULE.generate(data)
        self.assertIn("### 1.1 profile ที่ใช้ประเมิน", text)

    def test_dsba_no_coop_details_list_all_recorded_samples(self):
        data = json.loads((ROOT / "work" / "robustness_summary.json").read_text(encoding="utf-8"))
        text = MODULE.generate(data)
        marker = MODULE.STRINGS["dsba_no_coop_samples_summary"]
        block = text.split(f"<summary>{marker}</summary>", 1)[1].split("</details>", 1)[0]
        rows = [
            line for line in block.splitlines()
            if line.startswith("| ") and not line.startswith("| key |") and not line.startswith("| :---")
        ]
        self.assertEqual(len(rows), 15)
        self.assertIn("| 90642033 | LAW FOR NEW GENERATION | None | other |", block)
        self.assertIn("| 06026xxx | ELECTIVE IN DATA SCIENCE 1", block)
        self.assertNotIn("…", block)
        for sample_class in ("spelling", "truncation", "other"):
            self.assertIn(f"| {sample_class} |", block)

    def test_missing_baseline_note_is_generated_from_json(self):
        data = json.loads((ROOT / "work" / "robustness_summary.json").read_text(encoding="utf-8"))
        text = MODULE.generate(data)
        self.assertIn("baseline_v1 report", text)
        self.assertIn("`dsba-no-coop`", text)
        modified = json.loads(json.dumps(data))
        modified["ai"].pop("baseline_v1", None)
        modified_text = MODULE.generate(modified)
        note = next(line for line in modified_text.splitlines() if "baseline_v1 report" in line)
        self.assertIn("`ai`", note)
        self.assertIn("`dsba-no-coop`", note)

    def test_profile_display_names_and_dsba_mapping(self):
        data = json.loads((ROOT / "work" / "robustness_summary.json").read_text(encoding="utf-8"))
        text = MODULE.generate(data)
        self.assertTrue(MODULE.dsba_mapping_confirmed())
        self.assertIn("| `dsba-coop` | DSBA | coop | `work/lab8b_dsba_coop` | มี |", text)
        self.assertIn("| `dsba-no-coop` | DSBA | no-coop | `work/lab8b_dsba_no_coop` | มี |", text)
        self.assertNotIn("| `dsba` |", text)
        self.assertIn("[robustness_eval.py](robustness_eval.py)", text)

    def test_dsba_no_coop_ocr_metrics_are_rendered(self):
        data = json.loads((ROOT / "work" / "robustness_summary.json").read_text(encoding="utf-8"))
        text = MODULE.generate(data)
        self.assertIn("ocr", data["dsba-no-coop"])
        self.assertTrue((ROOT / "data" / "ground_truth" / "DSBA_academic_plan_no_coop.json").is_file())
        self.assertIn("| `dsba-no-coop` | 94.4% (n=45) |", text)
        self.assertIn("| `dsba-no-coop` | 95.5% | 93.3% | 42 | 3 | 2 | 45 | 44 |", text)
        self.assertNotIn("`dsba-no-coop` ยังไม่มี OCR evaluation", text)


if __name__ == "__main__":
    unittest.main()
