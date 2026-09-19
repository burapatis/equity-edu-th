#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 build_docs.py — สร้างเอกสารนำเสนออัตโนมัติจากข้อมูล สพฐ.
================================================================================
 สร้าง 3 ไฟล์จากแหล่งข้อมูลเดียว (assets/data/school-data.json):
   1) wsf-deck.pptx          ชุดสไลด์ 12 หน้า + สไลด์สำรอง + speaker notes
   2) executive-brief.pdf    บทสรุปผู้บริหาร 5 หน้า
   3) one-pager.pdf          บันทึกข้อเสนอ 1 หน้า

 การใช้งาน:
   python tools/build_docs.py --all
   python tools/build_docs.py --deck --ratio 20
   python tools/build_docs.py --brief --onepager --out dist/

 ติดตั้ง:
   pip install -r tools/requirements.txt

 ฟอนต์ (จำเป็นสำหรับ PDF):
   ดาวน์โหลด Sarabun จาก Google Fonts แล้ววางไว้ที่ tools/fonts/
   https://fonts.google.com/specimen/Sarabun
================================================================================
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_DIRS = [
    Path(__file__).resolve().parent / "fonts",
    Path("/usr/share/fonts/truetype/sarabun"),
    Path("/usr/share/fonts/truetype/tlwg"),
    Path("/usr/share/fonts/truetype/noto"),
    Path("/usr/share/fonts/truetype/thai"),
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
    Path("C:/Windows/Fonts"),
]

# ──────────────────────────────────────────────────────────────────────────────
# ส่วนที่ 0 — ข้อมูลสำรอง (ตรงกับ 11.xlsx ปีการศึกษา 2569)
# ──────────────────────────────────────────────────────────────────────────────
FALLBACK = {
    "meta": {
        "title": "ตารางที่ 11 จำนวนนักเรียนและห้องเรียน จำแนกตามประเภทโรงเรียน รายชั้น",
        "source": "สำนักงานคณะกรรมการการศึกษาขั้นพื้นฐาน (สพฐ.)",
        "academic_year": 2569,
        "teacher_ratio": 20,
        "coverage_note": "ครอบคลุมเฉพาะสถานศึกษาสังกัด สพฐ. ไม่รวม อปท. เอกชน และสังกัดอื่น",
    },
    "national": [
        {"key": "primary_opec",  "name_th": "ประถมศึกษา (สพป.)",  "students": 3843825, "classrooms": 263359},
        {"key": "special_ctr",   "name_th": "ศูนย์การศึกษาพิเศษ",  "students": 30311,   "classrooms": 7702},
        {"key": "special_ed",    "name_th": "การศึกษาพิเศษ",       "students": 12762,   "classrooms": 4731},
        {"key": "welfare",       "name_th": "การศึกษาสงเคราะห์",   "students": 34725,   "classrooms": 2551},
        {"key": "secondary_ope", "name_th": "มัธยมศึกษา (สพม.)",  "students": 2251217, "classrooms": 69704},
    ],
    "grand_total": {"students": 6172840, "classrooms": 348047},
    "grades": [
        {"label": "อนุบาล 1",          "students": 66636,  "classrooms": 7077},
        {"label": "อนุบาล 2",          "students": 303288, "classrooms": 27107},
        {"label": "อนุบาล 3",          "students": 334747, "classrooms": 27816},
        {"label": "ประถมศึกษาปีที่ 1", "students": 410425, "classrooms": 29379},
        {"label": "ประถมศึกษาปีที่ 2", "students": 433610, "classrooms": 29923},
        {"label": "ประถมศึกษาปีที่ 3", "students": 449855, "classrooms": 30077},
        {"label": "ประถมศึกษาปีที่ 4", "students": 450380, "classrooms": 30020},
        {"label": "ประถมศึกษาปีที่ 5", "students": 462565, "classrooms": 30075},
        {"label": "ประถมศึกษาปีที่ 6", "students": 475740, "classrooms": 30373},
        {"label": "มัธยมศึกษาปีที่ 1", "students": 554262, "classrooms": 20544},
        {"label": "มัธยมศึกษาปีที่ 2", "students": 574735, "classrooms": 20757},
        {"label": "มัธยมศึกษาปีที่ 3", "students": 552600, "classrooms": 20551},
        {"label": "มัธยมศึกษาปีที่ 4 หรือ เทียบเท่า", "students": 375959, "classrooms": 12264},
        {"label": "มัธยมศึกษาปีที่ 5 หรือ เทียบเท่า", "students": 354681, "classrooms": 12102},
        {"label": "มัธยมศึกษาปีที่ 6 หรือ เทียบเท่า", "students": 343046, "classrooms": 11836},
    ],
}

SHORT_NAME = {
    "primary_opec": "สพป.",
    "secondary_ope": "สพม.",
    "welfare": "กศ.สงเคราะห์",
    "special_ed": "กศ.พิเศษ",
    "special_ctr": "ศูนย์ กศ.พิเศษ",
}
CORE_KEYS = ("primary_opec", "secondary_ope")

# ──────────────────────────────────────────────────────────────────────────────
# ส่วนที่ 1 — โมเดลข้อมูลและการคำนวณ
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class Unit:
    key: str
    name: str
    short: str
    students: int
    rooms: int
    ratio: float = 20.0

    @property
    def spr(self) -> float:
        return self.students / self.rooms if self.rooms else 0.0

    @property
    def rule_headcount(self) -> float:
        return self.students / self.ratio

    @property
    def rule_classroom(self) -> float:
        return float(self.rooms)

    @property
    def gap(self) -> float:
        """บวก = ขาดครู · ลบ = เกิน"""
        return self.rule_classroom - self.rule_headcount


@dataclass
class Analysis:
    meta: dict
    units: list[Unit]
    grades: list[dict]
    total_students: int
    total_rooms: int
    ratio: float
    deficits: list[Unit] = field(default_factory=list)
    surpluses: list[Unit] = field(default_factory=list)

    def __post_init__(self):
        self.deficits = sorted([u for u in self.units if u.gap > 0],
                               key=lambda u: u.gap, reverse=True)
        self.surpluses = sorted([u for u in self.units if u.gap < 0],
                                key=lambda u: u.gap)

    @property
    def total_deficit(self) -> float:
        return sum(u.gap for u in self.deficits)

    @property
    def total_surplus(self) -> float:
        return abs(sum(u.gap for u in self.surpluses))

    @property
    def net_gap(self) -> float:
        return self.total_deficit - self.total_surplus

    @property
    def core_deficit(self) -> float:
        return sum(u.gap for u in self.units if u.key in CORE_KEYS and u.gap > 0)

    @property
    def core_surplus(self) -> float:
        return abs(sum(u.gap for u in self.units if u.key in CORE_KEYS and u.gap < 0))

    @property
    def core_net(self) -> float:
        return self.core_deficit - self.core_surplus

    @property
    def primary(self) -> Unit | None:
        return next((u for u in self.units if u.key == "primary_opec"), None)

    @property
    def secondary(self) -> Unit | None:
        return next((u for u in self.units if u.key == "secondary_ope"), None)

    @property
    def total_spr(self) -> float:
        return self.total_students / self.total_rooms if self.total_rooms else 0.0

    def realloc(self, pct: float, years: int) -> dict:
        """จำลองการโยกส่วนเกินไปเติมหน่วยที่ขาด"""
        prim = self.primary
        moved = self.total_surplus * pct
        remain = max(0.0, (prim.gap if prim else 0) - moved)
        closed = min(100.0, moved / prim.gap * 100) if prim and prim.gap > 0 else 0.0
        return {
            "moved": moved,
            "per_year": moved / max(years, 1),
            "remain": remain,
            "closed_pct": closed,
            "years": years,
        }


def load_analysis(json_path: Path, ratio: float) -> Analysis:
    raw = FALLBACK
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if data.get("national"):
                raw = data
                print(f"📥 อ่านข้อมูลจาก {json_path}")
        except Exception as e:
            print(f"⚠️  อ่าน JSON ไม่สำเร็จ ({e}) — ใช้ข้อมูลสำรองที่ฝังไว้")
    else:
        print("ℹ️  ไม่พบ school-data.json — ใช้ข้อมูลสำรองที่ฝังไว้ (11.xlsx ปี 2569)")

    units = []
    for n in raw["national"]:
        if n.get("key") == "total" or not n.get("classrooms"):
            continue
        units.append(Unit(
            key=n["key"],
            name=n["name_th"],
            short=SHORT_NAME.get(n["key"], n["name_th"][:12]),
            students=int(n["students"]),
            rooms=int(n["classrooms"]),
            ratio=ratio,
        ))

    gt = raw.get("grand_total", {})
    return Analysis(
        meta=raw.get("meta", FALLBACK["meta"]),
        units=units,
        grades=raw.get("grades", FALLBACK["grades"]),
        total_students=int(gt.get("students") or sum(u.students for u in units)),
        total_rooms=int(gt.get("classrooms") or sum(u.rooms for u in units)),
        ratio=ratio,
    )


def th(n) -> str:
    """จัดรูปแบบตัวเลขไทย"""
    return f"{round(n):,}"


# ──────────────────────────────────────────────────────────────────────────────
# ส่วนที่ 2 — ชุดสี (ใช้ร่วมกันทั้ง PPTX และ PDF)
# ──────────────────────────────────────────────────────────────────────────────
PALETTE = {
    "navy":   (0x1A, 0x2B, 0x4C),
    "navy2":  (0x25, 0x40, 0x6E),
    "navy_d": (0x0D, 0x1A, 0x30),
    "amber":  (0xE8, 0xA3, 0x3D),
    "red":    (0xC9, 0x48, 0x3C),
    "green":  (0x2E, 0x8B, 0x57),
    "teal":   (0x0F, 0x8A, 0x7E),
    "grey":   (0x4A, 0x57, 0x69),
    "grey_l": (0x7B, 0x87, 0x98),
    "line":   (0xE2, 0xE8, 0xF1),
    "bg":     (0xF6, 0xF8, 0xFB),
    "white":  (0xFF, 0xFF, 0xFF),
}


