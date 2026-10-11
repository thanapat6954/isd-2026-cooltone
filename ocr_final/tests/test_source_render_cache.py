import tempfile
from pathlib import Path
import unittest
import pymupdf
from scripts.render_a1_review_pages import render_page


class SourceRenderCacheTests(unittest.TestCase):
    def test_locked_reuse_retains_legacy_and_separates_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'synthetic.pdf'
            with pymupdf.open() as document:
                document.new_page().insert_text((50,50),'Synthetic page')
                document.save(source)
            cache = root/'images'
            cache.mkdir()
            legacy = cache/'synthetic-page-001.png'
            legacy.write_bytes(b'old unverified cache')
            first = render_page(source,1,cache,100)
            self.assertFalse(first['reused'])
            self.assertTrue(render_page(source,1,cache,100)['reused'])
            self.assertNotEqual(first['image'],render_page(source,1,cache,120)['image'])
            self.assertEqual(legacy.read_bytes(),b'old unverified cache')

    def test_corrupt_cache_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'synthetic.pdf'
            with pymupdf.open() as document:
                document.new_page()
                document.save(source)
            result = render_page(source,1,root/'images',100)
            Path(result['image']).write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError,'integrity guard'):
                render_page(source,1,root/'images',100)
