#!/usr/bin/env python3
"""Generate and inject the README evaluation summary from robustness JSON."""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable


START = "<!-- EVAL:START -->"
END = "<!-- EVAL:END -->"
PROFILE_ORDER = ("dsba", "ai", "it-coop", "it-no-coop", "dsba-no-coop")
PROFILE_DISPLAY_NAMES = {
    "dsba": "dsba-coop",
    "dsba-no-coop": "dsba-no-coop",
    "ai": "ai",
    "it-coop": "it-coop",
    "it-no-coop": "it-no-coop",
}
PROFILE_INFO = {
    "dsba": {"program": "DSBA", "variant": "coop", "folder": "work/lab8b_dsba_coop"},
    "dsba-no-coop": {"program": "DSBA", "variant": "no-coop", "folder": "work/lab8b_dsba_no_coop"},
    "ai": {"program": "AI", "variant": "แผนเดียว", "folder": "work/lab8b_ai"},
    "it-coop": {"program": "IT", "variant": "coop", "folder": "work/lab8b_it_coop"},
    "it-no-coop": {"program": "IT", "variant": "no-coop", "folder": "work/lab8b_it_no_coop"},
}
NAME_SIMILARITY_THRESHOLD = 0.5
ERROR_SAMPLE_LIMIT = 5
GT_FILES = {
    "dsba": "data/ground_truth/DSBA_academic_plan_coop.json",
    "dsba-no-coop": "data/ground_truth/DSBA_academic_plan_no_coop.json",
    "ai": "data/ground_truth/AIT_academic_plan.json",
    "it-coop": "data/ground_truth/IT_academic_plan_coop.json",
    "it-no-coop": "data/ground_truth/IT_academic_plan_no_coop.json",
}
GT_REVIEW_CANDIDATES = {
    ("dsba", "06026205"),
    ("dsba", "06066304"),
    ("dsba", "90641001"),
    ("it-coop", "06066301"),
    ("it-coop", "06016412"),
    ("it-no-coop", "06066301"),
    ("it-no-coop", "06016412"),
}

