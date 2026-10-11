import unittest
from scripts.extract_manifest_pages import select_pages, requested_pages, segment_image
import io
from PIL import Image
import tempfile
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock
from scripts import extract_manifest_pages as runner


def fake_load_pages(path, page):
    return [b'png']


class ManifestSelectionTests(unittest.TestCase):
    def test_instruction_echo_is_diagnostic_not_source_verification(self):
        text = 'Extract all text from the image. Only return the clean Markdown. Formatting Rules:'
        self.assertIn('instruction_echo_suspected', runner.quality_flags(text, 2))
        self.assertEqual(runner.quality_flags('06036147 สหกิจศึกษา 6(0-35-0)', 1), [])
        self.assertEqual(runner.quality_flags('เนื้อหา', 2), ['overlapping_segments_require_review'])

    def test_stored_markdown_hash_survives_real_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            text = 'ชื่อวิชา\nsecond line\n'
            hashed = runner.write_markdown(output/'page-1.md', text)
            (output/'page-1.png').write_bytes(b'image')
            self.assertEqual((output/'page-1.md').read_bytes(), text.encode('utf-8'))
            runner.validate_completed({'processed': [{'pdf_page': 1, 'markdown_sha256': hashed,
                'image_sha256': runner.sha(output/'page-1.png')}]}, output)

    def test_windows_reader_replacement_is_bounded(self):
        partial, checkpoint = Mock(), Mock()
        partial.replace.side_effect = [PermissionError('reader'), None]
        with patch.object(runner.time, 'sleep'):
            runner.replace_checkpoint(partial, checkpoint)
        self.assertEqual(partial.replace.call_count, 2)
        partial.replace.reset_mock()
        partial.replace.side_effect = PermissionError('persistent lock')
        with patch.object(runner.time, 'sleep'), self.assertRaises(PermissionError):
            runner.replace_checkpoint(partial, checkpoint)
        self.assertEqual(partial.replace.call_count, 5)

    def test_resume_rejects_changed_completed_content(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output/'page-1.md').write_bytes(b'markdown')
            (output/'page-1.png').write_bytes(b'image')
            row = {'pdf_page': 1, 'markdown_sha256': runner.sha(output/'page-1.md'),
                   'image_sha256': runner.sha(output/'page-1.png')}
            runner.validate_completed({'processed': [row]}, output)
            (output/'page-1.md').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                runner.validate_completed({'processed': [row]}, output)
    def test_failure_consumes_page_budget_and_keeps_pending_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'source'
            (source/'data/input').mkdir(parents=True)
            pdf = source/'data/input/book.pdf'
            pdf.write_bytes(b'pdf')
            manifest = root/'manifest.json'
            manifest.write_text(json.dumps({'source_file': 'book.pdf', 'source_sha256': runner.sha(pdf),
                'pages': [{'pdf_page': p, 'printed_book_page': p, 'decision': 'include'} for p in (1, 2)]}))
            lab = SimpleNamespace(MODEL_OCR='model', OLLAMA_HOST='http://localhost:11434', DPI=150,
                TYPHOON_PROMPT='prompt', OCR_NUM_CTX=8192, OCR_NUM_PREDICT=2048,
                OCR_TEMPERATURE=0.1, OCR_RETRIES=2, load_pages=fake_load_pages,
                extract_vlm_pages=Mock(side_effect=RuntimeError('failed transport')))
            args = ['runner', '--manifest', str(manifest), '--source-root', str(source),
                    '--output', str(root/'output'), '--max-pages', '1', '--continue-on-error',
                    '--region-context', 'Reviewed heading; page-specific region']
            response = Mock()
            response.json.return_value = {'models': [{'name': 'model', 'digest': 'digest'}]}
            with patch('sys.argv', args), patch.object(runner.importlib.util, 'module_from_spec', return_value=lab), \
                 patch.object(runner.importlib.util, 'spec_from_file_location') as spec, \
                 patch.object(runner.requests, 'get', return_value=response):
                self.assertEqual(runner.main(), 1)
            state = json.loads((root/'output/manifest-extraction.json').read_text())
            self.assertEqual(lab.extract_vlm_pages.call_count, 1)
            self.assertEqual(state['pending_requested'], [1, 2])
            self.assertEqual(len(state['failed']), 1)
            self.assertTrue(state['source_unchanged'])
            self.assertEqual(state['dependencies']['renderer']['region_context'], 'Reviewed heading; page-specific region')
            self.assertEqual(state['dependencies']['prompt'], 'prompt')
    def test_segments_preserve_coordinates_and_overlap(self):
        buffer = io.BytesIO()
        Image.new('RGB', (100, 400)).save(buffer, format='PNG')
        pieces = segment_image(buffer.getvalue(), 2)
        self.assertEqual([box for _, box in pieces], [(0, 0, 100, 240), (0, 160, 100, 400)])
    def test_crop_coordinates_are_original_not_relative(self):
        buffer = io.BytesIO()
        Image.new('RGB', (200, 600)).save(buffer, format='PNG')
        pieces = segment_image(buffer.getvalue(), 2, (20, 100, 180, 500))
        self.assertEqual([box for _, box in pieces], [(20, 100, 180, 340), (20, 260, 180, 500)])
        self.assertEqual(Image.open(io.BytesIO(pieces[0][0])).size, (160, 240))
        for box in ((-1, 0, 100, 200), (0, 0, 201, 200), (20, 100, 20, 500)):
            with self.assertRaises(ValueError):
                segment_image(buffer.getvalue(), 1, box)
    def test_empty_and_non_thai_output_are_only_review_flags(self):
        self.assertIn('empty_extraction', runner.quality_flags('', 1))
        self.assertIn('no_thai_text_requires_review', runner.quality_flags('Return Markdown only.', 1))
    def test_threshold_removes_light_ink_without_changing_original(self):
        buffer = io.BytesIO()
        original = Image.new('RGB', (20, 20), (250, 200, 170))
        original.putpixel((0, 0), (20, 20, 20))
        original.save(buffer, format='PNG')
        content = buffer.getvalue()
        cropped, _ = segment_image(content, 1, None, 170)[0]
        processed = Image.open(io.BytesIO(cropped))
        self.assertEqual(processed.getpixel((0, 0)), (0, 0, 0))
        self.assertEqual(processed.getpixel((1, 1)), (255, 255, 255))
        self.assertEqual(Image.open(io.BytesIO(content)).getpixel((1, 1)), (250, 200, 170))
        with self.assertRaises(ValueError):
            segment_image(content, 1, None, 256)
    def test_subset_preserves_manifest_order_and_deduplicates(self):
        selection = {'include': [93, 238, 257], 'skip': [], 'unreviewed': [94]}
        self.assertEqual(requested_pages(selection, [257, 93, 93]), [93, 257])
        self.assertEqual(requested_pages(selection, None), [93, 238, 257])
        with self.assertRaises(ValueError):
            requested_pages(selection, [94])
    def test_unreviewed_is_not_skipped(self):
        manifest = {'pages':[{'pdf_page':1,'decision':'include'},
                             {'pdf_page':2,'decision':'unreviewed'},
                             {'pdf_page':3,'decision':'skip'}]}
        self.assertEqual(select_pages(manifest), {'include':[1], 'skip':[3], 'unreviewed':[2]})

    def test_duplicate_or_missing_physical_page_fails(self):
        for numbers in ([1,1], [1,3], [2]):
            with self.assertRaises(ValueError):
                select_pages({'pages':[{'pdf_page':p,'decision':'include'} for p in numbers]})

    def test_invalid_decision_fails(self):
        with self.assertRaises(ValueError):
            select_pages({'pages':[{'pdf_page':1,'decision':'probably blank'}]})
