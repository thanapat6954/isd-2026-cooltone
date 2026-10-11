import unittest
from lab10_fastapi.curriculum_app.query_planner import detect_intent, _conditions


class DiverseRoutingTests(unittest.TestCase):
    def test_explicit_program_name_still_routes_to_program_information(self):
        self.assertEqual(detect_intent('หลักสูตร AI ชื่อว่าอะไร').intent, 'program_info')

    def test_written_thai_numbers_and_multiple_terms(self):
        plan=detect_intent('ปีสอง เทอมหนึ่งกับเทอมสอง หน่วยกิตเท่ากันไหม')
        self.assertEqual(plan.intent,'semester_credits')
        self.assertEqual(plan.year,2)
        self.assertEqual(plan.semesters,(1,2))
        self.assertIn('semester IN (1, 2)',_conditions(plan))

    def test_minimum_credits_requests_courses_not_year_total(self):
        plan=detect_intent('ขอวิชาบังคับที่อยู่ปี 2 หน่วยกิตอย่างน้อย 3 และแสดงชื่ออังกฤษ')
        self.assertEqual(plan.intent,'course_list')
        self.assertIn('credits >= 3',_conditions(plan,include_required=True))

    def test_context_is_not_a_request_for_program_information(self):
        for question in ('อยากเรียนเขียนโปรแกรม มีวิชาชื่อใกล้เคียงกันอะไรบ้าง',
                         'ขอตัวอย่างหัวข้อสอบ โดยอ้างเฉพาะข้อมูลหลักสูตรที่บันทึก',
                         'ชื่อภาษาอังกฤษของวิชารหัสตรงกันระหว่างฉบับเก่ากับใหม่เปลี่ยนไหม'):
            self.assertNotEqual(detect_intent('หลักสูตร IT 2565 สหกิจ: '+question).intent,'program_info')
