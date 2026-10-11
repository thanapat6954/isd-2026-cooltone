"""Archive completed evaluation outputs without rewriting their observed results."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import zipfile

MANIFEST = 'EVIDENCE_MANIFEST.json'
README = 'EVIDENCE_README.md'
ZIP = 'evaluation-evidence.zip'
SUMS = 'SHA256SUMS.txt'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inside(root, relative):
    name = PurePosixPath(relative)
    path = root.joinpath(*name.parts)
    if name.is_absolute() or '..' in name.parts or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Evidence path escapes its folder')
    return path


def verify(root):
    root = root.resolve()
    document = json.loads((root/MANIFEST).read_text(encoding='utf-8'))
    expected = {}
    for record in document['files']:
        path = inside(root, record['path'])
        if not path.is_file() or path.stat().st_size != record['bytes'] or sha(path) != record['sha256']:
            raise ValueError('Missing or changed evidence: '+record['path'])
        if record['path'] in expected:
            raise ValueError('Duplicate manifest entry')
        expected[record['path']] = record['sha256']
    for name in (MANIFEST, README):
        expected[name] = sha(root/name)
    sums = {}
    for line in (root/SUMS).read_text(encoding='utf-8').splitlines():
        digest, name = line.split('  ', 1)
        sums[name] = digest
    if set(sums) != {ZIP, MANIFEST} or any(sha(root/name) != digest for name, digest in sums.items()):
        raise ValueError('ZIP or manifest checksum differs')
    with zipfile.ZipFile(root/ZIP) as bundle:
        if len(bundle.namelist()) != len(expected) or set(bundle.namelist()) != set(expected) or bundle.testzip():
            raise ValueError('ZIP inventory or CRC differs')
        for name, digest in expected.items():
            with bundle.open(name) as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != digest:
                raise ValueError('ZIP entry differs: '+name)
    actual_files = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()}
    if actual_files != set(expected) | {ZIP, SUMS}:
        raise ValueError('Unexpected evidence file inventory')
    return {'verified_files': len(document['files']), 'zip_sha256': sums[ZIP],
            'observed_jobs': document['observed_run']['jobs']}


def archive(source, destination, label='observed evaluation; not full-book accuracy'):
    source, destination = source.resolve(), destination.resolve()
    if destination.exists():
        raise FileExistsError('Evidence folder already exists; preserve it and choose a new folder')
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError('Source and evidence folders must be separate')
    summary = json.loads((source/'summary.json').read_text(encoding='utf-8-sig'))
    if not (source/'REPORT.md').is_file() or (source/MANIFEST).exists():
        raise ValueError('Expected a completed raw result folder with REPORT.md')
    paths = sorted(path for path in source.rglob('*') if path.is_file())
    records = []
    for path in paths:
        relative = path.relative_to(source).as_posix()
        inside(source, relative)
        if path.is_symlink() or path.suffix.casefold() in {'.db', '.pdf', '.exe', '.dll'} or path.name == '.env':
            raise ValueError('Result evidence must not include databases, PDFs or environment secrets')
        records.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': sha(path)})
    destination.mkdir(parents=True, exist_ok=False)
    for record in records:
        target = inside(destination, record['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inside(source, record['path']), target)
        if sha(target) != record['sha256'] or sha(inside(source, record['path'])) != record['sha256']:
            raise ValueError('Source changed during archival: '+record['path'])
    manifest = {'format_version': 1, 'label': label, 'archived_at_utc': datetime.now(timezone.utc).isoformat(),
                'raw_source_directory': str(source), 'archiver_python': sys.version,
                'observed_run': {'app_root': summary['app_root'], 'url': summary['url'],
                                 'suite': summary.get('suite', 'All'), 'check_only': summary.get('check_only', False),
                                 'real_ui_checked': summary.get('real_ui_checked', False), 'jobs': summary['jobs']},
                'files': records,
                'limits': ['Checksums establish file integrity, not source-book accuracy or independent replication.',
                           'Original machine paths and test counts are preserved; new runs may differ.',
                           'Failed and incomplete findings remain in the original outputs.']}
    (destination/MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (destination/README).write_text('''# หลักฐาน Evaluation รอบนี้

REPORT.md คือสรุปผลจริง JSON เก็บผลรายคำถาม/คำตอบ/แหล่งอ้างอิงและสถานะ tests ส่วน logs เก็บ stdout/stderr และ audit/ เก็บ findings หากรอบนี้รัน Audit

ไฟล์เดิมถูกคัดลอกหลังรันจบโดยไม่แก้คำตอบ คะแนน หรือ path ของเครื่องที่รัน EVIDENCE_MANIFEST.json บันทึกขนาดและ SHA256 ของทุกไฟล์ รวมทั้ง scope/job exit codes ไม่มี DB/PDF/model weights ใน ZIP นี้

ส่ง evaluation-evidence.zip พร้อม SHA256SUMS.txt ให้อาจารย์ได้ หรือส่งทั้งโฟลเดอร์ หากต้องการตรวจ ZIP หลังแตก ให้คัดลอก ZIP ต้นฉบับและ SHA256SUMS.txt เข้าโฟลเดอร์ที่แตกด้วย แล้วรันจาก ocr_final:

```powershell
.\\venv\\Scripts\\python.exe scripts/archive_evaluation.py verify --evidence <เส้นทางโฟลเดอร์หลักฐาน>
```

SHA256 ยืนยันว่าไฟล์ยังตรงกับชุดที่บันทึก ไม่ได้พิสูจน์ว่า facts ทั้งเล่มถูกต้อง การยืนยันซ้ำต้องรันโค้ดกับข้อมูลที่ประกาศ scope เอง Failed/incomplete findings และการไม่ตรวจ UI จริงยังคงแสดงตามผลเดิม
''', encoding='utf-8')
    names = [record['path'] for record in records]+[MANIFEST, README]
    with zipfile.ZipFile(destination/ZIP, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in names:
            bundle.write(inside(destination, name), name)
    (destination/SUMS).write_text(f'{sha(destination/ZIP)}  {ZIP}\n{sha(destination/MANIFEST)}  {MANIFEST}\n', encoding='utf-8')
    return verify(destination)


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    pack = commands.add_parser('archive')
    pack.add_argument('--source', type=Path, required=True)
    pack.add_argument('--destination', type=Path, required=True)
    pack.add_argument('--label', default='observed evaluation; not full-book accuracy')
    check = commands.add_parser('verify')
    check.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    result = archive(args.source, args.destination, args.label) if args.command == 'archive' else verify(args.evidence)
    print(json.dumps({key: value for key, value in result.items() if key != 'observed_jobs'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
