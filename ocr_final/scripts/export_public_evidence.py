"""Export README-linked evidence with local paths redacted; preserve originals."""
import argparse
import json
from pathlib import Path
import re
import shutil


def redact(value):
    roots = {
        'C:/Users/thana/OneDrive/เอกสาร/isd-2026-cooltone': '<REPOSITORY>',
        'C:/Users/thana/OneDrive/เอกสาร/ocr_final': '<LIVE_APP>',
        'C:/Users/thana/AppData/Local/Temp': '<TEMP>',
        'C:/Users/thana/.codex': '<CODEX_HOME>',
        'C:/Users/thana': '<LOCAL_USER>',
    }
    for root, replacement in roots.items():
        for variant in (root, root.replace('/', '\\'), root.replace('/', '\\\\')):
            value = value.replace(variant, replacement)
    return value


def sanitize_json(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [sanitize_json(x) for x in value]
    if isinstance(value, dict):
        return {redact(k): sanitize_json(v) for k, v in value.items()}
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', type=Path, required=True)
    args = parser.parse_args()
    root = args.repository.resolve()
    source = root/'docs/results'
    destination = root/'docs/public_results'
    if destination.exists():
        raise ValueError('Destination exists; preserve it and use a reviewed update instead')
    pending = [root/'README.md']
    visited, copies = set(), set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        if path != root/'README.md':
            if not path.is_relative_to(source) or not path.is_file():
                continue
            copies.add(path)
        if path.suffix.lower() == '.md':
            text = path.read_text(encoding='utf-8')
            links = re.findall(r'\]\(([^)]+)\)', text)
            links += re.findall(r'(?:src|href)=[\"\']([^\"\']+)[\"\']', text)
            for link in links:
                if not link.startswith(('http:', 'https:', '#')):
                    candidate = (path.parent/link.split('#')[0]).resolve()
                    if candidate.is_relative_to(source):
                        pending.append(candidate)
    for path in sorted(copies):
        if path.suffix.lower() in ('.db', '.pdf', '.bak'):
            raise ValueError('Source/database artifact linked: '+str(path))
        target = destination/path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == '.json':
            value = sanitize_json(json.loads(path.read_text(encoding='utf-8-sig')))
            target.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        elif path.suffix.lower() in ('.md', '.txt', '.log'):
            target.write_text(redact(path.read_text(encoding='utf-8-sig')), encoding='utf-8')
        else:
            shutil.copy2(path, target)
    print(json.dumps({'files':len(copies), 'bytes':sum(p.stat().st_size for p in destination.rglob('*') if p.is_file()),
                      'scope':'README-linked public derivatives; original raw evidence unchanged'}, indent=2))


if __name__ == '__main__':
    main()
