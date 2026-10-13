import numpy as np
import pandas as pd

DISEASES = ["cvd", "t2d", "resp", "neuro"]

# Target baseline prevalences (centre of each Gate 4 band)
TARGET_PREV = {"cvd": 0.08, "t2d": 0.10, "resp": 0.12, "neuro": 0.07}

# Latent noise SD per disease (lower = stronger signal = higher AUROC)
NOISE_SD = {"cvd": 0.5, "t2d": 0.8, "resp": 0.8, "neuro": 0.8}

# Outcome drivers: single source of truth (validate.py Gate 5 reads this)
#   T2D is HbA1c-dominant; RESP and NEURO depend on their own domain biomarkers
COEFS = {
    "cvd":   {"age": 0.055, "systolic_bp": 0.025, "bio_fhrs_cvd": 0.65},
    "t2d":   {"bmi": 0.08, "hba1c": 1.8, "bio_fhrs_t2d": 0.5},
    "resp":  {"age": 0.04, "bmi": 0.04, "fev1_fvc_ratio": -0.06, "spo2": -0.15},
    "neuro": {"age": 0.05, "bio_fhrs_neuro": 1.0, "mmse": -0.12, "phq9": 0.06},
}


def linear_predictor(df, disease):
    """Sum of coefficient * feature (no intercept, no noise)."""
    z = np.zeros(len(df))
    for col, coef in COEFS[disease].items():
        z = z + df[col].to_numpy(dtype=float) * coef
    return z


def _sigmoid(x):
    return 1 / (1 + np.exp(-x))


def _solve_intercept(z, target_prev, lo=-40.0, hi=40.0, iters=100):
    """Bisection: find b such that mean(sigmoid(z + b)) == target_prev."""
    z = np.asarray(z, dtype=float)
    for _ in range(iters):
        mid = (lo + hi) / 2
        if _sigmoid(z + mid).mean() > target_prev:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def generate_outcomes(df):
    """Baseline outcomes. Stores per-patient noise, uniform draw and intercept
    so follow-up visits can be re-evaluated consistently."""
    n = len(df)
    for d in DISEASES:
        noise = np.random.normal(0, NOISE_SD[d], size=n)
        z = linear_predictor(df, d) + noise
        b = _solve_intercept(z, TARGET_PREV[d])
        u = np.random.rand(n)
        df[f"y_{d}"] = (u < _sigmoid(z + b)).astype(int)
        df[f"_noise_{d}"] = noise
        df[f"_u_{d}"] = u
        df[f"_b_{d}"] = b
    return df


def update_outcomes_longitudinal(df):
    """Incident-diagnosis framing: recompute risk from each visit's drifted
    biomarkers; once diagnosed, a patient stays diagnosed."""
    helper_cols = []
    for d in DISEASES:
        p = _sigmoid(linear_predictor(df, d)
                     + df[f"_noise_{d}"].to_numpy()
                     + df[f"_b_{d}"].to_numpy())
        y = pd.Series((df[f"_u_{d}"].to_numpy() < p).astype(int), index=df.index)
        df[f"y_{d}"] = y.groupby(df["patient_id"]).cummax()
        helper_cols += [f"_noise_{d}", f"_u_{d}", f"_b_{d}"]
    return df.drop(columns=helper_cols)