# ══════════════════════════════════════════════════════════════════════════════
#  PART A — POWERPOINT
# ══════════════════════════════════════════════════════════════════════════════
def build_deck(a: Analysis, out: Path, font: str) -> Path:
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt, Emu
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.oxml.ns import qn
    except ImportError:
        sys.exit("❌ ต้องติดตั้งก่อน:  pip install python-pptx")

    C = {k: RGBColor(*v) for k, v in PALETTE.items()}
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    W, H = 13.333, 7.5
    BLANK = prs.slide_layouts[6]

    # ---------- helpers ----------
    def _fix_font(run, name):
        """ตั้งฟอนต์ให้ครบทั้ง latin / east-asian / complex-script (สำคัญมากสำหรับไทย)"""
        rPr = run._r.get_or_add_rPr()
        for tag in ("a:latin", "a:ea", "a:cs"):
            el = rPr.find(qn(tag))
            if el is None:
                el = rPr.makeelement(qn(tag), {})
                rPr.append(el)
            el.set("typeface", name)

    def text(slide, x, y, w, h, content, *, size=18, bold=False, color="navy",
             align=PP_ALIGN.LEFT, space=6, anchor=MSO_ANCHOR.TOP, line=1.25):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        lines = content if isinstance(content, list) else [content]
        for i, item in enumerate(lines):
            if isinstance(item, dict):
                t, sz, bd, cl = item.get("t", ""), item.get("size", size), \
                                item.get("bold", bold), item.get("color", color)
            else:
                t, sz, bd, cl = item, size, bold, color
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            p.space_after = Pt(space)
            p.line_spacing = line
            r = p.add_run()
            r.text = t
            r.font.size = Pt(sz)
            r.font.bold = bd
            r.font.color.rgb = C[cl]
            r.font.name = font
            _fix_font(r, font)
        return box

    def rect(slide, x, y, w, h, fill="navy", line_col=None, radius=False):
        shp = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
            Inches(x), Inches(y), Inches(w), Inches(h))
        shp.fill.solid()
        shp.fill.fore_color.rgb = C[fill]
        if line_col:
            shp.line.color.rgb = C[line_col]
            shp.line.width = Pt(1)
        else:
            shp.line.fill.background()
        shp.shadow.inherit = False
        if radius:
            try:
                shp.adjustments[0] = 0.06
            except Exception:
                pass
        shp.text_frame.text = ""
        return shp

    def notes(slide, body):
        tf = slide.notes_slide.notes_text_frame
        tf.text = body.strip()
        for p in tf.paragraphs:
            for r in p.runs:
                r.font.size = Pt(11)
                r.font.name = font
                _fix_font(r, font)

    def new(title_band=True, band_text=""):
        s = prs.slides.add_slide(BLANK)
        rect(s, 0, 0, W, H, "white")
        if title_band:
            rect(s, 0, 0, W, 0.22, "navy")
            if band_text:
                text(s, 0.6, 0.35, W - 1.2, 0.5, band_text, size=12,
                     bold=True, color="grey_l")
        return s

    prim, sec = a.primary, a.secondary

    # ══════ SLIDE 1 — ปก ══════
    s = new(False)
    rect(s, 0, 0, W, H, "navy_d")
    rect(s, 0, 0, 0.35, H, "amber")
    text(s, 1.2, 2.0, 11, 0.5, "รายงานวิเคราะห์นโยบายสหวิทยาการ · 21 ส่วน",
         size=14, bold=True, color="amber")
    text(s, 1.2, 2.6, 11.2, 2.2, [
        {"t": "ประเทศไทยไม่ได้ขาดเงิน", "size": 44, "bold": True, "color": "white"},
        {"t": "แต่ขาด “สูตร”", "size": 54, "bold": True, "color": "amber"},
    ], line=1.15)
    text(s, 1.2, 5.0, 10.5, 1.0,
         "การปฏิรูปการจัดสรรทรัพยากรเพื่อความเสมอภาคทางการศึกษา",
         size=18, color="white")
    text(s, 1.2, 6.5, 10.5, 0.5,
         f"ข้อมูลประกอบ: {a.meta.get('source')} · ปีการศึกษา {a.meta.get('academic_year')}",
         size=11, color="grey_l")
    notes(s, """
[45 วินาที] ยืนนิ่ง มองรอบห้อง 2 วินาทีก่อนพูด

"กราบเรียนท่านประธานและท่านผู้บริหารทุกท่านครับ"
"ก่อนเข้าเนื้อหา ผมขอเรียนสองเรื่องที่ผม *จะไม่* ขอในวันนี้ก่อนนะครับ"
[มอง ผอ.สำนักงบประมาณ] "เรื่องแรก — ผมไม่ได้มาขอเงินเพิ่มแม้แต่บาทเดียว"
[กลับมากลางห้อง] "เรื่องที่สอง — ผมไม่ได้ขอให้แก้กฎหมายแม้แต่มาตราเดียวในปีนี้"
"ผมมาเสนอเรื่องเดียวครับ — คือการเปลี่ยนสูตร" [หยุด 3 วินาที]

⚠️ อย่าอ่านสไลด์ · ประโยคนี้ทำหน้าที่ปลดอาวุธผู้ฟังทันที
""")

    # ══════ SLIDE 2 — 97:3 ══════
    s = new(band_text="สไลด์ 2 / 12")
    text(s, 0.6, 0.9, 12, 1.3, "97 : 3", size=76, bold=True,
         color="navy", align=PP_ALIGN.CENTER)
    text(s, 0.6, 2.2, 12, 0.4, "ตัวเลขเดียวที่ต้องจำ", size=18,
         color="grey", align=PP_ALIGN.CENTER)

    rect(s, 0.9, 3.0, 11.5, 1.1, "red")
    text(s, 1.2, 3.2, 7.5, 0.8, [
        {"t": "เงินอุดหนุนรายหัว + อัตรากำลังครู", "size": 17, "bold": True, "color": "white"},
        {"t": "ออกแบบตามหลัก “เท่ากันทุกหัว” (Equality)", "size": 12, "color": "white"},
    ], space=2)
    text(s, 9.6, 3.25, 2.5, 0.7, "≈ 97–98%", size=26, bold=True,
         color="white", align=PP_ALIGN.RIGHT)

    rect(s, 0.9, 4.3, 11.5, 1.1, "green")
    text(s, 1.2, 4.5, 7.5, 0.8, [
        {"t": "กสศ. + โครงการเฉพาะ", "size": 17, "bold": True, "color": "white"},
        {"t": "ออกแบบตามหลัก “ตามความจำเป็น” (Equity)", "size": 12, "color": "white"},
    ], space=2)
    text(s, 9.6, 4.55, 2.5, 0.7, "≈ 2–3%", size=26, bold=True,
         color="white", align=PP_ALIGN.RIGHT)

    rect(s, 0.9, 5.75, 11.5, 1.0, "bg")
    rect(s, 0.9, 5.75, 0.09, 1.0, "amber")
    text(s, 1.3, 5.95, 11, 0.7,
         "ไม่ว่าจะทำ 3% ให้ดีเพียงใด ก็ไม่มีทางหักล้างแรงของ 97% ได้",
         size=21, bold=True, color="navy")
    notes(s, """
[2 นาที] สไลด์ที่สำคัญที่สุดในชุดนี้

"เรามีกลไกที่ออกแบบถูกหลักที่สุดในภูมิภาค คือ กสศ. — แต่มีขนาดแค่ 2–3%
ขณะที่อีก 97% ยังจัดสรรแบบเท่ากันทุกหัว"

⚠️ ย่อหน้าป้องกัน — ห้ามข้าม [หันไปทาง ผอ.กสศ.]
"นี่ไม่ใช่การวิจารณ์ กสศ. เลยแม้แต่น้อย — ตรงกันข้าม ระบบคัดกรอง iSEE
อยู่ในระดับแนวหน้าของภูมิภาค ปัญหาคือเราคาดหวังให้ 3% ไปแก้สิ่งที่ 97% สร้างขึ้น"

ปิดสไลด์ช้าที่สุด แล้วเงียบ 4 วินาที
""")

    # ══════ SLIDE 3 — 4 มิติ ══════
    s = new(band_text="สไลด์ 3 / 12")
    text(s, 0.6, 0.55, 12, 0.6, "ปัญหาย้ายที่แล้ว แต่เครื่องมือยังไม่ย้ายตาม",
         size=30, bold=True)
    text(s, 0.6, 1.25, 12, 0.4,
         "ความเหลื่อมล้ำไม่ใช่ปัญหาเดียว แต่เป็นปัญหา 4 ชั้นที่ซ้อนกัน",
         size=14, color="grey")

    dims = [
        ("1", "การเข้าถึง", "Access", "ดีที่ระดับประถม เหลือเพียงกลุ่มตกค้าง", "green"),
        ("2", "การคงอยู่", "Retention", "หน้าผาที่รอยต่อ ม.3 → ม.4", "red"),
        ("3", "การเรียนรู้", "Learning", "วิกฤตที่สุด — จุดที่ต้องทุ่มทรัพยากร", "red"),
        ("4", "การเปลี่ยนผ่าน", "Transition", "การเลื่อนชั้นทางสังคมยังต่ำ", "amber"),
    ]
    for i, (no, thn, en, desc, col) in enumerate(dims):
        x = 0.6 + i * 3.1
        rect(s, x, 2.0, 2.85, 2.6, "bg", "line")
        rect(s, x, 2.0, 2.85, 0.09, col)
        text(s, x + 0.25, 2.2, 2.4, 0.5, no, size=28, bold=True, color="grey_l")
        text(s, x + 0.25, 2.75, 2.4, 1.6, [
            {"t": thn, "size": 18, "bold": True, "color": "navy"},
            {"t": en, "size": 11, "color": "grey_l"},
            {"t": desc, "size": 12, "color": "grey"},
        ], space=4)

    rect(s, 0.6, 5.0, 12.1, 1.5, "red")
    text(s, 0.95, 5.2, 11.5, 1.1, [
        {"t": "Problem–Instrument Mismatch", "size": 17, "bold": True, "color": "white"},
        {"t": "ไทยแก้ปัญหามิติที่ 1 ได้เกือบหมดแล้ว แต่ยังใช้เครื่องมือของมิติที่ 1 "
              "(ขยายโอกาส + อุดหนุนค่าใช้จ่าย) มาแก้ปัญหาที่ตอนนี้อยู่ที่มิติที่ 3",
         "size": 13, "color": "white"},
    ], space=4)
    notes(s, """
[2 นาที]
ภาพเปรียบเทียบ: "เหมือนเราสร้างถนนไปถึงทุกหมู่บ้านสำเร็จแล้ว แต่ยังทุ่มงบสร้างถนนต่อ
ทั้งที่ปัญหาตอนนี้คือรถที่วิ่งบนถนนนั้นเครื่องไม่ดี"

เน้นเสียง: "เราชนะสงครามครั้งที่แล้ว แต่ยังใช้อาวุธชุดเดิมรบสงครามครั้งใหม่"

🔀 ถ้าถูกแย้งว่า "การเข้าถึงยังไม่ดีจริง" → ยอมรับบางส่วน:
"ถูกครับ ยังมีเด็กนอกระบบเกือบล้านคน แต่นั่นคือกลุ่มตกค้างที่ต้องใช้เครื่องมือเฉพาะทาง"
""")

    # ══════ SLIDE 4 — หลักฐาน ══════
    s = new(band_text="สไลด์ 4 / 12")
    text(s, 0.6, 0.55, 12, 0.6, "หลักฐานเชิงประจักษ์จากข้อมูล สพฐ.", size=30, bold=True)
    text(s, 0.6, 1.25, 12, 0.4,
         f"{a.meta.get('title')} · ปีการศึกษา {a.meta.get('academic_year')}",
         size=13, color="grey")

    cards = [
        (th(a.total_students), "คน", "นักเรียนทั้งสังกัด สพฐ."),
        (th(a.total_rooms), "ห้อง", "ห้องเรียนทั้งหมด"),
        (f"{prim.spr:.1f}", "คน/ห้อง", "ประถมศึกษา (สพป.)"),
        (f"{sec.spr:.1f}", "คน/ห้อง", "มัธยมศึกษา (สพม.)"),
    ]
    for i, (num, unit, cap) in enumerate(cards):
        x = 0.6 + i * 3.1
        rect(s, x, 2.0, 2.85, 1.7, "bg", "line")
        text(s, x + 0.25, 2.2, 2.4, 0.7, num, size=27, bold=True, color="navy")
        text(s, x + 0.25, 2.85, 2.4, 0.7, [
            {"t": unit, "size": 11, "color": "grey_l"},
            {"t": cap, "size": 13, "bold": True, "color": "grey"},
        ], space=2)

    rect(s, 0.6, 4.1, 12.1, 0.45, "navy")
    for i, (t, x, w) in enumerate([("ประเภทโรงเรียน", 0.85, 4.0),
                                   ("นักเรียน", 5.0, 2.3),
                                   ("ห้องเรียน", 7.5, 2.3),
                                   ("นักเรียน/ห้อง", 10.0, 2.4)]):
        text(s, x, 4.15, w, 0.35, t, size=12, bold=True, color="white",
             align=PP_ALIGN.LEFT if i == 0 else PP_ALIGN.RIGHT)

    for i, u in enumerate(a.units):
        y = 4.6 + i * 0.42
        if i % 2 == 0:
            rect(s, 0.6, y, 12.1, 0.42, "bg")
        col = "red" if u.spr < a.ratio else "green"
        text(s, 0.85, y + 0.05, 4.0, 0.32, u.name, size=12, color="grey")
        text(s, 5.0, y + 0.05, 2.3, 0.32, th(u.students), size=12,
             color="grey", align=PP_ALIGN.RIGHT)
        text(s, 7.5, y + 0.05, 2.3, 0.32, th(u.rooms), size=12,
             color="grey", align=PP_ALIGN.RIGHT)
        text(s, 10.0, y + 0.05, 2.4, 0.32, f"{u.spr:.1f}", size=12,
             bold=True, color=col, align=PP_ALIGN.RIGHT)
    notes(s, f"""
[1.5 นาที] อย่าไล่อ่านทุกบรรทัด — เลือกพูด 3 ตัวเลข

① "สพป. มีนักเรียนเฉลี่ยเพียง {prim.spr:.1f} คนต่อห้อง"
② "ขณะที่ สพม. มี {sec.spr:.1f} คน — ต่างกัน {sec.spr/prim.spr:.1f} เท่า"
③ "แต่เราจัดสรรครูด้วยอัตราเดียวกันทั้งระบบ"

⚠️ พูดเอง อย่ารอให้ถูกจับได้:
"อัตรา 1:{a.ratio:.0f} เป็นเกณฑ์อ้างอิงเพื่อการสาธิต เกณฑ์จริงของ ก.ค.ศ.
จำแนกตามขนาดโรงเรียนและซับซ้อนกว่านี้ครับ"
→ การยอมรับข้อจำกัดเองจะเพิ่มความน่าเชื่อถือของทั้งชุดนำเสนอ
""")

    # ══════ SLIDE 5 — วงจรกับดัก ══════
    s = new(band_text="สไลด์ 5 / 12")
    text(s, 0.6, 0.55, 12, 0.6, "กับดักโรงเรียนขนาดเล็ก — วงจรที่หมุนเองได้",
         size=30, bold=True)
    steps = [
        "จำนวนเด็กในโรงเรียนลดลง",
        "เกณฑ์อัตรากำลังอิง “จำนวนนักเรียน” → ได้ครูน้อยลง",
        "ครูควบชั้น / สอนไม่ตรงวิชาเอก",
        "คุณภาพการเรียนการสอนลดลง",
        "ผู้ปกครองที่มีทางเลือกย้ายลูกออก",
    ]
    for i, stp in enumerate(steps):
        y = 1.5 + i * 0.72
        rect(s, 2.6, y, 8.2, 0.58, "bg", "line")
        rect(s, 2.6, y, 0.58, 0.58, "navy")
        text(s, 2.6, y + 0.12, 0.58, 0.35, str(i + 1), size=15, bold=True,
             color="white", align=PP_ALIGN.CENTER)
        text(s, 3.4, y + 0.13, 7.2, 0.35, stp, size=14, color="grey")
        if i < len(steps) - 1:
            text(s, 2.6, y + 0.55, 0.58, 0.2, "↓", size=13, bold=True,
                 color="red", align=PP_ALIGN.CENTER)

    rect(s, 2.6, 5.1, 8.2, 0.58, "red")
    text(s, 2.75, 5.22, 8.0, 0.35, "↻   จำนวนเด็กลดลงอีก — วนกลับสู่ขั้นที่ 1",
         size=14, bold=True, color="white")

    rect(s, 0.6, 6.05, 12.1, 0.95, "bg", "amber")
    text(s, 0.95, 6.18, 11.5, 0.7, [
        {"t": "การกลับกรอบคำถาม", "size": 14, "bold": True, "color": "navy"},
        {"t": "คำถามที่ถูกต้องไม่ใช่ “ควรควบรวมโรงเรียนเล็กหรือไม่” "
              "แต่คือ “ทำไมสูตรจัดสรรของเราจึงลงโทษโรงเรียนตามขนาด แทนที่จะจัดสรรตามความจำเป็น”",
         "size": 13, "color": "grey"},
    ], space=3)
    notes(s, """
[2 นาที] สไลด์ที่เปลี่ยนใจคนได้มากที่สุด — ชี้ไล่ตามลูกศรทีละขั้น

"สังเกตนะครับ ไม่มีขั้นตอนไหนที่เกิดจากครูขี้เกียจ หรือผู้บริหารไม่เก่ง —
ทุกขั้นตอนเป็นผลของกฎเกณฑ์ที่เราเขียนขึ้นเอง"

เสริมเชิงวิชาการ: "งานวิจัยสากลชี้ว่าโรงเรียนเล็กมีข้อได้เปรียบด้านการดูแลรายบุคคล
ปัญหาจึงไม่ได้อยู่ที่ขนาด แต่อยู่ที่สูตรที่ลงโทษขนาด"

🔀 ถ้ามีเสียงเสนอให้ควบรวม:
"ผมไม่ได้ค้านครับ แต่เราไม่เคยประเมินย้อนหลังเลยว่าการควบรวม 10 ปีที่ผ่านมา
ให้ผลอย่างไร ผมเสนอให้วิจัยก่อนขยายนโยบาย ซึ่งอยู่ในแผนปีที่ 2"
""")

    # ══════ SLIDE 6 — ช่องว่าง 5 ประเภท ══════
    s = new(band_text="สไลด์ 6 / 12")
    text(s, 0.6, 0.55, 12, 0.6, "ทำไมจึงแก้ไม่ได้เสียที — ช่องว่าง 5 ประเภท",
         size=30, bold=True)
    gaps = [
        ("Design", "การออกแบบ", "พ.ร.บ.การศึกษาฯ ม.60(1) ใช้ถ้อยคำ “อย่างเท่าเทียมกัน”", "แก้ถ้อยคำ + สูตร WSF", False),
        ("Resource", "ทรัพยากร", "โรงเรียนเล็กได้งบตามหัว ไม่พอต้นทุนคงที่", "Fixed Cost Floor", False),
        ("Implementation", "การปฏิบัติ", "ม.39 กระจายอำนาจ — ไม่เกิดจริงตลอด 25 ปี", "กรอบเวลา + Earned Autonomy", True),
        ("Accountability", "ความรับผิด", "ไม่มีใครรับผิดเมื่อเด็กไม่ได้เรียนรู้", "Equity Ombudsman + รธน. ม.51", False),
        ("Evidence", "หลักฐาน", "ไม่เคยประเมินผลเชิงสาเหตุของทุนเสมอภาค", "RDD / DiD / Cluster RCT", False),
    ]
    rect(s, 0.6, 1.4, 12.1, 0.45, "navy")
    for t, x, w in [("ช่องว่าง", 0.85, 3.0), ("อาการในระบบไทย", 4.0, 5.0),
                    ("เครื่องมือที่ใช้ปิด", 9.2, 3.3)]:
        text(s, x, 1.45, w, 0.35, t, size=12, bold=True, color="white")
    for i, (en, thn, sym, fix, hot) in enumerate(gaps):
        y = 1.9 + i * 0.86
        rect(s, 0.6, y, 12.1, 0.86, "red" if hot else ("bg" if i % 2 == 0 else "white"))
        text(s, 0.85, y + 0.12, 3.0, 0.6, [
            {"t": en, "size": 14, "bold": True, "color": "white" if hot else "navy"},
            {"t": thn, "size": 10, "color": "white" if hot else "grey_l"},
        ], space=1)
        text(s, 4.0, y + 0.25, 5.0, 0.5, sym, size=12,
             color="white" if hot else "grey")
        text(s, 9.2, y + 0.25, 3.3, 0.5, fix, size=12,
             color="white" if hot else "grey")

    rect(s, 0.6, 6.3, 12.1, 0.75, "bg", "teal")
    text(s, 0.95, 6.42, 11.5, 0.55,
         "ไทยได้คะแนนสูงในสิ่งที่สร้างได้ด้วยความรู้ (ข้อมูล คัดกรอง ต้นแบบ) "
         "แต่ต่ำในสิ่งที่ต้องใช้อำนาจทางการเมือง (สูตรงบ อัตรากำลังครู) "
         "→ นี่ไม่ใช่ปัญหาทางเทคนิค แต่เป็นปัญหาเศรษฐศาสตร์การเมือง",
         size=13, color="navy")
    notes(s, """
[2 นาที] เน้นบรรทัด Implementation Gap (แถบสีแดง)

"ม.39 บอกให้กระจายอำนาจตั้งแต่ปี 2542 — ผ่านมา 25 ปียังไม่เกิด
นี่ไม่ใช่เพราะไม่มีใครรู้ แต่เพราะกฎหมายไม่ได้กำหนดว่า *เมื่อไหร่*
และ *ถ้าไม่ทำจะเกิดอะไรขึ้น*"

ประโยคปิดสไลด์: "ปัญหานี้ไม่ได้รอความรู้เพิ่มครับ ความรู้เรามีครบแล้ว
มันรอการตัดสินใจ — ซึ่งอยู่ในห้องนี้" [หยุด]

⚠️ อย่าพูด "เศรษฐศาสตร์การเมือง" ในเชิงกล่าวหาหน่วยงานใด
""")

    # ══════ SLIDE 7 — กฎหมาย ══════
    s = new(band_text="สไลด์ 7 / 12")
    text(s, 0.6, 0.55, 12, 0.6, "กฎหมายให้ทำได้แล้ว: ยุทธศาสตร์สองจังหวะ",
         size=30, bold=True)
    laws = [
        ("รัฐธรรมนูญ ม.27 วรรคท้าย", "ชัดเจน",
         "มาตรการช่วยผู้ด้อยโอกาส ไม่ถือเป็นการเลือกปฏิบัติ", "green"),
        ("รัฐธรรมนูญ ม.54 วรรคหก", "ชัดเจน",
         "รองรับมาตรการที่แตกต่างตามความจำเป็น", "green"),
        ("พ.ร.บ.การศึกษาฯ ม.60(1)", "ความเสี่ยงเชิงตีความ",
         "ถ้อยคำ “อย่างเท่าเทียมกัน” ถูกใช้อ้างเพื่อไม่ทำ", "amber"),
    ]
    for i, (name, st, desc, col) in enumerate(laws):
        y = 1.5 + i * 1.05
        rect(s, 0.6, y, 12.1, 0.9, "bg", "line")
        rect(s, 0.6, y, 0.09, 0.9, col)
        text(s, 0.95, y + 0.13, 4.3, 0.6, name, size=15, bold=True, color="navy")
        text(s, 5.4, y + 0.2, 2.5, 0.45, st, size=12, bold=True, color=col)
        text(s, 8.0, y + 0.2, 4.4, 0.45, desc, size=12, color="grey")

    rect(s, 0.6, 4.85, 5.9, 1.9, "navy", radius=True)
    text(s, 0.95, 5.05, 5.3, 1.5, [
        {"t": "จังหวะที่ ①", "size": 15, "bold": True, "color": "amber"},
        {"t": "เดินหน้าทันทีด้วยฐาน รธน. + ระเบียบ ก.ค.ศ. + Sandbox",
         "size": 13, "color": "white"},
        {"t": "ไม่ต้องรอแก้ พ.ร.บ.", "size": 13, "bold": True, "color": "white"},
    ], space=5)
    rect(s, 6.8, 4.85, 5.9, 1.9, "navy2", radius=True)
    text(s, 7.15, 5.05, 5.3, 1.5, [
        {"t": "จังหวะที่ ②", "size": 15, "bold": True, "color": "amber"},
        {"t": "ใช้หลักฐานจาก ① หนุนการแก้ ม.60", "size": 13, "color": "white"},
        {"t": "ให้ชัดเจนและถาวร", "size": 13, "bold": True, "color": "white"},
    ], space=5)
    notes(s, """
[2 นาที] สไลด์ปลดล็อกข้อกังวลของฝ่ายกฎหมาย — พูดล่วงหน้าก่อนถูกถาม

"คำถามแรกที่ทุกคนถามคือ ให้งบไม่เท่ากันเป็นการเลือกปฏิบัติหรือไม่ —
รัฐธรรมนูญ มาตรา 27 วรรคท้าย ตอบไว้ชัดเจนแล้วว่าไม่ใช่"

ความซื่อตรงที่ต้องแสดง:
"แต่ผมต้องเรียนตามตรงว่า ถ้อยคำ 'อย่างเท่าเทียมกัน' ใน ม.60 เป็นจุดที่
หน่วยปฏิบัติมักหยิบมาอ้างเพื่อไม่ทำ ผมจึงไม่เสนอให้เริ่มที่การแก้ พ.ร.บ."

💡 ถ้ามีนิติกรในห้อง — เชิญเขาแสดงความเห็นตรงนี้
""")

    # ══════ SLIDE 8 — ข้อเสนอหลัก ══════
    s = new(band_text="สไลด์ 8 / 12   ★ ข้อเสนอหลัก")
    rect(s, 0, 0.22, W, H - 0.22, "navy")
    text(s, 0.8, 0.75, 11.7, 0.45,
         "★  ข้อเสนอที่ให้ผลตอบแทนสูงสุดต่อความพยายาม",
         size=14, bold=True, color="amber")
    text(s, 0.8, 1.3, 11.7, 1.5, [
        {"t": "เปลี่ยนเกณฑ์อัตรากำลังครู", "size": 36, "bold": True, "color": "white"},
        {"t": "จาก “จำนวนนักเรียน”  →  “ห้องเรียน + ดัชนีความยากลำบาก”",
         "size": 22, "bold": True, "color": "amber"},
    ], space=6, line=1.2)

    facts = [("เครื่องมือ", "มติ / ระเบียบ ก.ค.ศ.", "white"),
             ("ต้องแก้ พ.ร.บ.", "ไม่ต้อง", "green"),
             ("ต้องขอเงินเพิ่ม", "ไม่ต้อง", "green"),
             ("ระยะเวลา", "ภายใน 1 ปีงบประมาณ", "white")]
    for i, (k, v, col) in enumerate(facts):
        x = 0.8 + i * 3.0
        rect(s, x, 3.1, 2.85, 1.0, "navy_d")
        text(s, x + 0.2, 3.2, 2.5, 0.35, k, size=11, color="grey_l")
        text(s, x + 0.2, 3.55, 2.5, 0.45, v, size=15, bold=True, color=col)

    rect(s, 0.8, 4.4, 11.7, 2.3, "navy_d")
    text(s, 1.1, 4.55, 11.1, 2.0, [
        {"t": "ตรรกะเชิงเลขคณิต", "size": 14, "bold": True, "color": "amber"},
        {"t": "โรงเรียนที่มีเด็กชั้นละ 8 คน ตั้งแต่ ป.1–ป.6 รวม 48 คน "
              "ได้ครูตามเกณฑ์รายหัวราว 2–3 คน แต่ต้องเปิดสอน 6 ชั้น",
         "size": 14, "color": "white"},
        {"t": "→ ครู 1 คน ต้องสอนควบ 2–3 ชั้นพร้อมกัน", "size": 14, "color": "white"},
        {"t": "ไม่ว่าครูคนนั้นจะเก่งเพียงใด ผลลัพธ์ก็จะออกมาแบบเดียวกัน "
              "เพราะนี่ไม่ใช่ปัญหาของคน แต่เป็นปัญหาของเลขคณิต",
         "size": 16, "bold": True, "color": "amber"},
    ], space=6)
    notes(s, """
[2.5 นาที] หัวใจของการขาย — ก้าวออกจากโพเดียมถ้าทำได้

"ท่านครับ ถ้าวันนี้ท่านให้ผมได้แค่ข้อเดียว ผมขอข้อนี้ครับ" [หยุด 3 วินาที]

อธิบายเลขคณิตช้า ๆ ใช้มือประกอบ — สมมติโรงเรียนชั้นละ 8 คน 6 ชั้น รวม 48 คน
[สบตาผู้มีอำนาจตัดสินใจมากที่สุด]
"ไม่ว่าครูคนนั้นจะเก่งแค่ไหน ทุ่มเทแค่ไหน ผลลัพธ์ก็จะออกมาแบบเดียวกันครับ
เพราะนี่ไม่ใช่ปัญหาของคน — นี่คือปัญหาของเลขคณิต"

🤝 ป้องกันแรงต้านจากองค์กรวิชาชีพครู:
"ผมเสนอให้เจรจาเป็นแพ็กเกจ — ค่าตอบแทนพื้นที่ยากลำบากสูงขึ้น 20–30%
และแต้มต่อวิทยฐานะ แลกกับการยอมรับกลไกการหมุนเวียน"
""")

    # ══════ SLIDE 9 — ข้อมูลจริงยืนยัน (กราฟ) ══════
    s = new(band_text="สไลด์ 9 / 12   📊 หลักฐานยืนยัน")
    text(s, 0.6, 0.55, 12, 0.6, "ข้อมูลจริงยืนยันข้อเสนอ", size=30, bold=True)
    text(s, 0.6, 1.22, 12, 0.4,
         f"เปรียบเทียบความต้องการครู: กฎเดิม (นักเรียน ÷ {a.ratio:.0f}) "
         f"vs กฎที่เสนอ (1 ครู / 1 ห้องเรียน)", size=13, color="grey")

    try:
        from pptx.chart.data import CategoryChartData
        from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
        cd = CategoryChartData()
        cd.categories = [u.short for u in a.units]
        cd.add_series("กฎเดิม (÷ %d)" % a.ratio,
                      tuple(round(u.rule_headcount) for u in a.units))
        cd.add_series("กฎที่เสนอ (1:ห้อง)",
                      tuple(round(u.rule_classroom) for u in a.units))
        gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED,
                                Inches(0.6), Inches(1.75),
                                Inches(7.3), Inches(4.0), cd)
        ch = gf.chart
        ch.has_legend = True
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM
        ch.legend.include_in_layout = False
        ch.plots[0].series[0].format.fill.solid()
        ch.plots[0].series[0].format.fill.fore_color.rgb = C["red"]
        ch.plots[0].series[1].format.fill.solid()
        ch.plots[0].series[1].format.fill.fore_color.rgb = C["green"]
    except Exception as e:
        print(f"⚠️  สร้างกราฟไม่สำเร็จ ({e}) — ข้ามกราฟในสไลด์ 9")

    kpis = [
        (th(a.core_deficit), "อัตรา", "ความขาดแคลนในระบบหลัก", "red"),
        (th(a.core_surplus), "อัตรา", f"ส่วนเกินใน {sec.short}", "green"),
        (th(a.core_net), "อัตรา", "ตัวเลขที่ระบบ “มองเห็น”", "navy"),
    ]
    for i, (num, unit, cap, col) in enumerate(kpis):
        y = 1.9 + i * 1.35
        rect(s, 8.2, y, 4.5, 1.15, "bg", "line")
        rect(s, 8.2, y, 0.08, 1.15, col)
        text(s, 8.5, y + 0.1, 4.0, 0.55, f"{num}  {unit}", size=22, bold=True, color=col)
        text(s, 8.5, y + 0.68, 4.0, 0.4, cap, size=12, color="grey")

    rect(s, 0.6, 6.0, 12.1, 0.95, "red")
    text(s, 0.95, 6.15, 11.5, 0.7, [
        {"t": "สิ่งที่ค่าเฉลี่ยรวมซ่อนไว้", "size": 14, "bold": True, "color": "white"},
        {"t": f"เราไม่ได้ขาดครู {th(a.core_net)} คน — เรากระจายผิดที่ {th(a.core_surplus)} คน "
              f"และขาดจริงอีก {th(a.core_net)} คน",
         "size": 15, "bold": True, "color": "white"},
    ], space=3)
    notes(s, f"""
[2 นาที] สไลด์หลักฐานที่หนักที่สุด

"ท่านครับ ตัวเลขที่รายงานบอกว่าเราขาดครู {th(a.core_net)} อัตรา —
แต่ข้อมูลของ สพฐ. เองปีการศึกษานี้บอกว่า
ระบบหลักขาด {th(a.core_deficit)} อัตรา และมีเกิน {th(a.core_surplus)} อัตราในเวลาเดียวกัน
(ถ้าใช้โมเดล 1:20 กับทุกประเภทรวมพิเศษ จะได้ขาด {th(a.total_deficit)} ซึ่งไม่ควรอ่านแบบเดียวกับ สพป.)"

"สิ่งที่ผมขอ ไม่ใช่อัตราเพิ่ม แต่คือการทบทวนว่าเรานับความต้องการด้วยฐานอะไรครับ"

🔀 ถ้าถูกถามว่า "โยกข้ามสังกัดทำได้จริงหรือ":
"เป็นประเด็นที่ถูกต้องครับ มีข้อจำกัดทางกฎหมายและใบอนุญาตวิชาชีพจริง
ผมจึงเสนอให้ใช้เฉพาะ *อัตราว่างจากการเกษียณ* ไม่ใช่การโยกย้ายตัวบุคคล"
""")

    # ══════ SLIDE 10 — Roadmap ══════
    s = new(band_text="สไลด์ 10 / 12")
    text(s, 0.6, 0.55, 12, 0.6, "แผนที่นำทาง 3 ระยะ", size=30, bold=True)
    text(s, 0.6, 1.25, 12, 0.4,
         "หลักการ: ① เริ่มจากสิ่งที่ทำได้โดยไม่ต้องแก้ พ.ร.บ. "
         "② สร้างหลักฐานก่อนขอกฎหมาย ③ ทำสองขาเสมอ — เงิน + คน",
         size=13, color="grey")
    phases = [
        ("ปีที่ 1", "green", "ทำได้ทันที", [
            "เปลี่ยนเกณฑ์อัตรากำลังครู (ก.ค.ศ.)",
            "ฝังการประเมินเชิงสาเหตุใน Sandbox",
            "ประกาศมาตรฐานขั้นต่ำ FSQL",
            "เปิด Equity Dashboard สาธารณะ",
            "เปิดใช้ระบบเตือนภัยล่วงหน้า (EWS)",
        ]),
        ("ปีที่ 2–3", "amber", "สร้างหลักฐาน", [
            "ขยาย Sandbox แบบสุ่มลำดับ",
            "Cost Function Analysis",
            "Benefit Incidence Analysis",
            "ประเมินย้อนหลังการควบรวม 10 ปี",
            "เจรจาแพ็กเกจกับองค์กรวิชาชีพครู",
        ]),
        ("ปีที่ 3–7", "red", "ปฏิรูปโครงสร้าง", [
            "แก้ ม.60 → Need-based Formula",
            "ตรากฎหมายรองรับ Zero Dropout",
            "แก้ ม.6 พ.ร.บ.กสศ.",
            "Scale-up Clause (comply-or-explain)",
            "ม.39 Earned Autonomy",
        ]),
    ]
    for i, (badge, col, sub, items) in enumerate(phases):
        x = 0.6 + i * 4.15
        rect(s, x, 1.9, 3.9, 4.7, "bg", "line")
        rect(s, x, 1.9, 3.9, 0.65, col)
        text(s, x + 0.25, 2.0, 3.4, 0.45, f"{badge}  ·  {sub}",
             size=15, bold=True, color="white")
        for j, it in enumerate(items):
            text(s, x + 0.25, 2.75 + j * 0.72, 3.45, 0.65,
                 f"▸  {it}", size=12, color="grey")
    notes(s, """
[2 นาที] อย่าอ่านทีละบรรทัด — ชี้ที่หลักการจัดลำดับแทน

"หลักการเรียงลำดับมี 3 ข้อครับ
① เริ่มจากสิ่งที่ทำได้โดยไม่ต้องแก้กฎหมาย
② สร้างหลักฐานก่อนขอกฎหมาย — เพราะผล Sandbox คือกระสุนที่เราจะใช้ผลักดัน ม.60
③ ทำสองขาเสมอ คือเงิน + คน เพราะปฏิรูปขาเดียวได้ผลน้อยมาก"

เน้น: "ทั้ง 5 รายการในปีที่ 1 ไม่มีข้อไหนต้องแก้ พ.ร.บ. และไม่มีข้อไหนต้องขอเงินก้อนใหม่"
""")

    # ══════ SLIDE 11 — ข้อโต้แย้ง + ภาษา ══════
    s = new(band_text="สไลด์ 11 / 12")
    text(s, 0.6, 0.55, 12, 0.6, "ข้อโต้แย้งที่จะเจอ · ภาษาที่ใช้สื่อสาร",
         size=30, bold=True)
    args = [
        ("“ต้องเพิ่มงบการศึกษา”", "งบอันดับ 3 ของประเทศแล้ว — เพิ่มเข้าสูตรผิดทิศ = ขยายช่องว่าง"),
        ("“ควบรวมโรงเรียนเล็กคือคำตอบ”", "ต้นทุนแฝงยังไม่เคยถูกวัด — ต้องวิจัยก่อนขยายนโยบาย"),
        ("“ครูไม่พอ ต้องบรรจุเพิ่ม”", "ปัญหาคือการกระจาย ไม่ใช่จำนวน"),
        ("“มี กสศ. แล้วเพียงพอ”", "กสศ. = 2–3% และอาจสร้าง Shifting the Burden"),
        ("“ให้งบไม่เท่ากัน = เลือกปฏิบัติ”", "รธน. ม.27 วรรคท้าย ระบุชัดว่าไม่ใช่"),
        ("“เด็กลดแล้ว ควรลดงบ”", "เด็กลด = โอกาสยกคุณภาพต่อหัว — ตัดงบ = เสียโอกาสถาวร"),
    ]
    for i, (q, ans) in enumerate(args):
        y = 1.4 + i * 0.62
        rect(s, 0.6, y, 7.5, 0.55, "bg" if i % 2 == 0 else "white", "line")
        text(s, 0.8, y + 0.04, 3.3, 0.45, q, size=11, bold=True, color="red")
        text(s, 4.2, y + 0.04, 3.75, 0.45, ans, size=10.5, color="grey")

    rect(s, 8.4, 1.4, 4.3, 3.85, "navy", radius=True)
    text(s, 8.7, 1.55, 3.7, 0.4, "ภาษาที่ใช้สื่อสาร", size=15, bold=True, color="amber")
    lang = [("✅ ควรพูด", "“โรงเรียนที่ครูสอนควบ 3 ชั้น”", "green"),
            ("❌ ควรเลี่ยง", "“ความเหลื่อมล้ำเชิงโครงสร้าง”", "red"),
            ("✅ ควรพูด", "“ไม่มีโรงเรียนไหนได้น้อยลง”", "green"),
            ("❌ ควรเลี่ยง", "“โยกงบจากโรงเรียนใหญ่”", "red"),
            ("✅ ควรพูด", "“เด็กลด งบเท่าเดิม = คุณภาพต่อหัวเพิ่ม”", "green")]
    for i, (tag, txt, col) in enumerate(lang):
        y = 2.05 + i * 0.62
        text(s, 8.7, y, 3.7, 0.55, [
            {"t": tag, "size": 9.5, "bold": True, "color": col},
            {"t": txt, "size": 11, "color": "white"},
        ], space=1)

    rect(s, 0.6, 5.4, 12.1, 1.5, "bg", "line")
    text(s, 0.95, 5.55, 11.5, 1.2, [
        {"t": "⚖️  ข้อวิพากษ์ที่เรายอมรับว่ายังไม่มีคำตอบที่ดีพอ",
         "size": 14, "bold": True, "color": "navy"},
        {"t": "① Fixed Cost Floor อาจสร้างแรงจูงใจให้คงโรงเรียนที่ไม่ควรคงไว้ → ต้องผูกกับเงื่อนไขระยะทาง",
         "size": 11.5, "color": "grey"},
        {"t": "② เงินที่เพิ่มในโรงเรียนที่ศักยภาพบริหารต่ำอาจไม่เกิดผล → ต้องจับคู่กับการพัฒนาผู้บริหาร",
         "size": 11.5, "color": "grey"},
        {"t": "③ สูตรที่แม่นยำเกินไปอาจอธิบายไม่ได้ → trade-off ระหว่างความแม่นยำ ↔ ความชอบธรรม",
         "size": 11.5, "color": "grey"},
    ], space=3)
    notes(s, """
[2 นาที] สไลด์นี้ทำหน้าที่ 2 อย่าง:
① เตรียมคำตอบให้ผู้บริหารใช้เองเวลาไปตอบสื่อ
② แสดงว่าเราคิดรอบด้าน

ให้เวลากับกล่องล่างมากเป็นพิเศษ:
"ผมขอใช้เวลาสักครู่กับสิ่งที่เรา *ยังตอบไม่ได้* นะครับ"
→ การยอมรับข้อจำกัดต่อหน้าผู้บริหารระดับสูงสร้างความน่าเชื่อถือ
   มากกว่าการอ้างว่าข้อเสนอสมบูรณ์แบบ

เรื่องภาษา: "การปฏิรูปนี้จะแพ้หรือชนะที่ภาษา ไม่ใช่ที่ตัวเลข"
เน้น hold-harmless: "เราไม่ได้เอาเงินจากโรงเรียนใหญ่ไปให้โรงเรียนเล็ก
แต่ใช้งบส่วนเพิ่มที่เกิดจากจำนวนเด็กที่ลดลง"
""")

    # ══════ SLIDE 12 — 3 มติ ══════
    s = new(band_text="สไลด์ 12 / 12")
    text(s, 0.6, 0.55, 12, 0.6, "สิ่งที่ขออนุมัติวันนี้", size=30, bold=True)
    asks = [
        ("1", "ตั้งคณะทำงานทบทวนเกณฑ์อัตรากำลังครู",
         "→ ห้องเรียน + ดัชนีความยากลำบาก", "ก.ค.ศ. + สพฐ.", "ไม่ต้อง", "ไม่ต้อง"),
        ("2", "ฝังการประเมินเชิงสาเหตุใน WSF Sandbox",
         "ที่กำลังดำเนินการอยู่", "กสศ. + ศธ.", "ไม่ต้อง", "ไม่ต้อง"),
        ("3", "อนุมัติงบวิจัย Benefit Incidence Analysis",
         "ของงบการศึกษาทั้งระบบ", "ศธ. + สงป.", "ไม่ต้อง", "งบวิจัยขนาดเล็ก"),
    ]
    for i, (no, title, sub, owner, law, money) in enumerate(asks):
        y = 1.45 + i * 1.25
        rect(s, 0.6, y, 12.1, 1.1, "bg", "line")
        rect(s, 0.6, y, 0.7, 1.1, "navy")
        text(s, 0.6, y + 0.32, 0.7, 0.5, no, size=24, bold=True,
             color="white", align=PP_ALIGN.CENTER)
        text(s, 1.55, y + 0.15, 6.0, 0.85, [
            {"t": title, "size": 15, "bold": True, "color": "navy"},
            {"t": sub, "size": 11.5, "color": "grey"},
        ], space=2)
        text(s, 7.8, y + 0.2, 1.9, 0.7, [
            {"t": "เจ้าภาพ", "size": 9.5, "color": "grey_l"},
            {"t": owner, "size": 12, "bold": True, "color": "grey"},
        ], space=1)
        text(s, 9.9, y + 0.2, 1.3, 0.7, [
            {"t": "แก้กฎหมาย", "size": 9.5, "color": "grey_l"},
            {"t": law, "size": 12, "bold": True, "color": "green"},
        ], space=1)
        text(s, 11.3, y + 0.2, 1.3, 0.7, [
            {"t": "ใช้เงินเพิ่ม", "size": 9.5, "color": "grey_l"},
            {"t": money, "size": 12, "bold": True,
             "color": "green" if money == "ไม่ต้อง" else "amber"},
        ], space=1)

    rect(s, 0.6, 5.3, 12.1, 1.55, "navy")
    text(s, 0.95, 5.5, 11.5, 1.2, [
        {"t": "ทุกปีที่เราไม่แก้สูตร ระบบจะผลิตซ้ำความเหลื่อมล้ำอีกหนึ่งรุ่นโดยอัตโนมัติ",
         "size": 19, "bold": True, "color": "white"},
        {"t": "— ไม่ใช่เพราะใครตั้งใจ แต่เพราะสูตรถูกเขียนไว้อย่างนั้น",
         "size": 15, "color": "white"},
        {"t": "และสูตร คือสิ่งที่แก้ได้ด้วยมติเดียว",
         "size": 17, "bold": True, "color": "amber"},
    ], space=5)
    notes(s, """
[1.5 นาที] การปิด — อย่าสรุปซ้ำทั้งหมด ใช้ 3 ประโยคนี้เท่านั้น

① "ผมขอ 3 มติครับ และไม่มีข้อไหนต้องแก้กฎหมาย"
② "ข้อที่ 1 และ 2 ไม่ต้องใช้งบเพิ่มแม้แต่บาทเดียว"
③ อ่านกล่องปิดท้ายช้า ๆ แล้วหยุด 3 วินาที ก่อนพูด "ขอบคุณครับ"

⚠️ อย่าเปิด Q&A ด้วย "มีคำถามไหมครับ"
ให้ใช้: "ผมขอฟังความเห็นของท่าน โดยเฉพาะเรื่องความเป็นไปได้ของมติข้อที่ 1 ครับ"
→ ชี้นำวงสนทนาไปยังข้อเสนอที่เราต้องการมากที่สุด
""")

    # ══════ สไลด์สำรอง B1–B6 ══════
    backups = [
        ("B1", "Theory of Change เต็มรูปแบบ",
         ["Inputs → Activities → Outputs → Outcomes → Impact",
          "สมมติฐาน A1: เงินเพิ่มจะถูกใช้อย่างมีประสิทธิผลที่ระดับโรงเรียน",
          "สมมติฐาน A4: ครูครบชั้น → คุณภาพการสอนดีขึ้น (ยังไม่ทดสอบ)"],
         "ใช้เมื่อถูกถามว่า 'ตรรกะจากงบไปสู่ผลลัพธ์คืออะไร'"),
        ("B2", "โครงสร้างสูตร WSF 4 ชั้น",
         ["① Fixed Cost Floor — เงินก้อนคงที่ต่อโรงเรียน",
          "② น้ำหนักรายนักเรียน — ยากจน +0.50 · พิการ +0.80–2.50 · ภาษา +0.30",
          "③ ตัวคูณบริบท — ความห่างไกล ×1.10–1.40",
          "④ แรงจูงใจเชื่อมผลลัพธ์ — ไม่เกิน 5% ของงบรวม"],
         "ใช้เมื่อถูกถามว่า 'สูตรหน้าตาเป็นอย่างไร'"),
        ("B3", "บทเรียนต่างประเทศ",
         ["ออสเตรเลีย — Gonski Review และ needs-based funding",
          "อังกฤษ — Pupil Premium",
          "บราซิล — FUNDEB กลไกปรับดุลระดับรัฐ",
          "เนเธอร์แลนด์ — weighted student funding ที่ใช้มายาวนานที่สุด"],
         "ใช้เมื่อถูกถามว่า 'ประเทศอื่นทำอย่างไร'"),
        ("B4", "ทะเบียนความเสี่ยง R1–R7",
         ["R1 เปลี่ยนรัฐบาล → ฝังในกฎหมายและสูตร ไม่ใช่โครงการ",
          "R2 ข้อมูล PMT ถูก manipulate → ตรวจสอบสุ่ม + เชื่อมข้อมูลข้ามหน่วยงาน",
          "R3 โรงเรียนได้เงินแต่ใช้ไม่เป็น → earned autonomy แบบไล่ระดับ",
          "R6 เด็กไร้สัญชาติหลุดจากระบบข้อมูล → ช่องทางลงทะเบียนพิเศษ"],
         "ใช้เมื่อถูกถามว่า 'ถ้าล้มเหลวจะเป็นอย่างไร'"),
        ("B5", "Stakeholder Map",
         ["สำนักงบประมาณ — อำนาจสูงมาก · กังวลภาระการคลัง",
          "สพฐ./ส่วนกลาง — อำนาจสูงมาก · อาจต้าน (สูญเสียดุลพินิจ)",
          "ครูโรงเรียนขนาดเล็ก — อำนาจต่ำ แต่จำนวนมาก · สนับสนุนแรง",
          "ส.ส. พื้นที่ชนบท — พันธมิตรที่ถูกมองข้ามมากที่สุด"],
         "ใช้เมื่อถูกถามว่า 'ใครจะคัดค้าน'"),
        ("B6", "วาระวิจัย 5 ลำดับแรก",
         ["① ทุนเสมอภาคมีผลต่อการเรียนรู้หรือเฉพาะการมาเรียน (RDD)",
          "② ทรัพยากรกระจายแบบ progressive หรือ regressive (BIA)",
          "③ เด็กที่กลับเข้าระบบคงอยู่ 12/24 เดือนหรือไม่",
          "④ Cost Function Analysis เพื่อกำหนดค่าน้ำหนักจริง",
          "⑤ ประเมินย้อนหลังการควบรวมโรงเรียน (Matched DiD)"],
         "ใช้เมื่อถูกถามว่า 'ต้องวิจัยอะไรบ้าง'"),
    ]
    for code, title, items, hint in backups:
        s = new(band_text=f"สไลด์สำรอง {code} — ห้ามนำเสนอเว้นแต่ถูกถาม")
        text(s, 0.6, 0.6, 12, 0.6, f"{code}  ·  {title}", size=27, bold=True)
        for j, it in enumerate(items):
            y = 1.6 + j * 0.85
            rect(s, 0.6, y, 12.1, 0.7, "bg", "line")
            text(s, 0.9, y + 0.15, 11.5, 0.45, f"▸  {it}", size=14, color="grey")
        notes(s, f"สไลด์สำรอง — {hint}\n\n⚠️ ห้ามนำเสนอเว้นแต่ถูกถาม")

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  PART B — PDF (reportlab)
# ══════════════════════════════════════════════════════════════════════════════
THAI_COMBINING = set("\u0e31\u0e34\u0e35\u0e36\u0e37\u0e38\u0e39\u0e3a"
                     "\u0e47\u0e48\u0e49\u0e4a\u0e4b\u0e4c\u0e4d\u0e4e")
