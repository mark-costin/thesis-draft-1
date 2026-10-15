import numpy as np

from backend.cdss.explain import compute_shap_drivers
from backend.cdss.features import FeatureError, normalize_payload
from backend.cdss.model_loader import ModelRegistry

# The one registry shared by inference and the /models routes.
registry = ModelRegistry()
_registry = registry  # old name, kept so existing imports keep working

# Used only if a model's metadata has no "tier_cutoffs" (probabilities, not percent).
DEFAULT_TIER_CUTOFFS = (0.4, 0.7)


def build_feature_vector(payload: dict, feature_names: list):
    """Align the payload with the model's feature order. Returns (X, missing_feature_names)."""
    missing, row = [], []
    for name in feature_names:
        value = payload.get(name)
        if value is None:
            missing.append(name)
            row.append(np.nan)
            continue
        try:
            row.append(float(value))
        except (TypeError, ValueError):
            raise FeatureError(f"Feature '{name}' must be numeric, got {value!r}.")
    return np.array([row], dtype=float), missing


def assign_tier(probability: float, cutoffs) -> str:
    """LOW below the first cutoff, HIGH at or above the second, MODERATE in between."""
    low, high = cutoffs
    if probability >= high:
        return "HIGH"
    if probability >= low:
        return "MODERATE"
    return "LOW"


def evaluate_biomarkers(disease: str, payload: dict) -> dict:
    """Run inference and TreeSHAP attribution for a specific disease head."""
    meta = registry.metadata(disease)
    model = registry.load(disease)
    feature_names = meta.get("feature_columns", [])

    if registry.is_stub(model) or not feature_names:
        return {
            "score": None,
            "probability": None,
            "tier": "UNAVAILABLE",
            "drivers": [],
            "model_version": meta.get("model_version", "stub-fallback"),
            "is_stub": True,
            "missing_features": [],
        }

    X, missing = build_feature_vector(normalize_payload(disease, payload), feature_names)
    probability = float(model.predict_proba(X)[0, 1])

    return {
        "score": round(probability * 100.0, 2),
        "probability": round(probability, 4),
        "tier": assign_tier(probability, meta.get("tier_cutoffs") or DEFAULT_TIER_CUTOFFS),
        "drivers": compute_shap_drivers(model, X, feature_names),
        "model_version": meta.get("model_version", "unknown"),
        "is_stub": False,
        "missing_features": missing,
    }
