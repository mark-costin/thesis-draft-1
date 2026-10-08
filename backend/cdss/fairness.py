import numpy as np
from sklearn.metrics import roc_auc_score


def run_fairness_audit(y_pred: np.ndarray, y_true: np.ndarray, subgroups: dict) -> dict:
    """Audit AUROC gap across demographic subgroups."""
    aurocs = {}
    for name, mask in subgroups.items():
        if mask.sum() < 30:
            continue
        try:
            aurocs[name] = roc_auc_score(y_true[mask], y_pred[mask])
        except ValueError:
            continue

    if len(aurocs) < 2:
        return {"passed": True, "disparity_detected": False, "gap": 0.0, "flags": []}

    gap = max(aurocs.values()) - min(aurocs.values())
    return {
        "passed": gap < 0.05,
        "disparity_detected": gap >= 0.05,
        "gap": round(gap, 4),
        "subgroup_aurocs": {k: round(v, 4) for k, v in aurocs.items()},
        "flags": [f"Subgroup gap {gap:.3f} exceeds 0.05 threshold"] if gap >= 0.05 else [],
    }