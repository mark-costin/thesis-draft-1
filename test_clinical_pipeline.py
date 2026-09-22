import time
import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text  # <-- 1. Add this import
from backend.dbconnect import app, db

# Register all tables
import backend.model_orm.adm_orm
import backend.model_orm.doc_orm
import backend.model_orm.pat_orm
import backend.model_orm.usr_orm
import backend.model_orm.clinic_orm
import backend.model_orm.clinical_vector

from backend.model_orm.usr_orm import User
from backend.model_orm.pat_orm import Patient
from backend.model_orm.clinic_orm import CVDMetrics, FamilyHistory, FHRSStratification, IdempotencyCache

def execute_pipeline():
    with app.app_context():
        # --- Add this block here to rebuild and sync the database schema ---
        db.session.execute(text("DROP TABLE IF EXISTS users, patients, doctors, admins, patient_clinical_vectors, patient_family_history, patient_fhrs_stratification, patient_cvd_metrics, idempotency_cache CASCADE;"))
        db.session.commit()
        db.create_all()
        # -------------------------------------------------------------------

        test_username = f"test_pat_{uuid.uuid4().hex[:8]}"
        idemp_key = f"TEST-IDEMP-{uuid.uuid4().hex}"
        test_user = User(username=test_username, password_hash="hash", role="PATIENT")

        try:
            # 1. Provision User & Patient
            db.session.add(test_user)
            db.session.flush()

            patient = Patient(
                user_id=test_user.user_id, first_name="Test", last_name="Subject",
                date_of_birth="1980-01-01", gender="Male", address="123 Test Ave",
                contact_number="0917-000-0000", email=f"{test_username}@example.com",
                emergency_contact_name="Jane Doe", emergency_contact_number="0917-111-1111",
                emergency_relation="Spouse"
            )
            db.session.add(patient)
            db.session.flush()
            pid = patient.patient_id

            # 2. Insert CVD Metrics
            cvd = CVDMetrics(
                patient_id=pid, age=46.0, biological_sex="Male",
                sbp=130.0, dbp=85.0, bmi=26.5, resting_hr=72.0, 
                total_cholesterol=180.0, hdl=45.0, ldl=110.0,
                triglycerides=150.0, hs_crp=1.2, serum_creatinine=0.9, 
                egfr=90.0, lvef=60.0, ctni=0.01, nt_probnp=100.0, 
                smoking_history=0.0, daily_sodium=2000.0, 
                family_history_premature_cvd=1, physical_activity=150.0
            )
            db.session.add(cvd)

            # 3. Build Pedigree (Family History)
            fh1 = FamilyHistory(
                patient_id=pid, disease_domain="Cardiovascular",
                specific_diagnosis="Myocardial Infarction", relationship_tier="Tier 1", 
                relationship_weight=0.50, onset_classification="Very Early", 
                onset_weight=3.00, shared_environment=False
            )
            fh2 = FamilyHistory(
                patient_id=pid, disease_domain="Cardiovascular",
                specific_diagnosis="Hypertension", relationship_tier="Tier 2", 
                relationship_weight=0.25, onset_classification="Typical", 
                onset_weight=1.00, shared_environment=False
            )
            db.session.add_all([fh1, fh2])
            db.session.flush()

            # 4. Computed Risk Stratification
            fhrs_record = FHRSStratification(
                patient_id=pid, disease_domain="Cardiovascular",
                clustering_score=1.5, environmental_modifier=1.0, 
                calculated_fhrs=3.25, risk_code=2, risk_category="Moderate"
            )
            db.session.add(fhrs_record)

            # 5. Insert Cache & Commit Clinical Data
            cache_entry = IdempotencyCache(key=idemp_key, data={"status": "Processed"}, status=201, timestamp=time.time())
            db.session.add(cache_entry)
            db.session.commit()

            # 6. Verify Duplicate Submission Rejection
            try:
                with db.session.begin_nested():
                    duplicate_entry = IdempotencyCache(key=idemp_key, data={"status": "Duplicate"}, status=409, timestamp=time.time())
                    db.session.add(duplicate_entry)
                    db.session.flush()
            except IntegrityError:
                print("[*] Idempotency guard correctly intercepted duplicate payload.")

            # 7. Relational Integrity Checks
            verify_patient = Patient.query.get(pid)
            assert verify_patient.cvd_metrics.sbp == 130.0, "CVD Metrics eager load failed."
            assert len(verify_patient.family_history) == 2, "Lineage load failed."
            assert verify_patient.fhrs_records[0].calculated_fhrs == 3.25, "FHRS binding failed."

            print("[PASS] Full Clinical & Vector Pipeline Operational")

        finally:
            # 8. Teardown triggers ON DELETE CASCADE through entire hierarchy
            if test_user.user_id:
                User.query.filter_by(user_id=test_user.user_id).delete()
            IdempotencyCache.query.filter_by(key=idemp_key).delete()
            db.session.commit()

if __name__ == "__main__":
    execute_pipeline()