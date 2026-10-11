"""Declared partial-build policy. This contains capabilities, never curriculum facts."""
PLAN_CAPABILITIES = ['academic_plan', 'plan_course_facts']
PLAN_CHECKS = {'identity', 'all_required_rows', 'course_codes', 'names', 'placeholders',
               'alternative_associations', 'hours', 'plan_boundaries', 'prerequisite_unknowns',
               'provenance', 'no_invented_text'}
FULL_CHECKS = PLAN_CHECKS | {'catalog_descriptions', 'program_rules'}


def contract(manifest):
    value = (manifest or {}).get('contract')
    if value is None:
        return {'kind': 'full-runtime', 'partial': False, 'expected_catalogs': 14}
    if (value.get('kind') != 'academic-plan-only' or value.get('partial') is not True
            or value.get('capabilities') != PLAN_CAPABILITIES or not value.get('profiles')
            or len(set(value['profiles'])) != len(value['profiles'])):
        raise ValueError('Invalid declared partial build contract; full validation cannot be bypassed')
    return {**value, 'expected_catalogs': len(value['profiles'])}


def partial_answer_notice():
    return 'ขอบเขตชุดข้อมูล: เฉพาะแผนการศึกษาของ profile ที่ประกาศ; รายวิชาในแผนไม่ใช่ catalog ครบทั้งเล่ม ยังไม่รองรับคำอธิบายรายวิชา ข้อกำหนดหลักสูตร วิชาบังคับก่อน หรือ legacy'


def supports_plan_question(plan, question):
    import re
    if re.search(r'คำอธิบาย|เนื้อหา|บังคับก่อน|prerequis|description|ลงทะเบียน|สำเร็จ|เกณฑ์.*จบ|graduate|graduation', question, re.I):
        return False
    return plan.intent in {'course_list', 'semester_credits', 'year_credits', 'course_count',
                           'elective_slots', 'course_detail', 'course_search', 'selection_clarification'}
