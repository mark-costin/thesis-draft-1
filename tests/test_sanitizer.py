"""sanitize_response: secrets stripped for everyone, model internals hidden from patients."""
import unittest

from tests._helpers import ROOT  # noqa: F401

from backend.middleware.sanitizer import sanitize_response

INFERENCE = {
    "risk": {"score": 31.2, "tier": "MODERATE"},
    "model_version": "v1",
    "fairness": {"passed": False, "gap": 0.1016},
    "fairness_audit": {"passed": False},
    "calibration": {"method": "sigmoid", "brier_score": 0.0709},
    "shap": {"drivers": [{"display_name": "ldl", "shap_value": 0.2}]},
    "user": {"username": "jane", "password_hash": "$2b$..."},
}


class SanitizerTests(unittest.TestCase):
    def test_patient_does_not_see_model_internals(self):
        out = sanitize_response({"encounter": {"cdss_payload": INFERENCE}}, role="PATIENT")
        payload = out["encounter"]["cdss_payload"]
        for hidden in ("model_version", "fairness", "fairness_audit", "calibration"):
            self.assertNotIn(hidden, payload, hidden)

    def test_patient_still_sees_risk_and_drivers(self):
        out = sanitize_response(INFERENCE, role="PATIENT")
        self.assertEqual(out["risk"]["tier"], "MODERATE")
        self.assertIn("shap", out)

    def test_doctor_sees_model_internals(self):
        out = sanitize_response(INFERENCE, role="DOCTOR")
        for kept in ("model_version", "fairness", "calibration"):
            self.assertIn(kept, out)

    def test_password_hash_stripped_for_every_role(self):
        for role in (None, "PATIENT", "DOCTOR", "ADMIN"):
            self.assertNotIn("password_hash", sanitize_response(INFERENCE, role=role)["user"])


if __name__ == "__main__":
    unittest.main()
