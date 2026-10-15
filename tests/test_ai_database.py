"""AI <-> database, end to end on a real SQLite database.

Biomarkers are stored through the API, inference reads them back from the database,
and every inference and encounter commit is written to a sealed audit ledger.

Needs: flask_sqlalchemy, bcrypt, pgvector (runs on your machine; skipped where missing).
"""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tests._helpers import FixedProbabilityModel, has_modules, make_token, write_model

DB_STACK = has_modules("flask_sqlalchemy", "bcrypt", "pgvector")

DOC_USER, DOC = 10, 1
ANA_USER, ANA = 20, 5
BEN_USER, BEN = 21, 6
BIO = "/api/v1/biomarkers"


def _person(prefix):
    return dict(first_name=f"{prefix}First", last_name=f"{prefix}Last", address="1 Test St",
                contact_number="0900-000-0000", email=f"{prefix.lower()}@example.com",
                emergency_contact_name="Contact", emergency_contact_number="0900-000-0001",
                emergency_relation="Sibling")


@unittest.skipUnless(DB_STACK, "needs flask_sqlalchemy + bcrypt + pgvector (runs on your machine)")
class AiDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = "sqlite://"
        from flask import Flask
        from backend.dbconnect import db, init_db
        import backend.model_orm  # noqa: F401  registers every table, audit_ledger included
        from backend.routes.biomarkers import biomarkers_bp
        from backend.routes.doctor import doctor_bp
        from backend.routes.predictions import predictions_bp

        app = Flask(__name__)
        init_db(app)
        for bp in (biomarkers_bp, doctor_bp, predictions_bp):
            app.register_blueprint(bp)
        cls.app, cls.db = app, db
        with app.app_context():
            db.create_all()

    def setUp(self):
        from backend.cdss.model_loader import ModelRegistry
        from backend.model_orm import AuditLedger, CVDMetrics, Doctor, IdempotencyCache, Patient, T2DMetrics, User
        from backend.model_orm.clinic_orm import Encounter
        import backend.cdss.engine as engine
        self.AuditLedger, self.CVDMetrics, self.Encounter = AuditLedger, CVDMetrics, Encounter

        self.tmp = tempfile.TemporaryDirectory()
        write_model(self.tmp.name, model=FixedProbabilityModel(0.55))  # features: age, systolic_bp
        self.registry_patch = patch.object(engine, "registry", ModelRegistry(model_dir=Path(self.tmp.name)))
        self.registry_patch.start()

        self.ctx = self.app.app_context()
        self.ctx.push()
        s = self.db.session
        for model in (AuditLedger, Encounter, CVDMetrics, T2DMetrics, IdempotencyCache, Patient, Doctor, User):
            s.query(model).delete()
        s.add_all([
            User(user_id=DOC_USER, username="doc", role="DOCTOR", password_hash="x"),
            User(user_id=ANA_USER, username="ana", role="PATIENT", password_hash="x"),
            User(user_id=BEN_USER, username="ben", role="PATIENT", password_hash="x"),
        ])
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
        self.registry_patch.stop()
        self.tmp.cleanup()

    # --- helpers ----------------------------------------------------------
    def h(self, user_id=DOC_USER, role="DOCTOR", key=True):
        self.n += 1
        headers = {"Authorization": f"Bearer {make_token(user_id=user_id, role=role)}"}
        if key:
            headers["Idempotency-Key"] = f"k-{self.n}"
        return headers

    def store(self, modality="cvd", patient_id=ANA, values=None, **kw):
        body = {"patient_id": patient_id, "values": values if values is not None else {"age": 58, "sbp": 142}}
        return self.client.post(f"{BIO}/{modality}", json=body, headers=self.h(**kw))

    # --- tables -----------------------------------------------------------
    def test_audit_ledger_table_is_created(self):
        from sqlalchemy import inspect
        tables = inspect(self.db.engine).get_table_names()
        self.assertIn("audit_ledger", tables)
        self.assertNotIn("baseline_records", tables)

    # --- storing biomarkers -------------------------------------------------
    def test_doctor_stores_cvd_biomarkers(self):
        r = self.store()
        self.assertEqual(r.status_code, 201, r.get_json())
        row = self.CVDMetrics.query.filter_by(patient_id=ANA).one()
        self.assertEqual(float(row.sbp), 142.0)

    def test_latest_biomarkers_are_returned(self):
        self.store(values={"age": 58, "sbp": 142})
        self.store(values={"age": 58, "sbp": 128})
        r = self.client.get(f"{BIO}/cvd/latest?patient_id={ANA}", headers=self.h(key=False))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["values"]["sbp"], 128.0)

    def test_unknown_field_is_rejected(self):
        r = self.store(values={"systolic": 142})
        self.assertEqual(r.status_code, 400)
        self.assertIn("systolic", r.get_json()["fields"])

    def test_value_too_large_for_column_is_400_not_500(self):
        r = self.store(modality="t2d", values={"hba1c": 1000})
        self.assertEqual(r.status_code, 400)
        self.assertIn("hba1c", r.get_json()["fields"])

    def test_patient_cannot_store_biomarkers(self):
        r = self.store(user_id=ANA_USER, role="PATIENT")
        self.assertEqual(r.status_code, 403)

    def test_patient_reads_only_own_latest_biomarkers(self):
        self.store(patient_id=ANA, values={"sbp": 142})
        self.store(patient_id=BEN, values={"sbp": 99})
        r = self.client.get(f"{BIO}/cvd/latest?patient_id={BEN}", headers=self.h(ANA_USER, "PATIENT", key=False))
        self.assertEqual(r.get_json()["values"]["sbp"], 142.0)

    def test_unknown_modality_is_404(self):
        self.assertEqual(self.store(modality="kidney").status_code, 404)

    def test_unknown_patient_is_404(self):
        self.assertEqual(self.store(patient_id=999).status_code, 404)

    def test_storing_requires_idempotency_key(self):
        r = self.client.post(f"{BIO}/cvd", json={"patient_id": ANA, "values": {"sbp": 1}},
                             headers=self.h(key=False))
        self.assertEqual(r.status_code, 400)

    # --- inference reads the database and is audited -------------------------
    def test_inference_uses_stored_biomarkers(self):
        self.store(values={"age": 58, "sbp": 142})
        r = self.client.post("/api/v1/predictions/infer", json={"patient_id": ANA, "modality": "cvd"},
                             headers=self.h(key=False))
        body = r.get_json()
        self.assertEqual(r.status_code, 200, body)
        self.assertEqual(body["biomarker_source"], "database")
        self.assertEqual(body["missing_features"], [])
        self.assertEqual(body["risk"]["tier"], "HIGH")

    def test_inference_writes_a_sealed_audit_entry(self):
        from backend.audit import verify_audit
        r = self.client.post("/api/v1/predictions/infer",
                             json={"patient_id": ANA, "modality": "cvd", "biomarker_payload": {"age": 50, "sbp": 130}},
                             headers=self.h(key=False))
        audit_id = r.get_json()["audit_id"]
        self.db.session.expire_all()
        entry = self.AuditLedger.query.filter_by(audit_id=audit_id).one()
        self.assertEqual(entry.event_type, "INFERENCE")
        self.assertEqual(entry.patient_id, ANA)
        self.assertEqual(entry.actor_user_id, DOC_USER)
        self.assertTrue(verify_audit(entry))

    def test_editing_an_audit_entry_breaks_its_seal(self):
        from backend.audit import verify_audit
        r = self.client.post("/api/v1/predictions/infer",
                             json={"patient_id": ANA, "modality": "cvd", "biomarker_payload": {"age": 50, "sbp": 130}},
                             headers=self.h(key=False))
        entry = self.AuditLedger.query.filter_by(audit_id=r.get_json()["audit_id"]).one()
        entry.payload = {**entry.payload, "tier": "LOW"}
        self.db.session.commit()
        self.db.session.expire_all()
        self.assertFalse(verify_audit(self.AuditLedger.query.filter_by(audit_id=entry.audit_id).one()))

    def test_inference_for_unknown_patient_is_404(self):
        r = self.client.post("/api/v1/predictions/infer", json={"patient_id": 999, "modality": "cvd"},
                             headers=self.h(key=False))
        self.assertEqual(r.status_code, 404)

    # --- encounter commits are audited ---------------------------------------
    def test_commit_encounter_writes_an_audit_entry(self):
        from backend.audit import verify_audit
        r = self.client.post("/api/v1/doctor/commit-encounter", headers=self.h(),
                             json={"patient_id": ANA, "encounter_type": "BASELINE",
                                   "cdss_payload_snapshot": {"risk": {"tier": "HIGH"}}, "care_plan": {"directive": "x"}})
        self.assertEqual(r.status_code, 201, r.get_json())
        entries = self.AuditLedger.query.filter_by(event_type="ENCOUNTER_COMMITTED").all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].payload["encounter_id"], r.get_json()["encounter_id"])
        self.assertTrue(verify_audit(entries[0]))


if __name__ == "__main__":
    unittest.main()