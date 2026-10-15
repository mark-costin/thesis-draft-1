"""ModelRegistry: integrity check, version check, metadata cache, honest stub status."""
import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import ROOT, FixedProbabilityModel, has_modules, write_model

from backend.cdss.model_loader import ModelRegistry
from backend.cdss.stub import DeterministicStub


class ModelRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_model_with_matching_hash_is_loaded(self):
        write_model(self.dir, model=FixedProbabilityModel(0.3))
        model = ModelRegistry(model_dir=self.dir).load("cvd")
        self.assertIsInstance(model, FixedProbabilityModel)

    def test_model_file_changed_after_training_is_not_loaded(self):
        write_model(self.dir, artifact_sha256="0" * 64)
        reg = ModelRegistry(model_dir=self.dir)
        self.assertIsInstance(reg.load("cvd"), DeterministicStub)
        self.assertIn("artifact_sha256", reg.status()["cvd"]["problem"])

    def test_missing_model_file_falls_back_to_stub_with_reason(self):
        write_model(self.dir, write_joblib=False)
        reg = ModelRegistry(model_dir=self.dir)
        self.assertTrue(reg.is_stub(reg.load("cvd")))
        self.assertFalse(reg.status()["cvd"]["loaded"])
        self.assertIn("missing", reg.status()["cvd"]["problem"])

    def test_library_version_mismatch_is_reported(self):
        write_model(self.dir, library_versions={"sklearn": "0.1.0"})
        reg = ModelRegistry(model_dir=self.dir)
        reg.load("cvd")
        warnings = reg.status()["cvd"]["version_warnings"]
        self.assertTrue(any("sklearn" in w for w in warnings), warnings)

    def test_metadata_is_read_once_until_cache_is_cleared(self):
        write_model(self.dir, model_version="v1")
        reg = ModelRegistry(model_dir=self.dir)
        self.assertEqual(reg.metadata("cvd")["model_version"], "v1")
        meta_path = self.dir / "cvd_head_latest.json"
        meta = json.loads(meta_path.read_text())
        meta["model_version"] = "v2"
        meta_path.write_text(json.dumps(meta))
        self.assertEqual(reg.metadata("cvd")["model_version"], "v1")
        reg.clear_cache()
        self.assertEqual(reg.metadata("cvd")["model_version"], "v2")

    def test_status_reports_real_model_as_loaded(self):
        write_model(self.dir)
        status = ModelRegistry(model_dir=self.dir).status()["cvd"]
        self.assertTrue(status["loaded"])
        self.assertIsNone(status["problem"])


class ModelFolderTests(unittest.TestCase):
    """
    Where the backend looks for the trained models. The training pipeline saves them to
    experiment/data/models/; the old setting looked in ml/models/ and experiments/models/
    (with an s), found neither, and every /infer quietly used the stub.
    """

    def resolve(self, root, env=None):
        from backend.cdss.model_loader import resolve_model_dir
        return resolve_model_dir(Path(root), env or {})

    def test_training_output_folder_is_used(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "experiment" / "data" / "models").mkdir(parents=True)
            self.assertEqual(self.resolve(root), Path(root) / "experiment" / "data" / "models")

    def test_ml_models_is_still_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "ml" / "models").mkdir(parents=True)
            self.assertEqual(self.resolve(root), Path(root) / "ml" / "models")

    def test_environment_setting_wins(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "experiment" / "data" / "models").mkdir(parents=True)
            chosen = self.resolve(root, {"CDSS_MODEL_DIR": "/srv/models"})
            self.assertEqual(chosen, Path("/srv/models"))

    def test_no_folder_is_logged_as_an_error(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertLogs("backend.cdss.model_loader", level="ERROR"):
                self.resolve(root)


REAL_MODELS = ROOT / "experiment" / "data" / "models"


@unittest.skipUnless((REAL_MODELS / "cvd_head_latest.joblib").exists() and has_modules("xgboost"),
                     "trained models not present (runs on your machine)")
class RealModelTests(unittest.TestCase):
    """The backend's default registry finds and loads all four trained models (no stub)."""

    def test_all_four_trained_models_load(self):
        from backend.cdss.model_loader import MODEL_DIR, ModelRegistry
        self.assertEqual(MODEL_DIR, REAL_MODELS)
        status = ModelRegistry().status()
        for disease in ("cvd", "t2d", "resp", "neuro"):
            self.assertTrue(status[disease]["loaded"], f"{disease}: {status[disease].get('problem')}")
            self.assertEqual(status[disease]["model_version"], "v1")


if __name__ == "__main__":
    unittest.main()
