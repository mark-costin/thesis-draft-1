import uuid
import random
from sqlalchemy import text  # <-- Add this import
from backend.dbconnect import app, db

# --- Add these imports so SQLAlchemy registers all tables ---
import backend.model_orm.adm_orm
import backend.model_orm.doc_orm
import backend.model_orm.pat_orm
import backend.model_orm.usr_orm
import backend.model_orm.clinic_orm
import backend.model_orm.clinical_vector
# ------------------------------------------------------------

from backend.model_orm.clinical_vector import ClinicalVector 
from backend.model_orm.pat_orm import Patient
from backend.model_orm.usr_orm import User

with app.app_context():
    # --- Force drop the tables and everything attached to them, then rebuild ---
    db.session.execute(text("DROP TABLE IF EXISTS users, patients, doctors, admins CASCADE;"))
    db.session.commit()
    db.create_all()
    # ---------------------------------------------------------------------------

    # 1. Create a dummy patient
    test_user = User(username=f"vectest_{uuid.uuid4().hex[:6]}", password_hash="dummy", role="PATIENT")
    db.session.add(test_user)
    db.session.flush()

    test_patient = Patient(
        user_id=test_user.user_id, first_name="Vector", last_name="Test",
        date_of_birth="1990-01-01", gender="Male", address="Test",
        contact_number="000", email=f"{test_user.username}@test.com",
        emergency_contact_name="None", emergency_contact_number="000", emergency_relation="None"
    )
    db.session.add(test_patient)
    db.session.flush()

    # 2. Insert a 384-dimensional zero/sample vector
    sample_vector = [0.0] * 384
    sample_vector[0] = 1.0  # simple unit vector
    
    vec_entry = ClinicalVector(
        patient_id=test_patient.patient_id,
        disease_narrative="Patient presents with acute shortness of breath and familial history of CAD.",
        embedding=sample_vector
    )
    db.session.add(vec_entry)
    db.session.commit()

    # 3. Test nearest-neighbor query
    results = db.session.query(
        ClinicalVector.patient_id,
        ClinicalVector.embedding.cosine_distance(sample_vector).label('distance')
    ).all()

    print(f"[PASS] Successfully queried {len(results)} vector record(s). Distance: {results[0].distance}")

    # 4. Clean up
    User.query.filter_by(user_id=test_user.user_id).delete()
    db.session.commit()
    print("[PASS] Test cleanup complete.")