"""Load the trained disease heads saved by experiment/src/ml/train.py.

Each `{disease}_head_latest.joblib` is a bundle (dict) with the calibrated model, the raw XGBoost,
the conformal thresholds, the tier cut-offs and the feature list. A bundle is used only if its
SHA-256 matches `artifact_sha256` in the matching `.json` record; otherwise the head falls back to
the deterministic stub and says why.

Model folder: $CDSS_MODEL_DIR if set, else <project root>/experiment/data/models.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import joblib

from backend.cdss.stub import DeterministicStub

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISEASES = ["cvd", "t2d", "resp", "neuro"]
DEFAULT_TIER_CUTOFFS = [0.20, 0.50]


def resolve_model_dir() -> Path:
    env = os.environ.get("CDSS_MODEL_DIR")
    return Path(env) if env else PROJECT_ROOT / "experiment" / "data" / "models"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class LoadedHead:
    """What the engine needs for one disease. `source` is "model" or "stub"."""
    disease: str
    source: str
    calibrated: object
    raw: object = None
    q_hat: dict | None = None
    tier_cutoffs: list = field(default_factory=lambda: list(DEFAULT_TIER_CUTOFFS))
    feature_columns: list = field(default_factory=list)
    velocity_markers: list = field(default_factory=list)
    model_version: str = "stub-fallback"
    reason: str | None = None


class ModelRegistry:
    """Loads and caches verified bundles; falls back to DeterministicStub with a reason."""

    def __init__(self, model_dir: Path | str | None = None):
        self.model_dir = Path(model_dir) if model_dir else resolve_model_dir()
        self._cache: dict[str, LoadedHead] = {}

    def _stub(self, disease: str, reason: str) -> LoadedHead:
        return LoadedHead(disease=disease, source="stub", calibrated=DeterministicStub(disease), reason=reason)

    def load(self, disease: str, version: str = "latest") -> LoadedHead:
        key = f"{disease}_{version}"
        if key in self._cache:
            return self._cache[key]

        path = self.model_dir / f"{disease}_head_{version}.joblib"
        record_path = path.with_suffix(".json")
        if not path.exists() or not record_path.exists():
            head = self._stub(disease, f"model file not found: {path}")
        else:
            record = json.loads(record_path.read_text())
            expected = record.get("artifact_sha256")
            if expected != _sha256(path):
                head = self._stub(disease, f"sha256 mismatch for {path.name}: file does not match its record")
            else:
                try:
                    b = joblib.load(path)
                    head = LoadedHead(
                        disease=disease, source="model", calibrated=b["calibrated"], raw=b["raw"],
                        q_hat=b["q_hat"], tier_cutoffs=list(b["tier_cutoffs"]),
                        feature_columns=list(b["feature_columns"]),
                        velocity_markers=list(b.get("velocity_markers", [])),
                        model_version=b.get("model_version", record.get("model_version", "unknown")),
                    )
                except Exception as e:   # unpickling needs the same xgboost/sklearn versions
                    head = self._stub(disease, f"could not load {path.name}: {type(e).__name__}: {e}")

        self._cache[key] = head
        return head

    def metadata(self, disease: str, version: str = "latest") -> dict:
        path = self.model_dir / f"{disease}_head_{version}.json"
        if path.exists():
            return json.loads(path.read_text())
        return {"loaded": False, "fallback": "deterministic_stub", "model_version": "stub-fallback",
                "feature_columns": []}

    def status(self) -> dict:
        out = {}
        for d in DISEASES:
            head = self.load(d)
            out[d] = {"loaded": head.source == "model", "source": head.source,
                      "model_version": head.model_version, "reason": head.reason,
                      "metadata": self.metadata(d)}
        return out

    def clear_cache(self):
        self._cache.clear()


_REGISTRY: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    """The one registry shared by inference and /models/reload."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ModelRegistry()
    return _REGISTRY