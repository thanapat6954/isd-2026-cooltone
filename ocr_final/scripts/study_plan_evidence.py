"""Capture bounded study-plan responses and hash-keyed source page renders."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import requests
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab10_fastapi.curriculum_app.database import DatabaseRegistry, open_readonly


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render', nargs='*', default=[])
    args=parser.parse_args()
    result={'databases':[], 'responses':[], 'renders':[]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not args.render:
        for db in DatabaseRegistry(args.app_root).active_programs:
            with open_readonly(db.path) as connection:
                rows=[dict(r) for r in connection.execute('SELECT * FROM v_plan WHERE (year=3 AND semester=1) OR (year=2 AND semester=2)')]
            result['databases'].append({'identity':db.curriculum_name,'path':str(db.path),'sha256':sha(db.path),'term_rows':rows})
            save()
        for program,year,semester,version in [('DSBA',3,1,'latest'),('IT',2,2,'latest'),('IT',2,2,'old')]:
            question=f'ปี {year} ภาคการศึกษาที่ {semester} มีรายวิชาอะไรบ้าง'
            response=requests.post('http://127.0.0.1:8000/ask',json={'curriculum':program,'version':version,'question':question},timeout=45)
            result['responses'].append({'program':program,'version':version,'question':question,'status':response.status_code,'response':response.json()})
            save()
        print('Saved',len(result['databases']),'profile snapshots and',len(result['responses']),'API responses')
    for spec in args.render:
        source,page=spec.rsplit(':',1)
        page=int(page)
        pdf=args.app_root/'data/input'/source
        image=ROOT/'tmp/pdfs/study_plans'/f'{pdf.stem}-{page:03}.png'
        image.parent.mkdir(parents=True,exist_ok=True)
        with pymupdf.open(pdf) as document:
            document[page-1].get_pixmap(dpi=150,alpha=False).save(image)
        result['renders'].append({'source_file':source,'source_sha256':sha(pdf),'pdf_page':page,'image':str(image),'image_sha256':sha(image)})
        save()
    if args.render: print('Rendered',len(result['renders']),'targeted pages')


if __name__=='__main__':main()
