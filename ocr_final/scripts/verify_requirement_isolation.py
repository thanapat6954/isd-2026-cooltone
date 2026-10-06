"""Observe API provenance on disposable SQLite copies, never production data."""
import argparse
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from lab10_fastapi.curriculum_app import main as web
from lab10_fastapi.curriculum_app.config import settings
from lab10_fastapi.curriculum_app.database import DatabaseRegistry
from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
from scripts.runtime_bundle import sha, snapshot


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, default=ROOT)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    source = DatabaseRegistry(a.app_root)
    hashes = {str(db.path): sha(db.path) for db in source.active_catalogs}
    result = {'purpose': 'API counterfactuals on isolated DB snapshots; no production markers', 'cases': []}
    def record(name, passed, response):
        result['cases'].append({'name': name, 'passed': bool(passed), 'status': response.status_code,
                                'response': response.json()})
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='curriculum-provenance-') as directory:
        root = Path(directory)
        chosen = [db for db in source.active_programs if db.curriculum_name in ('IT-2560-coop', 'IT-2565-coop')]
        if len(chosen) != 2:
            raise ValueError('Both IT versions are required; missing input is not a pass')
        targets = {}
        for db in chosen:
            path = root/db.curriculum_name/'curriculum.db'
            snapshot(db.path, path)
            targets[db.curriculum_version] = path
        service = QwenTextToSQL(replace(settings, sql_repair_attempts=0), web.lab8b)
        with patch.object(web, 'registry', DatabaseRegistry(root)), patch.object(web, 'model', service), TestClient(web.app) as client:
            q = 'IT-2560-coop เกณฑ์การสำเร็จการศึกษามีอะไรบ้าง'
            before = client.post('/api/ask', json={'question': q})
            record('baseline-retrieved-reference', before.status_code == 200 and bool(before.json().get('rows')), before)
            # Synthetic content exists only inside a disposable copy.
            with closing(sqlite3.connect(targets[2560])) as con, con:
                con.execute("UPDATE program_requirement SET rule_text='ISOLATED_DB_FACT_CHANGED'")
            changed = client.post('/api/ask', json={'question': q})
            record('changed-sqlite-fact-invalidates-cache', changed.status_code == 200 and 'ISOLATED_DB_FACT_CHANGED' in changed.json().get('answer', ''), changed)
            other = client.post('/api/ask', json={'question': 'IT-2565-coop เกณฑ์การสำเร็จการศึกษามีอะไรบ้าง'})
            record('other-version-isolated', other.status_code == 200 and 'ISOLATED_DB_FACT_CHANGED' not in other.json().get('answer', '') and other.json().get('selected_curricula') == ['IT-2565-coop'], other)
            with closing(sqlite3.connect(targets[2560])) as con, con:
                con.execute('DELETE FROM program_requirement')
            missing = client.post('/api/ask', json={'question': q})
            record('removed-evidence-no-runtime-overlay', missing.status_code == 200 and not missing.json().get('rows') and 'ISOLATED_DB_FACT_CHANGED' not in missing.json().get('answer', '') and 'IT-2560-coop' in missing.json().get('answer', ''), missing)
            targets[2560].write_bytes(b'isolated deliberately invalid SQLite')
            failure = client.post('/api/ask', json={'question': q})
            record('database-failure-no-fabricated-answer', failure.status_code >= 400 and 'answer' not in failure.json(), failure)
    result['production_hashes_unchanged'] = all(sha(Path(path)) == value for path, value in hashes.items())
    result['summary'] = {'passed': sum(c['passed'] for c in result['cases']), 'n': len(result['cases'])}
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(result['summary'], 'production unchanged:', result['production_hashes_unchanged'])
    return int(not result['production_hashes_unchanged'] or result['summary']['passed'] != result['summary']['n'])


if __name__ == '__main__':
    raise SystemExit(main())
