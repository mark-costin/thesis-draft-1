import logging

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from backend.dbconnect import db
from backend.model_orm.usr_orm import User
from backend.model_orm.doc_orm import Doctor

# Import Security Middleware
from backend.middleware.rbac import role_required
from backend.middleware.idempotency import enforce_idempotency
from backend.middleware.sanitizer import sanitize_response
from backend.validation import ValidationError, validate_provision

log = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')

ADMIN_ROLES = ['ADMIN', 'SYSTEM_ADMIN']


def _error(status_code, code, message, **extra):
    return jsonify({"status": "error", "code": code, "error": message, **extra}), status_code


@admin_bp.route('/directory', methods=['GET'])
@role_required(ADMIN_ROLES)
def list_system_directory():
    """Lists all accounts."""
    users = User.query.all()
    user_list = [user.to_dict() for user in users]
    return jsonify(sanitize_response(user_list, role=request.current_user.get("role"))), 200


@admin_bp.route('/provision', methods=['POST'])
@role_required(ADMIN_ROLES)
@enforce_idempotency
def provision_clinician_account():
    """
    Creates a DOCTOR account and its doctor profile. The new doctor starts unverified
    and cannot log in until an admin calls POST /doctors/<doctor_id>/verify.
    """
    try:
        clean = validate_provision(request.get_json(silent=True))
    except ValidationError as exc:
        return _error(400, "VALIDATION_FAILED", str(exc), fields=exc.fields)

    if User.query.filter_by(username=clean["username"]).first():
        return _error(409, "USERNAME_TAKEN", "Username is already taken.")
    if Doctor.query.filter_by(license_number=clean["license_number"]).first():
        return _error(409, "LICENSE_EXISTS", "A doctor with this license number already exists.")
    if Doctor.query.filter_by(email=clean["email"]).first():
        return _error(409, "EMAIL_EXISTS", "A doctor with this email already exists.")

    try:
        user = User(username=clean["username"], role="DOCTOR")
        user.set_password(clean["password"])
        db.session.add(user)
        db.session.flush()

        profile = {k: v for k, v in clean.items() if k not in ("username", "password")}
        doctor = Doctor(user_id=user.user_id, is_verified=False, **profile)
        db.session.add(doctor)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error(409, "DUPLICATE_ACCOUNT", "An account with these details already exists.")
    except Exception:
        db.session.rollback()
        log.exception("Clinician provisioning failed")
        return _error(500, "PROVISION_FAILED", "The account could not be created. Please retry.")

    response_payload = {
        "message": "Clinical account provisioned successfully",
        "account_id": user.username,
        "user_id": user.user_id,
        "doctor_id": doctor.doctor_id,
        "status": "Awaiting initial verification",
    }
    return jsonify(sanitize_response(response_payload, role=request.current_user.get("role"))), 201


@admin_bp.route('/doctors/<int:doctor_id>/verify', methods=['POST'])
@role_required(ADMIN_ROLES)
def verify_doctor(doctor_id):
    """Marks a doctor as verified so they can log in."""
    doctor = db.session.get(Doctor, doctor_id)
    if doctor is None:
        return _error(404, "DOCTOR_NOT_FOUND", f"Doctor {doctor_id} not found.")
    doctor.is_verified = True
    db.session.commit()
    return jsonify({"status": "success", "doctor_id": doctor_id, "is_verified": True}), 200


@admin_bp.route('/users/<int:user_id>/unlock', methods=['POST'])
@role_required(ADMIN_ROLES)
def unlock_user(user_id):
    """Clears a lockout after too many failed logins."""
    user = db.session.get(User, user_id)
    if user is None:
        return _error(404, "USER_NOT_FOUND", f"User {user_id} not found.")
    user.reset_lockout()
    db.session.commit()
    return jsonify({"status": "success", "user_id": user_id, "is_locked": False}), 200
