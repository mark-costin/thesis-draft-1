"""Train, calibrate and save one disease head (Chapter 3, §3.3.4 and §3.6.2–3.6.4).

Place at: experiment/src/ml/train.py
Smoke test (5 trials, a few minutes):
    uv run python experiment/src/ml/train.py --disease cvd --trials 5
Full run (100 trials, as in the paper):
    uv run python experiment/src/ml/train.py --disease cvd --trials 100

Steps for one head:
  1. Build the dataset from data.py (features, labels, patient partitions).
  2. Optuna searches XGBoost settings on the 70% training partition with 5 patient-grouped folds,
     minimising L = 0.35(1-AUROC) + 0.25(1-AUPRC) + 0.20 ECE + 0.10 Brier + 0.10 ΔAUROC_subgroup.
     ECE and Brier are measured after an in-fold isotonic calibration (§3.6.4).
  3. Refit the best settings on all training rows.
  4. Calibrate on calib_iso (7.5%): isotonic, or sigmoid if < 1,000 rows or < 100 positive patients.
  5. Fit Mondrian conformal thresholds q̂0, q̂1 on calib_conf (7.5%), α = 0.10.
  6. Save one bundle (calibrated model, raw model, thresholds, feature list) + a JSON record.

The holdout partition is never touched here; evaluate.py scores it once at the end.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

try:                                    # run as a module (python -m experiment.src.ml.train)
    from . import data as D
except ImportError:                     # run as a script (python experiment/src/ml/train.py)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import data as D

MODELS_DIR = D.PROJECT_ROOT / "experiment" / "data" / "models"
MLRUNS_DIR = D.PROJECT_ROOT / "experiment" / "mlruns"
MLFLOW_EXPERIMENT = "cdss-disease-heads"
MODEL_VERSION = "v1"
ALPHA = 0.10
TIER_CUTOFFS = [0.20, 0.50]
LOSS_WEIGHTS = {"auroc": 0.35, "auprc": 0.25, "ece": 0.20, "brier": 0.10, "subgroup": 0.10}
ISOTONIC_MIN_ROWS = 1000
ISOTONIC_MIN_POS_PATIENTS = 100
AGE_BRACKETS = [(18, 44), (45, 64), (65, 100)]


# ---------------------------------------------------------------------------
# Model factory (the only place XGBoost is named, so tests can swap it)
# ---------------------------------------------------------------------------

def make_model(params: dict):
    from xgboost import XGBClassifier
    return XGBClassifier(**params, tree_method="hist", eval_metric="logloss",
                         random_state=D.SEED, n_jobs=-1)


def suggest_params(trial, neg_pos_ratio: float) -> dict:
    return {
        "n_estimators":     trial.suggest_int("n_estimators", 100, 1000, step=50),
        "max_depth":        trial.suggest_int("max_depth", 2, 8),
        "learning_rate":    trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 20.0, log=True),
        "reg_lambda":       trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        "gamma":            trial.suggest_float("gamma", 0.0, 5.0),
        # §3.3.4: start at the class ratio, tuned within a bounded range
        "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, max(1.0, 2 * neg_pos_ratio)),
    }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def ece(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> float:
    """Expected calibration error over equal-frequency bins (deciles)."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    order = np.argsort(p, kind="stable")
    total = 0.0
    for idx in np.array_split(order, n_bins):
        if len(idx):
            total += len(idx) / len(p) * abs(y[idx].mean() - p[idx].mean())
    return float(total)


def subgroup_auroc_gap(y, p, sex, age) -> float:
    """Largest AUROC gap within sex, and within the three age brackets; the larger of the two (§3.7.1)."""
    y, p, sex, age = map(np.asarray, (y, p, sex, age))
    gaps = []
    groups_by_attr = [
        [sex == s for s in np.unique(sex)],
        [(age >= lo) & (age <= hi) for lo, hi in AGE_BRACKETS],
    ]
    for groups in groups_by_attr:
        aucs = [roc_auc_score(y[g], p[g]) for g in groups if g.sum() >= 50 and len(np.unique(y[g])) == 2]
        if len(aucs) >= 2:
            gaps.append(max(aucs) - min(aucs))
    return float(max(gaps)) if gaps else 0.0


def scalarized_loss(m: dict) -> float:
    w = LOSS_WEIGHTS
    return (w["auroc"] * (1 - m["auroc"]) + w["auprc"] * (1 - m["auprc"]) + w["ece"] * m["ece"]
            + w["brier"] * m["brier"] + w["subgroup"] * m["subgroup_gap"])


# ---------------------------------------------------------------------------
# Optuna objective
# ---------------------------------------------------------------------------

