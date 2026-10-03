import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from backend.dbconnect import db
from backend.model_orm.pat_orm import Patient
from backend.model_orm.doc_orm import Doctor
from backend.model_orm.clinic_orm import Encounter, FamilyHistory, FHRSStratification
from backend.middleware.rbac import role_required
from backend.middleware.sanitizer import sanitize_response

patient_bp = Blueprint('patient', __name__, url_prefix='/api/v1/patient')

# In-memory shared triage queue store synchronized with backend runtime
_ACTIVE_TRIAGE_QUEUE = []


def _resolve_patient_id(claims, requested_id=None):
    """
    Resolves patient_id from JWT claims or fallback requested_id.
    """
    if claims.get("patient_id"):
        return int(claims["patient_id"])

    user_role = claims.get("role")
    user_id = claims.get("user_id")

    if user_role == "PATIENT":
        pat = Patient.query.filter_by(user_id=user_id).first()
        if pat:
            return pat.patient_id
        if requested_id:
            return int(requested_id)
        return None

    if requested_id:
        return int(requested_id)

    return None


# --------------------------------------------------------------------------
# 1. ENCOUNTER & CARE PLAN LEDGER
# --------------------------------------------------------------------------
@patient_bp.route('/latest-encounter', methods=['GET'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def get_latest_encounter():
    """Fetches the most recent committed clinical encounter and care plan."""
    claims = request.current_user
    req_pid = request.args.get("patient_id")
    target_pid = _resolve_patient_id(claims, req_pid)

    if not target_pid:
        return jsonify({"status": "error", "error": "Patient identity could not be resolved."}), 404

    encounter = Encounter.query.filter_by(patient_id=target_pid)\
        .order_by(Encounter.created_at_utc.desc()).first()

    if not encounter:
        return jsonify({
            "status": "success",
            "has_encounter": False,
            "message": "No committed clinical encounters found for this patient."
        }), 200

    doctor = Doctor.query.get(encounter.doctor_id)
    doctor_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Lucerna Medica Clinician"

    payload = {
        "encounter_uid": encounter.encounter_uid,
        "record_type": encounter.record_type,
        "cryptographic_hash": encounter.cryptographic_hash,
        "parent_baseline_hash": encounter.parent_baseline_hash,
        "created_at": encounter.created_at_utc.isoformat() if encounter.created_at_utc else None,
        "doctor_name": doctor_name,
        "care_plan": encounter.care_plan or {},
        "cdss_payload": encounter.cdss_payload or {}
    }

    return jsonify({
        "status": "success",
        "has_encounter": True,
        "encounter": sanitize_response(payload, role=claims.get("role"))
    }), 200


@patient_bp.route('/encounters', methods=['GET'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def list_encounters():
    """Lists all historical cryptographic encounters for patient timeline view."""
    claims = request.current_user
    req_pid = request.args.get("patient_id")
    target_pid = _resolve_patient_id(claims, req_pid)

    if not target_pid:
        return jsonify({"status": "error", "error": "Patient identity could not be resolved."}), 404

    encounters = Encounter.query.filter_by(patient_id=target_pid)\
        .order_by(Encounter.created_at_utc.desc()).all()

    encounter_list = []
    for enc in encounters:
        doctor = Doctor.query.get(enc.doctor_id)
        doctor_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Attending Clinician"
        encounter_list.append({
            "encounter_uid": enc.encounter_uid,
            "record_type": enc.record_type,
            "created_at": enc.created_at_utc.isoformat() if enc.created_at_utc else None,
            "doctor_name": doctor_name,
            "cryptographic_hash": enc.cryptographic_hash,
            "summary_directive": (enc.care_plan or {}).get("clinical_order") or (enc.care_plan or {}).get("directive", "Standard follow-up")
        })

    return jsonify({
        "status": "success",
        "count": len(encounter_list),
        "encounters": sanitize_response(encounter_list, role=claims.get("role"))
    }), 200


# --------------------------------------------------------------------------
# 2. FAMILY HISTORY (FHRS FRAMEWORK)
# --------------------------------------------------------------------------
@patient_bp.route('/family-history', methods=['GET'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def get_family_history():
    """Retrieves all logged familial hereditary variables for the patient."""
    claims = request.current_user
    req_pid = request.args.get("patient_id")
    target_pid = _resolve_patient_id(claims, req_pid)

    if not target_pid:
        return jsonify({"status": "error", "error": "Patient not identified"}), 404

    records = FamilyHistory.query.filter_by(patient_id=target_pid)\
        .order_by(FamilyHistory.recorded_at.desc()).all()

    history_data = []
    for r in records:
        history_data.append({
            "record_id": r.record_id,
            "disease_domain": r.disease_domain,
            "specific_diagnosis": r.specific_diagnosis,
            "relationship_tier": r.relationship_tier,
            "relationship_weight": float(r.relationship_weight) if r.relationship_weight else 0.0,
            "onset_classification": r.onset_classification,
            "onset_weight": float(r.onset_weight) if r.onset_weight else 1.0,
            "shared_environment": r.shared_environment,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None
        })

    return jsonify({"status": "success", "family_history": history_data}), 200


@patient_bp.route('/family-history', methods=['POST'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def add_family_history():
    """Records a new familial hereditary risk entry into the database."""
    claims = request.current_user
    data = request.get_json() or {}

    target_pid = _resolve_patient_id(claims, data.get("patient_id"))
    if not target_pid:
        return jsonify({"status": "error", "error": "Valid patient ID is required"}), 400

    disease_domain = data.get("disease_domain")
    specific_diag = data.get("specific_diagnosis", disease_domain)
    rel_tier = data.get("relationship_tier", "Tier 1")
    rel_weight = data.get("relationship_weight", 0.5)
    onset_class = data.get("onset_classification", "Typical onset")
    onset_weight = data.get("onset_weight", 1.0)
    shared_env = bool(data.get("shared_environment", False))

    if not disease_domain:
        return jsonify({"status": "error", "error": "disease_domain is required"}), 400

    new_record = FamilyHistory(
        patient_id=target_pid,
        disease_domain=disease_domain,
        specific_diagnosis=specific_diag,
        relationship_tier=rel_tier,
        relationship_weight=rel_weight,
        onset_classification=onset_class,
        onset_weight=onset_weight,
        shared_environment=shared_env
    )

    db.session.add(new_record)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Family history record successfully stored in repository.",
        "record_id": new_record.record_id
    }), 201


# --------------------------------------------------------------------------
# 3. CLINIC TRIAGE QUEUE & CHECK-IN
# --------------------------------------------------------------------------
@patient_bp.route('/queue', methods=['GET'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def get_queue():
    """Returns the shared triage queue."""
    return jsonify({"status": "success", "queue": _ACTIVE_TRIAGE_QUEUE}), 200


@patient_bp.route('/queue/checkin', methods=['POST'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def submit_checkin():
    """Registers patient in the clinic triage queue and issues a ticket."""
    claims = request.current_user
    data = request.get_json() or {}

    target_pid = _resolve_patient_id(claims, data.get("patient_id"))
    if not target_pid:
        return jsonify({"status": "error", "error": "Patient identification required"}), 400

    # Avoid duplicate check-in tickets
    for item in _ACTIVE_TRIAGE_QUEUE:
        if item.get("patient_id") == target_pid:
            return jsonify({
                "status": "success",
                "message": "Patient is already checked into queue.",
                "ticket": item
            }), 200

    ticket_number = f"Q-{len(_ACTIVE_TRIAGE_QUEUE) + 1:02d}"
    now_str = datetime.now().strftime("%I:%M %p")

    ticket = {
        "queue_no": ticket_number,
        "patient_id": target_pid,
        "name": data.get("name", f"Patient #{target_pid}"),
        "time_in": now_str,
        "urgency": data.get("urgency", "🟢 Routine"),
        "complaint": data.get("complaint", "Routine follow-up"),
        "vitals": data.get("vitals", "Not recorded"),
        "watch_flag": data.get("watch_flag", "None declared"),
        "lifecycle_status": "In Waiting Room"
    }

    _ACTIVE_TRIAGE_QUEUE.append(ticket)

    return jsonify({
        "status": "success",
        "message": "Checked in successfully.",
        "ticket": ticket
    }), 201


@patient_bp.route('/queue/<int:patient_id>', methods=['DELETE'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def cancel_checkin(patient_id):
    """Cancels a check-in ticket or removes patient from active queue."""
    global _ACTIVE_TRIAGE_QUEUE
    before_len = len(_ACTIVE_TRIAGE_QUEUE)
    _ACTIVE_TRIAGE_QUEUE = [q for q in _ACTIVE_TRIAGE_QUEUE if q.get("patient_id") != patient_id]

    if len(_ACTIVE_TRIAGE_QUEUE) < before_len:
        return jsonify({"status": "success", "message": "Ticket cancelled."}), 200
    return jsonify({"status": "error", "message": "Ticket not found."}), 404
