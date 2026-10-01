"""Build a stratified, explicitly unverified A1 OCR review set.

The input JSON files are frozen outputs from the system under audit.  They are
candidate transcriptions, never ground truth.  A reviewer must compare every
row with the rendered PDF page and fill ``ground_truth`` plus ``review_status``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CANDIDATES = PROJECT / "docs" / "results" / "a1_candidates"
OUTPUT = PROJECT / "docs" / "results" / "a1_ground_truth_review.json"

PROFILES = [
    ("DSBA", 2565, "coop", "dsba-2565-coop.json", "DSBA.pdf"),
    ("DSBA", 2565, "no-coop", "dsba-2565-no-coop.json", "DSBA.pdf"),
    ("DSBA", 2560, "coop", "dsba-2560-coop.json", "DSBA-60.pdf"),
    ("DSBA", 2560, "no-coop", "dsba-2560-no-coop.json", "DSBA-60.pdf"),
    ("IT", 2565, "coop", "it-2565-coop.json", "IT.pdf"),
    ("IT", 2565, "no-coop", "it-2565-no-coop.json", "IT.pdf"),
    ("IT", 2560, "coop", "it-2560-coop.json", "IT-60.pdf"),
    ("IT", 2560, "no-coop", "it-2560-no-coop.json", "IT-60.pdf"),
    ("BIT", 2565, "coop", "bit-2565-coop.json", "BIT-65.pdf"),
    ("BIT", 2565, "no-coop", "bit-2565-no-coop.json", "BIT-65.pdf"),
    ("BIT", 2560, "coop", "bit-2560-coop.json", "BIT-60.pdf"),
    ("BIT", 2560, "no-coop", "bit-2560-no-coop.json", "BIT-60.pdf"),
]

FIELDS = [
    "code", "name_th", "name_en", "credits", "prerequisite", "category",
    "type", "year", "semester", "page_number",
]


def _select_15(rows: list[dict]) -> list[dict]:
    """Select five rows from early/middle/late pages, then fill to 15."""
    by_page: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        page = row.get("page_number")
        if isinstance(page, int) and page > 0:
            by_page[page].append(row)
    pages = sorted(by_page)
    if not pages:
        raise ValueError("candidate profile has no valid page numbers")
    anchors = [pages[0], pages[len(pages) // 2], pages[-1]]
    selected: list[dict] = []
    seen: set[int] = set()
    for page in anchors:
        for row in by_page[page][:5]:
            marker = id(row)
            if marker not in seen:
                selected.append(row)
                seen.add(marker)
    for row in sorted(rows, key=lambda item: (item.get("page_number") or 0, item.get("code") or "")):
        if len(selected) >= 15:
            break
        marker = id(row)
        if marker not in seen and isinstance(row.get("page_number"), int):
            selected.append(row)
            seen.add(marker)
    if len(selected) < 15:
        raise ValueError(f"profile has only {len(selected)} page-linked candidate rows")
    return selected[:15]


def main() -> None:
    samples: list[dict] = []
    for program, version, plan, filename, source_pdf in PROFILES:
        payload = json.loads((CANDIDATES / filename).read_text(encoding="utf-8"))
        rows = payload.get("courses") or []
        for ordinal, row in enumerate(_select_15(rows), start=1):
            candidate = {field: row.get(field) for field in FIELDS}
            candidate["source_file"] = row.get("source_file") or source_pdf
            samples.append({
                "sample_id": f"{program}-{version}-{plan}-{ordinal:02d}",
                "program": program,
                "curriculum_version": version,
                "plan": plan,
                "source_pdf": source_pdf,
                "candidate": candidate,
                "ground_truth": {field: None for field in FIELDS},
                "review_status": "candidate_only",
                "review_evidence": None,
                "review_notes": None,
            })

    output = {
        "method": (
            "180 stratified candidate rows: 15 per plan, 30 per program-version. "
            "Candidates are frozen system outputs and do not count as ground truth until "
            "review_status is visually_verified or corrected_after_visual_review."
        ),
        "required_fields": FIELDS,
        "samples": samples,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    counts: dict[str, int] = defaultdict(int)
    for sample in samples:
        counts[f"{sample['program']}-{sample['curriculum_version']}"] += 1
    print(json.dumps({"output": str(OUTPUT), "n": len(samples), "counts": counts}, indent=2))


if __name__ == "__main__":
    main()
