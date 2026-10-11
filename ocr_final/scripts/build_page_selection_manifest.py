"""Inventory every physical page; only reviewed evidence can include or skip it."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_all import VERSIONS


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def records(node, inherited=None):
    context=dict(inherited or {})
    if isinstance(node,dict):
        for key in ('source_file','sha256','source_sha256','review_status','status','decision','reason','skip_kind'):
            if key in node:context[key]=node[key]
        # A child's explicit review state overrides an inherited approval.
        if 'review_status' in node or 'status' in node:
            context['_approved']=node.get('review_status',node.get('status'))=='visually_verified'
        approved=context.get('_approved',False)
        if approved and context.get('source_file'):
            if context.get('decision')=='skip' and (context.get('skip_kind') not in ('blank','irrelevant') or not context.get('reason')):
                raise ValueError('A reviewed skip requires blank/irrelevant classification and a reason')
            page=node.get('pdf_page',node.get('page_number'))
            book=node.get('printed_page',node.get('printed_page_number',node.get('book_page')))
            if type(page) is int:yield context,page,book
            for pair in node.get('pages',[]):
                if isinstance(pair,list) and len(pair)==2 and all(type(v) is int for v in pair):yield context,*pair
        for value in node.values():
            if isinstance(value,(dict,list)):yield from records(value,context)
    elif isinstance(node,list):
        for value in node:yield from records(value,context)


def reviewed_relationship_pages(review, ingestion, ingestion_sha256):
    """Reconcile the older signed review ledger without importing its facts."""
    if review.get('status') != 'visually_verified':
        return []
    if review.get('ingestion_sha256') != ingestion_sha256:
        raise ValueError('Reviewed relationship dependency changed; page approval needs review')
    result=[]
    for filename, pairs in review.get('approved_pages', {}).items():
        digest=ingestion.get('sources', {}).get(filename)
        if not digest:
            raise ValueError(f'Missing reviewed source hash: {filename}')
        for pair in pairs:
            if not isinstance(pair,list) or len(pair)!=2 or not all(type(v) is int for v in pair):
                raise ValueError('Invalid historical reviewed page pair')
            result.append(({'source_file':filename,'source_sha256':digest,
                           'reason':'นำคู่หน้าจากบันทึกตรวจภาพเดิมที่ dependency hash ตรงกันมาใช้ ไม่ใช่การตรวจใหม่'},*pair))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--reviews-root',type=Path,default=ROOT/'data/source_reviews')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    evidence={}
    for path in args.reviews_root.rglob('*.json'):
        if args.output.resolve() in path.resolve().parents:continue
        data=json.loads(path.read_text(encoding='utf-8'))
        reviewed=list(records(data))
        if path.name=='study_plan_db_review.json':
            dependency=path.with_name('study_plan_relationships.json')
            reviewed.extend(reviewed_relationship_pages(data,json.loads(dependency.read_text(encoding='utf-8')),sha(dependency)))
        for context,page,book in reviewed:
            evidence.setdefault(context['source_file'],{}).setdefault(page,[]).append({
                'printed_page':book,'approval':path.relative_to(args.reviews_root).as_posix(),
                'approval_sha256':sha(path),'source_sha256':context.get('sha256',context.get('source_sha256')),
                'decision':context.get('decision','include'),'reason':context.get('reason'),'skip_kind':context.get('skip_kind')})
    summary=[]
    for filename,(program,version) in VERSIONS.items():
        path=args.app_root/'data/input'/filename
        if not path.exists():
            summary.append({'source_file':filename,'status':'source_missing'});continue
        digest=sha(path)
        with pymupdf.open(path) as pdf:count=len(pdf)
        pages=[]
        for number in range(1,count+1):
            approved=[item for item in evidence.get(filename,{}).get(number,[]) if item['source_sha256']==digest]
            folios={item['printed_page'] for item in approved if type(item['printed_page']) is int}
            decisions={item['decision'] for item in approved}
            if decisions-{'include','skip'}:raise ValueError('Invalid approved page decision')
            if len(decisions)>1:raise ValueError(f'Conflicting include/skip approvals: {filename} page {number}')
            decision=next(iter(decisions)) if decisions else 'unreviewed'
            pages.append({'pdf_page':number,'printed_book_page':next(iter(folios)) if len(folios)==1 else None,
                'decision':decision,
                'reason':'; '.join(item['reason'] for item in approved if item.get('reason')) or ('มี source approval ที่ตรวจภาพแล้วสำหรับเนื้อหาหรือแหล่งอ้างอิงหลักสูตร' if approved else 'ยังไม่ตรวจภาพ ห้ามถือว่าเป็นหน้าว่างหรือไม่เกี่ยวข้อง'),
                'evidence':approved,'mapping_conflict':len(folios)>1})
        document={'source_file':filename,'source_sha256':digest,'program':program,'curriculum_version':version,
            'identity_mapping':'scripts/audit_all.py VERSIONS; recorded authoritative source identities',
            'scope':'page-selection coverage, not full-book OCR/source review; unreviewed pages remain pending',
            'policy':'ไม่ตัด appendix อัตโนมัติ ต้องเก็บ descriptions/prerequisites/plans/structure/graduation/regulations; skip ต้องมี independent visual review',
            'pages':pages}
        (args.output/(filename[:-4]+'.json')).write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        summary.append({'source_file':filename,'physical_pages':count,'include':sum(p['decision']=='include' for p in pages),
                        'skip':sum(p['decision']=='skip' for p in pages),'unreviewed':sum(p['decision']=='unreviewed' for p in pages)})
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
