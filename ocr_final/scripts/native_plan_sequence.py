"""Source-only table stream with whole bundles and adjacent-page continuations."""
import hashlib
import re

from scripts.source_native import (CODE, CREDIT, TERM, bilingual_groups, clean,
    explicit_course_choice, fitz, lines, shared_placeholder_names, specialization_cell)


def credit_total(rows):
    ordinary, bundles = 0, {}
    for index, row in enumerate(rows):
        credits = int(re.match(r'\d+', str(row.get('credits_raw') or row['credits'])).group())
        if row.get('bundle_id'):
            slots = bundles.setdefault(row['bundle_id'], {})
            slot = row.get('alt_group') or f'row-{index}'
            if slot in slots and slots[slot] != credits:
                raise ValueError('Within-bundle alternatives have unequal credits')
            slots[slot] = credits
        else:
            ordinary += credits
    bundles = {key: sum(slots.values()) for key, slots in bundles.items()}
    if bundles and len(set(bundles.values())) != 1:
        raise ValueError('Whole specialization bundles have unequal credits; no inferred slot pairing')
    return ordinary + (next(iter(bundles.values())) if bundles else 0)


def merge_continuation(previous, current):
    """Join only a leading source OR or an orphan cell on the adjacent page."""
    cells = current['cells']
    if current['page'] != previous['page'] + 1:
        raise ValueError('Continuation is not on the adjacent PDF page')
    if clean(cells[0]) and not re.match(r'^(?:หรือ|OR)\b|^หรือ', clean(cells[0])):
        raise ValueError('Continuation lacks an explicit leading relation')
    for index, field in enumerate(('code', 'names', 'hours')):
        if clean(cells[index]):
            previous['cells'][index] += '\n' + cells[index]
            previous['claims'].append({'field': field, 'pdf_page': current['page'],
                'printed_page': current['printed'], 'literal': cells[index]})


def table_rows(page, table, decoder):
    physical = sorted({tuple(c) for r in table.rows for c in r.cells if c})
    text = lambda box: '\n'.join(r['text'] for r in lines(page, fitz.Rect(box), decoder))
    headers = {}
    for box in physical:
        if box[1] <= table.bbox[1] + 40:
            for label in ('รหัสวิชา', 'ชื่อวิชา', 'หน่วยกิต'):
                if label in text(box):
                    if label in headers and headers[label] != box:
                        raise ValueError('Ambiguous table column identity')
                    headers[label] = box
    if headers and len(headers) != 3:
        raise ValueError('Incomplete table header')
    if headers:
        code, name, credit = [headers[k] for k in ('รหัสวิชา', 'ชื่อวิชา', 'หน่วยกิต')]
        start = max(code[3], name[3], credit[3])
    else:
        # Re-derive boundaries from this page's cells, then compare with the
        # preceding table. Slight typesetting shifts must not clip characters.
        first = min(physical, key=lambda b: (b[1], b[0]))
        code = first
        names = [b for b in physical if abs(b[1]-first[1]) < 1 and abs(b[0]-first[2]) < 1]
        if len(names) != 1:
            raise ValueError('Headerless continuation columns unresolved')
        name = names[0]
        start = table.bbox[1]
    if abs(code[2]-name[0]) > 1:
        raise ValueError('Code/name columns do not align')
    result = []
    # Physical total rows can split into narrow empty cells. Union all row
    # boundaries and read semantic columns once per printed row.
    spans = sorted({(b[1], b[3]) for b in physical
                    if b[1] >= start-.5 and abs(b[0]-code[0]) < 1})
    for top, bottom in spans:
        boxes = [(code[0],top,code[2],bottom), (name[0],top,name[2],bottom),
                 (name[2],top,table.bbox[2],bottom)]
        values = [text(b) for b in boxes]
        # A merged total cell straddles the code/name divider.
        whole = text((table.bbox[0],top,table.bbox[2],bottom))
        if not CODE.search(whole) and re.search(r'\bรวม\b|รวม', whole) and re.search(r'\d+\s*$', whole):
            values = ['รวม', '', re.search(r'(\d+)\s*$', whole)[1]]
        result.append((values, boxes))
    return bool(headers), (code[0],code[2],name[2],table.bbox[2]), result


def is_whole_bundle(raw):
    codes = CODE.findall(raw['cells'][0])
    if not codes or any(re.search(r'[xX]', c) for c in codes):
        return False
    positioned = raw['positioned']
    code_lines = [r for r in positioned[0] if CODE.search(r['text'])]
    if not code_lines:
        return False
    boundary = code_lines[0]['bbox'][1] - 3
    # Older plans print one project per branch under a separate branch heading.
    # These are three one-course bundles, governed by the source branch rule.
    branch = any(r['bbox'][1] < boundary and re.match(r'^แขนงวิชา', r['text'])
                 for r in positioned[1])
    return branch or (len(codes)>1 and not explicit_course_choice(*raw['cells'][:2]))


