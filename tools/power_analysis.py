#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 power_analysis.py — คำนวณขนาดตัวอย่างสำหรับ WSF Sandbox
================================================================================
 รองรับ 2 แบบแผน:
   ① Parallel Cluster RCT   — ใช้เป็นฐานอนุรักษ์นิยม
   ② Stepped-Wedge CRT      — แบบแผนที่เสนอจริง (Hussey & Hughes 2007)

 การใช้งาน:
     python tools/power_analysis.py
     python tools/power_analysis.py --icc 0.24 --m 20
     python tools/power_analysis.py --from-icc-json assets/data/icc.json
     python tools/power_analysis.py --icc 0.20 --m 20 --target-mdes 0.10 --table

 ติดตั้ง:  pip install numpy scipy
================================================================================
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

try:
    from scipy.stats import norm
except ImportError:
    sys.exit("❌ ต้องติดตั้งก่อน:  pip install numpy scipy")


# ──────────────────────────────────────────────────────────────────────────────
# ① Parallel Cluster RCT
# ──────────────────────────────────────────────────────────────────────────────
def mdes_parallel(J: int, m: float, icc: float, *,
                  r2_cluster: float = 0.0, r2_indiv: float = 0.0,
                  P: float = 0.5, alpha: float = 0.05, power: float = 0.80) -> float:
    """
    MDES ของ parallel CRT (หน่วยสุ่ม = โรงเรียน)
      J = จำนวนโรงเรียนทั้งหมด · m = นักเรียนต่อโรงเรียน · P = สัดส่วนกลุ่มทดลอง
      r2_cluster / r2_indiv = สัดส่วนความแปรปรวนที่อธิบายได้ด้วยตัวแปรร่วม
    """
    if J < 3:
        return float("nan")
    M = norm.ppf(1 - alpha / 2) + norm.ppf(power)          # ≈ 2.802
    term_c = icc * (1 - r2_cluster) / (P * (1 - P) * J)
    term_i = (1 - icc) * (1 - r2_indiv) / (P * (1 - P) * J * m)
    return M * math.sqrt(term_c + term_i)


def solve_J_parallel(target: float, m: float, icc: float, **kw) -> int:
    lo, hi = 4, 100_000
    while lo < hi:
        mid = (lo + hi) // 2
        if mdes_parallel(mid, m, icc, **kw) <= target:
            hi = mid
        else:
            lo = mid + 1
    return lo


# ──────────────────────────────────────────────────────────────────────────────
# ② Stepped-Wedge CRT  (Hussey & Hughes 2007)
# ──────────────────────────────────────────────────────────────────────────────
def _sw_design_matrix(n_seq: int) -> np.ndarray:
    """X[k][j] = 1 ถ้าลำดับที่ k ได้รับมาตรการแล้วในช่วงเวลา j
       n_seq รุ่น → T = n_seq + 1 ช่วงเวลา (ช่วงที่ 0 = ฐาน ทุกรุ่นยังไม่ได้รับ)"""
    T = n_seq + 1
    X = np.zeros((n_seq, T), dtype=float)
    for k in range(n_seq):
        X[k, k + 1:] = 1.0
    return X


def var_stepped_wedge(I: int, n_seq: int, m: float, icc: float) -> float:
    """
    ความแปรปรวนของค่าประมาณผลมาตรการในแบบ stepped-wedge
    สมมติผลลัพธ์ถูกปรับมาตรฐาน (ความแปรปรวนรวม = 1)
        σ²_α = icc            (ระหว่างโรงเรียน)
        σ²_e = 1 − icc        (ภายในโรงเรียน)
        σ²   = σ²_e / m       (ความแปรปรวนของค่าเฉลี่ยกลุ่มต่อช่วงเวลา)
    """
    Xs = _sw_design_matrix(n_seq)
    T = Xs.shape[1]

    per_seq = I // n_seq
    if per_seq < 1:
        return float("nan")
    X = np.repeat(Xs, per_seq, axis=0)          # (I × T)
    I_eff = X.shape[0]

    U = float(X.sum())
    W = float(np.sum(X.sum(axis=0) ** 2))       # รวมตามช่วงเวลา
    V = float(np.sum(X.sum(axis=1) ** 2))       # รวมตามโรงเรียน

    s2a = icc                    # between-cluster
    s2  = (1 - icc) / m          # within, ต่อค่าเฉลี่ยกลุ่ม-ช่วงเวลา

    num = I_eff * s2 * (s2 + T * s2a)
    den = (I_eff * U - W) * s2 + (U**2 + I_eff * T * U - T * W - I_eff * V) * s2a
    return num / den if den > 0 else float("nan")


