"""normalize_payload: DB / API names -> the names each model was trained on."""
import unittest
from unittest.mock import patch

from tests._helpers import ROOT  # noqa: F401


class FeatureMappingTests(unittest.TestCase):
    def setUp(self):
        from backend.cdss import features
        self.features = features

    def test_cvd_database_names_are_renamed_to_model_names(self):
        out = self.features.normalize_payload("cvd", {"sbp": 130, "dbp": 85, "triglycerides": 150})
        self.assertEqual(out, {"systolic_bp": 130, "diastolic_bp": 85, "tg": 150})

    def test_model_name_already_present_is_not_overwritten(self):
        out = self.features.normalize_payload("cvd", {"sbp": 130, "systolic_bp": 128})
        self.assertEqual(out["systolic_bp"], 128)

    def test_input_payload_is_not_mutated(self):
        payload = {"sbp": 130}
        self.features.normalize_payload("cvd", payload)
        self.assertEqual(payload, {"sbp": 130})

    def test_text_sex_without_configured_encoding_is_an_error(self):
        with patch.object(self.features, "SEX_ENCODING", None):
            with self.assertRaises(self.features.FeatureError):
                self.features.normalize_payload("cvd", {"biological_sex": "Male"})

    def test_text_sex_is_encoded_when_mapping_is_configured(self):
        with patch.object(self.features, "SEX_ENCODING", {"male": 1, "female": 0}):
            out = self.features.normalize_payload("cvd", {"biological_sex": " Female "})
        self.assertEqual(out["biological_sex"], 0)

    def test_unknown_sex_value_is_an_error(self):
        with patch.object(self.features, "SEX_ENCODING", {"male": 1, "female": 0}):
            with self.assertRaises(self.features.FeatureError):
                self.features.normalize_payload("cvd", {"biological_sex": "unknown"})

    def test_numeric_sex_passes_through(self):
        out = self.features.normalize_payload("cvd", {"biological_sex": 1})
        self.assertEqual(out["biological_sex"], 1)


if __name__ == "__main__":
    unittest.main()
