"""Batch 3 routes against a real SQLite database: login, registration, doctor verification.

Needs: flask_sqlalchemy, bcrypt, pgvector (runs on your machine; skipped where missing).
"""
import os
import unittest
from datetime import date

from tests._helpers import has_modules, make_token

DB_STACK = has_modules("flask_sqlalchemy", "bcrypt", "pgvector")
LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"
PASSWORD = "correct-horse-1"

ADMIN_USER = 1
DOC_OK_USER, DOC_OK = 10, 1
DOC_PENDING_USER, DOC_PENDING = 11, 2
PAT_USER, PAT = 20, 5
PAT_INACTIVE_USER, PAT_INACTIVE = 21, 6

REGISTRATION = {
    "username": "new_patient", "password": PASSWORD,
    "first_name": "Jane", "last_name": "Cruz", "date_of_birth": "1990-05-14", "gender": "Female",
    "address": "1 Test St", "contact_number": "0900-000-0000", "email": "new.patient@example.com",
    "emergency_contact_name": "Ana", "emergency_contact_number": "0900-000-0001",
    "emergency_relation": "Sister", "hipaa_consent": True,
}
PROVISION = {
    "username": "dr_reyes", "password": "correct-horse-2",
    "first_name": "Luis", "last_name": "Reyes", "address": "2 Clinic Rd",
    "specialization": "Cardiology", "license_number": "PRC-0042",
    "contact_number": "0900-000-0002", "email": "reyes@example.com",
    "emergency_contact_name": "Maria", "emergency_contact_number": "0900-000-0003",
    "emergency_relation": "Spouse",
}


def _person(prefix):
    return dict(first_name=f"{prefix}First", last_name=f"{prefix}Last", address="1 Test St",
                contact_number="0900-000-0000", email=f"{prefix.lower()}@example.com",
                emergency_contact_name="Contact", emergency_contact_number="0900-000-0001",
                emergency_relation="Sibling")


