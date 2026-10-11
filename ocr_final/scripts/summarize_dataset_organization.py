"""Evidence-backed Thai report and preservation guards; no SQLite writes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--app-root',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True);p.add_argument('--repository',type=Path,default=ROOT.parent)
    a=p.parse_args();e=a.evidence;repo=a.repository.resolve();app=a.app_root.resolve()
    validation=load(e/'repository/validation_release.json')
    before=load(e/'gold.json')['dependencies'];gold=load(e/'gold_final.json')
    db_guard={name:sha(app/name)==digest for name,digest in before['databases'].items()}
    code_guard={name:sha(app/'lab10_fastapi/curriculum_app'/name)==digest for name,digest in before['code'].items()}
    sources=load(repo/'docs/results/week11_continuation/inventory.json')['sources']
    source_guard={r['source_file']:sha(app/'data/input'/r['source_file'])==r['sha256'] for r in sources}
    protected=subprocess.run(['git','diff','--name-only','--','ocr_final/tests/*.json'],cwd=repo,capture_output=True,text=True,encoding='utf-8',check=True).stdout.strip()
    guards={'runtime_databases':db_guard,'runtime_code':code_guard,'source_pdfs':source_guard,
            'protected_tracked_test_json_unchanged':not protected,'changed_protected_paths':protected}
    (e/'preservation.json').write_text(json.dumps(guards,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not all([*db_guard.values(),*code_guard.values(),*source_guard.values(),not protected]):raise ValueError('Preservation failure')
    old=[load(p) for p in sorted((e/'local_qa').glob('new_qa_*.json'))]
    old_pass=sum(sum(r['passed'] for r in d['cases']) for d in old);old_n=sum(len(d['cases']) for d in old)
    old_summary={key:value for d in old for key,value in d['summary'].items()}
    gp=sum(r['passed'] for r in gold['cases']);gn=len(gold['cases'])
    unit_log=(e/'unit_final.log').read_text(encoding='utf-8')
    if not re.search(r'^OK$',unit_log,re.M):raise ValueError('Unit result is not a passing run')
    unit=int(re.search(r'Ran (\d+) tests',unit_log).group(1))
    schema=re.search(r'ผ่าน (\d+) / ไม่ผ่าน (\d+)',(e/'schema_final.log').read_text(encoding='utf-8'))
    frontend=re.search(r'pass (\d+)',(e/'frontend_final.log').read_text(encoding='utf-8'))
    if schema.group(2)!='0' or not re.search(r'fail 0',(e/'frontend_final.log').read_text(encoding='utf-8')):
        raise ValueError('Schema/frontend result is not a passing run')
    ui=load(e/'ui.json');ui_pass=sum(c.get('scope_verified',False) for c in ui['cases'])
    unknown=sum(c.get('printed_page_unverified',False) for c in ui['cases'])
    ledger=load(e/'term_export_with_qa.json');fields=load(e/'fields_export.json')
    live=load(e/'live/validation_release.json')
    flat_profiles=[r for r in validation['profiles'] if r.get('flat_labels')]
    identical=sum(r['flat_duplicate_review']['identical_row_excess'] for r in flat_profiles)
    collisions=sum(r['flat_duplicate_review']['course_placement_key_collisions'] for r in flat_profiles)
    flat_n=sum(r['flat_row_count'] for r in flat_profiles)
    lines=['# การจัดชุดข้อมูลและความครอบคลุม Ground Truth', '',
      '## ขอบเขตและสถานะ', '',
      'ทำงานเฉพาะ local branch `week11_thanapat` ไม่ commit/push/merge ไม่แก้ main และไม่เปลี่ยนข้อเท็จจริงใน DB การใช้ curriculum-audit ช่วยแยก source review, development และ held-out พร้อมตรวจหลักฐานก่อนย้ายไฟล์', '',
      '**การจัด directory และการนำ labels เดิมที่มี approval กลับมาใช้เสร็จใน batch นี้ แต่ Ground Truth ครบทั้งเล่มยังไม่เสร็จ** การย้ายไฟล์/ผ่าน schema ไม่ใช่การยืนยันข้อมูลกับภาพหนังสือใหม่', '',
      '## ชื่อเดิม → ความหมายจริง → ตำแหน่งใหม่', '',
      'ดู [ตารางภาษาไทยพร้อมลิงก์ไฟล์จริง](../ocr_final/data/ground_truth/README.md) และ [catalog](../ocr_final/data/ground_truth/catalog.json)', '',
      f"- ตรวจและย้าย JSON เดิมใน repository {len(validation['migration'])} ไฟล์ และ live app {len(live['migration'])} ไฟล์: SHA และ JSON payload เดิมตรงกันทุกไฟล์ ไม่มีการลบ labels",
      '- AIT labels เดิมใช้กับ AI ผ่าน profile mapping และ approval ปก AI.pdf ที่ระบุ 2566; IT labels ใช้กับ IT.pdf รุ่น 2565 เป็นคนละหลักสูตร ไม่ใช่สหกิจ/ไม่สหกิจของหลักสูตรเดียวกัน',
      '- AIT labels เดิมมี plan=null จึงไม่ถือว่าข้อมูลนี้พิสูจน์ว่า source book ไม่แยกแผน; coop ของ AI เป็น runtime configuration ที่ยังต้องตรวจ plan coverage ให้ครบ',
      '- DSBA master ใช้ ingestion สองแผน ไม่ใช่ evaluation โดยอัตโนมัติ; flat DSBA/IT files ใช้ Lab 7 metrics; general-education pool ใช้ ingestion แต่ PDF provenance ยังไม่ครบ',
      '- rules shared ยังไม่ยืนยันปี/page ราย label; versioned_eval_questions อยู่ history เฉพาะ live app และสร้างจาก DB จึงไม่ใช่ independent ground truth/held-out ส่วน scripts ที่ consume ไฟล์นั้นถูกย้าย path แล้ว',
      '- หน้าที่/metadata/schema/counts และ references ใน code, scripts, tests, docs, checkpoints เก็บใน inventory.json ทั้งสอง root; ตรวจ recursive discovery ของ inventory และ explicit dataset paths ของ loaders แล้ว ไม่ย้าย backups เข้าบริเวณ discovery', '',
      f'- ตรวจ flat labels {flat_n} แถว: identical-row duplicates {identical}; code/year/semester key collisions {collisions} เป็น review candidates ไม่ใช่เหตุให้ลบ เพราะ wildcard slots/alternatives/tracks อาจซ้ำ key โดยถูกต้อง; จำนวน missing fields เก็บราย profile ใน catalog/validation', '',
      '## Labels ที่เพิ่มจากหลักฐานเดิม', '',
      f"- terms datasets {len(ledger)} ชุด ครอบคลุม {sum(x['terms'] for x in ledger)} semesters / {sum(x['rows'] for x in ledger)} printed options จาก ledger ภาพที่ตรวจไว้เดิม ตรวจ source/image SHA ก่อน reuse; options ไม่เท่ากับจำนวนวิชาที่ต้องเรียน เพราะมี alternatives/tracks",
      f"- reviewed-fields datasets {len(fields)} ชุด / {sum(x['labels'] for x in fields)} observations ใช้เฉพาะ approval ชื่อและ prerequisite เดิม ตรวจ SHA และเก็บ PDF/book page; printed page ที่ไม่ทราบยังเป็น null ไม่เดา offset",
      f"- source-backed development L1/L2 questions {old_n} ข้อ แยกทั้งหกแผน 2560; expected credits/term totals มาจาก printed ledger ไม่ได้ export จาก DB ไม่เปลี่ยน protected labels และไม่เรียกชุดนี้ว่า held-out", '',
      '## ความครอบคลุมทุกหลักสูตร/ปี/แผน', '',
      '| profile | flat labels | reviewed terms | source QA ใน batch นี้ | สถานะที่ยังขาด |', '|---|---|---|---|---|']
    for row in validation['profiles']:
        identity='-'.join(str(row[k]) for k in ('program','curriculum_version','plan')) if row.get('program') else 'legacy'
        result=old_summary.get(identity)
        q=f"{result['passed']}/{result['n']}" if result else 'n/a'
        flat=str(row.get('flat_row_count')) if row.get('flat_labels') else 'n/a'
        terms=str(row['reviewed_term_count']) if row['reviewed_term_count'] else 'n/a'
        lines.append(f"| {identity} | {flat} แถว".replace('n/a แถว','n/a')+f" | {terms} | {q} | "+('identity/ปี/แผนและ independent content labels ยังไม่ยืนยัน' if identity=='legacy' else 'full names/category/prerequisites/เงื่อนไขจบ และ independent L3–L4 ยังไม่ครบ')+' |')
    lines += ['', '## ผลการตรวจและข้อจำกัด', '',
      f'- unit {unit}/{unit}, schema {schema.group(1)}/{schema.group(1)} (ไม่ผ่าน {schema.group(2)}), frontend {frontend.group(1)}/{frontend.group(1)}; logs เก็บแยกจาก source data',
      f'- existing gold {gp}/{gn} ครอบคลุมทุก catalog ตามชุดเดิม; legacy เป็น safety/uncertainty checks ไม่ใช่ book-content accuracy',
      f'- new source-backed development {old_pass}/{old_n}; ไม่ใช่ generalization score หรือชุด frozen ใหม่',
      f'- actual browser {ui_pass}/{len(ui["cases"])} profile metadata responses แสดง curriculum/version/plan ตรงกับที่เลือก; console warnings/errors {len(ui["console"])}; ยังมี {unknown}/{len(ui["cases"])} program-total responses ที่ printed page ไม่ยืนยัน จึงไม่อ้าง citation ครบ',
      f'- runtime DB fingerprints {sum(db_guard.values())}/{len(db_guard)}, runtime code {sum(code_guard.values())}/{len(code_guard)}, source PDF {sum(source_guard.values())}/{len(source_guard)} คงเดิม; protected tracked JSON expectations ไม่มี diff',
      '- ingestion identity/name/prerequisite loaders ใช้ default paths ใหม่ได้ใน dry run exit0 โดยไม่ --apply และไม่เปลี่ยน DB; ไม่ได้ rebuild production DB ทั้งหมดใน batch นี้',
      '- readonly audit ก่อน/หลังยัง 16 datasets, FAIL1372 / incomplete4881, exit1; ไม่ถือเป็นจำนวนคำตอบผิดหรือผลผ่าน การจัด folder ไม่แก้ legacy/source coverage ที่ยังเปิดอยู่',
      '- first gold run เริ่มขณะ backend หยุด เก็บ failure ไว้แล้ว หลังเปิดจริง rerun ผ่าน; source QA ครั้งแรก runner ตรวจ printed page ของ aggregate ไม่เป็น จึงแก้ paired page_evidence checker พร้อม tests โดยไม่แก้ expected values',
      '- OneDrive result replacement error ถูกเก็บไว้พร้อม partial; รอบใหม่ใช้ temporary local output แล้ว copy ผลกลับ ไม่ทับ evidence ที่ล้มเหลว ไม่พบ git lock/index failure', '',
      '## การลบและ recovery', '',
      '- ไม่ลบไฟล์ข้อมูลที่พิสูจน์ไม่ได้ว่าเกินความจำเป็น; files เดิมเป็น relocation ไม่ใช่ discard เก็บสำเนา SHA ตรงกันภายนอก active discovery ใน docs/results/dataset_organization/{repository,live}/recovery/',
      '- migration_final.json ระบุ old/intermediate/new paths และ recovery; original inventories ไม่ถูกแก้ย้อนหลัง Recovery consumers อยู่ในสำเนาเดิม; หากย้อนกลับ ต้องคืน paths และ consumers พร้อมกัน ไม่แตะ DB',
      '- historical report IDs/ชื่อเดิมใน prose เก็บเพื่อเทียบผลย้อนหลัง และใช้ index เป็น migration mapping; ACTION_ITEMS_STATUS เปลี่ยนเฉพาะ path ของ pool ใหม่', '',
      '## วิธีตรวจซ้ำ', '',
      'จาก repository root ใช้ environment ตาม README (source PDFs/runtime DBs ไม่อยู่ Git):', '', '```powershell',
      'python ocr_final/scripts/validate_dataset_layout.py --app-root ocr_final --output validation.json',
      '# Local pre/post preservation checks additionally use --migration <migration_final.json>',
      'python ocr_final/scripts/run_qa_gold.py --app-root <LIVE_APP> --runs 1 --output gold.json',
      'python ocr_final/scripts/run_qa_gold.py --app-root <LIVE_APP> --gold ocr_final/data/ground_truth/evaluation/IT-2560/coop-qa.json --runs 1 --output it_old_source.json',
      '# Repeat the last command for all six *-2560/*-qa.json files.',
      'python ocr_final/scripts/audit_all.py --app-root <LIVE_APP> --out reports',
      '```', '',
      'Raw evidence: docs/results/dataset_organization/ (inventory, migration manifests, validation, preservation, audit, gold, local_qa, UI JSON/PNG, logs) เป็น local evidence ยังไม่ publish', '',
      '## งานที่ยังต้องทำ', '',
      '- เริ่ม BIT-2565 rendered academic-plan pages 26–35 เพื่อสร้าง flat/field labels ทั้งสองแผน แล้วตรวจ AI-2566 pages 23–26 เพื่อยืนยัน plan coverage ไม่ใช้ filename/DB เป็น GT',
      '- เติม names/categories/elective/track relationships/prerequisites/graduation conditions ที่ยังขาดจากภาพหนังสือทุกเวอร์ชัน รวม legacy identity; approvals/labels ใหม่ต้องมี page/hash และ review scope',
      '- independent L3/L4 และ frozen held-out ใหม่ยัง n/a; ไม่มีหลักฐาน same-year revision/dual-degree เพิ่ม จึงไม่แต่ง rules หรือ registration permissions',
      '- ตัว validator ผ่านไม่ได้แปลว่า source verification ครบ; dataset schema เดิมเก็บ byte-identical และใช้ catalog เป็น metadata/coverage mapping ไม่เปลี่ยนรูปแบบเฉลยย้อนหลัง', '']
    (repo/'docs/DATASET_ORGANIZATION.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'guards_pass':True,'db_files':len(db_guard),'unit':unit,'existing_gold':[gp,gn],'source_gold':[old_pass,old_n],'ui':[ui_pass,len(ui['cases'])]}))

if __name__=='__main__':main()
