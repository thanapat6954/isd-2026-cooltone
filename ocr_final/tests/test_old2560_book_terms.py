"""Independent book comparisons must fail on lost slots or changed patterns."""
import unittest
from scripts.compare_old2560_book_terms import book_ledger, compare_term


class BookTermTests(unittest.TestCase):
    def term(self):
        return {'year':4,'semester':2,'pdf_page':30,'printed_page':25,'printed_credits':6,
                'source_file':'BIT-60.pdf',
                'expected_options':[{'code':'06036046','credits_raw':'6(0-35-0)'},{'code':'06036047','credits_raw':'6(0-35-0)'}]}

    def rows(self):
        return [{'code':code,'raw_code':'06036046 หรือ 06036047','credits_raw':'6(0-35-0)',
                 'credits':6,'alt_group':'choice','source_file':'BIT-60.pdf',
                 'page_number':30,'printed_page_number':25} for code in ('06036046','06036047')]

    def test_alternatives_count_once_but_both_labels_must_exist(self):
        self.assertTrue(compare_term(self.term(),self.rows())['passed'])
        self.assertFalse(compare_term(self.term(),self.rows()[:1])['passed'])

    def test_wrong_hours_fail_even_when_integer_credit_total_matches(self):
        rows=self.rows()
        rows[0]['credits_raw']='6(0-36-0)'
        self.assertFalse(compare_term(self.term(),rows)['passed'])

    def test_wrong_version_or_printed_page_fails(self):
        for field,value in [('source_file','BIT-65.pdf'),('printed_page_number',29)]:
            rows=self.rows()
            rows[0][field]=value
            self.assertFalse(compare_term(self.term(),rows)['passed'])

    def test_all_six_profiles_and_every_printed_term_have_a_ledger(self):
        ledger=book_ledger()
        self.assertEqual(len(ledger),6)
        self.assertEqual(sum(len(p['terms']) for p in ledger),49)
        for p in ledger:
            self.assertEqual(sum(t['printed_credits'] for t in p['terms']),p['printed_total'])
            self.assertEqual(len(p['terms']),len({(t['year'],t['semester']) for t in p['terms']}))

    def test_repeated_wildcards_are_distinct_slots_not_duplicates(self):
        term={'year':4,'semester':2,'pdf_page':40,'printed_page':35,'printed_credits':6,
              'expected_options':[{'code':'xxxxxxxx','credits_raw':'3(3-0-6)'}]*2}
        rows=[{'code':f'ELEC-SLOT-{i}','raw_code':'xxxxxxxx','credits_raw':'3(3-0-6)',
               'credits':3,'alt_group':None,'page_number':40,'printed_page_number':35} for i in (1,2)]
        self.assertTrue(compare_term(term,rows)['passed'])
        self.assertFalse(compare_term(term,rows[:1])['passed'])

    def test_version_validator_uses_existing_api_source_contract(self):
        from scripts.run_version_isolation import validate
        response={'selected_curricula':['IT-2560-coop'],'rows':[{'code':'06016315','source_file':'IT-60.pdf',
                  '_source':{'curriculum_name':'IT-2560-coop','curriculum_version':2560}}]}
        self.assertTrue(validate(response,'IT-2560-coop','IT-60.pdf'))
        response['rows'][0]['source_file']='IT.pdf'
        self.assertFalse(validate(response,'IT-2560-coop','IT-60.pdf'))
        response['rows'][0]['source_file']='IT-60.pdf'
        response['rows'][0]['_source']['curriculum_version']=2565
        self.assertFalse(validate(response,'IT-2560-coop','IT-60.pdf'))

    def test_development_probe_rejects_heading_name_and_wrong_hour_pattern(self):
        from scripts.run_old2560_qa import check
        body={'selected_curricula':['IT-2560-coop'],'answer':'IT-2560-coop','rows':[
              {'code':'06016333','name_th':'แขนงวิชาเทคโนโลยีเครือข่ายและระบบ','credits_raw':'3(2-2-5)'}]}
        case={'names_by_code':{'06016333':'เทคโนโลยีการให้บริการอินเตอร์เน็ต'},
              'raw_credits_by_code':{'06016333':'3(3-0-6)'}}
        errors,_=check(body,{'answer':body['answer'],'sources':[]},'IT-2560-coop',case)
        self.assertIn('name_th mismatch 06016333',errors)
        self.assertIn('credits_raw mismatch 06016333',errors)

    def test_readability_inspects_actual_plan_labels_not_just_catalog(self):
        import sqlite3
        from contextlib import closing
        from scripts.audit_old2560 import inspect_plan_labels
        with closing(sqlite3.connect(':memory:')) as db:
            db.row_factory=sqlite3.Row
            db.execute('CREATE TABLE v_plan(code,name_th,source_file,page_number)')
            db.execute('INSERT INTO v_plan VALUES(?,?,?,?)',('06016333','แขนงวิชาเทคโนโลยีเครือข่ายและระบบ','IT-60.pdf',37))
            self.assertEqual(inspect_plan_labels(db)[0]['code'],'06016333')
            db.execute('UPDATE v_plan SET name_th=?',('เทคโนโลยีการให้บริการอินเตอร์เน็ต',))
            self.assertFalse(inspect_plan_labels(db))


if __name__=='__main__':unittest.main()
