#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
esa_constrained_randomize.py
การสุ่มแบบมีข้อจำกัด (covariate-constrained randomization)
สำหรับจัดรุ่นเขตพื้นที่การศึกษา — ใช้เมื่อจำนวนหน่วยน้อย (40–60 เขต)
"""

import hashlib
import numpy as np
import pandas as pd

SEED       = 25690801
N_WAVE     = 4
N_CANDIDATE = 100_000   # จำนวนชุดที่สร้างเพื่อคัดเลือก
KEEP_PCT   = 0.10       # เก็บ 10% ที่สมดุลที่สุด

# ตัวแปรที่ใช้ตรวจความสมดุล — ต้องประกาศล่วงหน้า ห้ามเปลี่ยนภายหลัง
BALANCE_VARS = [
    "students_per_room",   # อัตราส่วนนักเรียนต่อห้อง
    "poverty_rate",        # สัดส่วนนักเรียนยากจนพิเศษ
    "pct_short_staff",     # สัดส่วนโรงเรียนที่ครูไม่ครบชั้น
    "baseline_score",      # คะแนนฐานเฉลี่ย
    "n_schools",           # จำนวนโรงเรียนในเขต
    "remoteness_index",    # ดัชนีความห่างไกล
]


def imbalance_score(df: pd.DataFrame, waves: np.ndarray) -> float:
    """คะแนนความไม่สมดุล — ยิ่งต่ำยิ่งดี (ผลรวมความแปรปรวนของค่าเฉลี่ยรายรุ่น)"""
    total = 0.0
    for v in BALANCE_VARS:
        x = df[v].to_numpy(dtype=float)
        x = (x - x.mean()) / (x.std() + 1e-12)          # ปรับมาตรฐาน
        means = [x[waves == w].mean() for w in range(1, N_WAVE + 1)]
        total += float(np.var(means))
    return total


def main() -> None:
    esa = pd.read_csv("esa_frame.csv", encoding="utf-8")
    n = len(esa)
    rng = np.random.default_rng(SEED)

    base = np.resize(np.arange(1, N_WAVE + 1), n)       # กระจายรุ่นเท่า ๆ กัน

    # ---- สร้างชุดผู้สมัครและให้คะแนน ----
    candidates, scores = [], []
    for _ in range(N_CANDIDATE):
        w = rng.permutation(base)
        candidates.append(w)
        scores.append(imbalance_score(esa, w))

    scores = np.array(scores)
    cutoff = np.quantile(scores, KEEP_PCT)
    pool = [i for i, s in enumerate(scores) if s <= cutoff]

    # ---- จับสลากเลือก 1 ชุดจากกลุ่มที่สมดุล  (การสุ่มยังคงอยู่) ----
    chosen = candidates[int(rng.choice(pool))]
    esa["wave"] = chosen

    # ---- รายงานความสมดุล ----
    print(f"\n{'─'*72}")
    print(f"ผลการจัดรุ่นเขตพื้นที่  ·  seed = {SEED}  ·  จำนวนเขต = {n}")
    print(f"{'─'*72}")
    print(esa.groupby("wave")[BALANCE_VARS].mean().round(3).to_string())
    print(f"\nคะแนนความไม่สมดุลของชุดที่เลือก: {imbalance_score(esa, chosen):.5f}")
    print(f"ค่ามัธยฐานของชุดทั้งหมด:        {np.median(scores):.5f}")
    print(f"→ ดีกว่าชุดทั่วไป {(1 - imbalance_score(esa, chosen)/np.median(scores))*100:.1f}%")

    # ---- บันทึกผลพร้อมแฮชเพื่อการตรวจสอบ ----
    out = esa[["esa_id", "esa_name", "wave"]].sort_values(["wave", "esa_id"])
    out.to_csv("esa_wave_assignment_FINAL.csv", index=False, encoding="utf-8")

    with open("esa_wave_assignment_FINAL.csv", "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    print(f"\n🔒 SHA-256 ของไฟล์ผลลัพธ์:\n   {digest}")
    print("   → เผยแพร่ค่านี้ทันทีในวันจับสลาก เพื่อป้องกันการแก้ไขภายหลัง\n")


if __name__ == "__main__":
    main()