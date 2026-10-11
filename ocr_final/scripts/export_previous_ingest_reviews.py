"""Recover prior visually approved production corrections, never DB/eval labels."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.apply_reviewed_plan_term import apply_review

MAPPINGS = {
    'IT-2560': ('IT-60.pdf', {
        'it-2560-coop': 'work/lab8b_it_2560_coop/lab7b/reviewed_ingest_v4.json',
        'it-2560-no-coop': 'work/lab8b_it_2560_no_coop/lab7b/reviewed_ingest_v3.json'}),
    'BIT-2560': ('BIT-60.pdf', {
        'bit-2560-coop': 'work/lab8b_bit_2560_coop/lab7b/reviewed_ingest_v2.json'})}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--app-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    results=[]
    for curriculum,(pdf,profiles) in MAPPINGS.items():
        source_hash=sha(a.source_root/'data/input'/pdf)
        data={'purpose':'production corrections reused from prior visually approved ingestion; NOT new review or held-out',
              'source_sha256':source_hash,'profiles':{},'provenance':{}}
        for profile,path in profiles.items():
            original=a.source_root/Path(path).parent/'pred_vlm.json'
            reviewed=a.source_root/path
            approved_inputs={sha(p):p.name for p in [original,*reviewed.parent.glob('reviewed_ingest*.json')]}
            corrections=json.loads(reviewed.read_text(encoding='utf-8'))['reviewed_ingest_corrections']
            for review in corrections:
                if review['source_file']!=pdf or review['source_sha256']!=source_hash or review['input_sha256'] not in approved_inputs:
                    raise ValueError('Approval is not bound to unchanged book/original OCR')
                apply_review({'courses':[]},review)
            data['profiles'][profile]=corrections
            data['provenance'][profile]={'approved_ingest_path':path,'approved_ingest_sha256':sha(reviewed),
                                        'original_ocr_sha256':sha(original),
                                        'approval_input_chain':{r['input_sha256']:approved_inputs[r['input_sha256']] for r in corrections},
                                        'method':'reused earlier rendered-page approvals, including hash-bound prior reviewed inputs'}
        target=a.app_root/'data/source_reviews'/f'{curriculum}-plan-corrections.json'
        payload=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
        if target.exists() and target.read_text(encoding='utf-8')!=payload:
            raise ValueError('Refuse replacement of existing approvals')
        target.write_text(payload,encoding='utf-8')
        results.append({'dataset':target.name,'profiles':list(profiles),'terms':sum(len(r) for r in data['profiles'].values())})
    a.output.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results))


if __name__=='__main__':main()
