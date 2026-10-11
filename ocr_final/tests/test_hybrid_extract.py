"""Route disclosure and preservation when PDF text needs image OCR fallback."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.hybrid_extract import run, preserve_native_attempt


class HybridExtractionTests(unittest.TestCase):
    def test_native_renderer_string_is_compatible_with_fresh_parser(self):
        from scripts.parse_fresh_build import is_raster_ocr
        self.assertFalse(is_raster_ocr({'method':'pdf-text-tables','dependencies':{'renderer':'PyMuPDF'}}))
        self.assertTrue(is_raster_ocr({'method':'vision-OCR','dependencies':{'renderer':{'layout':'raster-rows'}}}))

    def fixture(self, root):
        source = root/'source'; source.mkdir()
        pdf = source/'source.pdf'; pdf.write_bytes(b'test-only-source')
        selection = source/'selection.json'; selection.write_text('{}')
        return pdf, selection, source

    def native(self, output, failed=False):
        output.mkdir()
        state = {'method':'pdf-text-tables', 'processed':[], 'pending_requested':[],
                 'failed':[{'pdf_page':1,'error':'unreadable source font'}] if failed else []}
        (output/'manifest-extraction.json').write_text(json.dumps(state))
        (output/'original.txt').write_text('native failure evidence')
        return state

    def test_readable_pdf_never_calls_ocr(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);pdf,selection,source=self.fixture(root);output=root/'fresh'
            with patch('scripts.hybrid_extract.extract',side_effect=lambda *a:self.native(output)), \
                    patch('scripts.hybrid_extract.subprocess.run') as request:
                result=run(pdf,[1],output,selection,source)
            request.assert_not_called()
            self.assertEqual(result['hybrid']['selected_method'],'pdf-text-tables')

    def test_failed_native_is_retained_and_not_fed_to_ocr(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);pdf,selection,source=self.fixture(root);output=root/'fresh'
            def image_ocr(command, **kwargs):
                self.assertNotIn('--reuse-job',command)
                self.assertNotIn('--resume',command)
                self.assertEqual(command[command.index('--source-root')+1],str(source))
                self.assertFalse(output.exists())
                self.assertEqual((root/'fresh.native-rejected/original.txt').read_text(),'native failure evidence')
                output.mkdir()
                (output/'manifest-extraction.json').write_text(json.dumps({'failed':[],
                    'pending_requested':[], 'processed':[{'pdf_page':1}], 'dependencies':{}}))
                return SimpleNamespace(returncode=0)
            with patch('scripts.hybrid_extract.extract',side_effect=lambda *a:self.native(output,True)), \
                    patch('scripts.hybrid_extract.subprocess.run',side_effect=image_ocr):
                result=run(pdf,[1],output,selection,source)
            self.assertTrue(result['ocr_performed'])
            self.assertEqual(result['hybrid']['native_attempt']['status'],'rejected')
            self.assertEqual(result['hybrid']['native_attempt']['failures'][0]['pdf_page'],1)

    def test_failed_ocr_does_not_disappear_after_routing(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);pdf,selection,source=self.fixture(root);output=root/'fresh'
            def failed(command, **kwargs):
                output.mkdir()
                (output/'manifest-extraction.json').write_text(json.dumps({'failed':[{'error':'model unavailable'}],
                    'pending_requested':[1],'processed':[]}))
                return SimpleNamespace(returncode=1)
            with patch('scripts.hybrid_extract.extract',side_effect=lambda *a:self.native(output,True)), \
                    patch('scripts.hybrid_extract.subprocess.run',side_effect=failed):
                result=run(pdf,[1],output,selection,source)
            self.assertEqual(result['pending_requested'],[1])
            self.assertEqual(result['failed'][0]['error'],'model unavailable')

    def test_prior_failure_archive_is_never_overwritten(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);output=root/'fresh';output.mkdir()
            archive=root/'fresh.native-rejected';archive.mkdir()
            (archive/'evidence').write_text('keep')
            with self.assertRaises(FileExistsError):preserve_native_attempt(output)
            self.assertTrue(output.exists())
            self.assertEqual((archive/'evidence').read_text(),'keep')
