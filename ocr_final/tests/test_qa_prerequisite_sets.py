import unittest
from scripts.run_qa_gold import evaluate


class PrerequisiteSetTests(unittest.TestCase):
    def body(self, codes):
        return {'selected_curricula':['AI-2566-coop'],
                'rows':[{'code':'06046406','requires':code,'prerequisite_status':'required'} for code in codes],
                'answer':'06046406 requires 06046401 and 06046402'}

    def test_all_edges_in_any_order(self):
        errors,_=evaluate(self.body(['06046402','06046401']),'AI-2566-coop',
                          {'code':'06046406','status':'required','requires':['06046401','06046402']})
        self.assertEqual(errors,[])

    def test_missing_edge_is_not_hidden_by_answer(self):
        errors,_=evaluate(self.body(['06046401']),'AI-2566-coop',
                          {'code':'06046406','requires':['06046401','06046402']})
        self.assertIn('required prerequisite',errors)

    def test_extra_edge_fails(self):
        errors,_=evaluate(self.body(['06046401','06046402','06046403']),'AI-2566-coop',
                          {'code':'06046406','requires':['06046401','06046402']})
        self.assertIn('required prerequisite',errors)
