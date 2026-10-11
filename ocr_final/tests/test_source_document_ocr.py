"""Hybrid source transcription preserves evidence and never prompts with native facts."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

import pymupdf as fitz
from scripts.source_document_ocr import run,image_blocks


class SourceDocumentOCRTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.root=Path(self.folder.name)
        self.pdf=self.root/'source.pdf'
        with fitz.open() as document:
            document.new_page().insert_text((72,120),'SOURCE NATIVE MUST NOT ENTER PROMPT')
            document.save(self.pdf)
        self.tags=Mock()
        self.tags.json.return_value={'models':[{'name':'scb10x/typhoon-ocr1.5-3b:latest','digest':'test-digest'}]}

    def tearDown(self):
        self.folder.cleanup()

    def response(self,truncated=False):
        value=Mock()
        value.status_code=200
        value.text='test response body'
        value.json.return_value={'done':True,'done_reason':'length' if truncated else 'stop',
                                 'message':{'content':'literal image output'}}
        return value

    def test_native_page_does_not_call_image_model(self):
        with patch('scripts.source_document_ocr.requests.get',return_value=self.tags),\
             patch('scripts.source_document_ocr.requests.post') as post:
            state=run(self.pdf,[1],self.root/'candidate')
        post.assert_not_called()
        self.assertEqual(state['processed'][0]['method'],'pdf-native-text')
        self.assertFalse(state['domains']['catalog_complete'])

    def test_image_fallback_prompt_is_only_image_and_published_prompt(self):
        with patch('scripts.source_document_ocr.requests.get',return_value=self.tags),\
             patch('scripts.source_document_ocr.native_page',side_effect=ValueError('image body')) ,\
             patch('scripts.source_document_ocr.requests.post',return_value=self.response()) as post:
            state=run(self.pdf,[1],self.root/'candidate')
        request=post.call_args.kwargs['json']
        self.assertNotIn('SOURCE NATIVE MUST NOT ENTER PROMPT',json.dumps(request))
        self.assertTrue(request['messages'][0]['images'])
        self.assertTrue(state['processed'][0]['ocr_performed'])
        self.assertEqual(state['processed'][0]['native_rejection'],'image body')
        self.assertTrue((self.root/'candidate/page-1-attempt-1/original-native.txt').is_file())

    def test_truncated_ocr_preserves_response_and_keeps_page_pending(self):
        with patch('scripts.source_document_ocr.requests.get',return_value=self.tags),\
             patch('scripts.source_document_ocr.native_page',side_effect=ValueError('unreviewed glyph')),\
             patch('scripts.source_document_ocr.requests.post',return_value=self.response(True)):
            state=run(self.pdf,[1],self.root/'candidate')
        self.assertEqual(state['pending_requested'],[1])
        self.assertEqual(state['processed'],[])
        self.assertTrue((self.root/'candidate/page-1-attempt-1/region-1-ocr-response.json').is_file())

    def test_raster_blocks_partition_every_pixel_without_overlap(self):
        with fitz.open(self.pdf) as document:
            png=document[0].get_pixmap(dpi=100).tobytes('png')
        rules=[{'top':n,'bottom':n,'left':0,'right':500} for n in range(100,700,100)]
        with patch('scripts.source_document_ocr.horizontal_rules',return_value=rules):
            regions=image_blocks(png,'raster-blocks',2)
        self.assertGreater(len(regions),1)
        self.assertEqual(regions[0]['box'][1],0)
        for first,second in zip(regions,regions[1:]):
            self.assertEqual(first['box'][3],second['box'][1])

    def test_changed_artifact_cannot_be_resumed(self):
        output=self.root/'candidate'
        with patch('scripts.source_document_ocr.requests.get',return_value=self.tags):
            run(self.pdf,[1],output)
            (output/'page-1-attempt-1/transcription.md').write_text('changed')
            with self.assertRaisesRegex(ValueError,'artifact changed'):
                run(self.pdf,[1],output,resume=True)


if __name__=='__main__':
    unittest.main()
