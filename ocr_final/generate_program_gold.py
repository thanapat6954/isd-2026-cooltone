"""Generate the reviewed 30-question answer keys for AI and both IT plans."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent

PROFILES = {
    "ai": {
        "folder": "lab8b_ai",
        "total": 120,
        "terms": [15, 19, 18, 19, 18, 13, 12, 6],
        "courses": [
            ("06046400", "แคลคูลัส 1", 3, 1, 1),
            ("06046403", "การโปรแกรมคอมพิวเตอร์", 3, 1, 2),
            ("06046405", "การเรียนรู้ของเครื่องเชิงความน่าจะเป็น", 3, 2, 1),
            ("06046407", "พื้นฐานวิทยาการข้อมูล", 3, 2, 2),
        ],
        "counts": (6, 1),
    },
    "it-coop": {
        "folder": "lab8b_it_coop",
        "total": 129,
        "terms": [18, 18, 18, 18, 18, 6, 18, 15],
        "courses": [
            ("06016401", "คณิตศาสตร์สำหรับเทคโนโลยีสารสนเทศ", 3, 1, 1),
            ("06016408", "การสร้างโปรแกรมเชิงวัตถุ", 3, 1, 2),
            ("06016403", "เทคโนโลยีสื่อประสม", 3, 2, 1),
            ("06016405", "พื้นฐานความมั่นคงปลอดภัยไซเบอร์", 3, 2, 2),
        ],
        "counts": (7, 5),
    },
    "it-no-coop": {
        "folder": "lab8b_it_no_coop",
        "total": 129,
        "terms": [18, 18, 18, 18, 18, 15, 15, 9],
        "courses": [
            ("06016401", "คณิตศาสตร์สำหรับเทคโนโลยีสารสนเทศ", 3, 1, 1),
            ("06016408", "การสร้างโปรแกรมเชิงวัตถุ", 3, 1, 2),
            ("06016403", "เทคโนโลยีสื่อประสม", 3, 2, 1),
            ("06016405", "พื้นฐานความมั่นคงปลอดภัยไซเบอร์", 3, 2, 2),
        ],
        "counts": (7, 3),
    },
}


def questions(config: dict) -> list[dict]:
    result = []
    for code, name, credits, year, semester in config["courses"]:
        result.extend([
            {"question": f"วิชา{name}มีรหัสอะไร",
             "expect": {"type": "value", "value": code}},
            {"question": f"วิชา {code} มีกี่หน่วยกิต",
             "expect": {"type": "value", "value": credits}},
            {"question": f"วิชา {code} อยู่ปีที่เท่าไร",
             "expect": {"type": "value", "value": year}},
            {"question": f"วิชา {code} อยู่เทอมที่เท่าไร",
             "expect": {"type": "value", "value": semester}},
        ])
    for index, credits in enumerate(config["terms"]):
        year, semester = divmod(index, 2)[0] + 1, index % 2 + 1
        result.append({
            "question": f"ปี {year} เทอม {semester} เรียนกี่หน่วยกิต",
            "expect": {"type": "value", "value": credits},
        })
    result.extend([
        {"question": "หลักสูตรนี้มีทั้งหมดกี่หน่วยกิต",
         "expect": {"type": "value", "value": config["total"]}},
        {"question": "หลักสูตรนี้มีกี่ปี", "expect": {"type": "value", "value": 4}},
        {"question": "ปี 1 เทอม 1 มีกี่วิชา",
         "expect": {"type": "count", "value": config["counts"][0]}},
        {"question": "ปี 4 เทอม 2 มีกี่วิชา",
         "expect": {"type": "count", "value": config["counts"][1]}},
        {"question": "วิชา 09999999 ชื่ออะไร", "expect": {"type": "none", "value": None}},
        {"question": "ปี 5 เทอม 1 เรียนวิชาอะไรบ้าง",
         "expect": {"type": "none", "value": None}},
    ])
    assert len(result) == 30
    return result


def main() -> None:
    for name, config in PROFILES.items():
        output = ROOT / "work" / config["folder"] / "gold_questions.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(questions(config), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"{name}: {output} (30 questions)")


if __name__ == "__main__":
    main()
