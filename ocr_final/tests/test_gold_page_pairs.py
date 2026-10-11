import json
import unittest
from scripts.run_qa_gold import supports_citation

class GoldPagePairTests(unittest.TestCase):
    def test_aggregate_preserves_pdf_and_printed_pair(self):
        row={'page_evidence':json.dumps([{'source_file':'IT-60.pdf','page':34,'book_page':29}])}
        self.assertTrue(supports_citation(row,{'source':'IT-60.pdf','page':34,'book_page':29}))
        self.assertFalse(supports_citation(row,{'source':'IT-60.pdf','page':34,'book_page':30}))

    def test_wrong_version_or_cross_pair_not_supported(self):
        row={'page_evidence':[{'source_file':'IT-60.pdf','page':34,'book_page':29},
                              {'source_file':'IT.pdf','page':38,'book_page':33}]}
        self.assertFalse(supports_citation(row,{'source':'IT-60.pdf','page':38,'book_page':33}))

    def test_single_row_and_malformed_aggregate(self):
        case={'source':'DSBA-60.pdf','page':30,'book_page':25}
        self.assertTrue(supports_citation({'source_file':'DSBA-60.pdf','page_number':30,'printed_page_number':25},case))
        self.assertFalse(supports_citation({'page_evidence':'broken JSON'},case))

if __name__=='__main__':unittest.main()
