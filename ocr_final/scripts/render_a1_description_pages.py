"""Render located A1 course-description pages with a resumable checkpoint."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf


PROJECT = Path(__file__).resolve().parents[2]
OCR_ROOT = PROJECT / "ocr_final"
LOCATOR = PROJECT / "docs" / "results" / "a1_description_locator.json"
OUTPUT_DIR = OCR_ROOT / "tmp" / "pdfs" / "a1_descriptions"
CHECKPOINT = PROJECT / "docs" / "results" / "a1_description_render_checkpoint.json"
DPI = 180


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    payload = json.loads(LOCATOR.read_text(encoding="utf-8"))
    wanted = sorted({
        (item["source_pdf"], int(item["description_page"]))
        for item in payload["items"] if item.get("description_page")
    })
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    completed: list[dict] = []
    documents: dict[str, pymupdf.Document] = {}
    try:
        for source_pdf, page_number in wanted:
            source = OCR_ROOT / "data" / "input" / source_pdf
            output = OUTPUT_DIR / f"{source.stem}-description-{page_number:03d}.png"
            if not output.exists():
                document = documents.setdefault(source_pdf, pymupdf.open(source))
                document[page_number - 1].get_pixmap(dpi=DPI, alpha=False).save(output)
            completed.append({
                "source_pdf": source_pdf,
                "page_number": page_number,
                "image": str(output.relative_to(PROJECT)).replace("\\", "/"),
                "sha256": sha256(output),
            })
            CHECKPOINT.write_text(json.dumps({
                "dpi": DPI,
                "completed": completed,
                "remaining": len(wanted) - len(completed),
            }, indent=2), encoding="utf-8")
    finally:
        for document in documents.values():
            document.close()
    print(json.dumps({"rendered_or_reused": len(completed), "checkpoint": str(CHECKPOINT)}, indent=2))


if __name__ == "__main__":
    main()
