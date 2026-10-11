"""Render the unique A1 review pages with a resumable checkpoint."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf


PROJECT = Path(__file__).resolve().parents[2]
OCR_ROOT = PROJECT / "ocr_final"
REVIEW_SET = PROJECT / "docs" / "results" / "a1_ground_truth_review.json"
OUTPUT_DIR = OCR_ROOT / "tmp" / "pdfs" / "a1_pages"
CHECKPOINT = PROJECT / "docs" / "results" / "a1_render_checkpoint.json"
DPI = 180


def render_page(source: Path, page_number: int, output_dir: Path, dpi: int = DPI) -> dict:
    """Reuse only source/configuration/renderer-locked images; retain legacy images."""
    identity = {'source_sha256': _sha256(source), 'pdf_page': page_number,
                'dpi': dpi, 'alpha': False, 'renderer': pymupdf.VersionBind}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = output_dir / key
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f'{source.stem}-page-{page_number:03d}.png'
    manifest = folder / 'render.json'
    if manifest.exists():
        saved = json.loads(manifest.read_text(encoding='utf-8'))
        if saved['identity'] != identity or not output.exists() or saved['sha256'] != _sha256(output):
            raise ValueError('Cached source render failed its dependency/integrity guard')
        return {**saved, 'image': str(output), 'reused': True}
    if output.exists():
        raise ValueError('Interrupted render without provenance; use a fresh output directory')
    with pymupdf.open(source) as document:
        document[page_number - 1].get_pixmap(dpi=dpi, alpha=False).save(output)
    saved = {'identity': identity, 'image': str(output), 'sha256': _sha256(output)}
    manifest.write_text(json.dumps(saved, indent=2), encoding='utf-8')
    return {**saved, 'reused': False}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    payload = json.loads(REVIEW_SET.read_text(encoding="utf-8"))
    wanted = sorted({
        (sample["source_pdf"], int(sample["candidate"]["page_number"]))
        for sample in payload["samples"]
    })
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    completed: list[dict] = []
    for source_pdf, page_number in wanted:
            source = OCR_ROOT / "data" / "input" / source_pdf
            rendered = render_page(source, page_number, OUTPUT_DIR)
            output = Path(rendered['image'])
            completed.append({
                "source_pdf": source_pdf,
                "page_number": page_number,
                "image": str(output.relative_to(PROJECT)).replace("\\", "/"),
                "sha256": _sha256(output),
                "identity": rendered['identity'],
                "reused": rendered['reused'],
            })
            CHECKPOINT.write_text(json.dumps({
                "dpi": DPI,
                "completed": completed,
                "remaining": len(wanted) - len(completed),
            }, indent=2), encoding="utf-8")
    print(json.dumps({"rendered_or_reused": len(completed), "checkpoint": str(CHECKPOINT)}, indent=2))


if __name__ == "__main__":
    main()
