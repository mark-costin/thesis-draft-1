"""Batch 2 routes against a real SQLite database: queue privacy, ticket ownership, FHRS weights.

Needs: flask_sqlalchemy, bcrypt, pgvector (runs on your machine; skipped where missing).
"""
import os
import unittest
from datetime import date
from unittest.mock import patch

from tests._helpers import has_modules, make_token

DB_STACK = has_modules("flask_sqlalchemy", "bcrypt", "pgvector")
BASE = "/api/v1/patient"

ANA_USER, ANA = 20, 5      # patient user id, patient id
BEN_USER, BEN = 21, 6
NO_PROFILE_USER = 22       # PATIENT role, no patients row
DOC_USER = 10


def _person(prefix):
    return dict(first_name=f"{prefix}First", last_name=f"{prefix}Last", address="1 Test St",
                contact_number="0900-000-0000", email=f"{prefix.lower()}@example.com",
                emergency_contact_name="Contact", emergency_contact_number="0900-000-0001",
                emergency_relation="Sibling")


@unittest.skipUnless(DB_STACK, "needs flask_sqlalchemy + bcrypt + pgvector (runs on your machine)")
class PatientPrivacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = "sqlite://"
        from flask import Flask
        from backend.dbconnect import db, init_db
        import backend.model_orm  # noqa: F401
        from backend.routes.patient import patient_bp

        app = Flask(__name__)
        init_db(app)
        app.register_blueprint(patient_bp)
        cls.app, cls.db = app, db
        with app.app_context():
            db.create_all()

    def setUp(self):
        from backend.model_orm import Doctor, FamilyHistory, IdempotencyCache, Patient, User
        from backend.triage_queue import TriageQueue
        import backend.routes.patient as patient_routes
        self.FamilyHistory = FamilyHistory
        self.queue_patch = patch.object(patient_routes, "QUEUE", TriageQueue())
        self.queue_patch.start()

        self.ctx = self.app.app_context()
        self.ctx.push()
        s = self.db.session
        for model in (FamilyHistory, IdempotencyCache, Patient, Doctor, User):
            s.query(model).delete()
        s.add_all([
            User(user_id=DOC_USER, username="doc", role="DOCTOR", password_hash="x"),
            User(user_id=ANA_USER, username="ana", role="PATIENT", password_hash="x"),
            User(user_id=BEN_USER, username="ben", role="PATIENT", password_hash="x"),
            User(user_id=NO_PROFILE_USER, username="nobody", role="PATIENT", password_hash="x"),
        ])
        s.flush()
        s.add(Doctor(doctor_id=1, user_id=DOC_USER, specialization="Cardiology", license_number="PRC-1",
                     is_verified=True, **_person("Doc")))
        for user_id, pid, prefix in ((ANA_USER, ANA, "Ana"), (BEN_USER, BEN, "Ben")):
            s.add(Patient(patient_id=pid, user_id=user_id, date_of_birth=date(1980, 1, 1), gender="Female",
                          hipaa_consent=True, **_person(prefix)))
        s.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        self.db.session.rollback()
        self.ctx.pop()
        self.queue_patch.stop()

    def h(self, user_id, role="PATIENT"):
        return {"Authorization": f"Bearer {make_token(user_id=user_id, role=role)}"}

    def checkin(self, user_id, role="PATIENT", **body):
        return self.client.post(f"{BASE}/queue/checkin", json=body, headers=self.h(user_id, role))

    # --- queue visibility -------------------------------------------------
    def test_patient_sees_only_own_ticket(self):
        self.checkin(ANA_USER, complaint="chest pain")
        self.checkin(BEN_USER, complaint="cough")
        queue = self.client.get(f"{BASE}/queue", headers=self.h(ANA_USER)).get_json()["queue"]
        self.assertEqual([t["patient_id"] for t in queue], [ANA])

    def test_doctor_sees_every_ticket(self):
        self.checkin(ANA_USER)
        self.checkin(BEN_USER)
        queue = self.client.get(f"{BASE}/queue", headers=self.h(DOC_USER, "DOCTOR")).get_json()["queue"]
        self.assertEqual(len(queue), 2)

    # --- ticket ownership -------------------------------------------------
    def test_patient_cannot_cancel_another_patients_ticket(self):
        self.checkin(BEN_USER)
        r = self.client.delete(f"{BASE}/queue/{BEN}", headers=self.h(ANA_USER))
        self.assertEqual(r.status_code, 403)
        queue = self.client.get(f"{BASE}/queue", headers=self.h(DOC_USER, "DOCTOR")).get_json()["queue"]
        self.assertEqual(len(queue), 1)

    def test_patient_can_cancel_own_ticket(self):
        self.checkin(ANA_USER)
        r = self.client.delete(f"{BASE}/queue/{ANA}", headers=self.h(ANA_USER))
        self.assertEqual(r.status_code, 200)

    def test_patient_cannot_check_in_someone_else(self):
        self.checkin(ANA_USER, patient_id=BEN)
        queue = self.client.get(f"{BASE}/queue", headers=self.h(DOC_USER, "DOCTOR")).get_json()["queue"]
        self.assertEqual([t["patient_id"] for t in queue], [ANA])

    def test_patient_cannot_set_urgency(self):
        ticket = self.checkin(ANA_USER, urgency="🔴 Emergency").get_json()["ticket"]
        self.assertEqual(ticket["urgency"], "🟢 Routine")

    # --- identity resolution ----------------------------------------------
    def test_patient_without_profile_cannot_read_another_patients_history(self):
        r = self.client.get(f"{BASE}/family-history?patient_id={ANA}", headers=self.h(NO_PROFILE_USER))
        self.assertEqual(r.status_code, 404)

    def test_patient_asking_for_other_id_gets_own_history(self):
        self.client.post(f"{BASE}/family-history", headers=self.h(DOC_USER, "DOCTOR"),
                         json={"patient_id": BEN, "disease_domain": "CVD"})
        r = self.client.get(f"{BASE}/family-history?patient_id={BEN}", headers=self.h(ANA_USER))
        self.assertEqual(r.get_json()["family_history"], [])

    def test_non_numeric_patient_id_is_400_not_500(self):
        r = self.client.get(f"{BASE}/family-history?patient_id=abc", headers=self.h(DOC_USER, "DOCTOR"))
        self.assertEqual(r.status_code, 400)

    # --- FHRS weights -----------------------------------------------------
    def test_patient_supplied_weights_are_not_stored(self):
        from backend.validation import DEFAULT_ONSET_WEIGHT, DEFAULT_RELATIONSHIP_WEIGHT
        r = self.client.post(f"{BASE}/family-history", headers=self.h(ANA_USER),
                             json={"disease_domain": "CVD", "relationship_weight": 99, "onset_weight": 99})
        self.assertEqual(r.status_code, 201)
        rec = self.db.session.get(self.FamilyHistory, r.get_json()["record_id"])
        self.assertEqual(float(rec.relationship_weight), DEFAULT_RELATIONSHIP_WEIGHT)
        self.assertEqual(float(rec.onset_weight), DEFAULT_ONSET_WEIGHT)

    def test_doctor_negative_weight_is_rejected(self):
        r = self.client.post(f"{BASE}/family-history", headers=self.h(DOC_USER, "DOCTOR"),
                             json={"patient_id": ANA, "disease_domain": "CVD", "relationship_weight": -1})
        self.assertEqual(r.status_code, 400)

    def test_zero_onset_weight_is_reported_as_zero(self):
        self.client.post(f"{BASE}/family-history", headers=self.h(DOC_USER, "DOCTOR"),
                         json={"patient_id": ANA, "disease_domain": "CVD", "onset_weight": 0})
        history = self.client.get(f"{BASE}/family-history?patient_id={ANA}",
                                  headers=self.h(DOC_USER, "DOCTOR")).get_json()["family_history"]
        self.assertEqual(history[0]["onset_weight"], 0.0)


if __name__ == "__main__":
    unittest.main()
