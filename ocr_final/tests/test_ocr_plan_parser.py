import unittest

from scripts.ocr_plan_parser import parse_page, table_rows


def regions(rows, total=6):
    return [{'text': 'ปีที่ 3 ภาคการศึกษาที่ 1', 'original_pixel_box': [0, 0, 600, 100]},
            *[{'text': '<table><tr>' + ''.join('<td>'+c+'</td>' for c in row) + '</tr></table>',
               'original_pixel_box': [0, (i+1)*100, 600, (i+2)*100]} for i, row in enumerate(rows)],
            {'text': f'<table><tr><td>รวม</td><td>{total}</td></tr></table>',
             'original_pixel_box': [0, 400, 600, 450]}]


class OCRPlanParserTests(unittest.TestCase):
    def test_split_html_total_is_one_total_only_inside_same_physical_band(self):
        source = regions([['06000001', 'ชื่อวิชา COURSE NAME', '3(3-0-6)']], total=3)
        source[-1]['text'] = '<table><tr><td></td><td>รวม</td></tr><tr><td>3</td></tr></table>'
        self.assertEqual(parse_page(source, 'source.pdf', 1, 1)['term_totals'][0]['credits'], 3)
        source[-1]['text'] += '<table><tr><td>6</td></tr></table>'
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            parse_page(source, 'source.pdf', 1, 1)

    def test_escaped_faculty_footnote_preserves_name(self):
        data = parse_page(regions([['06000001',
            'กลุ่มวิชาที่กำหนดโดยคณะ\\* ผู้ประกอบการสมัยใหม่ MODERN ENTREPRENEURS',
            '3(3-0-6)']], total=3), 'source.pdf', 1, 1)
        self.assertEqual(data['courses'][0]['name_th'], 'ผู้ประกอบการสมัยใหม่')

    def test_faculty_label_on_same_line_does_not_remove_thai_name(self):
        result = parse_page(regions([['06000001',
            'กลุ่มวิชาที่กำหนดโดยคณะ* กฎหมายสำหรับคนรุ่นใหม่ LAW FOR NEW GENERATION',
            '3(3-0-6)']], total=3), 'source.pdf', 1, 1)
        self.assertEqual(result['courses'][0]['category'], 'กลุ่มวิชาที่กำหนดโดยคณะ*')
        self.assertEqual(result['courses'][0]['name_th'], 'กฎหมายสำหรับคนรุ่นใหม่')
        self.assertEqual(result['courses'][0]['name_en'], 'LAW FOR NEW GENERATION')

    def test_individual_rows_preserve_names_hours_and_source_boxes(self):
        data = parse_page(regions([
            ['06026211', 'การเรียนรู้ของเครื่องเชิงประยุกต์ APPLIED MACHINE LEARNING', '3 (2-2-5)'],
            ['06026212', 'การสร้างคลังข้อมูล DATA WAREHOUSING', '3 (2-2-5)']]), 'DSBA.pdf', 27, 26)
        self.assertEqual([c['code'] for c in data['courses']], ['06026211', '06026212'])
        self.assertEqual(data['courses'][0]['name_en'], 'APPLIED MACHINE LEARNING')
        self.assertEqual(data['courses'][0]['name_th'], 'การเรียนรู้ของเครื่องเชิงประยุกต์')
        self.assertEqual(data['term_totals'][0]['credits'], 6)
        self.assertEqual(data['courses'][0]['source_claims'][0]['pixel_box'], [0, 100, 600, 200])

    def test_missing_last_row_does_not_pass_with_a_printed_total(self):
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            parse_page(regions([['06026211', 'ชื่อวิชา COURSE NAME', '3(2-2-5)']]), 'DSBA.pdf', 27, 26)

    def test_shared_placeholder_is_one_slot_with_all_name_pairs(self):
        data = parse_page(regions([['06026xxx',
            'วิชาเลือกกลุ่มวิทยาการข้อมูล 1<br/>ELECTIVE IN DATA SCIENCE<br/>'
            'วิชาเลือกกลุ่มการวิเคราะห์เชิงสถิติ 1<br/>ELECTIVE IN STATISTICAL ANALYSIS 1',
            '3(3-0-6)<br/>หรือ<br/>3(2-2-5)']], total=3), 'DSBA.pdf', 27, 26)
        self.assertEqual(len(data['courses']), 1)
        self.assertEqual(len(data['courses'][0]['source_name_groups']), 2)
        self.assertEqual(data['courses'][0]['credits'], '3(3-0-6) หรือ 3(2-2-5)')

    def test_wrong_column_association_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'leaked'):
            parse_page(regions([['06026xxx', 'ชื่อวิชา COURSE NAME 3(3-0-6)', '']], total=3), 'DSBA.pdf', 27, 26)

    def test_unresolved_bundle_cannot_be_silently_flattened(self):
        with self.assertRaisesRegex(ValueError, 'association'):
            parse_page(regions([['06000001 06000002', 'ชุดวิชา GROUP NAME', '3(3-0-6)']], total=3), 'source.pdf', 1, 1)

    def test_explicit_source_alternatives_are_one_credit_slot(self):
        result = parse_page(regions([['06036181<br/>หรือ<br/>06036182',
            'สหกิจศึกษา 1<br/>COOPERATIVE EDUCATION 1<br/>หรือ<br/>สหกิจศึกษา 2<br/>COOPERATIVE EDUCATION 2',
            '6(0-35-0)<br/>หรือ<br/>6(0-35-0)']], total=6), 'source.pdf', 1, 1)
        row = result['courses'][0]
        self.assertEqual(list(row['course_options']), ['06036181', '06036182'])
        self.assertEqual(row['credits'], '6(0-35-0)')
        self.assertEqual(result['term_totals'][0]['credits'], 6)

    def test_markdown_cells_preserve_line_breaks_without_separator_rows(self):
        self.assertEqual(table_rows('|code|name|hours|\n|---|---|---|\n|06026xxx|ชื่อ<br>NAME|3(3-0-6)|'),
            [['code', 'name', 'hours'], ['06026xxx', 'ชื่อ\nNAME', '3(3-0-6)']])
