"""evaluate_biomarkers: trained tier cutoffs, honest stub output, feature checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests._helpers import FixedProbabilityModel, write_model

from backend.cdss.model_loader import ModelRegistry


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def evaluate(self, payload, p=0.3, **meta):
        write_model(self.dir, model=FixedProbabilityModel(p), **meta)
        reg = ModelRegistry(model_dir=self.dir)
        import backend.cdss.engine as engine
        with patch.object(engine, "registry", reg, create=True):
            return engine.evaluate_biomarkers("cvd", payload)

    def test_tier_uses_cutoffs_saved_with_the_model(self):
        # Cutoffs [0.2, 0.5]: 30% is MODERATE (old hardcoded 40/70 said LOW).
        self.assertEqual(self.evaluate({"age": 50, "systolic_bp": 130}, p=0.30)["tier"], "MODERATE")

    def test_probability_at_upper_cutoff_is_high(self):
        # Old hardcoded 40/70 said MODERATE for 55%.
        self.assertEqual(self.evaluate({"age": 50, "systolic_bp": 130}, p=0.55)["tier"], "HIGH")

    def test_probability_below_lower_cutoff_is_low(self):
        self.assertEqual(self.evaluate({"age": 50, "systolic_bp": 130}, p=0.10)["tier"], "LOW")

    def test_score_is_percentage_of_probability(self):
        out = self.evaluate({"age": 50, "systolic_bp": 130}, p=0.3)
        self.assertEqual(out["score"], 30.0)
        self.assertFalse(out["is_stub"])

    def test_missing_features_are_reported(self):
        out = self.evaluate({"age": 50}, p=0.3)
        self.assertEqual(out["missing_features"], ["systolic_bp"])

    def test_database_column_names_are_mapped_before_inference(self):
        out = self.evaluate({"age": 50, "sbp": 130}, p=0.3)
        self.assertEqual(out["missing_features"], [])

    def test_non_numeric_feature_is_rejected(self):
        from backend.cdss.features import FeatureError
        with self.assertRaises(FeatureError):
            self.evaluate({"age": "fifty", "systolic_bp": 130})

    def test_stub_never_reports_a_clinical_tier(self):
        write_model(self.dir, write_joblib=False)
        reg = ModelRegistry(model_dir=self.dir)
        import backend.cdss.engine as engine
        with patch.object(engine, "registry", reg, create=True):
            out = engine.evaluate_biomarkers("cvd", {"age": 50})
        self.assertTrue(out["is_stub"])
        self.assertEqual(out["tier"], "UNAVAILABLE")
        self.assertIsNone(out["score"])


if __name__ == "__main__":
    unittest.main()
