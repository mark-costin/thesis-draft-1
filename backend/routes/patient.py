from flask import Blueprint, request, jsonify
from backend.dbconnect import db
from backend.model_orm.pat_orm import Patient
from backend.model_orm.doc_orm import Doctor
from backend.model_orm.clinic_orm import Encounter, EnvironmentalHazard, FamilyHistory
from backend.middleware.rbac import role_required
from backend.middleware.sanitizer import sanitize_response
from backend.triage_queue import TriageQueue
from backend.validation import (
    ValidationError, parse_biological_sex, parse_disease, parse_onset, parse_patient_id, parse_tier,
    validate_family_history, validate_hazard,
)

patient_bp = Blueprint('patient', __name__, url_prefix='/api/v1/patient')

# Shared triage queue for this server process (see backend/triage_queue.py)
QUEUE = TriageQueue()


def _resolve_patient_id(claims, requested_id=None):
    """
    The patient a request is about.
      - PATIENT: always their own profile, looked up from the database. A requested id
        is ignored, so a patient can never reach another patient's records.
      - Staff:   the requested id (validated); None if not given.
    Raises ValidationError for a malformed requested id.
    """
    if claims.get("role") == "PATIENT":
        pat = Patient.query.filter_by(user_id=claims.get("user_id")).first()
        return pat.patient_id if pat else None

    if requested_id in (None, ""):
        return None
    return parse_patient_id(requested_id)


def _target_patient(claims, requested_id):
    """(patient_id, None) or (None, error response)."""
    try:
        return _resolve_patient_id(claims, requested_id), None
    except ValidationError as exc:
        return None, (jsonify({"status": "error", "code": "VALIDATION_FAILED", "error": str(exc)}), 400)


