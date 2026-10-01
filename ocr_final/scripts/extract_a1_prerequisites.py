"""Extract prerequisite evidence from exact PDF course-description sections.

The output preserves the normalized source excerpt and extraction status.
It is audit evidence, not an automatic approval of the OCR candidate row.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf


PROJECT = Path(__file__).resolve().parents[2]
OCR_ROOT = PROJECT / "ocr_final"
LOCATOR = PROJECT / "docs" / "results" / "a1_description_locator.json"
OUTPUT = PROJECT / "docs" / "results" / "a1_prerequisite_ground_truth.json"


HEADER_RE = re.compile(r"(?m)^\s*(\d{8})\b")
CREDIT_RE = re.compile(r"\d+\s*\(\s*\d+\s*-\s*\d+\s*-\s*\d+\s*\)")


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).replace("\u00a0", " ")


def course_headers(page_text: str) -> list[tuple[int, str]]:
    """Return (offset, code) pairs for verified course-description headers."""
    headers: list[tuple[int, str]] = []
    for match in HEADER_RE.finditer(page_text):
        nearby = page_text[match.start():match.start() + 650]
        credit = CREDIT_RE.search(nearby)
        prerequisite = re.search(r"PREREQUISITE\s*: ?", nearby, re.I)
        next_code = HEADER_RE.search(nearby, len(match.group(0)))
        if (
            credit
            and prerequisite
            and credit.start() < prerequisite.start()
            and (next_code is None or next_code.start() > credit.start())
        ):
            headers.append((match.start(), match.group(1)))
    return headers


def course_section(page_text: str, code: str) -> str | None:
    headers = course_headers(page_text)
    header_index = next(
        (index for index, (_, header_code) in enumerate(headers) if header_code == code),
        None,
    )
    if header_index is None:
        return None
    start = headers[header_index][0]
    end = headers[header_index + 1][0] if header_index + 1 < len(headers) else len(page_text)
    return normalize(page_text[start:end]).strip()


def extract_prerequisite(section: str | None, own_code: str) -> tuple[str, list[str], str | None]:
    if not section:
        return "section_not_found", [], None
    match = re.search(r"PREREQUISITE\s*:?[ \t]*(.*)", section, re.I)
    if not match:
        return "heading_not_found", [], section[:500]
    after = section[match.start():]
    evidence_lines = [line.strip() for line in after.splitlines()[:10] if line.strip()]
    evidence = " | ".join(evidence_lines)[:500]
    # Only inspect the prerequisite heading and its next few short lines; a
    # course description later on the page can contain unrelated course codes.
    window = " ".join(evidence_lines)
    none_match = re.search(r"\bNONE\b", window, re.I)
    code_matches = [
        match
        for match in re.finditer(r"(?<!\d)\d{8}(?!\d)", window)
        if match.group(0) != own_code
    ]
    # NONE is authoritative when it appears before any foreign course code;
    # later codes may belong to prose or a malformed following section.
    if none_match and (not code_matches or none_match.start() < code_matches[0].start()):
        return "explicit_none", [], evidence
    if code_matches:
        return "parsed_codes", sorted({match.group(0) for match in code_matches}), evidence
    return "unparsed", [], evidence


def main() -> None:
    locator = json.loads(LOCATOR.read_text(encoding="utf-8"))
    documents: dict[str, pymupdf.Document] = {}
    page_cache: dict[tuple[str, int], str] = {}
    results: list[dict] = []
    try:
        for item in locator["items"]:
            page_number = item.get("description_page")
            raw_code = str(item.get("code") or "")
            codes = re.findall(r"(?<!\d)\d{8}(?!\d)", raw_code)
            if not page_number or len(codes) != 1:
                results.append({
                    "sample_id": item["sample_id"],
                    "code": raw_code,
                    "source_pdf": item["source_pdf"],
                    "description_page": page_number,
                    "status": "not_applicable_or_unlocated",
                    "prerequisite_codes": [],
                    "evidence": None,
                })
                continue
            key = (item["source_pdf"], int(page_number))
            if key not in page_cache:
                document = documents.setdefault(
                    item["source_pdf"],
                    pymupdf.open(OCR_ROOT / "data" / "input" / item["source_pdf"]),
                )
                page_cache[key] = document[int(page_number) - 1].get_text("text")
            section = course_section(page_cache[key], codes[0])
            status, prerequisite_codes, evidence = extract_prerequisite(section, codes[0])
            results.append({
                "sample_id": item["sample_id"],
                "code": codes[0],
                "source_pdf": item["source_pdf"],
                "description_page": page_number,
                "status": status,
                "prerequisite_codes": prerequisite_codes,
                "evidence": evidence,
            })
    finally:
        for document in documents.values():
            document.close()

    counts = Counter(item["status"] for item in results)
    payload = {
        "method": "exact course section and English PREREQUISITE heading from PDF text",
        "requires_visual_confirmation": True,
        "status_counts": dict(sorted(counts.items())),
        "items": results,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["status_counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
