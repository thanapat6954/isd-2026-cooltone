"""Parse physical OCR table bands without asking a second model to rewrite facts."""
from html import unescape
from html.parser import HTMLParser
import re

from scripts.source_native import CODE, CREDIT, TERM, bilingual_groups, clean, shared_placeholder_names, explicit_course_choice


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in {'td', 'th'}:
            if self.row is None:
                self.row = []
            self.cell = []
        elif tag in {'br', 'p', 'div'} and self.cell is not None:
            self.cell.append('\n')

    def handle_endtag(self, tag):
        if tag in {'td', 'th'} and self.cell is not None:
            self.row.append(''.join(self.cell).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def table_rows(text):
    if re.search(r'<table\b', text, re.I):
        parser = Tables()
        parser.feed(text)
        return parser.rows
    result = []
    for line in text.splitlines():
        if '|' not in line:
            continue
        cells = [unescape(re.sub(r'<br\s*/?>', '\n', c, flags=re.I)).strip()
                 for c in line.strip().strip('|').split('|')]
        if cells and all(re.fullmatch(r'[:\s-]*', c) for c in cells):
            continue
        result.append(cells)
    return result


def name_lines(text):
    # OCR can put a bilingual name on one HTML line. Restore only script
    # boundaries; never correct spelling or create missing name alternatives.
    text = re.sub(r'\\(\*)', r'\1', text)
    text = re.sub(r'(?<=[A-Za-z0-9)])\s+(?=[\u0e00-\u0e7f])', '\n', text)
    text = re.sub(r'(?<=[\u0e00-\u0e7f0-9*])\s+(?=[A-Z][A-Z])', '\n', text)
    # A faculty label can share an OCR line with the actual Thai course name.
    # Split the literal label rather than discarding the complete first line.
    text = re.sub(r'^(กลุ่มวิชา(?:ที่กำหนดโดยคณะ|ตามเกณฑ์ของคณะ)\*?)\s+(?=[\u0e00-\u0e7f])',
                  r'\1\n', text)
    return text


def parse_page(regions, source_file, pdf_page, printed_page):
    """Consume every physical data row; reject unresolved cells and totals."""
    courses, totals, active, term_rows = [], [], None, []
    for region in regions:
        text = region['text']
        headings = list(TERM.finditer(clean(re.sub(r'<[^>]+>', ' ', text))))
        if headings:
            if term_rows:
                raise ValueError('New OCR term heading before previous printed total')
            active = tuple(map(int, headings[-1].groups()))
        rows = table_rows(text)
        # OCR may serialize one physical merged total band as two HTML rows.
        # Accept only the literal total label plus exactly one numeric cell.
        flattened = [clean(c) for row in rows for c in row if clean(c)]
        if 'รวม' in flattened:
            if len(flattened) != 2 or flattened.count('รวม') != 1:
                raise ValueError('OCR total band contains ambiguous extra cells')
            numbers = [c for c in flattened if c != 'รวม']
            if not numbers[0].isdigit():
                raise ValueError('OCR total band lacks a literal numeric total')
            rows = [['รวม', numbers[0]]]
        # A table-band containing a code is required to have explicit columns.
        if CODE.search(text) and not rows:
            raise ValueError('OCR course band lost its columns; inspect its image')
        for cells in rows:
            if not CODE.search(' '.join(cells)) and any(clean(c) in {'รหัสวิชา', 'ชื่อวิชา'} for c in cells):
                continue
            total = next((i for i, c in enumerate(cells) if clean(c) == 'รวม'), None)
            if total is not None:
                numbers = [clean(c) for c in cells[total + 1:] if clean(c)]
                if not active or not term_rows or len(numbers) != 1 or not numbers[0].isdigit():
                    raise ValueError('OCR term total lacks an unambiguous source table')
                credit_sum = sum(int(CREDIT.search(c['credits'])[0].split('(')[0]) for c in term_rows)
                if credit_sum != int(numbers[0]):
                    raise ValueError('OCR row credits do not reconcile with its printed term total')
                totals.append({'year': active[0], 'semester': active[1], 'credits': int(numbers[0]),
                    'source_file': source_file, 'page_number': pdf_page, 'printed_page_number': printed_page})
                term_rows = []
                active = None
                continue
            codes = CODE.findall(cells[0]) if cells else []
            if not codes:
                if CREDIT.search(text) and not headings:
                    raise ValueError('OCR hours in a physical data band have no resolved code')
                continue
            if not active or len(cells) != 3:
                raise ValueError('OCR course row lacks three columns or an actual year/semester heading')
            residue = clean(CODE.sub('', cells[0]))
            if residue not in {'', 'หรือ', 'OR', 'or'}:
                raise ValueError('OCR code column has unexplained text')
            if len(codes) > 1 and not explicit_course_choice(cells[0], cells[1]):
                raise ValueError('OCR bundles require source association review')
            if CREDIT.search(cells[1]):
                raise ValueError('OCR hours leaked into the name column; retranscribe physical cells')
            name_text = name_lines(cells[1])
            category = None
            name_parts = name_text.splitlines()
            if len(name_parts) > 1 and re.fullmatch(r'กลุ่มวิชา(?:ที่กำหนดโดยคณะ|ตามเกณฑ์ของคณะ)\*?', name_parts[0].strip()):
                category = clean(name_parts.pop(0))
            names = bilingual_groups('\n'.join(name_parts))
            patterns = CREDIT.findall(cells[2])
            if not patterns or len(set(int(p.split('(')[0]) for p in patterns)) != 1:
                raise ValueError('OCR course hours missing or ambiguous')
            names, shared = shared_placeholder_names(codes, names, patterns, cells[2])
            if len(names) != len(codes):
                raise ValueError('OCR names have unresolved code associations')
            if len(codes) > 1 and (len(patterns) not in {1, len(codes)} or len({clean(p) for p in patterns}) != 1):
                raise ValueError('OCR code alternatives have unresolved hour associations')
            row = {'code': ' หรือ '.join(codes), **names[0], 'credits': ' หรือ '.join(dict.fromkeys(clean(p) for p in patterns)),
                'year': active[0], 'semester': active[1], 'source_file': source_file,
                'page_number': pdf_page, 'printed_page_number': printed_page,
                'prerequisite': None, 'category': category, 'type': None,
                'source_claims': [{'field': field, 'literal': value, 'pdf_page': pdf_page,
                    'printed_page': printed_page, 'pixel_box': region['original_pixel_box']}
                    for field, value in zip(('code', 'names', 'hours'), cells)]}
            if shared:
                row['source_name_groups'] = shared
                row['note'] = 'ช่อง placeholder เดียวมีหลายชื่อ; ไม่อนุมานการจับคู่ชื่อกับชั่วโมงหรือสิทธิเลือก'
            if len(codes) > 1:
                row['course_options'] = dict(zip(codes, names))
                row['alt_group'] = f'ocr-alternative-{source_file}-{pdf_page}-{region["original_pixel_box"][1]}'
            courses.append(row)
            term_rows.append(row)
    if term_rows:
        raise ValueError('OCR table is incomplete: its printed total/continuation is missing')
    if not courses or not totals:
        raise ValueError('OCR page has no complete academic-plan table')
    return {'courses': courses, 'term_totals': totals}
