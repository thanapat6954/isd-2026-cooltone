"""SQLite-only study-plan evidence. JSON reviews are ingestion inputs, never runtime facts."""
import json
from .database import open_readonly


DDL = """
CREATE TABLE IF NOT EXISTS study_term (
 id INTEGER PRIMARY KEY, program_id TEXT NOT NULL, version INTEGER NOT NULL,
 plan TEXT NOT NULL, year INTEGER NOT NULL, semester INTEGER NOT NULL,
 source_file TEXT NOT NULL, source_sha256 TEXT NOT NULL, printed_total INTEGER,
 note TEXT NOT NULL, review_method TEXT NOT NULL,
 UNIQUE(program_id, version, plan, year, semester, source_file));
CREATE TABLE IF NOT EXISTS study_page (
 term_id INTEGER NOT NULL REFERENCES study_term(id), pdf_page INTEGER NOT NULL,
 printed_page INTEGER NOT NULL, PRIMARY KEY(term_id,pdf_page));
CREATE TABLE IF NOT EXISTS study_track (
 term_id INTEGER NOT NULL REFERENCES study_term(id), track_id TEXT NOT NULL,
 label TEXT NOT NULL, aliases TEXT NOT NULL, PRIMARY KEY(term_id,track_id));
CREATE TABLE IF NOT EXISTS study_item (
 plan_item_id INTEGER PRIMARY KEY REFERENCES plan_item(id),
 term_id INTEGER NOT NULL REFERENCES study_term(id),
 shared INTEGER NOT NULL DEFAULT 0, requirement_id TEXT,
 section_label TEXT);
CREATE TABLE IF NOT EXISTS study_member (
 plan_item_id INTEGER NOT NULL REFERENCES study_item(plan_item_id),
 track_id TEXT NOT NULL, display_name_th TEXT, display_name_en TEXT,
 PRIMARY KEY(plan_item_id,track_id));
CREATE TABLE IF NOT EXISTS study_correction (
 id INTEGER PRIMARY KEY, term_id INTEGER NOT NULL REFERENCES study_term(id),
 plan_item_id INTEGER REFERENCES plan_item(id), target TEXT NOT NULL,
 field TEXT NOT NULL, old_value TEXT, new_value TEXT,
 pdf_page INTEGER NOT NULL, printed_page INTEGER NOT NULL,
 ingestion_sha256 TEXT NOT NULL, reviewed_on TEXT NOT NULL);
"""


def read_study_evidence(database):
    """Fail on DB I/O errors; no JSON or source-document fallback."""
    connection = open_readonly(database.path)
    try:
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'study_term' not in tables:
            return {'terms': [], 'tracks': {}, 'items': {}, 'members': {}}
        identity = (database.program_id, database.curriculum_version, database.plan)
        terms = [dict(r) for r in connection.execute(
            'SELECT * FROM study_term WHERE program_id=? AND version=? AND plan=?', identity)]
        result = {'terms': terms, 'tracks': {}, 'items': {}, 'members': {}}
        for t in terms:
            t['pages'] = [dict(r) for r in connection.execute('SELECT * FROM study_page WHERE term_id=?', (t['id'],))]
            tracks = [dict(r) for r in connection.execute('SELECT * FROM study_track WHERE term_id=? ORDER BY rowid', (t['id'],))]
            for track in tracks: track['aliases'] = json.loads(track['aliases'])
            result['tracks'][t['id']] = tracks
            for row in connection.execute('SELECT * FROM study_item WHERE term_id=?', (t['id'],)):
                result['items'][row['plan_item_id']] = dict(row)
                result['members'][row['plan_item_id']] = [dict(r) for r in connection.execute(
                    'SELECT * FROM study_member WHERE plan_item_id=? ORDER BY rowid', (row['plan_item_id'],))]
        return result
    finally:
        connection.close()
