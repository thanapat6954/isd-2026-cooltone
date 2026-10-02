import importlib.util
import sys
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lab8b_placeholder_test", ROOT / "scr" / "ocr_system" / "lab8b_curriculum_db.py"
)
LAB8 = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = LAB8
SPEC.loader.exec_module(LAB8)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab10_fastapi.curriculum_app.main import _frontend_sources  # noqa: E402
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL  # noqa: E402
from lab10_fastapi.curriculum_app.query_planner import QueryPlan  # noqa: E402


class PlaceholderFidelityTests(unittest.TestCase):
    def test_credit_deficit_is_blocked_not_filled_with_invented_slots(self):
        source = {"program": "TEST", "courses": [{
            "code": "06036086", "name_th": "หลักปรัชญาแห่งวิทยาศาสตร์",
            "credits": "3(3-0-6)", "year": 4, "semester": 2,
            "page_number": 30, "source_file": "BIT-60.pdf",
        }], "term_totals": [{"year": 4, "semester": 2, "credits": 12,
                               "row_count": 4, "page_number": 30}]}
        converted, _ = LAB8.convert_lab7b(source, program_id="TEST", total_credits=30, years=4)
        self.assertEqual(len(converted["plan"]), 1)
        kinds = {error["kind"] for error in LAB8.validate_conversion_fidelity(converted, source)}
        self.assertIn("term_credit_total_mismatch", kinds)
        self.assertIn("term_row_count_mismatch", kinds)

    def test_failed_replacement_preserves_existing_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "curriculum.db"
            with sqlite3.connect(db) as connection:
                connection.execute("CREATE TABLE sentinel(value TEXT)")
                connection.execute("INSERT INTO sentinel VALUES ('original')")
            connection.close()
            before = db.read_bytes()
            source = root / "input.json"
            source.write_text(json.dumps({"program": {}}), encoding="utf-8")
            with self.assertRaises(KeyError):
                LAB8.cmd_load(SimpleNamespace(input=str(source), database=str(db), replace=True))
            self.assertEqual(before, db.read_bytes())

    def test_load_roundtrip_preserves_credit_options_and_backup(self):
        source = {"program": "TEST", "courses": [{
            "code": "xxxxxxxx", "name_th": "วิชาเลือกเสรี 1",
            "credits": "3(3-0-6) หรือ 3(2-2-5)", "year": 4, "semester": 2,
            "page_number": 30, "source_file": "BIT-60.pdf",
        }]}
        converted, _ = LAB8.convert_lab7b(source, program_id="TEST", total_credits=30, years=4)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "curriculum.db"
            with sqlite3.connect(db) as connection:
                connection.execute("CREATE TABLE sentinel(value TEXT)")
            connection.close()
            source_path = root / "input.json"
            source_path.write_text(json.dumps(converted, ensure_ascii=False), encoding="utf-8")
            LAB8.cmd_load(SimpleNamespace(input=str(source_path), database=str(db), replace=True))
            backups = list(root.glob("*.bak"))
            self.assertEqual(len(backups), 1)
            with sqlite3.connect(backups[0]) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM sentinel").fetchone()[0], 0)
            connection.close()
            with sqlite3.connect(db) as connection:
                self.assertEqual(connection.execute("SELECT code FROM v_plan").fetchone()[0], "xxxxxxxx")
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM plan_item_credit_option").fetchone()[0], 2)
            connection.close()

    def test_wildcard_and_credit_alternatives_are_lossless(self):
        source = {
            "program": "DSBA",
            "courses": [{
                "code": "060261xx",
                "name_th": "วิชาเลือกทางวิทยาการข้อมูล 2",
                "name_en": "ELECTIVE COURSE IN DATA SCIENCE 2",
                "credits": "3(3-0-6) หรือ 3(2-2-5)",
                "year": 4,
                "semester": 1,
                "category": "หมวดวิชาเฉพาะ",
                "type": "เลือก",
                "source_file": "DSBA-60.pdf",
                "page_number": 29,
            }],
        }
        converted, _report = LAB8.convert_lab7b(
            source,
            program_id="DSBA-no-coop",
            total_credits=30,
            years=4,
            curriculum_version=2560,
            plan_variant="no-coop",
            printed_page_offset=5,
        )
        row = converted["plan"][0]
        self.assertTrue(row["is_placeholder"])
        self.assertEqual(row["raw_code"], "060261xx")
        self.assertEqual(row["code_pattern"], "060261XX")
        self.assertEqual(row["printed_page_number"], 24)
        self.assertEqual(len(row["credit_options"]), 2)
        self.assertEqual(row["credit_options"][1]["raw_pattern"], "3(2-2-5)")

    def test_same_ordinal_different_elective_families_do_not_merge(self):
        source={'courses':[{'code':'90xxxxxx','name_th':name,'credits':'3(3-0-6)',
                            'year':4,'semester':2,'source_file':'test.pdf','page_number':40}
                           for name in ('วิชาเลือกทางมนุษยศาสตร์ 2','วิชาเลือกทางวิทยาศาสตร์กับคณิตศาสตร์ 2')]}
        result,report=LAB8.convert_lab7b(source,program_id='TEST',total_credits=30,years=4)
        self.assertEqual(len(result['plan']),2)
        self.assertEqual(len({row['code'] for row in result['plan']}),2)

    def test_markdown_restores_all_x_placeholder_code(self):
        source = {"courses": [{
            "code": "วิชาเลือกเสรี 2",
            "name_th": "วิชาเลือกเสรี 2",
            "name_en": "FREE ELECTIVE COURSE 2",
        }]}
        markdown = (
            "<table><tr><td>Xxxxxxxx</td><td>วิชาเลือกเสรี 2<br/>"
            "FREE ELECTIVE COURSE 2</td><td>3(3-0-6)</td></tr></table>"
        )
        count = LAB8._recover_placeholder_codes_from_markdown(source, markdown)
        self.assertEqual(count, 1)
        self.assertEqual(source["courses"][0]["code"], "Xxxxxxxx")

    def test_rowspan_code_list_recovers_each_printed_slot(self):
        source = {"courses": [
            {"code": "วิชาเลือกเสรี 1", "name_th": "วิชาเลือกเสรี 1"},
            {"code": "วิชาเลือกเสรี 2", "name_th": "วิชาเลือกเสรี 2"},
        ]}
        markdown = (
            '<table><tr><td rowspan="4">06036086<br/>06036088<br/>xxxxxxx<br/>xxxxxxx</td>'
            '<td>หลักปรัชญาแห่งวิทยาศาสตร์</td><td>3(3-0-6)</td></tr>'
            '<tr><td>การคิดอย่างสร้างสรรค์</td><td>3(3-0-6)</td></tr>'
            '<tr><td>วิชาเลือกเสรี 1</td><td>3(3-0-6)</td></tr>'
            '<tr><td>วิชาเลือกเสรี 2</td><td>3(3-0-6)</td></tr></table>'
        )
        self.assertEqual(LAB8._recover_placeholder_codes_from_markdown(source, markdown), 2)
        self.assertEqual([row["code"] for row in source["courses"]], ["xxxxxxx", "xxxxxxx"])

    def test_adjacent_cooperative_alternatives_are_both_kept(self):
        source = {
            "program": "DSBA",
            "courses": [
                {
                    "code": "06026130", "name_th": "สหกิจศึกษาในประเทศ",
                    "name_en": "COOPERATIVE EDUCATION", "credits": "6(0-35-0)",
                    "year": 4, "semester": 2, "source_file": "DSBA-60.pdf", "page_number": 34,
                },
                {
                    "code": "06026131", "name_th": "สหกิจศึกษาต่างประเทศ",
                    "name_en": "INTERNATIONAL COOPERATIVE EDUCATION", "credits": None,
                    "year": 4, "semester": 2, "source_file": "DSBA-60.pdf", "page_number": 34,
                },
            ],
        }
        converted, _report = LAB8.convert_lab7b(
            source, program_id="DSBA-coop", total_credits=30, years=4,
            curriculum_version=2560, plan_variant="coop", printed_page_offset=5,
        )
        self.assertEqual([row["code"] for row in converted["plan"]], ["06026130", "06026131"])
        self.assertEqual([row["alternative_index"] for row in converted["plan"]], [1, 2])
        self.assertEqual(len({row["alt_group"] for row in converted["plan"]}), 1)
        self.assertEqual([row["credits"] for row in converted["plan"]], [6, 6])

    def test_frontend_source_has_pdf_and_book_page_and_clean_quote(self):
        sources = _frontend_sources({
            "intent": "course_list",
            "rows": [{
                "code": "Xxxxxxxx", "name_th": "วิชาเลือกเสรี 2",
                "name_en": "FREE ELECTIVE COURSE 2", "credits": 3,
                "credits_raw": "3(3-0-6)", "is_placeholder": 1,
                "source_file": "DSBA-60.pdf", "page_number": 29,
                "printed_page_number": 24,
                "_source": {"curriculum_version": 2560, "plan": "no-coop"},
            }],
        })
        self.assertEqual(sources[0]["page"], 29)
        self.assertEqual(sources[0]["book_page"], 24)
        self.assertNotIn("name_th:", sources[0]["quote"])
        self.assertIn("สล็อตวิชาเลือก", sources[0]["quote"])

    def test_course_list_never_exposes_internal_slot_id(self):
        plan = QueryPlan("course_list", 4, 2)
        rows = [{
            "code": "Xxxxxxxx", "internal_code": "ELEC-SLOT-043",
            "name_th": "วิชาเลือกเสรี 2", "name_en": "FREE ELECTIVE COURSE 2",
            "credits": 3, "credits_raw": "3(3-0-6)", "is_placeholder": 1,
            "elective_type": "free_elective",
            "_source": {"curriculum_name": "DSBA-2560-no-coop"},
        }]
        answer = QwenTextToSQL._ground_answer(plan, rows, "")
        self.assertNotIn("ELEC-SLOT", answer)
        self.assertIn("วิชาเลือกเสรี 2", answer)
        self.assertIn("รหัสยังไม่กำหนด", answer)


if __name__ == "__main__":
    unittest.main()
