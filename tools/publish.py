#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ซิงก์ chrome + sitemap แล้วจัดชุดไฟล์ไปที่ .site/"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage_site  # noqa: E402
import sync_chrome  # noqa: E402


def main() -> None:
    sync_chrome.main()
    stage_site.main()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        print(f"❌ {e}", file=sys.stderr)
        raise
