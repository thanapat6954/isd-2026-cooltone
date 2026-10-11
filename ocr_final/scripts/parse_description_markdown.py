"""Parse raw description pages without inventing study-plan placements or rules."""
import argparse
import hashlib
import json
from pathlib import Path
import re


HEADER = re.compile(r'^\s*(\d{8})\s+(.+?)\s+(\d+\s*\(\s*\d+\s*-\s*\d+\s*-\s*\d+\s*\).*)$', re.M)


def parse_descriptions(text, source_file, pdf_page, printed_page=None):
    matches = list(HEADER.finditer(text))
    rows = []
    seen = set()
    for index, match in enumerate(matches):
        code, name, credits_raw = match.groups()
        if code in seen:
            raise ValueError('Duplicate description code; review overlapping extraction before parsing')
        seen.add(code)
        section = text[match.end():matches[index+1].start() if index+1 < len(matches) else len(text)]
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        name_en = lines[0] if lines and re.match(r'^[A-Z][A-Z /&()0-9-]+$', lines[0]) else None
        prereq = re.search(r'^\s*PREREQUISITE\s*:\s*([^\n]*)', section, re.M | re.I)
        raw = prereq.group(1).strip() if prereq else None
        status = 'explicit_none' if raw and raw.upper() == 'NONE' else 'required' if raw else 'unknown'
        patterns = re.findall(r'(\d+)\s*\(\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*\)', credits_raw)
        hours = tuple(map(int, patterns[0])) if len(patterns) == 1 else None
        # Descriptive conditions remain literal, never converted to AND/OR or permission.
        description = None
        if prereq:
            thai_lines = []
            for line in section[prereq.end():].splitlines():
                stripped = line.strip()
                if re.match(r'^[A-Za-z]', stripped):
                    break
                if stripped and re.search(r'[ก-๙]', stripped):
                    thai_lines.append(stripped)
            description = '\n'.join(thai_lines) or None
        rows.append({'code': code, 'name_th': name.strip(), 'name_en': name_en,
            'credits_raw': credits_raw.strip(), 'credits': hours[0] if hours else None,
            'lecture_h': hours[1] if hours else None, 'lab_h': hours[2] if hours else None,
            'self_h': hours[3] if hours else None, 'description_th': description,
            'prerequisite_raw': raw, 'prerequisite_status': status,
            'prerequisite_codes': re.findall(r'(?<!\d)\d{8}(?!\d)', raw or ''),
            'prerequisite_logic': None, 'source_file': source_file,
            'page_number': pdf_page, 'printed_page_number': printed_page,
            'section': 'course description', 'source_verified': False})
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source-file', required=True)
    p.add_argument('--pdf-page', type=int, required=True)
    p.add_argument('--printed-page', type=int)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Preserve parsed attempts; use a new output file')
    text = a.input.read_text(encoding='utf-8')
    result = {'scope': 'raw description parsing; NOT study-plan rows, source approval or evaluation labels',
              'input_sha256': hashlib.sha256(a.input.read_bytes()).hexdigest(),
              'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'courses': parse_descriptions(text, a.source_file, a.pdf_page, a.printed_page)}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'parsed_course_count': len(result['courses']), 'source_verified': False}))


if __name__ == '__main__':
    main()
