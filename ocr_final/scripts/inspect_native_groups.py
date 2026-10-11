"""Fresh source-only group diagnostics. Never produces or activates databases."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.source_native import fitz, font_decoder, lines, logical_rows, specialization_cell, CODE, sha, save


def inspect(pdf_path, pages, review_path, output):
    output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    state={'scope':'partial source fragments; not a curriculum build or activation candidate',
           'method':'pdf-text-tables','ocr_performed':False,
           'source_sha256':sha(pdf_path),'font_review_sha256':sha(review_path),
           'code_sha256':sha(Path(__file__)),'parser_sha256':sha(Path(__file__).with_name('source_native.py')),
           'pages':[],'prior_databases_read':0,'saved_ocr_read':0,'course_corrections_read':0,'evaluation_read':0}
    with fitz.open(pdf_path) as pdf:
        decoder=font_decoder(pdf,json.loads(review_path.read_text(encoding='utf8')))
        for number in pages:
            page=pdf[number-1]
            page.get_pixmap(dpi=200).save(output/f'page-{number}.png')
            groups=[]
            for table in sorted(page.find_tables().tables,key=lambda t:t.bbox[1]):
                for cells,boxes in logical_rows(page,table,decoder):
                    if len(CODE.findall(cells[0])) < 2 or 'หรือ' in cells[0]:
                        continue
                    positioned=[lines(page,fitz.Rect(box),decoder) for box in boxes]
                    try:
                        group=specialization_cell(positioned,positioned[1])
                        group['cell_boxes']=boxes
                        groups.append(group)
                    except ValueError as exc:
                        groups.append({'error':str(exc),'cells':cells,'cell_boxes':boxes})
            record={'pdf_page':number,'image_sha256':sha(output/f'page-{number}.png'),'groups':groups}
            save(output/f'page-{number}.groups.json',record)
            state['pages'].append(record)
    state['seconds']=round(time.perf_counter()-started,3)
    save(output/'inspection.json',state)
    return state


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdf',type=Path,required=True)
    p.add_argument('--page',type=int,action='append',required=True)
    p.add_argument('--font-review',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); result=inspect(a.pdf,a.page,a.font_review,a.output)
    print(json.dumps({'pages':len(result['pages']),
        'groups':sum(len(r['groups']) for r in result['pages']),
        'errors':[g['error'] for r in result['pages'] for g in r['groups'] if 'error' in g],
        'scope':result['scope']},ensure_ascii=False))


if __name__=='__main__':main()
