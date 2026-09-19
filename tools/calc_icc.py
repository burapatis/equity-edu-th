#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 calc_icc.py — คำนวณ Intraclass Correlation Coefficient (ICC)
================================================================================
 จากข้อมูลคะแนนสอบรายบุคคล (NT / RT / O-NET) เพื่อใช้กำหนดขนาดตัวอย่าง
 ของ WSF Sandbox ตามโปรโตคอลการสุ่มลำดับ

 รูปแบบไฟล์ CSV ที่ต้องการ (ชื่อคอลัมน์ยืดหยุ่น — ดู COLUMN_ALIASES):
     school_id , student_id , score , [year] , [subject] , [grade]

 การใช้งาน:
     python tools/calc_icc.py data/nt_scores.csv
     python tools/calc_icc.py data/nt_scores.csv --by year subject
     python tools/calc_icc.py data/nt_scores.csv --min-students 10 --bootstrap 500
     python tools/calc_icc.py data/nt_scores.csv --out assets/data/icc.json

 ติดตั้ง:  pip install pandas numpy statsmodels
================================================================================
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np

try:
    import pandas as pd
except ImportError:
    sys.exit("❌ ต้องติดตั้งก่อน:  pip install pandas numpy statsmodels")

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
# ชื่อคอลัมน์ที่ยอมรับได้ (รองรับทั้งไทยและอังกฤษ)
# ──────────────────────────────────────────────────────────────────────────────
COLUMN_ALIASES = {
    "school_id":  ["school_id", "schoolid", "smis", "obec_code", "รหัสโรงเรียน", "โรงเรียน"],
    "student_id": ["student_id", "studentid", "pid", "รหัสนักเรียน", "เลขประจำตัว"],
    "score":      ["score", "total_score", "raw_score", "คะแนน", "คะแนนรวม"],
    "year":       ["year", "academic_year", "ปีการศึกษา", "ปี"],
    "subject":    ["subject", "test_name", "วิชา", "สาระ"],
    "grade":      ["grade", "level", "ชั้น", "ระดับชั้น"],
}


def resolve_columns(df: pd.DataFrame) -> dict:
    """จับคู่ชื่อคอลัมน์จริงกับชื่อมาตรฐาน"""
    lower = {str(c).strip().lower(): c for c in df.columns}
    found = {}
    for std, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            if a.lower() in lower:
                found[std] = lower[a.lower()]
                break
    missing = [k for k in ("school_id", "score") if k not in found]
    if missing:
        sys.exit(f"❌ ไม่พบคอลัมน์ที่จำเป็น: {missing}\n"
                 f"   คอลัมน์ที่มีในไฟล์: {list(df.columns)}")
    return found


# ──────────────────────────────────────────────────────────────────────────────
# วิธีที่ 1 — ANOVA-based ICC (เร็ว ใช้เป็นค่าอ้างอิง)
# ──────────────────────────────────────────────────────────────────────────────
def icc_anova(df: pd.DataFrame) -> dict:
    """ICC(1) จากการแยกความแปรปรวนแบบ one-way ANOVA"""
    g = df.groupby("school_id")["score"]
    k = g.ngroups
    n_total = len(df)
    if k < 2:
        return {"icc": np.nan, "method": "anova", "note": "โรงเรียนน้อยกว่า 2 แห่ง"}

    grand = df["score"].mean()
    counts = g.count().to_numpy(dtype=float)
    means = g.mean().to_numpy(dtype=float)

    ssb = float(np.sum(counts * (means - grand) ** 2))          # between
    ssw = float(((df["score"] - g.transform("mean")) ** 2).sum())  # within

    msb = ssb / (k - 1)
    msw = ssw / (n_total - k) if n_total > k else np.nan

    # n0 = ขนาดกลุ่มเฉลี่ยแบบปรับแก้
    n0 = (n_total - np.sum(counts ** 2) / n_total) / (k - 1)

    var_b = max((msb - msw) / n0, 0.0)
    var_w = msw
    icc = var_b / (var_b + var_w) if (var_b + var_w) > 0 else np.nan

    return {
        "icc": float(icc),
        "var_between": float(var_b),
        "var_within": float(var_w),
        "n_schools": int(k),
        "n_students": int(n_total),
        "avg_cluster_size": float(n0),
        "method": "anova",
    }