# All generated human-readable wording is centralized here for easy editing.
STRINGS = {
    "readme_title": "# ระบบ OCR และ RAG สำหรับข้อมูลหลักสูตร",
    "section_title": "## สรุปผลการประเมินและการวิเคราะห์ระบบ",
    "tldr_heading": "### 1. สรุปย่อ",
    "capabilities_label": "ความสามารถของระบบ",
    "capabilities_perfect": "ทุก profile ตอบชุด held-out ได้ครบและให้ผลคงที่เมื่อทดสอบซ้ำ",
    "capabilities_review": "ผล held-out แตกต่างกันตาม profile โปรดดูรายละเอียดในตารางด้านล่าง",
    "citation_uniform": "citation coverage ครบทุก profile",
    "citation_not_uniform": "citation coverage ยังไม่ครบทุก profile",
    "vulnerabilities_label": "จุดที่ต้องปรับปรุง",
    "no_ocr_failures": "JSON ไม่มีข้อมูลข้อผิดพลาดระดับ attribute ให้ตรวจสอบ",
    "reliability_label": "ความน่าเชื่อถือของข้อมูลประเมิน",
    "profiles_heading": "### 1.1 profile ที่ใช้ประเมิน",
    "col_program": "program",
    "col_variant": "variant",
    "col_source_folder": "source folder ภายใต้ `work/`",
    "col_ocr_gt_available": "มี OCR ground truth",
    "available_yes": "มี",
    "available_no": "ไม่มี",
    "mapping_confirmed": "JSON key `dsba` ชี้ไปที่ `work/lab8b_dsba_coop` จึงแสดงชื่อเป็น `dsba-coop` ตาม [robustness_eval.py](robustness_eval.py)",
    "mapping_unconfirmed": "ยืนยันไม่ได้ว่า JSON key `dsba` หมายถึง variant ใด เพราะไม่พบ mapping ที่คาดไว้ใน [robustness_eval.py](robustness_eval.py)",
    "reliability_unavailable": "ตรวจสอบไม่ได้ เนื่องจากไม่มีขนาดชุด held-out",
    "reliability_moderate": "ปานกลาง",
    "reliability_high": "สูง",
    "stable_all": "ผลคงที่ทุก profile ที่มีข้อมูล",
    "stable_not_all": "ผลยังไม่คงที่ครบทุก profile",
    "reliability_detail": "{level}: {stability} แต่ชุด held-out ที่เล็กที่สุดมีเพียง n={minimum} จึงยังมีความไม่แน่นอนแม้คะแนนจะเต็ม",
    "profile_summary_heading": "### 2. ภาพรวมผลประเมินแยกตาม profile",
    "col_profile": "profile",
    "col_ocr_f1": "OCR F1",
    "col_heldout_accuracy": "ความแม่นยำ held-out (ถูก/ทั้งหมด)",
    "col_citation": "citation coverage",
    "col_abstain_pr": "abstain Precision / Recall",
    "col_stability": "ความคงที่",
    "col_latency": "latency เฉลี่ย (วินาที)",
    "stable_yes": "คงที่",
    "stable_no": "ไม่คงที่",
    "ocr_breakdown_heading": "### 3. ผล OCR แยกตาม attribute",
    "alignment_heading": "#### ผล alignment ระดับรายวิชา",
    "col_precision": "Precision",
    "col_recall": "Recall",
    "col_matched": "matched",
    "col_missed": "missed",
    "col_spurious": "spurious",
    "col_gt_n": "GT (n)",
    "col_pred_n": "prediction (n)",
    "primary_profile_heading": "#### รายละเอียด profile หลัก (`dsba-coop`)",
    "col_attribute": "attribute",
    "col_sample_n": "จำนวนตัวอย่าง (n)",
    "other_profiles_summary": "คลิกเพื่อดูผล OCR ของ profile อื่น",
    "error_samples_heading": "#### ตัวอย่างข้อผิดพลาดจริงจากระบบ",
    "dsba_no_coop_samples_summary": "ตัวอย่าง error samples ทั้งหมดของ `dsba-no-coop` สำหรับ `name_th`, `name_en` และ `prereq`",
    "dsba_no_coop_samples_heading": "#### error samples ของ `dsba-no-coop`",
    "col_key": "key",
    "col_gt": "gt",
    "col_pred": "pred",
    "col_class": "class",
    "col_attribute_query": "attribute / คำถาม",
    "col_expected": "เฉลย",
    "col_actual": "ผลลัพธ์จริง",
    "col_error_type": "ลักษณะข้อผิดพลาด",
    "rag_heading": "### 4. ผลการประเมิน RAG (RAG Evaluation)",
    "col_expected_not_found": "ผล not found ที่ถูกต้อง",
    "col_abstain_precision": "abstain Precision",
    "col_false_abstains": "false abstains",
    "col_real_answer_recall": "real answer Recall",
    "col_runs": "จำนวนรอบ",
    "metric_n": "n",
    "metric_cer": "CER",
    "metric_wer": "WER",
    "metric_exact_match": "Exact Match",
    "metric_heldout": "held-out",
    "metric_field_recall": "Course-level Recall (alignment)",
    "metric_field_precision": "Course-level Precision (alignment)",
    "metric_abstain_precision": "abstain Precision",
    "metric_abstain_recall": "abstain Recall",
    "metric_false_abstain": "false abstain",
    "metric_citation_coverage": "citation coverage",
    "stability_explanation": "การตรวจความคงที่เปรียบเทียบ SQL, แถวผลลัพธ์, ข้อความคำตอบ, citation และข้อผิดพลาดจากการรันซ้ำแบบ deterministic ตาม [robustness_eval.py](robustness_eval.py) และ [lab8b_curriculum_db.py](scr/ocr_system/lab8b_curriculum_db.py)",
    "baseline_heading": "### 5. เปรียบเทียบ baseline v1 กับผลปัจจุบัน",
    "col_profile_metric": "profile / metric",
    "col_baseline_accuracy": "ความแม่นยำ baseline v1",
    "col_current_accuracy": "ความแม่นยำปัจจุบัน",
    "col_delta": "ผลต่าง (Δ)",
    "col_baseline_f1": "baseline F1",
    "col_current_f1": "F1 ปัจจุบัน",
    "ocr_f1_unchanged": "OCR F1 เท่าเดิมจาก baseline v1 ในทุก profile ที่มีข้อมูล ดังนั้นคะแนนความแม่นยำที่เพิ่มขึ้นมาจากฝั่ง RAG เท่านั้น",
    "ocr_f1_changed": "OCR F1 ระหว่าง baseline v1 กับผลปัจจุบันไม่เท่ากันครบทุก profile จึงสรุปไม่ได้ว่าผลต่างมาจาก RAG เท่านั้น",
    "baseline_missing_note": "profile ที่ไม่มี baseline_v1 report เพราะไม่เคยวัดก่อน current version: {profiles} ดังนั้นคอลัมน์ baseline จึงเป็น n/a โดยตั้งใจ ไม่ใช่ข้อมูลสูญหาย",
    "metric_matrix_heading": "### 6. แนวทางตีความ metric และผลกระทบ",
    "col_metric": "metric",
    "col_high_meaning": "ค่าสูงหมายถึง",
    "col_low_meaning": "ค่าต่ำหมายถึง",
    "col_impact": "ผลกระทบต่อระบบ",
    "field_recall_high": "ดึงข้อมูลได้ครบถ้วน",
    "field_recall_low": "รายวิชาหรือข้อมูลสูญหายจาก DB",
    "field_recall_impact": "รายวิชาหายและอาจทำให้นักศึกษาจัดแผนเรียนผิด",
    "field_precision_high": "ข้อมูลที่ดึงมาถูกต้องและไม่มีข้อมูลแต่งขึ้น",
    "field_precision_low": "มีข้อมูลขยะหรือวิชาที่ไม่มีอยู่จริง",
    "field_precision_impact": "ข้อมูลเท็จอาจถูกบันทึกลงฐานข้อมูล",
    "cer_wer_high": "มีข้อผิดพลาดระดับอักขระหรือคำจำนวนมาก",
    "cer_wer_low": "มีข้อผิดพลาดด้านอักขระหรือคำน้อย",
    "cer_wer_impact": "ชื่อวิชาและเงื่อนไขอาจเปลี่ยนความหมาย",
    "abstain_high": "การ abstain ส่วนใหญ่เกิดกับคำถามที่ไม่มีคำตอบจริง",
    "abstain_low": "ระบบ abstain ทั้งที่ฐานข้อมูลมีคำตอบ",
    "abstain_impact": "ผู้ใช้ต้องตรวจสอบหรือค้นหาคำตอบเองเพิ่มขึ้น",
    "citation_high": "คำตอบมีแหล่งอ้างอิงครบถ้วน",
    "citation_low": "คำตอบไม่มีแหล่งอ้างอิง",
    "citation_impact": "ตรวจสอบความถูกต้องและความน่าเชื่อถือได้ยาก",
    "exact_match_high": "ค่าที่สกัดได้ตรงกับเฉลยเป็นสัดส่วนสูง",
    "exact_match_low": "ค่าที่สกัดได้ไม่ตรงกับเฉลยหลายรายการ",
    "exact_match_impact": "ค่าที่ผิดอาจถูกนำไปตอบผู้ใช้หรือบันทึกลง DB",
    "false_abstain_high": "ระบบปฏิเสธคำถามจำนวนมากทั้งที่มีคำตอบ",
    "false_abstain_low": "ระบบแทบไม่ปฏิเสธคำถามที่มีคำตอบ",
    "false_abstain_impact": "ผู้ใช้อาจไม่ได้รับข้อมูลที่มีอยู่ใน DB",
    "abstain_recall_high": "ระบบ abstain ได้ครบเมื่อคำถามไม่มีคำตอบ",
    "abstain_recall_low": "ระบบยังพยายามตอบบางคำถามที่ไม่มีคำตอบ",
    "abstain_recall_impact": "เพิ่มความเสี่ยงที่ระบบจะแต่งคำตอบเมื่อไม่มีข้อมูล",
    "thai_wer_note": "**หมายเหตุ:** ภาษาไทยไม่มีช่องว่างคั่นระหว่างคำ ค่า WER จึงขึ้นกับวิธีตัดคำ และอาจสูงแม้ CER ต่ำเมื่อข้อผิดพลาดกระจายอยู่ในหลายคำ",
    "abstention_weak_uniform": "การประเมิน abstention มีคำถามที่ควร abstain เพียง n={n} ต่อ profile ดังนั้นคะแนนเต็มในส่วนนี้ยังเป็นหลักฐานที่อ่อน",
    "abstention_weak_varied": "จำนวนคำถามที่ควร abstain มีน้อยและแตกต่างกันตาม profile ({counts}) จึงยังเป็นหลักฐานที่อ่อน",
    "abstention_weak_missing": "JSON ไม่มีขนาดตัวอย่างสำหรับคำถามที่ควร abstain",
    "abstention_limit_label": "ข้อจำกัดของ abstention",
    "reliability_heading": "### 7. การตรวจ overfitting และความน่าเชื่อถือของข้อมูล",
    "sample_assessment_label": "ขนาดชุดประเมิน",
    "sample_profile_with_ocr": "`{name}`: held-out n={held_n}, OCR GT n={ocr_n}",
    "sample_profile_without_ocr": "`{name}`: held-out n={held_n}, OCR GT n/a",
    "smallest_sample": "ชุด held-out ที่เล็กที่สุดมี n={minimum} และต้องรายงานขนาดตัวอย่างควบคู่กับคะแนน",
    "sample_unavailable": "ตรวจสอบขนาดชุด held-out จาก JSON ไม่ได้",
    "perfect_score_label": "การตรวจคะแนนเต็ม",
    "perfect_score_text": "JSON ยืนยันคะแนนและขนาดตัวอย่างได้ แต่ยืนยันไม่ได้ว่าคำถามเคยถูกใช้ระหว่างการพัฒนาหรือไม่",
    "variance_label": "ความต่างระหว่าง profile และ shortcut learning",
    "variance_text": "คะแนน RAG เท่ากันทุก profile ขณะที่ผล OCR แตกต่างกัน แต่ JSON สรุปนี้ยังไม่เพียงพอที่จะตัดความเป็นไปได้ของ shortcut learning จากรูปแบบคำถาม",
    "gold_table_heading": "#### เปรียบเทียบ known-gold กับ held-out",
    "col_known_gold": "known-gold (ถูก/ทั้งหมด)",
    "col_heldout_count": "held-out (ถูก/ทั้งหมด)",
    "issues_heading": "### 8. ปัญหาที่พบและขั้นตอนถัดไป",
    "name_rule": "**กฎการแยก `name_th`:** จัดเป็น truncation / merged row / label bleed-in ก่อน เมื่อ pred เป็น strict subset ของ gt หรือมีข้อความหัวข้อเกินมา เช่น “กลุ่มวิชาด้าน”; รายการที่เหลือจัดเป็น row misalignment เมื่อ char-level similarity ต่ำกว่า {threshold} หรือ pred ตรงกับชื่อรายวิชาอื่นใน GT เต็มของ profile; นอกเหนือจากนั้นจัดเป็นข้อผิดพลาดระดับการสะกด",
    "error_sample_limit_note": "**หมายเหตุเกี่ยวกับ error samples:** JSON เก็บได้ไม่เกิน {limit} รายการต่อ attribute ต่อ profile ดังนั้นจำนวน pattern มาจากตัวอย่างที่บันทึกไว้ ส่วนจำนวนข้อผิดพลาดทั้ง attribute เป็น estimate",
    "tldr_issue_pointer": "`{attribute}` เป็นปัญหาที่มีผลกระทบสูงสุด ดูรายละเอียดและรายการอื่นในหัวข้อ 8",
    "severity_critical": "วิกฤต",
    "severity_major": "สำคัญ",
    "severity_minor": "เล็กน้อย",
    "recorded_samples": "จาก error samples ที่บันทึกไว้ {total} รายการ",
    "estimated_errors": "ข้อผิดพลาดทั้ง attribute โดยประมาณ {estimated}/{attribute_n} รายการ (estimate จาก round(n × (1 - Exact Match)))",
    "ctype_pattern": "{index}. **{severity}:** `ctype` {recorded}; พบทิศทาง gt→pred: {directions}; {estimate} ซึ่งอาจทำให้ผู้ใช้เข้าใจประเภทวิชาผิด",
    "prereq_pattern": "{index}. **{severity}:** `prereq` {recorded}; pred=“ไม่มี” ทั้งที่ gt ระบุ prerequisite {missing}/{total} รายการ, pred=None ซึ่งหมายถึง extraction ไม่ได้ค่า {none_count}/{total} รายการ และ other {other}/{total} รายการ ({other_keys}); รวม {classified}/{total} รายการ; {estimate} ผลกระทบคือผู้ใช้อาจได้รับแจ้งว่าไม่มี prerequisite ทั้งที่มีอยู่จริง",
    "name_misalignment_pattern": "{index}. **{severity}:** `name_th` {recorded}; พบ row misalignment {misaligned}/{total} รายการ ({cases}); {estimate} ซึ่งอาจแสดงชื่อรายวิชาผิดรายการ",
    "name_truncation_pattern": "{index}. **{severity}:** `name_th` {recorded}; พบ truncation / merged row / label bleed-in {truncated}/{total} รายการ ({cases}); {estimate} ซึ่งอาจแสดงชื่อรายวิชาไม่ครบหรือปนข้อความหัวข้อ",
    "name_spelling_pattern": "{index}. **{severity}:** `name_th` {recorded}; พบข้อผิดพลาดระดับการสะกด {spelling}/{total} รายการ; {estimate} ซึ่งมีผลกระทบต่ำกว่า row misalignment",
    "ground_truth_review_pattern": "{index}. **{severity} — Ground-truth review candidates:** `name_th` จำนวน {count} รายการที่ pred ดูเป็นรูปสะกดภาษาไทยมาตรฐานมากกว่า gt: {cases} ต้องตรวจด้วยตนเองกับ source PDF; หาก OCR ถูกต้อง ให้แก้ GT แล้วรัน evaluation ใหม่ โดยยังไม่สรุปว่า GT ผิด",
    "credits_pattern": "{index}. **{severity}:** `credits` {recorded}; ทางเลือกที่มีคำว่า “หรือ” ใน gt ถูกตัดเหลือเพียงรูปแบบเดียว {dropped}/{total} รายการ และ wrong pattern {wrong}/{total} รายการ; {estimate} ซึ่งอาจแสดงรูปแบบหน่วยกิตให้ผู้ใช้ไม่ครบหรือผิดรูปแบบ",
    "pattern_none": "{index}. **{severity}:** JSON ไม่มี error_samples สำหรับ pattern นี้",
    "dsba_no_coop_missing_ocr_with_gt": "{index}. **{severity}:** `dsba-no-coop` ยังไม่มี OCR evaluation ใน JSON แต่มี ground truth ที่ [`{gt_file}`]({gt_file}) แล้ว ให้รัน `.\\venv\\Scripts\\python.exe .\\run_lab8b.py --program dsba-no-coop` เพื่อสร้าง OCR evaluation จากนั้นรัน `.\\venv\\Scripts\\python.exe .\\robustness_eval.py --program dsba-no-coop` เพื่ออัปเดต OCR node ตาม [run_lab8b.py](run_lab8b.py)",
    "dsba_no_coop_missing_ocr_without_gt": "{index}. **{severity}:** `dsba-no-coop` ยังไม่มี OCR evaluation ใน JSON และไม่พบ ground truth ที่คาดไว้ `{gt_file}` จึงยังระบุคำสั่งสร้าง OCR node ที่ตรวจสอบได้ไม่ได้",
    "issue_na": "{index}. **{severity}:** n/a",
    "unverified_heading": "#### สิ่งที่ยังยืนยันไม่ได้",
    "unverified_ocr": "- JSON ไม่มีผล OCR สำหรับ profile: {profiles}",
    "unverified_abstain_n": "- JSON ไม่เก็บตัวหาร n ของ abstain Precision จึงยืนยันได้เฉพาะค่าร้อยละ",
    "unverified_independence": "- JSON ยืนยันไม่ได้ว่าคำถาม held-out เคยถูกใช้ในขั้นพัฒนาหรือไม่",
    "unverified_misalignment_cause": "- การแยก row misalignment เป็น heuristic จาก char-level similarity และการเทียบ GT จึงยังยืนยันสาเหตุเชิงกระบวนการไม่ได้",
    "rerun": "*สร้างสรุปนี้ใหม่ด้วยคำสั่ง:* `python scripts/make_eval_summary.py --json work/robustness_summary.json --readme Lab09_report.md`",
    "chart_ocr_alt": "กราฟสรุปค่า OCR F1",
    "chart_rag_alt": "กราฟสรุปความแม่นยำ held-out",
    "chart_ocr_axis": "ค่า OCR alignment F1",
    "chart_rag_axis": "ความแม่นยำ held-out",
    "marker_error": "README must contain exactly one complete EVAL marker pair",
    "json_type_error": "top-level robustness JSON must be an object",
    "audit_error": "generated section failed metric spot-check: {missing}",
    "updated_message": "Updated {readme} from {json}",
    "profile_chart_message": "Profiles: {profiles}; charts: {charts}",
}


