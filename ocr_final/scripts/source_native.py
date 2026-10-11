"""Fresh PDF text/table extraction; explicit font review is separate from OCR."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf as fitz


CODE = re.compile(r'(?<![0-9A-Za-z])[0-9xX]{8}(?![0-9A-Za-z])')
CREDIT = re.compile(r'\d+\s*\(\s*[0-9xX]+\s*-\s*[0-9xX]+\s*-\s*[0-9xX]+\s*\)')
TERM = re.compile(r'ปีที่\s*(\d+)\s*ภาคการศึกษาที่\s*(\d+)')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def clean(text):
    return ' '.join(text.split())


def font_decoder(document, review):
    """Use only explicitly reviewed mappings for exact embedded font bytes."""
    if review.get('format') != 1 or review.get('kind') != 'reviewed-font-encoding':
        raise ValueError('Unsupported font review')
    approved = {r['font_sha256']: r for r in review['fonts']}
    def decode(page, span):
        text = span['text']
        private = set(re.findall(r'[\ue000-\uf8ff]', text))
        if not private:
            return text
        candidates = []
        for xref, _, _, base, *_ in page.get_fonts(full=True):
            if base.split('+')[-1] != span['font']:
                continue
            cmap_kind, cmap_ref = document.xref_get_key(xref,'ToUnicode')
            if cmap_kind != 'xref':
                continue
            cmap = document.xref_stream(int(cmap_ref.split()[0])).decode('ascii')
            # Latin and Thai subsets can share a family name. Only the subset
            # which actually maps these private-use characters is a candidate.
            if not all(f'<{ord(c):04X}>' in cmap.upper() for c in private):
                continue
            # extract_font() may synthesize tables after rendering. Hash the
            # immutable PDF FontFile stream instead of MuPDF's repaired buffer.
            kind, descendant = document.xref_get_key(xref,'DescendantFonts')
            if kind == 'xref':
                descendant = document.xref_object(int(descendant.split()[0]))
            refs = re.findall(r'(\d+) 0 R',descendant)
            owner = int(refs[0]) if len(refs)==1 else xref
            descriptor = int(document.xref_get_key(owner,'FontDescriptor')[1].split()[0])
            stream = int(document.xref_get_key(descriptor,'FontFile2')[1].split()[0])
            digest = hashlib.sha256(document.xref_stream(stream)).hexdigest()
            if digest not in approved:
                raise ValueError('Embedded font hash has no reviewed encoding mapping: '+digest)
            mapping = approved[digest]['mapping']
            if any(f'{ord(c):04X}' not in mapping for c in private):
                raise ValueError('Unreviewed private-use glyph; do not guess Thai')
            candidates.append({c: chr(int(mapping[f'{ord(c):04X}'],16)) for c in private})
        if not candidates or any(m != candidates[0] for m in candidates):
            raise ValueError('Font identity or private-use encoding ambiguous')
        return ''.join(candidates[0].get(c,c) for c in text)
    return decode


def lines(page, rectangle=None, decoder=None):
    # Keep PDF character order. find_tables.extract() re-sorts Thai diacritics.
    result = []
    for block in page.get_text('dict', clip=rectangle)['blocks']:
        for line in block.get('lines', []):
            text = ''.join(decoder(page, span) if decoder else span['text']
                           for span in line['spans']).strip()
            if text:
                result.append({'text': text, 'bbox': list(line['bbox'])})
    return result


def bilingual_groups(text):
    groups, thai, english = [], [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line in {'หรือ', 'OR', 'or'}:
            continue
        # Classify an English name with a trailing Thai relation correctly,
        # but retain connectors inside a single source name (e.g. course group).
        classified = re.sub(r'\s+(?:หรือ|OR|or)\s*$', '', line)
        is_thai = bool(re.search(r'[\u0e00-\u0e7f]', classified))
        if is_thai and english:
            groups.append({'name_th': clean(' '.join(thai)), 'name_en': clean(' '.join(english))})
            thai, english = [], []
        (thai if is_thai else english).append(line)
    if thai or english:
        groups.append({'name_th': clean(' '.join(thai)), 'name_en': clean(' '.join(english))})
    if len(groups)>1:
        for group in groups:
            for key in ('name_th','name_en'):
                group[key] = re.sub(r'\s+(?:หรือ|OR|or)\s*$', '', group[key])
    if any(not g['name_th'] or not g['name_en'] for g in groups):
        raise ValueError('Native name cells lack resolved bilingual boundaries; OCR/review required')
    return groups


def shared_placeholder_names(codes, names, patterns, credit_text):
    """One printed placeholder cell may list several labels, not several slots."""
    if len(names) == len(codes):
        return names, None
    if (len(codes) != 1 or not re.search(r'[xX]', codes[0]) or len(names) < 2
            or not patterns or len({int(re.match(r'\d+', p).group()) for p in patterns}) != 1
            or (len(patterns) > 1 and not re.search(r'หรือ|\bOR\b', credit_text, re.I))):
        raise ValueError('Code/name/hour alternative associations unresolved')
    # Keep paired Thai/English labels in SQL; no inferred name-to-hour matching.
    return [{'name_th': ' / '.join(n['name_th'] for n in names),
             'name_en': ' / '.join(n['name_en'] for n in names)}], names


def explicit_course_choice(code_text, name_text):
    """A printed OR may be in the code cell or between bilingual name groups."""
    if re.search(r'หรือ|\bOR\b', code_text, re.I):
        return True
    rows = [line.strip() for line in name_text.splitlines() if line.strip()]
    for index, line in enumerate(rows[:-1]):
        match = re.search(r'(?:^|\s)(?:หรือ|OR|or)\s*$', line)
        if not match:
            continue
        # English label ends with OR, then the next Thai label starts. Do not
        # reinterpret a connector inside a wrapped course name as row choice.
        before = line[:match.start()].strip()
        if (not before or not re.search(r'[\u0e00-\u0e7f]', before)) and re.search(r'[\u0e00-\u0e7f]', rows[index+1]):
            return True
    return False


def logical_rows(page, table, decoder=None):
    """Recover three semantic columns from merged physical cells, using headers."""
    def text(box):
        return '\n'.join(r['text'] for r in lines(page, fitz.Rect(box), decoder))
    cells = sorted({tuple(c) for r in table.rows for c in r.cells if c})
    headings = {}
    for box in cells:
        if box[1] > table.bbox[1]+40:
            continue
        value = text(box)
        for label in ('รหัสวิชา', 'ชื่อวิชา', 'หน่วยกิต'):
            if label in value:
                if label in headings and headings[label] != box:
                    raise ValueError('Ambiguous logical table header')
                headings[label] = box
    if len(headings) != 3:
        return []
    code, name, credit = (headings[k] for k in ('รหัสวิชา','ชื่อวิชา','หน่วยกิต'))
    if not (abs(code[2]-name[0]) < 1 and name[2] <= credit[0]+6):
        raise ValueError('Logical source columns do not align')
    start = max(code[3],name[3],credit[3])
    result = []
    for box in sorted(cells,key=lambda b:(b[1],b[0])):
        if abs(box[0]-code[0]) > 1 or box[1] < start-.5:
            continue
        # Code cells span each printed row, including bilingual/alternative text.
        boxes = [box, (name[0],box[1],name[2],box[3]),
                 (name[2],box[1],table.bbox[2],box[3])]
        result.append(([text(b) for b in boxes], boxes))
    return result


def specialization_cell(cells, positioned_names):
    """Decode a printed group cell without inventing independent alternatives.

    This is a source fragment, not an activatable plan. Whole-group selection
    and continuation evidence still need SQL representation and validation.
    The input contains only the current PDF cell and its line coordinates.
    """
    code_lines = [r for r in cells[0] if CODE.search(r['text'])]
    if len(code_lines) < 2:
        raise ValueError('Not a multi-course group cell')
    codes = [CODE.findall(r['text']) for r in code_lines]
    if any(len(c) != 1 or clean(CODE.sub('', r['text'])) for c, r in zip(codes, code_lines)):
        raise ValueError('Group code lines ambiguous')
    boundary = code_lines[0]['bbox'][1] - 3
    heading = [r['text'] for r in positioned_names if r['bbox'][1] < boundary]
    body = [r['text'] for r in positioned_names if r['bbox'][1] >= boundary]
    if not heading or not re.match(r'^กลุ่มวิชา', clean(' '.join(heading))):
        raise ValueError('Group heading is not geometrically separate from course names')
    names = bilingual_groups('\n'.join(body))
    patterns = CREDIT.findall('\n'.join(r['text'] for r in cells[2]))
    if len(names) != len(codes) or len(patterns) != len(codes):
        raise ValueError('Group code/name/hour counts disagree')
    return {'label':clean(' '.join(heading)),
            'courses':[{'code':c[0], **n, 'credits':clean(p)}
                       for c,n,p in zip(codes,names,patterns)],
            'selection_status':'requires whole-group source rule and SQL coupling; not independent OR slots'}


def plan_page(page, source_file, number, decoder=None):
    if decoder is None and re.search(r'[\ue000-\uf8ff]',page.get_text()):
        raise ValueError('PDF font uses private-use characters; Thai text cannot be certified by this native route. ตรวจ font mapping หรือใช้ OCR แยก; ห้ามเดาหรือเติมจาก DB')
    page_lines = lines(page, decoder=decoder)
    folios = [int(r['text']) for r in page_lines
              if r['bbox'][1] < page.rect.height * .08 and r['text'].isdigit()]
    if len(set(folios)) != 1:
        raise ValueError('Printed page identity unresolved')
    printed = folios[0]
    courses, totals, evidence = [], [], []
    tables = sorted(page.find_tables().tables, key=lambda t: t.bbox[1])
    for table in tables:
        cell_rows = logical_rows(page, table, decoder)
        if not cell_rows:
            continue
        preceding = [(r['bbox'][1], TERM.search(clean(r['text']))) for r in page_lines
                     if r['bbox'][1] < table.bbox[1]]
        headings = [(y, m) for y, m in preceding if m]
        if not headings:
            raise ValueError('Plan table has no source year/semester heading')
        match = max(headings, key=lambda pair: pair[0])[1]
        year, semester = map(int, match.groups())
        term_rows, printed_total = [], None
        for row_number, (cells, cell_boxes) in enumerate(cell_rows, 1):
            code_text, name_text, credit_text = cells
            if clean(code_text) == 'รวม' or (not clean(code_text) and clean(name_text) == 'รวม'):
                if not clean(credit_text).isdigit() or printed_total is not None:
                    raise ValueError('Ambiguous printed term total')
                printed_total = int(clean(credit_text))
                continue
            codes = CODE.findall(code_text)
            if not codes or clean(CODE.sub('', code_text)).strip() not in {'', 'หรือ', 'OR', 'or'}:
                raise ValueError('Missing/ambiguous native course code; no invented slot allowed')
            name_lines = name_text.splitlines()
            category = None
            # A separately printed group heading is metadata, not a course name.
            if len(name_lines)>1 and re.match(r'^กลุ่มวิชา(?:ที่กำหนดโดยคณะ|ตามเกณฑ์ของคณะ)',name_lines[0]):
                category = clean(name_lines.pop(0))
            names = bilingual_groups('\n'.join(name_lines))
            patterns = CREDIT.findall(credit_text)
            if not patterns:
                raise ValueError('Missing source credit pattern')
            names, shared_names = shared_placeholder_names(codes, names, patterns, credit_text)
            if len(codes) > 1:
                if not explicit_course_choice(code_text, name_text):
                    raise ValueError('Multiple codes without explicit source alternative relation')
                if len(patterns) not in {1, len(codes)} or len({clean(x) for x in patterns}) != 1:
                    raise ValueError('Different-credit code alternatives need explicit association support')
            base = {'code': ' หรือ '.join(codes), 'name_th': names[0]['name_th'],
                    'name_en': names[0]['name_en'], 'credits': clean(patterns[0]),
                    'year': year, 'semester': semester, 'category': category, 'type': None,
                    'prerequisite': None, 'source_file': source_file,
                    'page_number': number, 'printed_page_number': printed}
            if shared_names:
                base['source_name_groups'] = shared_names
                base['note'] = 'ช่อง placeholder เดียวมีหลายชื่อ; hour patterns ใช้ร่วมกัน ยังไม่จับคู่ชื่อกับรูปแบบชั่วโมงหรืออนุมานสิทธิเลือก'
            if len(codes) > 1:
                base['course_options'] = dict(zip(codes, names))
                base['alt_group'] = f'source-alternative-{source_file}-{number}-{row_number}'
            elif len(patterns) > 1:
                # One code can have mutually exclusive printed hour patterns.
                base['credits'] = ' หรือ '.join(clean(x) for x in patterns)
            term_rows.append(base)
            evidence.append({'year': year, 'semester': semester, 'row': row_number,
                             'cells': cells, 'cell_boxes': cell_boxes,
                             'record': base})
        if printed_total is None or not term_rows:
            raise ValueError('Incomplete source table: rows or printed total missing')
        calculated = sum(int(re.match(r'\d+', r['credits']).group()) for r in term_rows)
        if calculated != printed_total:
            raise ValueError(f'Native rows do not reconcile with source total {year}/{semester}')
        courses.extend(term_rows)
        totals.append({'year': year, 'semester': semester, 'credits': printed_total,
                       'total_credits': printed_total, 'source_file': source_file,
                       'page_number': number, 'printed_page_number': printed})
    if not courses or '\ufffd' in page.get_text():
        raise ValueError('Native text/table extraction unavailable or unreliable; use explicit OCR mode')
    return {'courses': courses, 'term_totals': totals, 'source_cells': evidence,
            'printed_page_number': printed}


def extract(pdf_path, numbers, output, max_pages=None, font_review=None):
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    state = {'method': 'pdf-text-tables', 'ocr_performed': False, 'corrections': [],
             'dependencies': {'source_sha256': sha(pdf_path), 'code_sha256': sha(Path(__file__)),
                              'renderer': 'PyMuPDF', 'version': fitz.VersionBind, 'dpi': 200},
             'processed': [], 'failed': [], 'pending_requested': list(numbers)}
    save(output/'manifest-extraction.json', state)
    review = json.loads(font_review.read_text(encoding='utf-8')) if font_review else None
    if review:
        save(output/'font-encoding-review.json',review)
        state['corrections'] = [{'kind':'reviewed-font-encoding',
                                'path':'font-encoding-review.json','sha256':sha(output/'font-encoding-review.json')}]
    with fitz.open(pdf_path) as pdf:
        decoder = font_decoder(pdf,review) if review else None
        selected = numbers[:max_pages] if max_pages else numbers
        # Parse the entire selected stream before publishing finalized row
        # artifacts: a following page can complete a preceding row's fields.
        from scripts.native_plan_sequence import sequence
        try:
            parsed_pages, rule = sequence(pdf, selected, decoder, pdf_path.name)
            stream_error = None
        except (ValueError, RuntimeError) as exc:
            parsed_pages, rule, stream_error = {}, None, str(exc)
        if rule:
            save(output/'selection-rule.json', rule)
            pdf[rule['pdf_page']-1].get_pixmap(dpi=200).save(output/'selection-rule.png')
            state['supporting_source'] = [{'pdf_page':rule['pdf_page'],
                'image_sha256':sha(output/'selection-rule.png'), 'record_sha256':sha(output/'selection-rule.json')}]
        pdf[0].get_pixmap(dpi=200).save(output/'identity.png')
        (output/'identity.txt').write_text(pdf[0].get_text(),encoding='utf-8')
        state['identity_image_sha256'] = sha(output/'identity.png')
        for number in numbers[:max_pages] if max_pages else numbers:
            try:
                page = pdf[number-1]
                page.get_pixmap(dpi=200).save(output/f'page-{number}.png')
                (output/f'page-{number}.txt').write_text(page.get_text(), encoding='utf-8')
                if stream_error:
                    raise ValueError(stream_error)
                parsed = parsed_pages[number]
                save(output/f'page-{number}.plan.json', parsed)
                state['processed'].append({'pdf_page': number, 'printed_book_page': parsed['printed_page_number'],
                    'image_sha256': sha(output/f'page-{number}.png'),
                    'native_text_sha256': sha(output/f'page-{number}.txt'),
                    'parsed_sha256': sha(output/f'page-{number}.plan.json'), 'quality_flags': []})
                state['pending_requested'].remove(number)
            except (ValueError, RuntimeError) as exc:
                state['failed'].append({'pdf_page': number, 'error': str(exc)})
            save(output/'manifest-extraction.json', state)
    state['seconds'] = round(time.perf_counter()-started, 3)
    save(output/'manifest-extraction.json', state)
    return state


def validate_sql_chain(candidate, item):
    """Ensure normalization/ingestion preserved every native source-table field."""
    import sqlite3
    from contextlib import closing
    expected = []
    expected_names = []
    expected_bundles, expected_members, expected_claims = set(), [], []
    expected_totals = []
    raw = candidate/'raw'/item['profile']
    for path in sorted(raw.glob('page-*.plan.json')):
        parsed = json.loads(path.read_text(encoding='utf-8'))
        expected_totals.extend((t['year'],t['semester'],t['credits'],t['source_file'],t['page_number'],t['printed_page_number'])
                               for t in parsed.get('term_totals',[]))
        for row in parsed['courses']:
            codes = CODE.findall(row['code'])
            if row.get('bundle_id'):
                rule = row['selection_rule']
                expected_bundles.add((row['year'],row['semester'],row['bundle_id'],row['bundle_label'],
                    rule['text'],rule['source_file'],rule['pdf_page'],rule['printed_page']))
                expected_members.append((row['year'],row['semester'],codes[0],row['bundle_id']))
            for code in codes:
                option = row.get('course_options',{}).get(code,{})
                for claim in option.get('source_claims',row.get('source_claims', [])):
                    expected_claims.append((row['year'],row['semester'],code,row.get('bundle_id'),claim['field'],
                        row['source_file'],claim['pdf_page'],claim['printed_page'],clean(claim['literal'])))
            for position, name in enumerate(row.get('source_name_groups', []), 1):
                expected_names.append((row['year'],row['semester'],codes[0],position,name['name_th'],name['name_en']))
            for index, code in enumerate(codes):
                name = row.get('course_options', {}).get(code, row)
                expected.append((row['year'], row['semester'], code,
                    clean(name['name_th']), clean(name['name_en']),
                    int(re.match(r'\d+',row['credits']).group()), re.sub(r'\s','',row['credits']),
                    name.get('page_number',row['page_number']), name.get('printed_page_number',row['printed_page_number']),
                    index+1 if len(codes)>1 else None))
    db_path = candidate/item['path']
    with closing(sqlite3.connect(db_path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        actual = [(r[0],r[1],r[2],clean(r[3] or ''),clean(r[4] or ''),r[5],
                   re.sub(r'\s','',r[6] or ''),r[7],r[8],r[9]) for r in db.execute('''
            SELECT year,semester,CASE WHEN is_placeholder=1 THEN raw_code ELSE code END,
                   name_th,name_en,credits,credits_raw,page_number,printed_page_number,alternative_index
            FROM plan_item''')]
        if sorted(expected,key=repr) != sorted(actual,key=repr):
            missing=[r for r in expected if r not in actual]
            extra=[r for r in actual if r not in expected]
            raise ValueError(f'Native source→SQLite fidelity mismatch: missing={missing[:2]!r}; extra={extra[:2]!r}')
        has_names = db.execute("SELECT 1 FROM sqlite_master WHERE name='plan_item_source_name'").fetchone()
        actual_names = [tuple(r) for r in db.execute('''SELECT p.year,p.semester,p.raw_code,n.position,n.name_th,n.name_en
            FROM plan_item_source_name n JOIN plan_item p ON p.id=n.plan_item_id''')] if has_names else []
        if sorted(expected_names,key=repr) != sorted(actual_names,key=repr):
            raise ValueError('Shared source-cell bilingual name pairs lost in SQLite')
        if expected_bundles or expected_claims:
            actual_bundles = {tuple(r) for r in db.execute('SELECT * FROM plan_bundle')}
            actual_members = [tuple(r) for r in db.execute('''SELECT p.year,p.semester,p.code,m.bundle_id
                FROM plan_bundle_member m JOIN plan_item p ON p.id=m.plan_item_id''')]
            actual_claims = [(*r[:-1],clean(r[-1])) for r in db.execute('''SELECT p.year,p.semester,
                CASE WHEN p.is_placeholder=1 THEN p.raw_code ELSE p.code END,m.bundle_id,
                c.field,c.source_file,c.pdf_page,c.printed_page,c.literal
                FROM plan_source_claim c JOIN plan_item p ON p.id=c.plan_item_id
                LEFT JOIN plan_bundle_member m ON m.plan_item_id=p.id''')]
            if (expected_bundles != actual_bundles or sorted(expected_members,key=repr)!=sorted(actual_members,key=repr)
                    or sorted(expected_claims,key=repr)!=sorted(actual_claims,key=repr)):
                raise ValueError('Whole bundle membership or claim-specific source provenance lost in SQLite')
            if sorted(expected_totals) != sorted(tuple(r) for r in db.execute('SELECT * FROM plan_term_source')):
                raise ValueError('Printed term total provenance lost in SQLite')
        unknown = db.execute('SELECT COUNT(*) FROM prerequisite').fetchone()[0]
        if unknown:
            raise ValueError('Plan-only source cannot establish prerequisite facts')
    return {'rows':len(actual),'source_sql_fields_match':True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--page', type=int, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-pages', type=int)
    parser.add_argument('--font-review', type=Path, help='Explicit reviewed encoding map; never used by raw build')
    args = parser.parse_args()
    result = extract(args.pdf, args.page, args.output, args.max_pages, args.font_review)
    return int(bool(result['failed']))


if __name__ == '__main__':
    raise SystemExit(main())
