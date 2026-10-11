"""Portable staged PDF rebuild, bundle import, validation, offline activation and rollback."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_lab8b import PROFILES
from scripts.runtime_bundle import sha, snapshot, within
from lab10_fastapi.curriculum_app.build_store import consumer_lock, selected_build
from lab10_fastapi.curriculum_app.database import DatabaseRegistry
from lab10_fastapi.curriculum_app.build_scope import contract, PLAN_CAPABILITIES, PLAN_CHECKS, FULL_CHECKS


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.partial')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for attempt in range(5):
        try:
            os.replace(temporary, path)
            break
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.1)


def validate_plan_terms(db, native=False):
    """Keep regular terms and accept extra terms only with native source totals.

    The caller also checks the complete selected pages, visual receipt and the
    native artifact-to-SQL chain. This does not certify additional terms alone.
    """
    terms = {tuple(row) for row in db.execute('SELECT DISTINCT year,semester FROM plan_item')}
    regular = {(year, semester) for year in range(1, 5) for semester in (1, 2)}
    if not regular <= terms:
        raise ValueError('declared four-year plan scope missing required term rows')
    if terms != regular:
        if not native:
            raise ValueError('additional terms require a complete native source-to-SQL chain')
        evidence = {tuple(row) for row in db.execute('SELECT year,semester FROM plan_term_source')}
        if terms != evidence:
            raise ValueError('additional term identity differs from source-backed term totals')


def identity():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:10]


def readonly(path):
    connection = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    return connection


def required():
    return {(p['program_id'], p['curriculum_version'], p['target_plan'].replace('_', '-')) for p in PROFILES.values()}


def validate(candidate, app, *, full=True):
    manifest = read(candidate/'build.json')
    errors, seen, profiles = [], set(), []
    scope = contract(manifest)
    if not full and scope['kind'] != 'academic-plan-only':
        errors.append('declared activation ต้องมี academic-plan-only contract; diagnostic partial ไม่ใช่ ready')
    if not full and manifest.get('origin') not in {'fresh-raw', 'fresh-reviewed'}:
        errors.append('declared source build ต้องมี fresh extraction provenance; bundled snapshot ไม่ใช่ reconstruction')
    if full and scope['partial']:
        errors.append('declared partial build ไม่ใช่ full replacement; ใช้ activate-scoped อย่าง explicit')
    if manifest.get('format') != 1 or not manifest.get('databases'):
        errors.append('ไม่มี database manifest ที่รองรับ')
    for source in manifest.get('source_pdfs', []):
        path = within(app, source['path'])
        if not path.is_file() or sha(path) != source['sha256']:
            errors.append('PDF หายหรือ hash เปลี่ยน: '+source['path'])
    paths = []
    for item in manifest.get('databases', []):
        path = within(candidate, item['path'])
        detail = {'path': item['path'], 'profile': item['profile'], 'errors': []}
        profiles.append(detail)
        try:
            if item['path'] in paths or path.name != 'curriculum.db' or sha(path) != item['sha256']:
                raise ValueError('duplicate path / database hash mismatch')
            paths.append(item['path'])
            with closing(readonly(path)) as db:
                if [r[0] for r in db.execute('PRAGMA integrity_check')] != ['ok']:
                    raise ValueError('SQLite integrity failed')
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'program' in tables:
                    if not {'course', 'plan_item', 'prerequisite'} <= tables:
                        raise ValueError('required schema missing')
                    programs = list(db.execute('SELECT * FROM program'))
                    if len(programs) != 1:
                        raise ValueError('exactly one resolved program required')
                    program = dict(programs[0])
                    key = (program['program_id'], program.get('curriculum_version'), program.get('plan'))
                    if key not in required() or key in seen:
                        raise ValueError('unresolved/duplicate curriculum version or plan')
                    seen.add(key)
                    if (item.get('program_id'), item.get('version'), item.get('plan')) != key:
                        raise ValueError('manifest identity differs from SQLite')
                    columns = {r[1] for r in db.execute('PRAGMA table_info(plan_item)')}
                    if not {'raw_code', 'code_pattern', 'is_placeholder', 'alternative_index', 'printed_page_number'} <= columns:
                        raise ValueError('placeholder/alternative/page schema missing')
                    count = db.execute('SELECT COUNT(*) FROM plan_item').fetchone()[0]
                    if not count:
                        raise ValueError('empty plan extraction')
                    if not db.execute('SELECT COUNT(*) FROM course').fetchone()[0]:
                        raise ValueError('empty course catalog')
                    detail.update(identity=list(key), plan_rows=count)
                elif 'courses' in tables:
                    if item['profile'] != 'legacy-course-catalog' or 'legacy' in seen:
                        raise ValueError('invalid legacy identity')
                    seen.add('legacy')
                    if not db.execute('SELECT COUNT(*) FROM courses').fetchone()[0]:
                        raise ValueError('empty legacy extraction')
                else:
                    raise ValueError('unknown schema')
            if manifest['origin'] == 'bundled-snapshot':
                original = read(candidate/'origin-manifest.json')
                origin = [r for r in original['databases'] if r['path'] == item['path']]
                if len(origin) != 1 or origin[0]['sha256'] != item['sha256']:
                    raise ValueError('bundle origin hash mismatch')
                detail['factual_status'] = 'existing reviewed runtime snapshot; broader source gaps retained'
            else:
                extraction = read(candidate/item['extraction'])
                if manifest['origin']=='fresh-raw' and extraction.get('reviewed_corrections'):
                    raise ValueError('Raw build must not use reviewed corrections')
                if manifest.get('reviewed_input_scope')=='font-encoding-only; no course corrections':
                    approvals = extraction.get('reviewed_corrections',[])
                    native_encoding = extraction.get('extraction_method') == 'pdf-text-tables'
                    if (native_encoding and (len(approvals)!=1 or approvals[0].get('kind')!='reviewed-font-encoding')) or (not native_encoding and approvals):
                        raise ValueError('Reviewed encoding provenance incomplete or includes course corrections')
                    if approvals and sha(within(candidate,approvals[0]['path'])) != approvals[0]['sha256']:
                        raise ValueError('Reviewed encoding input changed')
                if extraction.get('conversion',{}).get('warnings') or extraction.get('conversion',{}).get('fidelity_errors'):
                    raise ValueError('parser/table fidelity defects remain; preserve raw output and review source')
                if manifest.get('source_review_findings'):
                    findings=manifest['source_review_findings']
                    path=within(candidate,findings['path'])
                    if sha(path)!=findings['sha256']:
                        raise ValueError('source-review findings hash mismatch')
                    if any(r.get('profile')==item['profile'] and r.get('status')!='resolved' for r in read(path)['findings']):
                        raise ValueError('known material source defects remain: see source-review-findings.json')
                if extraction.get('status') != 'parsed' or extraction.get('material_defects'):
                    raise ValueError('OCR/parsing failed or material defects remain')
                if extraction.get('pending_pages') or not extraction.get('pages'):
                    raise ValueError('incomplete OCR page coverage')
                if full and not all(extraction.get('domains', {}).get(domain) is True
                                    for domain in ('catalog_complete', 'program_rules_complete')):
                    raise ValueError('full replacement ต้องมี catalog descriptions และ program rules ที่ครบและ source-validated; plan/corpus candidates ไม่เพียงพอ')
                for artifact in extraction.get('artifacts', []):
                    if sha(within(candidate, artifact['path'])) != artifact['sha256']:
                        raise ValueError('generated extraction artifact changed')
                # Source review is a validation receipt, never an answer overlay.
                receipt_path = candidate/'source-validation.json'
                if not receipt_path.exists():
                    raise ValueError('ยังไม่มี independent source review: raw OCR/HTTP 200 ไม่ยืนยัน facts; ห้าม activate')
                receipt = read(receipt_path)
                review = receipt.get('profiles', {}).get(item['profile'], {})
                if review.get('database_sha256') != item['sha256'] or review.get('source_sha256') != extraction['source_sha256']:
                    raise ValueError('source review hash mismatch')
                checks = FULL_CHECKS if full else PLAN_CHECKS
                if set(review.get('verified_fields', [])) != checks or review.get('unresolved_defects') != []:
                    raise ValueError('source review incomplete or material defects unresolved')
                evidence = review.get('evidence', [])
                if not evidence or not set(extraction['pages']) <= {r['pdf_page'] for r in evidence}:
                    raise ValueError('source review must cover all extracted pages')
                for row in evidence:
                    proof = within(candidate, row['path'])
                    if sha(proof) != row['sha256']:
                        raise ValueError('source review evidence hash mismatch')
                detail['factual_status'] = 'independent manual source validation disclosed; not raw OCR accuracy'
                if not full:
                    config = PROFILES[item['profile']]
                    first, last = map(int, config['pages'].split('-'))
                    expected_pages = set(range(first, last+1))
                    if set(extraction['pages']) != expected_pages:
                        raise ValueError('declared plan scope must include every recorded plan page')
                    with closing(readonly(within(candidate,item['path']))) as db:
                        validate_plan_terms(db, native=extraction.get('extraction_method') == 'pdf-text-tables')
                    if extraction.get('extraction_method') == 'pdf-text-tables' or extraction.get('normalization_method') == 'deterministic-physical-table-parser':
                        from scripts.source_native import validate_sql_chain
                        validate_sql_chain(candidate, item)
        except (ValueError, OSError, KeyError, sqlite3.Error) as exc:
            detail['errors'].append(str(exc))
            errors.append(item['profile']+': '+str(exc))
    actual_files = {p.relative_to(candidate).as_posix() for p in candidate.rglob('curriculum.db')
                    if 'attempts' not in p.relative_to(candidate).parts}
    if actual_files != set(paths):
        errors.append('undeclared or missing database files')
    if full and seen != required() | {'legacy'}:
        errors.append('profile set ไม่ครบ: ต้องมี 13 curriculum/plan และ legacy 1; partial ไม่แทนทั้งระบบ')
    if not full and scope['kind'] == 'academic-plan-only':
        declared = scope['profiles']
        if any(p not in PROFILES for p in declared) or set(declared) != {r['profile'] for r in manifest['databases']}:
            errors.append('declared profile set missing/mismatched; no implicit subset')
        expected = {(PROFILES[p]['program_id'], PROFILES[p]['curriculum_version'], PROFILES[p]['target_plan'].replace('_','-'))
                    for p in declared if p in PROFILES}
        if seen != expected or manifest.get('requested_profiles') != declared:
            errors.append('declared profile identity mismatch')
    report = {'build_id': manifest['build_id'], 'ready': not errors, 'full_replacement': full,
              'contract': scope, 'partial': scope['partial'],
              'origin': manifest['origin'], 'profiles': profiles, 'errors': errors,
              'checked_utc': datetime.now(timezone.utc).isoformat()}
    write(candidate/'validation.json', report)
    return report


def import_bundle(bundle, app):
    original = read(bundle/'manifest.json')
    candidate = app/'work/staging'/identity()
    candidate.mkdir(parents=True, exist_ok=False)
    manifest = {'format': 1, 'build_id': candidate.name, 'origin': 'bundled-snapshot',
                'scope': original.get('scope'), 'databases': [], 'source_pdfs': original['source_pdfs']}
    write(candidate/'origin-manifest.json', original)
    for item in original['databases']:
        source, target = within(bundle, item['path']), within(candidate, item['path'])
        if sha(source) != item['sha256']:
            raise ValueError('bundle hash mismatch')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        with closing(readonly(target)) as db:
            table = db.execute("SELECT name FROM sqlite_master WHERE name='program'").fetchone()
            program = dict(db.execute('SELECT * FROM program').fetchone()) if table else {}
        manifest['databases'].append({**item, 'program_id': program.get('program_id')})
    write(candidate/'build.json', manifest)
    validate(candidate, app)
    return candidate


def backup_active(app, tag):
    output = app/'work/backups/build-switch'/tag
    output.mkdir(parents=True, exist_ok=False)
    root, build_id, _ = selected_build(app)
    registry = DatabaseRegistry(app)
    record = {'build_id': build_id, 'pointer': read(app/'work/active-build.json') if (app/'work/active-build.json').exists() else None,
              'contract': registry.build_manifest.get('contract') if registry.build_manifest else None,
              'scope': 'entire active databases including user edits/tables; kept separately, not silently migrated',
              'databases': []}
    for item in registry.active_catalogs:
        relative = item.path.relative_to(root).as_posix()
        target = within(output, relative)
        snapshot(item.path, target)
        record['databases'].append({'path': relative, 'sha256': sha(target), 'active_sha256': sha(item.path), 'integrity': 'ok'})
    write(output/'backup.json', record)
    return output, record


def activation(app, candidate, *, failure_hook=None, declared=False):
    with consumer_lock(app):
        report = validate(candidate, app, full=not declared)
        if not report['ready']:
            raise ValueError('candidate ถูกปฏิเสธ; ดู validation.json; active build ไม่เปลี่ยน')
        tag = identity()
        backup, previous = backup_active(app, tag)
        destination = app/'work/builds'/report['build_id']
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError('build identity already installed')
        shutil.copytree(candidate, destination)
        if not validate(destination, app, full=not declared)['ready']:
            raise ValueError('installed build validation failed; old pointer retained')
        pointer = app/'work/active-build.json'
        new = {'build_id': report['build_id'], 'directory': destination.relative_to(app).as_posix(), 'backup': backup.relative_to(app).as_posix()}
        write(backup/'transaction.json', {'status': 'prepared', 'new': new, 'previous': previous['pointer']})
        try:
            if failure_hook:
                failure_hook('before-pointer')
            write(pointer, new)
            if failure_hook:
                failure_hook('after-pointer')
            loaded = DatabaseRegistry(app)
            if loaded.build_id != new['build_id'] or len(loaded.active_catalogs) != report['contract']['expected_catalogs']:
                raise ValueError('post-activation identity/profile check failed')
            write(backup/'transaction.json', {'status': 'activated', 'new': new, 'previous': previous['pointer']})
        except Exception:
            if previous['pointer'] is None:
                pointer.unlink(missing_ok=True)
            else:
                write(pointer, previous['pointer'])
            write(backup/'transaction.json', {'status': 'rolled-back', 'new': new, 'previous': previous['pointer']})
            raise
        return {'build_id': new['build_id'], 'backup': str(backup),
                'contract': report['contract'], 'full_replacement': not declared,
                'recovery': '.\\venv\\Scripts\\python.exe scripts/database_build.py rollback --backup "'+str(backup)+'"'}


def rollback(app, backup):
    with consumer_lock(app):
        record = read(backup/'backup.json')
        for item in record['databases']:
            if sha(within(backup, item['path'])) != item['sha256']:
                raise ValueError('backup hash mismatch; active pointer retained')
        # Recover to backup snapshots, so subsequent user edits to old files are not overwritten.
        destination = app/'work/builds'/('recovery-'+identity())
        destination.mkdir(parents=True, exist_ok=False)
        for item in record['databases']:
            target = within(destination, item['path'])
            snapshot(within(backup, item['path']), target)
        if not record['databases']:
            raise ValueError('ไม่มี previous databases: ใช้ import-bundle และ activate ใหม่')
        manifest = {'format': 1, 'build_id': destination.name, 'origin': 'recovery-snapshot', 'databases': record['databases']}
        if record.get('contract'):
            manifest['contract'] = record['contract']
        write(destination/'build.json', manifest)
        write(app/'work/active-build.json', {'build_id': destination.name, 'directory': destination.relative_to(app).as_posix()})
        registry = DatabaseRegistry(app)
        return {'build_id': registry.build_id, 'database_count': len(registry.active_catalogs)}


def rebuild(app, profiles, mode, max_pages, timeout, resume=None, extraction_method='ocr', declared=False,
            source_documents=False, font_review=None):
    """No previous DB/OCR/master/evaluation is copied into the isolated executor."""
    if source_documents and (extraction_method != 'native' or declared or resume):
        raise ValueError('--source-documents ใช้กับ native/new staging/full diagnostic scope; ยังไม่ใช่ certified plan-only หรือ full replacement')
    if font_review and (mode != 'reviewed' or extraction_method not in {'native','hybrid'} or resume):
        raise ValueError('--font-review ต้องใช้ --mode reviewed --extraction native และ staging ใหม่; ใช้เฉพาะ encoding ไม่รวม course corrections')
    candidate = resume.resolve() if resume else app/'work/staging'/identity()
    if resume and not candidate.is_relative_to((app/'work/staging').resolve()):
        raise ValueError('resume ต้องเป็น staging ของแอปนี้')
    if not resume:
        candidate.mkdir(parents=True, exist_ok=False)
    sandbox = candidate/'executor'
    if not resume:
        sandbox.mkdir()
        for folder in ('scr', 'scripts'):
            shutil.copytree(ROOT/folder, sandbox/folder, ignore=shutil.ignore_patterns('__pycache__', '*.db', '*.json'))
    # Only page selection and explicitly named production corrections enter the build.
    if not resume:
        (sandbox/'data/input').mkdir(parents=True)
    manifest = {'format': 1, 'build_id': candidate.name, 'origin': 'fresh-'+mode,
                'scope': ('fresh academic-plan '+('native PDF text/table extraction; not vision OCR'
                           if extraction_method == 'native' else ('hybrid PDF text/tables with image OCR fallback' if extraction_method == 'hybrid' else 'vision OCR'))
                          +'; descriptions/rules/legacy require separate verified extraction'),
                'databases': [], 'source_pdfs': [], 'profiles': {}, 'dependencies': [], 'running': None}
    if declared:
        manifest['contract'] = {'kind': 'academic-plan-only', 'partial': True, 'profiles': profiles,
            'capabilities': PLAN_CAPABILITIES, 'exclusions': ['catalog_descriptions', 'program_rules', 'prerequisites', 'legacy', 'other_profiles']}
    manifest['extraction_method'] = extraction_method
    manifest['source_documents_requested'] = source_documents
    copied = set()
    env = {**os.environ, 'PYTHONUTF8': '1', 'LAB7B_OCR_RETRIES': '0', 'LAB7B_OCR_TEMPERATURE': '0',
           'LAB7_MODEL_OCR': os.getenv('LAB7_MODEL_OCR', 'scb10x/typhoon-ocr1.5-3b:latest'), 'LAB7_CHUNK': '1'}
    for path in sorted([*ROOT.glob('scripts/*.py'), *ROOT.glob('scr/ocr_system/*.py'),
                        ROOT/'run_lab8b.py', ROOT/'lab10_fastapi/curriculum_app/build_scope.py']):
        manifest['dependencies'].append({'kind': 'code', 'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)})
    manifest['configuration'] = {k: v for k,v in env.items() if k.startswith(('LAB7', 'LAB8', 'OLLAMA'))}
    manifest['model_inventory'] = {}
    if extraction_method in {'ocr','hybrid'} and any((app/'data/input'/PROFILES[name]['input'].name).exists() for name in profiles):
        try:
            tags=requests.get(env.get('OLLAMA_HOST','http://127.0.0.1:11434').rstrip('/')+'/api/tags',timeout=5)
            tags.raise_for_status()
            for kind, identifier in (('ocr',env['LAB7_MODEL_OCR']),('parser',env.get('LAB7_MODEL_TEXT','qwen3:4b'))):
                model=next((m for m in tags.json()['models'] if m['name'] in {identifier,identifier+':latest'}),{})
                manifest['model_inventory'][kind]={'identifier':identifier,'digest':model.get('digest')}
        except (requests.RequestException,ValueError,KeyError) as exc:
            manifest['model_inventory']['unavailable']=str(exc)
    manifest['requested_profiles'] = profiles
    manifest['mode'] = mode
    if font_review:
        font_review = font_review.resolve()
        reviewed_copy = candidate/'reviewed-inputs/font-encoding.json'
        write(reviewed_copy,read(font_review))
        manifest['reviewed_input_scope'] = 'font-encoding-only; no course corrections'
        manifest['dependencies'].append({'kind':'reviewed-font-encoding','path':str(font_review),
                                         'sha256':sha(font_review)})
    if resume:
        previous = read(candidate/'build.json')
        expected_code = [r for r in previous['dependencies'] if r['kind']=='code']
        if (expected_code != manifest['dependencies'] or previous['configuration'] != manifest['configuration']
                or previous['requested_profiles'] != profiles or previous['mode'] != mode
                or previous.get('extraction_method','ocr') != extraction_method or previous.get('contract') != manifest.get('contract')
                or previous.get('source_documents_requested',False) != source_documents
                or previous.get('model_inventory') != manifest['model_inventory']):
            raise ValueError('code/configuration/scope เปลี่ยน: เก็บ checkpoint เดิมและใช้ staging ใหม่')
        for item in previous['source_pdfs']:
            if sha(within(app,item['path'])) != item['sha256'] or sha(within(sandbox,item['path'])) != item['sha256']:
                raise ValueError('source เปลี่ยน: ห้าม resume')
        for dependency in previous['dependencies']:
            if dependency['kind']=='page-selection-only' and sha(within(app,dependency['path'])) != dependency['sha256']:
                raise ValueError('page selection เปลี่ยน: ห้าม resume')
        manifest=previous
        copied={Path(s['path']).name for s in previous['source_pdfs']}
        write(candidate/('build-before-resume-'+identity()+'.json'),previous)
    write(candidate/'build.json', manifest)
    for name in profiles:
        if resume and manifest['profiles'].get(name,{}).get('status')=='parsed' and not manifest['profiles'][name].get('pending_pages'):
            for artifact in manifest['profiles'][name].get('artifacts',[]):
                if sha(within(candidate,artifact['path'])) != artifact['sha256']:
                    raise ValueError('generated artifact เปลี่ยน: ห้าม reuse checkpoint')
            continue
        config = PROFILES[name]
        pdf = app/'data/input'/config['input'].name
        record = {'status': 'started', 'source_sha256': sha(pdf) if pdf.exists() else None,
                  'pages': [], 'pending_pages': [], 'material_defects': [], 'artifacts': [], 'stages': []}
        manifest['profiles'][name] = record
        manifest['running'] = name
        write(candidate/'build.json', manifest)
        if not pdf.exists():
            record.update(status='failed', material_defects=['ไม่พบ PDF: วาง '+pdf.name+' ใน data/input ก่อน rebuild'])
            write(candidate/'build.json', manifest)
            continue
        if pdf.name not in copied:
            shutil.copyfile(pdf, sandbox/'data/input'/pdf.name)
            copied.add(pdf.name)
            manifest['source_pdfs'].append({'path': 'data/input/'+pdf.name, 'sha256': sha(pdf)})
        selection = app/'data/source_reviews/page_selection'/(pdf.stem+'.json')
        selections = read(selection)
        first, last = map(int, config['pages'].split('-'))
        expected = list(range(first, last+1))
        if not set(expected) <= {r['pdf_page'] for r in selections['pages'] if r['decision'] == 'include'}:
            record.update(status='failed', material_defects=['plan page selection ยังไม่ผ่าน source review'])
            write(candidate/'build.json', manifest)
            continue
        selection_copy = sandbox/(pdf.stem+'-selection.json')
        shutil.copyfile(selection, selection_copy)
        dependency={'kind': 'page-selection-only', 'path': selection.relative_to(app).as_posix(), 'sha256': sha(selection)}
        if dependency not in manifest['dependencies']:
            manifest['dependencies'].append(dependency)
        raw = candidate/'raw'/name
        raw.parent.mkdir(exist_ok=True)
        command = [sys.executable, '-X', 'utf8', str(sandbox/'scripts/extract_manifest_pages.py'), '--manifest', str(selection_copy),
                   '--source-root', str(sandbox), '--output', str(raw)]
        if extraction_method == 'ocr':
            command += ['--layout', 'raster-rows']
        if extraction_method in {'native','hybrid'}:
            if resume:
                raise ValueError('native extraction ใช้ staging ใหม่; ไม่ reuse saved extraction')
            command = [sys.executable, '-X', 'utf8', str(sandbox/'scripts/source_native.py'),
                       '--pdf', str(sandbox/'data/input'/pdf.name), '--output', str(raw)]
            if font_review:
                command += ['--font-review',str(reviewed_copy)]
            if extraction_method == 'hybrid':
                command[3] = str(sandbox/'scripts/hybrid_extract.py')
                command += ['--manifest', str(selection_copy), '--source-root', str(sandbox)]
        for page in expected:
            command += ['--page', str(page)]
        if max_pages:
            command += ['--max-pages', str(max_pages)]
        if resume and (raw/'manifest-extraction.json').exists():
            command += ['--resume']
        started = time.perf_counter()
        try:
            with (candidate/(name+'.ocr.log')).open('a' if resume else 'w', encoding='utf-8') as log:
                result = subprocess.run(command, env=env, cwd=sandbox, stdout=log, stderr=log, timeout=timeout)
            record['stages'].append({'name': 'hybrid-source-extraction' if extraction_method=='hybrid' else ('render-source-native-tables' if extraction_method=='native' else 'render-preprocess-OCR'), 'seconds': round(time.perf_counter()-started, 3), 'exit_code': result.returncode, 'command': command})
            extraction = read(raw/'manifest-extraction.json')
            actual_native = extraction.get('method') == 'pdf-text-tables'
            record['pages'] = [r['pdf_page'] for r in extraction['processed']]
            record['pending_pages'] = sorted(set(expected)-set(record['pages']))
            record['material_defects'] = [flag for r in extraction['processed'] for flag in r['quality_flags']]
            if result.returncode:
                record['extraction_failures'] = extraction['failed']
                method = 'Native PDF extraction' if extraction_method=='native' else 'OCR'
                raise ValueError(method+' ล้มเหลว: ตรวจ manifest/log/ภาพต้นฉบับ; ห้ามใช้ bundle แทน')
            if extraction['failed'] or record['material_defects']:
                raise ValueError('OCR ว่าง/คุณภาพไม่ครบ: ตรวจภาพต้นฉบับก่อนแก้ configuration')
            record['status'] = 'ocr-complete' if not record['pending_pages'] else 'partial'
            # Preserve every prior parsed/DB attempt before regenerating staged output.
            prior_output=candidate/'work'/config['out'].name
            if prior_output.exists():
                archived=candidate/'attempts'/identity()
                archived.mkdir(parents=True)
                if not prior_output.resolve().is_relative_to(candidate) or not archived.resolve().is_relative_to(candidate):
                    raise ValueError('attempt archive escapes staging')
                prior_output.rename(archived/prior_output.name)
                for prior in list(candidate.glob(name+'.*.json')):
                    prior.rename(archived/prior.name)
                manifest['databases']=[d for d in manifest['databases'] if d['profile']!=name]
            # Parsing uses only fresh markdown and source-recorded code configuration.
            command = [sys.executable, '-X', 'utf8', str(ROOT/'scripts/parse_fresh_build.py'), '--candidate', str(candidate), '--profile', name,
                       '--mode', 'raw' if extraction_method=='hybrid' and not actual_native else mode, '--app-root', str(app)]
            if font_review and actual_native:
                command += ['--font-encoding-only']
            started = time.perf_counter()
            with (candidate/(name+'.parse.log')).open('a' if resume else 'w', encoding='utf-8') as log:
                result = subprocess.run(command, env=env, stdout=log, stderr=log, cwd=sandbox, timeout=timeout)
            record['stages'].append({'name': 'parse-normalize-SQLite', 'seconds': round(time.perf_counter()-started, 3), 'exit_code': result.returncode})
            if result.returncode:
                raise ValueError('parsing/build ล้มเหลว: ดู parse.log; active build ไม่เปลี่ยน')
            detail = read(candidate/(name+'.extraction.json'))
            if source_documents:
                source_output = candidate/'source-documents'/name
                command = [sys.executable, '-X', 'utf8', str(sandbox/'scripts/source_catalog.py'),
                           '--pdf', str(sandbox/'data/input'/pdf.name), '--output', str(source_output),
                           '--staged-database', str(candidate/'work'/config['out'].name/'curriculum.db')]
                if font_review:
                    command += ['--font-review', str(candidate/'reviewed-inputs/font-encoding.json')]
                started = time.perf_counter()
                with (candidate/(name+'.source-documents.log')).open('w',encoding='utf-8') as log:
                    result = subprocess.run(command,env=env,stdout=log,stderr=log,cwd=sandbox,timeout=timeout)
                record['stages'].append({'name':'fresh-native-corpus-catalog-candidates',
                    'seconds':round(time.perf_counter()-started,3),'exit_code':result.returncode})
                if result.returncode:
                    raise ValueError('source catalog extraction ล้มเหลว; ตรวจ log; ไม่ใช้ bundled descriptions/rules')
                source_state = read(source_output/'source-catalog.json')
                detail['source_documents'] = source_state
                detail['domains'] = {**source_state['domains'], 'academic_plan':True}
                detail['artifacts'].extend({'path':p.relative_to(candidate).as_posix(),'sha256':sha(p)}
                                           for p in sorted(source_output.rglob('*')) if p.is_file())
                detail['limitations'] = source_state['limitations'] + ['full runtime normalization/review pending; diagnostic only']
                write(candidate/(name+'.extraction.json'),detail)
            record.update(detail)
            db_path = 'work/'+config['out'].name+'/curriculum.db'
            manifest['databases'].append({'path': db_path, 'sha256': sha(candidate/db_path), 'profile': name,
                'program_id': config['program_id'], 'version': config['curriculum_version'], 'plan': config['target_plan'].replace('_', '-'),
                'extraction': name+'.extraction.json'})
        except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
            record['status'] = 'failed'
            record['material_defects'].append(str(exc))
        write(candidate/'build.json', manifest)
    manifest['running'] = None
    manifest['finished_utc'] = datetime.now(timezone.utc).isoformat()
    write(candidate/'build.json', manifest)
    validate(candidate, app, full=not declared)
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='action', required=True)
    command = sub.add_parser('import-bundle')
    command.add_argument('--bundle', type=Path, required=True)
    command = sub.add_parser('rebuild')
    command.add_argument('--profiles', nargs='+', choices=list(PROFILES), default=list(PROFILES))
    command.add_argument('--mode', choices=('raw', 'reviewed'), default='raw')
    command.add_argument('--max-pages', type=int)
    command.add_argument('--stage-timeout', type=int, default=900)
    command.add_argument('--extraction', choices=('ocr','native','hybrid'), default='hybrid', help='hybrid reads PDF text/tables first, then uses image OCR after native rejection; routes are recorded')
    command.add_argument('--font-review',type=Path,help='Explicit source-reviewed font encoding only; native/reviewed/new build; no course corrections')
    command.add_argument('--scope', choices=('full','academic-plan-only'), default='full', help='Partial scope is explicit and cannot pass full activation')
    command.add_argument('--source-documents',action='store_true',help='Native full-PDF corpus/catalog candidates in staging; experimental, not certified replacement')
    command.add_argument('--resume',type=Path,help='Continue only matching source/code/config/model page checkpoints; retained attempts stay separate')
    for action in ('validate', 'activate', 'activate-scoped'):
        command = sub.add_parser(action)
        command.add_argument('--candidate', type=Path, required=True)
        if action == 'validate':
            command.add_argument('--scope',choices=('full','declared'),default='full')
    command = sub.add_parser('rollback')
    command.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    app = args.app_root.resolve()
    if args.action == 'import-bundle':
        result = {'candidate': str(import_bundle(args.bundle.resolve(), app))}
    elif args.action == 'rebuild':
        candidate = rebuild(app, args.profiles, args.mode, args.max_pages, args.stage_timeout,args.resume,
                            args.extraction,args.scope=='academic-plan-only',args.source_documents,args.font_review)
        result = {'candidate': str(candidate), 'validation': read(candidate/'validation.json')}
    elif args.action == 'validate':
        result = validate(args.candidate.resolve(), app,full=args.scope=='full')
    elif args.action in {'activate','activate-scoped'}:
        result = activation(app, args.candidate.resolve(),declared=args.action=='activate-scoped')
    else:
        result = rollback(app, args.backup.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result.get('ready') is False or result.get('validation', {}).get('ready') is False)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError) as exc:
        print('ไม่สำเร็จ: '+str(exc)+'\nเก็บ diagnostics/staging ไว้; เปิดแอปด้วย previous build ได้ตามเดิม', file=sys.stderr)
        raise SystemExit(1)
