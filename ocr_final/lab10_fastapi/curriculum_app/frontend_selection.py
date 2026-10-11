"""Reject conflicting explicit years unless the question asks for comparisons."""
import re
from .query_planner import detect_intent


def validate_selected_year(question, selected_year, version):
    if version=='all versions' or selected_year is None or detect_intent(question).intent in {'version_course_diff','version_fact_comparison'}:
        return
    explicit={int(year) for year in re.findall(r'(?<!\d)(?:25|20)\d{2}(?!\d)',question)}
    if explicit and explicit!={selected_year}:
        raise ValueError(f'ปีหลักสูตรในคำถาม ({", ".join(map(str,sorted(explicit)))}) ไม่ตรงกับฉบับที่เลือก (พ.ศ. {selected_year}) กรุณาเลือกฉบับให้ตรง หรือเลือกทุกฉบับเมื่อต้องการเปรียบเทียบ')
