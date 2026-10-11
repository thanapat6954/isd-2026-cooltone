import unittest
from scripts.verify_reconstruction_labels import check_options


class ReviewedOptionTests(unittest.TestCase):
    def test_repeated_elective_slot_loss_is_detected(self):
        expected=[{'code':'xxxxxxxx','credits_raw':'3(x-x-x)'}]*2
        actual=[{'code':'ELEC-X-1','raw_code':'xxxxxxxx','credits_raw':'3(x-x-x)'}]
        self.assertTrue(any(r['kind']=='missing reviewed row multiplicity' for r in check_options(expected,actual)))

    def test_shared_track_course_is_not_double_counted(self):
        expected=[{'code':'06016418','credits_raw':'3(2-2-5)','alternative_group':'position-3'}]*2
        actual=[{'code':'06016418','raw_code':None,'credits_raw':'3(2-2-5)'}]
        self.assertEqual(check_options(expected,actual),[])

    def test_name_misalignment_is_not_a_credit_pass(self):
        expected=[{'code':'06016422','credits_raw':'3(2-2-5)','name_th':'อินเทอร์เน็ตของสรรพสิ่ง'}]
        actual=[{'code':'06016422','raw_code':None,'credits_raw':'3(2-2-5)','name_th':'ชื่ออีกวิชา'}]
        self.assertTrue(any(r.get('field')=='name_th' for r in check_options(expected,actual)))
