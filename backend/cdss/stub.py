import numpy as np


class DeterministicStub:
    """Fallback predictor returning deterministic probability arrays.
    Matches the scikit-learn / XGBoost interface: predict_proba(X) -> [n, 2].
    """

    def __init__(self, disease: str):
        self.disease = disease
        self.feature_importances_ = np.array([])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        n = len(X)
        # Neutral 50% baseline probability
        return np.tile([0.5, 0.5], (n, 1))