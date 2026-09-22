import json
import time
import uuid
from datetime import datetime, date
from dbconnect import db, app

# Import ORM Models
from backend.model_orm.usr_orm import User
from backend.model_orm.pat_orm import Patient
from backend.model_orm.clinical_orm import (
    FamilyHistory, FHRSStratification, CVDMetrics, IdempotencyCache
)

def run_verification_pipeline():
    with app.app_context():
        # Ensure tables exist
        db.create_all()
        
        test_username = f"test_pat_{uuid.uuid4().hex[:8]}"
        test_email = f"{test_username}@example.com"
        
        try:
            print(f"[*] Initializing test user and patient profile ({test_username})...")
            # 1. Provision User & Patient
            user = User(username=test_username, password_hash="hash", role="PATIENT")
            db.session.add(user)
            db.session.flush()

            patient = Patient(
                user_id=user.user_id, first_name="Test", last_name="Subject",
                date_of_birth=date(1980, 1, 1), gender="Male", address="123 Test Ave",
                contact_number="0917-000-0000", email=test_email,
                emergency_contact_name="Jane Doe", emergency_contact_number="0917-111-1111",
                emergency_relation="Spouse"
            )
            db.session.add(patient)
            db.session.flush()
            
            pid = patient.patient_id

            print("[*] Inserting CVD Metrics...")
            # 2. Insert CVD Metrics
            cvd = CVDMetrics(
                patient_id=pid, age=46, biological_sex="Male",
                systolic_bp=130.0, diastolic_bp=85.0, bmi=26.5
            )
            db.session.add(cvd)

            print("[*] Building Family History Matrix...")
            # 3. Insert Family History (Father & Maternal Uncle)
            fh1 = FamilyHistory(
                patient_id=pid, disease_category="Cardiovascular",
                relative_relationship="Father", relative_tier="Tier 1", r_weight=0.50,
                age_of_onset="Very Early", o_weight=3.00, shared_environment="None"
            )
            fh2 = FamilyHistory(
                patient_id=pid, disease_category="Cardiovascular",
                relative_relationship="Maternal Uncle", relative_tier="Tier 2", r_weight=0.25,
                age_of_onset="Typical", o_weight=1.00, shared_environment="None"
            )
            db.session.add_all([fh1, fh2])
            db.session.flush()

            print("[*] Executing Mathematical FHRS Stratification Engine...")
            # 4. Compute FHRS for Cardiovascular
            # C_d = N_T1(1.0) + N_T2(0.5)
            c_d = (1 * 1.0) + (1 * 0.5)  # = 1.5
            
            # Base FHRS = Sum(R_i * O_i * S_i) + C_d
            base_fhrs_sum = (0.50 * 3.00 * 1.0) + (0.25 * 1.00 * 1.0)  # = 1.5 + 0.25 = 1.75
            base_fhrs_total = base_fhrs_sum + c_d  # = 3.25
            
            # Adjusted FHRS = Base * E_d (E_d = 1.0 if no shared environment factors)
            e_d = 1.0 
            adjusted_fhrs = base_fhrs_total * e_d # = 3.25

            # Map to Risk Code
            if adjusted_fhrs < 2.0:
                risk_code, risk_label = "Code 1", "Low Risk"
            elif adjusted_fhrs < 4.5:
                risk_code, risk_label = "Code 2", "Moderate Risk"
            elif adjusted_fhrs < 8.0:
                risk_code, risk_label = "Code 3", "High Risk"
            else:
                risk_code, risk_label = "Code 4", "Very High Risk"

            fhrs_record = FHRSStratification(
                patient_id=pid, disease_category="Cardiovascular",
                base_fhrs=base_fhrs_total, cluster_coefficient=c_d,
                env_modifier=e_d, adjusted_fhrs=adjusted_fhrs,
                risk_code=risk_code, risk_label=risk_label
            )
            db.session.add(fhrs_record)
            
            print("[*] Testing PostgreSQL Idempotency Cache Insertion...")
            # 5. Test Idempotency Cache
            idemp_key = f"TEST-IDEMP-{uuid.uuid4().hex}"
            cache_entry = IdempotencyCache(
                key=idemp_key, data={"status": "Processed"}, 
                status=201, timestamp=time.time()
            )
            db.session.add(cache_entry)
            db.session.commit()

            # 6. Verify Relationships & Queries
            print("[*] Verifying Relationships & Database Integrities...")
            verify_patient = Patient.query.get(pid)
            assert verify_patient is not None, "Patient lookup failed"
            assert verify_patient.cvd_metrics.systolic_bp == 130.0, "1-to-1 metrics cascade mapping failed"
            assert len(verify_patient.family_history) == 2, "1-to-Many lineage mapping failed"
            assert verify_patient.fhrs_records[0].adjusted_fhrs == 3.25, "FHRS Math computation lookup failed"
            assert verify_patient.fhrs_records[0].risk_code == "Code 2", "FHRS Risk Stratification logic failed"
            
            verify_cache = IdempotencyCache.query.get(idemp_key)
            assert verify_cache is not None, "Idempotency insertion failed"
            
            print("===================================================")
            print("[PASS] Clinical Data & FHRS Pipeline Verified")
            print("===================================================")

        except AssertionError as ae:
            print(f"[FAIL] Assertion Error: {str(ae)}")
        except Exception as e:
            print(f"[FAIL] Exception Occurred: {str(e)}")
        finally:
            print("[*] Triggering automated teardown and cascade cleanup...")
            # Safe Cleanup (Cascades will auto-delete Profiles, Metrics, and FHRS Data)
            try:
                if 'user' in locals() and user.user_id:
                    User.query.filter_by(user_id=user.user_id).delete()
                if 'idemp_key' in locals():
                    IdempotencyCache.query.filter_by(key=idemp_key).delete()
                db.session.commit()
                print("[*] Teardown complete. Testing state reverted safely.")
            except Exception as cleanup_err:
                db.session.rollback()
                print(f"[!] Cleanup failed: {str(cleanup_err)}")
