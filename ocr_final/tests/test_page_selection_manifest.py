"""Page selection must be evidence-based, never an automatic appendix filter."""
import unittest
from scripts.build_page_selection_manifest import records, reviewed_relationship_pages


class PageSelectionTests(unittest.TestCase):
    def test_historical_review_requires_locked_dependency(self):
        review={'status':'visually_verified','ingestion_sha256':'locked','approved_pages':{'IT.pdf':[[34,29]]}}
        result=reviewed_relationship_pages(review,{'sources':{'IT.pdf':'sourcehash'}},'locked')
        self.assertEqual(result[0][1:],(34,29))
        self.assertEqual(result[0][0]['source_sha256'],'sourcehash')
        with self.assertRaises(ValueError):
            reviewed_relationship_pages(review,{'sources':{'IT.pdf':'sourcehash'}},'changed')

    def test_historical_unverified_pages_not_reused(self):
        self.assertEqual(reviewed_relationship_pages({'status':'unverified'}, {}, 'hash'),[])

    def test_inherited_review_and_exact_pair(self):
        data={'source_file':'AI.pdf','source_sha256':'hash','status':'visually_verified',
              'rows':[{'pdf_page':292,'printed_page':288}]}
        result=list(records(data))
        self.assertEqual([(r[1],r[2]) for r in result],[(292,288)])
        self.assertEqual(result[0][0]['source_sha256'],'hash')

    def test_child_unverified_overrides_parent(self):
        data={'source_file':'AI.pdf','status':'visually_verified',
              'rows':[{'pdf_page':292,'review_status':'unverified'}]}
        self.assertEqual(list(records(data)),[])

    def test_unreviewed_appendix_not_selected(self):
        self.assertEqual(list(records({'source_file':'AI.pdf','pdf_page':292,
                                       'section':'appendix'})),[])

    def test_missing_folio_stays_unknown(self):
        result=list(records({'source_file':'AI.pdf','status':'visually_verified','pdf_page':292}))
        self.assertIsNone(result[0][2])

    def test_pair_table_preserves_numbering(self):
        result=list(records({'source_file':'AI.pdf','status':'visually_verified',
                             'pages':[[23,19],[292,288]]}))
        self.assertEqual([(r[1],r[2]) for r in result],[(23,19),(292,288)])

    def test_skip_requires_inspected_reason(self):
        with self.assertRaises(ValueError):
            list(records({'source_file':'AI.pdf','review_status':'visually_verified','pdf_page':2,'decision':'skip'}))

    def test_reviewed_blank_skip_is_explicit(self):
        rows=list(records({'source_file':'AI.pdf','review_status':'visually_verified','pdf_page':2,
                           'decision':'skip','skip_kind':'blank','reason':'ตรวจภาพแล้วว่างจริง'}))
        self.assertEqual(rows[0][0]['decision'],'skip')
