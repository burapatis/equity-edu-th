#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ซิงก์ส่วนหัว ส่วนท้าย และ meta ร่วมจาก includes/ ไปยังหน้า HTML ทั้งชุด"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INCLUDES = ROOT / "includes"
PAGES = [
    {
        "file": "index.html",
        "nav": "index",
        "footer": "home",
        "extra_nav": True,
        "disclaimer": "",
        "footer_extra": "",
    },
    {
        "file": "report.html",
        "nav": "report",
        "footer": "inner",
        "disclaimer": "ตัวเลขที่มีระดับความเชื่อมั่นปานกลางควรตรวจสอบจากแหล่งต้นทางก่อนอ้างอิงทางการ",
        "footer_extra": " · สั่งพิมพ์หน้านี้เป็น PDF ได้จากเบราว์เซอร์",
    },
    {
        "file": "simulator.html",
        "nav": "simulator",
        "footer": "inner",
        "disclaimer": "ข้อมูลนักเรียนและห้องเรียนจาก สพฐ. ปีการศึกษา 2569 · ค่าน้ำหนักเป็นตัวเลขสาธิตที่ยังไม่ผ่านการสอบเทียบ",
        "footer_extra": "",
    },
    {
        "file": "gap-map.html",
        "nav": "gap-map",
        "footer": "inner",
        "disclaimer": "ข้อมูลนักเรียนและห้องเรียนจาก สพฐ. ปีการศึกษา 2569 · เกณฑ์ 1:20 เป็นตัวเลขสาธิต",
        "footer_extra": "",
    },
    {
        "file": "infographic.html",
        "nav": "infographic",
        "footer": "inner",
        "disclaimer": "",
        "footer_extra": "",
        "skip_footer": True,
    },
    {
        "file": "resources.html",
        "nav": "resources",
        "footer": "inner",
        "disclaimer": "เนื้อหาเผยแพร่ภายใต้ CC BY-NC-SA 4.0 · โค้ดเผยแพร่ภายใต้ MIT License",
        "footer_extra": "",
    },
    {
        "file": "about.html",
        "nav": "about",
        "footer": "inner",
        "disclaimer": "เนื้อหาเพื่อการแลกเปลี่ยนเรียนรู้เชิงวิชาการ ไม่ใช่เอกสารราชการ",
        "footer_extra": "",
    },
    {
        "file": "404.html",
        "nav": "",
        "footer": "inner",
        "disclaimer": "หน้านี้ใช้เมื่อโฮสต์ไม่พบเส้นทางที่ขอ",
        "footer_extra": "",
    },
]

SITEMAP_PATHS = [
    ("index.html", "1.0", "weekly"),
    ("report.html", "0.9", "monthly"),
    ("simulator.html", "0.8", "monthly"),
    ("gap-map.html", "0.8", "monthly"),
    ("infographic.html", "0.8", "monthly"),
    ("resources.html", "0.7", "monthly"),
    ("about.html", "0.6", "yearly"),
    ("dist/one-pager.pdf", "0.5", "yearly"),
    ("dist/executive-brief.pdf", "0.5", "yearly"),
    ("dist/wsf-deck.pptx", "0.4", "yearly"),
]

NAV_ITEMS = [
    ("index.html", "หน้าแรก", "index", ""),
    ("report.html", "รายงานเต็ม", "report", ""),
    ("simulator.html", "เครื่องมือจำลอง", "simulator", ""),
    ("gap-map.html", "แผนที่ช่องว่าง", "gap-map", ""),
    ("infographic.html", "Infographic", "infographic", ""),
    ("resources.html", "ทรัพยากร", "resources", "nav-cta"),
    ("about.html", "เกี่ยวกับ", "about", ""),
]


def fill(template: str, **kwargs: str) -> str:
    out = template
    for key, value in kwargs.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def wrap(name: str, body: str) -> str:
    return f"<!-- EET:{name} -->\n{body.rstrip()}\n<!-- /EET:{name} -->"


def swap(html: str, name: str, body: str, fallback: tuple[str, str] | None = None) -> str:
    start, end = f"<!-- EET:{name} -->", f"<!-- /EET:{name} -->"
    block = wrap(name, body)
    if start in html and end in html:
        pattern = re.escape(start) + r".*?" + re.escape(end)
        return re.sub(pattern, lambda _m: block, html, count=1, flags=re.S)
    if not fallback:
        raise SystemExit(f"ไม่พบมาร์กเกอร์ {name} และไม่มี fallback")
    a, b = fallback
    i = html.find(a)
    j = html.find(b, i if i >= 0 else 0)
    if i < 0 or j < 0 or j < i:
        raise SystemExit(f"ไม่พบช่วง {name} ในไฟล์")
    return html[:i] + block + html[j + len(b):]


def nav_html(active: str, extra: bool) -> str:
    lines = []
    for href, label, key, extra_class in NAV_ITEMS:
        classes = []
        attrs = [f'href="{href}"']
        if extra_class:
            classes.append(extra_class)
        if key == active:
            classes.append("is-active")
            attrs.append('aria-current="page"')
        if classes:
            attrs.append(f'class="{" ".join(classes)}"')
        lines.append(f"      <a {' '.join(attrs)}>{label}</a>")
        if extra and key == "index":
            lines.append('      <a href="#problem">ปัญหา</a>')
            lines.append('      <a href="#data">ข้อมูล</a>')
            lines.append('      <a href="#roadmap">ข้อเสนอ</a>')
    return "\n".join(lines)


