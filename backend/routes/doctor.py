import logging
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from backend.dbconnect import db
from backend.model_orm.pat_orm import Patient
from backend.model_orm.doc_orm import Doctor
from backend.model_orm.clinic_orm import Consultation, Encounter
from backend.triage_queue import TriageQueue
from backend.validation import ValidationError, validate_consultation
from backend.ledger import SEAL_ALGORITHM, canonical_timestamp, seal, verify_encounter
from backend.audit import log_event

# Import Security Middleware
from backend.middleware.rbac import role_required
from backend.middleware.idempotency import enforce_idempotency
from backend.middleware.sanitizer import sanitize_response

log = logging.getLogger(__name__)

doctor_bp = Blueprint('doctor', __name__, url_prefix='/api/v1/doctor')

# Encounter record types. An anchor starts or restarts a patient's chain.
RECORD_TYPES = {"BASELINE", "FOLLOWUP", "REANCHOR_BASELINE"}
ANCHOR_TYPES = ("BASELINE", "REANCHOR_BASELINE")

# The clinic queue (stored in queue_tickets, so every worker sees the same queue).
QUEUE = TriageQueue()


def _error(status_code, code, message, retryable=False, **extra):
    body = {"status": "error", "code": code, "error": message, "retryable": retryable, **extra}
    return jsonify(body), status_code


def _latest_anchor(patient_id):
    """The patient's most recent BASELINE or REANCHOR_BASELINE encounter, or None."""
    return (Encounter.query
            .filter(Encounter.patient_id == patient_id, Encounter.record_type.in_(ANCHOR_TYPES))
            .order_by(Encounter.created_at_utc.desc(), Encounter.id.desc())
            .first())


@doctor_bp.route('/queue', methods=['GET'])
@role_required(['DOCTOR', 'ADMIN'])
def get_triage_queue():
    """Today's waiting patients, in check-in order (the same tickets patients create)."""
    user_role = request.current_user.get("role")
    return jsonify({"status": "success", "queue": sanitize_response(QUEUE.list_for(user_role), role=user_role)}), 200