def mdes_stepped_wedge(I: int, n_seq: int, m: float, icc: float, *,
                       alpha: float = 0.05, power: float = 0.80) -> float:
    v = var_stepped_wedge(I, n_seq, m, icc)
    if not np.isfinite(v) or v <= 0:
        return float("nan")
    M = norm.ppf(1 - alpha / 2) + norm.ppf(power)
    return M * math.sqrt(v)


def solve_I_stepped_wedge(target: float, n_seq: int, m: float, icc: float, **kw) -> int:
    lo, hi = n_seq, 20_000
    while lo < hi:
        mid = (lo + hi) // 2
        mid -= mid % n_seq          # ให้หารลงตัวกับจำนวนรุ่น
        mid = max(mid, n_seq)
        val = mdes_stepped_wedge(mid, n_seq, m, icc, **kw)
        if np.isfinite(val) and val <= target:
            hi = mid
        else:
            lo = mid + n_seq
    return lo


# ──────────────────────────────────────────────────────────────────────────────
# รายงาน
# ──────────────────────────────────────────────────────────────────────────────
LINE = "─" * 74


def print_header(icc, m, target, n_seq, r2):
    print(f"\n{'═'*74}")
    print("📈 การคำนวณขนาดตัวอย่าง — WSF Sandbox")
    print(f"{'═'*74}")
    print(f"  ICC (ρ)                        : {icc:.4f}")
    print(f"  นักเรียนที่วัดผลต่อโรงเรียน (m)  : {m:.0f}")
    print(f"  R² จากคะแนนฐาน                  : {r2:.2f}")
    print(f"  ขนาดผลเป้าหมาย (MDES)           : {target:.3f} SD")
    print(f"  จำนวนรุ่นใน stepped-wedge        : {n_seq} รุ่น ({n_seq+1} ช่วงเวลา)")
    print(f"  α = 0.05 (สองทาง) · power = 0.80")
    deff = 1 + (m - 1) * icc
    print(f"\n  Design Effect (DEFF)           : {deff:.2f}")
    print(f"  → ต้องใช้โรงเรียนมากกว่าการสุ่มรายบุคคล ≈ {deff:.1f} เท่า")


def print_results(icc, m, target, n_seq, r2):
    kw_p = dict(r2_cluster=r2, r2_indiv=r2)

    J_par = solve_J_parallel(target, m, icc, **kw_p)
    I_sw  = solve_I_stepped_wedge(target, n_seq, m, icc)

    print(f"\n{LINE}")
    print("🎯 จำนวนโรงเรียนที่ต้องการ")
    print(LINE)
    print(f"  ① Parallel CRT (อนุรักษ์นิยม)      : {J_par:>6,} แห่ง")
    print(f"  ② Stepped-Wedge ({n_seq} รุ่น)        : {I_sw:>6,} แห่ง   ← แบบแผนที่เสนอ")
    if J_par > 0:
        print(f"\n  → Stepped-wedge ประหยัดโรงเรียนได้ {(1 - I_sw/J_par)*100:.0f}%")
    return J_par, I_sw


def print_mdes_table(icc, m, n_seq, r2):
    print(f"\n{LINE}")
    print("📋 ตาราง MDES ตามจำนวนโรงเรียน")
    print(LINE)
    print(f"  {'โรงเรียน':>10} {'Parallel':>12} {'Stepped-Wedge':>16}  ประเมิน")
    print(LINE)
    for J in (100, 150, 200, 300, 400, 500, 600, 800, 1000):
        p = mdes_parallel(J, m, icc, r2_cluster=r2, r2_indiv=r2)
        s = mdes_stepped_wedge(J - J % n_seq, n_seq, m, icc)
        flag = "🟢 ดี" if s <= 0.10 else ("🟠 พอใช้" if s <= 0.15 else "🔴 ไม่พอ")
        print(f"  {J:>10,} {p:>12.3f} {s:>16.3f}  {flag}")
    print(LINE)
    print("  เกณฑ์: 🟢 ≤0.10 SD (ตรวจจับผลระดับนโยบายได้) · 🔴 >0.15 SD (หยาบเกินไป)")


def print_sensitivity(m, target, n_seq, r2):
    print(f"\n{LINE}")
    print("🔬 ความไวต่อค่า ICC (Sensitivity Analysis)")
    print(LINE)
    print(f"  {'ICC':>8} {'DEFF':>8} {'Parallel':>12} {'Stepped-Wedge':>16}")
    print(LINE)
    for icc in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35):
        deff = 1 + (m - 1) * icc
        J = solve_J_parallel(target, m, icc, r2_cluster=r2, r2_indiv=r2)
        I = solve_I_stepped_wedge(target, n_seq, m, icc)
        print(f"  {icc:>8.2f} {deff:>8.2f} {J:>12,} {I:>16,}")
    print(LINE)
    print("  ⚠️ ให้ใช้ค่า ICC ที่สูงที่สุดจาก calc_icc.py ในการวางแผน")


