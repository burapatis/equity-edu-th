# Equity Education Thailand — 97:3

เว็บไซต์และชุดเครื่องมือเชิงนโยบายว่าด้วย
**ความเหลื่อมล้ำ ความเสมอภาค และความเท่าเทียมทางการศึกษาของประเทศไทย**

> ประเทศไทยไม่ได้ขาดเงิน ไม่ได้ขาดกฎหมาย และไม่ได้ขาดข้อมูล
> — แต่ขาดสูตรที่จะส่งทรัพยากรไปยังจุดที่จำเป็นที่สุด

## โครงสร้างโครงการ

```
index.html            หน้าแรก
report.html           รายงานฉบับเต็ม 21 ส่วน
simulator.html        เครื่องมือจำลองสูตร WSF
gap-map.html          แผนที่ช่องว่างอัตรากำลังครู
resources.html        คลังทรัพยากร อภิธานศัพท์ แหล่งอ้างอิง
about.html            เกี่ยวกับเว็บไซต์ ผู้จัดทำ และการใช้ข้อมูล
404.html              หน้าไม่พบสำหรับโฮสต์สแตติก
includes/             ส่วนหัว ส่วนท้าย และ meta ร่วม
assets/css/style.css  ระบบออกแบบร่วม
assets/js/main.js     สคริปต์ร่วม + ข้อมูลสำรอง
assets/vendor/        Chart.js ที่เก็บในโปรเจกต์
assets/img/           favicon และภาพแชร์โซเชียล
assets/data/          JSON จาก ETL และ facts.json
dist/                 PPTX และ PDF
sitemap.xml           แผนผังไซต์ (สร้างจาก base_url)
robots.txt
_headers / _redirects ส่วนหัวและความเปลี่ยนเส้นทาง Cloudflare Pages
wrangler.toml         ชี้ output ไปที่ .site/
11.xlsx               ตารางที่ 11 สพฐ. ปีการศึกษา 2569
tools/                ETL, สร้างเอกสาร, ซิงก์ chrome, ICC/power, สุ่มรุ่น WSF, ทดสอบ
LICENSE               MIT สำหรับโค้ด · CC BY-NC-SA 4.0 สำหรับเนื้อหา
```

## เริ่มใช้งาน

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt

python tools/etl_students.py 11.xlsx --report
python tools/test_etl.py
python tools/build_docs.py --all
python tools/build_og.py
python tools/sync_chrome.py
python -m http.server 8080
```

เปิด <http://localhost:8080>

แก้เมนูหรือส่วนท้ายที่ `includes/` แล้วรัน `python tools/sync_chrome.py` เพื่ออัปเดตทุกหน้า เมื่อมีโดเมนจริง ให้ใส่ URL ใน `assets/data/site.json` ที่ `base_url` เพื่อให้ canonical, `og:image` และ sitemap เป็นลิงก์สมบูรณ์

ฟอนต์ Sarabun สำหรับ PDF และภาพแชร์อยู่ใน `tools/fonts/` หากสร้าง PDF ไม่ได้ ให้ดาวน์โหลดจาก [Google Fonts](https://fonts.google.com/specimen/Sarabun) แล้ววางไฟล์ `.ttf` ในโฟลเดอร์นั้น

เปิดจากไฟล์โดยตรงก็ใช้หน้าแรกและรายงานได้ เครื่องมือจำลองและแผนที่ช่องว่างจะใช้ข้อมูลสำรองที่ฝังใน `assets/js/main.js` หากไม่มีเว็บเซิร์ฟเวอร์ — Chart.js อยู่ในโปรเจกต์แล้ว จึงไม่ต้องพึ่ง CDN

## เผยแพร่ (GitHub Pages)

เว็บสาธารณะอยู่ที่ <https://eet.thamdee.com/> จากรีโป [`burapatis/equity-edu-th`](https://github.com/burapatis/equity-edu-th) (ที่อยู่เดิม <https://burapatis.github.io/equity-edu-th/> ยังเปิดได้) — ไม่ใช้รีโป `burapatis.github.io` เพราะที่นั่นเป็นเว็บ TBLF อยู่แล้ว

GitHub Pages เสิร์ฟไฟล์จากรากสาขา `main` (มี `.nojekyll` เพื่อไม่ให้ Jekyll กรองไฟล์) หลังแก้ `base_url` ให้รัน `python tools/sync_chrome.py` แล้วพุช

หน้า `404.html` ใส่ `<base href>` ตาม path ของไซต์ เพื่อให้สไตล์และเมนูทำงานแม้ URL ที่ผิดจะอยู่ลึกกว่าโฟลเดอร์โปรเจกต์

### Cloudflare Pages (ทางเลือก)

ชุดย่อใน `.site/` ไม่รวม `.venv/`, `tools/`, `includes/`, `11.xlsx` และโฟลเดอร์ git ซ้อน

```bash
python tools/publish.py
npx wrangler pages deploy .site --project-name equity-edu-th
```

## ใบอนุญาต

เนื้อหาเผยแพร่ภายใต้ [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.th)
โค้ดเผยแพร่ภายใต้ MIT License — ดูรายละเอียดใน [`LICENSE`](LICENSE)
