"""Fresh native source corpus and catalog candidates; no prior facts or model fallback.

Literal source records are diagnostic until independent coverage/association review.
They do not assert registration rights, logical prerequisite edges or eligibility.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import time
import sys

import pymupdf as fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.source_native import CODE, CREDIT, clean, font_decoder, lines, save, sha

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


def body(page, decoder=None):
    # Geometry, not a dictionary of footer text; preserve original characters.
    return sorted((r for r in lines(page, decoder=decoder) if page.rect.height*.075 <= r['bbox'][1]
                   and r['bbox'][3] < page.rect.height*.91),
                  key=lambda r: (round(r['bbox'][1], 1), r['bbox'][0]))


def folio(page, decoder=None):
    values = {int(r['text']) for r in lines(page, decoder=decoder)
              if r['bbox'][1] < page.rect.height*.075 and r['text'].isdigit()}
    return next(iter(values)) if len(values) == 1 else None


def image_text_gaps(page, rows):
    """Flag substantial body images whose contents native extraction cannot read.

    Embedded watermarks behind readable text do not imply missing text. A page
    with only a native header/footer over scanned content must not count as read.
    This conservative review gate also covers diagrams; it never invents text.
    """
    body_rect=fitz.Rect(0,page.rect.height*.075,page.rect.width,page.rect.height*.91)
    gaps=[]
    for image in page.get_image_info():
        rectangle=fitz.Rect(image['bbox']) & body_rect
        if rectangle.get_area() < page.rect.get_area()*.15:
            continue
        count=sum(len(row['text']) for row in rows
                  if rectangle.contains(fitz.Point((row['bbox'][0]+row['bbox'][2])/2,
                                                  (row['bbox'][1]+row['bbox'][3])/2)))
        if count<80:
            gaps.append({'bbox':list(rectangle),'native_characters':count,
                         'reason':'Substantial body image is unreadable from native text; image OCR/review required'})
    return gaps


def native_page(page, decoder=None):
    """Return usable native rows, or fail visibly before catalog association."""
    decoded=lines(page,decoder=decoder)
    text='\n'.join(r['text'] for r in decoded)
    if re.search(r'[\ue000-\uf8ff]',text):
        raise ValueError('Unreviewed private-use glyph; native page needs source review or image OCR')
    gaps=image_text_gaps(page,decoded)
    if gaps:
        raise ValueError('Image body requires OCR/review: '+json.dumps(gaps,ensure_ascii=False))
    return decoded,text


def scan_coverage(pdf_path, output, font_review=None):
    """Read-only source preflight, without copying old facts or claiming OCR."""
    output.mkdir(parents=True,exist_ok=False)
    review=json.loads(font_review.read_text(encoding='utf8')) if font_review else None
    result={'source_file':pdf_path.name,'source_sha256':sha(pdf_path),
            'code_sha256':sha(Path(__file__)),'decoder_sha256':sha(Path(__file__).with_name('source_native.py')),
            'font_review_sha256':sha(font_review) if font_review else None,
            'scope':'native page readiness only; no OCR or source certification','pages':[]}
    with fitz.open(pdf_path) as document:
        decoder=font_decoder(document,review) if review else None
        result['total_source_pages']=len(document)
        for n,page in enumerate(document,1):
            entry={'pdf_page':n}
            try:
                rows,text=native_page(page,decoder)
                entry.update(status='native-readable-unverified',native_characters=len(text))
            except ValueError as error:
                entry.update(status='image-ocr-or-review-required',reason=str(error))
            result['pages'].append(entry)
            save(output/'source-coverage.json',result)
    result['native_pages']=sum(r['status']=='native-readable-unverified' for r in result['pages'])
    result['ocr_or_review_pages']=len(result['pages'])-result['native_pages']
    save(output/'source-coverage.json',result)
    return result


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
        name_rows = [clean(CREDIT.sub('', r['text'])) for r in rows[i:first_marker]]
        name_rows[0] = re.sub(r'^[0-9]{8}\s*', '', name_rows[0])
        th = clean(' '.join(t for t in name_rows if re.search(r'[\u0e00-\u0e7f]', t)))
        en = clean(' '.join(t for t in name_rows if t and not re.search(r'[\u0e00-\u0e7f]', t)))
        # Full geometry and literal prerequisites remain for independent review.
        result.append({'index': i, 'code': match[1], 'credits_raw': credit[0],
                       'name_th': th, 'name_en': en, 'marker': first_marker,
                       'status': 'candidate' if th and en else 'name_boundary_unresolved'})
    return result


def extract(pdf_path, output, font_review=None, render_rejected_pages=0):
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    source_hash = sha(pdf_path)
    records, page_records, rules, diagnostics, rejected, render_failures = [], [], [], [], [], []
    review = json.loads(font_review.read_text(encoding='utf-8')) if font_review else None
    if review:
        save(output/'font-encoding-review.json', review)
    with fitz.open(pdf_path) as pdf:
        decoder = font_decoder(pdf, review) if review else None
        pages, page_texts, folios = [], [], []
        for n, page in enumerate(pdf, 1):
            original = page.get_text()
            (output/f'page-{n}.original.txt').write_text(original, encoding='utf-8')
            try:
                decoded,text=native_page(page,decoder)
                pages.append([{**r, 'pdf_page': n} for r in body(page, decoder)])
                folios.append(folio(page, decoder))
                page_texts.append(text)
                page_records.append((pdf_path.name, n, folios[-1], source_hash,
                                     'pdf-native-text-reviewed-encoding' if review else 'pdf-native-text', text))
                (output/f'page-{n}.txt').write_text(text, encoding='utf-8')
            except ValueError as exc:
                # A rejected page is a hard association boundary. Never join
                # course text across an unreadable page or guess missing glyphs.
                rejected.append({'pdf_page': n, 'reason': str(exc)})
                pages.append([{'text':'CHAPTER UNREADABLE SOURCE PAGE', 'bbox':[0,0,1,1], 'pdf_page':n}])
                folios.append(None)
                page_texts.append(None)
                # Render selected evidence only. Rendering every scanned appendix
                # needlessly exhausts memory before a source-only catalog exists.
                if len(rejected)<=render_rejected_pages:
                    try:
                        page.get_pixmap(dpi=150).save(output/f'rejected-page-{n}.png')
                    except fitz.mupdf.FzErrorBase as error:
                        render_failures.append({'pdf_page':n,'reason':str(error)})
                    finally:
                        fitz.TOOLS.store_shrink(100)
            save(output/'source-catalog-checkpoint.json', {'source_sha256':source_hash,
                 'code_sha256':sha(Path(__file__)),'processed_source_pages':n,
                 'accepted_native_pages':len(page_records),'rejected_pages':rejected,
                 'total_source_pages':len(pdf),'status':'generating; not activation-ready'})
        all_rows = [r for rows in pages for r in rows]
        headers = catalog_headers(all_rows)
        for n, page in enumerate(pdf, 1):
            text = page_texts[n-1]
            if text is None:
                continue
            for row in pages[n-1]:
                if re.search(r'เกณฑ์การสำเร็จการศึกษา|ระเบียบ.*การศึกษา|ข้อบังคับ.*การศึกษา', row['text']):
                    rules.append((pdf_path.name, n, folios[n-1], row['text'], text,
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
                    fragments.append({'pdf_page':number,'printed_page':folios[number-1],
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
                records.append({**anchor, 'pdf_page': n, 'printed_page': folios[n-1],
                                'prerequisite_literal': '\n'.join(pre),
                                'description_th': th, 'description_en': en,
                                'fragments': fragments,
                                'association_status': 'unreviewed native candidate'})
                page.get_pixmap(dpi=150).save(output/f'catalog-page-{n}.png')
                fitz.TOOLS.store_shrink(100)
    database = output/'source.sqlite'
    with closing(sqlite3.connect(database)) as db, db:
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
             'decoder_sha256':sha(Path(__file__).with_name('source_native.py')),
             'font_review_sha256':sha(font_review) if font_review else None,
             'renderer_version': fitz.VersionBind, 'source_pages': len(pages),
             'accepted_native_pages':len(page_records), 'rejected_pages':rejected,
             'evidence_render_failures':render_failures,'render_rejected_pages':render_rejected_pages,
             'catalog_candidates': len(records), 'unique_candidate_codes': len({r['code'] for r in records}),
             'rule_heading_candidates': len(rules), 'unresolved_headers': diagnostics,
             'domains': {'academic_plan': False, 'source_document_corpus': not rejected,
                         'catalog_complete': False, 'program_rules_complete': False},
             'limitations': ['literal native text; visual fidelity not certified for every page',
                             'native image-body gaps and unreviewed glyph pages excluded; image OCR/review still required',
                             'catalog candidates require boundary/coverage review',
                             'wrapped prerequisites not normalized; no logical edges or rights inferred',
                             'rule headings may include TOC; normative scope not validated'],
             'database_sha256': sha(database), 'seconds': round(time.perf_counter()-started, 3)}
    save(output/'source-catalog.json', state)
    save(output/'source-catalog-checkpoint.json', {**state,'status':'complete diagnostic; not activation-ready'})
    return state


def ingest(source, target):
    """Copy only freshly extracted literal tables into the staged database."""
    with closing(sqlite3.connect(target)) as db, db:
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
    p.add_argument('--font-review', type=Path)
    p.add_argument('--coverage-only',action='store_true',help='Report native/OCR page readiness without creating or ingesting SQLite')
    p.add_argument('--render-rejected-pages',type=int,default=0,
                   help='Render at most this many rejected pages for review; originals and page locators are always preserved')
    args = p.parse_args()
    if args.coverage_only:
        if args.staged_database:
            p.error('--coverage-only cannot ingest a database')
        state=scan_coverage(args.pdf,args.output,args.font_review)
        print(json.dumps({k:v for k,v in state.items() if k!='pages'},ensure_ascii=False))
        return
    if args.render_rejected_pages<0:
        p.error('--render-rejected-pages must be nonnegative')
    state = extract(args.pdf, args.output, args.font_review,args.render_rejected_pages)
    if args.staged_database:
        ingest(args.output/'source.sqlite', args.staged_database)
    print(json.dumps({k: v for k, v in state.items() if k not in {'unresolved_headers'}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
