"""Compare saved real-browser observations with the unchanged frontend API."""
import argparse
import json
import re
from pathlib import Path
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--observations',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    args = parser.parse_args()
    result = {'cases':[],'scope':'Four observed current-family UI cases, not every version or all challenge levels'}
    for case in json.loads(args.observations.read_text(encoding='utf-8'))['cases']:
        response = requests.post(args.url+'/ask',json={key:case[key] for key in ('curriculum','version','question')},timeout=30)
        body = response.json()
        normalized = re.sub(r'\s+',' ',case['text'])
        answer_matches = re.sub(r'\s+',' ',body.get('answer','')) in normalized if response.status_code == 200 else False
        source_matches = all(f"PDF หน้า {source['page']}" in normalized and source['section'] in normalized for source in body.get('sources',[]))
        result['cases'].append({'curriculum':case['curriculum'],'question':case['question'],'status':response.status_code,
            'response':body,'answer_matches_ui':answer_matches,'source_matches_ui':source_matches,
            'passed':answer_matches and source_matches and bool(body.get('sources'))})
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"API/UI agree: {sum(case['passed'] for case in result['cases'])}/{len(result['cases'])}")
    return int(any(not case['passed'] for case in result['cases']))


if __name__ == '__main__':
    raise SystemExit(main())
