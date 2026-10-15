"""ModelRegistry: integrity check, version check, metadata cache, honest stub status."""
import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import FixedProbabilityModel, write_model

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


if __name__ == "__main__":
    unittest.main()
