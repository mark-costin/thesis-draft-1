import sys
import os

# Add parent directory to path for clean imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from dbconnect import db, app
from model_orm.usr_orm import User
from model_orm.pat_orm import Patient
from model_orm.doc_orm import Doctor
from model_orm.adm_orm import Admin

def run_orm_tests():
    with app.app_context():
        print("\n==========================================")
        print("  RUNNING ORM & CASCADE RELATIONSHIP TESTS  ")
        print("==========================================\n")

        # ----------------------------------------------------------------------
        # TEST 1: Forward Relationship (User -> Profile)
        # ----------------------------------------------------------------------
        print("[TEST 1] Testing Forward Navigation (User -> Child Profile)...")
        
        patient_user = User.query.filter_by(username='patient_jane').first()
        doctor_user  = User.query.filter_by(username='doc_smith').first()
        admin_user   = User.query.filter_by(username='admin_user').first()

        assert patient_user and patient_user.patient is not None, "❌ Patient forward relationship failed!"
        print(f"  ✅ User '{patient_user.username}' linked to Patient: {patient_user.patient.first_name} {patient_user.patient.last_name}")

        assert doctor_user and doctor_user.doctor is not None, "❌ Doctor forward relationship failed!"
        print(f"  ✅ User '{doctor_user.username}' linked to Doctor: Dr. {doctor_user.doctor.first_name} {doctor_user.doctor.last_name}")

        assert admin_user and admin_user.admin is not None, "❌ Admin forward relationship failed!"
        print(f"  ✅ User '{admin_user.username}' linked to Admin: {admin_user.admin.first_name} {admin_user.admin.last_name}")

        # ----------------------------------------------------------------------
        # TEST 2: Reverse Relationship (Profile -> User)
        # ----------------------------------------------------------------------
        print("\n[TEST 2] Testing Reverse Navigation (Child Profile -> User)...")
        
        patient_profile = Patient.query.first()
        doctor_profile  = Doctor.query.first()
        admin_profile   = Admin.query.first()

        assert patient_profile and patient_profile.user is not None, "❌ Patient reverse relationship failed!"
        print(f"  ✅ Patient '{patient_profile.first_name}' belongs to Username: '{patient_profile.user.username}'")

        assert doctor_profile and doctor_profile.user is not None, "❌ Doctor reverse relationship failed!"
        print(f"  ✅ Doctor '{doctor_profile.first_name}' belongs to Username: '{doctor_profile.user.username}'")

        assert admin_profile and admin_profile.user is not None, f"❌ Admin '{admin_profile.first_name}' belongs to Username: '{admin_profile.user.username}'"

        # ----------------------------------------------------------------------
        # TEST 3: Foreign Key Cascade Delete Verification
        # ----------------------------------------------------------------------
        print("\n[TEST 3] Testing Foreign Key ON DELETE CASCADE...")
        
        # 1. Create a dummy patient user and profile
        dummy_user = User(username='temp_test_user', password_hash='hash123', role='PATIENT')
        db.session.add(dummy_user)
        db.session.commit()

        dummy_patient = Patient(
            user_id=dummy_user.user_id,
            first_name='Temp',
            last_name='Test',
            date_of_birth='2000-01-01',
            gender='Male',
            address='123 Test St',
            contact_number='0900-000-0000',
            email='temp.test@gmail.com',
            emergency_contact_name='Emergency Contact',
            emergency_contact_number='0900-000-0001',
            emergency_relation='Friend',
            hipaa_consent=True
        )
        db.session.add(dummy_patient)
        db.session.commit()

        dummy_user_id = dummy_user.user_id
        print(f"  Created temporary user ID: {dummy_user_id}")

        # 2. Delete the parent User record
        db.session.delete(dummy_user)
        db.session.commit()
        print(f"  Deleted temporary parent user ID: {dummy_user_id}")

        # 3. Verify that the orphan Patient profile was deleted automatically
        orphan_patient = Patient.query.filter_by(user_id=dummy_user_id).first()
        assert orphan_patient is None, "❌ CASCADE delete failed! Orphan record still exists in patients table."
        print("  ✅ CASCADE DELETE verified: Deleting 'User' automatically purged the linked 'Patient' record.")

        print("\n==========================================")
        print("  🎉 ALL ORM RELATIONSHIP TESTS PASSED SUCCESSFULLY!  ")
        print("==========================================\n")

if __name__ == '__main__':
    run_orm_tests()