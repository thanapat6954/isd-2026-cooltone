"""Attach approved term evidence to existing facts without rewriting curriculum rows."""
import argparse
from contextlib import closing
import hashlib
import json
import re
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import open_readonly
from lab10_fastapi.curriculum_app.study_evidence import DDL


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def facts(db):
    """Every non-metadata table is protected, including alternative credit patterns."""
    return {name: [list(r) for r in db.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
            for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            if not name.startswith('study_') and name != 'term_metadata_approval'}


def patch(db, approval, approval_sha):
    db.row_factory = sqlite3.Row
    identities = [dict(r) for r in db.execute('SELECT * FROM program')]
    if len(identities) != 1:
        raise ValueError('Exactly one curriculum/version/plan is required')
    program = identities[0]
    matching = [(key, identity) for key, identity in approval['profile_identity_reviews'].items()
                if identity['program_id'] == program['program_id']]
    if len(matching) != 1:
        raise ValueError('No unique source-reviewed profile identity')
    key, identity = matching[0]
    if program['curriculum_version'] != approval['curriculum_version'] or program['plan'] != identity['plan']:
        raise ValueError('Wrong version/plan')
    terms = [t for t in approval['profiles'][key] if t['year'] in approval['term_metadata_years']]
    if not terms:
        raise ValueError('No approved metadata terms')
    before = facts(db)
    # Existing production databases already have the schema. For a new build,
    # create it before the bounded transaction to avoid executescript commits.
    for statement in DDL.split(';'):
        if statement.strip():
            db.execute(statement)
    db.execute('CREATE TABLE IF NOT EXISTS term_metadata_approval (term_id INTEGER REFERENCES study_term(id), approval_sha256 TEXT, reviewed_on TEXT, PRIMARY KEY(term_id,approval_sha256))')
    changed = []
    for term in terms:
        if term['status'] != 'visually_verified' or term['source_file'] != program['source_file']:
            raise ValueError('Unapproved source term')
        rows = [dict(r) for r in db.execute('SELECT * FROM plan_item WHERE year=? AND semester=? ORDER BY id', (term['year'], term['semester']))]
        if len(rows) != term['row_count'] or len(rows) != len(term['rows']):
            raise ValueError('Approved term count/credits mismatch')
        remaining = {r['id']: r for r in rows}
        pairs = set()
        approved_groups = {}
        memberships = {}
        tracks = term.get('tracks', [])
        track_ids = {track['id'] for track in tracks}
        if len(track_ids) != len(tracks) or any(not track['id'] or not track['label'] for track in tracks):
            raise ValueError('Invalid source-reviewed specialization identities')
        counted = 0
        for source in term['rows']:
            page = source.get('page_number', term['pdf_page'])
            folio = source.get('printed_page_number', term['printed_page'])
            candidates = [r for r in remaining.values()
                          if (r.get('raw_code') or r.get('code_pattern') or r['code']).upper() == source['code'].upper()
                          and r['name_th'] == source['name_th'] and r['name_en'] == source['name_en']
                          and re.sub(r'\s+', '', str(r['credits_raw'] or '')) == re.sub(r'\s+', '', source['credits']) and r['page_number'] == page
                          and r['printed_page_number'] == folio and r['source_file'] == term['source_file']]
            if len(candidates) != 1:
                raise ValueError('Approved row cannot be uniquely matched without changing facts: ' + source['code'])
            row = candidates[0]
            member_ids = source.get('track_ids', [])
            if len(set(member_ids)) != len(member_ids) or set(member_ids) - track_ids:
                raise ValueError('Unapproved specialization membership')
            memberships[row['id']] = member_ids
            if row['credits'] != int(source['credits'].split('(')[0]):
                raise ValueError('Counted row credits differ from the source')
            source_group = source.get('alt_group')
            if source_group:
                if not row.get('alt_group'):
                    raise ValueError('Printed alternative relationship missing from SQLite')
                approved_groups.setdefault(source_group, []).append(row)
            else:
                if row.get('alt_group'):
                    raise ValueError('SQLite alternative grouping is not approved for this row')
                counted += row['credits']
            remaining.pop(row['id'])
            pairs.add((page, folio))
        database_groups = set()
        for options in approved_groups.values():
            groups = {row['alt_group'] for row in options}
            credits = {row['credits'] for row in options}
            if len(options) < 2 or len(groups) != 1 or len(credits) != 1 or groups & database_groups:
                raise ValueError('Source and SQLite alternative groups disagree')
            database_groups |= groups
            counted += next(iter(credits))
        if counted != term['credits']:
            raise ValueError('Source-supported counted total disagrees with printed total')
        values = (program['program_id'], program['curriculum_version'], identity['plan'], term['year'], term['semester'], term['source_file'], approval['source_sha256'], term['credits'],
                  'รายวิชาทั้งหมดในภาคนี้อยู่ในแผนที่ระบุ; รูปแบบชั่วโมงที่เป็นทางเลือกไม่นับหน่วยกิตซ้ำ',
                  'Rendered PDF table and plan heading independently inspected; production approval only')
        existing = db.execute('SELECT * FROM study_term WHERE program_id=? AND version=? AND plan=? AND year=? AND semester=? AND source_file=?', values[:6]).fetchone()
        if existing:
            if existing['source_sha256'] != approval['source_sha256'] or existing['printed_total'] != term['credits']:
                raise ValueError('Conflicting existing reviewed term; separate source review required')
            tid = existing['id']
        else:
            tid = db.execute('INSERT INTO study_term(program_id,version,plan,year,semester,source_file,source_sha256,printed_total,note,review_method) VALUES (?,?,?,?,?,?,?,?,?,?)', values).lastrowid
            changed.append({'table':'study_term','term_id':tid,'year':term['year'],'semester':term['semester'],'printed_total':term['credits']})
        existing_pairs = {tuple(r) for r in db.execute('SELECT pdf_page,printed_page FROM study_page WHERE term_id=?', (tid,))}
        if existing_pairs - pairs:
            raise ValueError('Conflicting existing source-page evidence')
        for page, folio in sorted(pairs - existing_pairs):
            db.execute('INSERT INTO study_page VALUES (?,?,?)', (tid, page, folio))
            changed.append({'table':'study_page','term_id':tid,'pdf_page':page,'printed_page':folio})
        for track in tracks:
            expected_track = (tid, track['id'], track['label'], json.dumps(track.get('aliases', []), ensure_ascii=False))
            existing_track = db.execute('SELECT * FROM study_track WHERE term_id=? AND track_id=?', expected_track[:2]).fetchone()
            if existing_track and tuple(existing_track) != expected_track:
                raise ValueError('Conflicting specialization metadata')
            if not existing_track:
                db.execute('INSERT INTO study_track VALUES (?,?,?,?)', expected_track)
                changed.append({'table':'study_track','term_id':tid,'track_id':track['id']})
        for row in rows:
            members = memberships[row['id']]
            expected = (row['id'], tid, 0 if members else 1, None, None)
            item = db.execute('SELECT * FROM study_item WHERE plan_item_id=?', (row['id'],)).fetchone()
            if item and tuple(item) != expected:
                raise ValueError('Conflicting term membership')
            if not item:
                db.execute('INSERT INTO study_item VALUES (?,?,?,?,?)', expected)
                changed.append({'table':'study_item','plan_item_id':row['id'],'term_id':tid})
            existing_members = {tuple(r) for r in db.execute('SELECT * FROM study_member WHERE plan_item_id=?', (row['id'],))}
            expected_members = {(row['id'], track_id, None, None) for track_id in members}
            if existing_members - expected_members:
                raise ValueError('Conflicting existing specialization membership')
            for member in sorted(expected_members - existing_members):
                db.execute('INSERT INTO study_member VALUES (?,?,?,?)', member)
                changed.append({'table':'study_member','plan_item_id':row['id'],'track_id':member[1]})
        if db.execute('INSERT OR IGNORE INTO term_metadata_approval VALUES (?,?,?)', (tid, approval_sha, approval['reviewed_on'])).rowcount:
            changed.append({'table':'term_metadata_approval','term_id':tid,'approval_sha256':approval_sha})
    if facts(db) != before:
        raise ValueError('Curriculum facts changed during metadata ingestion')
    if db.execute('PRAGMA foreign_key_check').fetchall() or db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise ValueError('Integrity violation')
    return changed


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--database', type=Path, required=True)
    p.add_argument('--reviews', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    approval = json.loads(a.reviews.read_text(encoding='utf-8'))
    sources = {t['source_file'] for terms in approval['profiles'].values() for t in terms}
    if len(sources) != 1 or sha(a.app_root/'data/input'/next(iter(sources))) != approval['source_sha256']:
        raise ValueError('Source dependency changed')
    a.output.mkdir(parents=True, exist_ok=False)
    live_sha = sha(a.database)
    backup, stage = a.output/'before.db', a.output/'stage.db'
    with closing(open_readonly(a.database)) as original:
        for target in (backup, stage):
            with closing(sqlite3.connect(target)) as dest:
                original.backup(dest)
                if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Backup integrity failure')
    with closing(sqlite3.connect(stage)) as db, db:
        before = facts(db)
        changes = patch(db, approval, sha(a.reviews))
        if patch(db, approval, sha(a.reviews)):
            raise ValueError('Not idempotent')
    if a.apply:
        with closing(sqlite3.connect(a.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if sha(a.database) != live_sha or facts(db) != before:
                raise ValueError('Live dependency changed after backup')
            if patch(db, approval, sha(a.reviews)) != changes:
                raise ValueError('Staged/live changes differ')
    result = {'database':str(a.database),'approval':str(a.reviews),'approval_sha256':sha(a.reviews),
              'source_sha256':approval['source_sha256'],'backup':str(backup),'backup_sha256':sha(backup),
              'applied':a.apply,'changes':changes,'integrity':'ok','idempotent':True,'curriculum_facts_unchanged':True}
    (a.output/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('applied','integrity','idempotent','curriculum_facts_unchanged')} | {'changes':len(changes)}))


if __name__ == '__main__':
    main()
