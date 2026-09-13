#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""สร้างภาพแชร์โซเชียล 1200×630 จากฟอนต์ Sarabun ในโปรเจกต์"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "assets" / "img" / "og-image.png"

NAVY = (26, 43, 76)
NAVY_DEEP = (11, 18, 32)
CREAM = (244, 241, 234)
AMBER = (242, 183, 87)
MUTED = (201, 210, 222)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def main() -> None:
    img = Image.new("RGB", (1200, 630), NAVY)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 18, 630), fill=AMBER)
    draw.rectangle((0, 0, 1200, 8), fill=NAVY_DEEP)

    brand = font("Sarabun-Bold.ttf", 168)
    sub = font("Sarabun-SemiBold.ttf", 42)
    body = font("Sarabun-Regular.ttf", 32)
    small = font("Sarabun-Medium.ttf", 22)

    draw.text((72, 88), "97", font=brand, fill=CREAM)
    ninety_w = draw.textlength("97", font=brand)
    draw.text((72 + ninety_w, 88), ":", font=brand, fill=AMBER)
    colon_w = draw.textlength(":", font=brand)
    draw.text((72 + ninety_w + colon_w, 88), "3", font=brand, fill=CREAM)

    draw.text((72, 290), "ความเสมอภาคทางการศึกษาไทย", font=sub, fill=CREAM)
    draw.text((72, 348), "Equity Education Thailand", font=body, fill=MUTED)
    draw.rectangle((72, 430, 220, 436), fill=AMBER)
    draw.text((72, 458), "ไม่ได้ขาดเงิน — ขาดสูตร", font=sub, fill=AMBER)
    draw.text((72, 560), "รายงานวิเคราะห์เชิงนโยบาย 21 ส่วน · ข้อมูล สพฐ. ปีการศึกษา 2569", font=small, fill=MUTED)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"✅ {OUT}  ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