# ──────────────────────────────────────────────────────────────────────────────
# วิธีที่ 2 — Linear Mixed Model (แม่นยำกว่า ใช้เป็นค่าหลัก)
# ──────────────────────────────────────────────────────────────────────────────
def icc_mixed(df: pd.DataFrame) -> dict:
    try:
        import statsmodels.formula.api as smf
    except ImportError:
        return {"icc": np.nan, "method": "mixedlm", "note": "ไม่ได้ติดตั้ง statsmodels"}

    try:
        model = smf.mixedlm("score ~ 1", df, groups=df["school_id"])
        res = model.fit(reml=True, method="lbfgs")
        var_b = float(res.cov_re.iloc[0, 0])
        var_w = float(res.scale)
        icc = var_b / (var_b + var_w) if (var_b + var_w) > 0 else np.nan
        return {
            "icc": float(icc),
            "var_between": var_b,
            "var_within": var_w,
            "n_schools": int(df["school_id"].nunique()),
            "n_students": int(len(df)),
            "converged": bool(res.converged),
            "method": "mixedlm",
        }
    except Exception as e:
        return {"icc": np.nan, "method": "mixedlm", "note": f"ประมาณค่าไม่สำเร็จ: {e}"}


# ──────────────────────────────────────────────────────────────────────────────
# ช่วงความเชื่อมั่นแบบ cluster bootstrap
# ──────────────────────────────────────────────────────────────────────────────
def bootstrap_ci(df: pd.DataFrame, n_boot: int, seed: int = 20690801) -> tuple:
    if n_boot <= 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    schools = df["school_id"].unique()
    groups = {s: d for s, d in df.groupby("school_id")}
    vals = []
    for _ in range(n_boot):
        picked = rng.choice(schools, size=len(schools), replace=True)
        sample = pd.concat([groups[s] for s in picked], ignore_index=True)
        # ต้องตั้ง id ใหม่เพื่อไม่ให้โรงเรียนที่ถูกเลือกซ้ำถูกยุบรวมกัน
        sample["school_id"] = np.repeat(np.arange(len(picked)),
                                        [len(groups[s]) for s in picked])
        r = icc_anova(sample)
        if not np.isnan(r["icc"]):
            vals.append(r["icc"])
    if not vals:
        return (np.nan, np.nan)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


# ──────────────────────────────────────────────────────────────────────────────
# การเตรียมข้อมูล
# ──────────────────────────────────────────────────────────────────────────────
def prepare(df: pd.DataFrame, cols: dict, min_students: int,
            standardize: bool) -> pd.DataFrame:
    out = pd.DataFrame({
        "school_id": df[cols["school_id"]].astype(str),
        "score": pd.to_numeric(df[cols["score"]], errors="coerce"),
    })
    for opt in ("year", "subject", "grade"):
        if opt in cols:
            out[opt] = df[cols[opt]].astype(str)

    before = len(out)
    out = out.dropna(subset=["score"])
    dropped_na = before - len(out)

    # ปรับมาตรฐานภายในกลุ่ม ปี × วิชา  (สำคัญมาก — ดูหมายเหตุในเอกสาร)
    if standardize:
        keys = [k for k in ("year", "subject", "grade") if k in out.columns]
        if keys:
            out["score"] = out.groupby(keys)["score"].transform(
                lambda x: (x - x.mean()) / (x.std(ddof=0) + 1e-12))
        else:
            out["score"] = (out["score"] - out["score"].mean()) / (out["score"].std(ddof=0) + 1e-12)

    # คัดโรงเรียนที่มีนักเรียนน้อยเกินไป
    sizes = out.groupby("school_id")["score"].size()
    keep = sizes[sizes >= min_students].index
    dropped_small = int((~out["school_id"].isin(keep)).sum())
    out = out[out["school_id"].isin(keep)].reset_index(drop=True)

    print(f"   • ตัดแถวที่คะแนนว่าง       : {dropped_na:,}")
    print(f"   • ตัดโรงเรียนที่เล็กกว่า {min_students} คน : {dropped_small:,} แถว")
    return out


