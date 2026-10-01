"""Apply an explicit human-review batch to the frozen A1 candidate set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_REVIEW = PROJECT / "docs" / "results" / "a1_ground_truth_review.json"


def apply_batch(review: dict, batch: dict) -> dict:
    samples = {sample["sample_id"]: sample for sample in review.get("samples") or []}
    batch_ids = [item["sample_id"] for item in batch.get("items") or []]
    if len(batch_ids) != len(set(batch_ids)):
        raise ValueError("review batch contains duplicate sample_id values")
    unknown = sorted(set(batch_ids) - set(samples))
    if unknown:
        raise ValueError(f"review batch contains unknown sample IDs: {unknown}")

    copy_fields = batch.get("copy_candidate_fields") or []
    verified_fields = batch.get("verified_fields") or []
    for item in batch.get("items") or []:
        sample = samples[item["sample_id"]]
        candidate = sample.get("candidate") or {}
        ground_truth = sample.get("ground_truth") or {}
        for field in copy_fields:
            ground_truth[field] = candidate.get(field)
        ground_truth["plan"] = sample.get("plan")
        ground_truth["prerequisite"] = item.get("prerequisite")
        for field, value in (item.get("overrides") or {}).items():
            if field not in verified_fields:
                raise ValueError(f"override field is not verified: {field}")
            ground_truth[field] = value
        sample["ground_truth"] = ground_truth
        sample["review_status"] = "corrected_after_visual_review"
        sample["review_evidence"] = item.get("evidence")
        sample["review_notes"] = (
            f"Batch {batch['batch_id']}; verified fields: {', '.join(verified_fields)}. "
            "Category and type remain unverified and are excluded from metrics."
        )
    return review


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    args = parser.parse_args()
    review = json.loads(args.review.read_text(encoding="utf-8"))
    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    result = apply_batch(review, batch)
    args.review.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "batch_id": batch["batch_id"],
        "applied": len(batch.get("items") or []),
        "review": str(args.review),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