def get(data: Any, *path: str) -> Any:
    """Return None for absent, null, or structurally incompatible paths."""
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def pct(value: Any, digits: int = 1) -> str:
    number = finite_number(value)
    return "n/a" if number is None else f"{number * 100:.{digits}f}%"


def number(value: Any, digits: int = 3) -> str:
    parsed = finite_number(value)
    if parsed is None:
        return "n/a"
    if parsed.is_integer():
        return str(int(parsed))
    return f"{parsed:.{digits}f}".rstrip("0").rstrip(".")


def fixed(value: Any, digits: int = 2) -> str:
    parsed = finite_number(value)
    return "n/a" if parsed is None else f"{parsed:.{digits}f}"


def pp(value: Any, digits: int = 1) -> str:
    parsed = finite_number(value)
    if parsed is None:
        return "n/a"
    sign = "+" if parsed > 0 else ""
    return f"{sign}{parsed * 100:.{digits}f} pp"


def pct_with_n(value: Any, n: Any) -> str:
    rendered = pct(value)
    parsed_n = finite_number(n)
    return rendered if rendered == "n/a" or parsed_n is None else f"{rendered} (n={number(parsed_n)})"


def metric_accuracy(metric: Any) -> float | None:
    if not isinstance(metric, dict):
        return None
    accuracy = finite_number(metric.get("accuracy"))
    if accuracy is not None:
        return accuracy
    correct = finite_number(metric.get("correct"))
    total = finite_number(metric.get("total"))
    return correct / total if correct is not None and total not in (None, 0) else None