# ──────────────────────────────────────────────────────────────────────────────
# รายงาน
# ──────────────────────────────────────────────────────────────────────────────
def report_block(name: str, sub: pd.DataFrame, n_boot: int) -> dict:
    a = icc_anova(sub)
    m = icc_mixed(sub)
    lo, hi = bootstrap_ci(sub, n_boot)
    primary = m["icc"] if not np.isnan(m.get("icc", np.nan)) else a["icc"]

    print(f"\n  ── {name} " + "─" * max(0, 56 - len(name)))
    print(f"     โรงเรียน {a['n_schools']:,} แห่ง · นักเรียน {a['n_students']:,} คน "
          f"· เฉลี่ย {a['avg_cluster_size']:.1f} คน/โรงเรียน")
    print(f"     ICC (ANOVA)    : {a['icc']:.4f}")
    if not np.isnan(m.get("icc", np.nan)):
        print(f"     ICC (MixedLM)  : {m['icc']:.4f}   ← ใช้ค่านี้เป็นหลัก")
    if not np.isnan(lo):
        print(f"     95% CI         : [{lo:.4f}, {hi:.4f}]")

    return {
        "group": name,
        "icc": float(primary),
        "icc_anova": a["icc"],
        "icc_mixed": m.get("icc"),
        "ci_low": lo, "ci_high": hi,
        "n_schools": a["n_schools"],
        "n_students": a["n_students"],
        "avg_cluster_size": a["avg_cluster_size"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="คำนวณ ICC จากข้อมูลคะแนนสอบรายบุคคล",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path, help="ไฟล์ CSV ข้อมูลคะแนน")
    ap.add_argument("--by", nargs="*", default=[],
                    help="แยกคำนวณตามคอลัมน์ เช่น --by year subject")
    ap.add_argument("--min-students", type=int, default=10,
                    help="จำนวนนักเรียนขั้นต่ำต่อโรงเรียน (ค่าเริ่มต้น 10)")
    ap.add_argument("--bootstrap", type=int, default=0,
                    help="จำนวนรอบ bootstrap สำหรับช่วงความเชื่อมั่น (0 = ไม่ทำ)")
    ap.add_argument("--no-standardize", action="store_true",
                    help="ไม่ปรับมาตรฐานคะแนน (ไม่แนะนำ)")
    ap.add_argument("--out", type=Path, default=Path("assets/data/icc.json"))
    args = ap.parse_args()

    if not args.input.exists():
        sys.exit(f"❌ ไม่พบไฟล์: {args.input}")

    print(f"\n📂 อ่านไฟล์: {args.input}")
    raw = pd.read_csv(args.input, encoding="utf-8-sig")
    cols = resolve_columns(raw)
    print(f"   • จับคู่คอลัมน์ได้: {cols}")

    df = prepare(raw, cols, args.min_students, not args.no_standardize)
    if df.empty:
        sys.exit("❌ ไม่เหลือข้อมูลหลังการกรอง")

    print(f"\n{'═'*70}")
    print("📊 ผลการคำนวณ Intraclass Correlation Coefficient (ICC)")
    print(f"{'═'*70}")

    results = [report_block("ภาพรวมทั้งหมด", df, args.bootstrap)]

    by = [c for c in args.by if c in df.columns]
    if by:
        for keys, sub in df.groupby(by):
            label = " × ".join(map(str, keys if isinstance(keys, tuple) else (keys,)))
            if sub["school_id"].nunique() >= 10:
                results.append(report_block(label, sub, args.bootstrap))

    # ── สรุปและคำแนะนำ ──
    iccs = [r["icc"] for r in results[1:] if not np.isnan(r["icc"])] or [results[0]["icc"]]
    icc_max = float(np.nanmax(iccs))
    icc_med = float(np.nanmedian(iccs))
    m_avg = float(results[0]["avg_cluster_size"])

    print(f"\n{'═'*70}")
    print("🎯 สรุปสำหรับการออกแบบ Sandbox")
    print(f"{'═'*70}")
    print(f"  ICC มัธยฐาน                      : {icc_med:.4f}")
    print(f"  ICC สูงสุด (ใช้ค่านี้ในการวางแผน) : {icc_max:.4f}")
    print(f"  ขนาดกลุ่มเฉลี่ย (m)               : {m_avg:.1f} คน/โรงเรียน")
    deff = 1 + (m_avg - 1) * icc_max
    print(f"  Design Effect (DEFF)             : {deff:.2f}")
    print(f"\n  → ต้องใช้โรงเรียนมากกว่าการสุ่มรายบุคคลประมาณ {deff:.1f} เท่า")
    print(f"\n  ขั้นถัดไป:")
    print(f"     python tools/power_analysis.py --icc {icc_max:.4f} --m {m_avg:.0f}")

    # ── บันทึกผล ──
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": args.input.name,
        "standardized": not args.no_standardize,
        "min_students_per_school": args.min_students,
        "icc_recommended": icc_max,
        "icc_median": icc_med,
        "avg_cluster_size": m_avg,
        "design_effect": deff,
        "results": results,
        "caveat": ("ICC ที่แนะนำคือค่าสูงสุดจากกลุ่มย่อย เพื่อความอนุรักษ์นิยม "
                   "คะแนนถูกปรับมาตรฐานภายในกลุ่ม ปี×วิชา ก่อนคำนวณ"),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ บันทึกผลแล้ว: {args.out}\n")


if __name__ == "__main__":
    main()