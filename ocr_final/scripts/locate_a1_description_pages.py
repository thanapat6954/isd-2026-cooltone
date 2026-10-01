"""Locate course-description pages for A1 plan-row samples.

This uses only exact eight-digit code matches and the literal English heading
``PREREQUISITE`` in PDF text.  It does not infer prerequisite values and does
not mark candidates as verified.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import pymupdf


PROJECT = Path(__file__).resolve().parents[2]
OCR_ROOT = PROJECT / "ocr_final"
REVIEW_SET = PROJECT / "docs" / "results" / "a1_ground_truth_review.json"
OUTPUT = PROJECT / "docs" / "results" / "a1_description_locator.json"


def main() -> None:
    payload = json.loads(REVIEW_SET.read_text(encoding="utf-8"))
    by_pdf: dict[str, list[dict]] = defaultdict(list)
    for sample in payload["samples"]:
        by_pdf[sample["source_pdf"]].append(sample)

    located: list[dict] = []
    documents: dict[str, pymupdf.Document] = {}
    try:
        for source_pdf, samples in sorted(by_pdf.items()):
            document = documents.setdefault(
                source_pdf, pymupdf.open(OCR_ROOT / "data" / "input" / source_pdf)
            )
            page_text = [page.get_text("text") for page in document]
            for sample in samples:
                raw_code = str(sample["candidate"].get("code") or "")
                codes = re.findall(r"(?<!\d)\d{8}(?!\d)", raw_code)
                matches: list[int] = []
                for code in codes:
                    matches.extend(
                        index + 1
                        for index, text in enumerate(page_text)
                        if code in text and "PREREQUISITE" in text.upper()
                    )
                matches = sorted(set(matches))
                plan_page = sample["candidate"].get("page_number")
                description_page = next(
                    (page for page in matches if page != plan_page and page > 40),
                    matches[0] if matches else None,
                )
                located.append({
                    "sample_id": sample["sample_id"],
                    "source_pdf": source_pdf,
                    "code": raw_code,
                    "plan_page": plan_page,
                    "description_page": description_page,
                    "all_description_page_matches": matches,
                    "status": "located" if description_page else "not_located",
                })
    finally:
        for document in documents.values():
            document.close()

    output = {
        "method": "exact 8-digit code + PREREQUISITE heading; no value inference",
        "located": sum(item["status"] == "located" for item in located),
        "not_located": sum(item["status"] != "located" for item in located),
        "items": located,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: output[key] for key in ("located", "not_located")}, indent=2))


if __name__ == "__main__":
    main()
