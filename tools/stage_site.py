#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""คัดลอกเฉพาะไฟล์สาธารณะไปที่ .site/ สำหรับ Cloudflare Pages"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / ".site"

HTML = [
    "index.html",
    "report.html",
    "simulator.html",
    "gap-map.html",
    "infographic.html",
    "slides.html",
    "qa-slides.html",
    "resources.html",
    "about.html",
    "404.html",
]
FILES = [
    "LICENSE",
    "robots.txt",
    "sitemap.xml",
    "_headers",
    "_redirects",
]
TREES = ["assets", "dist"]


def main() -> None:
    missing = [name for name in HTML + FILES if not (ROOT / name).exists()]
    for name in TREES:
        if not (ROOT / name).is_dir():
            missing.append(name + "/")
    if missing:
        raise SystemExit("ยังไม่มีไฟล์ที่ต้องเผยแพร่: " + ", ".join(missing))

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    for name in HTML + FILES:
        shutil.copy2(ROOT / name, DEST / name)
    for name in TREES:
        shutil.copytree(
            ROOT / name,
            DEST / name,
            ignore=shutil.ignore_patterns(".DS_Store"),
        )
    print(f"จัดชุดเผยแพร่ที่ {DEST.relative_to(ROOT)}/")
    print("ขั้นตอนถัดไป:")
    print("  npx wrangler pages deploy .site --project-name equity-edu-th")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        print(f"❌ {e}", file=sys.stderr)
        raise
