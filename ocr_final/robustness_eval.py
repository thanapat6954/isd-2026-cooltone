"""Held-out, stability, slice, abstention, and OCR evaluation for Lab 7B/8B."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scr" / "ocr_system"))
import lab8b_curriculum_db as lab8  # noqa: E402


PROFILES = {
    "dsba": ROOT / "work" / "lab8b_dsba_coop",
    "dsba-no-coop": ROOT / "work" / "lab8b_dsba_no_coop",
    "ai": ROOT / "work" / "lab8b_ai",
    "it-coop": ROOT / "work" / "lab8b_it_coop",
    "it-no-coop": ROOT / "work" / "lab8b_it_no_coop",
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _tier(value: float) -> str:
    if value > 0.91:
        return "full (>91%)"
    if value >= 0.80:
        return "middle (80–90%)"
    return "lower (<80%)"


def generate_heldout(conn) -> list[dict]:
    """Create a deterministic question set that is distinct from DSBA's gold 30."""
    courses = [dict(row) for row in conn.execute(
        "SELECT code, name_th, credits FROM course "
        "WHERE name_th IS NOT NULL ORDER BY code"
    ).fetchall()]
    terms = [dict(row) for row in conn.execute(
        "SELECT year, semester, credits, n_courses FROM v_semester_credits "
        "ORDER BY year, semester"
    ).fetchall()]
    if len(courses) < 6 or len(terms) < 2:
        raise ValueError("ฐานข้อมูลมีข้อมูลไม่พอสร้าง held-out set")

    picks = [courses[i] for i in (2, len(courses) // 3, (2 * len(courses)) // 3,
                                   -3, -4, -1)]
    term_picks = [terms[2], terms[-1]]
    questions = [
        {
            "id": "H01", "slice": "value",
            "question": f"รายวิชารหัส {picks[0]['code']} มีชื่อภาษาไทยว่าอะไร",
            "expect": {"type": "value", "value": picks[0]["name_th"]},
        },
        {
            "id": "H02", "slice": "value",
            "question": f"จำนวนหน่วยกิตของรหัส {picks[1]['code']} เท่ากับเท่าไร",
            "expect": {"type": "value", "value": picks[1]["credits"]},
        },
        {
            "id": "H03", "slice": "value",
            "question": f"รายวิชารหัส {picks[2]['code']} มีชื่อภาษาไทยว่าอะไร",
            "expect": {"type": "value", "value": picks[2]["name_th"]},
        },
        {
            "id": "H04", "slice": "value",
            "question": f"จำนวนหน่วยกิตของรหัส {picks[3]['code']} เท่ากับเท่าไร",
            "expect": {"type": "value", "value": picks[3]["credits"]},
        },
    ]
    for number, term in enumerate(term_picks, 5):
        questions.append({
            "id": f"H{number:02d}", "slice": "count",
            "question": (
                f"ปี {term['year']} ภาคเรียน {term['semester']} "
                "ต้องลงทะเบียนกี่วิชา"
            ),
            "expect": {"type": "count", "value": term["n_courses"]},
        })
    for number, term in enumerate(term_picks, 7):
        codes = [row[0] for row in conn.execute(
            "SELECT code FROM plan_item WHERE year=? AND semester=? ORDER BY code",
            (term["year"], term["semester"]),
        ).fetchall()]
        questions.append({
            "id": f"H{number:02d}", "slice": "set",
            "question": (
                f"โปรดแสดงรหัสทั้งหมดในแผนปี {term['year']} "
                f"ภาคเรียน {term['semester']}"
            ),
            "expect": {"type": "set", "value": codes},
        })
    questions.extend([
        {
            "id": "H09", "slice": "none",
            "question": "รายวิชารหัส 88888888 มีชื่อภาษาไทยว่าอะไร",
            "expect": {"type": "none"},
        },
        {
            "id": "H10", "slice": "none",
            "question": "โปรดแสดงรหัสทั้งหมดในแผนปี 7 ภาคเรียน 3",
            "expect": {"type": "none"},
        },
        {
            "id": "H11", "slice": "value",
            "question": f"รายวิชารหัส {picks[4]['code']} มีชื่อภาษาไทยว่าอะไร",
            "expect": {"type": "value", "value": picks[4]["name_th"]},
        },
        {
            "id": "H12", "slice": "value",
            "question": f"จำนวนหน่วยกิตของรหัส {picks[5]['code']} เท่ากับเท่าไร",
            "expect": {"type": "value", "value": picks[5]["credits"]},
        },
    ])
    return questions