def print_caveats():
    print(f"\n{LINE}")
    print("⚠️  ข้อจำกัดที่ต้องระบุเมื่อนำผลไปใช้")
    print(LINE)
    print("  1. สูตร Hussey & Hughes สมมติว่าผลของมาตรการคงที่ตลอดเวลา")
    print("     หากผลค่อย ๆ สะสม กำลังทดสอบจริงจะต่ำกว่าที่คำนวณ")
    print("  2. ยังไม่ได้รวมการสูญหายของหน่วย (attrition) — ควรเผื่อ 10–15%")
    print("  3. ยังไม่ได้รวมความสัมพันธ์ภายในโรงเรียนข้ามเวลา (cluster autocorrelation)")
    print("  4. ค่า R² จากคะแนนฐานเป็นการประมาณ ควรตรวจสอบจากข้อมูลจริง")
    print("  5. มาตรการ M2 (อัตรากำลังครู) สุ่มที่ระดับเขต จึงต้องคำนวณแยก")
    print(f"{LINE}\n")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="คำนวณขนาดตัวอย่างสำหรับ WSF Sandbox (parallel + stepped-wedge)")
    ap.add_argument("--icc", type=float, default=0.20, help="ค่า ICC (ค่าเริ่มต้น 0.20)")
    ap.add_argument("--m", type=float, default=20, help="นักเรียนที่วัดผลต่อโรงเรียน")
    ap.add_argument("--target-mdes", type=float, default=0.10, help="MDES เป้าหมาย (SD)")
    ap.add_argument("--sequences", type=int, default=4, help="จำนวนรุ่นใน stepped-wedge")
    ap.add_argument("--r2", type=float, default=0.50, help="R² จากคะแนนฐาน")
    ap.add_argument("--from-icc-json", type=Path, default=None,
                    help="อ่านค่า ICC จากผลลัพธ์ของ calc_icc.py")
    ap.add_argument("--table", action="store_true", help="แสดงตาราง MDES")
    ap.add_argument("--out", type=Path, default=Path("assets/data/power.json"))
    args = ap.parse_args()

    icc, m = args.icc, args.m
    if args.from_icc_json and args.from_icc_json.exists():
        j = json.loads(args.from_icc_json.read_text(encoding="utf-8"))
        icc = j.get("icc_recommended", icc)
        m = j.get("avg_cluster_size", m)
        print(f"📥 อ่านค่าจาก {args.from_icc_json}: ICC = {icc:.4f} · m = {m:.1f}")

    print_header(icc, m, args.target_mdes, args.sequences, args.r2)
    J_par, I_sw = print_results(icc, m, args.target_mdes, args.sequences, args.r2)

    if args.table:
        print_mdes_table(icc, m, args.sequences, args.r2)
    print_sensitivity(m, args.target_mdes, args.sequences, args.r2)

    # ประเมินแผน 600 โรงเรียน
    mdes_600 = mdes_stepped_wedge(600, args.sequences, m, icc)
    print(f"\n{LINE}")
    print("✅ การประเมินแผนปัจจุบัน (600 โรงเรียน / 4 รุ่น)")
    print(LINE)
    print(f"  MDES ที่ได้ : {mdes_600:.3f} SD")
    if mdes_600 <= args.target_mdes:
        print(f"  ผลประเมิน  : 🟢 เพียงพอ — ตรวจจับผลขนาด {args.target_mdes} SD ได้")
    else:
        need = solve_I_stepped_wedge(args.target_mdes, args.sequences, m, icc)
        print(f"  ผลประเมิน  : 🔴 ไม่เพียงพอ — ต้องใช้ {need:,} โรงเรียน")
        print(f"  ทางเลือก   : ① เพิ่มโรงเรียนเป็น {need:,} แห่ง")
        print(f"               ② เพิ่มจำนวนรุ่นจาก {args.sequences} เป็น {args.sequences+2} รุ่น")
        print(f"               ③ ยอมรับ MDES ที่ {mdes_600:.2f} SD แทน")

    print_caveats()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "icc": icc, "m": m, "target_mdes": args.target_mdes,
        "sequences": args.sequences, "r2": args.r2,
        "design_effect": 1 + (m - 1) * icc,
        "required_schools_parallel": J_par,
        "required_schools_stepped_wedge": I_sw,
        "mdes_at_600_schools": mdes_600,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ บันทึกผลแล้ว: {args.out}\n")


if __name__ == "__main__":
    main()