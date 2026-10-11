"""Capture real local OCR HTTP errors without altering model settings or books."""
import argparse
import importlib.util
import json
from pathlib import Path
import requests
import time
import hashlib

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pdf', type=Path, required=True)
    p.add_argument('--page', type=int, required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--dpi', type=int, default=150)
    p.add_argument('--num-predict', type=int, default=2048)
    p.add_argument('--temperature', type=float, default=.1)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Preserve prior experiments; choose a new output file')
    spec = importlib.util.spec_from_file_location('ocr_error_lab7', ROOT/'scr/ocr_system/lab7b_curriculum.py')
    lab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab)
    lab.DPI = a.dpi
    original = requests.post
    record = {'pdf': a.pdf.name, 'pdf_page': a.page, 'model': a.model, 'attempts': []}
    record['source_sha256'] = hashlib.sha256(a.pdf.read_bytes()).hexdigest()
    record['configuration'] = {'dpi': a.dpi, 'num_ctx': lab.OCR_NUM_CTX,
        'num_predict': a.num_predict, 'temperature': a.temperature,
        'prompt_sha256': hashlib.sha256(lab.TYPHOON_PROMPT.encode()).hexdigest(),
        'segmentation': False, 'retries': 0}
    record['configuration_sha256'] = hashlib.sha256(json.dumps(record['configuration'], sort_keys=True).encode()).hexdigest()

    def capture(*args, **kwargs):
        response = original(*args, **kwargs)
        record['attempts'].append({'status': response.status_code,
            'error_body': response.text[:4000] if response.status_code != 200 else None})
        return response

    requests.post = capture
    started = time.perf_counter()
    try:
        image = lab.load_pages(str(a.pdf), str(a.page))[0]
        record['image_sha256'] = hashlib.sha256(image).hexdigest()
        markdown = lab.ollama_chat(a.model, [{'role': 'user', 'content': lab.TYPHOON_PROMPT}],
            images=[image], num_ctx=lab.OCR_NUM_CTX, num_predict=a.num_predict,
            temperature=a.temperature, retries=0)
        record['markdown'] = markdown
    except Exception as exc:
        record['error'] = str(exc)
    finally:
        requests.post = original
        record['elapsed_ms'] = round((time.perf_counter()-started)*1000, 2)
        a.output.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if k != 'markdown'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
