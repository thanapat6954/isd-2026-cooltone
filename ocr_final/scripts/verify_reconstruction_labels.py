"""Read-only source-label checks on rebuilt outputs; never edit expected labels."""
import argparse
import json
import re
import sqlite3
from contextlib import closing
from collections import Counter
from pathlib import Path

REQUIRED = {'raw_code','is_placeholder','code_pattern','elective_type','alternative_index','printed_page_number'}


def normalized(value):
    return re.sub(r'\s+','',str(value or '')).upper()


def check_options(expected, observed):
    """Check reviewed fields and repeated elective slots, not just presence."""
    missing=[]
    fixed=Counter((normalized(r['code']),normalized(r['credits_raw'])) for r in expected if not r.get('alternative_group'))
    for (code,raw),count in fixed.items():
        found=sum(code in re.findall(r'[0-9X]{4,}',normalized(r['raw_code'] or r['code'])) and normalized(r['credits_raw'])==raw for r in observed)
        if found<count:
            missing.append({'code':code,'kind':'missing reviewed row multiplicity','expected_n':count,'actual_n':found})
    for row in expected:
        code=normalized(row['code'])
        matches=[r for r in observed if code in re.findall(r'[0-9X]{4,}',normalized(r['raw_code'] or r['code']))]
        if not any(normalized(r['credits_raw'])==normalized(row['credits_raw']) for r in matches):
            missing.append({'code':row['code'],'expected_credits_raw':row['credits_raw'],'kind':'missing code/hour-pattern support'})
        for field in ('name_th','name_en'):
            if field in row and not any(normalized(r.get(field))==normalized(row[field]) for r in matches):
                missing.append({'code':row['code'],'field':field,'expected':row[field],'observed':[r.get(field) for r in matches],'kind':'reviewed name mismatch'})
    return missing


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--app-root',type=Path,required=True)
    p.add_argument('--labels-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    results=[]
    for path in sorted(a.app_root.glob('work/lab8b_*/curriculum.db')):
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            program=dict(db.execute('SELECT * FROM program').fetchone())
            identity={'program':program['program_id'].split('-')[0],'version':program['curriculum_version'],'plan':program['plan']}
            record={'identity':identity,'database':str(path),'integrity':db.execute('PRAGMA integrity_check').fetchone()[0],
                    'missing_fidelity_columns':sorted(REQUIRED-{r[1] for r in db.execute('PRAGMA table_info(plan_item)')}),'terms':[]}
            labels=a.labels_root/f'{identity["program"]}-{identity["version"]}'/f'{identity["plan"]}-terms.json'
            data=json.loads(labels.read_text(encoding='utf-8')) if labels.exists() else None
            record['source_label_status']='partial rendered-page labels' if data else 'n/a; independent semester labels unavailable'
            if data:
                for term in data['terms']:
                    observed=[dict(r) for r in db.execute('''SELECT p.code,p.raw_code,
                        COALESCE(p.credits_raw, CASE WHEN c.credits IS NOT NULL AND c.lecture_h IS NOT NULL AND c.lab_h IS NOT NULL AND c.self_h IS NOT NULL
                          THEN CAST(c.credits AS TEXT)||'('||CAST(c.lecture_h AS TEXT)||'-'||CAST(c.lab_h AS TEXT)||'-'||CAST(c.self_h AS TEXT)||')' END) AS credits_raw,
                        COALESCE(p.name_th,c.name_th) AS name_th,COALESCE(p.name_en,c.name_en) AS name_en,p.page_number,p.printed_page_number
                        FROM plan_item p LEFT JOIN course c ON c.code=p.code WHERE p.year=? AND p.semester=?''',(term['year'],term['semester']))]
                    total=db.execute('SELECT credits FROM v_semester_credits WHERE year=? AND semester=?',(term['year'],term['semester'])).fetchone()
                    missing=check_options(term['expected_options'],observed)
                    record['terms'].append({'year':term['year'],'semester':term['semester'],'pdf_page':term['pdf_page'],
                        'printed_page':term['printed_page'],'expected_total':term['printed_credits'],'actual_total':total[0] if total else None,
                        'credit_total_passed':bool(total and total[0]==term['printed_credits']), 'field_mismatches':missing})
            results.append(record)
    output={'scope':'read-only reconstructed schema and partial independent codes/hour-pattern/semester-total checks; NOT all names/prerequisites/graduation',
            'profiles':results,'summary':{'profiles':len(results),'integrity_passed':sum(r['integrity']=='ok' for r in results),
                'terms_n':sum(len(r['terms']) for r in results),'term_totals_passed':sum(t['credit_total_passed'] for r in results for t in r['terms']),
                'field_mismatches':sum(len(t['field_mismatches']) for r in results for t in r['terms'])}}
    a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(output['summary']))
    return int(output['summary']['field_mismatches']>0 or output['summary']['terms_n']!=output['summary']['term_totals_passed'])


if __name__=='__main__':raise SystemExit(main())
