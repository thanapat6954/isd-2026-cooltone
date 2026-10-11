import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lab7_page_resume', ROOT/'scr/ocr_system/lab7b_curriculum.py')
lab7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab7)


class OCRPageResumeTests(unittest.TestCase):
    def test_temperature_changes_request_and_checkpoint(self):
        text = 'a meaningful raw course description with enough content'
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(lab7, 'ollama_chat', return_value=text) as chat:
                for temperature in (0.1, 0.0, 0.0):
                    with patch.object(lab7, 'OCR_TEMPERATURE', temperature):
                        lab7.extract_vlm_pages([b'page'], Path(folder), page_numbers=[93], source_file='book.pdf')
                self.assertEqual(chat.call_count, 2)
                self.assertEqual([c.kwargs['temperature'] for c in chat.call_args_list], [0.1, 0.0])
    def test_raw_manifest_extraction_never_normalizes_plan_rows(self):
        text='a meaningful raw regulation page with enough content'
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(lab7,'ollama_chat',return_value=text), patch.object(lab7,'_text_to_json_chunked') as normalize:
                self.assertEqual(lab7.extract_vlm_pages([b'raw-page'],Path(folder),page_numbers=[77],source_file='book.pdf'),[text])
                normalize.assert_not_called()
    def test_failed_profile_is_resumable_without_discarding_history(self):
        from scripts.reconstruct_isolated import latest_results
        history=[{'profile':'ai','exit_code':1},{'profile':'bit','exit_code':0}]
        self.assertEqual(latest_results(history)['ai']['exit_code'],1)
        history.append({'profile':'ai','exit_code':0})
        self.assertEqual(latest_results(history)['ai']['exit_code'],0)
        self.assertEqual(len(history),3)
    def test_completed_pages_survive_failed_next_page(self):
        text='a meaningful extracted curriculum table with enough content'
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            with patch.object(lab7,'ollama_chat',side_effect=[text,RuntimeError('interrupted')]):
                with self.assertRaises(RuntimeError):
                    lab7.pipeline_vlm([b'page1',b'page2'],out,page_numbers=[23,24],source_file='book.pdf')
            with patch.object(lab7,'ollama_chat',return_value=text) as chat, patch.object(lab7,'_text_to_json_chunked',return_value={'courses':[]}):
                lab7.pipeline_vlm([b'page1',b'page2'],out,page_numbers=[23,24],source_file='book.pdf')
                self.assertEqual(chat.call_count,1)
            self.assertEqual(len(list((out/'ocr_page_checkpoints').glob('*.json'))),2)

    def test_changed_image_is_not_reused(self):
        text='a meaningful extracted curriculum table with enough content'
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(lab7,'ollama_chat',return_value=text) as chat, patch.object(lab7,'_text_to_json_chunked',return_value={}):
                for page in [b'page1',b'changed page']:
                    lab7.pipeline_vlm([page],Path(folder),page_numbers=[23],source_file='book.pdf')
                self.assertEqual(chat.call_count,2)