def cv_metrics(params: dict, X: pd.DataFrame, y: pd.Series, groups: pd.Series, folds) -> dict:
    """Average metrics over the CV folds. Within each fold, 20% of the fold's training patients
    fit an isotonic calibrator, so ECE and Brier are measured on calibrated probabilities."""
    per_fold = []
    for tr, va in folds:
        X_tr, y_tr, g_tr = X.iloc[tr], y.iloc[tr], groups.iloc[tr]
        X_va, y_va = X.iloc[va], y.iloc[va]

        inner = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=D.SEED)
        fit_idx, cal_idx = next(inner.split(X_tr, y_tr, groups=g_tr))
        model = make_model(params).fit(X_tr.iloc[fit_idx], y_tr.iloc[fit_idx])

        p_raw = model.predict_proba(X_va)[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)
        iso.fit(model.predict_proba(X_tr.iloc[cal_idx])[:, 1], y_tr.iloc[cal_idx])
        p_cal = iso.predict(p_raw)

        per_fold.append({
            "auroc": roc_auc_score(y_va, p_raw),
            "auprc": average_precision_score(y_va, p_raw),
            "ece": ece(y_va, p_cal),
            "brier": brier_score_loss(y_va, p_cal),
            "subgroup_gap": subgroup_auroc_gap(y_va, p_raw, X_va["biological_sex"], X_va["age"]),
        })
    return {k: float(np.mean([f[k] for f in per_fold])) for k in per_fold[0]}


def tune(X, y, groups, folds, n_trials: int):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    neg_pos_ratio = float((y == 0).sum() / max((y == 1).sum(), 1))

    def objective(trial):
        params = suggest_params(trial, neg_pos_ratio)
        m = cv_metrics(params, X, y, groups, folds)
        for k, v in m.items():
            trial.set_user_attr(k, v)
        return scalarized_loss(m)

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=D.SEED))
    study.enqueue_trial({"scale_pos_weight": neg_pos_ratio})   # first trial starts at the class ratio
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    best = study.best_trial
    cv = {k: best.user_attrs[k] for k in ("auroc", "auprc", "ece", "brier", "subgroup_gap")}
    cv["loss"] = best.value
    history = pd.DataFrame([
        {"trial": t.number, "loss": t.value, **t.params, **t.user_attrs}
        for t in study.trials if t.value is not None
    ])
    return dict(best.params), cv, neg_pos_ratio, history


# ---------------------------------------------------------------------------
# Calibration and Mondrian conformal thresholds
# ---------------------------------------------------------------------------

def calibrate(model, X_cal, y_cal, groups_cal):
    """§3.6.2: isotonic unless the calibration half is small; then sigmoid (Platt)."""
    pos_patients = groups_cal[y_cal == 1].nunique()
    method = ("isotonic" if len(y_cal) >= ISOTONIC_MIN_ROWS and pos_patients >= ISOTONIC_MIN_POS_PATIENTS
              else "sigmoid")
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method=method)
    calibrated.fit(X_cal, y_cal)
    return calibrated, method, int(pos_patients)


def mondrian_thresholds(p1: np.ndarray, y: np.ndarray, alpha: float = ALPHA) -> dict:
    """Class-conditional split-conformal thresholds.

    Score for a candidate label k is s = 1 - p̂_k. For each class y, q̂_y is the
    ceil((n_y + 1)(1 - α))-th smallest score among calibration rows with that label.
    """
    out = {}
    for label in (0, 1):
        p_true = p1[y == label] if label == 1 else 1 - p1[y == label]
        scores = np.sort(1 - p_true)
        n = len(scores)
        k = int(np.ceil((n + 1) * (1 - alpha)))
        out[str(label)] = float(scores[min(k, n) - 1]) if n else 1.0
    return out


def prediction_set(p1: float, q_hat: dict) -> list[int]:
    """Labels whose score 1 - p̂_k is within that class's threshold."""
    s = []
    if 1 - (1 - p1) <= q_hat["0"]:      # label 0: p̂_0 = 1 - p1, score = p1
        s.append(0)
    if 1 - p1 <= q_hat["1"]:            # label 1: score = 1 - p1
        s.append(1)
    return s


def risk_tier(p1: float) -> str:
    lo, hi = TIER_CUTOFFS
    return "Low" if p1 < lo else ("Moderate" if p1 < hi else "High")


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    return D.sha256_of(path)


def save_bundle(disease: str, bundle: dict, record: dict, outdir: Path | None = None) -> dict:
    """Write {disease}_head_latest.joblib atomically, copy to _v1, and write matching JSON records."""
    outdir = Path(outdir or MODELS_DIR)
    outdir.mkdir(parents=True, exist_ok=True)
    latest = outdir / f"{disease}_head_latest.joblib"
    tmp = latest.with_suffix(".joblib.tmp")
    joblib.dump(bundle, tmp)
    os.replace(tmp, latest)                              # backend never sees a half-written file
    versioned = outdir / f"{disease}_head_{MODEL_VERSION}.joblib"
    shutil.copy2(latest, versioned)

    record = {**record, "artifact_sha256": sha256_file(latest)}
    for stem in (f"{disease}_head_latest", f"{disease}_head_{MODEL_VERSION}"):
        (outdir / f"{stem}.json").write_text(json.dumps(record, indent=2))
    return {"joblib": str(latest), "versioned": str(versioned), "sha256": record["artifact_sha256"]}


