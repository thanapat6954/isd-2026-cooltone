"""Render SQLite-retrieved study-plan relationships without factual supplementation."""
from collections import OrderedDict
from copy import deepcopy
import re

PLAN_LABELS = {'coop': 'แผนสหกิจศึกษา', 'no-coop': 'แผนไม่สหกิจศึกษา'}


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


def build_study_plan(rows, question, evidence=None, *, required_only=False):
    """Only database-loaded evidence supplies curriculum facts and relationships."""
    evidence = evidence if isinstance(evidence, dict) else {}
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
        review = evidence.get(source.get('curriculum_name'), {})
        term = next((t for t in review.get('terms', []) if t['source_file'] == source_file
                     and str(t['version']) == str(version) and t['year'] == year
                     and t['semester'] == semester and t['plan'] == plan
                     and t['program_id'] == source.get('program_id')), None)
        notes, sections = [], OrderedDict()
        tracks = review.get('tracks', {}).get(term['id'], []) if term else []
        requested = [t['track_id'] for t in tracks if any(re.sub(r'\s+', '', alias).casefold()
                      in compact_question for alias in [t['label'], *t.get('aliases', [])])]
        if term:
            notes.append(term['note'])
            expected = {pid for pid, item in review.get('items', {}).items() if item['term_id'] == term['id']}
            missing = sorted(expected - {r.get('id') for r in term_rows})
            if missing and not required_only:
                notes.append('หลักฐานรายวิชาที่ค้นได้ยังไม่ครบตามตารางที่ตรวจ: plan_item ' + ', '.join(map(str, missing)))
        for row in term_rows:
            item = review.get('items', {}).get(row.get('id'), {})
            eligible = bool(term and item.get('term_id') == term['id'] and row.get('page_number') in [p['pdf_page'] for p in term['pages']])
            members = review.get('members', {}).get(row.get('id'), []) if eligible else []
            memberships = [m['track_id'] for m in members]
            if eligible:
                row['_study_review'] = {'source_sha256': term['source_sha256'], 'method': term['review_method'], 'data_source': 'SQLite'}
            destinations = memberships or [item.get('section_label') if eligible and item.get('section_label') else _elective_kind(row) or ('รายวิชาร่วมทุกกลุ่ม' if eligible and item.get('shared') else 'รายวิชาตามข้อมูลที่นำเข้า')]
            if memberships and requested:
                destinations = [m for m in memberships if m in requested]
            if not destinations:
                continue
            row['_study_context'] = {'track_ids': memberships, 'plan': plan,
                                     'category': _elective_kind(row), 'reviewed': eligible}
            annotated.append(row)
            for destination in destinations:
                label = next((t['label'] for t in tracks if t['track_id'] == destination), destination)
                section = sections.setdefault(destination, {'title': label, 'track_id': destination if memberships else None, 'kind': 'track' if destination in [t['track_id'] for t in tracks] else 'courses', 'rows': []})
                display = deepcopy(row)
                member = next((m for m in members if m['track_id'] == destination), {})
                if member.get('display_name_th'):
                    display['name_th'] = member['display_name_th']
                    display['name_en'] = member.get('display_name_en')
                identity_of = lambda r: r.get('id') or (r.get('code'), r.get('alt_group'), r.get('name_th'), r.get('name_en'), r.get('raw_code'))
                identity = identity_of(display)
                if not any(identity_of(r) == identity for r in section['rows']):
                    section['rows'].append(display)
        program = str(source.get('program_id') or source.get('curriculum_name') or 'หลักสูตร').split('-')[0]
        cards.append({'program': program, 'version': version, 'year': year, 'semester': semester,
                      'plan': plan, 'plan_label': PLAN_LABELS.get(plan, 'แผนตามข้อมูลที่นำเข้า'),
                      'sections': list(sections.values()), 'notes': list(dict.fromkeys(notes)),
                      'reviewed': bool(term), 'printed_total': term['printed_total'] if term and not required_only and not missing else None})
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
