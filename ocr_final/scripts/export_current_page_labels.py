"""Export only independently reviewed cells; no DB/OCR inputs or production writes."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(profile):
    if (profile['program'], profile['version'], profile['plan']) not in {
        ('BIT', 2565, 'coop'), ('BIT', 2565, 'no-coop'), ('AI', 2566, 'coop')
    }:
        raise ValueError('Identity not reviewed')
    keys = [(t['year'], t['semester']) for t in profile['terms']]
    if set(keys) != {(y, s) for y in range(1, 5) for s in (1, 2)} or len(keys) != 8:
        raise ValueError('Expected eight unique reviewed semesters')
    validate_term_credits(profile['terms'])
    if sum(t['printed_credits'] for t in profile['terms']) != profile['printed_total']:
        raise ValueError('Printed program total mismatch')


def validate_term_credits(terms):
    for term in terms:
        groups = {}
        total = 0
        for row in term['rows']:
            if not re.fullmatch(r'[0-9xX]{8}', row[0]):
                raise ValueError('Invalid printed code')
            value = int(re.match(r'\d+', row[1]).group())
            if len(row) == 3:
                if row[2] in groups and groups[row[2]] != value:
                    raise ValueError('Unequal alternative credits require manual review')
                groups[row[2]] = value
            else:
                total += value
        if total + sum(groups.values()) != term['printed_credits']:
            raise ValueError('Printed term total mismatch')


def export(observations, inventory, evidence, app):
    renders = {(r['source_file'], r['pdf_page']): r for r in inventory['renders']}
    results = []
    for profile in observations['profiles']:
        validate(profile)
        terms = []
        cases = []
        for term in profile['terms']:
            render = renders[profile['source_file'], term['pdf_page']]
            image = evidence / 'source_pages' / render['image']
            if hashlib.sha256(image.read_bytes()).hexdigest() != render['image_sha256']:
                raise ValueError('Reviewed image changed')
            source = app / 'data/input' / profile['source_file']
            if hashlib.sha256(source.read_bytes()).hexdigest() != render['sha256']:
                raise ValueError('Source changed')
            proof = {'source_file': profile['source_file'], 'source_sha256': render['sha256'],
                     'pdf_page': term['pdf_page'], 'printed_page': term['printed_page'],
                     'image': image.name, 'image_sha256': render['image_sha256'],
                     'review_status': 'manually_inspected_rendered_image'}
            terms.append({**term, **proof, 'expected_options': [
                {'code': r[0], 'credits_raw': r[1], 'alternative_group': r[2] if len(r) == 3 else None,
                 'source_row_index': i} for i, r in enumerate(term['rows'])]})
            common = {'source': profile['source_file'], 'page': term['pdf_page'],
                      'book_page': term['printed_page'], 'label_evidence': proof}
            cases.append({**common, 'question': f'ปี {term["year"]} ภาคการศึกษาที่ {term["semester"]} เรียนกี่หน่วยกิต',
                          'credits': term['printed_credits'], 'level': 'L2'})
            if term['year'] == term['semester'] == 1:
                for code, raw, *_ in term['rows'][:5]:
                    cases.append({**common, 'question': f'วิชา {code} มีกี่หน่วยกิต', 'code': code,
                                  'credits': int(re.match(r'\d+', raw).group()), 'level': 'L1'})
        identity = {k: profile[k] for k in ('program', 'version', 'plan')}
        folder = app / 'data/ground_truth/evaluation' / f'{profile["program"]}-{profile["version"]}'
        data = {'schema_version': 1, 'purpose': 'partial_source_evaluation', 'identity': identity,
                'source_file': profile['source_file'], 'printed_total': profile['printed_total'],
                'verified_fields': observations['verified_fields'], 'unverified_fields': observations['unverified_fields'],
                'plan_evidence': profile.get('plan_evidence'), 'terms': terms}
        gold = {'schema_version': 1, 'purpose': observations['purpose'], 'identity': identity,
                'unverified_levels': ['L3', 'L4'], 'groups': [{
                    'program': profile['program'], 'versions': [profile['version']],
                    'plans': [profile['plan']], 'cases': cases}]}
        folder.mkdir(parents=True, exist_ok=True)
        for suffix, payload in [('terms', data), ('qa', gold)]:
            path = folder / f'{profile["plan"]}-{suffix}.json'
            serialized = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
            if path.exists() and path.read_text(encoding='utf-8') != serialized:
                raise ValueError(f'Refusing to replace changed labels: {path}')
            path.write_text(serialized, encoding='utf-8')
        results.append({'identity': identity, 'terms': len(terms), 'options': sum(len(t['rows']) for t in terms), 'qa_n': len(cases)})
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--app-root', type=Path, default=ROOT)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    observations = json.loads((ROOT / 'data/ground_truth/evaluation/current-page-observations.json').read_text(encoding='utf-8'))
    result = export(observations, json.loads(a.inventory.read_text(encoding='utf-8')), a.inventory.parent, a.app_root)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
