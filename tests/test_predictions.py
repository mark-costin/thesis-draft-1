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
        self.stored_input = None
        self.fhrs = {"disease": "cvd", "relatives_counted": 3, "pedigree_sum": 2.625, "clustering": 1.0,
                     "bio_fhrs": 3.625, "hazards": ["secondhand_smoke"], "environmental_modifier": 1.15,
                     "adjusted_fhrs": 4.16875, "band": 3, "band_label": "Pronounced Risk", "skipped_records": []}
        self.recorded_fhrs = []
        self.patches = [
            patch.object(engine, "registry", self.reg, create=True),
            patch("backend.middleware.rbac.load_user", create=True, side_effect=self._user),
            patch("backend.routes.predictions.patient_exists", create=True,
                  side_effect=lambda pid: self.patient_found),
            patch("backend.routes.predictions.build_model_input", create=True,
                  side_effect=lambda modality, pid: self.stored_input),
            patch("backend.routes.predictions.patient_fhrs", create=True,
                  side_effect=lambda pid, modality: self.fhrs),
            patch("backend.routes.predictions.record_fhrs", create=True,
                  side_effect=lambda pid, result: self.recorded_fhrs.append((pid, result))),
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
    def test_without_payload_the_model_input_is_built_from_the_database(self):
        write_model(self.dir)
        self.stored_input = {"features": {"age": 50, "systolic_bp": 130}, "fhrs": self.fhrs, "records": 2}
        body = self.infer({"patient_id": 7, "modality": "cvd"}).get_json()
        self.assertEqual(body["biomarker_source"], "database")
        self.assertEqual(body["missing_features"], [])
        self.assertEqual(body["biomarker_payload"]["systolic_bp"], 130)

    def test_request_payload_gets_the_patients_fhrs_inputs(self):
        write_model(self.dir)
        payload = self.infer().get_json()["biomarker_payload"]
        self.assertEqual((payload["adjusted_fhrs_cvd"], payload["fhrs_band_cvd"]), (4.16875, 3))

    def test_fhrs_sent_with_the_request_is_not_overwritten(self):
        write_model(self.dir)
        body = {**PAYLOAD, "biomarker_payload": {"age": 50, "sbp": 130, "adjusted_fhrs_cvd": 0.5}}
        self.assertEqual(self.infer(body).get_json()["biomarker_payload"]["adjusted_fhrs_cvd"], 0.5)

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

    def test_out_of_range_biomarker_is_rejected_before_the_model_runs(self):
        # The models were trained on values clipped to the dictionary ranges, so a score
        # for sbp 900 would be an extrapolation, not a prediction.
        write_model(self.dir)
        body = {**PAYLOAD, "biomarker_payload": {"age": 50, "systolic_bp": 900}}
        r = self.infer(body)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["code"], "OUT_OF_RANGE")
        self.assertEqual(r.get_json()["fields"], ["systolic_bp"])
        self.assertEqual(self.audit_events, [])

    def test_boundary_values_are_accepted(self):
        write_model(self.dir)
        body = {**PAYLOAD, "biomarker_payload": {"age": 100, "sbp": 70}}
        self.assertEqual(self.infer(body).status_code, 200)

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

    def test_fhrs_breakdown_is_the_real_score(self):
        write_model(self.dir)
        fhrs = self.infer().get_json()["fhrs_decomposition"]
        self.assertFalse(fhrs["placeholder"])
        self.assertEqual((fhrs["adjusted_fhrs"], fhrs["band"], fhrs["band_label"]), (4.1688, 3, "Pronounced Risk"))
        self.assertEqual((fhrs["base_score"], fhrs["environmental_modifier"]), (3.625, 1.15))

    def test_fhrs_is_recorded_and_audited_with_the_inference(self):
        write_model(self.dir)
        self.infer()
        self.assertEqual([pid for pid, _ in self.recorded_fhrs], [7])
        self.assertEqual(self.audit_events[0]["payload"]["fhrs"]["band"], 3)

    def test_unknown_patient_records_no_fhrs(self):
        write_model(self.dir)
        self.patient_found = False
        self.infer()
        self.assertEqual(self.recorded_fhrs, [])

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
