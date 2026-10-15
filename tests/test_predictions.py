"""/api/v1/predictions: no fabricated numbers, input validated, one shared model registry."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests._helpers import FixedProbabilityModel, auth_header, fake_user, write_model

from flask import Flask

from backend.cdss.model_loader import ModelRegistry

PAYLOAD = {"patient_id": 7, "modality": "cvd", "biomarker_payload": {"age": 50, "sbp": 130}}


class PredictionRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.reg = ModelRegistry(model_dir=self.dir)
        import backend.cdss.engine as engine
        # Database calls are replaced here because SQLAlchemy is not available in every
        # test environment; tests/test_ai_database.py runs the real ones.
        self.audit_events = []
        self.audit_fails = False
        self.patient_found = True
        self.stored_biomarkers = None
        self.patches = [
            patch.object(engine, "registry", self.reg, create=True),
            patch("backend.middleware.rbac.load_user", create=True, side_effect=self._user),
            patch("backend.routes.predictions.patient_exists", create=True,
                  side_effect=lambda pid: self.patient_found),
            patch("backend.routes.predictions.latest_biomarkers", create=True,
                  side_effect=lambda modality, pid: self.stored_biomarkers),
            patch("backend.routes.predictions.log_event", create=True, side_effect=self._log_event),
        ]
        for p in self.patches:
            p.start()
        self.role = "DOCTOR"
        from backend.routes.predictions import predictions_bp
        app = Flask(__name__)
        app.register_blueprint(predictions_bp)
        self.client = app.test_client()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _user(self, user_id):
        return fake_user(user_id=user_id, role=self.role)

    def _log_event(self, event_type, payload, **kwargs):
        if self.audit_fails:
            raise RuntimeError("database unavailable")
        self.audit_events.append({"event_type": event_type, "payload": payload, **kwargs})
        return f"audit-{len(self.audit_events)}"

    # --- audit ledger -----------------------------------------------------
    def test_every_inference_is_logged_with_its_result(self):
        write_model(self.dir, model=FixedProbabilityModel(0.55))
        body = self.infer().get_json()
        self.assertEqual(len(self.audit_events), 1)
        event = self.audit_events[0]
        self.assertEqual(event["event_type"], "INFERENCE")
        self.assertEqual(event["patient_id"], 7)
        self.assertEqual(event["payload"]["tier"], "HIGH")
        self.assertEqual(event["payload"]["model_version"], "v1")
        self.assertEqual(body["audit_id"], "audit-1")

    def test_inference_fails_closed_when_audit_cannot_be_written(self):
        write_model(self.dir)
        self.audit_fails = True
        r = self.infer()
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.get_json()["code"], "AUDIT_LOG_FAILED")

    def test_unknown_patient_is_404_and_not_logged(self):
        write_model(self.dir)
        self.patient_found = False
        r = self.infer()
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["code"], "PATIENT_NOT_FOUND")
        self.assertEqual(self.audit_events, [])

    def test_reload_is_logged(self):
        self.role = "ADMIN"
        self.client.post("/api/v1/predictions/models/reload", headers=auth_header(role="ADMIN"))
        self.assertEqual([e["event_type"] for e in self.audit_events], ["MODELS_RELOADED"])

    # --- biomarkers from the database ---------------------------------------
    def test_without_payload_the_latest_stored_biomarkers_are_used(self):
        write_model(self.dir)
        self.stored_biomarkers = {"age": 50, "sbp": 130}
        body = self.infer({"patient_id": 7, "modality": "cvd"}).get_json()
        self.assertEqual(body["biomarker_source"], "database")
        self.assertEqual(body["missing_features"], [])

    def test_request_payload_is_reported_as_the_source(self):
        write_model(self.dir)
        self.assertEqual(self.infer().get_json()["biomarker_source"], "request")

    def test_without_payload_or_stored_biomarkers_is_404(self):
        write_model(self.dir)
        r = self.infer({"patient_id": 7, "modality": "cvd"})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["code"], "NO_BIOMARKERS")

    def infer(self, body=PAYLOAD, role="DOCTOR"):
        self.role = role
        return self.client.post("/api/v1/predictions/infer", json=body, headers=auth_header(role=role))

    # --- input validation -------------------------------------------------
    def test_missing_patient_id_is_rejected(self):
        write_model(self.dir)
        body = {k: v for k, v in PAYLOAD.items() if k != "patient_id"}
        r = self.infer(body)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["code"], "MISSING_PATIENT_ID")

    def test_non_numeric_biomarker_is_rejected(self):
        write_model(self.dir)
        body = {**PAYLOAD, "biomarker_payload": {"age": "fifty"}}
        r = self.infer(body)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["code"], "INVALID_FEATURE")

    # --- values come from the trained model's metadata ---------------------
    def test_calibration_is_read_from_model_metadata(self):
        write_model(self.dir)
        cal = self.infer().get_json()["calibration"]
        self.assertEqual(cal["method"], "sigmoid")
        self.assertEqual(cal["brier_score"], 0.0709)
        self.assertEqual(cal["source"], "trained_model")

    def test_fairness_reports_the_trained_subgroup_gap(self):
        write_model(self.dir)  # subgroup_gap 0.1016 > 0.05 threshold
        fair = self.infer().get_json()["fairness"]
        self.assertFalse(fair["passed"])
        self.assertTrue(fair["disparity_detected"])
        self.assertEqual(fair["gap"], 0.1016)

    def test_missing_features_are_returned(self):
        write_model(self.dir)
        body = {**PAYLOAD, "biomarker_payload": {"age": 50}}
        self.assertEqual(self.infer(body).get_json()["missing_features"], ["systolic_bp"])

    # --- placeholders are labelled, not presented as results ---------------
    def test_stub_is_labelled_as_fallback(self):
        write_model(self.dir, write_joblib=False)
        body = self.infer().get_json()
        self.assertEqual(body["calibration"]["source"], "deterministic_fallback")
        self.assertEqual(body["risk"]["tier"], "UNAVAILABLE")
        self.assertTrue(body["is_stub"])

    def test_fhrs_values_are_marked_placeholder(self):
        write_model(self.dir)
        fhrs = self.infer().get_json()["fhrs_decomposition"]
        self.assertTrue(fhrs["placeholder"])
        self.assertIsNone(fhrs["base_score"])

    def test_phase_two_deltas_are_marked_placeholder(self):
        write_model(self.dir)
        body = self.infer({**PAYLOAD, "baseline_hash": "abc"}).get_json()
        self.assertTrue(body["biomarker_deltas"]["placeholder"])
        self.assertEqual(body["biomarker_deltas"]["metrics"], {})
        self.assertIsNone(body["proposed_reanchor"]["eligible"])

    def test_real_model_tier_reaches_the_response(self):
        write_model(self.dir, model=FixedProbabilityModel(0.55))
        risk = self.infer().get_json()["risk"]
        self.assertEqual(risk["tier"], "HIGH")
        self.assertEqual(risk["domains"]["cvd"]["tier"], "HIGH")

    # --- model management -------------------------------------------------
    def test_doctor_cannot_reload_models(self):
        self.role = "DOCTOR"
        r = self.client.post("/api/v1/predictions/models/reload", headers=auth_header(role="DOCTOR"))
        self.assertEqual(r.status_code, 403)

    def test_reload_clears_the_registry_inference_uses(self):
        write_model(self.dir)
        before = self.reg.load("cvd")
        self.role = "ADMIN"
        r = self.client.post("/api/v1/predictions/models/reload", headers=auth_header(role="ADMIN"))
        self.assertEqual(r.status_code, 200)
        self.assertIsNot(self.reg.load("cvd"), before)

    def test_status_comes_from_the_same_registry(self):
        write_model(self.dir)
        r = self.client.get("/api/v1/predictions/models/status", headers=auth_header(role="DOCTOR"))
        self.assertTrue(r.get_json()["cvd"]["loaded"])


if __name__ == "__main__":
    unittest.main()