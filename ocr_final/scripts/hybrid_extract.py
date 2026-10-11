"""Prefer source PDF text/tables, preserving failures before image OCR fallback."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.source_native import extract, sha, save


def preserve_native_attempt(output):
    parent = output.resolve().parent
    target = parent / (output.name + '.native-rejected')
    if output.resolve().parent != parent or target.resolve().parent != parent:
        raise ValueError('Native attempt archive escapes the staging output')
    if target.exists():
        raise FileExistsError('Prior native attempt preserved; use a new output')
    output.rename(target)
    return target


def run(pdf, numbers, output, manifest, source_root, font_review=None, max_pages=None):
    state = extract(pdf, numbers, output, max_pages, font_review)
    policy = {'policy': 'PDF text/table extraction first; image-only OCR after native rejection',
              'native_attempt': {'status': 'accepted', 'source_sha256': sha(pdf)},
              'selected_method': 'pdf-text-tables'}
    if state['failed']:
        rejected = preserve_native_attempt(output)
        command = [sys.executable, '-X', 'utf8', str(ROOT/'scripts/extract_manifest_pages.py'),
                   '--manifest', str(manifest), '--source-root', str(source_root),
                   '--output', str(output), '--layout', 'raster-rows']
        for number in numbers:
            command += ['--page', str(number)]
        if max_pages:
            command += ['--max-pages', str(max_pages)]
        result = subprocess.run(command, check=False)
        if not (output/'manifest-extraction.json').exists():
            raise RuntimeError('Image OCR failed before checkpoint; native evidence retained at '+str(rejected))
        state = json.loads((output/'manifest-extraction.json').read_text(encoding='utf-8'))
        policy.update(selected_method='vision-OCR', native_attempt={
            'status': 'rejected', 'directory': rejected.name,
            'manifest_sha256': sha(rejected/'manifest-extraction.json'),
            'failures': json.loads((rejected/'manifest-extraction.json').read_text(encoding='utf-8'))['failed'],
            'ocr_exit_code': result.returncode})
        state['method'] = 'vision-OCR'
        state['ocr_performed'] = True
    state['hybrid'] = policy
    save(output/'manifest-extraction.json', state)
    return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdf', type=Path, required=True)
    p.add_argument('--page', type=int, action='append', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--font-review', type=Path)
    p.add_argument('--max-pages', type=int)
    a = p.parse_args()
    selection = json.loads(a.manifest.read_text(encoding='utf-8'))
    if sha(a.pdf) != selection['source_sha256']:
        raise ValueError('Source PDF differs from recorded page selection; review the new source first')
    result = run(a.pdf, a.page, a.output.resolve(), a.manifest, a.source_root, a.font_review, a.max_pages)
    return int(bool(result['failed'] or result['pending_requested']))


if __name__ == '__main__':
    raise SystemExit(main())
