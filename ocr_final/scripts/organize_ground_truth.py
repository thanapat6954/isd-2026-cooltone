"""Inventory and losslessly separate label/ingestion files; never edit facts or DBs."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Purposes established by content AND consumers, not filename inference.
LAYOUT = {
    'AIT_academic_plan.json': ('data/ground_truth/evaluation/AI-2566/academic_plan.json', 'evaluation', 'run_lab8b.PROFILES.ai; document_identity_reviews cover PDF1', 'ยังไม่ยืนยันทุกแถว; plan=null ใน labels ไม่ได้ยืนยันว่าเล่มไม่แยกแผน'),
    'DSBA_academic_plan_coop.json': ('data/ground_truth/evaluation/DSBA-2565/coop.json', 'evaluation', 'run_lab8b.PROFILES.dsba-coop; DSBA unified source_pages_by_plan', 'derived labels; ไม่ใช่หลักฐานอิสระครบทุก field'),
    'DSBA_academic_plan_no_coop.json': ('data/ground_truth/evaluation/DSBA-2565/no-coop.json', 'evaluation', 'run_lab8b.PROFILES.dsba-no-coop; DSBA unified source_pages_by_plan', 'derived labels; ไม่ใช่หลักฐานอิสระครบทุก field'),
    'IT_academic_plan_coop.json': ('data/ground_truth/evaluation/IT-2565/coop.json', 'evaluation', 'run_lab8b.PROFILES.it-coop; IT.pdf reviewed study-plan pages', 'labels จาก spreadsheet; ยังไม่ยืนยันทุกแถว'),
    'IT_academic_plan_no_coop.json': ('data/ground_truth/evaluation/IT-2565/no-coop.json', 'evaluation', 'run_lab8b.PROFILES.it-no-coop; IT.pdf reviewed study-plan pages', 'labels จาก spreadsheet; ยังไม่ยืนยันทุกแถว'),
    'DSBA_ground_truth.json': ('data/source_reviews/DSBA-2565/master.json', 'ingestion', 'run_lab8b lab8_input; source_file + plans + schedule_by_plan', 'historical clean import; ไม่ถือว่าทุก field visually verified'),
    'general_education_ground_truth.json': ('data/source_reviews/shared/general_education_ground_truth.json', 'ingestion', 'run_lab8b --general-education', 'ยังขาด PDF provenance; ชื่อ directory ไม่ยืนยันข้อเท็จจริง'),
    'document_identity_reviews.json': ('data/source_reviews/shared/document_identity_reviews.json', 'ingestion', 'ingest_identity_reviews.py; AI.pdf cover PDF1', 'source-reviewed identity เฉพาะที่มี approval'),
    'prerequisite_source_reviews.json': ('data/source_reviews/shared/prerequisite_source_reviews.json', 'ingestion', 'ingest_prerequisite_reviews.py; documents/source hashes/pages', 'source-reviewed subset ไม่ใช่วิชาบังคับก่อนครบทั้งเล่ม'),
    'old2560_name_reviews.json': ('data/source_reviews/shared/old2560_name_reviews.json', 'ingestion', 'ingest_name_reviews.py; source-specific approved rows', 'source-reviewed subset เท่านั้น'),
    'study_plan_relationships.json': ('data/source_reviews/shared/study_plan_relationships.json', 'relationships', 'migrate_study_evidence.py; approval study_plan_db_review.json', 'approved page/term subset ไม่ใช่ครบทุก track'),
    'study_plan_db_review.json': ('data/source_reviews/shared/study_plan_db_review.json', 'approval', 'migrate_study_evidence.py; ingestion_sha256 and approved_pages', 'approval/provenance ไม่ใช่ evaluation answers'),
    'rules_ground_truth.json': ('data/ground_truth/shared/rules.json', 'evaluation-unverified', 'content programs/rules from spreadsheet; no verified per-label page mapping', 'ปี/revision/page ของแต่ละ label ยังไม่ยืนยัน; ห้ามใช้เป็น production facts'),
    'versioned_eval_questions.json': ('data/ground_truth/history/versioned_eval_questions.json', 'development-history', 'generate_version_eval.py derives labels from DB; evaluate_versioned_questions.py', 'DB-derived development cases ไม่ใช่ independent ground truth หรือ held-out'),
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def records(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from records(child)
    elif isinstance(value, list):
        for child in value:
            yield from records(child)

def inspect(root, search_root):
    result = []
    for path in sorted((root/'data/ground_truth').rglob('*')):
        if not path.is_file():
            continue
        meta = LAYOUT.get(path.name)
        data = json.loads(path.read_text(encoding='utf-8-sig')) if path.suffix == '.json' else {}
        rows = list(records(data))
        command = ['rg', '-n', '-F', path.name, str(search_root), '--glob', '*.py', '--glob', '*.ps1', '--glob', '*.md', '--glob', '*.json', '--glob', '!work/**', '--glob', '!docs/results/**', '--glob', '!docs/public_results/**', '--glob', '!reports/**', '--glob', '!venv/**']
        scan = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        if scan.returncode not in (0, 1):
            raise RuntimeError(scan.stderr)
        result.append({'old_path':path.relative_to(root).as_posix(), 'sha256':sha(path), 'bytes':path.stat().st_size,
            'destination':meta[0] if meta else None, 'purpose':meta[1] if meta else 'unknown-preserve',
            'identity_evidence':meta[2] if meta else None, 'verification':meta[3] if meta else 'unverified',
            'schema':sorted(data) if isinstance(data, dict) else 'list',
            'record_counts':{key:sum(key in r for r in rows) for key in ('code','course_code','question','page_number','pdf_page','printed_page_number','prerequisite')},
            'identity_metadata':{key:sorted({str(r[key]) for r in rows if key in r}) for key in ('program','curriculum_version','plan','source_file')},
            'consumers_and_references':scan.stdout.splitlines(), 'required':'uncertain; preserve' if not meta else 'retained; migrated, not deleted'})
    return result

def rewrite(text):
    for name, (target, *_) in LAYOUT.items():
        # Rewrite concrete paths only; preserve factual source_file names/historical IDs.
        text = text.replace('data/ground_truth/'+name, target)
        parts = target.split('/')
        for quote in ('"', "'"):
            old = f'{quote}data{quote} / {quote}ground_truth{quote} / {quote}{name}{quote}'
            new = ' / '.join(quote+p+quote for p in parts)
            text = text.replace(old, new)
    # Active inventory must recursively discover the organized label directories.
    text = text.replace("(root / 'data/ground_truth').glob('*.json')", "(root / 'data/ground_truth').rglob('*.json')")
    return text

def migrate(root, inventory, backup):
    changed=[]
    for item in inventory:
        if not item['destination']:
            continue
        old, new = root/item['old_path'], root/item['destination']
        if new.exists():
            raise ValueError(f'Refusing to overwrite {new}')
        recover = backup/item['old_path']
        recover.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old, recover)
        if sha(recover) != item['sha256']:
            raise ValueError('Backup mismatch')
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old), str(new))
        if sha(new) != item['sha256']:
            raise ValueError('Migration changed labels')
    candidates = [root/'run_lab8b.py', root/'robustness_eval.py', root/'generate_program_gold.py', root/'README.md']
    for folder in ('scripts','tests','scr','lab10_fastapi'):
        candidates += [p for p in (root/folder).rglob('*') if p.suffix in {'.py','.ps1','.md'}]
    for path in candidates:
        if not path.is_file() or path.name in {'organize_ground_truth.py','test_ground_truth_layout.py'}:
            continue
        original=path.read_text(encoding='utf-8-sig')
        updated=rewrite(original)
        if updated != original:
            recover=backup/'consumers'/path.relative_to(root)
            recover.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,recover)
            path.write_text(updated,encoding='utf-8')
            changed.append(path.relative_to(root).as_posix())
    return changed

def index(root, inventory):
    purposes={'evaluation':'เฉลย evaluation','ingestion':'ข้อมูลสำหรับ ingestion','relationships':'ความสัมพันธ์ในแผน',
              'approval':'หลักฐาน approval','evaluation-unverified':'กฎ evaluation ที่ยังไม่ยืนยัน',
              'development-history':'ประวัติชุด development'}
    lines=['# ดัชนีข้อมูลสำหรับตรวจหลักสูตร', '',
        'แยก evaluation labels ออกจากข้อมูลที่ใช้ ingestion อย่างชัดเจน การย้ายไฟล์ไม่ใช่การยืนยันข้อมูลกับหนังสือ และไม่เปลี่ยนเฉลยเดิม', '',
        'สหกิจศึกษา = coop; ไม่สหกิจศึกษา = no-coop ส่วนไม่แยกแผนหมายถึง dataset ไม่ระบุแผน ไม่ใช่ข้อสรุปว่าเล่มไม่มีแผนอื่น', '',
        '`AIT` ใน labels เดิมถูกใช้กับ AI ผ่าน `run_lab8b.PROFILES.ai`; approval ปก AI.pdf หน้า PDF 1 ระบุ 2566 ส่วน IT ใช้ IT.pdf รุ่น 2565 จึงเป็นคนละหลักสูตร ไม่ใช่รุ่นของ IT (metadata plan ใน AIT เดิมเป็น null ยังต้องตรวจว่าครอบคลุมแผนใด)', '',
        '## ชื่อเดิมและตำแหน่งปัจจุบัน', '', '| ชื่อเดิม | ตำแหน่งใหม่ | หน้าที่และหลักฐาน identity | สถานะ |', '|---|---|---|---|']
    for item in inventory:
        dest=item['destination'] or item['old_path']
        relative=Path(dest).relative_to('data').as_posix()
        link='../'+relative if not relative.startswith('ground_truth/') else relative[len('ground_truth/'):]
        status=item['verification'].replace('derived labels;', 'labels ที่สร้างต่อจาก master;').replace('historical clean import;', 'ข้อมูล clean import เดิม;')
        evidence=(item['identity_evidence'] or 'ยังไม่ทราบ').replace('cover PDF1','ปก หน้า PDF 1').replace('from spreadsheet','จาก spreadsheet').replace('no verified per-label page mapping','ยังไม่มี page mapping ที่ยืนยันราย label').replace('derives labels from DB','สร้าง labels จาก DB').replace('reviewed study-plan pages','หน้าตารางแผนที่มี review').replace('source-specific approved rows','แถวที่มี approval แยก source')
        lines.append(f"| `{Path(item['old_path']).name}` | [{dest}]({link}) | {purposes.get(item['purpose'],'ยังไม่ทราบ')}: {evidence} | {status} |")
    lines += ['', '## ความครอบคลุมและข้อจำกัด', '',
        '- evaluation/ เก็บ labels รายหลักสูตร/ปี แยก plan; shared/ เก็บกฎที่ยังไม่ยืนยันปีและ page; history/ เก็บกรณี development ที่สร้างจาก DB ไม่ใช่ held-out',
        '- ../source_reviews/ เก็บ master, source approval และ relationships สำหรับ build/ingestion เท่านั้น runtime chatbot อ่าน SQLite ไม่อ่าน evaluation answers',
        '- evaluation/*-2560/*-terms.json คือ ledger เดิมจาก rendered pages: codes, credit patterns/options, term totals, PDF/book pages เท่านั้น ชื่อ/category/prerequisite/เงื่อนไขจบที่ไม่ได้ตรวจคงเป็น unknown ห้ามป้อนเข้า flat-course evaluator',
        '- BIT-2565 ทั้งสองแผนยังไม่มี flat evaluation labels; AI/DSBA/IT labels ปัจจุบันยังไม่ครบ field/source verification; legacy ยังไม่ยืนยัน identity จึงไม่สร้างปีหรือแผนขึ้นเอง',
        '- L1–L4: tests/qa_gold.json เป็น development regression; historical versioned questions สร้างจาก DB ไม่ใช่หลักฐานอิสระ; ยังไม่มีชุด source-grounded ครบทุกระดับและ frozen ใหม่',
        '- ไม่มีการลบ labels ที่ไม่ทราบหน้าที่ ไม่มีการแก้ DB/PDF/OCR/held-out; recovery เก็บนอก active dataset discovery ตาม migration manifest', '']
    (root/'data/ground_truth/README.md').write_text('\n'.join(lines),encoding='utf-8')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app-root',type=Path,default=ROOT)
    parser.add_argument('--search-root',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    root=args.app_root.resolve()
    inventory=inspect(root,(args.search_root or root).resolve())
    save(args.output,{'scope':'inventory; not independent source verification','files':inventory})
    if args.apply:
        changed=migrate(root,inventory,args.output.parent/'recovery'/root.name)
        index(root,inventory)
        save(args.output.with_name(args.output.stem+'_migration.json'),{'files':inventory,'changed_consumers':changed,'deletions':[], 'recovery':str(args.output.parent/'recovery'/root.name)})
    print(json.dumps({'files':len(inventory),'applied':args.apply},ensure_ascii=False))

def consolidate_source_directory(root, manifest_path):
    """Consolidate into the established source_reviews convention; preserve raw manifests."""
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    for item in manifest['files']:
        previous=item.get('destination') or ''
        if not previous.startswith('data/source_reviewed/'):
            continue
        target=previous.replace('data/source_reviewed/','data/source_reviews/',1)
        source,destination=root/previous,root/target
        if destination.exists():raise ValueError('Refusing existing destination')
        if sha(source)!=item['sha256']:raise ValueError('Migration dependency changed')
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(source),str(destination))
        item['intermediate_path']=previous
        item['destination']=target
    candidates=[root/'run_lab8b.py',root/'README.md']
    for folder in ('scripts','tests','data'):
        candidates += [p for p in (root/folder).rglob('*') if p.suffix in {'.py','.ps1','.md'}]
    for path in candidates:
        if not path.is_file() or path.name=='organize_ground_truth.py':continue
        before=path.read_text(encoding='utf-8-sig')
        after=before.replace('data/source_reviewed/','data/source_reviews/').replace("data/source_reviewed'","data/source_reviews'").replace('data/source_reviewed`','data/source_reviews`').replace('source_reviewed/', 'source_reviews/')
        for q in ('"',"'"):
            after=after.replace(q+'source_reviewed'+q,q+'source_reviews'+q)
        if after!=before:path.write_text(after,encoding='utf-8')
    readme=root/'data/source_reviewed/README.md'
    if readme.exists():
        shutil.move(str(readme),str(root/'data/source_reviews/README.md'))
    # Remove only empty intermediate directories, never data files.
    for folder in (root/'data/source_reviewed/shared',root/'data/source_reviewed/DSBA-2565',root/'data/source_reviewed'):
        if folder.exists() and not any(folder.iterdir()):folder.rmdir()
    final=manifest_path.with_name('migration_final.json')
    save(final,manifest)
    return final

if __name__=='__main__':
    main()
