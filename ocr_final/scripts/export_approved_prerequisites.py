"""Reuse already visually approved description evidence, never candidate OCR."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, default=ROOT.parent / 'docs/results/a1_ground_truth_review.json')
    parser.add_argument('--manifest', type=Path, default=ROOT.parent / 'docs/results/pdf_manifest.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/ground_truth/prerequisite_source_reviews.json')
    args = parser.parse_args()
    result = json.loads(args.output.read_text(encoding='utf-8'))
    sources = {item['file']:item['sha256'].lower() for item in json.loads(args.manifest.read_text(encoding='utf-8'))['files']}
    keys = {(item['source_file'],item['page_number'],tuple(item['codes'])) for item in result['documents']}
    added = 0
    for sample in json.loads(args.review.read_text(encoding='utf-8'))['samples']:
        if sample['review_status'] not in {'visually_verified','corrected_after_visual_review'}:
            continue
        gt = sample['ground_truth']
        if not re.fullmatch(r'\d{8}',str(gt.get('code'))) or not re.fullmatch(r'\d{8}',str(gt.get('prerequisite'))):
            continue
        pages = [re.fullmatch(re.escape(sample['source_pdf']) + r' p\.(\d+) description',line) for line in sample.get('review_evidence') or []]
        pages = [int(match.group(1)) for match in pages if match]
        if len(pages) != 1:
            raise ValueError('Approved prerequisite requires one explicit description page: ' + sample['sample_id'])
        key = (sample['source_pdf'],pages[0],(gt['code'],))
        if key in keys:
            for item in result['documents']:
                if (item['source_file'],item['page_number'],tuple(item['codes'])) == key:
                    item['name_th_by_code'] = {gt['code']:gt['name_th']}
            continue
        result['documents'].append({'source_file':sample['source_pdf'],'program':sample['program'],
            'curriculum_version':sample['curriculum_version'],'sha256':sources[sample['source_pdf']],
            'page_number':pages[0],'printed_page_number':None,'codes':[gt['code']],
            'requires':[gt['prerequisite']],'status':'required','review_status':'visually_verified',
            'name_th_by_code':{gt['code']:gt['name_th']},
            'review_evidence':sample['review_evidence'],'review_sample_id':sample['sample_id']})
        keys.add(key)
        added += 1
    result['scope'] = 'Current DSBA/IT three NONE facts per book plus already visually approved prerequisite-bearing A1 description rows only; not full coverage or registration permission.'
    stage = args.output.with_suffix('.partial')
    stage.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    stage.replace(args.output)
    print(f'Added {added} independently reviewed prerequisites; {len(result["documents"])} review records total')


if __name__ == '__main__':
    main()
