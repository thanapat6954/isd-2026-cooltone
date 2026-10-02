"""Render only missing academic-plan images, saving a checkpoint after each page."""
import argparse
import hashlib
import json
from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    images=ROOT/'tmp/pdfs/a1_pages'
    images.mkdir(parents=True,exist_ok=True)
    result=json.loads(args.output.read_text(encoding='utf-8')) if args.output.exists() else {'pages':[]}
    for source,start,end in [('DSBA-60.pdf',25,34),('IT-60.pdf',27,40),('BIT-60.pdf',23,30)]:
        pdf=args.app_root/'data/input'/source
        sha=hashlib.sha256(pdf.read_bytes()).hexdigest()
        with pymupdf.open(pdf) as document:
            for page in range(start,end+1):
                old=next((p for p in result['pages'] if p['source']==source and p['pdf_page']==page),None)
                if old:
                    if old['source_sha256']!=sha or hashlib.sha256((ROOT.parent/old['image']).read_bytes()).hexdigest()!=old['image_sha256']: raise ValueError('Checkpoint/source hash changed')
                    continue
                image=images/f'{Path(source).stem}-page-{page:03}.png'
                reused=image.exists()
                if not reused: document[page-1].get_pixmap(matrix=pymupdf.Matrix(2.5,2.5)).save(str(image))
                result['pages'].append({'source':source,'source_sha256':sha,'pdf_page':page,
                                       'image':image.relative_to(ROOT.parent).as_posix(),'reused':reused,
                                       'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
                                       'review_status':'rendered_not_automatically_verified'})
                args.output.parent.mkdir(parents=True,exist_ok=True)
                args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Plan pages available:',len(result['pages']))


if __name__=='__main__':main()
