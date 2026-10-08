import shap
import numpy as np


def compute_shap_drivers(model, X: np.ndarray, feature_names: list, top_k: int = 5) -> list:
    """Compute top-k local feature attributions using TreeSHAP."""
    if not feature_names or X.shape[1] != len(feature_names):
        return [{"display_name": "Model Stub / No Metadata", "shap_value": 0.0}]

    try:
        base_estimator = getattr(model, "estimator", model)
        if hasattr(base_estimator, "named_steps"):
            base_estimator = base_estimator.named_steps.get("classifier", base_estimator)

        explainer = shap.TreeExplainer(base_estimator)
        shap_values = explainer.shap_values(X)

        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        row = shap_values[0]
        order = np.argsort(np.abs(row))[::-1][:top_k]

        return [
            {
                "display_name": feature_names[i],
                "shap_value": round(float(row[i]), 4),
            }
            for i in order
        ]
    except Exception as e:
        return [{"display_name": "SHAP Unavailable", "shap_value": 0.0, "error": str(e)}]