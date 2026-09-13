#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ทดสอบ ETL เทียบตัวเลขใน 11.xlsx — ไม่ต้องติดตั้งไลบรารีเพิ่มนอกจาก requirements ของ ETL"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))

from etl_students import (  # noqa: E402
    CORE_KEYS,
    GRADE_TYPE_KEYS,
    build_payload,
    load_table,
    parse_rows,
    find_data_start,
    teacher_gap,
)

XLSX = ROOT / "11.xlsx"


class TestEtlAgainstExcel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not XLSX.exists():
            raise unittest.SkipTest(f"ไม่พบ {XLSX}")
        cls.data = build_payload(XLSX, 20.0)
        cls.by_key = {u["key"]: u for u in cls.data["national"]}

    def test_grand_total_matches_table_11(self):
        gt = self.data["grand_total"]
        self.assertEqual(gt["students"], 6_172_840)
        self.assertEqual(gt["classrooms"], 348_047)

    def test_core_units_match_excel(self):
        prim = self.by_key["primary_opec"]
        sec = self.by_key["secondary_ope"]
        self.assertEqual(prim["students"], 3_843_825)
        self.assertEqual(prim["classrooms"], 263_359)
        self.assertEqual(sec["students"], 2_251_217)
        self.assertEqual(sec["classrooms"], 69_704)

    def test_core_teacher_gap(self):
        prim = self.by_key["primary_opec"]["teacher"]
        sec = self.by_key["secondary_ope"]["teacher"]
        self.assertEqual(prim["gap"], 71_168)
        self.assertEqual(prim["status"], "deficit")
        self.assertEqual(sec["gap"], -42_857)
        self.assertEqual(sec["status"], "surplus")

    def test_core_keys_are_primary_and_secondary(self):
        self.assertEqual(CORE_KEYS, ("primary_opec", "secondary_ope"))
        self.assertEqual(GRADE_TYPE_KEYS, ("primary_opec", "secondary_ope", "welfare", "special_ed"))

    def test_inclusive_modelled_deficit(self):
        deficit = sum(
            abs(u["teacher"]["gap"])
            for u in self.data["national"]
            if u["key"] != "total" and u["teacher"] and u["teacher"]["status"] == "deficit"
        )
        self.assertEqual(deficit, 82_262)

    def test_kindergarten_1_excludes_special_center(self):
        k1 = next(g for g in self.data["grades"] if g["label"] == "อนุบาล 1")
        self.assertEqual(k1["students"], 66_636)
        self.assertEqual(k1["classrooms"], 7_077)
        special = self.by_key["special_ctr"]
        self.assertEqual(special["students"], 30_311)
        self.assertEqual(k1["students"] + special["students"], 96_947)
        self.assertNotEqual(k1["students"], 96_947)

    def test_grades_include_upper_secondary(self):
        labels = [g["label"] for g in self.data["grades"]]
        self.assertEqual(len(labels), 15)
        self.assertTrue(any("มัธยมศึกษาปีที่ 6" in x for x in labels))

    def test_raw_excel_primary_total_matches_payload(self):
        df = load_table(XLSX)
        rows = parse_rows(df, find_data_start(df))
        grand = next(r for r in rows if r["label"].replace(" ", "").startswith("รวมทั้งสิ้น"))
        src = grand["by_type"]["primary_opec"]
        self.assertEqual(src["students"], self.by_key["primary_opec"]["students"])
        self.assertEqual(src["classrooms"], self.by_key["primary_opec"]["classrooms"])

    def test_teacher_gap_helper(self):
        gap = teacher_gap(3_843_825, 263_359, 20.0)
        self.assertIsNotNone(gap)
        self.assertEqual(gap["gap"], 71_168)


if __name__ == "__main__":
    unittest.main(verbosity=2)