def _signature(item: dict) -> str:
    stable = {
        "sql": item.get("sql"),
        "rows": item.get("rows"),
        "answer": item.get("answer"),
        "citations": item.get("citations"),
        "error": item.get("error"),
    }
    return json.dumps(stable, ensure_ascii=False, sort_keys=True)


def run_questions(conn, questions: list[dict], repeats: int) -> list[list[dict]]:
    runs = []
    for run_no in range(1, repeats + 1):
        items = []
        for question in questions:
            started = time.perf_counter()
            got = lab8.ask(conn, question["question"], verbose=False)
            correct, why = lab8.score_one(question["expect"], got)
            items.append({
                **question,
                "run": run_no,
                "correct": correct,
                "why": why,
                "sql": got.get("sql"),
                "rows": got.get("rows") or [],
                "answer": got.get("answer"),
                "citations": got.get("citations") or [],
                "citation_covered": bool(got.get("citation_covered")),
                "error": got.get("error"),
                "seconds": round(time.perf_counter() - started, 3),
            })
        runs.append(items)
    return runs


def summarize(profile: str, runs: list[list[dict]], ocr: dict | None) -> dict:
    first = runs[0]
    by_slice: dict[str, list[dict]] = defaultdict(list)
    for item in first:
        by_slice[item["expect"]["type"]].append(item)
    slices = {
        name: {
            "correct": sum(bool(item["correct"]) for item in items),
            "total": len(items),
            "accuracy": round(sum(bool(item["correct"]) for item in items) / len(items), 4),
        }
        for name, items in sorted(by_slice.items())
    }

    unstable = []
    for index, question in enumerate(first):
        signatures = {_signature(run[index]) for run in runs}
        if len(signatures) != 1:
            unstable.append({"id": question["id"], "question": question["question"]})

    real = [item for item in first if item["expect"]["type"] != "none"]
    expected_none = [item for item in first if item["expect"]["type"] == "none"]
    abstained = [item for item in first if not item["rows"]]
    true_abstain = sum(item["expect"]["type"] == "none" for item in abstained)
    abstain_precision = true_abstain / len(abstained) if abstained else 1.0

    result: dict[str, Any] = {
        "profile": profile,
        "heldout": {
            "correct": sum(bool(item["correct"]) for item in first),
            "total": len(first),
            "accuracy": round(sum(bool(item["correct"]) for item in first) / len(first), 4),
            "citation_coverage": round(
                sum(bool(item["citation_covered"]) for item in first) / len(first), 4),
            "mean_seconds": round(statistics.mean(item["seconds"] for item in first), 3),
            "under_5_seconds": sum(item["seconds"] < 5 for item in first),
        },
        "stability": {
            "repeats": len(runs),
            "stable": len(unstable) == 0,
            "unstable_count": len(unstable),
            "unstable_questions": unstable,
        },
        "slices": slices,
        "abstention": {
            "real_answer_recall": round(
                sum(bool(item["correct"]) for item in real) / len(real), 4),
            "expected_abstain_accuracy": round(
                sum(bool(item["correct"]) for item in expected_none) / len(expected_none), 4),
            "abstain_precision": round(abstain_precision, 4),
            "false_abstains": sum(item["expect"]["type"] != "none" for item in abstained),
        },
    }
    if ocr:
        attrs = ocr.get("attributes") or {}
        name_th = attrs.get("name_th") or {}
        result["ocr"] = {
            "alignment": ocr.get("alignment"),
            "name_th_exact": name_th.get("exact_match_acc"),
            "name_th_wer": name_th.get("wer"),
            "name_th_tier": _tier(float(name_th.get("exact_match_acc") or 0)),
            "attributes": attrs,
        }
    return result


