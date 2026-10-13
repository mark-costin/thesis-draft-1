import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spec import BOUNDS

df = pd.read_parquet("experiment/data/raw/cohort.parquet")
base = df[df["visit_number"] == 1]
ok = True
DIS = ["cvd", "t2d", "resp", "neuro"]

def check(name, cond, info=""):
    global ok
    print(f"{'✅' if cond else '❌'} {name} {info}")
    ok = ok and bool(cond)

# --- Labels across visits ---
helpers = [c for c in df.columns if c.startswith("_")]
check("Labels | No helper columns left in cohort", len(helpers) == 0, f"{helpers}")

for d in DIS:
    drops = int((df.groupby("patient_id")[f"y_{d}"].diff().fillna(0) < 0).sum())
    check(f"Labels | y_{d} monotone across visits", drops == 0, f"(violations: {drops})")

n_vis = df.groupby("patient_id")["visit_number"].transform("max")
multi = df[n_vis > 1]
first = multi[multi["visit_number"] == 1].set_index("patient_id")
last = multi.loc[multi.groupby("patient_id")["visit_number"].idxmax()].set_index("patient_id")
for d in DIS:
    f, l = first[f"y_{d}"].mean(), last[f"y_{d}"].mean()
    new_cases = int(((first[f"y_{d}"] == 0) & (last[f"y_{d}"] == 1)).sum())
    check(f"Labels | y_{d} first→last visit (same patients)", l >= f,
          f"({f:.3f} → {l:.3f}, new cases: {new_cases})")

total_new = sum(int((df.groupby("patient_id")[f"y_{d}"].nunique() > 1).sum()) for d in DIS)
check("Labels | Some patients become diagnosed at follow-up", total_new > 0, f"({total_new} label changes)")

# --- CDSS Data Dictionary range compliance (every generated feature, every visit) ---
for col, b in BOUNDS.items():
    if col not in df.columns:
        continue
    s = df[col].dropna()
    out = int(((s < b["min"]) | (s > b["max"])).sum())
    check(f"Spec  | {col} within CDSS range [{b['min']}, {b['max']}]", out == 0,
          f"(out of range: {out}, observed {s.min():.2f}–{s.max():.2f})")

# --- Realism: glycaemia ---
hb_mean = base["hba1c"].mean()
check("Realism | HbA1c mean in 5.3–5.9%", 5.3 <= hb_mean <= 5.9, f"(mean {hb_mean:.2f}%)")
hb_diab = (base["hba1c"] >= 6.5).mean() * 100
t2d_prev = base["y_t2d"].mean() * 100
check("Realism | Diagnostic HbA1c (≥ 6.5%) share in 6–14%", 6 <= hb_diab <= 14,
      f"({hb_diab:.1f}% vs T2D prevalence {t2d_prev:.1f}%)")
m = base.groupby("y_t2d")["hba1c"].mean()
check("Realism | HbA1c higher in y_t2d=1", bool(m[1] > m[0]),
      f"(no disease {m[0]:.2f}% vs disease {m[1]:.2f}%)")
t2d_diag = (base.loc[base["y_t2d"] == 1, "hba1c"] >= 6.5).mean() * 100
print(f"ℹ️  T2D cases with HbA1c ≥ 6.5%: {t2d_diag:.1f}%")
pair = base[["fpg", "hba1c"]].dropna()
r = pair["fpg"].corr(pair["hba1c"])
check("Realism | FPG correlated with HbA1c (0.5–0.85)", 0.5 <= r <= 0.85,
      f"(r = {r:.2f}, FPG mean {pair['fpg'].mean():.1f} mg/dL)")

# --- Realism: dictionary high-risk ranges are reached ---
severe = [
    ("spo2", "min", 90.0, "< 90 (hypoxaemia)"),
    ("fev1_fvc_ratio", "min", 60.0, "< 60 (obstruction)"),
    ("mmse", "min", 18, "< 18 (severe cognitive impairment)"),
    ("phq9", "max", 15, "≥ 15 (moderately severe depression)"),
    ("fpg", "max", 126, "≥ 126 (diabetic fasting glucose)"),
]
for col, side, thr, label in severe:
    s = base[col].dropna()
    reached = (s.min() < thr) if side == "min" else (s.max() >= thr)
    share = ((s < thr) if side == "min" else (s >= thr)).mean() * 100
    check(f"Realism | {col} reaches {label}", bool(reached), f"({share:.1f}% of measured patients)")

# --- Realism: domain biomarkers are linked to their outcome ---
links = [
    ("y_resp", "fev1_fvc_ratio", "lower"),
    ("y_resp", "spo2", "lower"),
    ("y_neuro", "mmse", "lower"),
    ("y_neuro", "phq9", "higher"),
]
for y, col, direction in links:
    m = base.groupby(y)[col].mean()
    good = (m[1] < m[0]) if direction == "lower" else (m[1] > m[0])
    check(f"Realism | {col} {direction} in {y}=1", bool(good),
          f"(no disease {m[0]:.2f} vs disease {m[1]:.2f})")

# --- FHRS bands: mapping from the Adjusted FHRS (independent re-implementation) ---
for d in DIS:
    a = df[f"adjusted_fhrs_{d}"]
    expected = np.select([a <= 0.0, a < 1.76, a < 3.51, a <= 6.00], [0, 1, 2, 3], 4)
    mismatch = int((df[f"fhrs_band_{d}"].to_numpy() != expected).sum())
    check(f"FHRS  | fhrs_band_{d} matches Adjusted FHRS bands", mismatch == 0, f"(mismatches: {mismatch})")

# --- FHRS Band 0 = no documented familial risk (score exactly 0.0) ---
for d in DIS:
    band0 = base[f"fhrs_band_{d}"] == 0
    zero = base[f"bio_fhrs_{d}"] == 0.0
    check(f"FHRS  | fhrs_band_{d}: Band 0 ⇔ score 0.0", bool((band0 == zero).all()))

# --- FHRS bands: all five reachable ---
for d in DIS:
    counts = base[f"fhrs_band_{d}"].value_counts().reindex(range(5), fill_value=0)
    check(f"FHRS  | fhrs_band_{d} uses all 5 bands", bool((counts > 0).all()),
          f"{counts.to_dict()} (max adjusted FHRS: {base[f'adjusted_fhrs_{d}'].max():.2f})")

band0_share = (base["fhrs_band_cvd"] == 0).mean() * 100
print(f"ℹ️  Band 0 share (CVD, baseline): {band0_share:.1f}%")

print("=" * 50)
print("🏆 ALL FIX CHECKS PASSED" if ok else "🚨 SOME FIX CHECKS FAILED")
