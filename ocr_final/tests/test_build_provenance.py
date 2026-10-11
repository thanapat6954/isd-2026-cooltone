"""Health provenance must distinguish review coverage from a matching DB label."""
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from lab10_fastapi.curriculum_app.build_store import extraction_provenance
from lab10_fastapi.curriculum_app.build_scope import PLAN_CHECKS


class ProvenanceTests(unittest.TestCase):
    def test_source_identity_fields_and_defects_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'p.db').write_bytes(b'database fixture')
            digest=hashlib.sha256((root/'p.db').read_bytes()).hexdigest()
            extraction = {'extraction_method':'pdf-text-tables', 'ocr_performed':False,
                          'source_sha256':'source', 'pages':[2], 'reviewed_corrections':[]}
            (root/'p.json').write_text(json.dumps(extraction))
            manifest = {'databases':[{'profile':'p','path':'p.db','extraction':'p.json','sha256':digest}]}
            good = {'database_sha256':digest,'source_sha256':'source',
                    'verified_fields':sorted(PLAN_CHECKS),'unresolved_defects':[]}
            def result(record):
                (root/'source-validation.json').write_text(json.dumps({'profiles':{'p':record}}))
                return extraction_provenance(root,manifest)['profiles'][0]
            self.assertTrue(result(good)['source_validated'])
            for change in [{'source_sha256':'wrong'}, {'database_sha256':'wrong'},
                           {'verified_fields':['identity']}, {'unresolved_defects':['missing rows']}]:
                self.assertFalse(result({**good,**change})['source_validated'])
            self.assertFalse(result({})['source_validated'])
            page=result(good)['pages'][0]
            self.assertEqual(page['method'],'pdf-text-tables')
            self.assertFalse(page['ocr_performed'])
            (root/'raw').mkdir()
            proof = root/'raw/selection-rule.json'
            proof.write_text(json.dumps({'pdf_page':1}))
            extraction['artifacts']=[{'path':'raw/selection-rule.json',
                'sha256':hashlib.sha256(proof.read_bytes()).hexdigest()}]
            (root/'p.json').write_text(json.dumps(extraction))
            supporting=result(good)['pages'][-1]
            self.assertEqual(supporting['pdf_page'],1)
            self.assertEqual(supporting['role'],'supporting-selection-rule')
            self.assertFalse(supporting['ocr_performed'])
            proof.write_text(json.dumps({'pdf_page':99}))
            self.assertEqual(len(result(good)['pages']),1)
            (root/'p.db').write_bytes(b'changed file')
            self.assertFalse(result(good)['source_validated'])

    def test_bundled_origin_does_not_imply_fresh_ocr(self):
        self.assertEqual(extraction_provenance(Path('.'),None)['profiles'],[])


if __name__ == '__main__':
    unittest.main()
