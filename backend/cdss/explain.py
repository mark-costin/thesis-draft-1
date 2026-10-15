import numpy as np


def _unwrap_pipeline(estimator):
    """A Pipeline's last step is the model. (Assumes no preprocessing step changes X.)"""
    if hasattr(estimator, "named_steps"):
        return estimator.named_steps.get("classifier", estimator.steps[-1][1])
    return estimator


def tree_estimators(model) -> list:
    """
    Return the FITTED tree models to explain.

    A CalibratedClassifierCV keeps the fitted copies in `calibrated_classifiers_`
    (one per CV fold); its `.estimator` attribute is only the unfitted template.
    """
    calibrated = getattr(model, "calibrated_classifiers_", None)
    if calibrated:
        estimators = []
        for fold in calibrated:
            est = getattr(fold, "estimator", None)
            if est is None:  # scikit-learn < 1.2 used `base_estimator`
                est = getattr(fold, "base_estimator", None)
            estimators.append(_unwrap_pipeline(est))
        return estimators
    return [_unwrap_pipeline(model)]


def positive_class_values(shap_values) -> np.ndarray:
    """Normalize SHAP output to (rows, features) for the positive class."""
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    shap_values = np.asarray(shap_values)
    if shap_values.ndim == 3:  # newer SHAP: (rows, features, classes)
        shap_values = shap_values[..., 1]
    return shap_values


def compute_shap_drivers(model, X: np.ndarray, feature_names: list, top_k: int = 5) -> list:
    """
    Compute top-k local feature attributions using TreeSHAP.

    For a calibrated model, SHAP values are averaged over the fitted fold models.
    Values are in the trees' raw log-odds space, before calibration.
    """
    if not feature_names or X.shape[1] != len(feature_names):
        return [{"display_name": "Model Stub / No Metadata", "shap_value": 0.0}]

    try:
        import shap  # imported here so the rest of the AI layer works without SHAP installed

        per_fold = [
            positive_class_values(shap.TreeExplainer(est).shap_values(X))
            for est in tree_estimators(model)
        ]
        row = np.mean(per_fold, axis=0)[0]
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