@unittest.skipUnless(DB_STACK, "needs flask_sqlalchemy + bcrypt + pgvector (runs on your machine)")
class AccountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = "sqlite://"
        from flask import Flask
        from backend.dbconnect import db, init_db
        import backend.model_orm  # noqa: F401
        from backend.routes.admin import admin_bp
        from backend.routes.auth0 import auth_bp

        app = Flask(__name__)
        init_db(app)
        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp)
        cls.app, cls.db = app, db
        with app.app_context():
            db.create_all()

    def setUp(self):
        from backend.model_orm import Admin, Doctor, IdempotencyCache, Patient, User
        self.User, self.Doctor, self.Patient = User, Doctor, Patient
        self.ctx = self.app.app_context()
        self.ctx.push()
        s = self.db.session
        for model in (IdempotencyCache, Patient, Doctor, Admin, User):
            s.query(model).delete()
        for user_id, username, role in ((ADMIN_USER, "admin", "ADMIN"), (DOC_OK_USER, "doc_ok", "DOCTOR"),
                                        (DOC_PENDING_USER, "doc_pending", "DOCTOR"), (PAT_USER, "pat", "PATIENT"),
                                        (PAT_INACTIVE_USER, "pat_inactive", "PATIENT")):
            u = User(user_id=user_id, username=username, role=role)
            u.set_password(PASSWORD)
            s.add(u)
        s.flush()
        s.add(Doctor(doctor_id=DOC_OK, user_id=DOC_OK_USER, specialization="IM", license_number="PRC-1",
                     is_verified=True, **_person("DocOk")))
        s.add(Doctor(doctor_id=DOC_PENDING, user_id=DOC_PENDING_USER, specialization="IM", license_number="PRC-2",
                     is_verified=False, **_person("DocPending")))
        s.add(Patient(patient_id=PAT, user_id=PAT_USER, date_of_birth=date(1980, 1, 1), gender="Female",
                      hipaa_consent=True, **_person("Pat")))
        s.add(Patient(patient_id=PAT_INACTIVE, user_id=PAT_INACTIVE_USER, date_of_birth=date(1980, 1, 1),
                      gender="Male", hipaa_consent=True, is_active=False, **_person("PatInactive")))
        s.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        self.db.session.rollback()
        self.ctx.pop()

    def login(self, username, password=PASSWORD):
        return self.client.post(LOGIN, json={"username": username, "password": password})

    def admin(self, method, path, **kw):
        headers = {"Authorization": f"Bearer {make_token(user_id=ADMIN_USER, role='ADMIN')}",
                   "Idempotency-Key": f"{method}-{path}"}
        return getattr(self.client, method)(f"/api/v1/admin{path}", headers=headers, **kw)

    def user(self, user_id):
        self.db.session.expire_all()
        return self.db.session.get(self.User, user_id)

    # --- login does not reveal which accounts exist ------------------------
    def test_unknown_user_and_wrong_password_get_identical_responses(self):
        unknown = self.login("no_such_user", "whatever-123")
        wrong = self.login("pat", "wrong-password")
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(unknown.get_json(), wrong.get_json())

    def test_locked_account_gets_the_same_response(self):
        u = self.user(PAT_USER)
        u.is_locked = True
        self.db.session.commit()
        locked = self.login("pat")  # correct password
        self.assertEqual(locked.status_code, 401)
        self.assertEqual(locked.get_json(), self.login("no_such_user", "x" * 8).get_json())

    def test_five_wrong_passwords_lock_the_account(self):
        for _ in range(5):
            self.login("pat", "wrong-password")
        self.assertTrue(self.user(PAT_USER).is_locked)

    def test_failed_attempts_null_does_not_crash(self):
        u = self.user(PAT_USER)
        u.failed_attempts = None
        self.db.session.commit()
        self.assertEqual(self.login("pat", "wrong-password").status_code, 401)

    def test_empty_login_body_is_400_not_500(self):
        r = self.client.post(LOGIN, data="", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    # --- who may log in ---------------------------------------------------
    def test_verified_doctor_can_log_in(self):
        self.assertEqual(self.login("doc_ok").status_code, 200)

    def test_unverified_doctor_cannot_log_in(self):
        r = self.login("doc_pending")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.get_json()["code"], "ACCOUNT_PENDING_VERIFICATION")

    def test_inactive_patient_cannot_log_in(self):
        r = self.login("pat_inactive")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.get_json()["code"], "ACCOUNT_INACTIVE")

    def test_new_doctor_rows_default_to_unverified(self):
        u = self.User(user_id=30, username="doc_new", role="DOCTOR", password_hash="x")
        self.db.session.add(u)
        self.db.session.flush()
        d = self.Doctor(user_id=30, specialization="IM", license_number="PRC-30", **_person("DocNew"))
        self.db.session.add(d)
        self.db.session.commit()
        self.assertFalse(d.is_verified)

    # --- registration -----------------------------------------------------
    def test_registration_requires_consent(self):
        r = self.client.post(REGISTER, json={**REGISTRATION, "hipaa_consent": False})
        self.assertEqual(r.status_code, 400)

    def test_registration_rejects_bad_date(self):
        r = self.client.post(REGISTER, json={**REGISTRATION, "date_of_birth": "14/05/1990"})
        self.assertEqual(r.status_code, 400)

    def test_registration_stores_a_real_date_and_consent(self):
        r = self.client.post(REGISTER, json=REGISTRATION)
        self.assertEqual(r.status_code, 201, r.get_json())
        p = self.Patient.query.filter_by(email=REGISTRATION["email"]).one()
        self.assertEqual(p.date_of_birth, date(1990, 5, 14))
        self.assertTrue(p.hipaa_consent)
        self.assertEqual(p.user.role, "PATIENT")

    def test_duplicate_username_is_409_and_next_registration_still_works(self):
        dup = self.client.post(REGISTER, json={**REGISTRATION, "username": "pat"})
        self.assertEqual(dup.status_code, 409)
        ok = self.client.post(REGISTER, json=REGISTRATION)
        self.assertEqual(ok.status_code, 201, ok.get_json())

    # --- admin: provision, verify, unlock ----------------------------------
    def test_provision_creates_an_unverified_doctor(self):
        r = self.admin("post", "/provision", json=PROVISION)
        self.assertEqual(r.status_code, 201, r.get_json())
        d = self.Doctor.query.filter_by(license_number="PRC-0042").one()
        self.assertFalse(d.is_verified)
        self.assertEqual(d.user.role, "DOCTOR")
        self.assertEqual(self.login("dr_reyes", "correct-horse-2").status_code, 403)

    def test_provision_duplicate_license_is_409(self):
        r = self.admin("post", "/provision", json={**PROVISION, "license_number": "PRC-1"})
        self.assertEqual(r.status_code, 409)

    def test_provision_missing_field_is_400(self):
        r = self.admin("post", "/provision", json={**PROVISION, "license_number": ""})
        self.assertEqual(r.status_code, 400)

    def test_doctor_cannot_provision(self):
        headers = {"Authorization": f"Bearer {make_token(user_id=DOC_OK_USER, role='DOCTOR')}",
                   "Idempotency-Key": "doc-provision"}
        r = self.client.post("/api/v1/admin/provision", json=PROVISION, headers=headers)
        self.assertEqual(r.status_code, 403)

    def test_admin_verification_lets_the_doctor_log_in(self):
        r = self.admin("post", f"/doctors/{DOC_PENDING}/verify")
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(self.login("doc_pending").status_code, 200)

    def test_verify_unknown_doctor_is_404(self):
        self.assertEqual(self.admin("post", "/doctors/999/verify").status_code, 404)

    def test_admin_unlock_clears_the_lock(self):
        u = self.user(PAT_USER)
        u.is_locked, u.failed_attempts = True, 5
        self.db.session.commit()
        self.assertEqual(self.admin("post", f"/users/{PAT_USER}/unlock").status_code, 200)
        u = self.user(PAT_USER)
        self.assertFalse(u.is_locked)
        self.assertEqual(u.failed_attempts, 0)
        self.assertEqual(self.login("pat").status_code, 200)


if __name__ == "__main__":
    unittest.main()
