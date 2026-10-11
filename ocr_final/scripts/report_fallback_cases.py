"""Render verbatim development evidence; no evaluation labels enter production."""
import argparse
import json
from pathlib import Path
import statistics


def body(case):
    value = case['body']
    return json.loads(value) if isinstance(value, str) else value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    docs = args.repo / 'docs'
    base = docs / 'results/fallback_relevance_20261009'
    old = json.loads((docs / 'results/it_metadata_timeout_20261009/fallback-45s/result.json').read_text(encoding='utf-8'))
    before = {(case['route'], case['question']): case for case in old['requests'] if 'question' in case}
    lines = ['# ผลก่อนและหลังแก้ unknown fallback', '',
        '## ขอบเขตและข้อจำกัด', '',
        'ใช้ real qwen3:4b ผ่าน HTTP จริงกับ SQLite สำเนา IT-2565-coop; ไม่อ่าน held-out และไม่แก้ working DB. ตัวอย่างทั้งหมดเป็น development regression ไม่ใช่ independent accuracy. ข้อมูล course 305 แถวไม่มี description_th ที่ไม่ว่าง จึงคาดหวังการแจ้งข้อจำกัด ไม่ใช่คำตอบเนื้อหาที่แต่งเพิ่ม.', '',
        'แก้ generic topic extraction: รับเฉพาะ literal spans จากคำถาม สร้าง SELECT โดยโปรแกรมและใช้ SQL validator เดิม. ตัด program-summary bias; ไม่ถือคำอธิบายคล้ายกันเป็นความสัมพันธ์ที่หนังสือระบุ. Null descriptions ไม่เข้า evidence selection และบอกแถวที่ยังขาดข้อมูล.', '',
        'เพิ่ม retrieval ของ prerequisite ที่ปลายทั้งสองอยู่ใน course candidates ของคำถามเดียวกัน; เป็น explicit stored edge ไม่ใช่ inference จาก description. ยังไม่ครอบคลุม relationship ชนิดอื่นหรือรับรอง completeness. Printed folios ที่ DB ไม่ได้บันทึกยังไม่ยืนยันในคำตอบ ห้ามเดา offset. รอบนี้ตรวจ fallback ของ IT-2565-coop และ IT-2560-coop รวมคำถาม ambiguous; หลักสูตรและแผนอื่นยังไม่ทดสอบ fallback ใหม่.', '',
        '## ตัวอย่างจริงก่อนและหลัง', '']
    times = []
    for batch in ['release-cases', 'stored-relationship-final', 'citation-pairs', 'ambiguous', 'mutation-final-A', 'mutation-final-B', 'removal-final', 'retrieval-failure']:
        path = base / batch / 'result.json'
        if not path.exists():
            continue
        result = json.loads(path.read_text(encoding='utf-8'))
        lines += [f'### ชุด `{batch}`', '', f'[ผลดิบ](results/fallback_relevance_20261009/{batch}/result.json)', '']
        for case in result['requests']:
            if 'question' not in case:
                continue
            answer = body(case)
            trace = case.get('trace') or (answer if case['route'] == '/api/ask' else {})
            previous = before.get((case['route'], case['question']))
            lines += [f'#### `{case["route"]}` — IT / พ.ศ. 2565 / สหกิจศึกษา', '',
                      'คำถามจริง:', '', case['question'], '', 'คำตอบก่อนแก้:', '']
            lines += [body(previous).get('answer', body(previous).get('detail', 'not recorded')) if previous else 'not recorded', '']
            if previous:
                lines += [f'ก่อนแก้ HTTP {previous["status"]}; {previous["elapsed_ms"]:.2f} ms. อ้างอิง [ผลเดิม](results/it_metadata_timeout_20261009/fallback-45s/result.json).', '']
                old_body = body(previous)
                lines += ['SQL และแถวก่อนแก้:', '', '```json', json.dumps({key: old_body.get(key) for key in ('sql', 'rows', 'detail')}, ensure_ascii=False, indent=2), '```', '']
            lines += ['คำตอบหลังแก้ (ไม่ปรับถ้อยคำ):', '', answer.get('answer', answer.get('detail', 'not recorded')), '',
                      f'HTTP {case["status"]}; end-to-end {case["elapsed_ms"]:.2f} ms.', '', 'SQL จริง:', '', '```sql', str(trace.get('sql', 'not recorded')), '```', '',
                      'แถวหลักฐานจริง (ไม่รวม metadata ของ process):', '', '```json',
                      json.dumps([{k:v for k,v in row.items() if k != '_source'} for row in trace.get('rows', [])], ensure_ascii=False, indent=2), '```', '']
            lines += ['รายละเอียด query ที่ execute จริง:', '', '```json', json.dumps([{key: query.get(key) for key in ('sql', 'row_count', 'error', 'repair_attempts', 'citation_queries')} for query in trace.get('queries', [])], ensure_ascii=False, indent=2), '```', '']
            citations = [(row.get('source_file'), row.get('page_number'), row.get('printed_page_number')) for row in trace.get('rows', [])]
            lines += ['PDF / หน้าในเล่มจากผลดิบ: ' + (str(citations) if citations else 'n/a; ไม่มีหลักฐานรายวิชาที่ดึงมา'), '',
                      'หน้าในเล่มที่ไม่ปรากฏในผลดิบ: ยังไม่ยืนยันในคำตอบนี้ แม้มี source-review records เดิม; ไม่ถือว่าการย้ายข้อมูลเป็น source verification ใหม่.', '']
            if batch.startswith('mutation'):
                lines += ['การประเมิน: เป็น synthetic provenance probe ใน DB สำเนา ไม่ใช่ curriculum fact. ตรวจว่า marker A/B เปลี่ยนตาม DB จริงและระบุ description ที่ขาด; ไม่อ้าง completeness หรือ book-supported accuracy ของ marker.', '']
            elif batch in {'stored-relationship-final', 'citation-pairs'} and 'รหัสวิชา: 06016407' in answer.get('answer', ''):
                lines += ['การประเมิน: ตอบ explicit edge ที่มีใน SQLite (06016407 → 06016406, kind=pre) ไม่แทนด้วย description หรือ program summary. เป็น substantive DB-backed answer ของความสัมพันธ์ชนิดนี้เท่านั้น ไม่ใช่การยืนยันเงื่อนไขอื่น; PDF326 ระบุจาก stored edge แต่ printed folio NULL จึง citation ยังไม่ครบ. ไม่ได้ตรวจ book page ใหม่ในชุดนี้.', '']
            elif case['status'] != 200:
                lines += ['การประเมิน: request ล้มเหลว ไม่ใช่คำตอบสำเร็จ; ไม่มี unsupported factual answer แต่ recovery/error handling ยังต้องตรวจเพิ่ม.', '']
            else:
                lines += ['การประเมิน: แจ้ง specific insufficient evidence แทน program totals; ไม่ใช่ substantive answer. ยังไม่ครบเนื้อหาที่ผู้ใช้ขอ และไม่ใช้ HTTP200 เป็น correctness proof. Citation อ้างข้อมูลที่ค้น ไม่ได้ยืนยันความสัมพันธ์ที่ไม่มีใน DB.', '']
            if batch == 'release-cases':
                times.append(case['elapsed_ms'])
    if times:
        lines += ['## เวลาและจำนวนตัวอย่าง', '',
                  f'release-cases: n={len(times)}; substantive successes=0, abstentions={len(times)}, HTTP failures=0, timeouts=0; median {statistics.median(times):.2f} ms. stored-relationship-final มี substantive DB-backed answer2requestsแต่ printed folioยังขาด. ไม่รายงาน reliable p95 หรือ general accuracy. ไม่มี forced cold-load และไม่ได้ยืนยัน warm residency ทุก request; cold/warm แยกอย่างน่าเชื่อถือยัง n/a.', '']
    old_path = base / 'live-old-paired.json'
    if old_path.exists() and old_path.stat().st_size:
        lines += ['## การแยกฉบับเก่าใน LIVE', '', '[ผลดิบ](results/fallback_relevance_20261009/live-old-paired.json)', '']
        for case in json.loads(old_path.read_text(encoding='utf-8-sig')):
            lines += [f'### `{case["route"]}` — IT / พ.ศ. 2560 / สหกิจศึกษา', '', case['question'], '',
                      'ก่อนแก้: not recorded', '', 'คำตอบจริง:', '', case['body'].get('answer', str(case['body'])), '',
                      f'HTTP {case["status"]}; {case["elapsed_ms"]:.2f} ms.', '', 'SQL/rows/sources จริงจาก response (key ที่ไม่มีคือ not recorded):', '', '```json',
                      json.dumps({key:case['body'].get(key, 'not recorded') for key in ('sql', 'rows', 'sources', 'selected_curricula')}, ensure_ascii=False, indent=2), '```', '',
                      'เป็น scoped abstention; APIเลือก IT-2560-coop และ frontend sources เป็น IT-60.pdf/2560 เท่านั้น. คู่ PDF/printed page อยู่ในผลดิบด้านบน มาจาก selected SQLite ไม่เดา offset. ไม่ได้ตรวจ completeness/source correctness ทุกแถวใหม่จาก book.', '']
    paired = base / 'live-old-paired.json'
    if paired.exists():
        lines += ['## หลังแก้การดึง paired citation metadata', '', '[ผลดิบ LIVE ทั้งสองroutes](results/fallback_relevance_20261009/live-old-paired.json)', '',
                  'ดึงคู่หน้าจาก selected SQLite เท่านั้น มี raw citation_queries ไม่ใช้ global-profile lookup หรือ offset. source-viewer ที่เปิดจาก actual citationclick แสดง IT-60.pdf PDF34/book29 และเห็นรายวิชา06016319บนภาพ. [ภาพ](results/fallback_relevance_20261009/live-citation.png) / [DOM](results/fallback_relevance_20261009/live-citation.txt).', '',
                  'citation-pairs: DB-backed pairs IT2565 PDF38/book33,41/36,42/37 และ Project1 PDF43/book38,Project2 PDF44/book39. Edge PDF326 ไม่มี paired folioใน selectedDB จึงยัง n/a; ไม่อ้างว่า book-verified ใหม่จากการ lookup. Ambiguous content case แสดง candidate โครงงาน1/2และขอเลือก พร้อมบอกว่า descriptionsยังขาด.', '']
    source_check = base / 'source-check.json'
    if source_check.exists():
        review = json.loads(source_check.read_text(encoding='utf-8'))
        lines += ['## ตรวจ supporting source แยกจากข้อมูลที่ใช้ตอบ', '',
                  f'ตรวจ rendered {review["source_file"]} PDF{review["pdf_page"]} / หน้าในเล่ม{review["printed_page"]} โดยอ่าน folioจากภาพ ไม่คำนวณoffset. เห็นข้อความวิชาบังคับก่อนของโครงงาน2เป็นโครงงาน1 ยืนยัน substantive edge ที่อยู่ในSQLiteด้วย source image. [ภาพจริง](results/fallback_relevance_20261009/IT-326-viewer.png) / [บันทึก](results/fallback_relevance_20261009/source-check.json).', '',
                  'การตรวจภาพนี้ไม่เติม facts หรือ folioเข้าAPI ไม่เพิ่ม schema ไม่แก้ DB. หน้าในเล่มของ edge ยัง NULL ใน selectedSQLite จึง UIยังบอกว่ายังไม่ยืนยัน แม้รายงานนี้ตรวจfoliovisuallyแล้ว. Reviewนี้เป็น development evidence ไม่ใช่ production approval/held-out label.', '']
    lines += ['## หลักฐาน UI และผลที่ยังเปิด', '',
              '[UI clarification ล่าสุด](results/fallback_relevance_20261009/live-ambiguous-ui.png) / [DOM](results/fallback_relevance_20261009/live-ambiguous-ui.txt): actual LIVE คำถามโครงงานที่กำกวม แสดง06016406/06016407 ขอระบุรายวิชา และบอกว่า descriptionsยังขาด; PDF43/book38 และ44/book39. รอบนี้ server6054ms/end-to-end6064ms เป็น scoped abstention ไม่ผ่าน5s แม้ HTTP200. จึงไม่อ้าง reliable latency SLA จากชุดเร็วกว่าเดิม.', '',
              '[UI คู่หน้าเก่า](results/fallback_relevance_20261009/live-old-paired-ui.png) / [DOM](results/fallback_relevance_20261009/live-old-paired-ui.txt): PDF34/book29,35/30,38/33 จาก selected IT-2560-coop SQLite; viewerเปิดจริงและเห็นภาพ. ไม่มี2565sourcesในตัวอย่างนี้.', '',
              '[ภาพ UI isolated](results/fallback_relevance_20261009/ui-current.png) และ [DOM](results/fallback_relevance_20261009/ui-current.txt): IT/latest, loading→insufficient-evidence, citation3แหล่ง; server3890ms/end-to-end3914ms ตาม UI. ต่อมา restart verified LIVE backendด้วย stop_web/start_web; ไม่หยุด Ollama ไม่แก้ DB. หลักฐาน LIVE ใหม่แยกเป็น live-relationship-ui.png/txt และ live-gap-ui.png/txt ในโฟลเดอร์ผลเดียวกัน. Printed folios ที่ NULL คงแจ้งว่ายังไม่ยืนยัน. Citation navigation รอบนี้ต้องอ้าง screenshot/DOM ต้นฉบับที่บันทึกจริงเท่านั้น.', '',
              'คง failed attempts initial/narrow-schema/literal-topics และ mutation-A/B/A2/B2 ไว้ ไม่ลบผลที่ไม่ผ่าน. Mutation A2/B2 เคย abstain แม้มี marker เพราะ model เลือก null row; ไม่ถือเป็น provenance pass.', '',
              'ยังเปิด: relationship ชนิดอื่น/completeness, citation printed foliosบางหน้า, unknown fallback ของทุกprofileนอกITcoopที่ตรวจรอบนี้, untouched held-out, fresh relevant-page reconstruction, difficult cold/warm latency, process-kill recovery, legacy identity และ clean install. Shared regression results รุ่นล่าสุด [final-locked/checks.json](results/fallback_relevance_20261009/final-locked/checks.json) ไม่ใช่ held-out accuracy. Unit/schema/frontend/gold/old2560/provenance/version_sets เป็นคนละscope ห้ามบวกเป็น accuracy เดียว.', '']
    (docs / 'FALLBACK_BEFORE_AFTER.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Generated docs/FALLBACK_BEFORE_AFTER.md from verbatim raw evidence')


if __name__ == '__main__':
    main()
