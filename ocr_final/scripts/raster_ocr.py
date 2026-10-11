"""Image-only document segmentation. PDF text and curriculum facts are never inputs."""
import hashlib
import io
import json
from pathlib import Path
import re
from html import escape
from html.parser import HTMLParser

from PIL import Image, ImageOps


# Typhoon OCR 1.5 is trained for this published prompt, including HTML tables.
# https://ollama.com/scb10x/typhoon-ocr1.5-3b
PROMPT = """Extract all text from the image.

Instructions:
- Only return the clean Markdown.
- Do not include any explanation or extra text.
- You must include all information on the page.

Formatting Rules:
- Tables: Render tables using <table>...</table> in clean HTML format.
- Equations: Render equations using LaTeX syntax with inline ($...$) and block ($$...$$).
- Images/Charts/Diagrams: Wrap any clearly defined visual areas (e.g. charts, diagrams, pictures) in:

<figure>
Describe the image's main elements (people, objects, text), note any contextual clues (place, event, culture), mention visible text and its meaning, provide deeper analysis when relevant (especially for financial charts, graphs, or documents), comment on style or architecture if relevant, then give a concise overall summary. Describe in Thai.
</figure>
- Page Numbers: Wrap page numbers in <page_number>...</page_number> (e.g., <page_number>14</page_number>).
- Checkboxes: Use ☐ for unchecked and ☑ for checked boxes."""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def horizontal_rules(image):
    """Find long dark runs in raster pixels, without consulting embedded PDF text."""
    width, height = image.size
    mask = ImageOps.grayscale(image).point(lambda p: 1 if p < 135 else 0)
    data = mask.tobytes()
    pattern = re.compile(b'\x01{' + str(max(24, int(width * .4))).encode() + b',}')
    found = []
    for y in range(height):
        for match in pattern.finditer(data[y * width:(y + 1) * width]):
            if found and y <= found[-1]['bottom'] + 1 and abs(match.start() - found[-1]['left']) <= 4 and abs(match.end() - found[-1]['right']) <= 4:
                found[-1]['bottom'] = y
            else:
                found.append({'top': y, 'bottom': y, 'left': match.start(), 'right': match.end()})
    # A single footer rule is not a table. A border must have an aligned peer.
    return [r for r in found if any(
        other is not r and abs(other['left'] - r['left']) <= 5
        and abs(other['right'] - r['right']) <= 5
        and 8 <= abs(other['top'] - r['top']) <= height * .6
        for other in found)]


