"""Conservative DB-relative review of the existing exposed development matrix."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab10_fastapi.curriculum_app.query_planner import normalize_course_name

OUTCOMES = ('substantive_correct', 'justified_partial_gap', 'clarification',
            'incorrect_irrelevant', 'technical_failure', 'unreviewed')


def inspect(case):
    answer = str(case.get('body', {}).get('answer') or '')
    trace = case.get('trace') or case.get('body') or {}
    queries = trace.get('queries') or []
    facts = {'courses': 0, 'slots': 0, 'tracks': 0, 'rules': 0, 'names': set(), 'edges': [], 'common_codes': set()}
    sets = defaultdict(dict)
    replay = []
    for query in queries:
        path = Path(query.get('database_path', ''))
        if not path.is_file():
            return None, ['isolated database unavailable; cannot replay historical evidence']
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
            db.execute('PRAGMA query_only=ON')
            db.create_function('normalize_course_name', 1, lambda value: normalize_course_name(str(value or '')))
            db.row_factory = sqlite3.Row
            try:
                rows = [dict(r) for r in db.execute(query['sql'], query.get('parameters', []))]
                replay.append({'sql': query['sql'], 'parameters': query.get('parameters', []), 'rows_n': len(rows)})
            except sqlite3.Error as exc:
                return None, [str(exc)]
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
            if 'course' not in tables:
                continue
            names = [dict(r) for r in db.execute('SELECT code,name_th,name_en FROM course')]
            facts['courses'] += len(names)
            facts['names'].update(str(r['name_th']) for r in names if r['name_th'])
            key = (str(query.get('program_id') or '').split('-')[0], query.get('plan'))
            sets[key][query.get('curriculum_version')] = {r['code'] for r in names}
            if 'plan_item' in tables:
                facts['slots'] += db.execute("SELECT COUNT(*) FROM plan_item WHERE code LIKE 'ELEC-%' OR LOWER(code) LIKE '%x%'").fetchone()[0]
            if 'study_track' in tables:
                facts['tracks'] += db.execute('SELECT COUNT(*) FROM study_track').fetchone()[0]
            if 'program_requirement' in tables:
                facts['rules'] += db.execute('SELECT COUNT(*) FROM program_requirement').fetchone()[0]
            if 'prerequisite' in tables:
                facts['edges'].extend(dict(r) for r in db.execute('SELECT code,requires,kind FROM prerequisite'))
    for versions in sets.values():
        if len(versions) > 1:
            facts['common_codes'].update(set.intersection(*versions.values()))
    facts['common_codes'] = sorted(facts['common_codes'])
    facts['names'] = sorted(facts['names'])
    facts['replay'] = replay
    facts['answer'] = answer
    return facts, []


def review(case, historical=False):
    if case.get('status') != 200:
        return 'technical_failure', ['HTTP/transport failure'], None
    facts, errors = inspect(case)
    if errors:
        return 'unreviewed', errors, facts
    answer = facts['answer']
    category = case['category']
    trace = case.get('trace') or case.get('body') or {}
    rows = trace.get('rows', [])
    intent = trace.get('intent')
    if isinstance(intent, dict):
        intent = intent.get('intent')
    if intent == 'program_info' and category not in ():
        return 'incorrect_irrelevant', ['program identity does not answer the requested reasoning task'], facts
    if category == 'prerequisite_logic':
        if intent == 'course_search':
            return 'incorrect_irrelevant', ['function word treated as course name'], facts
        if 'AND/OR' in answer and ('ไม่หมายถึงไม่มี' in answer or 'ไม่อนุมานว่าไม่มี' in answer):
            return 'justified_partial_gap', ['logical relationship and complete prerequisite coverage unavailable; no permission inferred'], facts
        return 'incorrect_irrelevant', ['does not answer prerequisite multiplicity/logic or explain that specific gap'], facts
    if category == 'multi_condition' and intent != 'course_list':
        return 'incorrect_irrelevant', ['aggregate/other response replaces requested filtered course list'], facts
    if category == 'elective_alternatives':
        if not rows and facts['slots']:
            return 'incorrect_irrelevant', ['elective slot evidence exists but retrieval/answer omits it'], facts
        if rows and 'หรือ' in answer and not historical:
            if len(rows) == facts['slots'] and all(r.get('name_th') and r.get('credits') is not None and r.get('printed_page_number') is not None for r in rows):
                return 'substantive_correct', ['all DB slots retrieved with names/credits/paired pages; stored alternative strings preserved'], facts
            return 'justified_partial_gap', ['slot facts restored; missing names/folios/raw alternative metadata or incomplete row coverage remains'], facts
    if category == 'shared_specialization' and facts['tracks'] and not trace.get('study_plan'):
        return 'incorrect_irrelevant', ['recorded track evidence not presented'], facts
    if category == 'shared_specialization' and not historical and trace.get('study_plan'):
        cards = trace['study_plan']['cards']
        if all(card['reviewed'] for card in cards) and facts['tracks'] and all(r.get('printed_page_number') is not None for r in rows):
            return 'substantive_correct', ['reviewed SQLite track/shared grouping rendered without summing exclusive groups; paired source pages available'], facts
        if 'ไม่ยืนยันว่าทุกกลุ่ม' in answer:
            return 'justified_partial_gap', ['recorded plan rows shown; missing group relationships explicitly disclosed'], facts
    if category == 'plans_comparison' and not historical and trace.get('study_plan'):
        cards = trace['study_plan']['cards']
        if len({c['plan'] for c in cards}) > 1 and all(c['reviewed'] and c.get('printed_total') is not None for c in cards):
            return 'substantive_correct', ['both selected plans grouped by semester with SQLite-reviewed totals; alternatives not summed'], facts
        if 'แผนเดียว' in answer:
            return 'justified_partial_gap', ['second plan unavailable; one-plan facts disclosed as incomplete comparison'], facts
    if category == 'name_paraphrase' and 'โปรดระบุรหัสวิชา' in answer:
        codes = {str(r.get('code')) for r in rows if r.get('code')}
        if len(codes) > 1 and all(code in answer for code in codes):
            return 'clarification', ['multiple retrieved DB candidates listed; no arbitrary course chosen'], facts
    if category == 'version_comparison' and not facts['common_codes'] and 'รหัสวิชาตรงกัน' in answer:
        return 'justified_partial_gap', ['full selected course catalogs have no common codes; AI-old/legacy version evidence unavailable'], facts
    if category == 'graduation_partial' and facts['rules'] and 'ยังยืนยันไม่ได้' in answer:
        rule_rows = [r for r in rows if r.get('rule_text')]
        if rule_rows and all(r['rule_text'] in answer for r in rule_rows):
            return 'justified_partial_gap', ['retrieved rules rendered; complete eligibility not asserted; citation folios may remain unknown'], facts
    if category == 'misleading_assumption' and not rows and 'ยังสรุปไม่ได้' in answer:
        return 'justified_partial_gap', ['universal no-prerequisite claim not confirmed; imported edge coverage is incomplete'], facts
    if category == 'unsupported_description' and rows:
        return 'incorrect_irrelevant', ['course/program facts do not establish future exam topics or teaching language'], facts
    return 'unreviewed', ['requires substantive completeness and paired-citation review; HTTP200 is not a pass'], facts


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--rerun', type=Path, action='append', default=[])
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    baseline = json.loads(a.baseline.read_text(encoding='utf-8'))
    current = {(c['profile'], c['category'], c['route']): (c, True, str(a.baseline)) for c in baseline['cases']}
    historical = []
    for c in baseline['cases']:
        outcome, reasons, facts = review(c, historical=True)
        historical.append({'id': c['id'], 'category': c['category'], 'profile': c['profile'], 'route': c['route'], 'outcome': outcome, 'reasons': reasons})
    for path in a.rerun:
        for c in json.loads(path.read_text(encoding='utf-8'))['cases']:
            current[(c['profile'], c['category'], c['route'])] = (c, False, str(path))
    reviewed, counts = [], defaultdict(Counter)
    for c, old, path in current.values():
        outcome, reasons, facts = review(c, historical=old)
        counts[c['category']][outcome] += 1
        reviewed.append({'profile': c['profile'], 'category': c['category'], 'route': c['route'], 'outcome': outcome,
            'historical_only': old, 'raw_evidence': path, 'reasons': reasons, 'case': c, 'db_review': facts})
    a.output.mkdir(parents=True, exist_ok=True)
    result = {'scope': 'conservative selected-SQLite development review; not held-out/source-book accuracy',
        'historical_reviews': historical, 'cases': reviewed, 'counts': {k: dict(v) for k,v in counts.items()}}
    with (a.output/'review.json').open('w', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    lines = ['# ผลตรวจ diverse development', '', 'เป็นการตรวจเทียบ SQLite ของชุด development เดิม ไม่ใช่ held-out หรือความถูกต้องทั้งเล่ม สถานะ unreviewed ไม่ใช่ผ่าน รายการที่ยังไม่มีผลใหม่เก็บเป็น historical_only.', '',
        '| หมวด | ตอบถูกครบ | ตอบบางส่วน/ข้อมูลขาด | ขอให้ระบุ | ผิด/ไม่เกี่ยวข้อง | ขัดข้อง | ยังไม่ตรวจครบ |', '|---|---:|---:|---:|---:|---:|---:|']
    for category, values in sorted(counts.items()):
        lines.append('| '+category+' | '+' | '.join(str(values[v]) for v in OUTCOMES)+' |')
    lines += ['', 'แต่ละช่องนับ HTTP requests; 14 wordings /196 profile-question cases /392 requests ไม่ใช่ 392 reasoning tasks. ดูคำตอบจริง, SQL, rows และเกณฑ์รายกรณีใน [review.json](review.json). ไม่สรุป accuracy รวมจากตารางนี้.']
    (a.output/'review.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps(result['counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
