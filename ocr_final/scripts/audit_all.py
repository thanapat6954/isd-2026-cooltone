"""Read-only all-dataset audit with explicit schemas and page-aware evidence.

The supplied Downloads prototype was reviewed, not copied: column guessing,
substring book matching, sampled 400-character proof and SQL-only retrieval
fallback would misclassify this application's normalized/versioned schemas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.config import settings
from lab10_fastapi.curriculum_app.database import inspect_database, open_readonly
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
from lab10_fastapi.curriculum_app.query_planner import QueryPlan

VERSIONS = {'AI.pdf': ('AI', 2566), 'DSBA.pdf': ('DSBA', 2565), 'DSBA-60.pdf': ('DSBA', 2560),
            'IT.pdf': ('IT', 2565), 'IT-60.pdf': ('IT', 2560),
            'BIT-65.pdf': ('BIT', 2565), 'BIT-60.pdf': ('BIT', 2560)}
EXCLUDED = {'venv', '.venv', 'tmp', '.git', 'node_modules', 'backups', 'handoff', 'verification', 'ocr_page_cache'}


class NoGeneration:
    def ollama_generate(self, *args, **kwargs):
        raise RuntimeError('Audit cannot replace unsupported retrieval with model SQL')


def audit_dataset(path, app_root, references):
    info = inspect_database(path, app_root)
    result = {'identity': info.curriculum_name, 'database': info.relative_path,
              'program': info.program, 'schema': info.schema_family, 'checks': [], 'findings': []}
    def finding(check, status, message, row=None):
        row = row or {}
        key = f"{info.relative_path}|{check}|{row.get('code')}|{row.get('source_file')}|{row.get('page_number')}"
        result['findings'].append({'id': hashlib.sha256(key.encode()).hexdigest()[:20],
                                  'check': check, 'status': status, 'severity': 'HIGH',
                                  'message': message, 'code': row.get('code'),
                                  'source_file': row.get('source_file'), 'pdf_page': row.get('page_number')})
    if info.inspection_error or info.schema_family == 'unknown':
        finding('schema', 'FAIL' if info.inspection_error else 'SKIPPED', info.inspection_error or 'ยังไม่รองรับ schema นี้ จึงไม่เดาชื่อคอลัมน์')
        return result
    connection = open_readonly(path)
    try:
        integrity = connection.execute('PRAGMA integrity_check').fetchone()[0]
        result['checks'].append({'check': 'integrity', 'status': 'PASS' if integrity == 'ok' else 'FAIL'})
        if integrity != 'ok':
            finding('integrity', 'FAIL', integrity)
        if info.schema_family == 'lab8b':
            rows = [dict(r) for r in connection.execute('SELECT code, name_th, credits, source_file, page_number FROM course')]
            edges = connection.execute('SELECT COUNT(*) FROM prerequisite').fetchone()[0]
            evidence_count = connection.execute('SELECT COUNT(*) FROM course_prerequisite_evidence').fetchone()[0] if info.has('course_prerequisite_evidence', 'code') else 0
            result['prerequisite_edges'] = edges
            result['verified_prerequisite_courses'] = evidence_count
            if evidence_count < len(rows):
                finding('prerequisite_coverage', 'NEEDS_REVIEW', f'ยืนยันข้อมูลวิชาบังคับก่อนจากเล่มแล้ว {evidence_count}/{len(rows)} รายวิชา; การไม่มี edge ไม่ได้แปลว่าไม่มีวิชาบังคับก่อน')
            if info.has('v_total_credits', 'credits'):
                actual = connection.execute('SELECT credits FROM v_total_credits').fetchone()[0]
                expected = info.program.get('total_credits')
                result['credits'] = {'actual': actual, 'declared': expected}
                if actual != expected:
                    finding('program_credits', 'FAIL', f'นับได้ {actual} หน่วยกิต แต่ข้อมูลหลักสูตรระบุ {expected}')
            required = {'is_placeholder', 'raw_code', 'code_pattern', 'elective_type', 'printed_page_number', 'alternative_index'}
            missing = required - {c.name for c in info.objects['plan_item'].columns}
            if missing:
                finding('fidelity_schema', 'FAIL', 'ยังไม่มีคอลัมน์: ' + ', '.join(sorted(missing)))
        else:
            required = ('course_code', 'course_name_th', 'credits', 'source_file', 'page_number')
            if not info.has('courses', *required):
                finding('legacy_schema', 'SKIPPED', 'คอลัมน์ legacy ไม่ตรงกับ schema ที่รองรับ')
                return result
            rows = [dict(r) for r in connection.execute('SELECT course_code AS code, course_name_th AS name_th, credits, source_file, page_number FROM courses')]
            finding('legacy_identity', 'NEEDS_REVIEW', 'legacy รวมหลายเล่มและหลายบริบท ยังไม่มีข้อมูลปีและฉบับที่ยืนยันจากแหล่งทางการ')
        result['course_rows_checked'] = len(rows)
        assistant = QwenTextToSQL(replace(settings, debug=False), NoGeneration())
        codes = sorted({str(row['code']) for row in rows})
        misses = 0
        for code in codes:
            execution = assistant._execute_one('วิชา ' + code, QueryPlan('course_detail', course_code=code), info)
            if execution.error or not execution.rows:
                misses += 1
                finding('application_retrieval', 'FAIL', execution.error or 'ระบบค้นคืนรายวิชาที่มีในฐานข้อมูลไม่สำเร็จ', {'code': code})
        result['retrieval'] = {'tested': len(codes), 'misses': misses,
                               'scope': 'Actual application SQL validation/execution path; not LLM/API/UI scoring'}
        source_counts = {}
        for row in rows:
            code = str(row['code'])
            if not re.fullmatch(r'\d{8}', code):
                finding('code', 'FAIL', 'รหัสรายวิชาจริงต้องเป็นตัวเลขแปดหลักและเก็บเลขศูนย์นำหน้า', row)
            source = row.get('source_file')
            source_counts[source or 'unknown'] = source_counts.get(source or 'unknown', 0) + 1
            ref = references.get(source)
            if not ref:
                continue
            page = row.get('page_number')
            if page is None or not 1 <= int(page) <= len(ref):
                finding('citation_page', 'FAIL', 'ไม่มีเลขหน้า PDF หรือเลขหน้าอยู่นอกเล่ม', row)
            elif code not in re.sub(r'\s+', '', ref[int(page) - 1]['text']):
                finding('code_on_cited_page', 'NEEDS_REVIEW', 'ไม่พบรหัสใน embedded text ของหน้าอ้างอิง ต้องตรวจภาพหน้านี้; ยังไม่ใช่หลักฐานว่าไม่มีรายวิชา', row)
            mapping = VERSIONS.get(source)
            if mapping and info.program and (mapping[0] != re.sub(r'-(?:no-)?coop$', '', info.program_id) or mapping[1] != info.curriculum_version):
                finding('source_identity', 'FAIL', 'ข้อมูลปีหรือหลักสูตรใน DB ไม่ตรงกับการจับคู่เล่มที่ยืนยันแล้ว', row)
        result['sources'] = source_counts
        for source in source_counts:
            if source not in references:
                finding('reference_coverage', 'SKIPPED', f'ยังไม่มี reference ที่จับคู่ชื่อแหล่งข้อมูลตรงกันสำหรับ {source}', {'source_file': source})
        finding('full_source_fidelity', 'NEEDS_REVIEW', 'การค้นรหัสและหน้าไม่ได้ยืนยันชื่อ หน่วยกิต หมวดวิชา วิชาบังคับก่อน หรือเงื่อนไขจบการศึกษาทั้งเล่มอย่างอิสระ')
        return result
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, default=ROOT / 'reports')
    args = parser.parse_args()
    app_root = args.app_root.resolve()
    manifest = app_root / 'work/ref_text/manifest.json'
    references = {}
    if manifest.exists():
        for item in json.loads(manifest.read_text(encoding='utf-8'))['sources']:
            pdf = app_root / 'data/input' / item['source_file']
            if not pdf.exists():
                continue
            with pdf.open('rb') as handle:
                current_hash = hashlib.file_digest(handle, 'sha256').hexdigest()
            if current_hash != item['sha256']:
                continue
            references[item['source_file']] = [json.loads(line) for line in (manifest.parent / item['pages_file']).read_text(encoding='utf-8').splitlines()]
    paths = sorted(path for path in app_root.rglob('*.db')
                   if not any(part in EXCLUDED or part.startswith('_archive') for part in path.relative_to(app_root).parts))
    args.out.mkdir(parents=True, exist_ok=True)
    previous_path = args.out / 'audit_results.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else None
    datasets = []
    for path in paths:
        try:
            item = audit_dataset(path, app_root, references)
        except Exception as error:
            item = {'identity': path.stem, 'database': path.relative_to(app_root).as_posix(),
                    'checks': [], 'findings': [{'id': hashlib.sha256(str(path).encode()).hexdigest()[:20],
                      'severity': 'HIGH', 'status': 'FAIL', 'message': str(error), 'check': 'dataset_error'}]}
        datasets.append(item)
        tag = re.sub(r'[^A-Za-z0-9-]+', '-', item['identity']) + '-' + hashlib.sha256(item['database'].encode()).hexdigest()[:8]
        lines = [f"# การตรวจ {item['identity']}", '', '## Summary', '',
                 f"ฐานข้อมูล: `{item['database']}`; ตรวจรายวิชา {item.get('course_rows_checked', 0)} แถว",
                 'ผลนี้แยก PASS / FAIL / SKIPPED / NEEDS_REVIEW; ยังไม่ใช่ผลยืนยันหนังสือทั้งเล่ม', '', '## HIGH', '']
        for issue in item['findings']:
            location = f"{issue.get('source_file') or 'n/a'} PDF {issue.get('pdf_page') or 'n/a'} {issue.get('code') or ''}"
            lines.append(f"- {issue['status']} `{issue['check']}` — {location}: {issue['message']}")
        (args.out / f'audit_{tag}.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    coverage = {re.sub(r'-(?:no-)?coop$', '', (item.get('program') or {}).get('program_id', 'legacy')) for item in datasets}
    absent = sorted({'AI', 'DSBA', 'IT', 'BIT', 'legacy'} - coverage)
    new_ids = {issue['id'] for item in datasets for issue in item['findings']}
    old_ids = {issue['id'] for item in (previous or {}).get('datasets', []) for issue in item['findings']}
    result = {'datasets': datasets, 'missing_curricula': absent, 'reference_sources': sorted(references),
              'comparison': {'new_findings': sorted(new_ids-old_ids),
                             'no_longer_detected_not_automatically_fixed': sorted(old_ids-new_ids)},
              'scope': 'Full stored course-row locator and application retrieval checks, no full-book or gold Q&A claim'}
    staging = previous_path.with_suffix('.partial')
    staging.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    staging.replace(previous_path)
    failed = sum(issue['status'] == 'FAIL' for item in datasets for issue in item['findings'])
    incomplete = sum(issue['status'] in {'SKIPPED', 'NEEDS_REVIEW'} for item in datasets for issue in item['findings'])
    print(f'Datasets={len(datasets)}; FAIL={failed}; incomplete={incomplete}; missing curricula={absent}')
    return 1 if failed else (2 if incomplete or absent or not datasets else 0)


if __name__ == '__main__':
    raise SystemExit(main())
