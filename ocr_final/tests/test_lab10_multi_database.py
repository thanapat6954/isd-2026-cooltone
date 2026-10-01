"""Integration tests for Lab 10's schema-aware multi-database query path."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from lab10_fastapi.curriculum_app.config import PROJECT_ROOT, settings
from lab10_fastapi.curriculum_app.database import (
    DatabaseRegistry,
    SqlValidationError,
    execute_readonly,
    validate_sql,
)
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
from lab10_fastapi.curriculum_app.query_planner import detect_intent, deterministic_sql


class NoModel:
    def ollama_generate(self, *args, **kwargs):  # pragma: no cover - a test failure if reached
        raise AssertionError("The deterministic tests must not call Qwen for SQL")


class DeterministicAssistant(QwenTextToSQL):
    def summarize(self, question, plan, rows, executions):
        return json.dumps(rows, ensure_ascii=False)


class RepairAssistant(DeterministicAssistant):
    def make_sql(self, question, plan, database, *, previous_sql=None, error=None):
        if previous_sql is None:
            return "SELECT invented_column FROM program"
        return "SELECT total_credits FROM program"


class MultiDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = DatabaseRegistry(Path(os.getenv("CURRICULUM_TEST_ROOT", str(PROJECT_ROOT))))
        if not cls.registry.active_programs:
            raise unittest.SkipTest("Live-database integration needs generated databases or CURRICULUM_TEST_ROOT")
        cls.config = replace(settings, debug=True, sql_repair_attempts=2, max_rows=100)
        cls.assistant = DeterministicAssistant(cls.config, NoModel())

    def test_01_semester_credit_question_queries_all_relevant_curricula(self):
        result = self.assistant.ask(self.registry, "ปี 1 เทอม 1 เรียนกี่หน่วยกิต")
        self.assertEqual(result["intent"], "semester_credits")
        self.assertEqual(len(result["selected_curricula"]), len(self.registry.active_programs))
        self.assertTrue(all("year = 1" in item["sql"] for item in result["queries"]))
        self.assertTrue(all("semester = 1" in item["sql"] for item in result["queries"]))
        self.assertTrue(all("credits" in row for row in result["rows"]))

    def test_02_it_total_credits_selects_both_variants_without_fake_filters(self):
        result = self.assistant.ask(self.registry, "สาขา IT ฉบับล่าสุด 2565 เรียนรวมทั้งหมดกี่หน่วยกิต")
        self.assertEqual(result["selected_curricula"], ["IT-2565-coop", "IT-2565-no-coop"])
        self.assertEqual({row["total_credits"] for row in result["rows"]}, {129})
        for query in result["queries"]:
            self.assertIn("FROM program", query["sql"])
            self.assertNotIn("year", query["sql"].casefold())
            self.assertNotIn("semester", query["sql"].casefold())

    def test_03_course_count_uses_count(self):
        result = self.assistant.ask(self.registry, "มีวิชาทั้งหมดกี่วิชา")
        self.assertEqual(result["intent"], "course_count")
        self.assertTrue(all("COUNT(" in item["sql"] for item in result["queries"]))
        self.assertTrue(all("course_count" in row for row in result["rows"]))

    def test_04_course_list_filters_only_explicit_year_and_semester(self):
        result = self.assistant.ask(self.registry, "ปี 2 เทอม 1 มีวิชาอะไรบ้าง")
        self.assertEqual(result["intent"], "course_list")
        self.assertTrue(result["rows"])
        self.assertTrue(all(row["year"] == 2 and row["semester"] == 1 for row in result["rows"]))
        fallback = self.assistant._ground_answer(
            detect_intent("ปี 2 เทอม 1 มีวิชาอะไรบ้าง"),
            result["rows"],
            "ปี 2 เทอม 1 มีวิชาอะไรบ้าง",
        )
        self.assertIn(str(result["rows"][0]["code"]), fallback)
        self.assertIn(str(result["rows"][0]["_source"]["curriculum_name"]), fallback)

    def test_05_ai_question_selects_ai_database(self):
        result = self.assistant.ask(self.registry, "หลักสูตร AI มีหน่วยกิตรวมทั้งหมดเท่าไร")
        self.assertEqual(len(result["selected_curricula"]), 1)
        self.assertEqual(result["rows"][0]["_source"]["program_id"], "AI")
        self.assertEqual(result["rows"][0]["total_credits"], 120)

        info = self.assistant.ask(self.registry, "หลักสูตร AI ชื่อว่าอะไร")
        self.assertEqual(info["intent"], "program_info")
        self.assertNotIn("WHERE", info["queries"][0]["sql"].upper())

    def test_06_invalid_model_column_is_repaired(self):
        assistant = RepairAssistant(self.config, NoModel())
        # A valid but non-template question deliberately enters model SQL generation.
        result = assistant.ask(self.registry, "แสดงข้อมูลภาพรวมของหลักสูตร AI")
        self.assertEqual(len(result["selected_curricula"]), 1)
        self.assertEqual(result["rows"][0]["_source"]["program_id"], "AI")
        self.assertEqual(result["rows"][0]["total_credits"], 120)
        self.assertEqual(len(result["queries"][0]["repair_attempts"]), 1)
        self.assertIn("no such column", result["queries"][0]["repair_attempts"][0]["error"])

    def test_07_ambiguous_total_keeps_sources_separate(self):
        result = self.assistant.ask(self.registry, "หลักสูตรมีหน่วยกิตรวมทั้งหมดเท่าไร")
        self.assertEqual(len(result["selected_curricula"]), len(self.registry.active_programs))
        sources = {row["_source"]["curriculum_name"] for row in result["rows"]}
        self.assertEqual(sources, set(result["selected_curricula"]))
        self.assertEqual(len(result["rows"]), len(self.registry.active_programs))

    def test_08_mixed_schemas_generate_compatible_course_queries(self):
        plan = detect_intent("วิชา 06016401 มีรายละเอียดอะไร")
        selected = self.registry.select("วิชา 06016401 มีรายละเอียดอะไร", include_legacy=True)
        self.assertIn("lab8b", {item.schema_family for item in selected})
        self.assertIn("legacy-course-catalog", {item.schema_family for item in selected})
        for database in selected:
            sql = deterministic_sql(plan, database)
            self.assertIsNotNone(sql)
            validation, _ = execute_readonly(database, sql, 10)
            if database.schema_family == "lab8b":
                self.assertIn("FROM course ", validation.sql)
            else:
                self.assertIn("FROM courses ", validation.sql)

        search_plan = detect_intent("หลักสูตร DSBA วิชาแคลคูลัส 1 มีรหัสอะไร")
        self.assertEqual(search_plan.intent, "course_search")
        self.assertEqual(search_plan.search_term, "แคลคูลัส 1")
        dsba = self.registry.select("หลักสูตร DSBA พ.ศ. 2565 และสหกิจ")[0]
        search_sql = deterministic_sql(search_plan, dsba)
        _, rows = execute_readonly(dsba, search_sql, 10)
        self.assertEqual(rows[0]["code"], "06026200")

        programming_plan = detect_intent("วิชาการเขียนโปรแกรมมีกี่หน่วยกิต")
        self.assertEqual(programming_plan.intent, "course_search")
        self.assertEqual(programming_plan.search_term, "การเขียนโปรแกรม")
        programming_sql = deterministic_sql(programming_plan, dsba)
        _, programming_rows = execute_readonly(dsba, programming_sql, 10)
        self.assertEqual(programming_rows[0]["code"], "06066302")
        self.assertEqual(programming_rows[0]["credits"], 3)

    def test_09_version_diff_is_deterministic(self):
        plan = detect_intent("วิชาใดมีในหลักสูตรเดิม แต่ไม่มีในหลักสูตรฉบับปรับปรุง")
        self.assertEqual(plan.intent, "version_course_diff")
        self.assertTrue(plan.compare)
        dsba = next(
            item for item in self.registry.active_programs
            if item.program_id == "DSBA-coop" and item.curriculum_version == 2565
        )
        sql = deterministic_sql(plan, dsba)
        self.assertIn("SELECT DISTINCT code", sql)
        self.assertIn("FROM v_plan", sql)

    def test_10_version_metadata_is_exposed(self):
        dsba = next(
            item for item in self.registry.active_programs
            if item.program_id == "DSBA-coop" and item.curriculum_version == 2565
        )
        metadata = dsba.public_metadata()
        self.assertEqual(metadata["curriculum_version"], 2565)
        self.assertTrue(metadata["is_latest"])
        self.assertEqual(metadata["plan"], "coop")

    def test_11_bit_name_does_not_select_it(self):
        selected = self.registry.select("หลักสูตรเทคโนโลยีสารสนเทศทางธุรกิจ พ.ศ. 2565")
        self.assertTrue(selected)
        self.assertTrue(all((item.program_id or "").startswith("BIT") for item in selected))

    def test_12_required_course_ui_question_is_deterministic(self):
        question = "หลักสูตร IT 2565: ปี 2 ภาคการศึกษาที่ 1 มีวิชาบังคับอะไรบ้าง"
        result = self.assistant.ask(self.registry, question)
        self.assertEqual(result["intent"], "course_list")
        self.assertEqual(result["selected_curricula"], ["IT-2565-coop", "IT-2565-no-coop"])
        self.assertTrue(result["rows"])
        for query in result["queries"]:
            self.assertIn("year = 2", query["sql"])
            self.assertIn("semester = 1", query["sql"])
            self.assertIn("ctype LIKE", query["sql"])
            self.assertEqual(query["repair_attempts"], [])

    def test_validator_rejects_destructive_and_unknown_schema(self):
        database = self.registry.active_programs[0]
        with self.assertRaises(SqlValidationError):
            validate_sql(database, "DROP TABLE course")
        with self.assertRaises(SqlValidationError):
            validate_sql(database, "SELECT program_id FROM v_semester_credits")
        with self.assertRaises(SqlValidationError):
            self.assistant._validate_plan_filters(
                "หลักสูตร AI ชื่อว่าอะไร",
                detect_intent("หลักสูตร AI ชื่อว่าอะไร"),
                database,
                "SELECT name_th FROM program WHERE name_en = 'AI'",
            )
        with self.assertRaises(SqlValidationError):
            self.assistant._validate_plan_filters(
                "แสดงรายวิชา",
                detect_intent("แสดงรายวิชา"),
                database,
                "SELECT * FROM course WHERE name_th LIKE '%แคลคูลัส%'",
            )
        with self.assertRaises(SqlValidationError):
            self.assistant._validate_plan_filters(
                "หลักสูตร AI มีข้อมูลอะไร",
                detect_intent("หลักสูตร AI มีข้อมูลอะไร"),
                database,
                "SELECT * FROM program WHERE program_id = 'wrong-program'",
            )


if __name__ == "__main__":
    unittest.main()
