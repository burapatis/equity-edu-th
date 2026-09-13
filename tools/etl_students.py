#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 etl_students.py — ETL สำหรับ WSF Simulator และ Gap Map  (v2.0)
================================================================================
 อ่าน "ตารางที่ 11 จำนวนนักเรียนและห้องเรียน จำแนกตามประเภทโรงเรียน รายชั้น"
 (สพฐ.) แล้วแปลงเป็น JSON สำหรับ assets/data/school-data.json

 การใช้งาน:
     python tools/etl_students.py 11.xlsx
     python tools/etl_students.py 11.xlsx --report
     python tools/etl_students.py 11.xlsx --ratio 20 --out assets/data/school-data.json

 ติดตั้ง:  pip install pandas openpyxl
================================================================================
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("❌ ต้องติดตั้งก่อน:  pip install pandas openpyxl")


# ──────────────────────────────────────────────────────────────────────────────
# 1) โครงสร้างคอลัมน์  (index เริ่มที่ 0)
#    col 0 = ชั้น | จากนั้นเป็นคู่ (นักเรียน, ห้องเรียน) ของแต่ละประเภทโรงเรียน
# ──────────────────────────────────────────────────────────────────────────────
SCHOOL_TYPES = [
    # (key,           ชื่อไทย,                 ชื่อย่อ,          col_นร., col_ห้อง)
    ("primary_opec",  "ประถมศึกษา (สพป.)",      "สพป.",           1,  2),
    ("secondary_ope", "มัธยมศึกษา (สพม.)",      "สพม.",           3,  4),
    ("welfare",       "การศึกษาสงเคราะห์",       "กศ.สงเคราะห์",   5,  6),
    ("special_ed",    "การศึกษาพิเศษ",           "กศ.พิเศษ",       7,  8),
    ("special_ctr",   "ศูนย์การศึกษาพิเศษ",      "ศูนย์ กศ.พิเศษ", 9, 10),
    ("total",         "รวมทุกสังกัด สพฐ.",       "รวม",           11, 12),
]

SUBTOTAL_KEYS = ("รวม",)

LEVEL_RULES = [
    ("ปฐมวัย",    ("อนุบาล", "ก่อนประถม")),
    ("ประถม",     ("ประถมศึกษาปีที่", "รวมประถมศึกษา")),
    ("ม.ต้น",     ("มัธยมศึกษาปีที่ 1", "มัธยมศึกษาปีที่ 2",
                   "มัธยมศึกษาปีที่ 3", "ตอนต้น")),
    ("ม.ปลาย",    ("มัธยมศึกษาปีที่ 4", "มัธยมศึกษาปีที่ 5",
                   "มัธยมศึกษาปีที่ 6", "ตอนปลาย")),
]

NULL_TOKENS = {"", "-", "‐", "–", "—", "nan", "none", "null", "n/a"}

# รายชั้นไม่รวมศูนย์ กศ.พิเศษ — ต้นทางบันทึกทั้งก้อนไว้ที่อนุบาล 1
# และไม่ใช้คอลัมน์ "รวม" เพราะจะดึงศูนย์พิเศษปนเข้าไปด้วย
GRADE_TYPE_KEYS = ("primary_opec", "secondary_ope", "welfare", "special_ed")
CORE_KEYS = ("primary_opec", "secondary_ope")


# ──────────────────────────────────────────────────────────────────────────────
# 2) ทำความสะอาดข้อมูล
# ──────────────────────────────────────────────────────────────────────────────
def clean_text(v) -> str:
    if v is None:
        return ""
    s = unicodedata.normalize("NFKC", str(v))
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    return re.sub(r"\s+", " ", s).strip()


def to_int(v) -> int | None:
    s = clean_text(v).replace(",", "")
    if s.lower() in NULL_TOKENS:
        return None
    try:
        return int(round(float(s)))
    except ValueError:
        return None


def detect_level(label: str) -> str:
    for level, keys in LEVEL_RULES:
        if any(k in label for k in keys):
            return level
    return "อื่น ๆ"


def is_subtotal(label: str) -> bool:
    return any(label.replace(" ", "").startswith(k) for k in SUBTOTAL_KEYS)


def safe_div(a, b, nd=2):
    if not a or not b:
        return None
    return round(a / b, nd)


# ──────────────────────────────────────────────────────────────────────────────
# 3) อ่านไฟล์
# ──────────────────────────────────────────────────────────────────────────────
def load_table(path: Path, sheet=0) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
    return df.dropna(how="all").reset_index(drop=True)


def find_data_start(df: pd.DataFrame) -> int:
    for i in range(min(12, len(df))):
        if clean_text(df.iat[i, 0]) == "ชั้น":
            return i + 2
    for i in range(len(df)):
        if to_int(df.iat[i, 1]) is not None:
            return i
    raise ValueError("ไม่พบจุดเริ่มต้นของข้อมูลในไฟล์นี้")


