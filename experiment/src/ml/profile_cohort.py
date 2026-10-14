"""Profile the frozen v11 cohort before building the ML pipeline.

Place at: experiment/src/ml/profile_cohort.py
Run from the project root:
    uv run python experiment/src/ml/profile_cohort.py
or pass a path:
    uv run python experiment/src/ml/profile_cohort.py path/to/cohort.parquet

Paste the full output back into the chat. It decides the prediction horizon,
how labels are built, and which features exist.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd


def find_project_root() -> Path:
    """Walk up from this file until a folder containing experiment/ is found."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "experiment").is_dir():
            return parent
    return Path.cwd()


DEFAULT_PATH = find_project_root() / "experiment" / "data" / "raw" / "cohort.parquet"
DISEASES = ["cvd", "t2d", "resp", "neuro"]

# Inputs the thesis or the derived-feature formulas expect. Missing ones are reported, not errors.
EXPECTED = {
    "ids/time": ["patient_id", "days_since_baseline", "delta_time_months", "record_type"],
    "demographics": ["age", "biological_sex", "race", "ethnicity"],
    "cvd": ["systolic_bp", "diastolic_bp", "total_cholesterol", "hdl", "ldl", "tg",
            "resting_hr", "troponin", "creatinine", "egfr", "bp_treated", "smoker", "pack_years"],
    "t2d": ["hba1c", "fpg", "fasting_insulin", "bmi", "waist_cm", "hip_cm", "waist_hip_ratio",
            "physical_activity", "vegetables_daily", "antihypertensive_meds", "history_high_glucose"],
    "resp": ["fev1", "fvc", "fev1_fvc_ratio", "spo2", "eosinophils", "feno"],
    "neuro": ["mmse", "moca", "phq9", "gad7", "sleep_hours", "tsh", "cortisol", "b12"],
}


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    df = pd.read_parquet(path)

    section("1. Shape")
    print(f"path: {path}")
    print(f"rows: {len(df):,}   columns: {df.shape[1]}")
    if "patient_id" in df.columns:
        print(f"patients: {df['patient_id'].nunique():,}")

    section("2. Columns (dtype, % missing, n unique)")
    summary = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "missing_%": (df.isna().mean() * 100).round(1),
        "n_unique": df.nunique(),
    })
    with pd.option_context("display.max_rows", 200, "display.width", 120):
        print(summary)

    section("3. Expected inputs that are missing")
    for group, cols in EXPECTED.items():
        absent = [c for c in cols if c not in df.columns]
        print(f"{group:13s} missing: {absent if absent else 'none'}")

    if "patient_id" not in df.columns:
        print("\nNo patient_id column; stopping.")
        return

    section("4. Visits per patient")
    visits = df.groupby("patient_id").size()
    print(visits.value_counts().sort_index().to_string())
    print(f"mean visits per patient: {visits.mean():.2f}")

    section("5. Follow-up length (needed to choose the horizon)")
    time_col = next((c for c in ["days_since_baseline", "delta_time_months"] if c in df.columns), None)
    if time_col is None:
        print("No time column found.")
    else:
        fu = df.groupby("patient_id")[time_col].max()
        months = fu / 30.4375 if time_col == "days_since_baseline" else fu
        print(f"time column: {time_col}")
        print("follow-up in months, quantiles:")
        print(months.quantile([0, 0.1, 0.25, 0.5, 0.75, 0.9, 1]).round(1).to_string())
        for h in [12, 24, 36, 48, 60]:
            print(f"patients with >= {h:2d} months follow-up: {(months >= h).mean() * 100:5.1f}%")
        gaps = df.sort_values(["patient_id", time_col]).groupby("patient_id")[time_col].diff().dropna()
        if len(gaps):
            g = gaps / 30.4375 if time_col == "days_since_baseline" else gaps
            print(f"gap between visits (months): median {g.median():.1f}, "
                  f"share < 1 month: {(g < 1).mean() * 100:.1f}%")

    section("6. Labels: what do the y_* columns mean?")
    for d in DISEASES:
        col = f"y_{d}"
        if col not in df.columns:
            print(f"{col}: NOT FOUND")
            continue
        vals = df[col].value_counts(dropna=False).to_dict()
        per_patient_unique = df.groupby("patient_id")[col].nunique(dropna=False)
        varies = (per_patient_unique > 1).mean() * 100
        patient_prev = df.groupby("patient_id")[col].max().mean() * 100
        print(f"{col}: values {vals}")
        print(f"   row prevalence {df[col].mean() * 100:.1f}%   patient prevalence {patient_prev:.1f}%")
        print(f"   patients whose label changes between visits: {varies:.1f}%  "
              f"({'per-visit status' if varies > 0 else 'one label per patient'})")
        if varies > 0 and time_col:
            first = df[df[col] == 1].groupby("patient_id")[time_col].min()
            at_baseline = (first == df.groupby("patient_id")[time_col].min().loc[first.index]).mean() * 100
            print(f"   first positive already at first visit: {at_baseline:.1f}% of positive patients")

    section("7. FHRS columns")
    for d in DISEASES:
        for prefix in ["bio_fhrs", "adjusted_fhrs", "fhrs_band", "household_exposure"]:
            col = f"{prefix}_{d}"
            if col not in df.columns:
                print(f"{col}: NOT FOUND")
            elif prefix == "fhrs_band":
                print(f"{col}: {df[col].value_counts(dropna=False).sort_index().to_dict()}")
            else:
                s = df[col]
                print(f"{col}: min {s.min():.3f}  median {s.median():.3f}  max {s.max():.3f}  "
                      f"zeros {(s == 0).mean() * 100:.1f}%")
        if f"fhrs_band_{d}" in df.columns:
            const = (df.groupby("patient_id")[f"fhrs_band_{d}"].nunique() > 1).mean() * 100
            print(f"   patients whose band changes between visits: {const:.1f}% (expect ~0 unless re-anchored)")

    section("8. Missingness flags")
    flags = [c for c in df.columns if c.endswith("_measured") or c.startswith("m_") or c.endswith("_missing")]
    if not flags:
        print("No flag columns found.")
    for c in flags:
        base = c.replace("_measured", "").replace("_missing", "").removeprefix("m_")
        mean = df[c].mean()
        agree = ""
        if base in df.columns:
            agree_val = ((df[c] == 1) == df[base].notna()).mean() * 100
            agree = f"   flag==1 when value present: {agree_val:.1f}% (100 = 'measured', 0 = 'missing')"
        print(f"{c}: mean {mean:.3f}{agree}")

    section("9. Units spot-check")
    for c in ["fev1_fvc_ratio", "hba1c", "fpg", "bmi", "spo2", "age"]:
        if c in df.columns:
            s = df[c].dropna()
            print(f"{c}: min {s.min():.2f}  median {s.median():.2f}  max {s.max():.2f}")

    print("\nDone. Paste everything above into the chat.")


if __name__ == "__main__":
    main()