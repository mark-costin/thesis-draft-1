"""Per-patient reasons (TreeSHAP) for one prediction.

Uses XGBoost's built-in exact TreeSHAP (`pred_contribs=True`) on the RAW model stored in the bundle,
so the separate `shap` package is not needed. Values are contributions to the raw log-odds, before
calibration: they explain the ranking, not the calibrated percentage.
"""

from __future__ import annotations

import numpy as np


def shap_contributions(raw_model, X) -> tuple[np.ndarray, float]:
    """Return (contribution per feature, baseline) for the first row of X."""
    import xgboost as xgb
    contrib = raw_model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)[0]
    return np.asarray(contrib[:-1], float), float(contrib[-1])


def compute_shap_drivers(raw_model, X, feature_names: list, top_k: int = 5) -> list:
    """Top-k features by absolute contribution, largest first."""
    if raw_model is None or not feature_names:
        return [{"display_name": "Model Stub / No Metadata", "shap_value": 0.0}]
    try:
        phi, _ = shap_contributions(raw_model, X)
        values = np.asarray(X, float)[0]
        order = np.argsort(-np.abs(phi), kind="stable")[:top_k]
        return [
            {
                "display_name": feature_names[i],
                "shap_value": round(float(phi[i]), 4),
                "value": None if np.isnan(values[i]) else round(float(values[i]), 4),
                "direction": "raises risk" if phi[i] > 0 else ("lowers risk" if phi[i] < 0 else "no effect"),
            }
            for i in order
        ]
    except Exception as e:
        return [{"display_name": "SHAP Unavailable", "shap_value": 0.0, "error": type(e).__name__}]