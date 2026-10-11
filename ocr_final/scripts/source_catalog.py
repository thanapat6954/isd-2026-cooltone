"""Fresh native source corpus and catalog candidates; no prior facts or model fallback.

Literal source records are diagnostic until independent coverage/association review.
They do not assert registration rights, logical prerequisite edges or eligibility.
"""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import time
import sys

import pymupdf as fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.source_native import CODE, CREDIT, clean, lines, save, sha

SECTION = re.compile(r'^(?:ภาคผนวก(?:\s|$)|หมวด(?:วิชา|ที่)|กลุ่มวิชา|คำอธิบายรายวิชา|APPENDIX\b|CHAPTER\b)', re.I)


DDL = '''
CREATE TABLE source_document_page (
 source_file TEXT, pdf_page INTEGER, printed_page INTEGER, source_sha256 TEXT,
 extraction_method TEXT, text TEXT, PRIMARY KEY(source_file,pdf_page));
CREATE TABLE catalog_source_entry (
 entry_id INTEGER PRIMARY KEY, code TEXT, name_th TEXT, name_en TEXT,
 credits_raw TEXT, prerequisite_literal TEXT, description_th TEXT,
 description_en TEXT, source_file TEXT, pdf_page INTEGER, printed_page INTEGER,
 association_status TEXT);
CREATE TABLE catalog_source_fragment (
 entry_id INTEGER, pdf_page INTEGER, printed_page INTEGER, text TEXT,
 PRIMARY KEY(entry_id,pdf_page));
CREATE TABLE program_rule_source (
 source_file TEXT, pdf_page INTEGER, printed_page INTEGER, heading TEXT,
 literal_page_text TEXT, interpretation_status TEXT);
'''


def body(page):
    # Geometry, not a dictionary of footer text; preserve original characters.
    return sorted((r for r in lines(page) if page.rect.height*.075 <= r['bbox'][1]
                   and r['bbox'][3] < page.rect.height*.91),
                  key=lambda r: (round(r['bbox'][1], 1), r['bbox'][0]))


def folio(page):
    values = {int(r['text']) for r in lines(page)
              if r['bbox'][1] < page.rect.height*.075 and r['text'].isdigit()}
    return next(iter(values)) if len(values) == 1 else None


def catalog_headers(rows):
    result = []
    for i, row in enumerate(rows):
        match = re.match(r'^([0-9]{8})(?:\s|$)', row['text'])
        if not match:
            continue
        same_line = [r for r in rows[max(0,i-4):i+5]
                     if r.get('pdf_page') == row.get('pdf_page') and abs(r['bbox'][1]-row['bbox'][1]) < 2]
        credit = [clean(m.group()) for r in same_line for m in CREDIT.finditer(r['text'])]
        if len(credit) != 1:
            continue
        following = []
        for later in rows[i+1:i+16]:
            if re.match(r'^[0-9]{8}(?:\s|$)',later['text']) or SECTION.search(later['text']):
                break
            following.append(later)
        markers = [j for j, r in enumerate(following) if re.search(r'วิชาบังคับก่อน|PREREQUISITE', r['text'], re.I)]
        if not markers:
            result.append({'index': i, 'code': match[1], 'status': 'no_prerequisite_marker'})
            continue
        first_marker = i+1+markers[0]
        name_rows = [r['text'] for r in rows[i:first_marker]
                     if not CREDIT.fullmatch(clean(r['text']))]
        name_rows[0] = re.sub(r'^[0-9]{8}\s*', '', name_rows[0])
        th = clean(' '.join(t for t in name_rows if re.search(r'[\u0e00-\u0e7f]', t)))
        en = clean(' '.join(t for t in name_rows if t and not re.search(r'[\u0e00-\u0e7f]', t)))
        # Full geometry and literal prerequisites remain for independent review.
        result.append({'index': i, 'code': match[1], 'credits_raw': credit[0],
                       'name_th': th, 'name_en': en, 'marker': first_marker,
                       'status': 'candidate' if th and en else 'name_boundary_unresolved'})
    return result


