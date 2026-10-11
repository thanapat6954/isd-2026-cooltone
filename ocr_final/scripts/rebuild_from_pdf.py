"""Rebuild the declared academic plans from PDFs, then verify known-source fidelity."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_lab8b import PROFILES
from scripts.database_build import rebuild, validate, activation
from scripts.source_plan_witness import certify
from scripts.database_build import read


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app-root',type=Path,default=ROOT)
    p.add_argument('--profiles',nargs='+',choices=list(PROFILES),default=list(PROFILES))
    p.add_argument('--stage-timeout',type=int,default=3600)
    p.add_argument('--activate',action='store_true',help='Install the verified declared plan scope, with backup; stop its backend first')
    a = p.parse_args()
    app = a.app_root.resolve()
    font_review = ROOT/'data/source_reviews/font_encoding/all-reviewed-source-glyphs-20261011.json'
    witness = ROOT/'data/source_reviews/rebuild-plan-witnesses-20261011.json'
    approval = read(witness)
    read(font_review)
    missing = [profile for profile in a.profiles if profile not in approval.get('profiles',{})]
    if missing:
        p.error('No prior source approval for: '+', '.join(missing))
    missing_pdfs = sorted({PROFILES[profile]['input'].name for profile in a.profiles
                           if not (app/'data/input'/PROFILES[profile]['input'].name).is_file()})
    if missing_pdfs:
        p.error('Missing source PDFs: '+', '.join(missing_pdfs))
    print('สร้างใหม่จาก PDF: เฉพาะแผนการศึกษา '+str(len(a.profiles))+' profiles; อ่าน PDF text/table ก่อน และใช้ image OCR เมื่ออ่านตรงไม่ได้',flush=True)
    candidate = rebuild(app,a.profiles,'reviewed',None,a.stage_timeout,
                        extraction_method='hybrid',declared=True,font_review=font_review)
    try:
        certify(candidate,witness)
    except (ValueError,OSError,KeyError) as error:
        print(json.dumps({'candidate':str(candidate),'ready':False,'source_verification_error':str(error)},ensure_ascii=False),flush=True)
        return 1
    report = validate(candidate,app,full=False)
    result = {'candidate':str(candidate),'ready':report['ready'],'contract':report['contract'],
              'source_verification':'Exact match to prior visual source approval; reference fingerprints used only after construction',
              'exclusions':['catalog descriptions','prerequisites','program regulations','legacy']}
    if a.activate and report['ready']:
        result['activation'] = activation(app,candidate,declared=True)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return int(not report['ready'])


if __name__=='__main__':
    raise SystemExit(main())
