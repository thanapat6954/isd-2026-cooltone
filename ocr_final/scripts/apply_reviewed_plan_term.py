"""Apply a visually reviewed table to a NEW ingest copy, never the OCR baseline."""

import argparse
import copy
import hashlib
import json
from pathlib import Path


def apply_review(data: dict, review: dict) -> dict:
    if review.get('status') != 'visually_verified':
        raise ValueError('Only visually verified reviews may repair ingest data')
    if len(review['rows']) != review['row_count']:
        raise ValueError('Reviewed row count does not match the supplied rows')
    # Combined cells must be split by the reviewer, with explicit shared groups.
    if any('หรือ' in row['code'] or ' or ' in row['code'].lower() for row in review['rows']):
        raise ValueError('Alternative-group reviews require a group-aware tool')
    groups = {}
    for index, row in enumerate(review['rows']):
        credit = int(row['credits'].split('(')[0])
        group = row.get('alt_group') or f'row-{index}'
        if group in groups and groups[group] != credit:
            raise ValueError('Alternative choices disagree on counted credit value')
        groups[group] = credit
    total = sum(groups.values())
    if total != review['credits']:
        raise ValueError('Reviewed credits do not match the printed total')
    result = copy.deepcopy(data)
    def is_term(row):
        return (row.get('year'), row.get('semester')) == (review['year'], review['semester'])
    existing = [row for row in result.get('courses', []) if is_term(row)]
    if any(row.get('source_file') != review['source_file'] for row in existing):
        raise ValueError('Reviewed term crosses source files')
    result['courses'] = [row for row in result.get('courses', []) if not is_term(row)]
    for row in review['rows']:
        result['courses'].append({**row, 'year': review['year'], 'semester': review['semester'],
                                  'source_file': review['source_file'], 'page_number': review['pdf_page'],
                                  'printed_page_number': review.get('printed_page'),
                                  'prerequisite': None})
    totals = [row for row in result.get('term_totals', []) if not is_term(row)]
    totals.append({key: review[key] for key in ('year', 'semester', 'credits', 'row_count')}
                  | {'page_number': review['pdf_page'], 'source_file': review['source_file']})
    result['term_totals'] = totals
    result.setdefault('reviewed_ingest_corrections', []).append(review)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--review', type=Path, nargs='+', required=True)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {args.input.resolve(), args.pdf.resolve(), *(p.resolve() for p in args.review)}:
        raise ValueError('Output must not overwrite any source')
    result = json.loads(args.input.read_text(encoding='utf-8'))
    for review_path in args.review:
        review = json.loads(review_path.read_text(encoding='utf-8'))
        for path, key in ((args.input, 'input_sha256'), (args.pdf, 'source_sha256')):
            if hashlib.sha256(path.read_bytes()).hexdigest() != review[key]:
                raise ValueError(f'Hash mismatch for {path}; review must be repeated')
        result = apply_review(result, review)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Reviewed ingest copy: {args.output}; original OCR unchanged')


if __name__ == '__main__':
    main()
