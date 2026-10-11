"""A repeated source build must reject changed facts and incomplete evidence."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.source_plan_witness import fingerprint,verify_profile
from scripts.database_build import write,sha
from lab10_fastapi.curriculum_app.build_scope import PLAN_CHECKS


class SourceWitnessTests(unittest.TestCase):
    def fixture(self,root):
        raw=root/'raw/test'
        raw.mkdir(parents=True)
        data={'courses':[{'year':1,'semester':1,'code':'06000001','name_th':'TEST ONLY',
            'name_en':'TEST ONLY','credits':'3(3-0-6)','source_file':'SYN.pdf',
            'page_number':2,'printed_page_number':1}],
            'term_totals':[{'year':1,'semester':1,'credits':3,'source_file':'SYN.pdf',
                           'page_number':2,'printed_page_number':1}]}
        write(raw/'page-2.plan.json',data)
        for name in ['identity.png','page-2.png']:(raw/name).write_bytes(b'synthetic image test only')
        db=root/'curriculum.db';db.write_bytes(b'synthetic SQLite hash test only')
        extraction={'status':'parsed','source_sha256':'test-source','pages':[2],
                    'pending_pages':[],'material_defects':[],
                    'artifacts':[{'path':'raw/test/page-2.plan.json','sha256':sha(raw/'page-2.plan.json')}]}
        write(root/'extraction.json',extraction)
        item={'profile':'test','extraction':'extraction.json','path':'curriculum.db','sha256':sha(db)}
        approval={'source_sha256':'test-source','pages':[2],'facts_sha256':fingerprint(data),
                  'verified_fields':sorted(PLAN_CHECKS),'evidence':[{'pdf_page':p,'file':n,'sha256':sha(raw/n)}
                   for p,n in [(1,'identity.png'),(2,'page-2.png')]]}
        return data,extraction,item,approval

    def test_unchanged_facts_reach_readonly_sql_verifier(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,_,item,approval=self.fixture(root)
            with patch('scripts.source_plan_witness.validate_sql_chain',return_value={'source_sql_fields_match':True}) as checker:
                result=verify_profile(root,item,approval)
                checker.assert_called_once_with(root,item)
                self.assertEqual(result['source_fingerprint'],approval['facts_sha256'])

    def test_changed_name_rejected_even_if_artifact_hash_updated(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data,extraction,item,approval=self.fixture(root)
            data['courses'][0]['name_en']='INVENTED'
            path=root/'raw/test/page-2.plan.json';write(path,data)
            extraction['artifacts'][0]['sha256']=sha(path);write(root/'extraction.json',extraction)
            with self.assertRaisesRegex(ValueError,'plan facts differ'):
                verify_profile(root,item,approval)

    def test_source_coverage_images_and_database_must_match(self):
        for mutation,message in [('source','PDF differs'),('coverage','page coverage'),('fields','every plan field'),
                                 ('cover','lacks cover'),('image','Source image differs'),('database','SQLite changed')]:
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);_,_,item,approval=self.fixture(root)
                if mutation=='source':approval['source_sha256']='other'
                if mutation=='coverage':approval['pages']=[2,3]
                if mutation=='fields':approval['verified_fields']=[]
                if mutation=='cover':approval['evidence']=approval['evidence'][1:]
                if mutation=='image':(root/'raw/test/page-2.png').write_bytes(b'other image')
                if mutation=='database':(root/'curriculum.db').write_bytes(b'other database')
                with self.assertRaisesRegex(ValueError,message):verify_profile(root,item,approval)

    def test_pending_extraction_cannot_be_certified(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,extraction,item,approval=self.fixture(root)
            extraction['pending_pages']=[2];write(root/'extraction.json',extraction)
            with self.assertRaisesRegex(ValueError,'Incomplete'):verify_profile(root,item,approval)