# --------------------------------------------------------------------------
# 1. ENCOUNTER & CARE PLAN LEDGER
# --------------------------------------------------------------------------
@patient_bp.route('/latest-encounter', methods=['GET'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def get_latest_encounter():
    """Fetches the most recent committed clinical encounter and care plan."""
    claims = request.current_user
    target_pid, err = _target_patient(claims, request.args.get("patient_id"))
    if err:
        return err

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

    doctor = db.session.get(Doctor, encounter.doctor_id)
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
    target_pid, err = _target_patient(claims, request.args.get("patient_id"))
    if err:
        return err

    if not target_pid:
        return jsonify({"status": "error", "error": "Patient identity could not be resolved."}), 404

    encounters = Encounter.query.filter_by(patient_id=target_pid)\
        .order_by(Encounter.created_at_utc.desc()).all()

    encounter_list = []
    for enc in encounters:
        doctor = enc.doctor
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
    target_pid, err = _target_patient(claims, request.args.get("patient_id"))
    if err:
        return err

    if not target_pid:
        return jsonify({"status": "error", "error": "Patient not identified"}), 404

    records = FamilyHistory.query.filter_by(patient_id=target_pid)\
        .order_by(FamilyHistory.recorded_at.desc()).all()

    history_data = []
    for r in records:
        history_data.append({
            "record_id": r.record_id,
            "disease_domain": parse_disease(r.disease_domain) or r.disease_domain,
            "specific_diagnosis": r.specific_diagnosis,
            "relationship_tier": parse_tier(r.relationship_tier) or r.relationship_tier,
            "relationship_weight": float(r.relationship_weight) if r.relationship_weight is not None else None,
            "onset_classification": parse_onset(r.onset_classification) or r.onset_classification,
            "onset_weight": float(r.onset_weight) if r.onset_weight is not None else None,
            "age_at_diagnosis": r.age_at_diagnosis,
            "shared_environment": r.shared_environment,
            "is_verified": bool(r.is_verified),
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None
        })

    return jsonify({"status": "success", "family_history": history_data}), 200


def _validation_error(exc):
    return jsonify({"status": "error", "code": "VALIDATION_FAILED", "error": str(exc), "fields": exc.fields}), 400


@patient_bp.route('/family-history', methods=['POST'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def add_family_history():
    """
    Records one affected relative. Tier (1-3) and onset (severe_early, early, typical, late)
    are required; their weights come from cdss_spec.json (CDSS FHRS Guide), never the request.
    Only a doctor or admin can mark the diagnosis verified.
    """
    claims = request.current_user
    data = request.get_json(silent=True) or {}

    target_pid, err = _target_patient(claims, data.get("patient_id"))
    if err:
        return err
    if not target_pid:
        return jsonify({"status": "error", "error": "Valid patient ID is required"}), 400
    if db.session.get(Patient, target_pid) is None:
        return jsonify({"status": "error", "code": "PATIENT_NOT_FOUND", "error": "Patient not found."}), 404

    try:
        entry = validate_family_history(claims.get("role"), data)
    except ValidationError as exc:
        return _validation_error(exc)

    new_record = FamilyHistory(patient_id=target_pid, **entry)
    db.session.add(new_record)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Family history record successfully stored in repository.",
        "record_id": new_record.record_id,
        "is_verified": new_record.is_verified,
    }), 201


@patient_bp.route('/family-history/<int:record_id>/verify', methods=['POST'])
@role_required(['DOCTOR', 'ADMIN'])
def verify_family_history(record_id):
    """A doctor confirms a relative's diagnosis (records or lab results seen): S_i becomes 1.0."""
    record = db.session.get(FamilyHistory, record_id)
    if record is None:
        return jsonify({"status": "error", "code": "NOT_FOUND", "error": "Family history record not found."}), 404
    record.is_verified = True
    db.session.commit()
    return jsonify({"status": "success", "record_id": record_id, "is_verified": True}), 200


# --------------------------------------------------------------------------
# 2b. ENVIRONMENTAL HAZARDS, BIOLOGICAL SEX AND THE FHRS VIEW
# --------------------------------------------------------------------------
def _hazard_catalogue():
    from backend.cdss.fhrs import HAZARDS
    return {d: [{k: h[k] for k in ("code", "label", "e_j", "evidence", "source", "status")} for h in hazards.values()]
            for d, hazards in HAZARDS.items()}


@patient_bp.route('/hazards', methods=['GET'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def get_hazards():
    """The patient's recorded hazards, plus the fixed list per disease to choose from."""
    from backend.cdss.fhrs import HAZARDS
    claims = request.current_user
    target_pid, err = _target_patient(claims, request.args.get("patient_id"))
    if err:
        return err
    if not target_pid:
        return jsonify({"status": "error", "error": "Patient not identified"}), 404

    rows = EnvironmentalHazard.query.filter_by(patient_id=target_pid).order_by(EnvironmentalHazard.id).all()
    hazards = []
    for h in rows:
        info = HAZARDS.get(h.disease_domain, {}).get(h.hazard_code, {})
        hazards.append({"id": h.id, "disease_domain": h.disease_domain, "hazard_code": h.hazard_code,
                        "label": info.get("label"), "e_j": info.get("e_j"),
                        "recorded_at": h.recorded_at.isoformat() if h.recorded_at else None})
    return jsonify({"status": "success", "patient_id": target_pid, "hazards": hazards,
                    "catalogue": _hazard_catalogue()}), 200


@patient_bp.route('/hazards', methods=['POST'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def add_hazard():
    """Records a shared domestic hazard from the fixed list (FHRS questionnaire)."""
    claims = request.current_user
    data = request.get_json(silent=True) or {}
    target_pid, err = _target_patient(claims, data.get("patient_id"))
    if err:
        return err
    if not target_pid:
        return jsonify({"status": "error", "error": "Valid patient ID is required"}), 400
    if db.session.get(Patient, target_pid) is None:
        return jsonify({"status": "error", "code": "PATIENT_NOT_FOUND", "error": "Patient not found."}), 404
    try:
        disease, code = validate_hazard(data)
    except ValidationError as exc:
        return _validation_error(exc)

    if EnvironmentalHazard.query.filter_by(patient_id=target_pid, disease_domain=disease, hazard_code=code).first():
        return jsonify({"status": "error", "code": "ALREADY_RECORDED",
                        "error": "This hazard is already recorded for this patient and disease."}), 409
    row = EnvironmentalHazard(patient_id=target_pid, disease_domain=disease, hazard_code=code)
    db.session.add(row)
    db.session.commit()
    return jsonify({"status": "success", "id": row.id, "disease_domain": disease, "hazard_code": code}), 201


@patient_bp.route('/hazards/<int:hazard_id>', methods=['DELETE'])
@role_required(['DOCTOR', 'ADMIN'])
def remove_hazard(hazard_id):
    row = db.session.get(EnvironmentalHazard, hazard_id)
    if row is None:
        return jsonify({"status": "error", "code": "NOT_FOUND", "error": "Hazard not found."}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"status": "success", "id": hazard_id}), 200


@patient_bp.route('/biological-sex', methods=['POST'])
@role_required(['DOCTOR', 'ADMIN'])
def set_biological_sex():
    """Sets the biological sex all four models use (CDSS dictionary: Female 0, Male 1)."""
    data = request.get_json(silent=True) or {}
    try:
        patient_id = parse_patient_id(data.get("patient_id"))
        sex = parse_biological_sex(data.get("biological_sex"))
    except ValidationError as exc:
        return _validation_error(exc)
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        return jsonify({"status": "error", "code": "PATIENT_NOT_FOUND", "error": "Patient not found."}), 404
    patient.biological_sex = sex
    db.session.commit()
    return jsonify({"status": "success", "patient_id": patient_id, "biological_sex": sex}), 200


@patient_bp.route('/fhrs', methods=['GET'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def get_fhrs():
    """The FHRS breakdown for one disease (?disease=cvd|t2d|resp|neuro). Computed, not stored."""
    from backend.fhrs_store import fhrs_summary, patient_fhrs
    claims = request.current_user
    target_pid, err = _target_patient(claims, request.args.get("patient_id"))
    if err:
        return err
    if not target_pid:
        return jsonify({"status": "error", "error": "Patient not identified"}), 404
    disease = parse_disease(request.args.get("disease"))
    if disease is None:
        return jsonify({"status": "error", "code": "VALIDATION_FAILED",
                        "error": "disease must be cvd, t2d, resp or neuro.", "fields": ["disease"]}), 400
    return jsonify({"status": "success", "patient_id": target_pid, "disease": disease,
                    "fhrs": fhrs_summary(patient_fhrs(target_pid, disease))}), 200


# --------------------------------------------------------------------------
# 3. CLINIC TRIAGE QUEUE & CHECK-IN
# --------------------------------------------------------------------------
@patient_bp.route('/queue', methods=['GET'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def get_queue():
    """Staff see the whole queue; a patient sees only their own ticket."""
    claims = request.current_user
    role = claims.get("role")
    own_pid = _resolve_patient_id(claims) if role == "PATIENT" else None
    return jsonify({"status": "success", "queue": QUEUE.list_for(role, own_pid)}), 200


@patient_bp.route('/queue/checkin', methods=['POST'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def submit_checkin():
    """Registers a patient in the triage queue. Only staff can set urgency and watch flags."""
    claims = request.current_user
    data = request.get_json(silent=True) or {}

    target_pid, err = _target_patient(claims, data.get("patient_id"))
    if err:
        return err
    if not target_pid:
        return jsonify({"status": "error", "error": "Patient identification required"}), 400

    ticket, created = QUEUE.checkin(target_pid, data, by_staff=claims.get("role") != "PATIENT")
    if not created:
        return jsonify({
            "status": "success",
            "message": "Patient is already checked into queue.",
            "ticket": ticket
        }), 200

    return jsonify({
        "status": "success",
        "message": "Checked in successfully.",
        "ticket": ticket
    }), 201


@patient_bp.route('/queue/<int:patient_id>', methods=['DELETE'])
@role_required(['PATIENT', 'DOCTOR', 'ADMIN'])
def cancel_checkin(patient_id):
    """Cancels a check-in ticket. A patient may cancel only their own."""
    claims = request.current_user
    role = claims.get("role")
    own_pid = _resolve_patient_id(claims) if role == "PATIENT" else None

    result = QUEUE.cancel(patient_id, role=role, caller_patient_id=own_pid)
    if result == "forbidden":
        return jsonify({"status": "error", "code": "FORBIDDEN", "message": "You can only cancel your own ticket."}), 403
    if result == "not_found":
        return jsonify({"status": "error", "message": "Ticket not found."}), 404
    return jsonify({"status": "success", "message": "Ticket cancelled."}), 200
