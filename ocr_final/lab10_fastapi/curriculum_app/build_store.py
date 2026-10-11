"""Offline, atomic selection of immutable database sets; no runtime fact overlays."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path


def selected_build(root: Path):
    pointer = root / 'work/active-build.json'
    if not pointer.exists():
        return root, 'unversioned-bundled', None
    record = json.loads(pointer.read_text(encoding='utf-8'))
    relative = record['directory']
    target = (root / relative).resolve()
    builds = (root / 'work/builds').resolve()
    if not target.is_relative_to(builds) or target == builds or not target.is_dir():
        raise ValueError('active-build ผิดหรือไฟล์หาย: ใช้ database_build.py rollback --backup <backup>')
    manifest = json.loads((target/'build.json').read_text(encoding='utf-8'))
    if manifest['build_id'] != record['build_id']:
        raise ValueError('active-build identity mismatch')
    return target, record['build_id'], manifest


@contextmanager
def consumer_lock(root: Path):
    """OS releases this lock even when a backend crashes. Same lock guards activation."""
    lock = root / 'work/web/build-consumer.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a+b') as stream:
        if lock.stat().st_size == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('แอปยังใช้ฐานข้อมูลอยู่: หยุด backend ของโฟลเดอร์นี้ด้วย stop_web.ps1 -Port <port> ก่อน activate/rollback; อย่าหยุด Ollama') from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def extraction_provenance(root, manifest):
    """Operational build history only; never used by SQL retrieval or answers."""
    if not manifest:
        return {'origin': 'unversioned-bundled', 'source_validation': 'not declared', 'profiles': []}
    from .build_scope import PLAN_CHECKS
    profiles = []
    receipt = root/'source-validation.json'
    reviewed = json.loads(receipt.read_text(encoding='utf-8')) if receipt.is_file() else {}
    for item in manifest.get('databases', []):
        name = item.get('extraction')
        path = (root/name).resolve() if name else None
        extraction = {}
        if path and path.is_relative_to(root.resolve()) and path.is_file():
            extraction = json.loads(path.read_text(encoding='utf-8'))
        validation = reviewed.get('profiles', {}).get(item.get('profile'), {})
        database = (root/item['path']).resolve() if item.get('path') else None
        digest = None
        if validation and database and database.is_relative_to(root.resolve()) and database.is_file():
            with database.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        pages = list(extraction.get('page_paths', [{'pdf_page': n,
            'method': extraction.get('extraction_method', 'not recorded'),
            'ocr_performed': extraction.get('ocr_performed'),
            'reviewed_ingestion': bool(extraction.get('reviewed_corrections'))}
            for n in extraction.get('pages', [])]))
        # Supporting selection pages are sealed build provenance, not answer facts.
        for artifact in extraction.get('artifacts', []):
            if not artifact.get('path', '').endswith('/selection-rule.json'):
                continue
            proof = (root/artifact['path']).resolve()
            if proof.is_relative_to(root.resolve()) and proof.is_file():
                content = proof.read_bytes()
                if hashlib.sha256(content).hexdigest() == artifact.get('sha256'):
                    rule = json.loads(content)
                    if rule['pdf_page'] not in {p['pdf_page'] for p in pages}:
                        pages.append({'pdf_page': rule['pdf_page'], 'role': 'supporting-selection-rule',
                            'method': extraction.get('extraction_method', 'not recorded'),
                            'ocr_performed': extraction.get('ocr_performed'),
                            'reviewed_ingestion': bool(extraction.get('reviewed_corrections'))})
        profiles.append({'profile': item.get('profile'),
            'method': extraction.get('extraction_method', 'not recorded'),
            'ocr_performed': extraction.get('ocr_performed'),
            'reviewed_corrections': extraction.get('reviewed_corrections', []),
            'reviewed_input_scope': manifest.get('reviewed_input_scope'),
            'source_validated': bool(validation and digest == item.get('sha256')
                                     and validation.get('database_sha256') == item.get('sha256')
                                     and validation.get('source_sha256') == extraction.get('source_sha256')
                                     and PLAN_CHECKS.issubset(set(validation.get('verified_fields', [])))
                                     and validation.get('unresolved_defects') == []),
            'pages': pages})
    return {'origin': manifest.get('origin', 'not recorded'),
            'reviewed_input_scope': manifest.get('reviewed_input_scope'), 'profiles': profiles}
