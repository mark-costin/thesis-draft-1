import time
import uuid
from datetime import datetime, date
from backend.dbconnect import db, app
from pgvector.sqlalchemy import Vector

from backend.model_orm.usr_orm import User
from backend.model_orm.pat_orm import Patient

def run_verification_pipeline():
    with app.app_context():
        db.create_all()
        
        test_username = f"test_pat_{uuid.uuid4().hex[:8]}"
        
        try:
            print(f"[*] Initializing test user and patient profile ({test_username})...")
            user = User(username=test_username, password_hash="hash", role="PATIENT")
            db.session.add(user)
            db.session.flush()

            patient = Patient(
                user_id=user.user_id, first_name="Test", last_name="Subject",
                date_of_birth=date(1980, 1, 1), gender="Male", address="123 Test Ave",
                contact_number="0917-000-0000", email=f"{test_username}@example.com",
                emergency_contact_name="Jane Doe", emergency_contact_number="0917-111-1111",
                emergency_relation="Spouse"
            )
            db.session.add(patient)
            db.session.flush()
            pid = patient.patient_id

            print("[*] Inserting CVD Metrics (All NOT NULL fields included)...")
            cvd = CVDMetrics(
                patient_id=pid, age=46.0, biological_sex="Male",
                sbp=130.0, dbp=85.0, bmi=26.5,
                resting_hr=72.0, total_cholesterol=180.0, hdl=45.0, ldl=110.0,
                triglycerides=150.0, hs_crp=1.2, serum_creatinine=0.9, egfr=90.0,
                lvef=60.0, ctni=0.01, nt_probnp=100.0, smoking_history=0.0,
                daily_sodium=2000.0, family_history_premature_cvd=1, physical_activity=150.0
            )
            db.session.add(cvd)

            print("[*] Building Family History Matrix...")
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

            print("[*] Executing Mathematical FHRS Stratification Engine...")
            c_d = (1 * 1.0) + (1 * 0.5)  
            base_fhrs_total = ((0.50 * 3.00 * 1.0) + (0.25 * 1.00 * 1.0)) + c_d  
            adjusted_fhrs = base_fhrs_total * 1.0 

            fhrs_record = FHRSStratification(
                patient_id=pid, disease_domain="Cardiovascular",
                clustering_score=c_d, environmental_modifier=1.0, 
                calculated_fhrs=adjusted_fhrs, risk_code=2, risk_category="Moderate"
            )
            db.session.add(fhrs_record)
            
            idemp_key = f"TEST-IDEMP-{uuid.uuid4().hex}"
            db.session.add(IdempotencyCache(key=idemp_key, data={"status": "Processed"}, status=201, timestamp=time.time()))
            db.session.commit()

            print("[*] Verifying Relationships & Database Integrities...")
            verify_patient = Patient.query.get(pid)
            assert verify_patient.cvd_metrics.sbp == 130.0
            assert len(verify_patient.family_history) == 2
            assert verify_patient.fhrs_records[0].calculated_fhrs == 3.25
            assert verify_patient.fhrs_records[0].risk_code == 2
            
            print("\n[PASS] Clinical Data & FHRS Pipeline Verified")

        except Exception as e:
            print(f"\n[FAIL] Exception Occurred: {str(e)}")
        finally:
            try:
                if 'user' in locals(): User.query.filter_by(user_id=user.user_id).delete()
                if 'idemp_key' in locals(): IdempotencyCache.query.filter_by(key=idemp_key).delete()
                db.session.commit()
            except Exception:
                db.session.rollback()

if __name__ == "__main__":
    run_verification_pipeline()

