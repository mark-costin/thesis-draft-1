"""Data preparation for the four CDSS disease heads (Chapter 3, §3.3 and §3.6.1).

Place at: experiment/src/ml/data.py
Run the self-check from the project root:
    uv run python -m experiment.src.ml.data

What this module does, in order:
  1. load_cohort()        read the frozen v11 cohort and verify its SHA-256
  2. add_derived()        missingness flags (M = 1 means missing) and biomarker velocity
  3. make_partitions()    one patient-level split shared by all heads: 70 / 7.5 / 7.5 / 15
  4. build_dataset()      features X, label y and patient groups for one head
  5. prune_by_missingness()  50% routine / 70% specialized rule, computed on training rows only
  6. make_cv_folds()      5-fold StratifiedGroupKFold over training rows, grouped by patient

The label is current-status risk (§3.6.1): y_d is constant per patient, so each patient's
maximum label is used for all of their encounters.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, train_test_split


# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

def find_project_root() -> Path:
    """Walk up from this file until a folder containing experiment/ is found."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "experiment").is_dir():
            return parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()
COHORT_PATH = PROJECT_ROOT / "experiment" / "data" / "raw" / "cohort.parquet"
PROCESSED_DIR = PROJECT_ROOT / "experiment" / "data" / "processed"
COHORT_SHA256 = "23d28b00c57b3895f914526d446e8623b4a96b8adc0996a51e6306821fbcb5e3"

SEED = 42
DISEASES = ["cvd", "t2d", "resp", "neuro"]
DAYS_PER_MONTH = 30.4375
MIN_VELOCITY_DAYS = 30          # §3.5.2: velocity is NaN when Δt < 30 days

# §3.6.1 domain feature masks (real cohort column names)
MASKS = {
    "cvd":   ["systolic_bp", "diastolic_bp", "resting_hr", "total_cholesterol",
              "hdl", "ldl", "tg", "egfr"],
    "t2d":   ["hba1c", "fpg", "bmi", "tg", "hdl"],
    "resp":  ["fev1", "fvc", "fev1_fvc_ratio", "spo2"],
    "neuro": ["mmse", "phq9", "gad7", "sleep_hours"],
}
SHARED_CORE = ["age", "biological_sex"]

# Cohort stores "<test>_measured" (1 = present). The thesis uses M = 1 for missing,
# so each flag below is converted to m_<test> = 1 - <test>_measured.
MEASURED_FLAG_FOR = {
    "total_cholesterol": "total_cholesterol_measured",
    "ldl": "ldl_measured",
    "tg": "tg_measured",
    "fpg": "fpg_measured",
    "bmi": "bmi_measured",
    "fev1": "spirometry_measured",          # spirometry is masked as one test
    "fvc": "spirometry_measured",
    "fev1_fvc_ratio": "spirometry_measured",
    "spo2": "spo2_measured",
    "phq9": "phq9_measured",
    "gad7": "gad7_measured",
}

# §3.3.2 missingness thresholds
SPECIALIZED = {"fev1", "fvc", "fev1_fvc_ratio", "spo2", "phq9", "gad7"}
ROUTINE_MAX_MISSING = 0.50
SPECIALIZED_MAX_MISSING = 0.70