def score(metric: Any) -> str:
    if not isinstance(metric, dict):
        return "n/a"
    correct = finite_number(metric.get("correct"))
    total = finite_number(metric.get("total"))
    accuracy = metric_accuracy(metric)
    if correct is None or total is None:
        return "n/a"
    suffix = f" ({pct(accuracy)})" if accuracy is not None else ""
    return f"{int(correct)}/{int(total)}{suffix}"


def cell(value: Any, limit: int | None = 100) -> str:
    if value is None:
        return "n/a"
    text = str(value).replace("\r", " ").replace("\n", "<br>").replace("|", "\\|")
    return text if limit is None or len(text) <= limit else text[: limit - 1] + "…"


def profiles(data: dict[str, Any]) -> list[str]:
    ordered = [name for name in PROFILE_ORDER if name in data]
    return ordered + sorted(name for name in data if name not in ordered)


def display_name(profile: str) -> str:
    return PROFILE_DISPLAY_NAMES.get(profile, profile)


def repo_path(relative: str) -> Path:
    return Path(__file__).resolve().parents[1] / relative


def dsba_mapping_confirmed() -> bool:
    source = repo_path("robustness_eval.py")
    if not source.is_file():
        return False
    text = source.read_text(encoding="utf-8")
    return (
        '"dsba": ROOT / "work" / "lab8b_dsba_coop"' in text
        and '"dsba-no-coop": ROOT / "work" / "lab8b_dsba_no_coop"' in text
    )


def attributes(report: Any) -> dict[str, dict[str, Any]]:
    value = get(report, "ocr", "attributes")
    return value if isinstance(value, dict) else {}


def profile_ocr_f1(report: Any) -> Any:
    return get(report, "ocr", "alignment", "f1")


def ocr_f1_with_n(report: Any) -> str:
    value = profile_ocr_f1(report)
    return pct_with_n(value, get(report, "ocr", "alignment", "gt_total"))


def collected_samples(data: dict[str, Any], attribute: str) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    for profile in profiles(data):
        metric = attributes(data[profile]).get(attribute) or {}
        for sample in metric.get("error_samples") or []:
            if isinstance(sample, dict):
                found.append((profile, sample))
    return found


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def full_gt_names(profile: str, attribute: str = "name_th") -> dict[str, str]:
    relative = GT_FILES.get(profile)
    if not relative:
        return {}
    path = repo_path(relative)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for key in ("courses_master", "courses"):
            value = payload.get(key)
            if isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, dict))
        pool = payload.get("flexible_electives_pool")
        if isinstance(pool, dict) and isinstance(pool.get("courses"), list):
            rows.extend(item for item in pool["courses"] if isinstance(item, dict))
    return {
        str(item.get("code")): normalize_text(item.get(attribute))
        for item in rows
        if item.get("code") and normalize_text(item.get(attribute))
    }


def classify_name_sample(
    profile: str, sample: dict[str, Any], attribute: str = "name_th"
) -> str:
    """Classify shape only; this does not decide whether GT or prediction is correct."""
    key = str(sample.get("key"))
    raw_expected = str(sample.get("gt") or "")
    raw_prediction = str(sample.get("pred") or "")
    expected = normalize_text(raw_expected)
    prediction = normalize_text(raw_prediction)
    if expected in {"", "none", "null"} or prediction in {"", "none", "null"}:
        return "other"
    merged_row = "\n" in raw_prediction
    if (
        (prediction != expected and prediction in expected)
        or "กลุ่มวิชาด้าน" in prediction
        or merged_row
    ):
        return "truncation"
    other_names = {
        value for other_key, value in full_gt_names(profile, attribute).items()
        if other_key != key
    }
    similarity = SequenceMatcher(None, expected, prediction).ratio()
    if similarity < NAME_SIMILARITY_THRESHOLD or prediction in other_names:
        return "misalignment"
    return "spelling"


def is_gt_review_candidate(profile: str, sample: dict[str, Any]) -> bool:
    """Flag cautious orthography-review candidates without asserting GT is wrong."""
    key = str(sample.get("key"))
    if (profile, key) in GT_REVIEW_CANDIDATES:
        return True
    expected = normalize_text(sample.get("gt"))
    prediction = normalize_text(sample.get("pred"))
    orthography_repairs = (
        ("เบื้อต้น", "เบื้องต้น"),
        ("อออกแบบ", "ออกแบบ"),
        ("เสน่าห์", "เสน่ห์"),
        ("อัลกอรึทึม", "อัลกอริทึม"),
        ("ปฎิบัติการ", "ปฏิบัติการ"),
    )
    return any(old in expected and new in prediction for old, new in orthography_repairs)


def attribute_error_estimate(data: dict[str, Any], attribute: str) -> tuple[int, int]:
    total_n = estimated = 0
    for profile in profiles(data):
        metric = attributes(data[profile]).get(attribute) or {}
        n_items = finite_number(metric.get("n_items"))
        exact_match = finite_number(metric.get("exact_match_acc"))
        if n_items is None or exact_match is None:
            continue
        total_n += int(n_items)
        estimated += round(n_items * (1.0 - exact_match))
    return total_n, estimated