def library_versions() -> dict:
    out = {"python": platform.python_version()}
    for name in ("numpy", "pandas", "sklearn", "xgboost", "optuna", "joblib"):
        try:
            out[name] = __import__(name).__version__
        except Exception:
            out[name] = None
    return out


def log_mlflow(disease: str, params: dict, cv: dict, extra: dict) -> None:
    try:
        import mlflow
    except ImportError:
        print("mlflow not installed; skipping run log")
        return
    MLRUNS_DIR.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DIR / 'mlflow.db'}")
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    with mlflow.start_run(run_name=f"{disease}_head_{MODEL_VERSION}"):
        mlflow.log_params(params)
        mlflow.log_metrics({f"cv_{k}": v for k, v in cv.items()})
        mlflow.log_dict(extra, "record.json")
    print(f"[{disease}] logged to MLflow ({MLRUNS_DIR / 'mlflow.db'})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def train_head(disease: str, n_trials: int, df: pd.DataFrame | None = None, save: bool = True) -> dict:
    cohort = df if df is not None else D.load_cohort()
    cohort, vel = D.add_derived(cohort)
    part = D.make_partitions(cohort)
    ds = D.build_dataset(cohort, disease, part, vel)

    is_train = ds["partition"] == "train"
    kept, _ = D.prune_by_missingness(ds["X"], is_train)
    X = ds["X"][kept]
    y, groups, partition = ds["y"], ds["groups"], ds["partition"]

    X_tr, y_tr, g_tr = X[is_train], y[is_train], groups[is_train]
    folds = D.make_cv_folds(y_tr, g_tr)

    print(f"[{disease}] tuning: {n_trials} trials × {len(folds)} folds on {len(X_tr):,} training rows")
    best_params, cv, ratio, history = tune(X_tr, y_tr, g_tr, folds, n_trials)
    print(f"[{disease}] best CV: " + ", ".join(f"{k}={v:.4f}" for k, v in cv.items()))

    raw = make_model(best_params).fit(X_tr, y_tr)

    iso_mask = partition == "calib_iso"
    calibrated, method, pos_pat = calibrate(raw, X[iso_mask], y[iso_mask], groups[iso_mask])
    print(f"[{disease}] calibration: {method} ({iso_mask.sum():,} rows, {pos_pat} positive patients)")

    conf_mask = partition == "calib_conf"
    p_conf = calibrated.predict_proba(X[conf_mask])[:, 1]
    q_hat = mondrian_thresholds(p_conf, y[conf_mask].to_numpy())
    sets = [prediction_set(p, q_hat) for p in p_conf]
    yc = y[conf_mask].to_numpy()
    cover = {str(k): float(np.mean([k in s for s, t in zip(sets, yc) if t == k])) for k in (0, 1)}
    print(f"[{disease}] conformal q̂ = {q_hat}, coverage on calib_conf by class = {cover}")

    bundle = {
        "disease": disease,
        "model_version": MODEL_VERSION,
        "calibrated": calibrated,          # use for ŷ
        "raw": raw,                        # use for SHAP (explains the raw log-odds, not ŷ)
        "q_hat": q_hat,
        "tier_cutoffs": TIER_CUTOFFS,
        "feature_columns": kept,
        "velocity_markers": vel,
    }
    record = {
        "disease": disease,
        "model_version": MODEL_VERSION,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "cohort_sha256": D.COHORT_SHA256,
        "feature_columns": kept,
        "best_params": best_params,
        "neg_pos_ratio": ratio,
        "n_trials": n_trials,
        "seed": D.SEED,
        "loss_weights": LOSS_WEIGHTS,
        "cv_metrics": cv,
        "calibration_method": method,
        "conformal": {"alpha": ALPHA, "q_hat": q_hat, "calib_conf_coverage_by_class": cover},
        "tier_cutoffs": TIER_CUTOFFS,
        "library_versions": library_versions(),
    }
    if save:
        paths = save_bundle(disease, bundle, record)
        trials_csv = MODELS_DIR / f"{disease}_trials.csv"
        history.to_csv(trials_csv, index=False)
        print(f"[{disease}] tuning history: {trials_csv}")
        print(f"[{disease}] saved {paths['joblib']} (sha256 {paths['sha256'][:12]}…)")
        log_mlflow(disease, best_params, cv, record)
    return {"bundle": bundle, "record": record}


def main():
    ap = argparse.ArgumentParser(description="Train one CDSS disease head")
    ap.add_argument("--disease", choices=D.DISEASES, required=True)
    ap.add_argument("--trials", type=int, default=100)
    args = ap.parse_args()
    train_head(args.disease, args.trials)


if __name__ == "__main__":
    main()