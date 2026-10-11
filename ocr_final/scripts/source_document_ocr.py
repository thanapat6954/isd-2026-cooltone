"""Fresh hybrid transcription for source pages; no course facts or activation.

Native rows are preserved when readable. Image-only model input handles native
glyph/image-body rejection. Raw results require independent association review.
"""
import argparse
import base64
import json
import io
import os
from pathlib import Path
import sys
import time

import pymupdf as fitz
import requests
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.raster_ocr import PROMPT,horizontal_rules,digest,raster_regions
from scripts.source_native import font_decoder,save,sha
from scripts.source_catalog import native_page


def image_blocks(png,layout,rows_per_block):
    image=Image.open(io.BytesIO(png)).convert('RGB')
    width,height=image.size
    if layout=='page':
        return [{'box':[0,0,width,height],'png':png}]
    if layout=='raster-rows':
        return [{'box':list(r['box']),'band':list(r['band']),'png':r['png']}
                for r in raster_regions(png)]
    boundaries=sorted({0,height,*[(r['top']+r['bottom'])//2 for r in horizontal_rules(image)]})
    # Adjacent table rules belong to the same border, not separate content rows.
    separated=[]
    for value in boundaries:
        if separated and value-separated[-1]<5 and value!=height:
            continue
        separated.append(value)
    cuts=[0,*separated[rows_per_block:-1:rows_per_block],height]
    regions=[]
    for top,bottom in zip(cuts,cuts[1:]):
        box=[0,top,width,bottom]
        buffer=io.BytesIO()
        image.crop(box).save(buffer,format='PNG')
        regions.append({'box':box,'png':buffer.getvalue()})
    return regions


def run(pdf_path,pages,output,font_review=None,*,resume=False,dpi=200,num_predict=4096,
        layout='page',rows_per_block=4,
        model='scb10x/typhoon-ocr1.5-3b:latest',host='http://127.0.0.1:11434',timeout=600):
    if not pages or len(set(pages))!=len(pages):
        raise ValueError('Select unique source PDF pages explicitly')
    if layout not in {'page','raster-blocks','raster-rows'} or rows_per_block<1:
        raise ValueError('Invalid image layout')
    host=host.rstrip('/')
    tags=requests.get(host+'/api/tags',timeout=10)
    tags.raise_for_status()
    matches=[r for r in tags.json()['models'] if r['name'] in {model,model+':latest'}]
    if len(matches)!=1 or not matches[0].get('digest'):
        raise ValueError('Installed OCR model digest unavailable; no model download fallback')
    identity={'source_file':pdf_path.name,'source_sha256':sha(pdf_path),'requested_pages':pages,
              'code_sha256':sha(Path(__file__)),
              'native_guard_sha256':sha(ROOT/'scripts/source_catalog.py'),
              'font_decoder_sha256':sha(ROOT/'scripts/source_native.py'),
              'font_review_sha256':sha(font_review) if font_review else None,
              'renderer_version':fitz.VersionBind,'dpi':dpi,'model':model,
              'layout':layout,'rows_per_block':rows_per_block,
              'segmenter_sha256':sha(ROOT/'scripts/raster_ocr.py'),
              'model_digest':matches[0]['digest'],'host':host,'prompt':PROMPT,
              'generation':{'temperature':0,'num_ctx':8192,'num_predict':num_predict}}
    manifest=output/'source-transcription.json'
    if resume:
        state=json.loads(manifest.read_text(encoding='utf8'))
        if state['identity']!=identity:
            raise ValueError('Source/model/code/configuration changed; preserve output and use a new folder')
        for entry in state['processed']:
            for artifact in entry['artifacts']:
                path=(output/artifact['path']).resolve()
                if not path.is_relative_to(output.resolve()) or sha(path)!=artifact['sha256']:
                    raise ValueError('Prior transcription artifact changed; cannot resume')
    else:
        output.mkdir(parents=True,exist_ok=False)
        state={'identity':identity,'scope':'literal source-page transcription only; no catalog certification/DB activation',
               'processed':[],'failed':[],'running':None,
               'domains':{'catalog_complete':False,'program_rules_complete':False}}
    review=json.loads(font_review.read_text(encoding='utf8')) if font_review else None
    with fitz.open(pdf_path) as document:
        if any(p<1 or p>len(document) for p in pages):
            raise ValueError('Requested PDF page outside source document')
        state['total_source_pages']=len(document)
        decoder=font_decoder(document,review) if review else None
        for number in pages:
            if number in {r['pdf_page'] for r in state['processed']}:
                continue
            state['running']=number
            save(manifest,state)
            page=document[number-1]
            # New failed attempts never overwrite the previous response/image.
            attempt=output/f'page-{number}-attempt-{len(list(output.glob(f"page-{number}-attempt-*")))+1}'
            attempt.mkdir()
            started=time.perf_counter()
            page.get_pixmap(dpi=dpi).save(attempt/'page.png')
            (attempt/'original-native.txt').write_text(page.get_text(),encoding='utf8')
            reason=None
            try:
                try:
                    rows,text=native_page(page,decoder)
                    method='pdf-native-text'
                    save(attempt/'native-rows.json',rows)
                except ValueError as error:
                    reason=str(error)
                    method='image-OCR'
                    texts=[]
                    blocks=image_blocks((attempt/'page.png').read_bytes(),layout,rows_per_block)
                    save(attempt/'regions.json',[{'region':i,'original_pixel_box':r['box'],
                                                 'original_pixel_band':r.get('band',r['box'])}
                                                 for i,r in enumerate(blocks,1)])
                    cache=output/'image-region-checkpoints'
                    cache.mkdir(exist_ok=True)
                    for i,region in enumerate(blocks,1):
                        image_path=attempt/f'region-{i}.png'
                        image_path.write_bytes(region['png'])
                        region_identity={**identity,'pdf_page':number,'box':region['box'],
                                         'image_sha256':sha(image_path)}
                        checkpoint=cache/(digest(region_identity)+'.json')
                        if checkpoint.exists():
                            stored=json.loads(checkpoint.read_text(encoding='utf8'))
                            if stored['identity']!=region_identity or digest(stored['raw'])!=stored['response_digest']:
                                raise ValueError('OCR region checkpoint changed; preserve output')
                            raw=stored['raw']
                        else:
                            print(f'PDF {number}: image region {i}/{len(blocks)}',flush=True)
                            payload={'model':model,'messages':[{'role':'user','content':PROMPT,
                                     'images':[base64.b64encode(region['png']).decode()]}],
                                     'stream':False,'options':identity['generation']}
                            response=requests.post(host+'/api/chat',json=payload,timeout=timeout)
                            save(attempt/f'region-{i}-http-response.json',
                                 {'status':response.status_code,'body':response.text})
                            response.raise_for_status()
                            raw=response.json()
                        save(attempt/f'region-{i}-ocr-response.json',raw)
                        part=raw.get('message',{}).get('content','')
                        (attempt/f'region-{i}.md').write_text(part,encoding='utf8')
                        if not part.strip() or raw.get('done') is not True or raw.get('done_reason')=='length':
                            raise ValueError('Empty/incomplete/truncated OCR; preserved raw response, no completed page')
                        if not checkpoint.exists():
                            save(checkpoint,{'identity':region_identity,'raw':raw,'response_digest':digest(raw)})
                        texts.append(part)
                    text='\n\n'.join(texts)
                (attempt/'transcription.md').write_text(text,encoding='utf8')
                state['processed'].append({'pdf_page':number,'method':method,'ocr_performed':method=='image-OCR',
                     'native_rejection':reason,'source_review':'unverified literal transcription',
                     'seconds':round(time.perf_counter()-started,3),
                     'artifacts':[{'path':p.relative_to(output).as_posix(),'sha256':sha(p)}
                                  for p in sorted(attempt.iterdir()) if p.is_file()]})
                print(f'PDF {number}: {method}; literal transcription complete, source review pending',flush=True)
            except (ValueError,requests.RequestException) as error:
                state['failed'].append({'pdf_page':number,'attempt':attempt.name,'reason':str(error)})
                print(f'PDF {number}: failed; raw attempt preserved: {error}',flush=True)
            save(manifest,state)
    state['running']=None
    state['pending_requested']=sorted(set(pages)-{r['pdf_page'] for r in state['processed']})
    state['requested_transcription_complete']=not state['pending_requested']
    save(manifest,state)
    return state


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf',type=Path,required=True)
    parser.add_argument('--pages',type=int,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--font-review',type=Path)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--num-predict',type=int,default=4096)
    parser.add_argument('--dpi',type=int,default=200)
    parser.add_argument('--layout',choices=['page','raster-blocks','raster-rows'],default='page')
    parser.add_argument('--rows-per-block',type=int,default=4)
    args=parser.parse_args()
    state=run(args.pdf,args.pages,args.output,args.font_review,resume=args.resume,
              dpi=args.dpi,num_predict=args.num_predict,layout=args.layout,rows_per_block=args.rows_per_block,
              host=os.getenv('OLLAMA_HOST','http://127.0.0.1:11434'))
    print(json.dumps({'output':str(args.output),'processed':len(state['processed']),
                      'pending':state['pending_requested'],'source_verified':False},ensure_ascii=False))
    return int(bool(state['pending_requested']))


if __name__=='__main__':
    raise SystemExit(main())
