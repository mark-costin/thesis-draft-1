import json
import joblib
from pathlib import Path
from backend.cdss.stub import DeterministicStub

# Look for models in ml/models (or experiments/models as fallback)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "ml" / "models"
if not MODEL_DIR.exists():
    MODEL_DIR = BASE_DIR / "experiments" / "models"

DISEASES = ["cvd", "t2d", "resp", "neuro"]


class ModelRegistry:
    """Loads trained artifacts. Falls back to DeterministicStub if missing."""

    def __init__(self):
        self._cache = {}

    def load(self, disease: str, version: str = "latest"):
        key = f"{disease}_{version}"
        if key in self._cache:
            return self._cache[key]

        path = MODEL_DIR / f"{disease}_head_{version}.joblib"
        if path.exists():
            model = joblib.load(path)
            self._cache[key] = model
            return model

        stub = DeterministicStub(disease)
        self._cache[key] = stub
        return stub

    def metadata(self, disease: str, version: str = "latest") -> dict:
        path = MODEL_DIR / f"{disease}_head_{version}.json"
        if path.exists():
            return json.loads(path.read_text())
        return {
            "loaded": False,
            "fallback": "deterministic_stub",
            "model_version": "stub-fallback",
            "feature_columns": []
        }

    def status(self) -> dict:
        return {
            d: {
                "loaded": (MODEL_DIR / f"{d}_head_latest.joblib").exists(),
                "metadata": self.metadata(d),
            }
            for d in DISEASES
        }

    def clear_cache(self):
        self._cache.clear()