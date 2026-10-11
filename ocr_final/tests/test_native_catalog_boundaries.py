"""Synthetic catalog headers exercise real cross-page association failure modes."""
import unittest
from scripts.source_catalog import catalog_headers, SECTION


def row(text,x,y,page):
    return {'text':text,'bbox':[x,y,x+80,y+15],'pdf_page':page}


class CatalogBoundaries(unittest.TestCase):
    def test_bilingual_name_and_marker_can_continue_on_next_page(self):
        rows=[row('12345678',75,735,1),row('ชื่อวิชา',150,735,1),row('6(0-45-0)',450,735,1),
              row('A LONG COURSE NAME',150,73,2),row('วิชาบังคับก่อน : ไม่มี',150,95,2),
              row('PREREQUISITE : None',150,116,2)]
        header=catalog_headers(rows)[0]
        self.assertEqual(header['status'],'candidate')
        self.assertEqual(header['name_en'],'A LONG COURSE NAME')
        self.assertEqual(header['marker'],4)

    def test_next_course_marker_cannot_certify_previous_list_row(self):
        rows=[row('12345678',75,100,1),row('ชื่อแรก',150,100,1),row('3(3-0-6)',450,100,1),
              row('87654321',75,140,1),row('ชื่อใหม่',150,140,1),row('3(3-0-6)',450,140,1),
              row('NEW NAME',150,160,1),row('วิชาบังคับก่อน : ไม่มี',150,180,1)]
        self.assertEqual(catalog_headers(rows)[0]['status'],'no_prerequisite_marker')

    def test_appendix_and_group_headings_end_previous_description(self):
        self.assertTrue(SECTION.search('ภาคผนวก ฉ'))
        self.assertTrue(SECTION.search('กลุ่มวิชาโครงงานและสัมมนา'))
        self.assertFalse(SECTION.search('โครงงานนี้ใช้ความรู้จากหลายวิชา'))