THAI_LEAD_VOWEL = set("\u0e40\u0e41\u0e42\u0e43\u0e44")


def _tokenizer():
    """ใช้ pythainlp ถ้ามี — ถ้าไม่มีใช้การตัดทีละอักขระแบบมีเงื่อนไข"""
    try:
        from pythainlp import word_tokenize
        return lambda s: word_tokenize(s, engine="newmm")
    except Exception:
        return None


def _can_break(text: str, i: int) -> bool:
    """ตรวจว่าขึ้นบรรทัดใหม่ก่อนตำแหน่ง i ได้หรือไม่ (กฎการตัดคำไทย)"""
    if i <= 0 or i >= len(text):
        return False
    if text[i] in THAI_COMBINING:       # ห้ามแยกสระ/วรรณยุกต์ออกจากพยัญชนะ
        return False
    if text[i - 1] in THAI_LEAD_VOWEL:  # ห้ามตัดหลังสระหน้า เ แ โ ใ ไ
        return False
    return True


class ThaiPDF:
    """ตัวช่วยวาด PDF ภาษาไทย — จัดการตัดบรรทัดเองเพื่อความแม่นยำ"""

    def __init__(self, path: Path, fonts: dict):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        self.W, self.H = A4
        self.c = canvas.Canvas(str(path), pagesize=A4)
        self.c.setTitle("ความเสมอภาคทางการศึกษาไทย")
        self.f = fonts
        self.M = 42  # ระยะขอบ

    # ---------- primitives ----------
    def rgb(self, key, alpha=None):
        from reportlab.lib.colors import Color
        r, g, b = PALETTE[key]
        return Color(r / 255, g / 255, b / 255, alpha if alpha is not None else 1)

    def rect(self, x, y, w, h, fill=None, stroke=None, lw=0.7, radius=0):
        if fill:
            self.c.setFillColor(self.rgb(fill))
        if stroke:
            self.c.setStrokeColor(self.rgb(stroke))
            self.c.setLineWidth(lw)
        if radius:
            self.c.roundRect(x, y, w, h, radius, stroke=1 if stroke else 0,
                             fill=1 if fill else 0)
        else:
            self.c.rect(x, y, w, h, stroke=1 if stroke else 0, fill=1 if fill else 0)

    def wrap(self, text, font, size, max_w):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        tok = _tokenizer()
        lines, cur = [], ""
        atoms = []
        for chunk in text.split(" "):
            if tok and any("\u0e00" <= ch <= "\u0e7f" for ch in chunk):
                atoms.extend(tok(chunk))
            else:
                atoms.append(chunk)
            atoms.append(" ")
        if atoms and atoms[-1] == " ":
            atoms.pop()

        for atom in atoms:
            trial = cur + atom
            if stringWidth(trial, font, size) <= max_w:
                cur = trial
                continue
            if cur.strip():
                lines.append(cur.rstrip())
                cur = atom.lstrip() if atom != " " else ""
            else:
                cur = atom
            # ถ้า atom เดียวยังยาวเกิน → ตัดทีละอักขระตามกฎไทย
            while stringWidth(cur, font, size) > max_w:
                cut = len(cur)
                while cut > 1 and (stringWidth(cur[:cut], font, size) > max_w
                                   or not _can_break(cur, cut)):
                    cut -= 1
                if cut <= 1:
                    break
                lines.append(cur[:cut])
                cur = cur[cut:]
        if cur.strip():
            lines.append(cur.rstrip())
        return lines or [""]

    def text(self, x, y, txt, *, font="r", size=10, color="grey",
             max_w=None, leading=None, align="l"):
        fname = self.f[font]
        lead = leading or size * 1.55
        self.c.setFont(fname, size)
        self.c.setFillColor(self.rgb(color))
        lines = self.wrap(txt, fname, size, max_w) if max_w else [txt]
        for ln in lines:
            if align == "c":
                self.c.drawCentredString(x, y, ln)
            elif align == "r":
                self.c.drawRightString(x, y, ln)
            else:
                self.c.drawString(x, y, ln)
            y -= lead
        return y

    def hr(self, y, color="line", inset=0):
        self.c.setStrokeColor(self.rgb(color))
        self.c.setLineWidth(0.8)
        self.c.line(self.M + inset, y, self.W - self.M - inset, y)

    def header_band(self, title, sub=""):
        self.rect(0, self.H - 74, self.W, 74, "navy")
        self.rect(0, self.H - 74, 6, 74, "amber")
        self.text(self.M, self.H - 38, title, font="b", size=15, color="white")
        if sub:
            self.text(self.M, self.H - 56, sub, size=9, color="grey_l")

    def footer(self, page, total, src):
        self.hr(52)
        self.text(self.M, 38, src, size=7.5, color="grey_l",
                  max_w=self.W - 2 * self.M - 60)
        self.text(self.W - self.M, 38, f"หน้า {page} / {total}",
                  size=8, color="grey_l", align="r")

    def bar(self, x, y, w, h, pct, label, color):
        self.rect(x, y, w, h, "line")
        self.rect(x, y, w * pct, h, color)
        self.text(x + 8, y + h / 2 - 3.5, label, font="b", size=9, color="white")

    def page_break(self):
        self.c.showPage()

    def save(self):
        self.c.save()


