# 1) ติดตั้ง
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt

# 2) ฟอนต์ Sarabun อยู่ใน tools/fonts/ แล้ว
#    ถ้า PDF ไม่ขึ้นภาษาไทย ให้ดาวน์โหลดจาก Google Fonts แล้ววางไฟล์ .ttf ที่นั่น

# 3) แปลงข้อมูลจาก Excel เป็น JSON แล้วทดสอบ
python tools/etl_students.py 11.xlsx --report
python tools/test_etl.py

# 4) สร้างเอกสารทั้งหมด + ภาพแชร์ + ซิงก์ส่วนหัวส่วนท้าย
python tools/build_docs.py --all
python tools/build_og.py
python tools/sync_chrome.py

# 5) เปิดเว็บ
python -m http.server 8080

# 6) เผยแพร่ GitHub Pages จากสาขา main ของรีโป equity-edu-th
#    เว็บอยู่ที่ https://burapatis.github.io/equity-edu-th/

# ทางเลือก: จัดชุดย่อไปที่ .site/ สำหรับ Cloudflare Pages
# python tools/publish.py
# npx wrangler pages deploy .site --project-name equity-edu-th
