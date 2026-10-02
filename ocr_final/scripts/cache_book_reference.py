"""Cache page-delimited official PDF text; not an independent OCR accuracy GT."""
import argparse
import hashlib
import json
from pathlib import Path

import pymupdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.app_root.resolve()
    target = root / 'work/ref_text'
    target.mkdir(parents=True, exist_ok=True)
    entries = []
    for source in sorted((root / 'data/input').glob('*.pdf')):
        with source.open('rb') as source_handle:
            sha = hashlib.file_digest(source_handle, 'sha256').hexdigest()
        output = target / (source.stem + '-' + sha[:12] + '.jsonl')
        if not output.exists():
            staging = output.with_suffix('.partial')
            completed = 0
            if staging.exists():
                completed = len(staging.read_text(encoding='utf-8').splitlines())
            with pymupdf.open(source) as document, staging.open('a', encoding='utf-8') as handle:
                for index in range(completed, len(document)):
                    text = document[index].get_text('text')
                    handle.write(json.dumps({'pdf_page': index + 1, 'text': text}, ensure_ascii=False) + '\n')
                    handle.flush()
            staging.replace(output)
        entries.append({'source_file': source.name, 'sha256': sha, 'pages_file': output.name,
                        'method': 'embedded PDF text, locator only; font-corrupted Thai needs visual verification'})
        print(f'{source.name}: cached page text')
    manifest = target / 'manifest.json'
    staging = manifest.with_suffix('.partial')
    staging.write_text(json.dumps({'sources': entries}, ensure_ascii=False, indent=2), encoding='utf-8')
    staging.replace(manifest)


if __name__ == '__main__':
    main()