def _find_fonts(font_dir: Path | None) -> dict:
    """ค้นหาไฟล์ฟอนต์ไทยและลงทะเบียนกับ reportlab"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    cands = {
        "r": ["Sarabun-Regular.ttf", "Sarabun.ttf", "NotoSansThai-Regular.ttf",
              "THSarabunNew.ttf", "Kanit-Regular.ttf", "tahoma.ttf"],
        "b": ["Sarabun-Bold.ttf", "NotoSansThai-Bold.ttf",
              "THSarabunNew Bold.ttf", "Kanit-Bold.ttf", "tahomabd.ttf"],
        "sb": ["Sarabun-SemiBold.ttf", "NotoSansThai-SemiBold.ttf",
               "Kanit-Medium.ttf"],
    }
    dirs = ([font_dir] if font_dir else []) + FONT_DIRS
    found = {}
    for key, names in cands.items():
        for d in dirs:
            if not d or not d.exists():
                continue
            for nm in names:
                p = d / nm
                if p.exists():
                    fid = f"Thai-{key}"
                    pdfmetrics.registerFont(TTFont(fid, str(p)))
                    found[key] = fid
                    break
            if key in found:
                break

    if "r" not in found:
        sys.exit(
            "❌ ไม่พบฟอนต์ไทยสำหรับสร้าง PDF\n\n"
            "   วิธีแก้:\n"
            "   1) ดาวน์โหลด Sarabun → https://fonts.google.com/specimen/Sarabun\n"
            "   2) แตกไฟล์แล้ววาง Sarabun-Regular.ttf และ Sarabun-Bold.ttf\n"
            f"      ไว้ที่  {FONT_DIRS[0]}\n"
            "   3) หรือระบุโฟลเดอร์เอง:  --font-dir /path/to/fonts\n"
        )
    found.setdefault("b", found["r"])
    found.setdefault("sb", found["b"])
    print(f"🔤 ใช้ฟอนต์: {found['r']} / {found['b']}")
    return found


# ---------- Executive Brief (5 หน้า) ----------
def build_brief(a: Analysis, out: Path, font_dir: Path | None) -> Path:
    fonts = _find_fonts(font_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    p = ThaiPDF(out, fonts)
    W, M = p.W, p.M
    CW = W - 2 * M
    src = (f"{a.meta.get('source')} · ปีการศึกษา {a.meta.get('academic_year')} · "
           f"สร้างเมื่อ {datetime.now():%d/%m/%Y %H:%M}")
    prim, sec = a.primary, a.secondary
    TOTAL = 5

    # ═══ หน้า 1 ═══
    p.header_band("บทสรุปผู้บริหาร: การปฏิรูปการจัดสรรทรัพยากรทางการศึกษา",
                  "สำหรับผู้บริหารระดับนโยบาย · เวลาอ่านประมาณ 12 นาที")
    y = p.H - 110
    p.rect(M, y - 46, CW, 46, "bg")
    p.rect(M, y - 46, 5, 46, "amber")
    p.text(M + 16, y - 20, "ประเทศไทยไม่ได้ขาดเงิน ไม่ได้ขาดกฎหมาย และไม่ได้ขาดข้อมูล",
           font="b", size=13, color="navy", max_w=CW - 32)
    p.text(M + 16, y - 36, "— แต่ขาดสูตรที่จะส่งทรัพยากรไปยังจุดที่จำเป็นที่สุด",
           font="b", size=12, color="red", max_w=CW - 32)
    y -= 72

    p.text(M, y, "ข้อค้นพบแกนกลาง 3 ข้อ", font="b", size=13, color="navy")
    y -= 24
    for i, (h, b) in enumerate([
        ("ปัญหาย้ายที่แล้ว แต่เครื่องมือยังไม่ย้ายตาม",
         "ไทยแก้ปัญหา “การเข้าถึง” ได้เกือบหมดแล้ว แต่ยังใช้เครื่องมือของยุคนั้น "
         "มาแก้ปัญหาที่ปัจจุบันอยู่ที่ “คุณภาพการเรียนรู้” — เรียกว่า problem–instrument mismatch"),
        ("ช่องว่าง 97 : 3 คือหัวใจของปัญหา",
         "กลไกที่ออกแบบตามหลักความเสมอภาค (กสศ. + โครงการเฉพาะ) มีขนาดเพียง 2–3% "
         "ขณะที่ระบบหลัก 97–98% ยังจัดสรรแบบเท่ากันทุกหัว"),
        ("หน้าต่างโอกาสกำลังเปิด และจะปิดใน 3–5 ปี",
         "เด็กเกิดน้อยลงเร็ว หากคงกรอบงบเดิมไว้ งบต่อหัวจะเพิ่มเองโดยไม่ต้องขอเงินใหม่ "
         "— แต่หากปล่อยให้งบถูกตัดตามจำนวนเด็ก โอกาสนี้จะหายไปถาวร"),
    ], 1):
        p.rect(M, y - 52, 22, 22, "navy")
        p.text(M + 11, y - 45, str(i), font="b", size=11, color="white", align="c")
        p.text(M + 32, y - 38, h, font="b", size=11, color="navy", max_w=CW - 40)
        p.text(M + 32, y - 53, b, size=9.5, color="grey", max_w=CW - 40, leading=13)
        y -= 82

    y -= 4
    p.text(M, y, "สัดส่วนการจัดสรรทรัพยากร", font="b", size=12, color="navy")
    y -= 26
    p.bar(M, y, CW, 26, 0.97, "เงินอุดหนุนรายหัว + อัตรากำลังครู  ≈ 97–98%  (Equality)", "red")
    y -= 34
    p.bar(M, y, CW, 26, 0.03, "", "green")
    p.text(M + CW * 0.03 + 10, y + 9, "กสศ. + โครงการเฉพาะ  ≈ 2–3%  (Equity)",
           font="b", size=9, color="green")
    y -= 42
    p.rect(M, y - 26, CW, 26, "bg")
    p.text(M + 12, y - 17,
           "ไม่ว่าจะทำ 3% ให้ดีเพียงใด ก็ไม่มีทางหักล้างแรงของ 97% ได้",
           font="b", size=11, color="navy")
    p.footer(1, TOTAL, src)
    p.page_break()

    # ═══ หน้า 2 ═══
    p.header_band("การวินิจฉัย: ปัญหาอยู่ตรงไหนกันแน่", "ความเหลื่อมล้ำ 4 ชั้นที่ซ้อนกัน")
    y = p.H - 110
    p.rect(M, y - 20, CW, 20, "navy")
    for t, dx, w, al in [("มิติ", 10, 150, "l"), ("สถานะ", 175, 90, "l"),
                         ("คำวินิจฉัย", 280, CW - 290, "l")]:
        p.text(M + dx, y - 13, t, font="b", size=9, color="white")
    y -= 20
    for i, (m, st, v, col) in enumerate([
        ("1. การเข้าถึง (Access)", "ดีแล้ว", "เหลือเพียงกลุ่มตกค้าง", "green"),
        ("2. การคงอยู่ (Retention)", "วิกฤต", "หน้าผาที่รอยต่อ ม.3 → ม.4", "red"),
        ("3. การเรียนรู้ (Learning)", "วิกฤตที่สุด", "จุดที่ต้องทุ่มทรัพยากร", "red"),
        ("4. การเปลี่ยนผ่าน (Transition)", "อ่อน", "การเลื่อนชั้นทางสังคมต่ำ", "amber"),
    ]):
        if i % 2 == 0:
            p.rect(M, y - 22, CW, 22, "bg")
        p.text(M + 10, y - 15, m, font="b", size=9.5, color="navy")
        p.text(M + 175, y - 15, st, font="b", size=9.5, color=col)
        p.text(M + 280, y - 15, v, size=9.5, color="grey")
        y -= 22

    y -= 22
    p.text(M, y, "ตัวเลขสำคัญจากข้อมูล สพฐ.", font="b", size=12, color="navy")
    y -= 22
    stats = [
        (th(a.total_students), "นักเรียนทั้งสังกัด (คน)"),
        (th(a.total_rooms), "ห้องเรียนทั้งหมด (ห้อง)"),
        (f"{prim.spr:.1f}", f"{prim.short} (คน/ห้อง)"),
        (f"{sec.spr:.1f}", f"{sec.short} (คน/ห้อง)"),
    ]
    bw = (CW - 3 * 8) / 4
    for i, (n, c) in enumerate(stats):
        x = M + i * (bw + 8)
        p.rect(x, y - 52, bw, 52, "bg", "line")
        p.text(x + 10, y - 24, n, font="b", size=15, color="navy")
        p.text(x + 10, y - 42, c, size=8, color="grey", max_w=bw - 20)
    y -= 74

    p.text(M, y, "กับดักโรงเรียนขนาดเล็ก — วงจรที่หมุนเองได้",
           font="b", size=12, color="navy")
    y -= 22
    for i, stp in enumerate([
        "จำนวนเด็กในโรงเรียนลดลง",
        "เกณฑ์อัตรากำลังอิง “จำนวนนักเรียน” → ได้ครูน้อยลง",
        "ครูควบชั้น / สอนไม่ตรงวิชาเอก",
        "คุณภาพการเรียนการสอนลดลง",
        "ผู้ปกครองที่มีทางเลือกย้ายลูกออก",
        "↻  จำนวนเด็กลดลงอีก — วนกลับสู่ขั้นที่ 1",
    ]):
        last = i == 5
        p.rect(M, y - 21, CW, 21, "red" if last else "bg", "line")
        p.rect(M, y - 21, 20, 21, "red" if last else "navy")
        p.text(M + 10, y - 15, "↻" if last else str(i + 1), font="b",
               size=9, color="white", align="c")
        p.text(M + 30, y - 15, stp, font="b" if last else "r", size=9.5,
               color="white" if last else "grey")
        y -= 24

    y -= 8
    p.rect(M, y - 40, CW, 40, "bg", "amber")
    p.text(M + 12, y - 16, "การกลับกรอบคำถาม", font="b", size=10, color="navy")
    p.text(M + 12, y - 31,
           "คำถามที่ถูกต้องไม่ใช่ “ควรควบรวมโรงเรียนเล็กหรือไม่” แต่คือ "
           "“ทำไมสูตรจัดสรรจึงลงโทษโรงเรียนตามขนาด แทนที่จะจัดสรรตามความจำเป็น”",
           size=9, color="grey", max_w=CW - 24)
    p.footer(2, TOTAL, src)
    p.page_break()

    # ═══ หน้า 3 — หลักฐานเชิงตัวเลข ═══
    p.header_band("หลักฐาน: ช่องว่างอัตรากำลังครูที่ถูกซ่อนไว้",
                  f"คำนวณที่เกณฑ์อ้างอิง 1 : {a.ratio:.0f}")
    y = p.H - 110
    p.rect(M, y - 20, CW, 20, "navy")
    heads = [("หน่วย", 10, "l"), ("นักเรียน", 200, "r"), ("ห้องเรียน", 275, "r"),
             ("นร./ห้อง", 340, "r"), ("กฎเดิม", 420, "r"), ("กฎใหม่", 480, "r"),
             ("ส่วนต่าง", CW - 10, "r")]
    for t, dx, al in heads:
        p.text(M + dx, y - 13, t, font="b", size=8.5, color="white", align=al)
    y -= 20
    for i, u in enumerate(a.units):
        if i % 2 == 0:
            p.rect(M, y - 20, CW, 20, "bg")
        col = "red" if u.gap > 0 else "green"
        p.text(M + 10, y - 14, u.name, font="b", size=8.5, color="navy")
        p.text(M + 200, y - 14, th(u.students), size=8.5, color="grey", align="r")
        p.text(M + 275, y - 14, th(u.rooms), size=8.5, color="grey", align="r")
        p.text(M + 340, y - 14, f"{u.spr:.1f}", font="b", size=8.5,
               color="red" if u.spr < a.ratio else "green", align="r")
        p.text(M + 420, y - 14, th(u.rule_headcount), size=8.5, color="grey", align="r")
        p.text(M + 480, y - 14, th(u.rule_classroom), size=8.5, color="grey", align="r")
        p.text(M + CW - 10, y - 14,
               f"{'+' if u.gap > 0 else ''}{th(u.gap)}", font="b", size=8.5,
               color=col, align="r")
        y -= 20

    p.rect(M, y - 22, CW, 22, "navy")
    p.text(M + 10, y - 15, "รวมทั้งสิ้น", font="b", size=9, color="white")
    p.text(M + 200, y - 15, th(a.total_students), font="b", size=9,
           color="white", align="r")
    p.text(M + 275, y - 15, th(a.total_rooms), font="b", size=9,
           color="white", align="r")
    p.text(M + 340, y - 15, f"{a.total_spr:.1f}", font="b", size=9,
           color="amber", align="r")
    p.text(M + CW - 10, y - 15, f"+{th(a.net_gap)}", font="b", size=9,
           color="amber", align="r")
    y -= 48

    cards = [(th(a.core_deficit), "ความขาดแคลนในระบบหลัก", "red"),
             (th(a.core_surplus), f"ส่วนเกินใน {sec.short}", "green"),
             (th(a.core_net), "ตัวเลขที่ระบบมองเห็น", "navy")]
    cw2 = (CW - 2 * 10) / 3
    for i, (n, c, col) in enumerate(cards):
        x = M + i * (cw2 + 10)
        p.rect(x, y - 58, cw2, 58, "bg", "line")
        p.rect(x, y - 58, 4, 58, col)
        p.text(x + 14, y - 26, n, font="b", size=18, color=col)
        p.text(x + 14, y - 44, "อัตรา", size=8, color="grey_l")
        p.text(x + 14, y - 54, c, font="b", size=8.5, color="grey", max_w=cw2 - 24)
    y -= 78

    p.rect(M, y - 56, CW, 56, "red")
    p.text(M + 14, y - 20, "สิ่งที่ค่าเฉลี่ยรวมซ่อนไว้", font="b", size=11, color="white")
    p.text(M + 14, y - 36,
           f"ระบบหลักขาดสุทธิ {th(a.core_net)} อัตรา — ขาด {th(a.core_deficit)} ที่ สพป. "
           f"ถูกกลบด้วยส่วนเกิน {th(a.core_surplus)} ที่ สพม. "
           f"(รวมพิเศษตามโมเดล 1:20 จะได้ขาด {th(a.total_deficit)})",
           size=9.5, color="white", max_w=CW - 28)
    p.text(M + 14, y - 51,
           "ปัญหาของเราคือ “การกระจาย” ไม่ใช่ “จำนวน”",
           font="b", size=11, color="amber")
    y -= 74

    r = a.realloc(1.0, 8)
    p.text(M, y, "การจำลองจัดสรรใหม่ (โยกส่วนเกิน 100% ภายใน 8 ปี)",
           font="b", size=11, color="navy")
    y -= 20
    p.text(M, y,
           f"โยกได้ {th(r['moved'])} อัตรา (เฉลี่ยปีละ {th(r['per_year'])} อัตรา) "
           f"→ ปิดช่องว่างของ {prim.short} ได้ {r['closed_pct']:.0f}% "
           f"เหลือขาดอีก {th(r['remain'])} อัตรา",
           size=9.5, color="grey", max_w=CW, leading=14)
    p.footer(3, TOTAL, src)
    p.page_break()

    # ═══ หน้า 4 — ข้อเสนอ ═══
    p.header_band("ข้อเสนอและแผนที่นำทาง", "หลักการ: เริ่มจากสิ่งที่ทำได้โดยไม่ต้องแก้ พ.ร.บ.")
    y = p.H - 110
    p.rect(M, y - 88, CW, 88, "navy")
    p.rect(M, y - 88, 5, 88, "amber")
    p.text(M + 16, y - 22, "★  ข้อเสนอที่ให้ผลตอบแทนสูงสุดต่อความพยายาม",
           font="b", size=9.5, color="amber")
    p.text(M + 16, y - 42, "เปลี่ยนเกณฑ์อัตรากำลังครู", font="b", size=15, color="white")
    p.text(M + 16, y - 60, "จาก “จำนวนนักเรียน” → “ห้องเรียน + ดัชนีความยากลำบาก”",
           font="b", size=12, color="amber")
    p.text(M + 16, y - 79,
           "เครื่องมือ: มติ ก.ค.ศ.  ·  ต้องแก้ พ.ร.บ.: ไม่ต้อง  ·  "
           "ต้องขอเงินเพิ่ม: ไม่ต้อง  ·  ระยะเวลา: ภายใน 1 ปีงบประมาณ",
           size=9, color="white", max_w=CW - 32)
    y -= 108

    phases = [
        ("ปีที่ 1 — ทำได้ทันที", "green", [
            "เปลี่ยนเกณฑ์อัตรากำลังครู (มติ ก.ค.ศ.)",
            "ฝังการประเมินเชิงสาเหตุใน WSF Sandbox (กสศ. + ศธ.)",
            "ประกาศมาตรฐานขั้นต่ำแห่งชาติ FSQL (มติ ครม.)",
            "เปิด Equity Dashboard สาธารณะ · เปิดใช้ระบบ EWS จาก iSEE",
        ]),
        ("ปีที่ 2–3 — สร้างหลักฐาน", "amber", [
            "ขยาย Sandbox ระดับจังหวัดแบบสุ่มลำดับ → หลักฐาน DiD",
            "Cost Function Analysis → ค่าน้ำหนักที่มีฐานเชิงประจักษ์",
            "Benefit Incidence Analysis → ตัวเลขที่ไทยยังไม่เคยมี",
            "ประเมินย้อนหลังการควบรวมโรงเรียน 10 ปี (Matched DiD)",
        ]),
        ("ปีที่ 3–7 — ปฏิรูปโครงสร้าง", "red", [
            "แก้ไข ม.60 พ.ร.บ.การศึกษาฯ → Need-based Formula",
            "ตรากฎหมายรองรับ Zero Dropout · แก้ ม.6 พ.ร.บ.กสศ.",
            "Scale-up Clause (comply-or-explain) แก้ pilot trap",
            "ม.39 Earned Autonomy · ขยายภาคบังคับ 9 → 12 ปี",
        ]),
    ]
    for title, col, items in phases:
        h = 26 + len(items) * 15
        p.rect(M, y - h, CW, h, "bg", "line")
        p.rect(M, y - h, 4, h, col)
        p.text(M + 14, y - 17, title, font="b", size=10.5, color="navy")
        yy = y - 33
        for it in items:
            p.text(M + 14, yy, f"▸  {it}", size=9, color="grey", max_w=CW - 28)
            yy -= 15
        y -= h + 12
    p.footer(4, TOTAL, src)
    p.page_break()

    # ═══ หน้า 5 — ความเสี่ยงและข้อเสนอ ═══
    p.header_band("ข้อโต้แย้ง ข้อจำกัด และสิ่งที่ขออนุมัติ", "")
    y = p.H - 108
    p.text(M, y, "ข้อโต้แย้งที่จะเจอ และคำตอบ", font="b", size=12, color="navy")
    y -= 20
    for i, (q, ans) in enumerate([
        ("“ต้องเพิ่มงบการศึกษา”", "งบอันดับ 3 ของประเทศแล้ว — เพิ่มเข้าสูตรผิดทิศ = ขยายช่องว่าง"),
        ("“ควบรวมโรงเรียนเล็กคือคำตอบ”", "ต้นทุนแฝงยังไม่เคยถูกวัด — ต้องวิจัยก่อนขยายนโยบาย"),
        ("“ครูไม่พอ ต้องบรรจุเพิ่ม”", "ปัญหาคือการกระจาย ไม่ใช่จำนวน"),
        ("“มี กสศ. แล้วเพียงพอ”", "กสศ. = 2–3% และอาจสร้าง Shifting the Burden"),
        ("“ให้งบไม่เท่ากัน = เลือกปฏิบัติ”", "รธน. ม.27 วรรคท้าย ระบุชัดว่าไม่ใช่"),
        ("“เด็กลดแล้ว ควรลดงบ”", "เด็กลด = โอกาสยกคุณภาพต่อหัว — ตัดงบ = เสียโอกาสถาวร"),
    ]):
        if i % 2 == 0:
            p.rect(M, y - 21, CW, 21, "bg")
        p.text(M + 8, y - 14, q, font="b", size=8.5, color="red")
        p.text(M + 195, y - 14, ans, size=8.5, color="grey", max_w=CW - 205)
        y -= 21

    y -= 18
    p.rect(M, y - 62, CW, 62, "bg", "line")
    p.text(M + 12, y - 17, "⚖️  ข้อวิพากษ์ที่เรายอมรับว่ายังไม่มีคำตอบที่ดีพอ",
           font="b", size=10, color="navy")
    yy = y - 32
    for t in [
        "① Fixed Cost Floor อาจสร้างแรงจูงใจให้คงโรงเรียนที่ไม่ควรคงไว้ → ต้องผูกกับเงื่อนไขระยะทาง",
        "② เงินที่เพิ่มในโรงเรียนที่ศักยภาพบริหารต่ำอาจไม่เกิดผล → ต้องจับคู่กับการพัฒนาผู้บริหาร",
        "③ สูตรที่แม่นยำเกินไปอาจอธิบายไม่ได้ → trade-off ระหว่างความแม่นยำ ↔ ความชอบธรรม",
    ]:
        p.text(M + 12, yy, t, size=8.5, color="grey", max_w=CW - 24)
        yy -= 14
    y -= 82

    p.text(M, y, "สิ่งที่ขออนุมัติ", font="b", size=12, color="navy")
    y -= 20
    for i, (t, owner, law, money) in enumerate([
        ("ตั้งคณะทำงานทบทวนเกณฑ์อัตรากำลังครู", "ก.ค.ศ. + สพฐ.", "ไม่ต้อง", "ไม่ต้อง"),
        ("ฝังการประเมินเชิงสาเหตุใน WSF Sandbox", "กสศ. + ศธ.", "ไม่ต้อง", "ไม่ต้อง"),
        ("อนุมัติงบวิจัย Benefit Incidence Analysis", "ศธ. + สงป.", "ไม่ต้อง", "งบวิจัยขนาดเล็ก"),
    ], 1):
        p.rect(M, y - 30, CW, 30, "bg", "line")
        p.rect(M, y - 30, 22, 30, "navy")
        p.text(M + 11, y - 20, str(i), font="b", size=11, color="white", align="c")
        p.text(M + 32, y - 13, t, font="b", size=9.5, color="navy")
        p.text(M + 32, y - 25, f"เจ้าภาพ: {owner}", size=8, color="grey")
        p.text(M + CW - 130, y - 13, f"แก้กฎหมาย: {law}", size=8, color="green")
        p.text(M + CW - 130, y - 25, f"ใช้เงินเพิ่ม: {money}", size=8,
               color="green" if money == "ไม่ต้อง" else "amber")
        y -= 36

    y -= 10
    p.rect(M, y - 54, CW, 54, "navy")
    p.text(M + 14, y - 22,
           "ทุกปีที่เราไม่แก้สูตร ระบบจะผลิตซ้ำความเหลื่อมล้ำอีกหนึ่งรุ่นโดยอัตโนมัติ",
           font="b", size=11, color="white", max_w=CW - 28)
    p.text(M + 14, y - 38, "— ไม่ใช่เพราะใครตั้งใจ แต่เพราะสูตรถูกเขียนไว้อย่างนั้น",
           size=9.5, color="white")
    p.text(M + 14, y - 51, "และสูตร คือสิ่งที่แก้ได้ด้วยมติเดียว",
           font="b", size=10.5, color="amber")
    p.footer(5, TOTAL, src)
    p.save()
    return out


# ---------- One-Pager (1 หน้า) ----------
def build_onepager(a: Analysis, out: Path, font_dir: Path | None) -> Path:
    fonts = _find_fonts(font_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    p = ThaiPDF(out, fonts)
    W, M = p.W, p.M
    CW = W - 2 * M
    prim, sec = a.primary, a.secondary

    p.rect(0, p.H - 68, W, 68, "navy")
    p.rect(0, p.H - 68, 6, 68, "amber")
    p.text(M, p.H - 32, "บันทึกข้อเสนอเชิงนโยบาย", font="b", size=14, color="white")
    p.text(M, p.H - 50,
           "การเพิ่มประสิทธิภาพการจัดสรรอัตรากำลังครู โดยไม่ต้องขอเงินเพิ่มและไม่ต้องแก้กฎหมาย",
           size=9, color="grey_l", max_w=CW)

    y = p.H - 92
    p.text(M, y, "๑.  ปัญหาแกนกลาง", font="b", size=11, color="navy")
    y -= 16
    y = p.text(M + 12, y,
               f"งบประมาณกระทรวงศึกษาธิการกว่า 97% จัดสรรแบบ “เท่ากันทุกหัว” "
               f"ในสภาพที่ประชากรวัยเรียนลดลง สูตรนี้กลายเป็นการลงโทษพื้นที่ที่เด็กเบาบางที่สุด "
               f"— {prim.short} มีนักเรียนเฉลี่ย {prim.spr:.1f} คน/ห้อง ขณะที่ {sec.short} "
               f"มี {sec.spr:.1f} คน/ห้อง ต่างกัน {sec.spr / prim.spr:.1f} เท่า",
               size=9.5, color="grey", max_w=CW - 12, leading=14) - 8

    p.text(M, y, "๒.  หลักฐานจากข้อมูล สพฐ. ปีการศึกษา 2569", font="b", size=11, color="navy")
    y -= 18
    cw2 = (CW - 2 * 8) / 3
    for i, (n, c, col) in enumerate([
        (th(a.core_deficit), "ขาดแคลนในระบบหลัก (อัตรา)", "red"),
        (th(a.core_surplus), f"ส่วนเกินใน {sec.short} (อัตรา)", "green"),
        (th(a.core_net), "ตัวเลขที่ระบบมองเห็น (อัตรา)", "navy"),
    ]):
        x = M + i * (cw2 + 8)
        p.rect(x, y - 50, cw2, 50, "bg", "line")
        p.rect(x, y - 50, 4, 50, col)
        p.text(x + 12, y - 24, n, font="b", size=16, color=col)
        p.text(x + 12, y - 42, c, size=8, color="grey", max_w=cw2 - 22)
    y -= 62
    p.rect(M, y - 30, CW, 30, "red")
    p.text(M + 12, y - 19,
           f"ความขาดแคลนระบบหลัก {th(a.core_deficit)} อัตรา ถูกกลบด้วยส่วนเกิน "
           f"{th(a.core_surplus)} อัตรา → ปัญหาการกระจายจึงไม่ปรากฏในรายงานภาพรวม",
           font="b", size=9.5, color="white", max_w=CW - 24)
    y -= 46

    p.text(M, y, "๓.  ข้อเสนอที่ทำได้ทันที", font="b", size=11, color="navy")
    y -= 18
    p.rect(M, y - 58, CW, 58, "navy")
    p.rect(M, y - 58, 4, 58, "amber")
    p.text(M + 14, y - 20, "เปลี่ยนเกณฑ์อัตรากำลังครู", font="b", size=13, color="white")
    p.text(M + 14, y - 37, "จาก “จำนวนนักเรียน” → “ห้องเรียน + ดัชนีความยากลำบาก”",
           font="b", size=11, color="amber")
    p.text(M + 14, y - 52,
           "เครื่องมือ: มติ ก.ค.ศ.  ·  ไม่ต้องแก้ พ.ร.บ.  ·  ไม่ต้องขอเงินเพิ่ม  ·  ภายใน 1 ปีงบประมาณ",
           size=8.5, color="white", max_w=CW - 28)
    y -= 76

    p.text(M, y, "๔.  ตรรกะที่ผู้บริหารต้องทราบ", font="b", size=11, color="navy")
    y -= 16
    for t in [
        "ทำไมไม่ต้องขอเงินเพิ่ม — จำนวนเด็กที่ลดลงทำให้งบต่อหัวเพิ่มขึ้นเอง เราเพียงเปลี่ยนวิธีกระจาย",
        "ทำไมไม่ถือเป็นการเลือกปฏิบัติ — รัฐธรรมนูญ ม.27 วรรคท้าย รองรับมาตรการช่วยผู้ด้อยโอกาสไว้แล้ว",
        "ทำไมต้องทำตอนนี้ — จำนวนห้องเรียนไม่ลดตามสัดส่วนเด็ก ปัญหาจะรุนแรงขึ้นทุกปีการศึกษา",
    ]:
        p.text(M + 12, y, f"▸  {t}", size=9, color="grey", max_w=CW - 24, leading=13)
        y -= 22

    y -= 4
    p.text(M, y, "๕.  สิ่งที่ขอความกรุณาจากท่าน", font="b", size=11, color="navy")
    y -= 18
    for i, t in enumerate([
        "อนุมัติแต่งตั้งคณะทำงานทบทวนเกณฑ์อัตรากำลังครู (ก.ค.ศ. + สพฐ.)",
        "ฝังการประเมินผลเชิงสาเหตุใน WSF Sandbox ที่ดำเนินการอยู่ (กสศ. + ศธ.)",
        "อนุมัติงบวิจัย Benefit Incidence Analysis ของงบการศึกษาทั้งระบบ",
    ], 1):
        p.rect(M, y - 24, CW, 24, "bg", "line")
        p.rect(M, y - 24, 20, 24, "navy")
        p.text(M + 10, y - 16, str(i), font="b", size=10, color="white", align="c")
        p.text(M + 30, y - 16, t, font="b", size=9.5, color="navy", max_w=CW - 42)
        y -= 28

    y -= 8
    p.rect(M, y - 40, CW, 40, "bg")
    p.rect(M, y - 40, 4, 40, "amber")
    p.text(M + 14, y - 18,
           "ทุกปีที่เราไม่แก้สูตร ระบบจะผลิตซ้ำความเหลื่อมล้ำอีกหนึ่งรุ่นโดยอัตโนมัติ",
           font="b", size=10, color="navy", max_w=CW - 28)
    p.text(M + 14, y - 33,
           "— ไม่ใช่เพราะใครตั้งใจ แต่เพราะสูตรถูกเขียนไว้อย่างนั้น",
           size=9, color="grey")

    p.hr(58)
    p.text(M, 44,
           f"แหล่งข้อมูล: {a.meta.get('title')} · {a.meta.get('source')} · "
           f"ปีการศึกษา {a.meta.get('academic_year')}",
           size=7, color="grey_l", max_w=CW)
    p.text(M, 34,
           f"หมายเหตุ: อัตรา 1:{a.ratio:.0f} เป็นเกณฑ์อ้างอิงเพื่อการวิเคราะห์ "
           f"เกณฑ์จริงของ ก.ค.ศ. จำแนกตามขนาดสถานศึกษา · "
           f"ข้อมูลเป็นค่ารวมระดับประเทศ ไม่สะท้อนการกระจายรายโรงเรียน",
           size=7, color="grey_l", max_w=CW)
    p.save()
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(
        description="สร้างเอกสารนำเสนออัตโนมัติจากข้อมูล สพฐ.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="ตัวอย่าง:\n"
               "  python tools/build_docs.py --all\n"
               "  python tools/build_docs.py --deck --font 'IBM Plex Sans Thai'\n"
               "  python tools/build_docs.py --brief --ratio 25\n")
    ap.add_argument("--data", type=Path, default=ROOT / "assets/data/school-data.json")
    ap.add_argument("--out", type=Path, default=ROOT / "dist")
    ap.add_argument("--ratio", type=float, default=20.0, help="อัตรานักเรียนต่อครูอ้างอิง")
    ap.add_argument("--font", default="Sarabun", help="ชื่อฟอนต์สำหรับ PPTX")
    ap.add_argument("--font-dir", type=Path, default=None, help="โฟลเดอร์ไฟล์ .ttf สำหรับ PDF")
    ap.add_argument("--deck", action="store_true")
    ap.add_argument("--brief", action="store_true")
    ap.add_argument("--onepager", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if not any([args.deck, args.brief, args.onepager, args.all]):
        args.all = True

    a = load_analysis(args.data, args.ratio)

    print(f"\n{'─'*70}")
    print(f"📊 สรุปข้อมูลที่ใช้สร้างเอกสาร (เกณฑ์อ้างอิง 1:{args.ratio:.0f})")
    print(f"{'─'*70}")
    for u in a.units:
        mark = "🔴 ขาด" if u.gap > 0 else "🟢 เกิน"
        print(f"  {u.name:<24} {u.spr:>6.1f} คน/ห้อง   {mark} {abs(u.gap):>8,.0f} อัตรา")
    print(f"{'─'*70}")
    print(f"  ระบบหลัก ขาด {a.core_deficit:>10,.0f}  ส่วนเกิน {a.core_surplus:>8,.0f}  สุทธิ {a.core_net:>8,.0f}")
    print(f"  รวมพิเศษ ขาด {a.total_deficit:>10,.0f}  ส่วนเกิน {a.total_surplus:>8,.0f}  สุทธิ {a.net_gap:>8,.0f}")
    print(f"{'─'*70}\n")

    made = []
    if args.deck or args.all:
        made.append(build_deck(a, args.out / "wsf-deck.pptx", args.font))
    if args.brief or args.all:
        made.append(build_brief(a, args.out / "executive-brief.pdf", args.font_dir))
    if args.onepager or args.all:
        made.append(build_onepager(a, args.out / "one-pager.pdf", args.font_dir))

    print("✅ สร้างเอกสารเสร็จสิ้น:")
    for f in made:
        size = f.stat().st_size / 1024
        print(f"   • {f}  ({size:,.0f} KB)")
    print("\n💡 ทุกครั้งที่ข้อมูลอัปเดต ให้รัน etl_students.py แล้วรันสคริปต์นี้ซ้ำ")


if __name__ == "__main__":
    main()