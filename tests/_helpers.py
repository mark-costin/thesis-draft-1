"""Shared test utilities. Test-only code lives here, never in backend/."""
import hashlib
import importlib.util
import json
import logging
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_SECRET = "unit-test-secret-" + "x" * 40
os.environ.setdefault("JWT_SECRET", TEST_SECRET)
os.environ.setdefault("CORS_ALLOWED_ORIGIN", "http://localhost:8501")
TEST_SEAL_KEY = "unit-test-seal-key-" + "y" * 40
os.environ.setdefault("ENCOUNTER_SEAL_KEY", TEST_SEAL_KEY)

# Expected "using deterministic stub" warnings would otherwise print during tests.
logging.getLogger("backend").addHandler(logging.NullHandler())
logging.getLogger("backend").propagate = False

import jwt  # noqa: E402
import joblib  # noqa: E402
import numpy as np  # noqa: E402


def has_modules(*names):
    """True when every named module can be imported (used to skip integration tests)."""
    return all(importlib.util.find_spec(n) is not None for n in names)


def make_token(user_id=1, role="DOCTOR", token_version=1, secret=None, **extra):
    payload = {"user_id": user_id, "role": role, "token_version": token_version, **extra}
    return jwt.encode(payload, secret or os.environ["JWT_SECRET"], algorithm="HS256")


def auth_header(**kwargs):
    return {"Authorization": f"Bearer {make_token(**kwargs)}"}


def fake_user(user_id=1, role="DOCTOR", token_version=1, is_locked=False):
    """Stand-in for a users row: only the fields rbac reads."""
    return SimpleNamespace(user_id=user_id, role=role, token_version=token_version, is_locked=is_locked)


class FixedProbabilityModel:
    """Picklable stand-in for a trained disease head: always predicts probability `p`."""

    def __init__(self, p):
        self.p = p

    def predict_proba(self, X):
        X = np.asarray(X)
        return np.tile([1 - self.p, self.p], (len(X), 1))


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_model(model_dir, disease="cvd", model=None, features=("age", "systolic_bp"),
                write_joblib=True, **meta_overrides):
    """Write <disease>_head_latest.joblib + .json the way the training pipeline does."""
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib_path = model_dir / f"{disease}_head_latest.joblib"
    if write_joblib:
        joblib.dump(model if model is not None else FixedProbabilityModel(0.3), joblib_path)

    import sklearn
    meta = {
        "disease": disease,
        "model_version": "v1",
        "feature_columns": list(features),
        "tier_cutoffs": [0.2, 0.5],
        "calibration_method": "sigmoid",
        "cv_metrics": {"auroc": 0.81, "brier": 0.0709, "ece": 0.0186, "subgroup_gap": 0.1016},
        "library_versions": {"sklearn": sklearn.__version__},
    }
    if write_joblib:
        meta["artifact_sha256"] = sha256_of(joblib_path)
    meta.update(meta_overrides)
    (model_dir / f"{disease}_head_latest.json").write_text(json.dumps(meta))
    return meta
