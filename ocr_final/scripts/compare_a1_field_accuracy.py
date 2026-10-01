"""Compute A1 field metrics without treating OCR candidates as ground truth.

Only rows whose review status explicitly records visual approval are scored.
When no rows are approved, metrics are emitted as ``null``/``n/a`` evidence
rather than silently scoring the candidate transcription against itself.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT / "docs" / "results" / "a1_ground_truth_review.json"
DEFAULT_OUTPUT = PROJECT / "docs" / "results" / "a1_field_metrics.json"

APPROVED_STATUSES = {"visually_verified", "corrected_after_visual_review"}
DIRECT_FIELDS = [
    "code",
    "name_th",
    "name_en",
    "credits",
    "prerequisite",
    "category",
    "type",
    "year",
    "semester",
    "plan",
    "page_number",
]
HOUR_FIELDS = ["lecture_hours", "lab_hours", "self_study_hours"]
FIELDS = DIRECT_FIELDS + HOUR_FIELDS
CREDIT_RE = re.compile(
    r"^\s*\d+(?:\.\d+)?\s*\(\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*\)\s*$"
)
SUSPICIOUS_THAI_RE = re.compile(r"[\ue000-\uf8ff\ufffd]")
THAI_COMBINING_RE = re.compile(r"[\u0e31\u0e34-\u0e3a\u0e47-\u0e4e]")


def normalized(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def credit_hours(value: Any) -> dict[str, int | None]:
    text = normalized(value)
    match = CREDIT_RE.fullmatch(text) if isinstance(text, str) else None
    if not match:
        return {field: None for field in HOUR_FIELDS}
    return dict(zip(HOUR_FIELDS, (int(part) for part in match.groups()), strict=True))


def sample_value(sample: dict, side: str, field: str) -> Any:
    if field == "plan":
        container = sample.get(side) or {}
        return container.get("plan", sample.get("plan") if side == "candidate" else None)
    if field in HOUR_FIELDS:
        return credit_hours((sample.get(side) or {}).get("credits"))[field]
    return (sample.get(side) or {}).get(field)


def is_garbled_thai(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if SUSPICIOUS_THAI_RE.search(value):
        return True
    # A combining mark cannot start a Thai word. This catches a common broken
    # vowel/tone-mark ordering symptom without rejecting valid combining marks.
    return any(
        THAI_COMBINING_RE.fullmatch(char) and (index == 0 or value[index - 1].isspace())
        for index, char in enumerate(value)
    )


def empty_field_stats() -> dict[str, dict[str, int | float | None]]:
    return {
        field: {"correct": 0, "n": 0, "accuracy": None}
        for field in FIELDS
    }


def finalize_field_stats(stats: dict[str, dict[str, int | float | None]]) -> None:
    for values in stats.values():
        n = int(values["n"] or 0)
        values["accuracy"] = round(int(values["correct"] or 0) / n, 6) if n else None


def compare(samples: list[dict]) -> dict:
    approved = [sample for sample in samples if sample.get("review_status") in APPROVED_STATUSES]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for sample in approved:
        grouped[f"{sample.get('program')}-{sample.get('curriculum_version')}"] .append(sample)

    overall = empty_field_stats()
    per_profile: dict[str, dict] = {}
    wrong_rows: list[dict] = []

    for profile in sorted(grouped):
        profile_stats = empty_field_stats()
        for sample in grouped[profile]:
            mismatches: list[str] = []
            for field in FIELDS:
                expected = sample_value(sample, "ground_truth", field)
                if expected is None:
                    continue
                predicted = sample_value(sample, "candidate", field)
                for bucket in (profile_stats[field], overall[field]):
                    bucket["n"] = int(bucket["n"] or 0) + 1
                if normalized(predicted) == normalized(expected):
                    profile_stats[field]["correct"] = int(profile_stats[field]["correct"] or 0) + 1
                    overall[field]["correct"] = int(overall[field]["correct"] or 0) + 1
                else:
                    mismatches.append(field)
            if mismatches:
                wrong_rows.append({"sample_id": sample.get("sample_id"), "fields": mismatches})
        finalize_field_stats(profile_stats)
        per_profile[profile] = {"approved_rows": len(grouped[profile]), "fields": profile_stats}

    finalize_field_stats(overall)

    identities = [
        (
            sample.get("program"),
            sample.get("curriculum_version"),
            sample.get("plan"),
            normalized((sample.get("candidate") or {}).get("code")),
            (sample.get("candidate") or {}).get("year"),
            (sample.get("candidate") or {}).get("semester"),
        )
        for sample in samples
    ]
    duplicate_groups = [
        {"identity": list(identity), "count": count}
        for identity, count in sorted(Counter(identities).items(), key=lambda item: repr(item[0]))
        if count > 1 and identity[3]
    ]
    candidate_missing_values = [
        sample.get("sample_id")
        for sample in approved
        if any(
            sample_value(sample, "candidate", field) in (None, "")
            and sample_value(sample, "ground_truth", field) not in (None, "")
            for field in FIELDS
        )
    ]
    thai_values = [sample_value(sample, "candidate", "name_th") for sample in approved]
    garbled = sum(is_garbled_thai(value) for value in thai_values)

    return {
        "method": (
            "normalized exact match over visually approved rows only; hour fields are parsed "
            "from the credit pattern; null ground-truth fields are excluded"
        ),
        "approved_statuses": sorted(APPROVED_STATUSES),
        "candidate_rows": len(samples),
        "approved_rows": len(approved),
        "unapproved_rows": len(samples) - len(approved),
        "overall": {"fields": overall},
        "per_program_version": per_profile,
        "row_quality": {
            "wrong_rows": wrong_rows,
            "wrong_row_count": len(wrong_rows),
            "candidate_missing_value_rows": candidate_missing_values,
            "candidate_missing_value_row_count": len(candidate_missing_values),
            "duplicate_groups": duplicate_groups,
            "duplicate_group_count": len(duplicate_groups),
            "garbled_thai_rows": garbled,
            "garbled_thai_n": len(thai_values),
            "garbled_thai_rate": round(garbled / len(thai_values), 6) if thai_values else None,
        },
        "limitations": [
            "This stratified candidate sample cannot measure full-database spurious or missing-row recall.",
            "A metric remains null until at least one visually approved ground-truth value exists.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = compare(payload.get("samples") or [])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "approved_rows": result["approved_rows"],
        "unapproved_rows": result["unapproved_rows"],
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
