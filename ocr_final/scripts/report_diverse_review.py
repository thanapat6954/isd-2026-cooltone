"""Conservative triage of recorded development answers; never an accuracy score."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sqlite3


def answer(case):
    body = case['body']
    return str(body.get('answer', body.get('detail', body.get('error', ''))))


def triage(case):
    if case['status'] != 200:
        return 'technical_failure'
    if not answer(case).strip():
        return 'empty_answer'
    sql = str(case['body'].get('sql') or (case.get('trace') or {}).get('sql') or '')
    if case['category'] not in {'graduation_partial'} and re.search(r'\bFROM\s+program\b', sql, re.I) and not re.search(r'\b(?:JOIN|UNION)\b', sql, re.I):
        return 'unrelated_program_answer'
    if case['category'] == 'graduation_partial' and 'ยัง' in answer(case):
        return 'partial_rules_disclosed_needs_coverage_review'
    return 'needs_substantive_review'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--after', type=Path, action='append', default=[])
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    raw = json.loads(a.baseline.read_text(encoding='utf-8'))
    cases = raw['cases']
    coverage = []
    for source_path, expected_hash in raw['dependencies'].items():
        if not source_path.endswith('.db'):
            continue
        import hashlib
        path = Path(source_path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError('DB changed since baseline; do not reuse coverage evidence')
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as db:
            db.execute('PRAGMA query_only=ON')
            tables = {r[0] for r in db.execute('SELECT name FROM sqlite_master')}
            item = {'database': str(path), 'source_hash_unchanged': True}
            for label, table, where in [('courses','course',''), ('descriptions','course',"WHERE LENGTH(TRIM(COALESCE(description_th,'')))>0"),
                    ('elective_slots','plan_item','WHERE is_placeholder=1'), ('study_tracks','study_track',''),
                    ('prerequisite_edges','prerequisite',''), ('graduation_rules','program_requirement','')]:
                try:
                    item[label] = db.execute(f'SELECT COUNT(*) FROM {table} {where}').fetchone()[0] if table in tables else None
                except sqlite3.OperationalError:
                    item[label] = None
            coverage.append(item)
    labels = [{'id': c['id'], 'category': c['category'], 'profile': c['profile'], 'route': c['route'],
               'triage': triage(c), 'status': c['status']} for c in cases]
    a.output.with_suffix('.json').write_text(json.dumps({'scope': 'conservative development triage, not independently source-scored accuracy',
        'n': len(labels), 'counts': dict(Counter(c['triage'] for c in labels)), 'db_coverage': coverage,
        'cases': labels}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# การตรวจชุด development 14 หมวด — 2026-10-09', '',
        'ชุดนี้เปิดเผยเพื่อ debugging ไม่ใช่ held-out และไม่ใช้ expected answers เป็น production facts. '
        'การจัดกลุ่มด้านล่างเป็น triage ไม่ใช่การรับรองว่าคำตอบทั้งหมดถูกต้องตามหนังสือ.', '',
        f"Baseline: {raw['coverage']['wordings_n']} wordings / {raw['coverage']['scoped_questions_n']} scoped questions / {raw['coverage']['categories_n']} reasoning categories / {len(cases)} HTTP requests.",
        'คำถามเดียวกันที่ส่งสอง routes ไม่ใช่ reasoning task ใหม่; scope ต่างกันต้องตรวจ DB/version/plan แยก.', '',
        '| หมวด | HTTP requests | HTTP200 | technical failure | unrelated program answer | ยังต้องตรวจเนื้อหา |',
        '|---|---:|---:|---:|---:|---:|']
    for category in dict.fromkeys(c['category'] for c in cases):
        group = [c for c in cases if c['category'] == category]
        counts = Counter(triage(c) for c in group)
        lines.append(f"| `{category}` | {len(group)} | {sum(c['status']==200 for c in group)} | {counts['technical_failure']} | {counts['unrelated_program_answer']} | {counts['needs_substantive_review']+counts['partial_rules_disclosed_needs_coverage_review']} |")
    lines += ['', '## ตัวอย่างก่อน–หลังจากผลจริง', '', 'ไม่ปรับถ้อยคำคำตอบจริงให้ดูดีขึ้น; SQL/rows เต็มอยู่ใน raw JSON. ก่อนหรือหลังที่ไม่มีบันทึกระบุว่า not recorded.']
    after = [c for path in a.after for c in json.loads(path.read_text(encoding='utf-8'))['cases']]
    for category in ('semester_aggregation', 'multi_condition', 'name_paraphrase', 'unsupported_description'):
        key = lambda c: c['profile'] == 'AI-2566-coop' and c['category'] == category and c['route'] == '/api/ask'
        before = next((c for c in cases if key(c)), None)
        current = next((c for c in reversed(after) if key(c)), None)
        lines += ['', f'### `{category}` — AI-2566-coop', '', (before or current)['question']]
        for title, case in [('ก่อนแก้', before), ('หลังแก้', current)]:
            lines += ['', title, '', '```text', answer(case) if case else 'not recorded', '```']
            if case:
                lines += ['', f"HTTP {case['status']}; end-to-end {case['elapsed_ms']:.2f} ms; raw case `{case['id']}`."]
    a.output.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'n':len(labels), 'triage':dict(Counter(c['triage'] for c in labels))}))


if __name__ == '__main__':
    main()
