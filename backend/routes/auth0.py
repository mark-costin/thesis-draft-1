import datetime
import logging
import bcrypt
import jwt
from flask import Blueprint, request, jsonify
from backend.dbconnect import db
from sqlalchemy.exc import IntegrityError

# Import Models
from backend.model_orm.usr_orm import User
from backend.model_orm.pat_orm import Patient
from backend.model_orm.doc_orm import Doctor
from backend.model_orm.adm_orm import Admin

# Import Middleware
from backend.middleware.sanitizer import sanitize_response
from backend.middleware.rbac import role_required
from backend.config import JWT_SECRET, JWT_ALGORITHM
from backend.validation import ValidationError, validate_registration

log = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

DOCTOR_ROLES = ("DOCTOR", "CLINICIAN")

# Checked against when the username does not exist, so an unknown username takes as long
# as a wrong password and response timing does not reveal which accounts exist.
_DUMMY_HASH = bcrypt.hashpw(b"timing-equalizer", bcrypt.gensalt())


def _invalid_credentials():
    """One response for unknown user, wrong password and locked account."""
    return jsonify({"status": "error", "code": "INVALID_CREDENTIALS",
                    "error": "Invalid credentials"}), 401


@auth_bp.route('/register', methods=['POST'])
def register_patient():
    """
    Patient Self-Service Registration.
    Strictly enforces the 'PATIENT' role to prevent Privilege Escalation.
    Requires hipaa_consent = true and a YYYY-MM-DD date_of_birth.
    """
    try:
        clean = validate_registration(request.get_json(silent=True))
    except ValidationError as exc:
        return jsonify({"status": "error", "code": "VALIDATION_FAILED", "error": str(exc),
                        "fields": exc.fields}), 400

    assigned_role = "PATIENT"  # never taken from the request

    if User.query.filter_by(username=clean["username"]).first():
        return jsonify({"error": "Username is already taken"}), 409
    if Patient.query.filter_by(email=clean["email"]).first():
        return jsonify({"error": "Email is already registered to a patient profile"}), 409

    try:
        new_user = User(username=clean["username"], role=assigned_role)
        new_user.set_password(clean["password"])
        db.session.add(new_user)
        db.session.flush()  # assigns new_user.user_id

        new_patient = Patient(
            user_id=new_user.user_id,
            first_name=clean["first_name"],
            middle_name=clean.get("middle_name"),
            last_name=clean["last_name"],
            date_of_birth=clean["date_of_birth"],
            gender=clean["gender"],
            religion=clean.get("religion"),
            address=clean["address"],
            contact_number=clean["contact_number"],
            email=clean["email"],
            emergency_contact_name=clean["emergency_contact_name"],
            emergency_contact_number=clean["emergency_contact_number"],
            emergency_relation=clean["emergency_relation"],
            hipaa_consent=True,  # validated above; hipaa_consent_at defaults to now
        )
        db.session.add(new_patient)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database integrity constraint violated"}), 409
    except Exception:
        db.session.rollback()
        log.exception("Patient registration failed")
        return jsonify({"error": "An internal error occurred during registration"}), 500

    profile_dict = {column.name: getattr(new_patient, column.name) for column in new_patient.__table__.columns}
    return jsonify({
        "message": "Patient profile successfully created",
        "profile": sanitize_response(profile_dict, role=assigned_role)
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Unified Authentication endpoint for Patients, Doctors, and Admins.
    Unknown user, wrong password and locked account all get the same 401, so the
    response never confirms that an account exists.
    """
    data = request.get_json(silent=True) or {}
    identifier = data.get("username")  # Can be username or email
    password = data.get("password")

    if not isinstance(identifier, str) or not isinstance(password, str) or not identifier or not password:
        return jsonify({"error": "Username/Email and password are required"}), 400

    # Locate user by username OR associated profile email
    user = User.query.outerjoin(Patient).outerjoin(Doctor).outerjoin(Admin).filter(
        (User.username == identifier) |
        (Patient.email == identifier) |
        (Doctor.email == identifier) |
        (Admin.email == identifier)
    ).first()

    if not user:
        bcrypt.checkpw(password.encode("utf-8"), _DUMMY_HASH)
        return _invalid_credentials()

    if user.is_locked:
        # Not even the password is checked, so a locked account gives no password oracle.
        return _invalid_credentials()

    if not user.check_password(password):
        user.record_failed_attempt()
        db.session.commit()
        return _invalid_credentials()

    # Password is correct from here on, so these messages reveal nothing to a guesser.
    if user.role in DOCTOR_ROLES and (user.doctor is None or not user.doctor.is_verified):
        return jsonify({"status": "error", "code": "ACCOUNT_PENDING_VERIFICATION",
                        "error": "This doctor account is awaiting administrator verification."}), 403
    if user.role == "PATIENT" and user.patient is not None and user.patient.is_active is False:
        return jsonify({"status": "error", "code": "ACCOUNT_INACTIVE",
                        "error": "This patient account is inactive. Contact the clinic."}), 403

    # On success: clear lockout
    user.reset_lockout()
    db.session.commit()

    # Generate JWT
    exp_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    payload = {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "token_version": user.token_version,
        "exp": exp_time
    }
    if user.role == "PATIENT" and user.patient:
        payload["patient_id"] = user.patient.patient_id
    elif user.role in ["DOCTOR", "CLINICIAN"] and user.doctor:
        payload["doctor_id"] = user.doctor.doctor_id
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

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User record not found"}), 404

    # Incrementing token_version ensures any previously issued JWT is now considered invalid
    # (Requires updating the @role_required middleware to check token_version against the DB if strict state is desired)
    user.token_version = (user.token_version or 0) + 1
    db.session.commit()

    return jsonify({"message": "Successfully logged out across all active sessions"}), 200

@auth_bp.route('/change-password', methods=['POST'])
@role_required(["PATIENT", "DOCTOR", "CLINICIAN", "ADMIN", "SYSTEM_ADMIN", "IT_SUPPORT", "COMPLIANCE_AUDITOR"])
def change_password():
    """
    Enables authenticated users to update their credentials securely.
    """
    claims = request.current_user
    user_id = claims.get("user_id")

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request payload cannot be empty"}), 400

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not current_password or not new_password:
        return jsonify({"error": "Both current_password and new_password are required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters long"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User record not found"}), 404

    if not user.check_password(current_password):
        return jsonify({"error": "Incorrect current password"}), 401

    user.set_password(new_password)
    user.token_version = (user.token_version or 0) + 1
    db.session.commit()

    return jsonify({"status": "success", "message": "Password successfully updated"}), 200