def parse_row(raw, year, semester, source_file, rule):
    code_text, name_text, credit_text = raw['cells']
    codes = CODE.findall(code_text)
    if not codes or clean(CODE.sub('',code_text)) not in {'','หรือ','OR','or'}:
        raise ValueError('Missing/ambiguous source code')
    base = {'year':year,'semester':semester,'source_file':source_file,
            'page_number':raw['page'],'printed_page_number':raw['printed'],
            'source_claims':raw['claims'],'prerequisite':None,'type':None,'category':None}
    if is_whole_bundle(raw):
        if not rule:
            raise ValueError('Whole-group selection rule has no source evidence')
        positioned = raw['positioned']
        if explicit_course_choice(code_text,name_text):
            first = min(r['bbox'][1] for r in positioned[0] if CODE.search(r['text'])) - 3
            heading = [r['text'] for r in positioned[1] if r['bbox'][1] < first]
            body = [r for r in positioned[1] if r['bbox'][1] >= first]
            label = clean(' '.join(heading))
            if not re.match(r'^แขนงวิชา',label):
                raise ValueError('Nested source choice has no separate branch heading')
            inner = {**raw,'cells':[code_text,'\n'.join(r['text'] for r in body),credit_text],
                     'positioned':[positioned[0],body,positioned[2]]}
            parsed = parse_row(inner,year,semester,source_file,rule)
            bundle = hashlib.sha256(re.sub(r'[\s,，]', '', label).encode('utf8')).hexdigest()[:16]
            return [{**c,'bundle_id':bundle,'bundle_label':label,'selection_rule':rule} for c in parsed]
        group = specialization_cell(positioned,positioned[1])
        # Source heading punctuation/line wrapping is not a new group identity.
        canonical = re.sub(r'[\s,，]', '', group['label'])
        bundle = hashlib.sha256(canonical.encode('utf8')).hexdigest()[:16]
        return [{**base, **c, 'bundle_id':bundle,'bundle_label':group['label'],
                 'selection_rule':rule} for c in group['courses']]
    category = None
    name_lines = name_text.splitlines()
    if len(name_lines)>1 and re.match(r'^กลุ่มวิชา(?:ที่กำหนดโดยคณะ|ตามเกณฑ์ของคณะ)',name_lines[0]):
        category = clean(name_lines.pop(0))
    names = bilingual_groups('\n'.join(name_lines))
    patterns = CREDIT.findall(credit_text)
    if not patterns:
        raise ValueError('Source hour pattern missing')
    names, shared = shared_placeholder_names(codes,names,patterns,credit_text)
    if len(codes)>1 and (len(patterns) not in {1,len(codes)} or len({clean(p) for p in patterns}) != 1):
        raise ValueError('Code alternatives have unresolved hour associations')
    row = {**base,'code':' หรือ '.join(codes),**names[0],'category':category,
           'credits':' หรือ '.join(dict.fromkeys(clean(p) for p in patterns))}
    if len(codes)>1:
        row['course_options'] = dict(zip(codes,names))
        for code, option in row['course_options'].items():
            claims = [c for c in raw['claims'] if c['field']=='code' and code in CODE.findall(c['literal'])]
            if len(claims)!=1:
                raise ValueError('Alternative code page identity ambiguous')
            option['page_number'] = claims[0]['pdf_page']
            option['printed_page_number'] = claims[0]['printed_page']
            own_hours = [c for c in raw['claims'] if c['field']=='hours' and c['pdf_page']==option['page_number']]
            option['source_claims'] = [c for c in raw['claims'] if
                (c['field']=='code' and code in CODE.findall(c['literal'])) or
                (c['field']=='names' and any(clean(option[k]) in clean(c['literal']) for k in ('name_th','name_en'))) or
                (c['field']=='hours' and (not own_hours or c in own_hours))]
            # The relation itself cites both sides, without labelling the other
            # option's code/name as evidence of this option's own fields.
            option['source_claims'] += [{**c,'field':'alternative_relation'} for c in raw['claims'] if c['field']=='code']
        row['alt_group'] = f"source-alternative-{source_file}-{raw['page']}-{raw['ordinal']}"
        row['credits'] = clean(patterns[0])
    if shared:
        row['source_name_groups'] = shared
        row['note'] = 'ช่อง placeholder เดียวมีหลายชื่อ; ไม่อนุมานการจับคู่ชื่อกับชั่วโมงหรือสิทธิเลือก'
    return [row]


def numbered_section(text):
    match = re.match(r'^\s*(\d+(?:\.\d+)+)\.?\s+(.+)', text)
    return (tuple(map(int, match[1].split('.'))), match[2]) if match else None


def whole_group_rule(text):
    """Retain the literal choice rule, including timing and faculty approval."""
    patterns = (r'ต้องเลือกเรียนวิชาในกลุ่มวิชาใดกลุ่มวิชาหนึ่ง',
                r'นักศึกษาจะต้องเลือกแขนงที่จะเรียน')
    return next((line for line in text.splitlines()
                 if any(re.search(pattern, line) for pattern in patterns)), None)


