import os
import datetime
import jwt
from flask import Blueprint, request, jsonify
from dbconnect import db
from sqlalchemy.exc import IntegrityError

# Import Models
from backend.model_orm.usr_orm import User
from backend.model_orm.pat_orm import Patient
from backend.model_orm.doc_orm import Doctor
from backend.model_orm.adm_orm import Admin

# Import Middleware
from backend.middleware.sanitizer import sanitize_response
from backend.middleware.rbac import role_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

JWT_SECRET = os.environ.get("JWT_SECRET", "clinical-platform-default-jwt-secret-key")
JWT_ALGORITHM = "HS256"

@auth_bp.route('/register', methods=['POST'])
def register_patient():
    """
    Patient Self-Service Registration.
    Strictly enforces the 'PATIENT' role to prevent Privilege Escalation.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid payload"}), 400

    username = data.get("username")
    password = data.get("password")
    
    # Required core profile fields
    required_fields = [
        "first_name", "last_name", "date_of_birth", "gender", 
        "address", "contact_number", "email", 
        "emergency_contact_name", "emergency_contact_number", "emergency_relation"
    ]
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
        
    if len(password) < 8:
        return jsonify({"error": "Password does not meet minimum strength requirements (8 characters)"}), 400

    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({"error": f"Missing required profile fields: {', '.join(missing)}"}), 400

    # Ensure role immutability
    assigned_role = "PATIENT"

    try:
        # Wrap creation in a transactional block
        with db.session.begin_nested():
            # Check duplicates
            if User.query.filter_by(username=username).first():
                return jsonify({"error": "Username is already taken"}), 409
            if Patient.query.filter_by(email=data.get("email")).first():
                return jsonify({"error": "Email is already registered to a patient profile"}), 409

            # 1. Create Base User
            new_user = User(username=username, role=assigned_role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush() # Flush to get new_user.user_id

            # 2. Create Linked Patient Profile
            new_patient = Patient(
                user_id=new_user.user_id,
                first_name=data.get("first_name"),
                middle_name=data.get("middle_name"),
                last_name=data.get("last_name"),
                date_of_birth=data.get("date_of_birth"),
                gender=data.get("gender"),
                religion=data.get("religion"),
                address=data.get("address"),
                contact_number=data.get("contact_number"),
                email=data.get("email"),
                emergency_contact_name=data.get("emergency_contact_name"),
                emergency_contact_number=data.get("emergency_contact_number"),
                emergency_relation=data.get("emergency_relation"),
                hipaa_consent=data.get("hipaa_consent", False)
            )
            db.session.add(new_patient)

        db.session.commit()
        
        # Serialize and sanitize response
        profile_dict = {column.name: getattr(new_patient, column.name) for column in new_patient.__table__.columns}
        sanitized_profile = sanitize_response(profile_dict, role=assigned_role)
        
        return jsonify({
            "message": "Patient profile successfully created",
            "profile": sanitized_profile
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity constraint violated"}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An internal error occurred during registration"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Unified Authentication endpoint for Patients, Doctors, and Admins.
    """
    data = request.get_json()
    identifier = data.get("username") # Can be username or email
    password = data.get("password")

    if not identifier or not password:
        return jsonify({"error": "Username/Email and password are required"}), 400

    # Locate user by username OR associated profile email
    user = User.query.outerjoin(Patient).outerjoin(Doctor).outerjoin(Admin).filter(
        (User.username == identifier) | 
        (Patient.email == identifier) | 
        (Doctor.email == identifier) | 
        (Admin.email == identifier)
    ).first()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if user.is_locked:
        return jsonify({"error": "Account is locked due to multiple failed login attempts. Contact administration."}), 403

    if not user.check_password(password):
        user.record_failed_attempt()
        db.session.commit()
        remaining = 5 - user.failed_attempts
        return jsonify({"error": f"Invalid credentials. {remaining} attempt(s) remaining before lockout."}), 401

    # On success: clear lockout
    user.reset_lockout()
    db.session.commit()

    # Generate JWT
    exp_time = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    payload = {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "token_version": user.token_version,
        "exp": exp_time
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    # Hydrate profile data based on role
    profile_data = {}
    if user.role == "PATIENT" and user.patient:
        profile_data = {c.name: getattr(user.patient, c.name) for c in user.patient.__table__.columns}
    elif user.role in ["DOCTOR", "CLINICIAN"] and user.doctor:
        profile_data = {c.name: getattr(user.doctor, c.name) for c in user.doctor.__table__.columns}
    elif user.role in ["ADMIN", "SYSTEM_ADMIN", "IT_SUPPORT"] and user.admin:
        profile_data = {c.name: getattr(user.admin, c.name) for c in user.admin.__table__.columns}

    # Sanitize payload output
    sanitized_user = sanitize_response(user.to_dict(), role=user.role)
    sanitized_profile = sanitize_response(profile_data, role=user.role)

    return jsonify({
        "access_token": token,
        "token_type": "Bearer",
        "user": sanitized_user,
        "profile": sanitized_profile
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@role_required(["PATIENT", "DOCTOR", "CLINICIAN", "ADMIN", "SYSTEM_ADMIN", "IT_SUPPORT", "COMPLIANCE_AUDITOR"])
def logout():
    """
    Invalidates all active tokens for the user by incrementing the token_version.
    """
    current_user_claims = request.current_user
    user_id = current_user_claims.get("user_id")

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User record not found"}), 404

    # Incrementing token_version ensures any previously issued JWT is now considered invalid
    # (Requires updating the @role_required middleware to check token_version against the DB if strict state is desired)
    user.token_version += 1
    db.session.commit()

    return jsonify({"message": "Successfully logged out across all active sessions"}), 200