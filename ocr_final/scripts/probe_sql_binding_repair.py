"""Bounded real-model SQL repair diagnostics; no expected answers or DB writes."""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Preserve existing diagnostic evidence')
    os.environ['CURRICULUM_DATABASE_ROOT'] = str(a.app_root.resolve())
    from lab10_fastapi.curriculum_app import main as web
    from lab10_fastapi.curriculum_app.database import DatabaseRegistry, execute_readonly
    from lab10_fastapi.curriculum_app.query_planner import QueryPlan
    from lab10_fastapi.curriculum_app.sql_parameters import BoundSQL, constraint_sql
    from lab10_fastapi.curriculum_app.request_budget import REQUEST_DEADLINE
    database = next(d for d in DatabaseRegistry(a.app_root).active_catalogs
                    if d.curriculum_name == 'BIT-2565-no-coop')
    web.model.config = replace(web.model.config, request_timeout=30)
    question = 'ปี 3 ภาค 1 มีวิชาเลือกอะไรบ้าง แสดงชื่อและหมวดวิชา'
    plan = QueryPlan('course_list', year=3, semester=1, elective_only=True)
    previous = BoundSQL('SELECT code, name_th FROM plan_item WHERE year=3 AND semester=1',
                        {'year': 3, 'semester': 1})
    error = 'Named parameter keys must match SQL markers exactly; markers=[], keys=[semester, year]'
    result = {'purpose':'exposed development SQL diagnostics, not answer accuracy',
              'database':str(database.path), 'question':question, 'attempts':[]}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    token = REQUEST_DEADLINE.set(time.perf_counter()+45)
    try:
        for attempt in range(2):
            started = time.perf_counter()
            entry = {'attempt':attempt+1}
            try:
                sql = web.model.make_sql(question, plan, database,
                                         previous_sql=previous, error=error)
                parameters = getattr(sql, 'parameters', ())
                entry.update(sql=str(sql), parameters=parameters)
                checked = constraint_sql(sql, parameters)
                web.model._validate_plan_filters(question, plan, database, checked)
                _, rows = execute_readonly(database, str(sql), parameters=parameters)
                entry.update(validated=True, rows=rows)
            except Exception as exc:
                entry.update(validated=False, error=f'{type(exc).__name__}: {exc}')
                error = str(exc)
                if 'sql' in entry:
                    previous = BoundSQL(entry['sql'], entry['parameters'])
            entry['elapsed_ms'] = round((time.perf_counter()-started)*1000,2)
            result['attempts'].append(entry)
            a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            if entry['validated']:
                break
    finally:
        REQUEST_DEADLINE.reset(token)
    print(json.dumps({'attempts':len(result['attempts']),
                      'validated':any(x['validated'] for x in result['attempts'])}))


if __name__ == '__main__':
    main()