# ---------------------------------------------------------------------------
# 1. Load
# ---------------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cohort(path: Path = COHORT_PATH, verify: bool = True) -> pd.DataFrame:
    """Read the frozen cohort. Refuses to continue if the file is not the frozen v11 version."""
    if verify:
        digest = sha256_of(path)
        if digest != COHORT_SHA256:
            raise ValueError(f"Cohort SHA-256 mismatch.\n  expected {COHORT_SHA256}\n  got      {digest}")
    df = pd.read_parquet(path)
    if df["patient_id"].nunique() != 15000 or len(df) != 23996:
        raise ValueError(f"Unexpected cohort size: {len(df)} rows, {df['patient_id'].nunique()} patients")
    return df.sort_values(["patient_id", "days_since_baseline"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. Derived columns: missingness flags and velocity
# ---------------------------------------------------------------------------

def varying_markers(df: pd.DataFrame, min_share: float = 0.01) -> list[str]:
    """Mask features whose value changes between visits for at least `min_share` of multi-visit patients.

    Markers that are constant per patient (e.g. diastolic BP in v11) get no velocity column,
    because their velocity would always be 0.
    """
    multi = df[df.groupby("patient_id")["patient_id"].transform("size") > 1]
    candidates = sorted({c for cols in MASKS.values() for c in cols})
    out = []
    for c in candidates:
        changes = multi.groupby("patient_id")[c].nunique(dropna=True) > 1
        if changes.mean() >= min_share:
            out.append(c)
    return out


def add_derived(df: pd.DataFrame, velocity_markers: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Add m_<test> flags and v_<marker> velocity columns. Returns (df, velocity_markers)."""
    df = df.copy()

    for flag in sorted(set(MEASURED_FLAG_FOR.values())):
        df["m_" + flag.removesuffix("_measured")] = 1 - df[flag].astype(int)

    if velocity_markers is None:
        velocity_markers = varying_markers(df)

    first_day = df.groupby("patient_id")["days_since_baseline"].transform("min")
    dt_days = df["days_since_baseline"] - first_day
    dt_months = dt_days / DAYS_PER_MONTH
    too_soon = dt_days < MIN_VELOCITY_DAYS

    first_row = df["days_since_baseline"] == first_day
    for c in velocity_markers:
        # B_0 = the value at the patient's first visit; stays NaN if that test was not done then.
        b0 = df[c].where(first_row).groupby(df["patient_id"]).transform("first")
        v = (df[c] - b0) / dt_months
        v[too_soon] = np.nan
        df["v_" + c] = v

    # One shared flag: velocity not available (first visit or Δt < 30 days)
    df["m_velocity"] = too_soon.astype(int)
    return df, velocity_markers


# ---------------------------------------------------------------------------
# 3. Labels and partitions
# ---------------------------------------------------------------------------

def patient_labels(df: pd.DataFrame) -> pd.DataFrame:
    """One row per patient: maximum label per disease (§3.6.1 label consistency)."""
    return df.groupby("patient_id")[[f"y_{d}" for d in DISEASES]].max().astype(int)


def make_partitions(df: pd.DataFrame, seed: int = SEED) -> pd.Series:
    """Assign every patient to train / calib_iso / calib_conf / holdout (70 / 7.5 / 7.5 / 15).

    One split is shared by all four heads, stratified on the combination of the four labels.
    Returns a Series indexed by patient_id.
    """
    labels = patient_labels(df)
    full_key = labels.astype(str).agg("".join, axis=1)   # e.g. "0100" = T2D only

    def safe_key(ids: np.ndarray, min_count: int = 6) -> pd.Series:
        """Stratification key for this subset: small label combinations are pooled so every
        class has enough members to appear on both sides of the split."""
        key = full_key.loc[ids]
        counts = key.value_counts()
        key = key.where(key.map(counts) >= min_count, "rare")
        if (key == "rare").sum() < min_count:          # pool too small: merge into the largest class
            key = key.replace("rare", key.value_counts().index[0])
        return key

    ids = labels.index.to_numpy()
    train, rest = train_test_split(ids, test_size=0.30, stratify=safe_key(ids), random_state=seed)
    calib, holdout = train_test_split(rest, test_size=0.50, stratify=safe_key(rest), random_state=seed)
    calib_iso, calib_conf = train_test_split(calib, test_size=0.50, stratify=safe_key(calib), random_state=seed)

    part = pd.Series("", index=labels.index, name="partition")
    part.loc[train] = "train"
    part.loc[calib_iso] = "calib_iso"
    part.loc[calib_conf] = "calib_conf"
    part.loc[holdout] = "holdout"
    return part


def save_partitions(part: pd.Series, path: Path | None = None) -> Path:
    """Write the patient → partition table so every later step uses the same split."""
    path = path or PROCESSED_DIR / "partitions.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    part.rename_axis("patient_id").reset_index().to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# 4. Per-head dataset
# ---------------------------------------------------------------------------

def feature_columns(disease: str, velocity_markers: list[str]) -> list[str]:
    mask = MASKS[disease]
    flags = sorted({"m_" + MEASURED_FLAG_FOR[c].removesuffix("_measured") for c in mask if c in MEASURED_FLAG_FOR})
    velocity = [f"v_{c}" for c in mask if c in velocity_markers]
    cols = (SHARED_CORE + mask + [f"adjusted_fhrs_{disease}", f"fhrs_band_{disease}"]
            + flags + velocity + (["m_velocity"] if velocity else []))
    return list(dict.fromkeys(cols))      # keep order, drop duplicates


def build_dataset(df: pd.DataFrame, disease: str, part: pd.Series,
                  velocity_markers: list[str]) -> dict:
    """Return X, y, groups and partition label for every encounter, for one disease head.

    bio_fhrs_* is deliberately excluded: the generator uses it to make labels (§3.7.2).
    """
    cols = feature_columns(disease, velocity_markers)
    y_patient = patient_labels(df)[f"y_{disease}"]
    return {
        "X": df[cols].astype(float),
        "y": df["patient_id"].map(y_patient).astype(int),
        "groups": df["patient_id"],
        "partition": df["patient_id"].map(part),
        "feature_columns": cols,
    }


# ---------------------------------------------------------------------------
# 5. Missingness pruning (training rows only)
# ---------------------------------------------------------------------------

def prune_by_missingness(X: pd.DataFrame, is_train: pd.Series) -> tuple[list[str], dict]:
    """Drop test features missing above 50% (routine) or 70% (specialized) on training rows.

    Velocity columns are exempt: they are missing by design at every first visit, not because a
    test was skipped. Returns (kept_columns, missing_rate_per_column).
    """
    rates = X.loc[is_train].isna().mean().to_dict()
    kept = []
    for c in X.columns:
        if c.startswith("v_") or c.startswith("m_") or rates[c] == 0:
            kept.append(c)
            continue
        limit = SPECIALIZED_MAX_MISSING if c in SPECIALIZED else ROUTINE_MAX_MISSING
        if rates[c] <= limit:
            kept.append(c)
    return kept, rates


# ---------------------------------------------------------------------------
# 6. Cross-validation folds
# ---------------------------------------------------------------------------

def make_cv_folds(y_train: pd.Series, groups_train: pd.Series, n_splits: int = 5, seed: int = SEED):
    """5-fold StratifiedGroupKFold over training ROWS, grouped by patient.

    Returns a list of (train_idx, valid_idx) positional index arrays into y_train.
    """
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    dummy = np.zeros(len(y_train))
    return list(cv.split(dummy, y_train.to_numpy(), groups=groups_train.to_numpy()))


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def run_checks(df: pd.DataFrame, verbose: bool = True) -> None:
    df, vel = add_derived(df)
    part = make_partitions(df)

    # Every patient in exactly one partition
    assert part.notna().all() and (part != "").all(), "Some patients have no partition"
    counts = part.value_counts()
    share = (counts / counts.sum()).round(3)

    # No patient's encounters split across partitions
    row_part = df["patient_id"].map(part)
    assert (df.assign(p=row_part).groupby("patient_id")["p"].nunique() == 1).all(), "Patient leak"

    # Missingness flag direction matches the thesis (M = 1 means missing)
    assert ((df["m_fpg"] == 1) == df["fpg"].isna()).all(), "m_fpg does not mean 'missing'"

    if verbose:
        print("Velocity markers (change between visits):", vel)
        print("Partition sizes (patients):", counts.to_dict(), " shares:", share.to_dict())

    for d in DISEASES:
        ds = build_dataset(df, d, part, vel)
        is_train = ds["partition"] == "train"
        kept, rates = prune_by_missingness(ds["X"], is_train)
        dropped = [c for c in ds["X"].columns if c not in kept]
        folds = make_cv_folds(ds["y"][is_train], ds["groups"][is_train])

        # Folds never split a patient
        g = ds["groups"][is_train].to_numpy()
        for tr, va in folds:
            assert not set(g[tr]) & set(g[va]), "Patient appears in both sides of a fold"

        if verbose:
            prev = ds["y"].groupby(ds["partition"]).mean().round(3).to_dict()
            print(f"\n[{d}] {len(ds['feature_columns'])} features, dropped by missingness rule: {dropped or 'none'}")
            print(f"     features: {kept}")
            print(f"     row prevalence by partition: {prev}")
            print(f"     CV folds: {len(folds)}, validation rows per fold: {[len(va) for _, va in folds]}")

    if verbose:
        print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    cohort = load_cohort()
    run_checks(cohort)
    print("Partitions saved to:", save_partitions(make_partitions(add_derived(cohort)[0])))