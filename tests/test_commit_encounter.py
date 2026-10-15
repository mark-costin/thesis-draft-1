"""POST /api/v1/doctor/commit-encounter against a real SQLite database.

Needs: flask_sqlalchemy, bcrypt, pgvector (runs on your machine; skipped where missing).
"""
import os
import unittest
from datetime import date

from tests._helpers import has_modules, make_token

DB_STACK = has_modules("flask_sqlalchemy", "bcrypt", "pgvector")

DOCTOR_USER_ID = 10   # deliberately different from the doctor profile id
DOCTOR_ID = 1
PATIENT_ID = 5
URL = "/api/v1/doctor/commit-encounter"


def _person(prefix):
    return dict(first_name=f"{prefix}First", last_name=f"{prefix}Last", address="1 Test St",
                contact_number="0900-000-0000", email=f"{prefix.lower()}@example.com",
                emergency_contact_name="Contact", emergency_contact_number="0900-000-0001",
                emergency_relation="Sibling")


@unittest.skipUnless(DB_STACK, "needs flask_sqlalchemy + bcrypt + pgvector (runs on your machine)")
class CommitEncounterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = "sqlite://"
        from flask import Flask
        from backend.dbconnect import db, init_db
        import backend.model_orm  # noqa: F401
        from backend.routes.doctor import doctor_bp

        app = Flask(__name__)
        init_db(app)
        app.register_blueprint(doctor_bp)
        cls.app, cls.db = app, db
        with app.app_context():
            db.create_all()

    def setUp(self):
        from backend.model_orm import Doctor, IdempotencyCache, Patient, User
        from backend.model_orm.clinic_orm import Encounter
        self.Encounter = Encounter
        self.ctx = self.app.app_context()
        self.ctx.push()
        s = self.db.session
        for model in (Encounter, IdempotencyCache, Patient, Doctor, User):
            s.query(model).delete()
        s.add_all([
            User(user_id=DOCTOR_USER_ID, username="doc", role="DOCTOR", password_hash="x"),
            User(user_id=11, username="doc_no_profile", role="DOCTOR", password_hash="x"),
            User(user_id=20, username="pat", role="PATIENT", password_hash="x"),
        ])
        s.flush()
        s.add(Doctor(doctor_id=DOCTOR_ID, user_id=DOCTOR_USER_ID, specialization="Cardiology",
                     license_number="PRC-0001", **_person("Doc")))
        s.add(Patient(patient_id=PATIENT_ID, user_id=20, date_of_birth=date(1970, 1, 1),
                      gender="Female", hipaa_consent=True, **_person("Pat")))
        s.commit()
        self.client = self.app.test_client()
        self.n = 0

    def tearDown(self):
        self.db.session.rollback()
        self.ctx.pop()

    # --- helpers ----------------------------------------------------------
    def commit(self, encounter_type="BASELINE", user_id=DOCTOR_USER_ID, key=None, **extra):
        self.n += 1
        body = {
            "patient_id": PATIENT_ID,
            "encounter_type": encounter_type,
            "cdss_payload_snapshot": {"risk": {"tier": "HIGH", "score": 61.2}},
            "care_plan": {"directive": "Start statin", "prescriptions": ["atorvastatin 20mg"]},
            **extra,
        }
        headers = {"Authorization": f"Bearer {make_token(user_id=user_id, role='DOCTOR')}",
                   "Idempotency-Key": key or f"key-{self.n}"}
        return self.client.post(URL, json=body, headers=headers)

    def stored(self, encounter_uid):
        self.db.session.expire_all()  # read back what the database actually holds
        return self.Encounter.query.filter_by(encounter_uid=encounter_uid).one()

    def verify(self, encounter_uid):
        headers = {"Authorization": f"Bearer {make_token(user_id=DOCTOR_USER_ID, role='DOCTOR')}"}
        return self.client.get(f"/api/v1/doctor/encounter/{encounter_uid}/verify", headers=headers)

    # --- 1. doctor_id ---------------------------------------------------------
    def test_doctor_id_is_the_doctor_profile_not_the_user(self):
        r = self.commit()
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertEqual(self.stored(r.get_json()["encounter_id"]).doctor_id, DOCTOR_ID)
        self.assertEqual(r.get_json()["audit_trail"]["attending_physician_id"], DOCTOR_ID)

    def test_doctor_role_without_profile_is_rejected(self):
        r = self.commit(user_id=11)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.get_json()["code"], "DOCTOR_PROFILE_MISSING")

    # --- 2. care plan sealed + 4. reproducible ----------------------------------
    def test_seal_verifies_after_reading_back_from_database(self):
        from backend.ledger import verify_encounter
        uid = self.commit().get_json()["encounter_id"]
        self.assertTrue(verify_encounter(self.stored(uid)))
        body = self.verify(uid).get_json()
        self.assertTrue(body["seal_valid"])

    def test_editing_care_plan_in_database_breaks_the_seal(self):
        from backend.ledger import verify_encounter
        uid = self.commit().get_json()["encounter_id"]
        enc = self.stored(uid)
        enc.care_plan = {"directive": "Start statin", "prescriptions": ["atorvastatin 80mg"]}
        self.db.session.commit()
        self.assertFalse(verify_encounter(self.stored(uid)))
        self.assertFalse(self.verify(uid).get_json()["seal_valid"])

    def test_verify_unknown_encounter_is_404(self):
        self.assertEqual(self.verify("ENC-NOPE").status_code, 404)

    # --- 3. parent hash from the server ---------------------------------------
    def test_followup_parent_is_the_latest_baseline(self):
        baseline = self.commit("BASELINE").get_json()
        followup = self.commit("FOLLOWUP").get_json()
        self.assertEqual(followup["parent_baseline_hash"], baseline["cryptographic_hash"])

    def test_wrong_parent_hash_from_client_is_rejected(self):
        self.commit("BASELINE")
        r = self.commit("FOLLOWUP", parent_baseline_hash="f" * 64)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["code"], "STALE_PARENT_HASH")
        self.assertEqual(self.Encounter.query.count(), 1)

    def test_matching_parent_hash_from_client_is_accepted(self):
        h = self.commit("BASELINE").get_json()["cryptographic_hash"]
        self.assertEqual(self.commit("FOLLOWUP", parent_baseline_hash=h).status_code, 201)

    def test_followup_without_baseline_is_rejected(self):
        r = self.commit("FOLLOWUP")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["code"], "NO_BASELINE")

    def test_second_baseline_is_rejected(self):
        self.commit("BASELINE")
        r = self.commit("BASELINE")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["code"], "BASELINE_EXISTS")

    def test_reanchor_links_to_previous_anchor_and_becomes_the_new_one(self):
        first = self.commit("BASELINE").get_json()["cryptographic_hash"]
        reanchor = self.commit("REANCHOR_BASELINE").get_json()
        self.assertEqual(reanchor["parent_baseline_hash"], first)
        followup = self.commit("FOLLOWUP").get_json()
        self.assertEqual(followup["parent_baseline_hash"], reanchor["cryptographic_hash"])

    def test_baseline_has_no_parent(self):
        self.assertIsNone(self.commit("BASELINE").get_json()["parent_baseline_hash"])

    # --- input validation -------------------------------------------------
    def test_unknown_record_type_is_rejected(self):
        r = self.commit("EVALUATION")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["code"], "INVALID_RECORD_TYPE")

    def test_care_plan_must_be_an_object(self):
        r = self.commit(care_plan="take meds")
        self.assertEqual(r.status_code, 400)

    def test_unknown_patient_is_404(self):
        r = self.commit(patient_id=999)
        self.assertEqual(r.status_code, 404)

    # --- idempotency ------------------------------------------------------
    def test_retry_with_same_key_creates_one_encounter(self):
        first = self.commit("BASELINE", key="retry-1")
        second = self.commit("BASELINE", key="retry-1")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.get_json(), first.get_json())
        self.assertEqual(self.Encounter.query.count(), 1)

    def test_missing_idempotency_key_is_rejected(self):
        headers = {"Authorization": f"Bearer {make_token(user_id=DOCTOR_USER_ID, role='DOCTOR')}"}
        r = self.client.post(URL, json={"patient_id": PATIENT_ID, "encounter_type": "BASELINE"}, headers=headers)
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
