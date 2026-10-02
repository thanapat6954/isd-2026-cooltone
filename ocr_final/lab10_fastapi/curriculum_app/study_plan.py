"""Source-reviewed relationships, independent of plan and frozen OCR inputs."""
from collections import OrderedDict
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

PLAN_LABELS = {'coop': 'แผนสหกิจศึกษา', 'no-coop': 'แผนไม่สหกิจศึกษา'}


def review_fingerprint(root):
    path = Path(root) / 'data/ground_truth/study_plan_relationships.json'
    sources = Path(root) / 'data/input'
    return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size)
                 for p in [path, *sorted(sources.glob('*.pdf'))] if p.is_file())


@lru_cache(maxsize=24)
def _hash(path, modified, size):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _verified(root, review, source):
    path = Path(root) / 'data/input' / source
    return (path.is_file() and _hash(str(path), path.stat().st_mtime_ns, path.stat().st_size)
            == review.get('sources', {}).get(source))


def _pattern(row):
    for key in ('code_pattern', 'raw_code', 'code'):
        value = str(row.get(key) or '')
        match = re.search(r'[0-9xX]{6,8}', value)
        if match and re.search('[xX]', match[0]):
            return match[0].lower()
    return ''


def _elective_kind(row):
    name = str(row.get('name_th') or '')
    kind = str(row.get('elective_type') or '')
    category = str(row.get('category') or '')
    if 'เสรี' in name or 'เสรี' in category or kind in {'free', 'free_elective'}:
        return 'วิชาเลือกเสรี'
    if 'ศึกษาทั่วไป' in name or 'ศึกษาทั่วไป' in category or 'หมวดภาษา' in name or kind == 'general_education':
        return 'วิชาศึกษาทั่วไป'
    if 'มนุษยศาสตร์' in name or kind == 'humanities_elective':
        return 'วิชาเลือกทางมนุษยศาสตร์'
    if 'วิทยาศาสตร์และคณิตศาสตร์' in name or kind == 'science_math_elective':
        return 'วิชาเลือกทางวิทยาศาสตร์และคณิตศาสตร์'
    if row.get('is_placeholder') or _pattern(row) or str(row.get('code', '')).startswith('ELEC-'):
        return 'ข้อกำหนดวิชาเลือก'
    return None


