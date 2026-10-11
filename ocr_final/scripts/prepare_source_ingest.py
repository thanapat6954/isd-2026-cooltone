"""Apply independent production book approvals to a NEW ingestion copy only."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.apply_reviewed_plan_term import apply_review


def prepare(input_path, pdf, review_path, profile, output):
    if output.resolve() in {input_path.resolve(), pdf.resolve(), review_path.resolve()} or output.exists():
        raise ValueError('Never overwrite source, OCR, approvals or existing output')
    approvals = json.loads(review_path.read_text(encoding='utf-8'))
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != approvals['source_sha256']:
        raise ValueError('Changed official source; repeat review')
    data = json.loads(input_path.read_text(encoding='utf-8'))
    for review in approvals['profiles'][profile]:
        if review['source_file'] != pdf.name:
            raise ValueError('Wrong book identity')
        if review.get('kind') == 'field_correction':
            if review.get('status') != 'visually_verified':
                raise ValueError('Unverified field correction')
            if not {'code','year','semester','source_file','page_number'} <= set(review['match']):
                raise ValueError('Field correction needs explicit original row and source-page identity')
            if review['match']['source_file'] != pdf.name or review['match']['page_number'] != review['pdf_page']:
                raise ValueError('Field correction crosses source pages')
            matches = [row for row in data.get('courses', []) if all(
                row.get(key) == value for key, value in review['match'].items())]
            if len(matches) != 1:
                raise ValueError('Source correction must identify exactly one original row')
            if not set(review['changes']) <= {'code', 'credits'}:
                raise ValueError('Unsupported field correction')
            matches[0].update(review['changes'])
            matches[0]['printed_page_number'] = review['printed_page']
            data.setdefault('reviewed_ingest_corrections', []).append(review)
            continue
        data = apply_review(data, {**review, 'source_sha256': approvals['source_sha256'],
                                  'input_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest()})
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    for name in ('input','pdf','reviews','output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--profile', required=True)
    a = p.parse_args()
    prepare(a.input,a.pdf,a.reviews,a.profile,a.output)


if __name__ == '__main__':
    main()