def raster_regions(png):
    image = Image.open(io.BytesIO(png)).convert('RGB')
    width, height = image.size
    rules = horizontal_rules(image)
    boundaries = sorted({0, height, *[(r['top'] + r['bottom']) // 2 for r in rules]})
    regions = []
    for top, bottom in zip(boundaries, boundaries[1:]):
        if bottom <= top:
            continue
        band = image.crop((0, top, width, bottom))
        ink = ImageOps.grayscale(band).point(lambda p: 255 if p < 235 else 0)
        # Ignore border pixels only when trimming; the saved crop remains original.
        if top:
            ink.paste(0, (0, 0, width, min(3, band.height)))
        if bottom < height:
            ink.paste(0, (0, max(0, band.height - 3), width, band.height))
        extent = ink.getbbox()
        if not extent:
            continue
        left, ink_top, right, ink_bottom = extent
        box = (max(0, left - 12), top + max(0, ink_top - 8),
               min(width, right + 12), top + min(band.height, ink_bottom + 8))
        crop = image.crop(box)
        buffer = io.BytesIO()
        crop.save(buffer, format='PNG')
        regions.append({'png': buffer.getvalue(), 'box': box,
            'band': (0, top, width, bottom),
            'kind': 'table-band' if top not in (0, height) and bottom not in (0, height) else 'page-context'})
    if not regions:
        raise ValueError('Rendered page has no visible ink; preserve source and inspect it')
    return regions


def cell_regions(png):
    """Detect the three physical columns from vertical raster borders."""
    image = Image.open(io.BytesIO(png)).convert('RGB')
    width, height = image.size
    mask = ImageOps.grayscale(image).point(lambda p: 1 if p < 135 else 0).transpose(Image.Transpose.TRANSPOSE)
    data = mask.tobytes()
    long_run = re.compile(b'\x01{' + str(max(12, int(height * .75))).encode() + b',}')
    borders = []
    for x in range(width):
        if long_run.search(data[x * height:(x + 1) * height]):
            if borders and x <= borders[-1][-1] + 1:
                borders[-1].append(x)
            else:
                borders.append([x])
    positions = [(r[0] + r[-1]) // 2 for r in borders]
    if len(positions) != 4:
        raise ValueError('Cannot resolve three raster columns; retain row and inspect source image')
    result = []
    for left, right in zip(positions, positions[1:]):
        box = (left + 3, 3, right - 2, height - 3)
        if box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError('Raster column is too narrow to transcribe safely')
        buffer = io.BytesIO()
        image.crop(box).save(buffer, format='PNG')
        result.append({'png': buffer.getvalue(), 'box': box})
    return result


class LiteralText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {'br', 'tr', 'td', 'th', 'p'}:
            self.parts.append('\n')

    def handle_data(self, text):
        self.parts.append(text)


def literal_text(text):
    if re.search(r'<(?:table|br|td|p)\b', text, re.I):
        parser = LiteralText()
        parser.feed(text)
        return '\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())
    return text.strip()


def needs_cell_transcription(text):
    from scripts.ocr_plan_parser import table_rows
    from scripts.source_native import CODE, CREDIT
    if not CODE.search(text) and not CREDIT.search(text):
        return False
    rows = table_rows(text)
    return (len(rows) != 1 or len(rows[0]) != 3 or not CODE.search(rows[0][0]) or
            bool(CREDIT.search(rows[0][1])) or not CREDIT.search(rows[0][2]))


def extract_regions(png, output, lab7, *, page_number, source_file, model_digest):
    """Checkpoints are per physical band, so an interrupted page resumes its rows."""
    regions = raster_regions(png)
    cache = output / 'raster_ocr_checkpoints'
    cache.mkdir(exist_ok=True)
    records, texts = [], []
    for ordinal, region in enumerate(regions, 1):
        image_hash = hashlib.sha256(region['png']).hexdigest()
        identity = {'format': 1, 'image_sha256': image_hash, 'source_file': source_file,
            'pdf_page': page_number, 'box': list(region['box']), 'band': list(region['band']),
            'kind': region['kind'], 'prompt': PROMPT, 'model': lab7.MODEL_OCR,
            'model_digest': model_digest, 'host': lab7.OLLAMA_HOST,
            'num_ctx': lab7.OCR_NUM_CTX, 'num_predict': lab7.OCR_NUM_PREDICT,
            'temperature': lab7.OCR_TEMPERATURE}
        checkpoint = cache / (digest(identity) + '.json')
        image_path = output / f'page-{page_number}-region-{ordinal}.png'
        markdown_path = output / f'page-{page_number}-region-{ordinal}.md'
        image_path.write_bytes(region['png'])
        reused = checkpoint.exists()
        if reused:
            stored = json.loads(checkpoint.read_text(encoding='utf-8'))
            text = stored['markdown']
            if stored['identity'] != identity or hashlib.sha256(text.encode()).hexdigest() != stored['markdown_sha256']:
                raise ValueError('Raster OCR checkpoint changed; preserve it and use a new output')
        else:
            print(f'PDF {page_number}: image band {ordinal}/{len(regions)}', flush=True)
            text = lab7.ollama_chat(lab7.MODEL_OCR,
                [{'role': 'user', 'content': PROMPT}], images=[region['png']],
                temperature=lab7.OCR_TEMPERATURE, retries=lab7.OCR_RETRIES,
                num_ctx=lab7.OCR_NUM_CTX, num_predict=lab7.OCR_NUM_PREDICT)
            if not text.strip():
                raise ValueError(f'OCR returned empty text for nonempty image band {ordinal}')
            stored = {'identity': identity, 'markdown': text,
                'markdown_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'status': 'image transcription; independent source review still required'}
            partial = checkpoint.with_suffix('.partial')
            partial.write_bytes((json.dumps(stored, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
            partial.replace(checkpoint)
        row_text = text
        cells = []
        if needs_cell_transcription(text):
            for column, cell in enumerate(cell_regions(region['png']), 1):
                cell_hash = hashlib.sha256(cell['png']).hexdigest()
                cell_identity = {**identity, 'image_sha256': cell_hash,
                    'kind': 'physical-column', 'column': column, 'row_crop_box': list(cell['box'])}
                cell_checkpoint = cache / (digest(cell_identity) + '.json')
                cell_image = output / f'page-{page_number}-region-{ordinal}-cell-{column}.png'
                cell_image.write_bytes(cell['png'])
                cell_reused = cell_checkpoint.exists()
                if cell_reused:
                    saved_cell = json.loads(cell_checkpoint.read_text(encoding='utf-8'))
                    cell_text = saved_cell['markdown']
                    if (saved_cell['identity'] != cell_identity or
                            hashlib.sha256(cell_text.encode()).hexdigest() != saved_cell['markdown_sha256']):
                        raise ValueError('Cell OCR checkpoint changed; preserve it and use a new output')
                else:
                    print(f'PDF {page_number}: band {ordinal}, physical column {column}/3', flush=True)
                    cell_text = lab7.ollama_chat(lab7.MODEL_OCR,
                        [{'role': 'user', 'content': PROMPT}], images=[cell['png']],
                        temperature=lab7.OCR_TEMPERATURE, retries=lab7.OCR_RETRIES,
                        num_ctx=lab7.OCR_NUM_CTX, num_predict=lab7.OCR_NUM_PREDICT)
                    if not cell_text.strip():
                        raise ValueError('Nonempty physical column returned empty OCR')
                    saved_cell = {'identity': cell_identity, 'markdown': cell_text,
                        'markdown_sha256': hashlib.sha256(cell_text.encode()).hexdigest()}
                    partial = cell_checkpoint.with_suffix('.partial')
                    partial.write_bytes((json.dumps(saved_cell, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
                    partial.replace(cell_checkpoint)
                (output / f'page-{page_number}-region-{ordinal}-cell-{column}.md').write_bytes(cell_text.encode())
                cells.append({'column': column, 'row_crop_box': list(cell['box']),
                    'image_sha256': cell_hash, 'markdown_sha256': saved_cell['markdown_sha256'],
                    'checkpoint': cell_checkpoint.relative_to(output).as_posix(),
                    'reused': cell_reused, 'literal': literal_text(cell_text)})
            (output / f'page-{page_number}-region-{ordinal}-row-raw.md').write_bytes(row_text.encode())
            text = '<table><tr>' + ''.join('<td>' + escape(c['literal']).replace('\n', '<br/>') + '</td>' for c in cells) + '</tr></table>'
        markdown_path.write_bytes(text.encode('utf-8'))
        records.append({'segment': ordinal, 'original_pixel_box': list(region['box']),
            'original_pixel_band': list(region['band']), 'kind': region['kind'],
            'coordinate_space': 'original rendered full-page pixels',
            'image_sha256': image_hash, 'markdown_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'row_raw_sha256': stored['markdown_sha256'], 'cell_transcriptions': cells,
            'checkpoint': checkpoint.relative_to(output).as_posix(), 'reused': reused and all(c['reused'] for c in cells)})
        texts.append(text)
    return '\n\n'.join(texts), records
