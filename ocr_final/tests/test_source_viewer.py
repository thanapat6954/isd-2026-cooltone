import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import sqlite3
from contextlib import closing
import pymupdf
from fastapi import HTTPException
from lab10_fastapi.curriculum_app.source_viewer import identity,render_page,source_path,printed_pages
from lab10_fastapi.curriculum_app.database import inspect_database


class SourceViewerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'data/input').mkdir(parents=True)
        with pymupdf.open() as pdf:
            pdf.new_page().insert_text((50,50),'Source content')
            pdf.new_page()
            pdf.save(self.root/'data/input/IT.pdf')
    def tearDown(self):self.temp.cleanup()
    def test_visible_and_blank_pages_are_both_rendered(self):
        for page in (1,2):
            path=render_page(self.root,'IT.pdf',page)
            self.assertGreater(path.stat().st_size,100)
            self.assertEqual(path,render_page(self.root,'IT.pdf',page))
        self.assertNotEqual(render_page(self.root,'IT.pdf',1).read_bytes(),render_page(self.root,'IT.pdf',2).read_bytes())
    def test_unknown_and_traversal_source_are_rejected(self):
        for name in ('../IT.pdf','unknown.pdf'):
            with self.assertRaises(HTTPException) as error:source_path(self.root,name)
            self.assertEqual(error.exception.status_code,404)
    def test_out_of_range_is_not_silently_redirected(self):
        for page in (0,3):
            with self.assertRaises(HTTPException) as error:identity(self.root,'IT.pdf',page)
            self.assertEqual(error.exception.status_code,416)
    def test_mapping_uses_pairs_without_assuming_offset(self):
        db=self.root/'curriculum.db'
        with closing(sqlite3.connect(db)) as connection, connection:
            connection.executescript('CREATE TABLE plan_item(source_file TEXT,page_number INTEGER,printed_page_number INTEGER); INSERT INTO plan_item VALUES("IT.pdf",1,88);')
        registry=SimpleNamespace(active_programs=[inspect_database(db,self.root)])
        self.assertEqual(printed_pages(registry,'IT.pdf',1),[88])
        self.assertEqual(printed_pages(registry,'IT.pdf',2),[])
        self.assertEqual(printed_pages(registry,'AI.pdf',1),[])
    def test_rule_and_continuation_page_mappings_are_sqlite_only(self):
        db=self.root/'curriculum.db'
        with closing(sqlite3.connect(db)) as connection, connection:
            connection.executescript('''CREATE TABLE plan_source_claim(source_file TEXT,pdf_page INTEGER,printed_page INTEGER);
                INSERT INTO plan_source_claim VALUES('IT.pdf',2,99);
                CREATE TABLE plan_bundle(source_file TEXT,rule_pdf_page INTEGER,rule_printed_page INTEGER);
                INSERT INTO plan_bundle VALUES('IT.pdf',1,88);''')
        registry=SimpleNamespace(active_programs=[inspect_database(db,self.root)])
        self.assertEqual(printed_pages(registry,'IT.pdf',1),[88])
        self.assertEqual(printed_pages(registry,'IT.pdf',2),[99])
