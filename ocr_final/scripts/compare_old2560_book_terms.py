"""Read-only comparison against manually reviewed rendered academic-plan pages.

The ledger is separate from measured/frozen OCR. Counts and credit patterns are
independent book observations; no full name/prerequisite accuracy is inferred.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
P = '3(2-2-5)'
T = '3(3-0-6)'
A = '3(3-0-6) หรือ 3(2-2-5)'


def entries(codes, practical=(), alternatives=(), special=None):
    special = special or {}
    return [{'code': code, 'credits_raw': special.get(code, A if code in alternatives else P if code in practical else T)}
            for code in codes.split()]


def book_ledger():
    # These tuples were transcribed from rendered pages, not exported from a DB.
    dsba = [
        (1, 1, 18, entries('06026100 06026104 90101007 90201001 90401013 90101xxx', ('06026100', '06026104'))),
        (1, 2, 18, entries('06026101 06026105 06026106 06026107 90201002 90401012', ('06026106',))),
        (2, 1, 19, entries('06026102 06026103 06026108 06026109 06026110 06026111 90201012', ('06026109',), special={'06026111':'1(0-2-1)'})),
        (2, 2, 19, entries('06026112 06026113 06026114 06026115 06026116 06026117 90201026', ('06026114','06026115','06026116'), special={'06026113':'1(0-2-1)'})),
        (3, 1, 18, entries('06026118 06026119 06026120 06026121 06026122 90304004', ('06026120','06026121','06026122'))),
        (3, 2, 16, entries('06026123 06026124 06026125 06026126 06026127 060261xx', ('06026124','06026125'), ('060261xx',), {'06026123':'1(1-0-2)','06026127':'3(0-9-0)'})),
    ]
    it = [
        (1, 1, 18, entries('06016301 06016314 06016319 90101007 90201001 90401013', ('06016301','06016314','06016319'))),
        (1, 2, 18, entries('06016302 06016311 06016315 06016320 90201002 90201012', ('06016311','06016315'))),
        (2, 1, 18, entries('06016303 06016305 06016312 06016313 06016316 06016317', ('06016312','06016317'))),
        (2, 2, 18, entries('06016304 06016306 06016308 90201026 06016321 06016322 06016331 06016332 06016341 06016342', ('06016308','06016322','06016331','06016341','06016342'))),
        (3, 1, 18, entries('06016309 06016310 90304004 06016323 06016324 06016325 06016333 06016334 06016335 06016343 06016344 06016345', ('06016323','06016325','06016333','06016335','06016344','06016345'))),
        (3, 2, 16, entries('06016307 06016318 060163xx 06016326 06016327 06016328 06016336 06016337 06016338 06016346 06016347 06016348', ('06016327','06016328','06016336','06016346','06016347','06016348'), ('060163xx',), {'06016318':'1(1-0-2)'})),
    ]
    bit = [
        (1, 1, 18, entries('06036001 06036021 06036027 06036081 06036083 06036085', ('06036001','06036021'))),
        (1, 2, 18, entries('06036002 06036004 06036022 06036082 06036084 06036090', ('06036022',))),
        (2, 1, 18, entries('06036003 06036005 06036023 06036028 06036087 06036089')),
        (2, 2, 18, entries('06036006 06036008 06036011 06036012 06036013 06036024', ('06036011','06036013'))),
        (3, 1, 18, entries('06036007 06036009 06036010 06036014 06036025 060360xx', ('06036010',), ('060360xx',))),
        (3, 2, 18, entries('06036015 06036016 06036017 06036018 06036026 060360xx', ('06036015','06036026'), ('060360xx',))),
    ]
    profiles = []
    for program, common, total, source in [('dsba',dsba,126,'DSBA-60.pdf'),('it',it,130,'IT-60.pdf'),('bit',bit,126,'BIT-60.pdf')]:
        for plan in ('coop','no_coop'):
            terms = list(common)
            if program == 'dsba':
                if plan == 'coop':
                    terms += [(4,1,12,entries('06026128 xxxxxxxx xxxxxxxx 90xxxxxx', special={'06026128':'3(0-9-0)'})),
                              (4,2,6,entries('06026130 06026131',special={'06026130':'6(0-35-0)','06026131':'6(0-35-0)'}))]
                    pages=[30,30,31,32,32,33,33,34]
                else:
                    terms += [(3,3,3,entries('06026129',special={'06026129':'3(0-35-0)'})),
                              (4,1,9,entries('06026128 060261xx 90xxxxxx',alternatives=('060261xx',),special={'06026128':'3(0-9-0)'})),
                              (4,2,6,entries('xxxxxxxx 90xxxxxx'))]
                    pages=[25,26,26,27,27,28,28,29,29]
            elif program == 'it':
                if plan == 'coop':
                    codes='06016393 06016394 06016395 06016396 06016397 06016398'
                    terms += [(4,1,6,entries(codes,special={c:'6(0-36-0)' for c in codes.split()})),
                              (4,2,18,entries('90401011 060163xx 90xxxxxx 90xxxxxx xxxxxxxx xxxxxxxx', alternatives=('060163xx',)))]
                    pages=[34,35,35,36,37,38,39,40]
                else:
                    terms += [(4,1,18,entries('060163xx 90xxxxxx 90xxxxxx xxxxxxxx xxxxxxxx 06016329 06016339 06016349', alternatives=('060163xx',),special={c:'3(0-9-0)' for c in ('06016329','06016339','06016349')})),
                              (4,2,6,entries('90401011 06016330 06016340 06016350',special={c:'3(0-9-0)' for c in ('06016330','06016340','06016350')}))]
                    pages=[27,28,28,29,30,31,32,33]
            else:
                if plan == 'coop':
                    terms += [(4,1,6,entries('06036046 06036047',special={'06036046':'6(0-35-0)','06036047':'6(0-35-0)'})),
                              (4,2,12,entries('06036086 06036088 xxxxxxxx xxxxxxxx'))]
                    pages=[27,27,28,28,29,29,30,30]
                else:
                    terms += [(4,1,9,entries('06036019 06036086 xxxxxxx',special={'06036019':'3(0-9-0)'})),
                              (4,2,9,entries('06036020 06036088 xxxxxxx',special={'06036020':'3(0-9-0)'}))]
                    pages=[23,23,24,24,25,25,26,26]
            profiles.append({'profile':f'{program}_2560_{plan}','source_file':source,'printed_total':total,
                             'terms':[{'year':y,'semester':s,'printed_credits':credit,'pdf_page':page,'printed_page':page-5,
                                       'expected_options':rows,'full_name_fields_verified':None,'all_prerequisites_verified':None}
                                      for (y,s,credit,rows),page in zip(terms,pages)]})
    return profiles


def canonical(value):
    return re.sub(r'\s+', '', str(value or '')).upper()


def compare_term(expected, observed):
    errors=[]
    expected_pairs=Counter((canonical(r['code']),canonical(r['credits_raw'])) for r in expected['expected_options'])
    # raw_code may be the combined printed cell on a split alternative: code is
    # the specific choice then, whereas wildcard raw_code is the printed slot.
    actual_pairs=Counter((canonical(r['code'] if re.search(r'\d{8}.*\d{8}',str(r.get('raw_code') or '')) else r.get('raw_code') or r['code']),canonical(r['credits_raw'])) for r in observed)
    if expected_pairs != actual_pairs:
        errors.append({'kind':'course/credit-pattern mismatch','missing':list((expected_pairs-actual_pairs).elements()),'extra':list((actual_pairs-expected_pairs).elements())})
    groups={}
    total=0
    for row in observed:
        if expected.get('source_file') and row.get('source_file') != expected['source_file']:
            errors.append({'kind':'source version mismatch','code':row['code'],'source_file':row.get('source_file')})
        if row['alt_group']:
            groups.setdefault(row['alt_group'],set()).add(row['credits'])
        else: total+=row['credits']
        if row['page_number']!=expected['pdf_page'] or row['printed_page_number']!=expected['printed_page']:
            errors.append({'kind':'page mismatch','code':row['code'],'pdf':row['page_number'],'printed':row['printed_page_number']})
    for group, credits in groups.items():
        if len(credits)!=1: errors.append({'kind':'unequal alternative credits','group':group})
        total+=min(credits)
    if total!=expected['printed_credits']: errors.append({'kind':'term total mismatch','expected':expected['printed_credits'],'actual':total})
    return {'year':expected['year'],'semester':expected['semester'],'pdf_page':expected['pdf_page'],
            'printed_page':expected['printed_page'],'expected_options':len(expected['expected_options']),
            'stored_options':len(observed),'printed_credits':expected['printed_credits'],'db_counted_credits':total,
            'passed':not errors,'errors':errors}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    renders=json.loads((REPO/'docs/results/old2560_plan_render_checkpoint.json').read_text())['pages']
    ledger=book_ledger()
    results=[]
    for profile in ledger:
        path=args.app_root/'work'/('lab8b_'+profile['profile'])/'curriculum.db'
        with sqlite3.connect(f'file:{path.as_posix()}?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            terms=[]
            for term in profile['terms']:
                image=next(r for r in renders if r['source']==profile['source_file'] and r['pdf_page']==term['pdf_page'])
                if hashlib.sha256((REPO/image['image']).read_bytes()).hexdigest()!=image['image_sha256']:raise ValueError('Reviewed image changed')
                if hashlib.sha256((args.app_root/'data/input'/profile['source_file']).read_bytes()).hexdigest()!=image['source_sha256']:raise ValueError('Source PDF changed')
                term.update(source_file=profile['source_file'],source_sha256=image['source_sha256'],image=image['image'],image_sha256=image['image_sha256'],review_status='manually_inspected_rendered_image')
                rows=[dict(r) for r in db.execute('SELECT code,raw_code,credits,credits_raw,alt_group,source_file,page_number,printed_page_number FROM v_plan WHERE year=? AND semester=?',(term['year'],term['semester']))]
                terms.append(compare_term(term,rows))
            actual=set(tuple(r) for r in db.execute('SELECT DISTINCT year,semester FROM v_plan'))
            expected={(t['year'],t['semester']) for t in profile['terms']}
            counted=sum(t['db_counted_credits'] for t in terms)
            declared=db.execute('SELECT total_credits FROM program').fetchone()[0]
        results.append({'profile':profile['profile'],'db_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'terms':terms,
                        'printed_total':profile['printed_total'],'db_total':counted,'declared_total':declared,
                        'unexpected_terms':sorted(actual-expected),
                        'passed':all(t['passed'] for t in terms) and actual==expected and counted==declared==profile['printed_total']})
    output={'scope':'All academic-plan code/options, credit/hour patterns, semester totals and printed folios; NOT full names/prerequisites or book-wide completeness',
            'ledger':ledger,'results':results}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for r in results:print(r['profile'],'PASS' if r['passed'] else 'FAIL',sum(t['passed'] for t in r['terms']),'/',len(r['terms']),'terms',r['db_total'],'/',r['printed_total'],'credits')
    raise SystemExit(int(any(not r['passed'] for r in results)))


if __name__=='__main__':main()