def extract_title(df: pd.DataFrame) -> str:
    t = clean_text(df.iat[0, 0])
    return t if t else "ตารางจำนวนนักเรียนและห้องเรียน"


def extract_year(title: str) -> int:
    m = re.search(r"25\d{2}", title)
    return int(m.group()) if m else datetime.now().year + 543


# ──────────────────────────────────────────────────────────────────────────────
# 4) แปลงเป็นโครงสร้างข้อมูล
# ──────────────────────────────────────────────────────────────────────────────
def parse_rows(df: pd.DataFrame, start: int) -> list[dict]:
    records = []
    for i in range(start, len(df)):
        label = clean_text(df.iat[i, 0])
        if not label:
            continue
        row = {"label": label, "level": detect_level(label),
               "is_total": is_subtotal(label), "by_type": {}}
        has_any = False
        for key, th_name, short, c_stu, c_room in SCHOOL_TYPES:
            if c_room >= df.shape[1]:
                continue
            stu, room = to_int(df.iat[i, c_stu]), to_int(df.iat[i, c_room])
            if stu is None and room is None:
                continue
            has_any = True
            row["by_type"][key] = {
                "name_th": th_name, "short": short,
                "students": stu, "classrooms": room,
                "students_per_room": safe_div(stu, room),
            }
        if has_any:
            records.append(row)
    return records


def sum_types(row: dict, keys: tuple[str, ...]) -> dict:
    stu = room = 0
    found = False
    for key in keys:
        d = row["by_type"].get(key) or {}
        if d.get("students") is None and d.get("classrooms") is None:
            continue
        found = True
        stu += d.get("students") or 0
        room += d.get("classrooms") or 0
    if not found:
        return {}
    return {
        "students": stu,
        "classrooms": room,
        "students_per_room": safe_div(stu, room),
    }


def teacher_gap(students, classrooms, ratio: float) -> dict | None:
    if not students or not classrooms:
        return None
    a, b = students / ratio, float(classrooms)
    return {
        "rule_headcount": round(a),
        "rule_classroom": round(b),
        "gap": round(b - a),
        "gap_pct": round((b - a) / b * 100, 1),
        "status": "deficit" if b > a else "surplus",
    }