def summarize_saved_eval(items: list[dict]) -> dict:
    """Summarize the original repeatedly-used gold set without rerunning it."""
    by_slice: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_slice[(item.get("expect") or {}).get("type", "value")].append(item)
    slices = {
        name: {
            "correct": sum(bool(item.get("correct")) for item in rows),
            "total": len(rows),
            "accuracy": round(sum(bool(item.get("correct")) for item in rows) / len(rows), 4),
        }
        for name, rows in sorted(by_slice.items())
    }
    real = [item for item in items if (item.get("expect") or {}).get("type") != "none"]
    expected_none = [item for item in items if (item.get("expect") or {}).get("type") == "none"]
    abstained = [item for item in items if int(item.get("n_rows") or 0) == 0]
    true_abstain = sum((item.get("expect") or {}).get("type") == "none" for item in abstained)
    return {
        "correct": sum(bool(item.get("correct")) for item in items),
        "total": len(items),
        "accuracy": round(sum(bool(item.get("correct")) for item in items) / len(items), 4),
        "slices": slices,
        "abstention": {
            "real_answer_recall": round(
                sum(bool(item.get("correct")) for item in real) / len(real), 4),
            "expected_abstain_accuracy": round(
                sum(bool(item.get("correct")) for item in expected_none) / len(expected_none), 4),
            "abstain_precision": round(
                true_abstain / len(abstained) if abstained else 1.0, 4),
            "false_abstains": sum(
                (item.get("expect") or {}).get("type") != "none" for item in abstained),
        },
    }


def evaluate_profile(name: str, folder: Path, repeats: int) -> dict:
    database = folder / "curriculum.db"
    if not database.is_file():
        raise FileNotFoundError(database)
    output = folder / "robustness"
    output.mkdir(parents=True, exist_ok=True)
    questions_path = output / "heldout_questions_v2.json"
    conn = lab8.open_db(database, readonly=True)
    if questions_path.is_file():
        questions = _json(questions_path)
    else:
        questions = generate_heldout(conn)
        questions_path.write_text(
            json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")

    warm_row = conn.execute(
        "SELECT code FROM course WHERE code GLOB '[0-9]*' ORDER BY code LIMIT 1"
    ).fetchone()
    if warm_row:
        lab8.ask(
            conn,
            f"รายวิชารหัส {warm_row['code']} มีจำนวนหน่วยกิตเท่าใด",
            verbose=False,
        )
    runs = run_questions(conn, questions, repeats)
    conn.close()
    (output / "heldout_runs_v2.json").write_text(
        json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
    evaluation_path = folder / "lab7b" / "evaluation.json"
    ocr = (_json(evaluation_path).get("vlm") if evaluation_path.is_file() else None)
    report = summarize(name, runs, ocr)
    known_eval_path = folder / "eval_result.json"
    if known_eval_path.is_file():
        report["known_gold"] = summarize_saved_eval(_json(known_eval_path))
    baseline_path = output / "baseline_v1_report.json"
    if baseline_path.is_file():
        report["baseline_v1"] = _json(baseline_path)
    (output / "robustness_report_v2.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--program", default="all",
        choices=["all", *PROFILES],
        help="program/plan to evaluate",
    )
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be at least 1")

    selected = PROFILES if args.program == "all" else {args.program: PROFILES[args.program]}
    reports = {}
    for name, folder in selected.items():
        print(f"\n[{name}] held-out × {args.repeats}")
        report = evaluate_profile(name, folder, args.repeats)
        reports[name] = report
        held = report["heldout"]
        stable = report["stability"]
        print(
            f"  accuracy {held['correct']}/{held['total']} ({held['accuracy']:.0%}) · "
            f"citations {held['citation_coverage']:.0%} · "
            f"stable={stable['stable']} · under5={held['under_5_seconds']}/{held['total']}"
        )
    combined = ROOT / "work" / "robustness_summary.json"
    combined_reports = _json(combined) if combined.is_file() else {}
    combined_reports.update(reports)
    combined.write_text(
        json.dumps(combined_reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {combined}")


if __name__ == "__main__":
    main()
