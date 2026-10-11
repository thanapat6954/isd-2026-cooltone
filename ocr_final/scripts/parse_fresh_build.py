"""Fresh markdown -> parser -> SQLite without previous DB metadata or masters."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_lab8b import PROFILES
from scripts.database_build import read, write, sha


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def is_raster_ocr(state):
    renderer = state.get('dependencies', {}).get('renderer')
    return state.get('method') != 'pdf-text-tables' and isinstance(renderer, dict) and renderer.get('layout') == 'raster-rows'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--profile', choices=list(PROFILES), required=True)
    parser.add_argument('--mode', choices=('raw', 'reviewed'), required=True)
    parser.add_argument('--font-encoding-only',action='store_true')
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    sandbox = candidate/'executor'
    raw = candidate/'raw'/args.profile
    state = read(raw/'manifest-extraction.json')
    native = state.get('method') == 'pdf-text-tables'
    raster = is_raster_ocr(state)
    lab7 = load('fresh_lab7', sandbox/'scr/ocr_system/lab7b_curriculum.py')
    lab8 = load('fresh_lab8', sandbox/'scr/ocr_system/lab8b_curriculum_db.py')
    lab7.REQUEST_TIMEOUT = 120
    original = lab7.ollama_chat
    responses = []
    def chat(*positional, **keyword):
        keyword['retries'] = 0
        result = original(*positional, **keyword)
        responses.append(result)
        write(candidate/(args.profile+'.parser-responses.json'), responses)
        return result
    lab7.ollama_chat = chat
    courses, totals = [], []
    config = PROFILES[args.profile]
    for row in state['processed']:
        if native:
            source_record = raw/f"page-{row['pdf_page']}.plan.json"
            if sha(source_record) != row['parsed_sha256'] or sha(raw/f"page-{row['pdf_page']}.txt") != row['native_text_sha256']:
                raise ValueError('fresh native extraction changed')
            result = read(source_record)
        elif raster:
            from scripts.ocr_plan_parser import parse_page
            regions = []
            for segment in row['segments']:
                path = raw/f"page-{row['pdf_page']}-region-{segment['segment']}.md"
                if sha(path) != segment['markdown_sha256']:
                    raise ValueError('fresh raster transcription changed')
                image = raw/f"page-{row['pdf_page']}-region-{segment['segment']}.png"
                if sha(image) != segment['image_sha256']:
                    raise ValueError('fresh raster source crop changed')
                regions.append({**segment, 'text': path.read_text(encoding='utf-8')})
            result = parse_page(regions, config['input'].name, row['pdf_page'], row['printed_book_page'])
            write(raw/f"page-{row['pdf_page']}.plan.json", result)
        else:
            if sha(raw/f"page-{row['pdf_page']}.md") != row['markdown_sha256']:
                raise ValueError('fresh markdown changed')
            result = lab7._text_to_json_chunked([(raw/f"page-{row['pdf_page']}.md").read_text(encoding='utf-8')],
                page_numbers=[row['pdf_page']], source_file=config['input'].name)
        if not result.get('courses'):
            raise ValueError('required plan page parsed no course rows')
        for course in result['courses']:
            course.setdefault('printed_page_number', row['printed_book_page'])
        courses.extend(result['courses'])
        totals.extend(result.get('term_totals') or [])
        write(candidate/(args.profile+f".page-{row['pdf_page']}.parsed.json"), result)
    prediction = candidate/(args.profile+'.fresh-prediction.json')
    write(prediction, {'courses': courses, 'term_totals': totals})
    ingest = prediction
    approvals = []
    if args.font_encoding_only:
        if args.mode != 'reviewed' or not native or not state.get('corrections'):
            raise ValueError('Reviewed encoding provenance missing')
        approvals = [{'kind':'reviewed-font-encoding','path':(raw/'font-encoding-review.json').relative_to(candidate).as_posix(),
                      'sha256':sha(raw/'font-encoding-review.json')}]
    elif args.mode == 'reviewed':
        from scripts.prepare_source_ingest import prepare
        for path in sorted((args.app_root/'data/source_reviews').glob('*-plan-corrections.json')):
            if args.profile not in read(path).get('profiles', {}):
                continue
            target = candidate/(args.profile+'.'+path.stem+'.ingest.json')
            prepare(ingest, sandbox/'data/input'/config['input'].name, path, args.profile, target)
            copied = candidate/'reviewed-inputs'/path.name
            write(copied, read(path))
            approvals.append({'path': copied.relative_to(candidate).as_posix(), 'sha256': sha(copied)})
            ingest = target
    converted, conversion = lab8.convert_lab7b(read(ingest), program_id=config['program_id'],
        program_name=config['program_name'], years=4, total_credits=config['total_credits'],
        target_plan=config['target_plan'], curriculum_version=config['curriculum_version'],
        is_latest=config['is_latest'], plan_variant=config['target_plan'].replace('_', '-'), source_only=True)
    conversion['fidelity_errors'] = lab8.validate_conversion_fidelity(converted, read(ingest))
    output = candidate/'work'/config['out'].name
    output.mkdir(parents=True, exist_ok=False)
    write(output/'curriculum.json', converted)
    lab8.cmd_load(SimpleNamespace(input=str(output/'curriculum.json'), database=str(output/'curriculum.db'), replace=False))
    artifacts = [*raw.glob('*.md'), *raw.glob('*.txt'), *raw.glob('*.plan.json'), *raw.glob('*.png'), raw/'manifest-extraction.json',
                 prediction, ingest, output/'curriculum.json']
    if args.font_encoding_only:
        artifacts += [raw/'font-encoding-review.json', candidate/'reviewed-inputs/font-encoding.json']
    artifacts += list(raw.glob('selection-rule.*'))
    if raster:
        artifacts += list((raw/'raster_ocr_checkpoints').glob('*.json'))
    rejected = raw.parent/(raw.name+'.native-rejected')
    if state.get('hybrid',{}).get('native_attempt',{}).get('status') == 'rejected':
        artifacts += [p for p in rejected.rglob('*') if p.is_file()]
    write(candidate/(args.profile+'.extraction.json'), {
        'status': 'parsed', 'source_sha256': state['dependencies']['source_sha256'],
        'pages': [r['pdf_page'] for r in state['processed']], 'pending_pages': state['pending_requested'],
        'page_paths': [{'pdf_page': r['pdf_page'], 'method': state.get('method', 'vision-OCR'),
                        'ocr_performed': not native, 'reviewed_ingestion': bool(approvals)}
                       for r in state['processed']],
        'material_defects': [flag for r in state['processed'] for flag in r['quality_flags']]
                            + conversion['fidelity_errors'] + conversion.get('warnings', []),
        'artifacts': [{'path': p.relative_to(candidate).as_posix(), 'sha256': sha(p)} for p in artifacts],
        'mode': args.mode, 'reviewed_corrections': approvals, 'conversion': conversion,
        'extraction_method': state.get('method', 'vision-OCR'), 'ocr_performed': not native,
        'normalization_method': 'deterministic-physical-table-parser' if raster else ('native-source-parser' if native else 'LLM-parser'),
        'hybrid': state.get('hybrid'),
        'metadata_origin': 'source-recorded PROFILES code configuration; no database metadata read',
        'limitations': ['academic-plan pages only', 'no source review certification yet',
                        'no full catalog/description/rules/legacy reconstruction', 'prerequisites unknown when table lacks evidence']})


if __name__ == '__main__':
    main()
