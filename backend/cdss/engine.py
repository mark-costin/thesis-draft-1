"""Inference for one disease head: features -> calibrated risk, tier, conformal set, reasons.

Features are built with the training pipeline's own `data.py` (missingness flags, velocity), so the
backend computes every input exactly as training did.

Payload (one encounter), keys named as in the cohort:
    {"age": 61, "biological_sex": 1, "hba1c": 7.4, "bmi": 31.0, ...,
     "adjusted_fhrs_t2d": 2.1, "fhrs_band_t2d": 3,
     "days_since_baseline": 365,                    # optional: days since the patient's first visit
     "baseline": {"hba1c": 6.9, "bmi": 30.0}}       # optional: first-visit values, for velocity
A test that was not done is simply left out (or sent as null).
"""

from __future__ import annotations

import importlib
import math
import sys

import numpy as np
import pandas as pd

from backend.cdss.explain import compute_shap_drivers
from backend.cdss.model_loader import PROJECT_ROOT, LoadedHead, ModelRegistry, get_registry

REQUIRED = ["age", "biological_sex"]
SET_LABELS = {(0,): "ruled out", (0, 1): "uncertain", (1,): "flagged", (): "no label"}


def _ml(name: str):
    """Import a module from experiment/src/ml (data.py, train.py)."""
    ml_dir = str(PROJECT_ROOT / "experiment" / "src" / "ml")
    if ml_dir not in sys.path:
        sys.path.insert(0, ml_dir)
    return importlib.import_module(name)


def tier_label(p: float, cutoffs) -> str:
    lo, hi = cutoffs
    return "LOW" if p < lo else ("MODERATE" if p < hi else "HIGH")


def display_score(p: float) -> float:
    """Percentage shown to the user, capped at 99 (isotonic calibration can output exactly 1.0)."""
    return min(round(p * 100, 2), 99.0)


def _number(name: str, value) -> float:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{name}' must be a number, got {value!r}") from None


def build_features(payload: dict, head: LoadedHead):
    """Return (feature names, one-row DataFrame) in the order the head was trained on."""
    D = _ml("data")
    for name in REQUIRED:
        if math.isnan(_number(name, payload.get(name))):
            raise ValueError(f"'{name}' is required")

    raw_cols = sorted(set(D.SHARED_CORE) | {c for cols in D.MASKS.values() for c in cols}
                      | {c for c in head.feature_columns if not c.startswith(("m_", "v_"))})
    current = {c: _number(c, payload.get(c)) for c in raw_cols}

    rows = []
    days = payload.get("days_since_baseline")
    baseline = payload.get("baseline") or {}
    if baseline and days is not None:
        first = {c: math.nan for c in raw_cols}
        first.update({c: _number(f"baseline.{c}", baseline.get(c)) for c in head.velocity_markers})
        rows.append({**first, "days_since_baseline": 0})
        rows.append({**current, "days_since_baseline": int(days)})
    else:
        rows.append({**current, "days_since_baseline": 0})

    for row in rows:
        row["patient_id"] = "request"
        for flag in set(D.MEASURED_FLAG_FOR.values()):
            tests = [t for t, f in D.MEASURED_FLAG_FOR.items() if f == flag]
            row[flag] = int(any(not math.isnan(row[t]) for t in tests))

    derived, _ = D.add_derived(pd.DataFrame(rows), head.velocity_markers)
    X = derived.iloc[[-1]][head.feature_columns].astype(float).reset_index(drop=True)
    return list(head.feature_columns), X


def evaluate_biomarkers(disease: str, payload: dict, registry: ModelRegistry | None = None) -> dict:
    """Run one disease head on one encounter."""
    head = (registry or get_registry()).load(disease)

    if head.source != "model":
        return {"score": None, "probability": None, "tier": "UNAVAILABLE", "conformal_set": None,
                "conformal_label": None, "uncertain": None, "drivers": [], "missing_inputs": [],
                "model_version": head.model_version, "model_source": "stub", "reason": head.reason}

    names, X = build_features(payload, head)
    p = float(head.calibrated.predict_proba(X)[0, 1])
    s = _ml("train").prediction_set(p, head.q_hat)
    raw_inputs = [c for c in names if not c.startswith(("m_", "v_"))]
    return {
        "score": display_score(p),
        "probability": p,
        "tier": tier_label(p, head.tier_cutoffs),
        "conformal_set": s,
        "conformal_label": SET_LABELS[tuple(s)],
        "uncertain": s == [0, 1],
        "drivers": compute_shap_drivers(head.raw, X, names),
        "missing_inputs": [c for c in raw_inputs if np.isnan(X.at[0, c])],
        "model_version": head.model_version,
        "model_source": "model",
        "reason": None,
    }