def build_study_plan(rows, question, root, *, required_only=False):
    """Return structured cards and annotated evidence; never write a database."""
    path = Path(root) / 'data/ground_truth/study_plan_relationships.json'
    review = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    groups = OrderedDict()
    for original in rows:
        row = deepcopy(original)
        source = row.get('_source') or {}
        key = (source.get('curriculum_name'), row.get('year'), row.get('semester'))
        groups.setdefault(key, []).append(row)
    cards, annotated = [], []
    compact_question = re.sub(r'\s+', '', question).casefold()
    for (_, year, semester), term_rows in groups.items():
        source = term_rows[0].get('_source') or {}
        plan = source.get('plan') or ''
        version = source.get('curriculum_version')
        source_file = term_rows[0].get('source_file')
        candidate = next((t for t in review.get('terms', []) if t['source_file'] == source_file
                          and str(t['version']) == str(version) and t['year'] == year
                          and t['semester'] == semester and plan in t['pages']), None)
        term = candidate if candidate and _verified(root, review, source_file) else None
        notes, sections = [], OrderedDict()
        tracks = review.get('track_sets', {}).get(term['track_set'], []) if term else []
        requested = [t['id'] for t in tracks if any(re.sub(r'\s+', '', alias).casefold()
                      in compact_question for alias in [t['label'], *t.get('aliases', [])])]
        codes = (term.get('track_codes_by_plan', {}).get(plan) or term.get('track_codes', {})) if term else {}
        if candidate and not term:
            notes.append('ข้อมูลความสัมพันธ์ที่ตรวจไว้ไม่ตรงกับไฟล์ต้นฉบับปัจจุบัน จึงไม่จัดกลุ่มโดยอาศัยข้อมูลนั้น')
        if term:
            notes.append(term['note'])
            expected = set(term.get('shared_codes', [])) | {c for cs in codes.values() for c in cs}
            missing = sorted(expected - {r.get('code') for r in term_rows})
            if missing and not required_only:
                notes.append('ข้อมูลที่นำเข้ายังขาดรายวิชาจากหน้าตาราง: ' + ', '.join(missing))
        for row in term_rows:
            eligible = bool(term and row.get('page_number') in [p[0] for p in term['pages'][plan]])
            memberships = [tid for tid, values in codes.items() if eligible and row.get('code') in values]
            if term:
                if row.get('page_number') not in [p[0] for p in term['pages'][plan]]:
                    notes.append('พบแหล่งอ้างอิงไม่ตรงกับหน้าที่ตรวจ: ' + str(row.get('code')))
                    memberships = []
                else:
                    row.update(term.get('row_facts', {}).get(row.get('code'), {}))
                    row['printed_page_number'] = next(p[1] for p in term['pages'][plan] if p[0] == row.get('page_number'))
                    row['_study_review'] = {'source_sha256': review['sources'][source_file], 'method': review['review_method']}
            pattern = _pattern(row)
            ordinal = re.search(r'(\d+)\s*$', str(row.get('name_th') or '') + ' ' + str(row.get('name_en') or ''))
            if not ordinal:
                ordinal = re.search(r'(\d+)\s*$', str(row.get('name_th') or ''))
            dsba_slot = bool(eligible and pattern == term.get('elective_pattern')
                             and ordinal and int(ordinal[1]) in term.get('elective_ordinals', []))
            if dsba_slot:
                memberships = [t['id'] for t in tracks]
                row['credits_raw'] = term['elective_credits_raw']
                row['requirement_id'] = f'{pattern}-{ordinal[1]}'
            if eligible and pattern in term.get('general_patterns', []):
                row.update(name_th=term['general_name'], credits_raw=term['general_credits_raw'])
            destinations = memberships or [_elective_kind(row) or ('รายวิชาร่วมทุกกลุ่ม' if eligible and row.get('code') in term.get('shared_codes', []) else 'รายวิชาตามข้อมูลที่นำเข้า')]
            if memberships and requested:
                destinations = [m for m in memberships if m in requested]
            if not destinations:
                continue
            row['_study_context'] = {'track_ids': memberships, 'plan': plan,
                                     'category': _elective_kind(row), 'reviewed': eligible}
            annotated.append(row)
            for destination in destinations:
                label = next((t['label'] for t in tracks if t['id'] == destination), destination)
                section = sections.setdefault(destination, {'title': label, 'track_id': destination if memberships else None, 'kind': 'track' if destination in [t['id'] for t in tracks] else 'courses', 'rows': []})
                display = deepcopy(row)
                if dsba_slot:
                    track = next(t for t in tracks if t['id'] == destination)
                    display['name_th'] = track['elective_name'] + ' ' + ordinal[1]
                    display['name_en'] = None
                identity_of = lambda r: r.get('requirement_id') or (r.get('code'), r.get('alt_group'), r.get('name_th'), r.get('name_en'), r.get('raw_code'))
                identity = identity_of(display)
                if not any(identity_of(r) == identity for r in section['rows']):
                    section['rows'].append(display)
        program = str(source.get('program_id') or source.get('curriculum_name') or 'หลักสูตร').split('-')[0]
        cards.append({'program': program, 'version': version, 'year': year, 'semester': semester,
                      'plan': plan, 'plan_label': PLAN_LABELS.get(plan, 'แผนตามข้อมูลที่นำเข้า'),
                      'sections': list(sections.values()), 'notes': list(dict.fromkeys(notes)),
                      'reviewed': bool(term), 'printed_total': (term.get('printed_total_by_plan', {}).get(plan) or term.get('printed_total')) if term and not required_only else None})
    # Only claim equality after comparing actual displayed requirements.
    for card in cards:
        peers = [c for c in cards if c['program'] == card['program'] and c['version'] == card['version']
                 and c['year'] == card['year'] and c['semester'] == card['semester'] and c['plan'] != card['plan']]
        signature = lambda c: [(s['title'], [(r.get('code_pattern') or r.get('raw_code') or r.get('code'), r.get('name_th'), r.get('credits'), r.get('credits_raw')) for r in s['rows']]) for s in c['sections']]
        if card['reviewed'] and any(p['reviewed'] and signature(card) == signature(p) for p in peers):
            card['notes'].append('รายวิชาในภาคการศึกษานี้เหมือนกันระหว่างสองแผน ไม่ได้หมายความว่าทั้งหลักสูตรเหมือนกัน')
    return {'cards': cards}, annotated


def study_plan_text(payload):
    lines = []
    for card in payload['cards']:
        lines.append(f"{card['program']} พ.ศ. {card['version']} — ปี {card['year']} ภาคการศึกษาที่ {card['semester']} — {card['plan_label']}")
        if sum(s['kind'] == 'track' for s in card['sections']) > 1:
            lines.append('กลุ่มหรือแขนงที่แสดงเป็นทางเลือก ไม่ใช่ให้เรียนรายวิชาของทุกกลุ่มพร้อมกัน')
        for section in card['sections']:
            lines.append(section['title'])
            alternatives = [r.get('alt_group') for r in section['rows'] if r.get('alt_group')]
            if any(alternatives.count(group) > 1 for group in alternatives):
                lines.append('รายวิชาที่อยู่ในชุดตัวเลือก “หรือ” เดียวกันให้เลือกเพียงหนึ่งตัวเลือก')
            for row in section['rows']:
                code = row.get('raw_code') or row.get('code_pattern') or row.get('code')
                if str(code).startswith('ELEC-'):
                    code = 'ไม่กำหนดรหัส'
                name = row.get('name_th') or row.get('name_en') or 'เลือกจากรายวิชาในหมวดนี้ (ยังไม่ยืนยันชื่อหมวดจากข้อมูลที่นำเข้า)'
                hours = row.get('credits_raw')
                suffix = f" ({hours})" if hours and 'หรือ' in hours else ''
                lines.append(f"- {code} {name} — {row.get('credits')} หน่วยกิต{suffix}")
        lines.extend(card['notes'])
    return '\n'.join(lines)
