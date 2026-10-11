import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from PIL import Image, ImageDraw

from scripts.raster_ocr import extract_regions, horizontal_rules, raster_regions


def document():
    image = Image.new('RGB', (800, 900), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((350, 30), 'Year 3 Semester 1', fill='black')
    for y in (100, 180, 280, 520, 610):
        draw.line((80, y, 720, y), fill='black', width=2)
    for x in (80, 190, 550, 720):
        draw.line((x, 100, x, 610), fill='black', width=2)
    draw.text((100, 200), '06000001', fill='black')
    draw.text((220, 220), 'NAME ONE', fill='black')
    draw.text((220, 310), 'NAME TWO', fill='black')
    draw.text((220, 450), 'NAME THREE IN SAME MERGED CELL', fill='black')
    draw.text((220, 555), 'FINAL ROW', fill='black')
    draw.line((80, 780, 720, 780), fill='black', width=2)
    draw.text((90, 810), 'FOOTNOTE', fill='black')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


class RasterOCRTests(unittest.TestCase):
    def test_real_borders_keep_merged_cell_and_final_row(self):
        regions = raster_regions(document())
        bands = [r['band'] for r in regions]
        self.assertEqual(len(regions), 6)
        self.assertEqual(bands[3], (0, 280, 800, 520))
        self.assertEqual(bands[4], (0, 520, 800, 610))
        # Blank whitespace between the table and footer can be omitted; ink
        # bands must retain their original order and may never overlap.
        self.assertTrue(all(a[3] <= b[1] for a, b in zip(bands, bands[1:])))
        self.assertEqual(bands[0][1], 0)
        self.assertEqual(bands[-1][3], 900)

    def test_footer_rule_alone_does_not_split_document(self):
        image = Image.new('RGB', (800, 900), 'white')
        draw = ImageDraw.Draw(image)
        draw.text((100, 200), 'VISIBLE TEXT', fill='black')
        draw.line((80, 780, 720, 780), fill='black', width=2)
        self.assertEqual(horizontal_rules(image), [])

    def test_blank_page_is_not_a_successful_extraction(self):
        buffer = io.BytesIO()
        Image.new('RGB', (800, 900), 'white').save(buffer, format='PNG')
        with self.assertRaises(ValueError):
            raster_regions(buffer.getvalue())

    def test_interrupted_page_reuses_completed_bands_only(self):
        lab = SimpleNamespace(MODEL_OCR='ocr', OLLAMA_HOST='http://localhost',
            OCR_NUM_CTX=8192, OCR_NUM_PREDICT=1024, OCR_TEMPERATURE=0, OCR_RETRIES=0,
            ollama_chat=Mock(side_effect=['first', 'second', RuntimeError('interrupted')]))
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            with self.assertRaises(RuntimeError):
                extract_regions(document(), out, lab, page_number=27, source_file='source.pdf', model_digest='v1')
            self.assertEqual(len(list((out/'raster_ocr_checkpoints').glob('*.json'))), 2)
            lab.ollama_chat = Mock(return_value='remaining')
            text, regions = extract_regions(document(), out, lab, page_number=27, source_file='source.pdf', model_digest='v1')
            self.assertEqual(lab.ollama_chat.call_count, 4)
            self.assertEqual([r['reused'] for r in regions], [True, True, False, False, False, False])
            self.assertTrue(text.startswith('first\n\nsecond'))
            # A different model digest must transcribe every band again.
            lab.ollama_chat.reset_mock()
            extract_regions(document(), out, lab, page_number=27, source_file='source.pdf', model_digest='v2')
            self.assertEqual(lab.ollama_chat.call_count, 6)

    def test_changed_checkpoint_text_cannot_be_used(self):
        lab = SimpleNamespace(MODEL_OCR='ocr', OLLAMA_HOST='http://localhost',
            OCR_NUM_CTX=8192, OCR_NUM_PREDICT=1024, OCR_TEMPERATURE=0, OCR_RETRIES=0,
            ollama_chat=Mock(return_value='original'))
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            extract_regions(document(), out, lab, page_number=27, source_file='source.pdf', model_digest='v1')
            checkpoint = next((out/'raster_ocr_checkpoints').glob('*.json'))
            record = json.loads(checkpoint.read_text())
            record['markdown'] = 'changed'
            checkpoint.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                extract_regions(document(), out, lab, page_number=27, source_file='source.pdf', model_digest='v1')