def pattern_context(data: dict[str, Any], attribute: str, total: int) -> tuple[str, str]:
    attribute_n, estimated = attribute_error_estimate(data, attribute)
    recorded = STRINGS["recorded_samples"].format(
        total=total, limit=ERROR_SAMPLE_LIMIT
    )
    estimate = STRINGS["estimated_errors"].format(
        estimated=estimated, attribute_n=attribute_n
    )
    return recorded, estimate


def error_pattern_rows(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return impact-ranked issue descriptions computed only from JSON samples."""
    rows: list[tuple[str, str]] = []

    prereq = collected_samples(data, "prereq")
    if prereq:
        recorded, estimate = pattern_context(data, "prereq", len(prereq))
        missing = sum(
            normalize_text(sample.get("pred")) == "ไม่มี"
            and normalize_text(sample.get("gt")) not in {"", "ไม่มี", "none", "null", "n/a", "-"}
            for _, sample in prereq
        )
        none_count = sum(
            normalize_text(sample.get("pred")) in {"", "none", "null"}
            for _, sample in prereq
        )
        other_samples = [
            (profile, sample)
            for profile, sample in prereq
            if not (
                normalize_text(sample.get("pred")) == "ไม่มี"
                and normalize_text(sample.get("gt")) not in {"", "ไม่มี", "none", "null", "n/a", "-"}
            )
            and normalize_text(sample.get("pred")) not in {"", "none", "null"}
        ]
        other = len(other_samples)
        other_keys = ", ".join(
            f"`{display_name(profile)}/{sample.get('key')}`"
            for profile, sample in other_samples
        ) or "ไม่มี"
        classified = missing + none_count + other
        if classified:
            rows.append((STRINGS["severity_critical"], STRINGS["prereq_pattern"].format(
                index="{index}", severity="{severity}", total=len(prereq),
                missing=missing, none_count=none_count, other=other,
                other_keys=other_keys, classified=classified,
                recorded=recorded, estimate=estimate,
            )))

    names = collected_samples(data, "name_th")
    if names:
        recorded, estimate = pattern_context(data, "name_th", len(names))
        truncated = 0
        truncated_cases: list[str] = []
        misaligned = 0
        misaligned_cases: list[str] = []
        spelling = 0
        review_cases: list[str] = []
        for profile, sample in names:
            key = str(sample.get("key"))
            case = f"`{display_name(profile)}/{key}`"
            sample_class = classify_name_sample(profile, sample)
            is_truncated = sample_class == "truncation"
            is_misaligned = sample_class == "misalignment"
            spelling += sample_class == "spelling"
            truncated += is_truncated
            if is_truncated:
                truncated_cases.append(case)
            misaligned += is_misaligned
            if is_misaligned:
                misaligned_cases.append(case)
            if is_gt_review_candidate(profile, sample):
                review_cases.append(
                    f"{case} (gt=“{cell(sample.get('gt'))}”, pred=“{cell(sample.get('pred'))}”)"
                )
        if misaligned:
            rows.append((STRINGS["severity_critical"], STRINGS["name_misalignment_pattern"].format(
                index="{index}", severity="{severity}", total=len(names),
                misaligned=misaligned, cases=", ".join(misaligned_cases),
                recorded=recorded, estimate=estimate,
            )))
        if truncated:
            rows.append((STRINGS["severity_major"], STRINGS["name_truncation_pattern"].format(
                index="{index}", severity="{severity}", total=len(names),
                truncated=truncated, cases=", ".join(truncated_cases),
                recorded=recorded, estimate=estimate,
            )))
        if review_cases:
            rows.append((STRINGS["severity_major"], STRINGS["ground_truth_review_pattern"].format(
                index="{index}", severity="{severity}", count=len(review_cases),
                cases="; ".join(review_cases),
            )))
        if spelling:
            rows.append((STRINGS["severity_minor"], STRINGS["name_spelling_pattern"].format(
                index="{index}", severity="{severity}", total=len(names),
                spelling=spelling, recorded=recorded, estimate=estimate,
            )))

    ctype = collected_samples(data, "ctype")
    if ctype:
        recorded, estimate = pattern_context(data, "ctype", len(ctype))
        directions = Counter(
            f"{cell(sample.get('gt'))}→{cell(sample.get('pred'))}" for _, sample in ctype
        )
        rendered = ", ".join(
            f"{direction} {count}/{len(ctype)}" for direction, count in directions.most_common()
        )
        rows.append((STRINGS["severity_major"], STRINGS["ctype_pattern"].format(
            index="{index}", severity="{severity}", total=len(ctype), directions=rendered,
            recorded=recorded, estimate=estimate,
        )))

    credits = collected_samples(data, "credits")
    if credits:
        recorded, estimate = pattern_context(data, "credits", len(credits))
        dropped = sum(
            "หรือ" in str(sample.get("gt") or "")
            and "หรือ" not in str(sample.get("pred") or "")
            for _, sample in credits
        )
        wrong = sum(
            normalize_text(sample.get("gt")) != normalize_text(sample.get("pred"))
            and not (
                "หรือ" in str(sample.get("gt") or "")
                and "หรือ" not in str(sample.get("pred") or "")
            )
            for _, sample in credits
        )
        if dropped or wrong:
            rows.append((STRINGS["severity_major"], STRINGS["credits_pattern"].format(
                index="{index}", severity="{severity}", total=len(credits),
                dropped=dropped, wrong=wrong, recorded=recorded, estimate=estimate,
            )))

    severity_order = {
        STRINGS["severity_critical"]: 0,
        STRINGS["severity_major"]: 1,
        STRINGS["severity_minor"]: 2,
    }
    return sorted(rows, key=lambda item: severity_order[item[0]])


def render_pattern(pattern: tuple[str, str], index: int, body_only: bool = False) -> str:
    severity, template = pattern
    rendered = template.format(index=index, severity=severity)
    if body_only and ":** " in rendered:
        return rendered.split(":** ", 1)[1]
    return rendered


def concise_pattern(pattern: tuple[str, str]) -> str:
    """Render a short TL;DR derived from the highest-ranked Section 8 issue."""
    body = render_pattern(pattern, 1, body_only=True)
    parts = body.split("`")
    attribute = parts[1] if len(parts) > 2 else "OCR"
    return STRINGS["tldr_issue_pointer"].format(attribute=attribute)


def abstention_evidence_note(data: dict[str, Any]) -> str:
    counts = {
        name: int(value)
        for name in profiles(data)
        if (value := finite_number(get(data[name], "slices", "none", "total"))) is not None
    }
    if not counts:
        return STRINGS["abstention_weak_missing"]
    unique = set(counts.values())
    if len(unique) == 1 and len(counts) == len(profiles(data)):
        return STRINGS["abstention_weak_uniform"].format(n=next(iter(unique)))
    rendered = ", ".join(f"`{display_name(name)}` n={count}" for name, count in counts.items())
    return STRINGS["abstention_weak_varied"].format(counts=rendered)


def issue_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles(data):
        for key, metric in attributes(data[profile]).items():
            cer = finite_number(metric.get("cer"))
            em = finite_number(metric.get("exact_match_acc"))
            severity = max(cer or 0.0, 1.0 - em if em is not None else 0.0)
            if severity <= 0:
                continue
            rows.append({
                "profile": profile,
                "key": key,
                "label": metric.get("label") or key,
                "cer": cer,
                "em": em,
                "n": metric.get("n_items"),
                "severity": severity,
                "samples": metric.get("error_samples") or [],
            })
    return sorted(rows, key=lambda row: (-row["severity"], row["profile"], row["key"]))


def md_table(
    headers: Iterable[str], rows: Iterable[Iterable[Any]], *, cell_limit: int | None = 100
) -> list[str]:
    headers = list(headers)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(":---" for _ in headers) + " |"]
    lines.extend(
        "| " + " | ".join(cell(item, cell_limit) for item in row) + " |"
        for row in rows
    )
    return lines


def reliability(data: dict[str, Any]) -> str:
    totals = [finite_number(get(data[name], "heldout", "total")) for name in profiles(data)]
    stable = [get(data[name], "stability", "stable") for name in profiles(data)]
    usable = [int(value) for value in totals if value is not None]
    if not usable:
        return STRINGS["reliability_unavailable"]
    minimum = min(usable)
    stability = all(value is True for value in stable) and len(stable) == len(usable)
    return STRINGS["reliability_detail"].format(
        level=STRINGS["reliability_moderate"] if minimum < 30 else STRINGS["reliability_high"],
        stability=STRINGS["stable_all"] if stability else STRINGS["stable_not_all"],
        minimum=minimum,
    )


def make_charts(data: dict[str, Any], image_dir: Path) -> list[str]:
    """Create optional charts when matplotlib exists; absence is not an error."""
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError:
        return []
    image_dir.mkdir(parents=True, exist_ok=True)
    names = profiles(data)
    labels = [display_name(name) for name in names]
    f1 = [finite_number(profile_ocr_f1(data[name])) for name in names]
    acc = [metric_accuracy(get(data[name], "heldout")) for name in names]
    generated: list[str] = []
    if any(value is not None for value in f1):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(labels, [value if value is not None else 0 for value in f1], color="#4C78A8")
        ax.set_ylim(0, 1.05); ax.set_ylabel(STRINGS["chart_ocr_axis"]); ax.tick_params(axis="x", rotation=20)
        fig.tight_layout(); path = image_dir / "eval_overview.png"; fig.savefig(path, dpi=160); plt.close(fig)
        generated.append(path.name)
    if any(value is not None for value in acc):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(labels, [value if value is not None else 0 for value in acc], color="#59A14F")
        ax.set_ylim(0, 1.05); ax.set_ylabel(STRINGS["chart_rag_axis"]); ax.tick_params(axis="x", rotation=20)
        fig.tight_layout(); path = image_dir / "rag_performance.png"; fig.savefig(path, dpi=160); plt.close(fig)
        generated.append(path.name)
    return generated


def generate(data: dict[str, Any], image_names: list[str] | None = None) -> str:
    names = profiles(data)
    issues = issue_rows(data)
    patterns = error_pattern_rows(data)
    abstention_note = abstention_evidence_note(data)
    heldout_perfect = all(metric_accuracy(get(data[name], "heldout")) == 1 for name in names) if names else False
    citations_perfect = all(get(data[name], "heldout", "citation_coverage") == 1 for name in names) if names else False
    lines = [START, STRINGS["section_title"], "", STRINGS["tldr_heading"], ""]
    capability = STRINGS["capabilities_perfect"] if heldout_perfect else STRINGS["capabilities_review"]
    citation = STRINGS["citation_uniform"] if citations_perfect else STRINGS["citation_not_uniform"]
    vulnerability = concise_pattern(patterns[0]) if patterns else STRINGS["no_ocr_failures"]
    lines += [
        f"- **{STRINGS['capabilities_label']}:** {capability}; {citation}",
        f"- **{STRINGS['vulnerabilities_label']}:** {vulnerability}",
        f"- **{STRINGS['reliability_label']}:** {reliability(data)}",
        f"- **{STRINGS['abstention_limit_label']}:** {abstention_note}",
    ]
    if image_names:
        alt_by_name = {
            "eval_overview.png": STRINGS["chart_ocr_alt"],
            "rag_performance.png": STRINGS["chart_rag_alt"],
        }
        lines += ["", " ".join(f"![{alt_by_name.get(name, name)}](docs/img/{name})" for name in image_names)]

    lines += ["", STRINGS["profiles_heading"], ""]
    profile_rows = []
    for name in names:
        info = PROFILE_INFO.get(name, {})
        gt_relative = GT_FILES.get(name)
        gt_available = bool(gt_relative and repo_path(gt_relative).is_file())
        profile_rows.append([
            f"`{display_name(name)}`", info.get("program"), info.get("variant"),
            f"`{info.get('folder')}`" if info.get("folder") else "n/a",
            STRINGS["available_yes"] if gt_available else STRINGS["available_no"],
        ])
    lines += md_table([
        STRINGS["col_profile"], STRINGS["col_program"], STRINGS["col_variant"],
        STRINGS["col_source_folder"], STRINGS["col_ocr_gt_available"],
    ], profile_rows)
    lines += ["", STRINGS["mapping_confirmed"] if dsba_mapping_confirmed() else STRINGS["mapping_unconfirmed"]]

    lines += ["", STRINGS["profile_summary_heading"], ""]
    summary_rows = []
    for name in names:
        report = data[name]
        abstain_p = get(report, "abstention", "abstain_precision")
        stable = get(report, "stability", "stable")
        heldout_n = get(report, "heldout", "total")
        none_n = get(report, "slices", "none", "total")
        summary_rows.append([
            f"`{display_name(name)}`", ocr_f1_with_n(report), score(get(report, "heldout")),
            pct_with_n(get(report, "heldout", "citation_coverage"), heldout_n),
            f"{pct(abstain_p)} / {pct_with_n(get(report, 'abstention', 'expected_abstain_accuracy'), none_n)}",
            STRINGS["stable_yes"] if stable is True else STRINGS["stable_no"] if stable is False else "n/a",
            f"{fixed(get(report, 'heldout', 'mean_seconds'))} (n={number(heldout_n)})",
        ])
    lines += md_table(
        [STRINGS["col_profile"], STRINGS["col_ocr_f1"], STRINGS["col_heldout_accuracy"], STRINGS["col_citation"], STRINGS["col_abstain_pr"], STRINGS["col_stability"], STRINGS["col_latency"]],
        summary_rows,
    )

    lines += ["", STRINGS["ocr_breakdown_heading"], "", STRINGS["alignment_heading"], ""]
    alignment_rows = []
    for name in names:
        alignment = get(data[name], "ocr", "alignment") or {}
        alignment_rows.append([
            f"`{display_name(name)}`", pct(alignment.get("precision")), pct(alignment.get("recall")),
            number(alignment.get("matched")), number(alignment.get("missed")),
            number(alignment.get("spurious")), number(alignment.get("gt_total")),
            number(alignment.get("pred_total")),
        ])
    lines += md_table([
        STRINGS["col_profile"], STRINGS["col_precision"], STRINGS["col_recall"],
        STRINGS["col_matched"], STRINGS["col_missed"], STRINGS["col_spurious"],
        STRINGS["col_gt_n"], STRINGS["col_pred_n"],
    ], alignment_rows)
    lines += ["", STRINGS["primary_profile_heading"], ""]
    primary = data.get("dsba", {})
    primary_rows = [[metric.get("label") or key, number(metric.get("n_items")), pct(metric.get("cer")), pct(metric.get("wer")), pct(metric.get("exact_match_acc"))] for key, metric in attributes(primary).items()]
    lines += md_table([STRINGS["col_attribute"], STRINGS["col_sample_n"], STRINGS["metric_cer"], STRINGS["metric_wer"], STRINGS["metric_exact_match"]], primary_rows or [["n/a"] * 5])
    lines += ["", "<details>", f"<summary>{STRINGS['other_profiles_summary']}</summary>", ""]
    for name in names:
        if name == "dsba":
            continue
        lines += [f"#### `{display_name(name)}`", ""]
        rows = [[metric.get("label") or key, number(metric.get("n_items")), pct(metric.get("cer")), pct(metric.get("wer")), pct(metric.get("exact_match_acc"))] for key, metric in attributes(data[name]).items()]
        lines += md_table([STRINGS["col_attribute"], STRINGS["metric_n"], STRINGS["metric_cer"], STRINGS["metric_wer"], STRINGS["metric_exact_match"]], rows or [["n/a"] * 5]) + [""]
    lines += ["</details>", "", STRINGS["error_samples_heading"], ""]
    sample_rows = []
    # Prefer breadth: one real example from each of the five worst measurements.
    for issue in issues:
        if not issue["samples"]:
            continue
        sample = issue["samples"][0]
        sample_rows.append([
            display_name(issue["profile"]), f"{issue['label']} / {sample.get('key', 'n/a')}",
            sample.get("gt"), sample.get("pred"),
            f"{STRINGS['metric_cer']} {pct(issue['cer'])}; {STRINGS['metric_exact_match']} {pct(issue['em'])}",
        ])
        if len(sample_rows) == 5:
            break
    lines += md_table([STRINGS["col_profile"], STRINGS["col_attribute_query"], STRINGS["col_expected"], STRINGS["col_actual"], STRINGS["col_error_type"]], sample_rows or [["n/a"] * 5])

    lines += ["", "<details>", f"<summary>{STRINGS['dsba_no_coop_samples_summary']}</summary>", "", STRINGS["dsba_no_coop_samples_heading"], ""]
    no_coop_attributes = get(data.get("dsba-no-coop", {}), "ocr", "attributes") or {}
    for attribute in ("name_th", "name_en", "prereq"):
        samples = get(no_coop_attributes, attribute, "error_samples") or []
        rows = []
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            sample_class = (
                classify_name_sample("dsba-no-coop", sample, attribute)
                if attribute in {"name_th", "name_en"}
                else "other"
            )
            rows.append([
                sample.get("key"), sample.get("gt"), sample.get("pred"), sample_class,
            ])
        lines += [f"##### `{attribute}`", ""]
        lines += md_table(
            [STRINGS["col_key"], STRINGS["col_gt"], STRINGS["col_pred"], STRINGS["col_class"]],
            rows or [["n/a"] * 4],
            cell_limit=None,
        ) + [""]
    lines += ["</details>"]

    lines += ["", STRINGS["rag_heading"], ""]
    slice_names = sorted({key for name in names for key in (get(data[name], "slices") or {})})
    rag_rows = []
    for name in names:
        none_n = get(data[name], "slices", "none", "total")
        heldout_n = finite_number(get(data[name], "heldout", "total"))
        parsed_none_n = finite_number(none_n)
        real_n = int(heldout_n - parsed_none_n) if heldout_n is not None and parsed_none_n is not None else None
        false_abstains = finite_number(get(data[name], "abstention", "false_abstains"))
        false_abstains_text = (
            f"{int(false_abstains)}/{real_n}"
            if false_abstains is not None and real_n is not None else number(false_abstains)
        )
        rag_rows.append([
            f"`{display_name(name)}`", score(get(data[name], "heldout")),
            *[score(get(data[name], "slices", slice_name)) for slice_name in slice_names],
            pct_with_n(get(data[name], "abstention", "expected_abstain_accuracy"), none_n),
            pct(get(data[name], "abstention", "abstain_precision")),
            false_abstains_text,
            pct_with_n(get(data[name], "abstention", "real_answer_recall"), real_n),
            number(get(data[name], "stability", "repeats")),
        ])
    lines += md_table([
        STRINGS["col_profile"], STRINGS["metric_heldout"], *slice_names,
        STRINGS["col_expected_not_found"], STRINGS["col_abstain_precision"],
        STRINGS["col_false_abstains"], STRINGS["col_real_answer_recall"],
        STRINGS["col_runs"],
    ], rag_rows)
    lines += ["", STRINGS["stability_explanation"]]

    lines += ["", STRINGS["baseline_heading"], ""]
    baseline_rows = []
    for name in names:
        baseline = get(data[name], "baseline_v1")
        base_acc = metric_accuracy(get(baseline, "heldout"))
        current_acc = metric_accuracy(get(data[name], "heldout"))
        delta = None if finite_number(base_acc) is None or finite_number(current_acc) is None else float(current_acc) - float(base_acc)
        baseline_rows.append([
            f"`{display_name(name)}`", score(get(baseline, "heldout")), score(get(data[name], "heldout")),
            pp(delta), ocr_f1_with_n(baseline), ocr_f1_with_n(data[name]),
        ])
    lines += md_table([STRINGS["col_profile_metric"], STRINGS["col_baseline_accuracy"], STRINGS["col_current_accuracy"], STRINGS["col_delta"], STRINGS["col_baseline_f1"], STRINGS["col_current_f1"]], baseline_rows)
    missing_baselines = [
        display_name(name)
        for name in names
        if not isinstance(get(data[name], "baseline_v1"), dict)
    ]
    if missing_baselines:
        lines += ["", STRINGS["baseline_missing_note"].format(
            profiles=", ".join(f"`{name}`" for name in missing_baselines)
        )]
    comparable_f1 = [
        (finite_number(profile_ocr_f1(get(data[name], "baseline_v1"))), finite_number(profile_ocr_f1(data[name])))
        for name in names
        if finite_number(profile_ocr_f1(get(data[name], "baseline_v1"))) is not None
        and finite_number(profile_ocr_f1(data[name])) is not None
    ]
    lines += ["", STRINGS["ocr_f1_unchanged"] if comparable_f1 and all(old == new for old, new in comparable_f1) else STRINGS["ocr_f1_changed"]]

    lines += ["", STRINGS["metric_matrix_heading"], ""]
    lines += md_table(
        [STRINGS["col_metric"], STRINGS["col_high_meaning"], STRINGS["col_low_meaning"], STRINGS["col_impact"]],
        [
            [STRINGS["metric_field_recall"], STRINGS["field_recall_high"], STRINGS["field_recall_low"], STRINGS["field_recall_impact"]],
            [STRINGS["metric_field_precision"], STRINGS["field_precision_high"], STRINGS["field_precision_low"], STRINGS["field_precision_impact"]],
            [f"{STRINGS['metric_cer']} / {STRINGS['metric_wer']}", STRINGS["cer_wer_high"], STRINGS["cer_wer_low"], STRINGS["cer_wer_impact"]],
            [STRINGS["metric_exact_match"], STRINGS["exact_match_high"], STRINGS["exact_match_low"], STRINGS["exact_match_impact"]],
            [STRINGS["metric_abstain_precision"], STRINGS["abstain_high"], STRINGS["abstain_low"], STRINGS["abstain_impact"]],
            [STRINGS["metric_false_abstain"], STRINGS["false_abstain_high"], STRINGS["false_abstain_low"], STRINGS["false_abstain_impact"]],
            [STRINGS["metric_abstain_recall"], STRINGS["abstain_recall_high"], STRINGS["abstain_recall_low"], STRINGS["abstain_recall_impact"]],
            [STRINGS["metric_citation_coverage"], STRINGS["citation_high"], STRINGS["citation_low"], STRINGS["citation_impact"]],
        ],
    )
    lines += ["", STRINGS["thai_wer_note"]]

    lines += ["", STRINGS["reliability_heading"], ""]
    sample_bits = []
    heldout_sizes = []
    for name in names:
        held_n = get(data[name], "heldout", "total")
        parsed_held_n = finite_number(held_n)
        if parsed_held_n is not None:
            heldout_sizes.append(int(parsed_held_n))
        ocr_n = get(data[name], "ocr", "alignment", "gt_total")
        sample_template = (
            STRINGS["sample_profile_with_ocr"]
            if finite_number(ocr_n) is not None else STRINGS["sample_profile_without_ocr"]
        )
        sample_bits.append(sample_template.format(
            name=display_name(name), held_n=number(held_n), ocr_n=number(ocr_n)
        ))
    smallest_note = (
        STRINGS["smallest_sample"].format(minimum=min(heldout_sizes))
        if heldout_sizes else
        STRINGS["sample_unavailable"]
    )
    lines += [
        f"- **{STRINGS['sample_assessment_label']}:** {'; '.join(sample_bits)} {smallest_note}",
        f"- **{STRINGS['perfect_score_label']}:** {STRINGS['perfect_score_text']}",
        f"- **{STRINGS['variance_label']}:** {STRINGS['variance_text']}",
        f"- **{STRINGS['abstention_limit_label']}:** {abstention_note}",
    ]
    lines += ["", STRINGS["gold_table_heading"], ""]
    gold_rows = []
    for name in names:
        known = metric_accuracy(get(data[name], "known_gold"))
        held = metric_accuracy(get(data[name], "heldout"))
        gap = None if finite_number(known) is None or finite_number(held) is None else float(held) - float(known)
        gold_rows.append([
            f"`{display_name(name)}`", score(get(data[name], "known_gold")),
            score(get(data[name], "heldout")), pp(gap),
        ])
    lines += md_table([
        STRINGS["col_profile"], STRINGS["col_known_gold"],
        STRINGS["col_heldout_count"], STRINGS["col_delta"],
    ], gold_rows)

    lines += ["", STRINGS["issues_heading"], ""]
    lines += [STRINGS["name_rule"].format(
        threshold=f"{NAME_SIMILARITY_THRESHOLD:.2f}"
    ), "", STRINGS["error_sample_limit_note"].format(limit=ERROR_SAMPLE_LIMIT), ""]
    if patterns:
        for index, pattern in enumerate(patterns, 1):
            lines.append(render_pattern(pattern, index))
        next_issue_index = len(patterns) + 1
    else:
        lines.append(STRINGS["pattern_none"].format(
            index=1, severity=STRINGS["severity_minor"]
        ))
        next_issue_index = 2

    dsba_no_coop = data.get("dsba-no-coop")
    if isinstance(dsba_no_coop, dict) and not isinstance(dsba_no_coop.get("ocr"), dict):
        gt_file = GT_FILES["dsba-no-coop"]
        template = (
            STRINGS["dsba_no_coop_missing_ocr_with_gt"]
            if repo_path(gt_file).is_file()
            else STRINGS["dsba_no_coop_missing_ocr_without_gt"]
        )
        lines.append(template.format(
            index=next_issue_index, severity=STRINGS["severity_major"], gt_file=gt_file
        ))

    lines += ["", "---", "", STRINGS["rerun"], "", STRINGS["unverified_heading"], ""]
    missing_ocr = [name for name in names if not isinstance(get(data[name], "ocr"), dict)]
    if missing_ocr:
        lines.append(STRINGS["unverified_ocr"].format(
            profiles=", ".join(f"`{display_name(name)}`" for name in missing_ocr)
        ))
    lines += [
        STRINGS["unverified_abstain_n"], STRINGS["unverified_independence"],
        STRINGS["unverified_misalignment_cause"], END,
    ]
    return "\n".join(lines) + "\n"


def inject(readme_text: str, section: str) -> str:
    if START in readme_text or END in readme_text:
        if readme_text.count(START) != 1 or readme_text.count(END) != 1:
            raise ValueError(STRINGS["marker_error"])
        before, remainder = readme_text.split(START, 1)
        _, after = remainder.split(END, 1)
        return before.rstrip() + "\n\n" + section.rstrip() + "\n" + after.lstrip("\n")
    prefix = readme_text.rstrip() or STRINGS["readme_title"]
    return prefix + "\n\n" + section


def audit(section: str, data: dict[str, Any]) -> None:
    candidates: list[str] = []
    for name in profiles(data):
        candidates += [
            f"`{display_name(name)}`", score(get(data[name], "heldout")),
            pct(get(data[name], "heldout", "citation_coverage")),
            fixed(get(data[name], "heldout", "mean_seconds")),
            pct(get(data[name], "abstention", "abstain_precision")),
        ]
        f1 = pct(profile_ocr_f1(data[name]))
        if f1 != "n/a":
            candidates.append(f1)
        candidates.extend(
            score(metric) for metric in (get(data[name], "slices") or {}).values()
        )
    candidates = [value for value in candidates if value != "n/a"]
    checks = random.Random(20260921).sample(candidates, min(10, len(candidates)))
    missing = [value for value in checks if value not in section]
    if missing:
        raise AssertionError(STRINGS["audit_error"].format(missing=missing))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default="work/robustness_summary.json")
    parser.add_argument("--readme", default="Lab09_report.md")
    parser.add_argument("--image-dir", default="docs/img")
    parser.add_argument("--no-charts", action="store_true")
    args = parser.parse_args()
    json_path, readme_path = Path(args.json), Path(args.readme)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(STRINGS["json_type_error"])
    images = [] if args.no_charts else make_charts(data, Path(args.image_dir))
    section = generate(data, images)
    audit(section, data)
    original = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    updated = inject(original, section)
    readme_path.write_text(updated, encoding="utf-8", newline="\n")
    print(STRINGS["updated_message"].format(readme=readme_path, json=json_path))
    print(STRINGS["profile_chart_message"].format(profiles=len(profiles(data)), charts=len(images)))


if __name__ == "__main__":
    main()
