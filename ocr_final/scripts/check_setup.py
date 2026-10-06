"""Read-only preflight: report missing artifacts rather than inventing data."""
import argparse
import importlib.util
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = {'python': sys.version.split()[0], 'platform': sys.platform,
              'missing_runtime_packages': [name for name in ('fastapi', 'uvicorn', 'dotenv', 'requests', 'pydantic')
                                           if importlib.util.find_spec(name) is None]}
    if not result['missing_runtime_packages']:
        from lab10_fastapi.curriculum_app.config import settings
        from lab10_fastapi.curriculum_app.database import DatabaseRegistry
        from lab10_fastapi.curriculum_app.model_service import QwenTextToSQL
        from run_lab8b import PROFILES
        registry = DatabaseRegistry(settings.database_root)
        reviews = ROOT/'data/source_reviews/graduation_references.json'
        expected = json.loads(reviews.read_text(encoding='utf-8'))['reviews'] if reviews.is_file() else []
        changed_sources = []
        for item in expected:
            path = ROOT/'data/input'/item['source_file']
            if path.is_file():
                with path.open('rb') as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != item['sha256']:
                        changed_sources.append(item['source_file'])
        result.update({'queryable_profiles': [d.curriculum_name for d in registry.active_catalogs],
                       'changed_source_pdfs': changed_sources,
                       'model': settings.ollama_model, 'model_installed_and_service_ready': QwenTextToSQL(settings, None).available(),
                       'missing_profile_databases': [key for key, profile in PROFILES.items()
                           if not (settings.database_root / profile['out'].relative_to(ROOT) / 'curriculum.db').is_file()],
                       'missing_source_pdfs': sorted({p['input'].name for p in PROFILES.values() if not p['input'].is_file()}),
                       'invalid_databases': [d.relative_path for d in registry.databases if d.inspection_error]})
    result['ready'] = not result['missing_runtime_packages'] and bool(result.get('queryable_profiles')) and result.get('model_installed_and_service_ready', False) and not result.get('missing_profile_databases') and not result.get('missing_source_pdfs') and not result.get('changed_source_pdfs') and not result.get('invalid_databases')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
