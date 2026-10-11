"""Resumable raw page OCR, deliberately separate from study-plan normalization."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time
import requests
import fitz
import io
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def select_pages(manifest):
    pages = manifest['pages']
    numbers = [p['pdf_page'] for p in pages]
    if any(type(n) is not int for n in numbers) or len(set(numbers)) != len(numbers) or sorted(numbers) != list(range(1, len(numbers)+1)):
        raise ValueError('Manifest must inventory every physical page exactly once')
    if any(p['decision'] not in {'include', 'skip', 'unreviewed'} for p in pages):
        raise ValueError('Invalid selection decision')
    return {decision: [p['pdf_page'] for p in pages if p['decision'] == decision]
            for decision in ('include', 'skip', 'unreviewed')}


def requested_pages(selection, pages):
    if not pages:
        return selection['include'][:]
    if any(p not in selection['include'] for p in pages):
        raise ValueError('Requested pages must have a reviewed include decision')
    return [p for p in selection['include'] if p in set(pages)]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def write_markdown(path, text):
    # Hash exactly the stored bytes, not pre-Windows-newline-conversion text.
    path.write_bytes(text.encode('utf-8'))
    return sha(path)


def quality_flags(text, segment_count):
    # Diagnostics only: transport and checkpoints cannot certify source fidelity.
    flags = ['overlapping_segments_require_review'] if segment_count > 1 else []
    instructions = ('extract all text from the image', 'only return the clean markdown',
                    'formatting rules:', 'do not include any explanation')
    if sum(phrase in text.lower() for phrase in instructions) >= 3:
        flags.append('instruction_echo_suspected')
    if not text.strip():
        flags.append('empty_extraction')
    elif not re.search(r'[\u0e00-\u0e7f]', text):
        flags.append('no_thai_text_requires_review')
    return flags


def replace_checkpoint(partial, checkpoint):
    # A concurrent Windows reader can briefly deny replacement. Keep it bounded.
    for attempt in range(5):
        try:
            partial.replace(checkpoint)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05)


def validate_completed(state, output):
    for row in state['processed']:
        number = row['pdf_page']
        if sha(output/f'page-{number}.md') != row['markdown_sha256']:
            raise ValueError('Completed markdown changed; preserve evidence and use a new output')
        if sha(output/f'page-{number}.png') != row['image_sha256']:
            raise ValueError('Completed page image changed; refuse resume')


def segment_image(png, count, crop_box=None, ink_threshold=None):
    image = Image.open(io.BytesIO(png))
    width, height = image.size
    left, origin_top, right, origin_bottom = crop_box or (0, 0, width, height)
    if not (0 <= left < right <= width and 0 <= origin_top < origin_bottom <= height):
        raise ValueError('Crop must be a nonempty box inside the original rendered page')
    height = origin_bottom - origin_top
    segments = []
    for index in range(count):
        # Preserve original coordinates; overlap is explicit, never silently deduplicated.
        top = max(0, height * index // count - (40 if index else 0))
        bottom = min(height, height * (index + 1) // count + (40 if index + 1 < count else 0))
        box = (left, origin_top + top, right, origin_top + bottom)
        buffer = io.BytesIO()
        cropped = image.crop(box)
        if ink_threshold is not None:
            if not 0 <= ink_threshold <= 255:
                raise ValueError('Ink threshold must be between 0 and 255')
            cropped = cropped.convert('L').point(lambda pixel: 0 if pixel < ink_threshold else 255).convert('RGB')
        cropped.save(buffer, format='PNG')
        segments.append((buffer.getvalue(), box))
    return segments


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-job', type=Path, action='append', default=[])
    parser.add_argument('--reuse-page-job', type=Path, action='append', default=[])
    parser.add_argument('--continue-on-error', action='store_true', help='Record failed pages and attempt independent remaining pages')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--cached-only', action='store_true', help='Verify reusable pages only; all others remain pending')
    parser.add_argument('--max-pages', type=int, help='Park cleanly after this many pages; remaining pages stay pending')
    parser.add_argument('--page', type=int, action='append', help='Only attempt these reviewed include pages (repeatable)')
    parser.add_argument('--segments', type=int, choices=(1, 2), default=1,
                        help='Experimental overlapping vertical crops; original coordinates retained')
    parser.add_argument('--prompt-file', type=Path, help='Explicit isolated OCR prompt override; default prompt remains unchanged')
    parser.add_argument('--crop-box', type=int, nargs=4, metavar=('LEFT', 'TOP', 'RIGHT', 'BOTTOM'),
                        help='Experimental crop in original rendered pixels; full page retained for context')
    parser.add_argument('--region-context', help='Reviewed heading/context and reason for this page-specific region; metadata only, never added to the OCR prompt')
    parser.add_argument('--ink-threshold', type=int, help='Experimental luminance threshold 0..255; original image preserved')
    args = parser.parse_args()
    source = args.source_root.resolve()
    output = args.output.resolve()
    if output == source or source in output.parents or output == ROOT or ROOT in output.parents:
        raise ValueError('Output must be outside source and repository applications')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    selection = select_pages(manifest)
    requested = requested_pages(selection, args.page)
    if args.max_pages is not None and args.max_pages < 1:
        raise ValueError('--max-pages must be positive')
    if args.ink_threshold is not None and not 0 <= args.ink_threshold <= 255:
        raise ValueError('--ink-threshold must be between 0 and 255')
    pdf = source/'data/input'/manifest['source_file']
    if sha(pdf) != manifest['source_sha256']:
        raise ValueError('Source no longer matches reviewed selection manifest')
    spec = importlib.util.spec_from_file_location('manifest_lab7', ROOT/'scr/ocr_system/lab7b_curriculum.py')
    lab7 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab7)
    if args.prompt_file:
        prompt = args.prompt_file.read_text(encoding='utf-8').strip()
        if not prompt:
            raise ValueError('OCR prompt override must not be empty')
        lab7.TYPHOON_PROMPT = prompt
    response = requests.get(lab7.OLLAMA_HOST.rstrip('/')+'/api/tags', timeout=15)
    response.raise_for_status()
    models = response.json()['models']
    model = next((m for m in models if any(
        name == lab7.MODEL_OCR or name == lab7.MODEL_OCR + ':latest'
        for name in (m.get('name'), m.get('model')))), None)
    if not model or not model.get('digest'):
        raise ValueError('Installed OCR model digest unavailable; cannot establish reuse identity')
    renderer = {'library': 'PyMuPDF', 'version': fitz.VersionBind, 'dpi': lab7.DPI,
                'segments': args.segments, 'overlap_pixels': 40 if args.segments > 1 else 0,
                'crop_box': args.crop_box,
                'region_context': args.region_context,
                'region_scope': 'page-specific experiment' if args.crop_box else 'full page',
                'ink_threshold': args.ink_threshold,
                'load_pages_sha256': digest(__import__('inspect').getsource(lab7.load_pages))}
    generation = {'num_ctx': lab7.OCR_NUM_CTX, 'num_predict': lab7.OCR_NUM_PREDICT,
                  'temperature': lab7.OCR_TEMPERATURE, 'retries': lab7.OCR_RETRIES}
    dependencies = {'source_sha256': sha(pdf), 'manifest_sha256': sha(args.manifest),
                    'extractor_sha256': sha(ROOT/'scr/ocr_system/lab7b_curriculum.py'),
                    'runner_sha256': sha(Path(__file__)), 'model': lab7.MODEL_OCR,
                    'host': lab7.OLLAMA_HOST, 'dpi': lab7.DPI, 'prompt': lab7.TYPHOON_PROMPT,
                    'num_ctx': lab7.OCR_NUM_CTX, 'num_predict': lab7.OCR_NUM_PREDICT,
                    'temperature': lab7.OCR_TEMPERATURE, 'model_digest': model['digest'],
                    'prompt_sha256': hashlib.sha256(lab7.TYPHOON_PROMPT.encode()).hexdigest(),
                    'renderer': renderer, 'renderer_sha256': digest(renderer),
                    'generation_sha256': digest(generation)}
    checkpoint = output/'manifest-extraction.json'
    if args.resume:
        state = json.loads(checkpoint.read_text(encoding='utf-8'))
        if state['dependencies'] != dependencies:
            raise ValueError('Dependencies changed; preserve output and use a new directory')
        if state.get('requested_pages') != requested:
            raise ValueError('Requested scope changed; use a new output directory')
        validate_completed(state, output)
    else:
        output.mkdir(parents=True, exist_ok=False)
        state = {'scope': 'raw reviewed-include page extraction only; no evaluation labels or DB ingestion',
                 'dependencies': dependencies, 'selection': selection, 'processed': [], 'failed': [],
                 'running': None, 'reuse_jobs': [], 'requested_pages': requested}
    cache = output/'ocr_page_checkpoints'
    cache.mkdir(exist_ok=True)
    for prior_job in args.reuse_page_job:
        previous = json.loads((prior_job/'manifest-extraction.json').read_text(encoding='utf-8'))
        # Runner changes may alter orchestration, never OCR checkpoint identity.
        for field in ('source_sha256', 'manifest_sha256', 'extractor_sha256', 'model', 'host', 'dpi', 'prompt', 'num_ctx', 'num_predict', 'temperature', 'model_digest', 'renderer_sha256', 'generation_sha256'):
            if previous['dependencies'].get(field) != dependencies[field]:
                raise ValueError(f'Reusable page job changed {field}')
        for old_cache in (prior_job/'ocr_page_checkpoints').glob('*.json'):
            entry = json.loads(old_cache.read_text(encoding='utf-8'))
            if hashlib.sha256(entry['markdown'].encode()).hexdigest() != entry.get('markdown_sha256'):
                raise ValueError('Corrupt page-job checkpoint')
            shutil.copy2(old_cache, cache/old_cache.name)
        state['reuse_jobs'].append({'page_job': str(prior_job), 'identity': 'source/model/configuration/extractor/content checked; image checked before reuse'})
    def save():
        state['pending'] = [p for p in selection['include'] if p not in {r['pdf_page'] for r in state['processed']}]
        state['pending_requested'] = [p for p in requested if p in state['pending']]
        partial = checkpoint.with_suffix('.partial')
        partial.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        replace_checkpoint(partial, checkpoint)
    for job in args.reuse_job:
        old = json.loads((job/'reconstruction.json').read_text(encoding='utf-8'))
        if any(old.get('ocr_identity', {}).get(k) != dependencies[k]
               for k in ('model_digest', 'renderer_sha256', 'generation_sha256')):
            raise ValueError('Reconstruction lacks matching model/renderer/generation identity')
        matches = [v for k,v in old['dependencies'].items() if Path(k).name == pdf.name]
        if matches != [sha(pdf)]:
            raise ValueError('Reuse job lacks matching source PDF hash')
        copied = 0
        for previous in (job/'app/work').glob('lab8b_*/lab7b/ocr_page_checkpoints/*.json'):
            data = json.loads(previous.read_text(encoding='utf-8'))
            identity = data.get('identity', {})
            wanted = {'source_file': pdf.name, 'model': lab7.MODEL_OCR, 'host': lab7.OLLAMA_HOST,
                      'prompt': lab7.TYPHOON_PROMPT, 'num_ctx': lab7.OCR_NUM_CTX,
                      'num_predict': lab7.OCR_NUM_PREDICT, 'temperature': lab7.OCR_TEMPERATURE}
            if not all(identity.get(k) == v for k,v in wanted.items()):
                continue
            if identity.get('pdf_page') not in selection['include']:
                continue
            if hashlib.sha256(data['markdown'].encode()).hexdigest() != data.get('markdown_sha256'):
                raise ValueError('Corrupt reusable OCR checkpoint')
            target = cache/previous.name
            if target.exists() and sha(target) != sha(previous):
                raise ValueError('Conflicting checkpoint content')
            shutil.copy2(previous, target)
            copied += 1
        state['reuse_jobs'].append({'job': str(job), 'candidate_checkpoints': copied,
                                   'policy': 'image/config identity still checked by extractor before use'})
    save()
    done = {r['pdf_page'] for r in state['processed']}
    count = 0
    for number in requested:
        if number in done:
            continue
        if args.cached_only and not any(json.loads(p.read_text(encoding='utf-8')).get('identity', {}).get('pdf_page') == number
                                        for p in cache.glob('*.json')):
            continue
        if args.max_pages is not None and count >= args.max_pages:
            break
        state['running'] = number
        count += 1
        save()
        started = time.perf_counter()
        transport = []
        original_post = requests.post
        def capture_post(*positional, **keyword):
            response = original_post(*positional, **keyword)
            payload = keyword.get('json', {})
            request_summary = {k: v for k, v in payload.items() if k != 'messages'}
            request_summary['messages'] = [
                {k: v for k, v in m.items() if k != 'images'} | {
                    'image_count': len(m.get('images', [])),
                    'encoded_image_sha256': [hashlib.sha256(im.encode()).hexdigest()
                                              for im in m.get('images', [])]}
                for m in payload.get('messages', [])]
            try:
                response_body = response.json()
            except (ValueError, TypeError):
                response_body = {'non_json_body': response.text[:4000]}
            transport.append({'status': response.status_code, 'request': request_summary,
                              'response': response_body,
                              'error_body': response.text[:4000] if not response.ok else None})
            return response
        try:
            images = lab7.load_pages(str(pdf), str(number))
            (output/f'page-{number}.png').write_bytes(images[0])
            state['running_image_sha256'] = hashlib.sha256(images[0]).hexdigest()
            save()
            cached_names = {p.name for p in cache.glob('*.json')}
            requests.post = capture_post
            parts = []
            crops = []
            for index, (png, box) in enumerate(segment_image(images[0], args.segments, args.crop_box, args.ink_threshold)
                    if args.segments > 1 or args.crop_box or args.ink_threshold is not None else [(images[0], None)]):
                (output/f'page-{number}-segment-{index+1}.png').write_bytes(png)
                state['running_segment'] = {'segment': index + 1, 'original_pixel_box': box,
                                           'image_sha256': hashlib.sha256(png).hexdigest()}
                save()
                raw = lab7.extract_vlm_pages([png], output, page_numbers=[number], source_file=pdf.name)[0]
                crops.append({'segment': index + 1, 'original_pixel_box': box,
                              'heading_context': args.region_context,
                              'coordinate_space': 'original rendered full-page pixels',
                              'image_sha256': hashlib.sha256(png).hexdigest()})
                write_markdown(output/f'page-{number}-segment-{index+1}.md', raw)
                parts.append(raw)
            text = '\n\n<!-- overlapping source segment; review duplicates before parsing -->\n\n'.join(parts)
            new_names = {p.name for p in cache.glob('*.json')}
            markdown_hash = write_markdown(output/f'page-{number}.md', text)
            state['processed'].append({'pdf_page': number,
                'printed_book_page': manifest['pages'][number-1]['printed_book_page'],
                'seconds': round(time.perf_counter()-started, 2), 'reused': new_names == cached_names,
                'image_sha256': hashlib.sha256(images[0]).hexdigest(),
                'transport': transport,
                'segments': crops,
                'markdown_sha256': markdown_hash,
                'quality_flags': quality_flags(text, args.segments),
                'interpretation': 'raw extraction, not independently verified field accuracy'})
        except Exception as exc:
            state['failed'].append({'pdf_page': number, 'error': str(exc), 'transport': transport,
                'image_sha256': state.get('running_image_sha256'),
                'segment': state.get('running_segment'),
                'seconds': round(time.perf_counter()-started, 2)})
            state['running'] = None
            save()
            if not args.continue_on_error:
                raise
            continue
        finally:
            requests.post = original_post
        state['running'] = None
        state['running_segment'] = None
        save()
    state['source_unchanged'] = sha(pdf) == dependencies['source_sha256']
    state['complete_included_selection'] = not state['pending']
    state['complete_requested_selection'] = not state['pending_requested']
    save()
    print(json.dumps({'processed': len(state['processed']), 'pending': len(state['pending']),
                      'failed_attempts': len(state['failed']), 'skipped': len(selection['skip']),
                      'unreviewed': len(selection['unreviewed'])}))
    return int(bool(state['pending_requested']) and args.continue_on_error)


if __name__ == '__main__':
    raise SystemExit(main())