def extract(pdf_path, output):
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    source_hash = sha(pdf_path)
    records, page_records, rules, diagnostics = [], [], [], []
    with fitz.open(pdf_path) as pdf:
        pages = [[{**r,'pdf_page':n} for r in body(page)] for n,page in enumerate(pdf,1)]
        all_rows = [r for rows in pages for r in rows]
        headers = catalog_headers(all_rows)
        for n, page in enumerate(pdf, 1):
            text = page.get_text()
            (output/f'page-{n}.txt').write_text(text, encoding='utf-8')
            page_records.append((pdf_path.name, n, folio(page), source_hash, 'pdf-native-text', text))
            save(output/'source-catalog-checkpoint.json', {'source_sha256':source_hash,
                 'code_sha256':sha(Path(__file__)),'processed_source_pages':n,
                 'total_source_pages':len(pdf),'status':'generating; not activation-ready'})
            for row in pages[n-1]:
                if re.search(r'เกณฑ์การสำเร็จการศึกษา|ระเบียบ.*การศึกษา|ข้อบังคับ.*การศึกษา', row['text']):
                    rules.append((pdf_path.name, n, folio(page), row['text'], text,
                                  'literal source only; scope/continuation/interpretation not certified'))
            for anchor in (h for h in headers if all_rows[h['index']]['pdf_page']==n):
                if anchor['status'] != 'candidate':
                    diagnostics.append({'pdf_page': n, **anchor})
                    continue
                end = next((h['index'] for h in headers if h['index'] > anchor['index']),len(all_rows))
                end = next((i for i in range(anchor['marker']+1,end)
                            if SECTION.search(all_rows[i]['text'])),end)
                segment = all_rows[anchor['index']:end]
                fragments = []
                for number in sorted({r['pdf_page'] for r in segment}):
                    fragments.append({'pdf_page':number,'printed_page':folio(pdf[number-1]),
                                      'text':'\n'.join(r['text'] for r in segment if r['pdf_page']==number)})
                text_lines = [r['text'] for r in all_rows[anchor['marker']:end]]
                # Preserve prerequisites as a literal block. Wrapped continuation
                # cannot safely be turned into AND/OR edges by code matching.
                text_lines = [t for t in text_lines if not CREDIT.fullmatch(clean(t))]
                english_marker = [i for i,t in enumerate(text_lines) if re.search(r'PREREQUISITE',t,re.I)]
                boundary = None
                if english_marker:
                    boundary = next((i for i in range(english_marker[0]+1,len(text_lines))
                                     if re.search(r'[\u0e00-\u0e7f]',text_lines[i])),None)
                if boundary is None:
                    diagnostics.append({'pdf_page': n, 'code': anchor['code'],
                                        'status': 'prerequisite_description_boundary_unresolved'})
                    pre, description = text_lines, []
                else:
                    pre, description = text_lines[:boundary], text_lines[boundary:]
                th = clean(' '.join(t for t in description if re.search(r'[\u0e00-\u0e7f]', t)))
                en = clean(' '.join(t for t in description if not re.search(r'[\u0e00-\u0e7f]', t)))
                records.append({**anchor, 'pdf_page': n, 'printed_page': folio(page),
                                'prerequisite_literal': '\n'.join(pre),
                                'description_th': th, 'description_en': en,
                                'fragments': fragments,
                                'association_status': 'unreviewed native candidate'})
                page.get_pixmap(dpi=150).save(output/f'catalog-page-{n}.png')
    database = output/'source.sqlite'
    with sqlite3.connect(database) as db:
        db.executescript(DDL)
        db.executemany('INSERT INTO source_document_page VALUES (?,?,?,?,?,?)', page_records)
        db.executemany('INSERT INTO program_rule_source VALUES (?,?,?,?,?,?)', rules)
        for entry_id, record in enumerate(records, 1):
            db.execute('INSERT INTO catalog_source_entry VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       (entry_id, record['code'], record['name_th'], record['name_en'], record['credits_raw'],
                        record['prerequisite_literal'], record['description_th'], record['description_en'],
                        pdf_path.name, record['pdf_page'], record['printed_page'], record['association_status']))
            db.executemany('INSERT INTO catalog_source_fragment VALUES (?,?,?,?)',
                           [(entry_id, f['pdf_page'], f['printed_page'], f['text']) for f in record['fragments']])
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    save(output/'catalog-candidates.json', records)
    state = {'method': 'pdf-native-text', 'ocr_performed': False, 'reviewed_corrections': [],
             'source_sha256': source_hash, 'code_sha256': sha(Path(__file__)),
             'renderer_version': fitz.VersionBind, 'source_pages': len(page_records),
             'catalog_candidates': len(records), 'unique_candidate_codes': len({r['code'] for r in records}),
             'rule_heading_candidates': len(rules), 'unresolved_headers': diagnostics,
             'domains': {'academic_plan': False, 'source_document_corpus': True,
                         'catalog_complete': False, 'program_rules_complete': False},
             'limitations': ['literal native text; visual fidelity not certified for every page',
                             'catalog candidates require boundary/coverage review',
                             'wrapped prerequisites not normalized; no logical edges or rights inferred',
                             'rule headings may include TOC; normative scope not validated'],
             'database_sha256': sha(database), 'seconds': round(time.perf_counter()-started, 3)}
    save(output/'source-catalog.json', state)
    return state


def ingest(source, target):
    """Copy only freshly extracted literal tables into the staged database."""
    with sqlite3.connect(target) as db:
        db.execute('ATTACH DATABASE ? AS fresh', (str(source.resolve()),))
        for table in ('source_document_page', 'catalog_source_entry', 'catalog_source_fragment', 'program_rule_source'):
            db.execute(f'CREATE TABLE {table} AS SELECT * FROM fresh.{table}')
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Staged source catalog integrity failed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdf', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--staged-database', type=Path)
    args = p.parse_args()
    state = extract(args.pdf, args.output)
    if args.staged_database:
        ingest(args.output/'source.sqlite', args.staged_database)
    print(json.dumps({k: v for k, v in state.items() if k not in {'unresolved_headers'}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