@doctor_bp.route('/patient/<int:patient_id>', methods=['GET'])
@role_required(['DOCTOR', 'ADMIN'])
def get_patient_record(patient_id):
    """Fetches a complete patient clinical record."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Patient record not found"}), 404
        
    patient_data = {column.name: getattr(patient, column.name) for column in patient.__table__.columns}
    user_role = request.current_user.get("role")
    return jsonify(sanitize_response(patient_data, role=user_role)), 200


@doctor_bp.route('/patient/<int:patient_id>/baseline', methods=['GET'])
@role_required(['DOCTOR', 'ADMIN'])
def get_patient_baseline(patient_id):
    """Queries encounters for the latest valid baseline record."""
    baseline_encounter = Encounter.query.filter(
        Encounter.patient_id == patient_id,
        Encounter.record_type.in_(['BASELINE', 'REANCHOR_BASELINE'])
    ).order_by(Encounter.created_at_utc.desc()).first()
    
    if not baseline_encounter:
        return jsonify({
            "status": "success",
            "has_baseline": False,
            "message": "No established clinical baseline found. Initiate Phase 1 Intake."
        }), 404
        
    payload = baseline_encounter.cdss_payload or {}

    biomarkers = payload.get("biomarker_payload")
    if biomarkers is None:
        known_meta = {
            "risk_assessment", "fhrs_decomposition", "fhrs_data", 
            "fairness_audit", "shap_explanations", "modality", 
            "model_version", "patient_id", "status"
        }
        biomarkers = {k: v for k, v in payload.items() if k not in known_meta}

    fhrs_data = payload.get("fhrs_data") or payload.get("fhrs_decomposition") or {}

    risk_data = payload.get("risk") or payload.get("risk_assessment", {})
    if isinstance(risk_data, dict) and "domains" in risk_data:
        baseline_risk = risk_data.get("domains", {})
    elif isinstance(risk_data, dict):
        baseline_risk = risk_data
    else:
        baseline_risk = {}

    ts = baseline_encounter.created_at_utc
    if ts:
        if ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc)
        established_at_utc = ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    else:
        established_at_utc = None

    return jsonify({
        "status": "success",
        "has_baseline": True,
        "encounter_id": baseline_encounter.encounter_uid,
        "record_type": baseline_encounter.record_type,
        "baseline_hash": baseline_encounter.cryptographic_hash,
        "established_at_utc": established_at_utc,
        "fhrs_data": fhrs_data,
        "baseline_biomarkers": biomarkers,
        "baseline_risk": baseline_risk
    }), 200


@doctor_bp.route('/consultation', methods=['POST'])
@role_required(['DOCTOR'])
@enforce_idempotency
def submit_consultation():
    """
    Saves a consultation (directives and notes) for a patient, by the logged-in doctor.
    Closes the patient's waiting queue ticket and writes a sealed audit entry, all in one
    transaction. Body: {"patient_id": 5, "directives": {...} | [...] | "text", "notes": "..."}
    """
    data = request.get_json(silent=True) or {}
    try:
        consultation = validate_consultation(data)
    except ValidationError as exc:
        return _error(400, "VALIDATION_FAILED", str(exc), fields=exc.fields)

    doctor = Doctor.query.filter_by(user_id=request.current_user.get("user_id")).first()
    if doctor is None:
        return _error(403, "DOCTOR_PROFILE_MISSING", "This account has no doctor profile.")
    patient_id = consultation["patient_id"]
    if db.session.get(Patient, patient_id) is None:
        return _error(404, "PATIENT_NOT_FOUND", f"Target patient ID {patient_id} not found in database.")

    row = Consultation(consultation_uid=f"CONS-{uuid.uuid4().hex[:12].upper()}", patient_id=patient_id,
                       doctor_id=doctor.doctor_id, directives=consultation["directives"],
                       notes=consultation["notes"], created_at=datetime.now(timezone.utc))
    db.session.add(row)
    ticket_closed = QUEUE.close_for_patient(patient_id)
    try:
        log_event("CONSULTATION_SAVED",
                  {"consultation_uid": row.consultation_uid, "directives": row.directives, "notes": row.notes,
                   "queue_ticket_closed": ticket_closed},
                  patient_id=patient_id, doctor_id=doctor.doctor_id,
                  actor_user_id=request.current_user.get("user_id"), commit=False)
        db.session.commit()
    except Exception:
        db.session.rollback()
        log.exception("Saving consultation failed for patient %s", patient_id)
        return _error(500, "CONSULTATION_SAVE_FAILED", "The consultation could not be saved. Please retry.",
                      retryable=True)

    return jsonify({
        "status": "success",
        "message": "Consultation saved.",
        "consultation_uid": row.consultation_uid,
        "patient_id": patient_id,
        "doctor_id": doctor.doctor_id,
        "queue_ticket_closed": ticket_closed,
    }), 201


@doctor_bp.route('/patient/<int:patient_id>/consultations', methods=['GET'])
@role_required(['DOCTOR', 'ADMIN'])
def list_consultations(patient_id):
    """A patient's saved consultations, newest first."""
    if db.session.get(Patient, patient_id) is None:
        return _error(404, "PATIENT_NOT_FOUND", f"Target patient ID {patient_id} not found in database.")
    rows = (Consultation.query.filter_by(patient_id=patient_id)
            .order_by(Consultation.created_at.desc(), Consultation.id.desc()).all())
    return jsonify({"status": "success", "patient_id": patient_id, "consultations": [
        {"consultation_uid": r.consultation_uid, "doctor_id": r.doctor_id, "directives": r.directives,
         "notes": r.notes, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows]}), 200


@doctor_bp.route('/commit-encounter', methods=['POST'])
@role_required(['DOCTOR'])
@enforce_idempotency
def commit_encounter_atomic():
    """
    D5: Seals physician directives, prescriptions, CDSS predictions and cryptographic
    proof into one database transaction. Retries are handled by @enforce_idempotency
    (Idempotency-Key header, 24-hour replay window, scoped per doctor).

    The server decides everything that goes into the seal except the clinical content:
      - doctor_id      from the logged-in doctor's profile (never from the request)
      - parent hash    the patient's latest anchor (a client value must match it)
      - timestamp      server time, sealed in canonical UTC form
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return _error(400, "INVALID_PAYLOAD", "Encounter commitment payload is empty.")

    doctor = Doctor.query.filter_by(user_id=request.current_user.get("user_id")).first()
    if doctor is None:
        return _error(403, "DOCTOR_PROFILE_MISSING", "This account has no doctor profile.")

    try:
        patient_id = int(data["patient_id"])
    except (KeyError, TypeError, ValueError):
        return _error(400, "VALIDATION_FAILED", "patient_id is required and must be an integer.")
    if db.session.get(Patient, patient_id) is None:
        return _error(404, "PATIENT_NOT_FOUND", f"Target patient ID {patient_id} not found in database.")

    record_type = str(data.get("encounter_type", "FOLLOWUP")).upper()
    if record_type not in RECORD_TYPES:
        return _error(400, "INVALID_RECORD_TYPE", f"encounter_type must be one of {sorted(RECORD_TYPES)}.")

    snapshot = data.get("cdss_payload_snapshot", {})
    care_plan = data.get("care_plan", {})
    if not isinstance(snapshot, dict) or not isinstance(care_plan, dict):
        return _error(400, "VALIDATION_FAILED", "cdss_payload_snapshot and care_plan must be JSON objects.")

    cdss_payload = dict(snapshot)
    client_parent = cdss_payload.pop("parent_baseline_hash", None) or data.get("parent_baseline_hash")
    if "fhrs_data" in data and "fhrs_data" not in cdss_payload:
        cdss_payload["fhrs_data"] = data["fhrs_data"]
    if "biomarker_payload" in data and "biomarker_payload" not in cdss_payload:
        cdss_payload["biomarker_payload"] = data["biomarker_payload"]

    # Server-authoritative lineage: the parent is always the patient's latest anchor.
    anchor = _latest_anchor(patient_id)
    if record_type == "BASELINE" and anchor is not None:
        return _error(409, "BASELINE_EXISTS",
                      "This patient already has a baseline. Use REANCHOR_BASELINE to establish a new one.")
    if record_type != "BASELINE" and anchor is None:
        return _error(409, "NO_BASELINE", "No established clinical baseline found. Initiate Phase 1 Intake.")
    parent_baseline_hash = anchor.cryptographic_hash if anchor else None
    if client_parent and client_parent != parent_baseline_hash:
        return _error(409, "STALE_PARENT_HASH",
                      "parent_baseline_hash does not match the patient's current baseline. Reload and retry.",
                      current_parent_baseline_hash=parent_baseline_hash)

    created_at = datetime.now(timezone.utc)
    encounter_uid = f"ENC-{uuid.uuid4().hex[:12].upper()}"
    sealed_fields = {
        "encounter_uid": encounter_uid,
        "patient_id": patient_id,
        "doctor_id": doctor.doctor_id,
        "record_type": record_type,
        "parent_baseline_hash": parent_baseline_hash,
        "created_at": created_at,
        "cdss_payload": cdss_payload,
        "care_plan": care_plan,
        "reanchor_decision": data.get("reanchor_decision"),
    }
    crypto_hash = seal(**sealed_fields)

    try:
        db.session.add(Encounter(
            encounter_uid=encounter_uid,
            patient_id=patient_id,
            doctor_id=doctor.doctor_id,
            record_type=record_type,
            parent_baseline_hash=parent_baseline_hash,
            cryptographic_hash=crypto_hash,
            cdss_payload=cdss_payload,
            care_plan=care_plan,
            reanchor_decision=sealed_fields["reanchor_decision"],
            created_at_utc=created_at,
        ))
        # Same transaction: the encounter and its audit entry are saved together or not at all.
        log_event(
            "ENCOUNTER_COMMITTED",
            {"encounter_id": encounter_uid, "record_type": record_type,
             "cryptographic_hash": crypto_hash, "parent_baseline_hash": parent_baseline_hash},
            patient_id=patient_id,
            doctor_id=doctor.doctor_id,
            actor_user_id=request.current_user.get("user_id"),
            commit=False,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        log.exception("commit-encounter failed for patient %s", patient_id)
        return _error(500, "DATABASE_COMMIT_FAILED", "The encounter could not be saved. Please retry.", retryable=True)

    response_payload = {
        "status": "success",
        "encounter_id": encounter_uid,
        "record_type": record_type,
        "envelope_status": "SEALED",
        "parent_baseline_hash": parent_baseline_hash,
        "cryptographic_hash": crypto_hash,
        "committed_at_utc": canonical_timestamp(created_at),
        "audit_trail": {
            "attending_physician_id": doctor.doctor_id,
            "signing_algorithm": SEAL_ALGORITHM,
            "atomic_transaction_id": f"tx_{uuid.uuid4().hex[:8]}",
            "verification_status": "COMMITTED_EHR",
        },
    }
    user_role = request.current_user.get("role")
    return jsonify(sanitize_response(response_payload, role=user_role)), 201


@doctor_bp.route('/encounter/<encounter_uid>/verify', methods=['GET'])
@role_required(['DOCTOR', 'ADMIN'])
def verify_encounter_seal(encounter_uid):
    """Recomputes an encounter's seal from the stored row. seal_valid=False means it was altered."""
    encounter = Encounter.query.filter_by(encounter_uid=encounter_uid).first()
    if encounter is None:
        return _error(404, "ENCOUNTER_NOT_FOUND", f"Encounter {encounter_uid} not found.")

    parent_found = None
    if encounter.parent_baseline_hash:
        parent_found = Encounter.query.filter_by(
            patient_id=encounter.patient_id, cryptographic_hash=encounter.parent_baseline_hash
        ).first() is not None

    return jsonify({
        "status": "success",
        "encounter_id": encounter.encounter_uid,
        "seal_valid": verify_encounter(encounter),
        "parent_found": parent_found,
        "signing_algorithm": SEAL_ALGORITHM,
    }), 200
