import hashlib
import json
import logging
import platform
from importlib import metadata as importlib_metadata
from pathlib import Path

import joblib

from backend.cdss.stub import DeterministicStub

log = logging.getLogger(__name__)

# Look for models in ml/models (or experiments/models as fallback)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "ml" / "models"
if not MODEL_DIR.exists():
    MODEL_DIR = BASE_DIR / "experiments" / "models"

DISEASES = ["cvd", "t2d", "resp", "neuro"]

# metadata "library_versions" key -> installed distribution name
_DISTRIBUTIONS = {"sklearn": "scikit-learn", "xgboost": "xgboost", "numpy": "numpy", "joblib": "joblib"}

_STUB_METADATA = {
    "loaded": False,
    "fallback": "deterministic_stub",
    "model_version": "stub-fallback",
    "feature_columns": [],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _major_minor(version: str) -> tuple:
    return tuple(str(version).split(".")[:2])


def check_library_versions(trained: dict) -> list:
    """Compare major.minor of training libraries with this server. Returns warnings."""
    warnings = []
    for key, trained_version in (trained or {}).items():
        if key == "python":
            installed = platform.python_version()
        elif key in _DISTRIBUTIONS:
            try:
                installed = importlib_metadata.version(_DISTRIBUTIONS[key])
            except importlib_metadata.PackageNotFoundError:
                warnings.append(f"{key}: trained with {trained_version}, not installed on this server")
                continue
        else:
            continue  # training-only tools (pandas, optuna) do not affect loading
        if _major_minor(installed) != _major_minor(trained_version):
            warnings.append(f"{key}: trained with {trained_version}, server has {installed}")
    return warnings


class ModelRegistry:
    """
    Loads trained artifacts and their metadata, with caching.

    Before loading a .joblib file it checks the file's SHA-256 against `artifact_sha256`
    in the metadata. joblib files can run code when loaded, so a changed file is refused
    and the stub is used instead (visible in status()).
    """

    def __init__(self, model_dir=None):
        self.model_dir = Path(model_dir) if model_dir is not None else MODEL_DIR
        self._models = {}
        self._metadata = {}
        self._problems = {}
        self._version_warnings = {}

    @staticmethod
    def is_stub(model) -> bool:
        return isinstance(model, DeterministicStub)

    def metadata(self, disease: str, version: str = "latest") -> dict:
        key = f"{disease}_{version}"
        if key not in self._metadata:
            path = self.model_dir / f"{disease}_head_{version}.json"
            self._metadata[key] = json.loads(path.read_text()) if path.exists() else dict(_STUB_METADATA)
        return self._metadata[key]

    def load(self, disease: str, version: str = "latest"):
        key = f"{disease}_{version}"
        if key in self._models:
            return self._models[key]

        meta = self.metadata(disease, version)
        path = self.model_dir / f"{disease}_head_{version}.joblib"
        problem = None

        if not path.exists():
            problem = f"model file missing: {path.name}"
        else:
            expected = meta.get("artifact_sha256")
            if expected and _sha256(path) != expected:
                problem = "artifact_sha256 mismatch: the .joblib file changed after training"

        if problem:
            log.warning("CDSS %s: %s; using deterministic stub", disease, problem)
            model = DeterministicStub(disease)
        else:
            warnings = check_library_versions(meta.get("library_versions"))
            for w in warnings:
                log.warning("CDSS %s: library version mismatch: %s", disease, w)
            self._version_warnings[key] = warnings
            model = joblib.load(path)

        self._problems[key] = problem
        self._models[key] = model
        return model

    def status(self) -> dict:
        report = {}
        for d in DISEASES:
            key = f"{d}_latest"
            model = self.load(d)
            report[d] = {
                "loaded": not self.is_stub(model),
                "model_version": self.metadata(d).get("model_version"),
                "problem": self._problems.get(key),
                "version_warnings": self._version_warnings.get(key, []),
                "metadata": self.metadata(d),
            }
        return report

    def clear_cache(self):
        self._models.clear()
        self._metadata.clear()
        self._problems.clear()
        self._version_warnings.clear()