def build_payload(path: Path, ratio: float, sheet=0) -> dict:
    df = load_table(path, sheet)
    start = find_data_start(df)
    rows = parse_rows(df, start)
    title = extract_title(df)

    grand = next((r for r in rows if r["label"].replace(" ", "").startswith("รวมทั้งสิ้น")), None)
    if grand is None:
        grand = rows[-1]

    national = []
    for key, th_name, short, *_ in SCHOOL_TYPES:
        d = grand["by_type"].get(key)
        if not d:
            continue
        national.append({
            "key": key, "name_th": th_name, "short": short,
            "students": d["students"], "classrooms": d["classrooms"],
            "students_per_room": d["students_per_room"],
            "teacher": teacher_gap(d["students"], d["classrooms"], ratio),
        })

    grades = []
    for r in rows:
        if r["is_total"]:
            continue
        src = sum_types(r, GRADE_TYPE_KEYS)
        if not src.get("students"):
            continue
        grades.append({
            "label": r["label"], "level": r["level"],
            "students": src.get("students"), "classrooms": src.get("classrooms"),
            "students_per_room": src.get("students_per_room"),
        })

    subtotals = []
    for r in rows:
        if not r["is_total"] or r["label"].replace(" ", "").startswith("รวมทั้งสิ้น"):
            continue
        src = sum_types(r, GRADE_TYPE_KEYS)
        if not src.get("students"):
            continue
        subtotals.append({
            "label": r["label"], "level": r["level"],
            "students": src.get("students"), "classrooms": src.get("classrooms"),
            "students_per_room": src.get("students_per_room"),
        })

    gt = grand["by_type"].get("total") or {}
    return {
        "meta": {
            "title": title,
            "source": "สำนักงานคณะกรรมการการศึกษาขั้นพื้นฐาน (สพฐ.)",
            "academic_year": extract_year(title),
            "source_file": path.name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "teacher_ratio": ratio,
            "coverage_note": "ครอบคลุมเฉพาะสถานศึกษาสังกัด สพฐ. ไม่รวม อปท. เอกชน และสังกัดอื่น",
            "caveat": (f"อัตรา 1:{ratio:g} เป็นเกณฑ์อ้างอิงเพื่อการสาธิต "
                       "เกณฑ์อัตรากำลังจริงของ ก.ค.ศ. จำแนกตามขนาดโรงเรียนและมีรายละเอียดมากกว่านี้"),
            "aggregation_note": ("ข้อมูลเป็นค่ารวมระดับประเทศ จึงไม่สะท้อนการกระจายรายโรงเรียน "
                                 "ช่องว่างที่แท้จริงในโรงเรียนขนาดเล็กรายแห่งย่อมรุนแรงกว่าค่าเฉลี่ยนี้"),
            "grades_note": ("รายชั้นและผลรวมย่อยรวม สพป. สพม. การศึกษาสงเคราะห์ และการศึกษาพิเศษ "
                            "ไม่รวมศูนย์การศึกษาพิเศษ เพราะต้นทางบันทึกทั้งก้อนไว้ที่อนุบาล 1"),
            "core_keys": list(CORE_KEYS),
        },
        "national": national,
        "grades": grades,
        "subtotals": subtotals,
        "grand_total": {
            "students": gt.get("students"),
            "classrooms": gt.get("classrooms"),
            "students_per_room": gt.get("students_per_room"),
            "teacher": teacher_gap(gt.get("students"), gt.get("classrooms"), ratio),
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# 5) รายงานสรุป
# ──────────────────────────────────────────────────────────────────────────────
def print_report(p: dict) -> None:
    n = lambda v: f"{v:,}" if isinstance(v, (int, float)) else "—"
    line = "─" * 78
    ratio = p["meta"]["teacher_ratio"]

    print(f"\n{line}\n📊 {p['meta']['title']}\n{line}")
    print(f"{'ประเภทโรงเรียน':<26}{'นักเรียน':>13}{'ห้องเรียน':>12}{'นร./ห้อง':>11}")
    print(line)
    for t in p["national"]:
        print(f"{t['name_th']:<26}{n(t['students']):>13}"
              f"{n(t['classrooms']):>12}{t['students_per_room'] or '—':>11}")

    print(f"\n{line}\n🎯 การจำลองความต้องการครู (เกณฑ์อ้างอิง 1:{ratio:g})\n{line}")
    print(f"{'หน่วย':<26}{'กฎเดิม(หัว)':>14}{'กฎใหม่(ห้อง)':>14}{'ส่วนต่าง':>16}")
    print(line)
    tot_def = tot_sur = core_def = core_sur = 0
    for t in p["national"]:
        tg = t["teacher"]
        if not tg or t["key"] == "total":
            continue
        if tg["status"] == "deficit":
            tot_def += abs(tg["gap"]); mark = "🔴 ขาด"
            if t["key"] in CORE_KEYS:
                core_def += abs(tg["gap"])
        else:
            tot_sur += abs(tg["gap"]); mark = "🟢 เกิน"
            if t["key"] in CORE_KEYS:
                core_sur += abs(tg["gap"])
        print(f"{t['name_th']:<26}{n(tg['rule_headcount']):>14}"
              f"{n(tg['rule_classroom']):>14}{mark} {n(abs(tg['gap'])):>8}")

    print(line)
    print("  ระบบหลัก (สพป./สพม.)")
    print(f"    ขาดแคลน        {core_def:>12,} อัตรา")
    print(f"    ส่วนเกิน        {core_sur:>12,} อัตรา")
    print(f"    สุทธิ           {core_def - core_sur:>12,} อัตรา")
    print("  รวมทุกประเภท (โมเดล 1:20 รวมพิเศษ)")
    print(f"    ขาดแคลน        {tot_def:>12,} อัตรา")
    print(f"    ส่วนเกิน        {tot_sur:>12,} อัตรา")
    print(f"    สุทธิ           {tot_def - tot_sur:>12,} อัตรา")
    print(f"\n⚠️  {p['meta']['aggregation_note']}")
    if p["meta"].get("grades_note"):
        print(f"⚠️  {p['meta']['grades_note']}\n")


# ──────────────────────────────────────────────────────────────────────────────
# 6) CLI
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="แปลงตารางจำนวนนักเรียน/ห้องเรียน (สพฐ.) เป็น JSON")
    ap.add_argument("input", type=Path, help="ไฟล์ .xlsx ต้นทาง เช่น 11.xlsx")
    ap.add_argument("--out", type=Path, default=Path("assets/data/school-data.json"))
    ap.add_argument("--sheet", default=0, help="ชื่อหรือลำดับชีต (ค่าเริ่มต้น 0)")
    ap.add_argument("--ratio", type=float, default=20.0, help="อัตรานักเรียนต่อครูอ้างอิง")
    ap.add_argument("--report", action="store_true", help="แสดงรายงานสรุปบนหน้าจอ")
    args = ap.parse_args()

    if not args.input.exists():
        sys.exit(f"❌ ไม่พบไฟล์: {args.input}")

    try:
        sheet = int(args.sheet)
    except ValueError:
        sheet = args.sheet

    payload = build_payload(args.input, args.ratio, sheet)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ สร้างไฟล์แล้ว: {args.out}")
    print(f"   • รายชั้น {len(payload['grades'])} รายการ"
          f" · ผลรวมย่อย {len(payload['subtotals'])} รายการ"
          f" · ประเภทโรงเรียน {len(payload['national'])} ประเภท")

    if args.report:
        print_report(payload)


if __name__ == "__main__":
    main()