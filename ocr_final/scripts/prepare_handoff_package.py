"""Package current uncommitted code and separately supplied artifacts, without publication."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-root',type=Path,required=True)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--lineage',type=Path,help='Disclosed source/build origins; delivery metadata, never runtime facts')
    parser.add_argument('--data-archive',type=Path,help='Copy an unchanged prior runtime archive after matching its source manifest; preserve old delivery')
    args=parser.parse_args()
    root=args.project_root.resolve()
    args.output.mkdir(parents=True,exist_ok=False)
    ignored={'venv','.venv','work','reports','input','tmp','__pycache__','node_modules','.git'}
    files=[root/'README.md',root/'AGENTS.md']
    for path in (root/'ocr_final').rglob('*'):
        relative=path.relative_to(root/'ocr_final')
        if path.is_file() and not any(p in ignored for p in relative.parts) and path.name!='.env' and path.suffix not in {'.db','.pyc','.log'}:
            files.append(path)
    for path in (root/'docs').rglob('*'):
        relative=path.relative_to(root/'docs')
        if path.is_file() and not any(p in {'results','history'} for p in relative.parts) and path.suffix!='.log':
            files.append(path)
    # Preserve raw evidence explicitly linked by the guide, not unrelated output trees.
    for target in re.findall(r'\]\((docs/results/[^)#]+)(?:#[^)]*)?\)',(root/'README.md').read_text(encoding='utf-8')):
        path=root/target
        if path.is_file():
            files.append(path)
    evidence=root/'docs/results/fresh_handoff_20261011'
    if evidence.exists():
        files.extend(path for path in evidence.rglob('*') if path.is_file())
    evidence=root/'docs/results/two_mode_handoff_20261011'
    if evidence.exists():
        files.extend(path for path in evidence.rglob('*') if path.is_file() and path.suffix not in {'.db','.pyc'})
    evidence=root/'docs/results/fresh_ai_scope_20261011'
    if evidence.exists():
        files.extend(path for path in evidence.rglob('*') if path.is_file() and path.suffix not in {'.db','.sqlite','.pyc'})
    evidence=root/'docs/results/font_table_rebuild_20261011'
    if evidence.exists():
        files.extend(path for path in evidence.rglob('*') if path.is_file() and path.suffix not in {'.db','.sqlite','.pyc'})
    files=sorted(set(files))
    inventory=[{'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)} for path in files]
    code=args.output/'curriculum-project.zip'
    with zipfile.ZipFile(code,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
        for path in files:
            archive.write(path,path.relative_to(root).as_posix())
    data=args.output/'runtime-data.zip'
    if args.data_archive:
        with zipfile.ZipFile(args.data_archive) as archive:
            if hashlib.sha256(archive.read('runtime-data/manifest.json')).hexdigest()!=digest(args.bundle/'manifest.json'):
                raise ValueError('Prior runtime archive manifest differs; cannot reuse')
            if args.lineage and hashlib.sha256(archive.read('runtime-data/build-lineage.json')).hexdigest()!=digest(args.lineage):
                raise ValueError('Prior archive lineage differs; cannot reuse')
        shutil.copyfile(args.data_archive,data)
    else:
        with zipfile.ZipFile(data,'x',compression=zipfile.ZIP_STORED) as archive:
            for path in args.bundle.rglob('*'):
                if path.is_file():
                    archive.write(path,'runtime-data/'+path.relative_to(args.bundle).as_posix())
            if args.lineage:
                archive.write(args.lineage,'runtime-data/build-lineage.json')
    result={'scope':'local handoff only; no venv, model cache, .env or working DB in code archive',
        'archives':[{'file':path.name,'bytes':path.stat().st_size,'sha256':digest(path)} for path in (code,data)],
        'code_files':inventory,'artifact_manifest_sha256':digest(args.bundle/'manifest.json')}
    (args.output/'handoff-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'archives':result['archives'],'code_file_count':len(files)}))


if __name__=='__main__':
    main()
