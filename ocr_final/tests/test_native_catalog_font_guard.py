"""Native corpus must expose rejected glyph pages and preserve source text."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pymupdf as fitz
from scripts import source_catalog


class NativeCatalogFontGuard(unittest.TestCase):
    def test_native_header_and_footer_do_not_cover_scanned_body(self):
        with fitz.open() as document:
            page=document.new_page()
            pixmap=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,120,160),False)
            pixmap.clear_with(255)
            page.insert_image(fitz.Rect(72,90,520,700),pixmap=pixmap)
            page.insert_text((72,40),'Native header')
            page.insert_text((72,795),'Native footer')
            gaps=source_catalog.image_text_gaps(page,source_catalog.lines(page))
            self.assertTrue(gaps)
            self.assertEqual(gaps[0]['native_characters'],0)

    def test_background_image_with_readable_body_text_is_not_a_gap(self):
        with fitz.open() as document:
            page=document.new_page()
            pixmap=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,120,160),False)
            pixmap.clear_with(255)
            page.insert_image(fitz.Rect(72,90,520,700),pixmap=pixmap)
            for y in range(120,600,30):
                page.insert_text((90,y),'Readable native source course text and table rows')
            self.assertEqual(source_catalog.image_text_gaps(page,source_catalog.lines(page)),[])

    def test_readable_text_elsewhere_does_not_cover_separate_scanned_table(self):
        with fitz.open() as document:
            page=document.new_page()
            pixmap=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,120,80),False)
            pixmap.clear_with(255)
            page.insert_image(fitz.Rect(72,400,520,700),pixmap=pixmap)
            for y in range(120,320,30):
                page.insert_text((90,y),'Readable source paragraph outside the image')
            self.assertTrue(source_catalog.image_text_gaps(page,source_catalog.lines(page)))

    def test_private_use_page_is_preserved_and_excluded_from_native_corpus(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            pdf=root/'source.pdf'
            with fitz.open() as document:
                document.new_page().insert_text((72,100),'Original source text')
                document.save(pdf)
            original_lines=source_catalog.lines
            def unreviewed(page, *args, **kwargs):
                rows=original_lines(page,*args,**kwargs)
                rows[0]['text']='unmapped \ue001'
                return rows
            output=root/'candidate'
            with patch.object(source_catalog,'lines',side_effect=unreviewed):
                state=source_catalog.extract(pdf,output,render_rejected_pages=1)
            self.assertFalse(state['domains']['source_document_corpus'])
            self.assertFalse(state['domains']['catalog_complete'])
            self.assertEqual(state['accepted_native_pages'],0)
            self.assertEqual(state['rejected_pages'][0]['pdf_page'],1)
            self.assertIn('Original source text',(output/'page-1.original.txt').read_text())
            self.assertFalse((output/'page-1.txt').exists())
            self.assertTrue((output/'rejected-page-1.png').exists())
            with closing(sqlite3.connect(f'file:{output / "source.sqlite"}?mode=ro',uri=True)) as db:
                db.execute('PRAGMA query_only=ON')
                self.assertEqual(db.execute('SELECT count(*) FROM source_document_page').fetchone()[0],0)
            checkpoint=json.loads((output/'source-catalog-checkpoint.json').read_text())
            self.assertIn('not activation-ready',checkpoint['status'])


if __name__=='__main__':
    unittest.main()
