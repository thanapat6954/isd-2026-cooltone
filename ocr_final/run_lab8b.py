"""Run Lab 7B OCR -> Lab 8B SQLite for the supported curricula."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LAB7 = ROOT / "scr" / "ocr_system" / "lab7b_curriculum.py"
LAB8 = ROOT / "scr" / "ocr_system" / "lab8b_curriculum_db.py"
GENERAL_EDUCATION = ROOT / "data" / "ground_truth" / "general_education_ground_truth.json"
PYTHON = next(
    (
        candidate
        for candidate in (
            ROOT / "venv" / "Scripts" / "python.exe",
            ROOT / "venv" / "bin" / "python",
            ROOT / ".venv" / "Scripts" / "python.exe",
            ROOT / ".venv" / "bin" / "python",
        )
        if candidate.is_file()
    ),
    Path(sys.executable),
)

# Page ranges were verified against the actual PDFs, not copied from DSBA.
PROFILES = {
    "dsba-coop": {
        "input": ROOT / "data" / "input" / "DSBA.pdf",
        # Lab 7B metrics compare academic-plan pages to the flat plan GT.  The
        # normalized master file remains available for clean Lab 8B imports.
        "gt": ROOT / "data" / "ground_truth" / "DSBA_academic_plan_coop.json",
        "pages": "30-36",
        "printed_page_offset": 1,
        "program_id": "DSBA-coop",
        "program_name": "วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ (สหกิจศึกษา)",
        "target_plan": "coop",
        "curriculum_version": 2565,
        "is_latest": True,
        "lab8_input": ROOT / "data" / "ground_truth" / "DSBA_ground_truth.json",
        "total_credits": 132,
        "out": ROOT / "work" / "lab8b_dsba_coop",
        "gold": ROOT / "work" / "lab8b_dsba_coop" / "gold_questions.json",
    },
    "dsba-no-coop": {
        "input": ROOT / "data" / "input" / "DSBA.pdf",
        "gt": ROOT / "data" / "ground_truth" / "DSBA_academic_plan_no_coop.json",
        "pages": "23-29",
        "printed_page_offset": 1,
        "program_id": "DSBA-no-coop",
        "program_name": "วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ (ไม่เข้าร่วมสหกิจศึกษา)",
        "target_plan": "no_coop",
        "curriculum_version": 2565,
        "is_latest": True,
        "lab8_input": ROOT / "data" / "ground_truth" / "DSBA_ground_truth.json",
        "total_credits": 132,
        "out": ROOT / "work" / "lab8b_dsba_no_coop",
        "gold": ROOT / "work" / "lab8b_dsba_no_coop" / "gold_questions.json",
    },
    "ai": {
        "input": ROOT / "data" / "input" / "AI.pdf",
        "gt": ROOT / "data" / "ground_truth" / "AIT_academic_plan.json",
        "pages": "23-26",
        "program_id": "AI",
        "curriculum_version": 2566,
        "is_latest": True,
        "program_name": "เทคโนโลยีปัญญาประดิษฐ์",
        "target_plan": "coop",
        "total_credits": 120,
        "out": ROOT / "work" / "lab8b_ai",
        "gold": ROOT / "work" / "lab8b_ai" / "gold_questions.json",
    },
    "it-no-coop": {
        "input": ROOT / "data" / "input" / "IT.pdf",
        "gt": ROOT / "data" / "ground_truth" / "IT_academic_plan_no_coop.json",
        "pages": "31-37",
        "printed_page_offset": 5,
        "program_id": "IT-no-coop",
        "program_name": "เทคโนโลยีสารสนเทศ (ไม่เข้าร่วมสหกิจศึกษา)",
        "target_plan": "no_coop",
        "curriculum_version": 2565,
        "is_latest": True,
        "total_credits": 129,
        "out": ROOT / "work" / "lab8b_it_no_coop",
        "gold": ROOT / "work" / "lab8b_it_no_coop" / "gold_questions.json",
    },
    "it-coop": {
        "input": ROOT / "data" / "input" / "IT.pdf",
        "gt": ROOT / "data" / "ground_truth" / "IT_academic_plan_coop.json",
        "pages": "38-44",
        "printed_page_offset": 5,
        "program_id": "IT-coop",
        "program_name": "เทคโนโลยีสารสนเทศ (สหกิจศึกษา)",
        "target_plan": "coop",
        "curriculum_version": 2565,
        "is_latest": True,
        "total_credits": 129,
        "out": ROOT / "work" / "lab8b_it_coop",
        "gold": ROOT / "work" / "lab8b_it_coop" / "gold_questions.json",
    },
    "dsba-2560-no-coop": {
        "input": ROOT / "data" / "input" / "DSBA-60.pdf",
        "gt": ROOT / "data" / "ground_truth" / "DSBA_2560_academic_plan_no_coop.json",
        "pages": "25-29",
        "printed_page_offset": 5,
        "program_id": "DSBA-no-coop",
        "program_name": "วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ (ไม่เข้าร่วมสหกิจศึกษา)",
        "target_plan": "no_coop",
        "curriculum_version": 2560,
        "is_latest": False,
        "total_credits": 126,
        "out": ROOT / "work" / "lab8b_dsba_2560_no_coop",
    },
    "dsba-2560-coop": {
        "input": ROOT / "data" / "input" / "DSBA-60.pdf",
        "gt": ROOT / "data" / "ground_truth" / "DSBA_2560_academic_plan_coop.json",
        "pages": "30-34",
        "printed_page_offset": 5,
        "program_id": "DSBA-coop",
        "program_name": "วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ (สหกิจศึกษา)",
        "target_plan": "coop",
        "curriculum_version": 2560,
        "is_latest": False,
        "total_credits": 126,
        "out": ROOT / "work" / "lab8b_dsba_2560_coop",
    },
    "it-2560-no-coop": {
        "input": ROOT / "data" / "input" / "IT-60.pdf",
        "gt": ROOT / "data" / "ground_truth" / "IT_2560_academic_plan_no_coop.json",
        "pages": "27-33",
        "printed_page_offset": 5,
        "program_id": "IT-no-coop",
        "program_name": "เทคโนโลยีสารสนเทศ (ไม่เข้าร่วมสหกิจศึกษา)",
        "target_plan": "no_coop",
        "curriculum_version": 2560,
        "is_latest": False,
        "total_credits": 130,
        "out": ROOT / "work" / "lab8b_it_2560_no_coop",
    },
    "it-2560-coop": {
        "input": ROOT / "data" / "input" / "IT-60.pdf",
        "gt": ROOT / "data" / "ground_truth" / "IT_2560_academic_plan_coop.json",
        "pages": "34-40",
        "printed_page_offset": 5,
        "program_id": "IT-coop",
        "program_name": "เทคโนโลยีสารสนเทศ (สหกิจศึกษา)",
        "target_plan": "coop",
        "curriculum_version": 2560,
        "is_latest": False,
        "total_credits": 130,
        "out": ROOT / "work" / "lab8b_it_2560_coop",
    },
    "bit-2565-no-coop": {
        "input": ROOT / "data" / "input" / "BIT-65.pdf",
        "gt": ROOT / "data" / "ground_truth" / "BIT_2565_academic_plan_no_coop.json",
        "pages": "26-30",
        "printed_page_offset": 5,
        "program_id": "BIT-no-coop",
        "program_name": "เทคโนโลยีสารสนเทศทางธุรกิจ (ไม่เข้าร่วมสหกิจศึกษา)",
        "target_plan": "no_coop",
        "curriculum_version": 2565,
        "is_latest": True,
        "total_credits": 126,
        "out": ROOT / "work" / "lab8b_bit_2565_no_coop",
    },
    "bit-2565-coop": {
        "input": ROOT / "data" / "input" / "BIT-65.pdf",
        "gt": ROOT / "data" / "ground_truth" / "BIT_2565_academic_plan_coop.json",
        "pages": "31-35",
        "printed_page_offset": 5,
        "program_id": "BIT-coop",
        "program_name": "เทคโนโลยีสารสนเทศทางธุรกิจ (สหกิจศึกษา)",
        "target_plan": "coop",
        "curriculum_version": 2565,
        "is_latest": True,
        "total_credits": 126,
        "out": ROOT / "work" / "lab8b_bit_2565_coop",
    },
    "bit-2560-no-coop": {
        "input": ROOT / "data" / "input" / "BIT-60.pdf",
        "gt": ROOT / "data" / "ground_truth" / "BIT_2560_academic_plan_no_coop.json",
        "pages": "23-26",
        "printed_page_offset": 5,
        "program_id": "BIT-no-coop",
        "program_name": "เทคโนโลยีสารสนเทศทางธุรกิจ (ไม่เข้าร่วมสหกิจศึกษา)",
        "target_plan": "no_coop",
        "curriculum_version": 2560,
        "is_latest": False,
        "total_credits": 126,
        "out": ROOT / "work" / "lab8b_bit_2560_no_coop",
    },
    "bit-2560-coop": {
        "input": ROOT / "data" / "input" / "BIT-60.pdf",
        "gt": ROOT / "data" / "ground_truth" / "BIT_2560_academic_plan_coop.json",
        "pages": "27-30",
        "printed_page_offset": 5,
        "program_id": "BIT-coop",
        "program_name": "เทคโนโลยีสารสนเทศทางธุรกิจ (สหกิจศึกษา)",
        "target_plan": "coop",
        "curriculum_version": 2560,
        "is_latest": False,
        "total_credits": 126,
        "out": ROOT / "work" / "lab8b_bit_2560_coop",
    },
}


def run(*args: object) -> None:
    subprocess.run([str(PYTHON), *(str(x) for x in args)], cwd=ROOT, check=True)


def run_profile(name: str, *, skip_lab7: bool, skip_eval: bool = False) -> None:
    profile = PROFILES[name]
    input_pdf = Path(profile["input"])
    gt = Path(profile["gt"])
    out = Path(profile["out"])
    lab7_out = out / "lab7b"
    lab7_out.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    if not input_pdf.is_file():
        raise SystemExit(f"ไม่พบ PDF สำหรับ {name}: {input_pdf}")
    if not skip_lab7:
        command: list[object] = [
            LAB7, "-i", input_pdf, "-p", "vlm", "--pages", profile["pages"],
            "-o", lab7_out,
        ]
        if gt.is_file():
            command.extend(["-g", gt, "--target-plan", profile["target_plan"]])
        run(*command)

    prediction = next(
        (p for p in (lab7_out / "pred_vlm.json", lab7_out / "pred_text.json") if p.exists()),
        None,
    )
    configured_lab8_input = profile.get("lab8_input")
    if prediction is None and configured_lab8_input is None:
        raise SystemExit(f"ไม่พบผล Lab 7B สำหรับ {name} ใน {lab7_out}")
    lab8_input = Path(configured_lab8_input or prediction)

    run(LAB8, "schema", "-o", out / "schema")
    import_command: list[object] = [
        LAB8, "import-lab7b", "-i", lab8_input, "-o", out / "curriculum.json",
        "--program-id", profile["program_id"],
        "--program-name", profile["program_name"], "--years", 4,
        "--target-plan", profile["target_plan"],
        "--plan", "no-coop" if profile["target_plan"] == "no_coop" else "coop",
    ]
    if profile.get("curriculum_version") is not None:
        import_command.extend(["--curriculum-version", profile["curriculum_version"]])
    if profile.get("is_latest"):
        import_command.append("--is-latest")
    if profile.get("total_credits") is not None:
        import_command.extend(["--total-credits", profile["total_credits"]])
    if profile.get("printed_page_offset") is not None:
        import_command.extend(["--printed-page-offset", profile["printed_page_offset"]])
    if profile.get("curriculum_version") == 2565 or name == "ai":
        import_command.extend(["--general-education", GENERAL_EDUCATION])
    run(*import_command)
    run(LAB8, "load", "-i", out / "curriculum.json", "-d", out / "curriculum.db", "--replace")
    identity_reviews = ROOT / "data" / "ground_truth" / "document_identity_reviews.json"
    if identity_reviews.is_file():
        run(ROOT / "scripts" / "ingest_identity_reviews.py", "--app-root", ROOT,
            "--reviews", identity_reviews, "--database", out / "curriculum.db", "--apply",
            "--output", out / "identity_review_ingest.json")
    # Reapply only hash-guarded book reviews after rebuilding; unknowns stay unknown.
    review_file = ROOT / "data" / "ground_truth" / "prerequisite_source_reviews.json"
    if review_file.is_file():
        run(ROOT / "scripts" / "ingest_prerequisite_reviews.py", "--app-root", ROOT,
            "--reviews", review_file, "--database", out / "curriculum.db", "--apply",
            "--output", out / "prerequisite_review_ingest.json")
    name_reviews = ROOT / 'data/ground_truth/old2560_name_reviews.json'
    if name_reviews.exists():
        run(ROOT / 'scripts/ingest_name_reviews.py', '--app-root', ROOT,
            '--database', out / 'curriculum.db', '--reviews', name_reviews, '--apply',
            '--output', out / 'name_review_ingest.json')
    # Source-reviewed relationships are ingested, never added while answering.
    if (ROOT / 'data/ground_truth/study_plan_db_review.json').is_file():
        run(ROOT / 'scripts/prepare_db_only.py', '--app-root', ROOT,
            '--output', out / 'study_db_backups.json')
        run(ROOT / 'scripts/migrate_study_evidence.py', '--app-root', ROOT,
            '--backups', out / 'study_db_backups.json', '--database', out / 'curriculum.db',
            '--apply', '--output', out / 'study_db_ingest.json')
    run(LAB8, "verify", "-d", out / "curriculum.db", "-o", out / "verify.json")

    gold = profile.get("gold")
    if gold and not skip_eval:
        gold_path = Path(gold)
        if gold_path.is_file() and len(json.loads(gold_path.read_text(encoding="utf-8"))) >= 30:
            run(LAB8, "eval", "-d", out / "curriculum.db", "-q", gold_path,
                "-o", out / "eval_result.json")
    print(f"\nเสร็จแล้ว [{name}]: {out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--program", default="dsba",
        choices=[*PROFILES, "dsba", "dsba-all", "ai", "it", "it-both", "it-all", "bit", "all"],
        help="หลักสูตร/แผนที่จะประมวลผล (it และ it-both = รัน IT no-coop แล้ว IT coop)",
    )
    parser.add_argument("--skip-lab7", action="store_true")
    parser.add_argument("--skip-eval", action="store_true")
    args = parser.parse_args()

    os.environ.update({
        "PYTHONUTF8": "1",
        "LAB7_CHUNK": "1",
        "LAB7B_NUM_CTX": "16384",
        "LAB7B_NUM_PREDICT": "8192",
        "LAB7B_OCR_NUM_CTX": "8192",
        "LAB7B_OCR_NUM_PREDICT": "2048",
    })

    selected = {
        "dsba": ["dsba-coop"],
        "dsba-all": ["dsba-coop", "dsba-no-coop", "dsba-2560-coop", "dsba-2560-no-coop"],
        "it": ["it-no-coop", "it-coop"],
        "it-both": ["it-no-coop", "it-coop"],
        "it-all": ["it-no-coop", "it-coop", "it-2560-no-coop", "it-2560-coop"],
        "bit": ["bit-2565-no-coop", "bit-2565-coop", "bit-2560-no-coop", "bit-2560-coop"],
        "all": list(PROFILES),
    }.get(args.program, [args.program])
    for name in selected:
        run_profile(name, skip_lab7=args.skip_lab7, skip_eval=args.skip_eval)


if __name__ == "__main__":
    main()
