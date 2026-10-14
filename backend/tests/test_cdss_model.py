"""The backend must serve the trained heads exactly as the training pipeline built them.

Run from the project root:  uv run pytest backend/tests/test_cdss_model_connection.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_DIR = PROJECT_ROOT / "experiment" / "src" / "ml"
for p in (str(PROJECT_ROOT), str(ML_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import data as D   # noqa: E402  (the training pipeline's own modules)
import train as T  # noqa: E402

VEL = ["bmi", "egfr", "hba1c", "systolic_bp"]


def make_t2d_bundle(outdir: Path) -> dict:
    """Train a small T2D head on synthetic rows and save it exactly as train.py does."""
    rng = np.random.default_rng(0)
    cols = D.feature_columns("t2d", VEL)
    n = 2400
    X = pd.DataFrame(rng.normal(size=(n, len(cols))), columns=cols)
    X["age"] = rng.integers(18, 90, n)
    X["biological_sex"] = rng.integers(0, 2, n)
    X["hba1c"] = rng.normal(5.8, 0.8, n)
    y = pd.Series((rng.random(n) < 1 / (1 + np.exp(-(X["hba1c"] - 6.3) * 3))).astype(int))
    groups = pd.Series([f"P{i}" for i in range(n)])
    tr, cal, conf = slice(0, 1200), slice(1200, 1800), slice(1800, n)
    raw = T.make_model({"n_estimators": 30, "max_depth": 2, "learning_rate": 0.3}).fit(X[tr], y[tr])
    calibrated, method, _ = T.calibrate(raw, X[cal], y[cal], groups[cal])
    q_hat = T.mondrian_thresholds(calibrated.predict_proba(X[conf])[:, 1], y[conf].to_numpy())
    bundle = {"disease": "t2d", "model_version": "v1", "calibrated": calibrated, "raw": raw,
              "q_hat": q_hat, "tier_cutoffs": T.TIER_CUTOFFS, "feature_columns": cols,
              "velocity_markers": VEL}
    record = {"disease": "t2d", "model_version": "v1", "feature_columns": cols,
              "calibration_method": method}
    T.save_bundle("t2d", bundle, record, outdir=outdir)
    return bundle


@pytest.fixture
def model_dir(tmp_path):
    make_t2d_bundle(tmp_path)
    return tmp_path


@pytest.fixture
def registry(model_dir):
    from backend.cdss.model_loader import ModelRegistry
    return ModelRegistry(model_dir=model_dir)


@pytest.fixture
def payload():
    """One T2D encounter as the frontend would send it (fpg not done)."""
    return {"age": 61, "biological_sex": 1, "hba1c": 7.4, "bmi": 31.0, "tg": 190.0,
            "hdl": 42.0, "adjusted_fhrs_t2d": 2.1, "fhrs_band_t2d": 3}

import json  # noqa: E402
import math  # noqa: E402


# --------------------------------------------------------------------------- model_loader

def test_default_model_dir_is_experiment_data_models(monkeypatch):
    monkeypatch.delenv("CDSS_MODEL_DIR", raising=False)
    from backend.cdss.model_loader import resolve_model_dir
    assert resolve_model_dir() == PROJECT_ROOT / "experiment" / "data" / "models"


def test_env_variable_overrides_model_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CDSS_MODEL_DIR", str(tmp_path))
    from backend.cdss.model_loader import resolve_model_dir
    assert resolve_model_dir() == tmp_path


def test_verified_bundle_loads_as_real_model(registry):
    head = registry.load("t2d")
    assert head.source == "model"
    assert head.feature_columns == D.feature_columns("t2d", ["bmi", "egfr", "hba1c", "systolic_bp"])
    assert head.raw is not None and head.q_hat is not None


def test_bundle_with_wrong_fingerprint_falls_back_to_stub(model_dir):
    rec_path = model_dir / "t2d_head_latest.json"
    rec = json.loads(rec_path.read_text())
    rec["artifact_sha256"] = "0" * 64
    rec_path.write_text(json.dumps(rec))
    from backend.cdss.model_loader import ModelRegistry
    head = ModelRegistry(model_dir=model_dir).load("t2d")
    assert head.source == "stub"
    assert "sha256" in head.reason.lower()


def test_missing_bundle_falls_back_to_stub(registry):
    head = registry.load("cvd")
    assert head.source == "stub"
    assert "not found" in head.reason.lower()


def test_status_marks_only_verified_heads_as_loaded(registry):
    status = registry.status()
    assert status["t2d"]["loaded"] is True
    assert status["cvd"]["loaded"] is False


def test_engine_and_reload_share_one_registry():
    from backend.cdss import engine
    from backend.cdss.model_loader import get_registry
    assert engine.get_registry() is get_registry()


# --------------------------------------------------------------------------- features

def test_missing_test_sets_its_missingness_flag(registry, payload):
    from backend.cdss.engine import build_features
    names, X = build_features(payload, registry.load("t2d"))
    row = dict(zip(names, X.iloc[0]))
    assert row["m_fpg"] == 1 and math.isnan(row["fpg"])
    assert row["m_tg"] == 0 and row["m_bmi"] == 0


def test_velocity_is_change_per_month_since_baseline(registry, payload):
    from backend.cdss.engine import build_features
    p = {**payload, "days_since_baseline": 365, "baseline": {"hba1c": 6.9, "bmi": 30.0}}
    names, X = build_features(p, registry.load("t2d"))
    row = dict(zip(names, X.iloc[0]))
    assert row["v_hba1c"] == pytest.approx((7.4 - 6.9) / (365 / D.DAYS_PER_MONTH))
    assert row["m_velocity"] == 0


def test_velocity_is_missing_at_first_visit(registry, payload):
    from backend.cdss.engine import build_features
    names, X = build_features(payload, registry.load("t2d"))
    row = dict(zip(names, X.iloc[0]))
    assert math.isnan(row["v_hba1c"]) and row["m_velocity"] == 1


def test_missing_age_is_rejected(registry, payload):
    from backend.cdss.engine import build_features
    p = {k: v for k, v in payload.items() if k != "age"}
    with pytest.raises(ValueError, match="age"):
        build_features(p, registry.load("t2d"))


def test_text_in_a_numeric_field_is_rejected(registry, payload):
    from backend.cdss.engine import build_features
    with pytest.raises(ValueError, match="hba1c"):
        build_features({**payload, "hba1c": "high"}, registry.load("t2d"))


# --------------------------------------------------------------------------- inference

def test_score_tier_and_set_come_from_the_calibrated_model(registry, payload):
    from backend.cdss.engine import build_features, evaluate_biomarkers
    head = registry.load("t2d")
    _, X = build_features(payload, head)
    p = float(head.calibrated.predict_proba(X)[0, 1])
    out = evaluate_biomarkers("t2d", payload, registry=registry)
    assert out["probability"] == pytest.approx(p)
    assert out["score"] == pytest.approx(min(round(p * 100, 2), 99.0))
    assert out["conformal_set"] == T.prediction_set(p, head.q_hat)
    assert out["model_source"] == "model"


@pytest.mark.parametrize("p, tier", [(0.19, "LOW"), (0.20, "MODERATE"), (0.49, "MODERATE"), (0.50, "HIGH")])
def test_tiers_follow_chapter_3_cutoffs(p, tier):
    from backend.cdss.engine import tier_label
    assert tier_label(p, [0.20, 0.50]) == tier


def test_displayed_score_never_shows_100_percent():
    from backend.cdss.engine import display_score
    assert display_score(1.0) == 99.0
    assert display_score(0.064) == 6.4


def test_stub_result_is_flagged_not_moderate(registry, payload):
    from backend.cdss.engine import evaluate_biomarkers
    out = evaluate_biomarkers("cvd", payload, registry=registry)
    assert out["model_source"] == "stub"
    assert out["tier"] == "UNAVAILABLE"


def test_inputs_not_sent_are_listed(registry, payload):
    from backend.cdss.engine import evaluate_biomarkers
    out = evaluate_biomarkers("t2d", payload, registry=registry)
    assert "fpg" in out["missing_inputs"]
    assert "hba1c" not in out["missing_inputs"]


# --------------------------------------------------------------------------- explanations

def test_drivers_come_from_the_raw_model_and_add_up(registry, payload):
    from backend.cdss.engine import build_features
    from backend.cdss.explain import shap_contributions, compute_shap_drivers
    head = registry.load("t2d")
    names, X = build_features(payload, head)
    phi, base = shap_contributions(head.raw, X)
    margin = head.raw.get_booster().predict(__import__("xgboost").DMatrix(X), output_margin=True)[0]
    assert phi.sum() + base == pytest.approx(float(margin), rel=1e-4, abs=1e-4)
    drivers = compute_shap_drivers(head.raw, X, names, top_k=3)
    assert len(drivers) == 3
    assert abs(drivers[0]["shap_value"]) >= abs(drivers[-1]["shap_value"])
    assert "SHAP Unavailable" not in [d["display_name"] for d in drivers]


# --------------------------------------------------------------------------- real models (your machine)

REAL_DIR = PROJECT_ROOT / "experiment" / "data" / "models"
REAL_READY = (REAL_DIR / "t2d_head_latest.joblib").exists() and D.COHORT_PATH.exists()


@pytest.mark.skipif(not REAL_READY, reason="real models or cohort not on this machine")
def test_backend_matches_training_pipeline_on_real_patients():
    """Backend features + prediction equal the notebook's for real cohort visits, all four heads."""
    from backend.cdss.model_loader import ModelRegistry
    from backend.cdss.engine import evaluate_biomarkers
    reg = ModelRegistry(model_dir=REAL_DIR)
    cohort = D.load_cohort()
    for d in D.DISEASES:
        head = reg.load(d)
        assert head.source == "model", f"{d}: {head.reason}"
        derived, _ = D.add_derived(cohort, head.velocity_markers)
        later = cohort.index[cohort["visit_number"] == 3][:5].tolist()
        for i in [0, 1, 2] + later:
            r = cohort.loc[i]
            first = cohort[cohort["patient_id"] == r["patient_id"]].iloc[0]
            payload = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
            payload["days_since_baseline"] = int(r["days_since_baseline"] - first["days_since_baseline"])
            payload["baseline"] = {c: first[c] for c in head.velocity_markers if c in first}
            expected = float(head.calibrated.predict_proba(derived.loc[[i], head.feature_columns].astype(float))[0, 1])
            out = evaluate_biomarkers(d, payload, registry=reg)
            assert out["probability"] == pytest.approx(expected, abs=1e-9), f"{d} row {i}"