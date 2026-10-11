"""Bounded verbatim development excerpts; HTTP success is never a quality score."""
import argparse
from collections import Counter
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--excerpts', action='store_true')
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8'))
    cases = data['cases']
    summary = {'wordings_n':len({c['question'].split(': ',1)[-1] for c in cases}),
               'scoped_questions_n':len({(c['profile'],c['question']) for c in cases}),
               'categories_n':len({c['category'] for c in cases}), 'http_requests_n':len(cases),
               'http_statuses':dict(Counter(str(c['status']) for c in cases)),
               'profiles':dict(Counter(c['profile'] for c in cases)),
               'categories':dict(Counter(c['category'] for c in cases)),
               'note':'transport counts only; substantive/manual quality judgments separate'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
    if args.excerpts:
        for case in cases:
            if case['route'] != '/api/ask':
                continue
            body = case['body']
            answer = str(body.get('answer',body.get('detail',body.get('error',''))))
            print(json.dumps({'id':case['id'],'category':case['category'],'http':case['status'],
                              'intent':(case.get('trace') or {}).get('intent'), 'answer':answer[:240]},ensure_ascii=False))


if __name__ == '__main__':
    main()
