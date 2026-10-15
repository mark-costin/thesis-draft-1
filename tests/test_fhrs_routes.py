"""
AI <-> database part 2 against a real (SQLite) database:
family history with verification, environmental hazards, biological sex, the FHRS view,
and /infer building each model's full input from stored records.

Needs: flask_sqlalchemy, bcrypt, pgvector (runs on your machine; skipped where missing).
"""
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tests._helpers import FixedProbabilityModel, has_modules, make_token, write_model

DB_STACK = has_modules("flask_sqlalchemy", "bcrypt", "pgvector")
P = "/api/v1/patient"
DOC_USER, DOC = 10, 1
ANA_USER, ANA = 20, 5
BEN_USER, BEN = 21, 6
CVD_FEATURES = ("age", "biological_sex", "systolic_bp", "tg", "adjusted_fhrs_cvd", "fhrs_band_cvd",
                "m_tg", "v_systolic_bp", "m_velocity")


def _person(prefix):
    return dict(first_name=f"{prefix}First", last_name=f"{prefix}Last", address="1 Test St",
                contact_number="0900-000-0000", email=f"{prefix.lower()}@example.com",
                emergency_contact_name="Contact", emergency_contact_number="0900-000-0001",
                emergency_relation="Sibling")


@unittest.skipUnless(DB_STACK, "needs flask_sqlalchemy + bcrypt + pgvector (runs on your machine)")
class FhrsRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = "sqlite://"
        from flask import Flask
        from backend.dbconnect import db, init_db
        import backend.model_orm  # noqa: F401
        from backend.routes.patient import patient_bp
        from backend.routes.predictions import predictions_bp

        app = Flask(__name__)
        init_db(app)
        app.register_blueprint(patient_bp)
        app.register_blueprint(predictions_bp)
        cls.app, cls.db = app, db
        with app.app_context():
            db.create_all()

    def setUp(self):
        from backend.cdss.model_loader import ModelRegistry
        from backend.model_orm import (AuditLedger, CVDMetrics, Doctor, EnvironmentalHazard, FamilyHistory,
                                       FHRSStratification, IdempotencyCache, Patient, User)
        import backend.cdss.engine as engine
        self.M = dict(CVDMetrics=CVDMetrics, FamilyHistory=FamilyHistory, Patient=Patient,
                      FHRSStratification=FHRSStratification, EnvironmentalHazard=EnvironmentalHazard)

        self.tmp = tempfile.TemporaryDirectory()
        write_model(self.tmp.name, model=FixedProbabilityModel(0.55), features=CVD_FEATURES)
        self.registry_patch = patch.object(engine, "registry", ModelRegistry(model_dir=Path(self.tmp.name)))
        self.registry_patch.start()

        self.ctx = self.app.app_context()
        self.ctx.push()
        s = self.db.session
        for model in (AuditLedger, FHRSStratification, EnvironmentalHazard, FamilyHistory, CVDMetrics,
                      IdempotencyCache, Patient, Doctor, User):
            s.query(model).delete()
        s.add_all([User(user_id=DOC_USER, username="doc", role="DOCTOR", password_hash="x"),
                   User(user_id=ANA_USER, username="ana", role="PATIENT", password_hash="x"),
                   User(user_id=BEN_USER, username="ben", role="PATIENT", password_hash="x")])
        s.flush()
        s.add(Doctor(doctor_id=DOC, user_id=DOC_USER, specialization="IM", license_number="PRC-1",
                     is_verified=True, **_person("Doc")))
        for user_id, pid, prefix in ((ANA_USER, ANA, "Ana"), (BEN_USER, BEN, "Ben")):
            s.add(Patient(patient_id=pid, user_id=user_id, date_of_birth=date(1970, 1, 1), gender="Male",
                          hipaa_consent=True, **_person(prefix)))
        s.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        self.db.session.rollback()
        self.ctx.pop()
        self.registry_patch.stop()
        self.tmp.cleanup()

    # --- helpers ----------------------------------------------------------
    def h(self, user_id=DOC_USER, role="DOCTOR"):
        return {"Authorization": f"Bearer {make_token(user_id=user_id, role=role)}"}

    def relative(self, tier, onset, verified=False, user_id=DOC_USER, role="DOCTOR", patient_id=ANA, disease="cvd"):
        return self.client.post(f"{P}/family-history", headers=self.h(user_id, role),
                                json={"patient_id": patient_id, "disease_domain": disease, "relationship_tier": tier,
                                      "onset_classification": onset, "is_verified": verified})

    def hazard(self, code, disease="cvd", user_id=DOC_USER, role="DOCTOR", patient_id=ANA):
        return self.client.post(f"{P}/hazards", headers=self.h(user_id, role),
                                json={"patient_id": patient_id, "disease_domain": disease, "hazard_code": code})

    def john(self):
        """CDSS FHRS Guide, section 6."""
        self.relative(1, "early", True)
        self.relative(1, "severe_early", True)
        self.relative(2, "typical", False)
        self.hazard("secondhand_smoke")

    def fhrs(self, disease="cvd", user_id=DOC_USER, role="DOCTOR", patient_id=ANA):
        return self.client.get(f"{P}/fhrs?patient_id={patient_id}&disease={disease}", headers=self.h(user_id, role))

    # --- family history and verification ------------------------------------
    def test_entry_is_stored_with_spec_weights_and_returned(self):
        self.assertEqual(self.relative(2, "Early onset").status_code, 201)
        entry = self.client.get(f"{P}/family-history?patient_id={ANA}", headers=self.h()).get_json()["family_history"][0]
        self.assertEqual((entry["relationship_tier"], entry["onset_classification"]), (2, "early"))
        self.assertEqual((entry["relationship_weight"], entry["onset_weight"], entry["is_verified"]), (0.25, 2.0, False))

    def test_patient_cannot_mark_their_own_entry_verified(self):
        r = self.relative(1, "typical", True, user_id=ANA_USER, role="PATIENT")
        rec = self.db.session.get(self.M["FamilyHistory"], r.get_json()["record_id"])
        self.assertFalse(rec.is_verified)

    def test_doctor_verifies_an_entry(self):
        rid = self.relative(1, "typical", user_id=ANA_USER, role="PATIENT").get_json()["record_id"]
        r = self.client.post(f"{P}/family-history/{rid}/verify", headers=self.h())
        self.assertEqual(r.status_code, 200)
        self.db.session.expire_all()
        self.assertTrue(self.db.session.get(self.M["FamilyHistory"], rid).is_verified)

    def test_patient_cannot_use_the_verify_route(self):
        rid = self.relative(1, "typical", user_id=ANA_USER, role="PATIENT").get_json()["record_id"]
        r = self.client.post(f"{P}/family-history/{rid}/verify", headers=self.h(ANA_USER, "PATIENT"))
        self.assertEqual(r.status_code, 403)

    def test_verifying_a_missing_entry_is_404(self):
        self.assertEqual(self.client.post(f"{P}/family-history/9999/verify", headers=self.h()).status_code, 404)

    # --- hazards --------------------------------------------------------------
    def test_hazard_from_the_list_is_stored(self):
        self.assertEqual(self.hazard("biomass_heating", "resp").status_code, 201)
        body = self.client.get(f"{P}/hazards?patient_id={ANA}", headers=self.h()).get_json()
        self.assertEqual([(h["disease_domain"], h["hazard_code"], h["e_j"]) for h in body["hazards"]],
                         [("resp", "biomass_heating", 0.35)])
        self.assertIn("secondhand_smoke", {h["code"] for h in body["catalogue"]["cvd"]})

    def test_hazard_not_on_that_diseases_list_is_400(self):
        r = self.hazard("biomass_heating", "cvd")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["fields"], ["hazard_code"])

    def test_same_hazard_twice_is_409(self):
        self.hazard("high_salt_diet")
        self.assertEqual(self.hazard("high_salt_diet").status_code, 409)

    def test_patient_records_hazards_only_for_themselves(self):
        self.assertEqual(self.hazard("high_salt_diet", user_id=ANA_USER, role="PATIENT", patient_id=BEN).status_code, 201)
        stored = self.M["EnvironmentalHazard"].query.one()
        self.assertEqual(stored.patient_id, ANA)

    def test_doctor_removes_a_hazard(self):
        hid = self.hazard("high_salt_diet").get_json()["id"]
        self.assertEqual(self.client.delete(f"{P}/hazards/{hid}", headers=self.h()).status_code, 200)
        self.assertEqual(self.M["EnvironmentalHazard"].query.count(), 0)

    # --- biological sex -------------------------------------------------------
    def test_doctor_sets_biological_sex(self):
        r = self.client.post(f"{P}/biological-sex", headers=self.h(), json={"patient_id": ANA, "biological_sex": "male"})
        self.assertEqual(r.status_code, 200)
        self.db.session.expire_all()
        self.assertEqual(self.db.session.get(self.M["Patient"], ANA).biological_sex, "Male")

    def test_patient_cannot_set_biological_sex(self):
        r = self.client.post(f"{P}/biological-sex", headers=self.h(ANA_USER, "PATIENT"),
                             json={"patient_id": ANA, "biological_sex": "Male"})
        self.assertEqual(r.status_code, 403)

    def test_invalid_biological_sex_is_400(self):
        r = self.client.post(f"{P}/biological-sex", headers=self.h(), json={"patient_id": ANA, "biological_sex": "M"})
        self.assertEqual(r.status_code, 400)

    # --- FHRS view --------------------------------------------------------------
    def test_john_scores_4_17_band_3(self):
        self.john()
        body = self.fhrs().get_json()
        self.assertEqual(body["fhrs"]["adjusted_fhrs"], 4.1688)
        self.assertEqual((body["fhrs"]["band"], body["fhrs"]["band_label"]), (3, "Pronounced Risk"))

    def test_no_family_history_is_band_0(self):
        self.assertEqual(self.fhrs().get_json()["fhrs"]["band"], 0)

    def test_other_diseases_do_not_count(self):
        self.relative(1, "severe_early", True, disease="t2d")
        self.assertEqual(self.fhrs("cvd").get_json()["fhrs"]["band"], 0)

    def test_old_free_text_rows_are_still_scored(self):
        s = self.db.session
        s.add(self.M["FamilyHistory"](patient_id=ANA, disease_domain="CVD", specific_diagnosis="MI",
                                      relationship_tier="Tier 1", relationship_weight=0.5,
                                      onset_classification="Typical onset", onset_weight=1.0))
        s.commit()
        self.assertEqual(self.fhrs().get_json()["fhrs"]["bio_fhrs"], 0.25)

    def test_patient_sees_only_their_own_fhrs(self):
        self.john()
        body = self.fhrs(user_id=BEN_USER, role="PATIENT", patient_id=ANA).get_json()
        self.assertEqual((body["patient_id"], body["fhrs"]["band"]), (BEN, 0))

    def test_unknown_disease_is_400(self):
        self.assertEqual(self.fhrs("kidney").status_code, 400)

    # --- /infer builds the full model input from the database ------------------
    def store_cvd(self, days_ago, **values):
        when = datetime.now(timezone.utc) - timedelta(days=days_ago)
        self.db.session.add(self.M["CVDMetrics"](patient_id=ANA, recorded_at=when, **values))
        self.db.session.commit()

    def infer(self):
        return self.client.post("/api/v1/predictions/infer", json={"patient_id": ANA, "modality": "cvd"},
                                headers=self.h())

    def test_every_model_input_comes_from_the_database(self):
        self.john()
        self.client.post(f"{P}/biological-sex", headers=self.h(), json={"patient_id": ANA, "biological_sex": "Male"})
        self.store_cvd(90, age=56, sbp=130, triglycerides=150)
        self.store_cvd(0, age=56, sbp=142, triglycerides=160)
        body = self.infer().get_json()
        self.assertEqual(body["missing_features"], [])
        inputs = body["biomarker_payload"]
        self.assertEqual(inputs["biological_sex"], 1)
        self.assertEqual((inputs["fhrs_band_cvd"], inputs["m_tg"], inputs["m_velocity"]), (3, 0, 0))
        self.assertAlmostEqual(inputs["v_systolic_bp"], 12 / (90 / 30.4375), places=3)

    def test_inference_records_the_fhrs_it_used(self):
        self.john()
        self.store_cvd(0, age=56, sbp=142, triglycerides=160)
        self.infer()
        row = self.M["FHRSStratification"].query.one()
        self.assertEqual((row.disease_domain, row.risk_code, float(row.calculated_fhrs)), ("cvd", 3, 4.1688))

    def test_single_record_has_no_velocity(self):
        self.store_cvd(0, age=56, sbp=142, triglycerides=160)
        body = self.infer().get_json()
        self.assertEqual(body["biomarker_payload"]["m_velocity"], 1)
        self.assertIn("v_systolic_bp", body["missing_features"])


if __name__ == "__main__":
    unittest.main()
