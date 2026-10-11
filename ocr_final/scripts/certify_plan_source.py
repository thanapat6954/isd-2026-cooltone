"""Record a disclosed source-validation receipt after a complete visual review.

This is not automatic accuracy certification and does not correct any facts.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.database_build import read,write,sha
from scripts.source_native import validate_sql_chain
from lab10_fastapi.curriculum_app.build_scope import contract,PLAN_CHECKS


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--reviewer',required=True)
    p.add_argument('--confirm-reviewed-all-fields',action='store_true',
                   help='Attest inspection of cover, every source plan row, codes/names/credits/alternatives/pages; not a substitute for review')
    a=p.parse_args(); candidate=a.candidate.resolve(); manifest=read(candidate/'build.json')
    encoding = manifest.get('reviewed_input_scope') == 'font-encoding-only; no course corrections'
    if contract(manifest)['kind']!='academic-plan-only' or not (
            manifest['origin']=='fresh-raw' or (manifest['origin']=='fresh-reviewed' and encoding)):
        raise ValueError('This receipt helper supports raw or explicit font-encoding-only reviewed plan builds')
    if not a.confirm_reviewed_all_fields or not a.reviewer.strip():
        raise ValueError('ต้องตรวจภาพ identity.png และทุก page-*.png เทียบ page-*.plan.json/SQLite ก่อน; แล้วระบุ --reviewer และ --confirm-reviewed-all-fields')
    receipt={'scope':'disclosed independent visual source validation; no factual corrections',
             'reviewer':a.reviewer,'profiles':{}}
    for item in manifest['databases']:
        extraction=read(candidate/item['extraction'])
        native = extraction.get('extraction_method')=='pdf-text-tables'
        raster = extraction.get('normalization_method')=='deterministic-physical-table-parser'
        if not (native or raster) or extraction.get('pending_pages') or extraction.get('material_defects'):
            raise ValueError('Complete source-table extraction required; errors cannot be certified away')
        if encoding and native and (len(extraction.get('reviewed_corrections',[]))!=1 or
                         extraction['reviewed_corrections'][0].get('kind')!='reviewed-font-encoding'):
            raise ValueError('Encoding-only receipt cannot certify course corrections')
        validate_sql_chain(candidate,item)
        if sha(candidate/item['path'])!=item['sha256']:
            raise ValueError('SQLite hash changed; review receipt refused')
        raw=candidate/'raw'/item['profile']; proof=raw/'identity.png'
        if not proof.exists():
            raise ValueError('Source cover image missing; rebuild into new staging')
        evidence=[{'pdf_page':1,'path':proof.relative_to(candidate).as_posix(),'sha256':sha(proof)}]
        for number in extraction['pages']:
            image=raw/f'page-{number}.png'
            evidence.append({'pdf_page':number,'path':image.relative_to(candidate).as_posix(),'sha256':sha(image)})
        if (raw/'selection-rule.json').exists():
            rule = read(raw/'selection-rule.json'); image = raw/'selection-rule.png'
            evidence.append({'pdf_page':rule['pdf_page'],'path':image.relative_to(candidate).as_posix(),'sha256':sha(image)})
        receipt['profiles'][item['profile']]={'database_sha256':item['sha256'],
            'source_sha256':extraction['source_sha256'],'verified_fields':sorted(PLAN_CHECKS),
            'unresolved_defects':[],'evidence':evidence,
            'notes':['Reviewer attests complete visual comparison; certification is not automatic extraction accuracy',
                     'Plan prerequisites remain unknown; catalog/rules/legacy excluded']}
    if set(receipt['profiles'])!=set(manifest['requested_profiles']):
        raise ValueError('Partial/missing profile extraction cannot receive a complete receipt')
    if (candidate/'source-validation.json').exists():
        raise FileExistsError('Existing validation receipt preserved; use a new staging build')
    write(candidate/'source-validation.json',receipt)
    print('บันทึก source-validation.json แล้ว; ใช้ validate --scope declared ก่อน activate-scoped')


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError) as exc:
        print(str(exc),file=sys.stderr); raise SystemExit(1)
