"""Verify a repeated build against prior visual source approval; never ingest facts."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.source_native import CODE, CREDIT, clean, validate_sql_chain
from scripts.database_build import read, write, sha, within
from lab10_fastapi.curriculum_app.build_scope import contract, PLAN_CHECKS


def canonical_plan(data):
    rows = []
    for row in data['courses']:
        codes = CODE.findall(row['code'])
        patterns = list(dict.fromkeys(re.sub(r'\s', '', p) for p in CREDIT.findall(row['credits'])))
        pairs = [{'name_th':clean(n['name_th']), 'name_en':clean(n['name_en'])}
                 for n in row.get('source_name_groups', [])]
        for index, code in enumerate(codes):
            name = row.get('course_options', {}).get(code, row)
            rows.append({'year':row['year'], 'semester':row['semester'], 'code':code,
                'name_th':clean(name['name_th']), 'name_en':clean(name['name_en']),
                'hours':patterns, 'source_names':pairs, 'category':row.get('category'),
                'source_file':row['source_file'], 'pdf_page':name.get('page_number',row['page_number']),
                'printed_page':name.get('printed_page_number',row['printed_page_number']),
                'alternative_index':index+1 if len(codes)>1 else None,
                'bundle_label':row.get('bundle_label'), 'selection_rule':row.get('selection_rule')})
    totals = [{'year':t['year'], 'semester':t['semester'], 'credits':t['credits'],
               'source_file':t['source_file'], 'pdf_page':t['page_number'],
               'printed_page':t['printed_page_number']} for t in data.get('term_totals', [])]
    return {'rows':sorted(rows,key=repr), 'term_totals':sorted(totals,key=repr)}


def fingerprint(data):
    return hashlib.sha256(json.dumps(canonical_plan(data),ensure_ascii=False,sort_keys=True,
                          separators=(',', ':')).encode()).hexdigest()


def verify_profile(candidate, item, approval):
    extraction = read(candidate/item['extraction'])
    if extraction.get('pending_pages') or extraction.get('material_defects') or extraction.get('status') != 'parsed':
        raise ValueError('Incomplete or defective extraction cannot match an approved source')
    if extraction['source_sha256'] != approval['source_sha256']:
        raise ValueError('PDF differs from the previously reviewed source')
    if set(extraction['pages']) != set(approval['pages']):
        raise ValueError('Plan page coverage differs from the approved source')
    if set(approval['verified_fields']) != PLAN_CHECKS:
        raise ValueError('Prior visual source approval does not cover every plan field')
    for artifact in extraction['artifacts']:
        if sha(within(candidate,artifact['path'])) != artifact['sha256']:
            raise ValueError('Extraction artifact changed before source verification')
    raw = candidate/'raw'/item['profile']
    parsed = {'courses':[], 'term_totals':[]}
    paths = list(raw.glob('page-*.plan.json'))
    if {int(p.name.split('-')[1].split('.')[0]) for p in paths} != set(approval['pages']):
        raise ValueError('Missing or extra source-normalization page')
    for path in paths:
        data = read(path)
        parsed['courses'] += data['courses']
        parsed['term_totals'] += data.get('term_totals', [])
    if fingerprint(parsed) != approval['facts_sha256']:
        raise ValueError('New plan facts differ from the previously source-reviewed facts')
    evidence = []
    for expected in approval['evidence']:
        proof = within(raw,expected['file'])
        if sha(proof) != expected['sha256']:
            raise ValueError('Source image differs from prior visual approval; review this rendering explicitly')
        evidence.append({'pdf_page':expected['pdf_page'], 'path':proof.relative_to(candidate).as_posix(),
                         'sha256':expected['sha256']})
    if not {1, *extraction['pages']} <= {r['pdf_page'] for r in evidence}:
        raise ValueError('Prior approval lacks cover or required source images')
    if sha(candidate/item['path']) != item['sha256']:
        raise ValueError('SQLite changed before source verification')
    chain = validate_sql_chain(candidate,item)
    return {'database_sha256':item['sha256'], 'source_sha256':extraction['source_sha256'],
            'verified_fields':sorted(PLAN_CHECKS), 'unresolved_defects':[], 'evidence':evidence,
            'source_fingerprint':approval['facts_sha256'], 'source_sql_chain':chain,
            'notes':['Exact source-image and plan-fingerprint match to prior visual source approval',
                     'Fingerprint checked only after construction; no reference facts supplied to extraction or ingest',
                     'Academic plans only; not raw vision OCR accuracy or a held-out score']}


def certify(candidate, witness_path):
    candidate = candidate.resolve()
    manifest = read(candidate/'build.json')
    witness = read(witness_path)
    if (witness.get('format') != 1 or witness.get('kind') != 'visually-reviewed-plan-fingerprints'
            or contract(manifest)['kind'] != 'academic-plan-only'):
        raise ValueError('This source witness verifies academic-plan scope only')
    if manifest['origin'] not in {'fresh-raw','fresh-reviewed'}:
        raise ValueError('Bundled snapshots are not a PDF reconstruction')
    if manifest['origin']=='fresh-reviewed' and manifest.get('reviewed_input_scope')!='font-encoding-only; no course corrections':
        raise ValueError('Known-source verification does not approve factual corrections')
    items = manifest['databases']
    if len(items)!=len(manifest['requested_profiles']) or {r['profile'] for r in items}!=set(manifest['requested_profiles']):
        raise ValueError('All requested profiles must be rebuilt before verification')
    profiles = {}
    for item in items:
        approval = witness['profiles'].get(item['profile'])
        if not approval:
            raise ValueError('No complete prior visual source approval for '+item['profile'])
        profiles[item['profile']] = verify_profile(candidate,item,approval)
    if (candidate/'source-validation.json').exists():
        raise FileExistsError('Existing review receipt preserved; use a new build')
    copy = candidate/'verification-inputs/source-plan-witness.json'
    write(copy,witness)
    receipt = {'scope':'Repeated PDF reconstruction verified against prior visual source approval; no factual corrections',
               'reviewer':witness['reviewer'], 'profiles':profiles,
               'source_witness':{'path':copy.relative_to(candidate).as_posix(),'sha256':sha(copy)},
               'verification_code_sha256':sha(Path(__file__))}
    write(candidate/'source-validation.json',receipt)
    return receipt
