"""
Batch 5b routes against a real (SQLite) database.

Before: /api/v1/doctor/queue returned two hardcoded tickets (patients 1 and 2) whatever was
in the queue, and /api/v1/doctor/consultation answered "recorded successfully" without
saving anything.
Needs: flask_sqlalchemy (runs on your machine; skipped where missing).
"""
import os
import unittest
from datetime import date

from tests._helpers import has_modules, make_token

DB_STACK = has_modules("flask_sqlalchemy", "bcrypt", "pgvector")
DOC_USER, DOC = 10, 7
NO_PROFILE_DOC_USER = 11
ANA_USER, ANA = 20, 5
BEN_USER, BEN = 21, 6


def _person(prefix):
    return dict(first_name=f"{prefix}First", last_name=f"{prefix}Last", address="1 Test St",
                contact_number="0900-000-0000", email=f"{prefix.lower()}@example.com",
                emergency_contact_name="Contact", emergency_contact_number="0900-000-0001",
                emergency_relation="Sibling")


@unittest.skipUnless(DB_STACK, "needs flask_sqlalchemy + bcrypt + pgvector (runs on your machine)")
class ConsultationAndQueueRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = "sqlite://"
        from flask import Flask
        from backend.dbconnect import db, init_db
        import backend.model_orm  # noqa: F401
        from backend.routes.doctor import doctor_bp
        from backend.routes.patient import patient_bp
        app = Flask(__name__)
        init_db(app)
        app.register_blueprint(doctor_bp)
        app.register_blueprint(patient_bp)
        cls.app, cls.db = app, db
        with app.app_context():
            db.create_all()

    def setUp(self):
        from backend.model_orm import AuditLedger, Doctor, IdempotencyCache, Patient, User
        from backend.model_orm.clinic_orm import Consultation, QueueTicket
        self.AuditLedger, self.Consultation, self.QueueTicket = AuditLedger, Consultation, QueueTicket
        self.ctx = self.app.app_context()
        self.ctx.push()
        s = self.db.session
        for model in (AuditLedger, Consultation, QueueTicket, IdempotencyCache, Patient, Doctor, User):
            s.query(model).delete()
        s.add_all([User(user_id=DOC_USER, username="doc", role="DOCTOR", password_hash="x"),
                   User(user_id=NO_PROFILE_DOC_USER, username="doc2", role="DOCTOR", password_hash="x"),
                   User(user_id=ANA_USER, username="ana", role="PATIENT", password_hash="x"),
                   User(user_id=BEN_USER, username="ben", role="PATIENT", password_hash="x")])
        s.flush()
        s.add(Doctor(doctor_id=DOC, user_id=DOC_USER, specialization="IM", license_number="PRC-1",
                     is_verified=True, **_person("Doc")))
        for user_id, pid, prefix in ((ANA_USER, ANA, "Ana"), (BEN_USER, BEN, "Ben")):
            s.add(Patient(patient_id=pid, user_id=user_id, date_of_birth=date(1970, 1, 1), gender="Female",
                          hipaa_consent=True, **_person(prefix)))
        s.commit()
        self.client = self.app.test_client()
        self.n = 0

    def tearDown(self):
        self.db.session.rollback()
        self.ctx.pop()

    def h(self, user_id=DOC_USER, role="DOCTOR", key=True):
        self.n += 1
        headers = {"Authorization": f"Bearer {make_token(user_id=user_id, role=role)}"}
        if key:
            headers["Idempotency-Key"] = f"k-{self.n}"
        return headers

    def checkin(self, user_id):
        return self.client.post("/api/v1/patient/queue/checkin", json={"complaint": "dizzy"},
                                headers=self.h(user_id, "PATIENT", key=False))

    def consult(self, patient_id=ANA, directives=None, **kw):
        body = {"patient_id": patient_id, "directives": directives or {"medication": "Amlodipine 5 mg daily"},
                "notes": "Recheck BP in 2 weeks"}
        return self.client.post("/api/v1/doctor/consultation", json=body, headers=self.h(**kw))

    # --- doctor queue -----------------------------------------------------
    def test_doctor_queue_shows_the_real_tickets(self):
        self.checkin(ANA_USER)
        queue = self.client.get("/api/v1/doctor/queue", headers=self.h(key=False)).get_json()["queue"]
        self.assertEqual([t["patient_id"] for t in queue], [ANA])     # the mock always said 1 and 2

    def test_doctor_queue_is_empty_when_nobody_checked_in(self):
        self.assertEqual(self.client.get("/api/v1/doctor/queue", headers=self.h(key=False)).get_json()["queue"], [])

    def test_patient_check_in_is_stored_in_the_database(self):
        self.checkin(BEN_USER)
        self.assertEqual(self.QueueTicket.query.one().patient_id, BEN)

    def test_staff_check_in_of_an_unknown_patient_is_404(self):
        # PostgreSQL rejects a ticket for a patient that does not exist; answer 404, not 500.
        r = self.client.post("/api/v1/patient/queue/checkin", json={"patient_id": 999},
                             headers=self.h(key=False))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.QueueTicket.query.count(), 0)

    # --- consultation -----------------------------------------------------
    def test_consultation_is_saved_with_the_logged_in_doctor(self):
        r = self.consult()
        self.assertEqual(r.status_code, 201, r.get_json())
        row = self.Consultation.query.filter_by(consultation_uid=r.get_json()["consultation_uid"]).one()
        self.assertEqual((row.patient_id, row.doctor_id), (ANA, DOC))
        self.assertEqual(row.directives, {"medication": "Amlodipine 5 mg daily"})
        self.assertEqual(row.notes, "Recheck BP in 2 weeks")

    def test_consultation_closes_the_patients_queue_ticket(self):
        self.checkin(ANA_USER)
        r = self.consult()
        self.assertTrue(r.get_json()["queue_ticket_closed"])
        self.assertEqual(self.QueueTicket.query.one().status, "DONE")

    def test_consultation_is_written_to_the_sealed_audit_log(self):
        from backend.audit import verify_audit
        self.consult()
        entry = self.AuditLedger.query.filter_by(event_type="CONSULTATION_SAVED").one()
        self.assertEqual((entry.patient_id, entry.doctor_id), (ANA, DOC))
        self.assertTrue(verify_audit(entry))

    def test_missing_directives_is_400_naming_the_field(self):
        r = self.client.post("/api/v1/doctor/consultation", json={"patient_id": ANA}, headers=self.h())
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["fields"], ["directives"])
        self.assertEqual(self.Consultation.query.count(), 0)

    def test_unknown_patient_is_404(self):
        self.assertEqual(self.consult(patient_id=999).status_code, 404)

    def test_patient_cannot_write_a_consultation(self):
        self.assertEqual(self.consult(user_id=ANA_USER, role="PATIENT").status_code, 403)

    def test_doctor_account_without_a_profile_is_refused(self):
        r = self.consult(user_id=NO_PROFILE_DOC_USER)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.get_json()["code"], "DOCTOR_PROFILE_MISSING")

    def test_consultation_needs_an_idempotency_key(self):
        self.assertEqual(self.consult(key=False).status_code, 400)

    def test_doctor_lists_a_patients_consultations_newest_first(self):
        self.consult(directives="First visit")
        self.consult(directives="Second visit")
        r = self.client.get(f"/api/v1/doctor/patient/{ANA}/consultations", headers=self.h(key=False))
        self.assertEqual([c["directives"] for c in r.get_json()["consultations"]], ["Second visit", "First visit"])


if __name__ == "__main__":
    unittest.main()