def strip_old_head_chrome(html: str) -> str:
    html = html.replace("<text y='.9em' font-size='90'>⚖️</text></svg>\">", "")
    patterns = [
        r'\n<meta name="theme-color"[^>]*>',
        r'\n<meta property="og:[^"]+"[^>]*>',
        r'\n<meta name="twitter:[^"]+"[^>]*>',
        r'\n<link rel="preconnect"[^>]*>',
        r'\n<link href="https://fonts\.googleapis\.com[^"]*"[^>]*>',
        r'\n<link rel="stylesheet" href="assets/css/style\.css">',
        r'\n<link rel="canonical"[^>]*>',
        r'\n<link rel="icon"[^>]*>',
        r"\n<link rel=\"icon\" href=\"data:image/svg\+xml,[^>]*>.*?</svg>\">",
        r'\n<link rel="apple-touch-icon"[^>]*>',
    ]
    for pat in patterns:
        html = re.sub(pat, "", html)
    return html


def inject_head(html: str, chrome: str) -> str:
    if "<!-- EET:CHROME-HEAD -->" in html:
        return swap(html, "CHROME-HEAD", chrome)
    html = strip_old_head_chrome(html)
    return html.replace("</head>", wrap("CHROME-HEAD", chrome) + "\n</head>", 1)


def page_meta(html: str) -> tuple[str, str]:
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    desc = re.search(r'<meta name="description" content="([^"]*)"', html)
    og_title = re.sub(r"\s+", " ", title.group(1)).strip() if title else "97:3"
    og_desc = desc.group(1) if desc else og_title
    return og_title, og_desc


def site_base() -> str:
    site = ROOT / "assets" / "data" / "site.json"
    if site.exists():
        return (json.loads(site.read_text(encoding="utf-8")).get("base_url") or "").rstrip("/")
    return ""


def base_href() -> str:
    path = urlparse(site_base()).path.rstrip("/")
    return f"{path}/" if path else "/"


def og_image_url() -> str:
    base = site_base()
    path = "assets/img/og-image.png"
    return f"{base}/{path}" if base else path


def page_canonical(filename: str) -> str:
    base = site_base()
    if filename in {"index.html", "404.html"}:
        rel = "/"
    else:
        rel = f"/{filename}"
    return f"{base}{rel}" if base else rel.lstrip("/") or "/"


def loc_url(rel: str) -> str:
    base = site_base()
    if rel == "index.html":
        path = "/"
    else:
        path = f"/{rel.lstrip('/')}"
    return f"{base}{path}" if base else path


def iso_date(path: Path) -> str:
    if not path.exists():
        return ""
    from datetime import datetime, timezone
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ts.date().isoformat()


def write_sitemap() -> None:
    from datetime import datetime, timezone

    base = site_base()
    if not base:
        print("  ⚠ ยังไม่มี base_url ใน assets/data/site.json — ข้าม sitemap/robots")
        return
    urls = []
    for rel, prio, freq in SITEMAP_PATHS:
        lastmod = iso_date(ROOT / rel)
        last = f"    <lastmod>{lastmod}</lastmod>\n" if lastmod else ""
        urls.append(
            "  <url>\n"
            f"    <loc>{loc_url(rel)}</loc>\n"
            f"{last}"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{prio}</priority>\n"
            "  </url>"
        )
    generated = datetime.now(timezone.utc).date().isoformat()
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<!-- generated {generated} by tools/sync_chrome.py -->\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n",
        encoding="utf-8",
    )
    (ROOT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {base}/sitemap.xml\n",
        encoding="utf-8",
    )
    print("  ✓ sitemap.xml")
    print("  ✓ robots.txt")


def build_nav_and_footer(page: dict) -> tuple[str, str]:
    header_tpl = (INCLUDES / "header.html").read_text(encoding="utf-8")
    header = fill(header_tpl, nav=nav_html(page["nav"], page.get("extra_nav", False)))
    if page["footer"] == "home":
        footer = (INCLUDES / "footer-home.html").read_text(encoding="utf-8")
    else:
        footer = fill(
            (INCLUDES / "footer-inner.html").read_text(encoding="utf-8"),
            disclaimer=page["disclaimer"],
            extra=page.get("footer_extra") or "",
        )
    return header, footer


def sync_file(page: dict) -> None:
    path = ROOT / page["file"]
    html = path.read_text(encoding="utf-8")
    og_title, og_desc = page_meta(html)
    chrome = fill(
        (INCLUDES / "chrome-head.html").read_text(encoding="utf-8"),
        og_title=og_title,
        og_description=og_desc,
        og_image=og_image_url(),
        canonical=page_canonical(page["file"]),
    )
    html = inject_head(html, chrome)
    header, footer = build_nav_and_footer(page)
    html = swap(
        html, "HEADER", header,
        fallback=('<a href="#main" class="skip-link">', "</header>"),
    )
    if not page.get("skip_footer"):
        html = swap(
            html, "FOOTER", footer,
            fallback=('<footer class="site-footer">', "</footer>"),
        )
    if page["file"] == "404.html":
        html = re.sub(r'<base href="[^"]*">', f'<base href="{base_href()}">', html, count=1)
    path.write_text(html, encoding="utf-8")
    print(f"  ✓ {page['file']}")


def main() -> None:
    print("ซิงก์ chrome จาก includes/")
    for page in PAGES:
        sync_file(page)
    write_sitemap()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        print(f"❌ {e}", file=sys.stderr)
        raise