def sequence(pdf, numbers, decoder, source_file):
    result, terms, pending, previous_number = {}, [], None, None
    rule, plan_section = None, None
    for number in numbers:
        page = pdf[number-1]; page_lines = lines(page,decoder=decoder)
        if decoder is None and re.search(r'[\ue000-\uf8ff]', page.get_text()):
            raise ValueError('Unreviewed private-use PDF glyphs; reviewed font decoding or image OCR required')
        folios = [int(r['text']) for r in page_lines if r['bbox'][1]<page.rect.height*.08 and r['text'].isdigit()]
        if len(set(folios)) != 1:
            raise ValueError(f'Printed page unresolved on PDF{number}')
        printed = folios[0]
        result[number] = {'courses':[],'term_totals':[],'source_cells':[], 'printed_page_number':printed}
        for table in sorted(page.find_tables().tables,key=lambda t:t.bbox[1]):
            sections = [(r['bbox'][1], numbered_section(r['text'])) for r in page_lines
                        if r['bbox'][1] < table.bbox[1] and numbered_section(r['text'])]
            if sections:
                _, (section, title) = max(sections, key=lambda r:r[0])
                if 'แผนการศึกษา' in re.sub(r'\s+', '', title):
                    plan_section = section
                elif (plan_section and section[:len(plan_section)] != plan_section
                      and section > plan_section):
                    if pending:
                        raise ValueError('New source section before unfinished plan term total')
                    # Selected pages can end with a clearly numbered non-plan
                    # section. Preserve the exclusion and its actual boundary.
                    result[number].setdefault('excluded_tables', []).append({
                        'bbox':list(table.bbox), 'section':'.'.join(map(str,section)),
                        'title':title, 'reason':'explicit source section outside academic plan'})
                    continue
            header, layout, rows = table_rows(page,table,decoder)
            headings = [(r['bbox'][1],TERM.search(clean(r['text']))) for r in page_lines if r['bbox'][1]<table.bbox[1]]
            headings = [(y,m) for y,m in headings if m]
            if header:
                if pending:
                    raise ValueError('Unfinished term before a new table header')
                if not headings:
                    raise ValueError('Term heading missing')
                year, semester = map(int,max(headings,key=lambda r:r[0])[1].groups())
                pending = {'year':year,'semester':semester,'rows':[],'layout':layout}
            elif not (pending and previous_number == number-1 and table.bbox[1]<page.rect.height*.15
                      and all(abs(a-b)<3 for a,b in zip(layout,pending['layout']))):
                raise ValueError('Headerless table lacks an adjacent, aligned unfinished term')
            for ordinal,(cells,boxes) in enumerate(rows,1):
                if clean(cells[0])=='รวม':
                    if not clean(cells[2]).isdigit() or not pending['rows']:
                        raise ValueError('Missing rows or ambiguous total')
                    pending['total'] = int(clean(cells[2]));pending['total_page']=number;pending['total_printed']=printed
                    terms.append(pending);pending=None
                    continue
                if pending is None:
                    raise ValueError('Rows after term total')
                raw = {'cells':cells,'page':number,'printed':printed,'ordinal':ordinal,
                       'positioned':[lines(page,fitz.Rect(b),decoder) for b in boxes],
                       'claims':[{'field':f,'pdf_page':number,'printed_page':printed,'literal':v}
                                 for f,v in zip(('code','names','hours'),cells) if clean(v)]}
                if not clean(cells[0]) or re.match(r'^หรือ|^OR\b',clean(cells[0])):
                    if not pending['rows']:
                        raise ValueError('Orphan continuation has no preceding row')
                    merge_continuation(pending['rows'][-1],raw)
                else:
                    pending['rows'].append(raw)
                result[number]['source_cells'].append(raw)
        previous_number = number
    if pending:
        raise ValueError('Selected pages end before the unfinished term total')
    needs_rule = any(is_whole_bundle(r) for t in terms for r in t['rows'])
    if needs_rule:
        # Only source PDF text is read. A rule is retained literally with its page;
        # it does not supply course names or an external specialization map.
        for index in reversed(range(min(numbers)-1)):
            text = '\n'.join(r['text'] for r in lines(pdf[index],decoder=decoder))
            match = whole_group_rule(text)
            if match:
                folios = [r['text'] for r in lines(pdf[index],decoder=decoder)
                          if r['bbox'][1]<pdf[index].rect.height*.08 and r['text'].isdigit()]
                if len(set(folios)) != 1:
                    raise ValueError('Selection rule printed page unresolved')
                candidate = {'text':clean(match),'pdf_page':index+1,'printed_page':int(folios[0]),'source_file':source_file}
                if rule and rule['text'] != candidate['text']:
                    raise ValueError('Multiple incompatible whole-group rules')
                rule = candidate
                break
    for term in terms:
        parsed = [c for raw in term['rows'] for c in parse_row(raw,term['year'],term['semester'],source_file,rule)]
        if credit_total(parsed) != term['total']:
            raise ValueError(f"Source term total mismatch {term['year']}/{term['semester']}")
        for c in parsed:
            result[c['page_number']]['courses'].append(c)
        result[term['total_page']]['term_totals'].append({'year':term['year'],'semester':term['semester'],
            'credits':term['total'],'source_file':source_file,'page_number':term['total_page'],
            'printed_page_number':term['total_printed']})
    return result, rule
