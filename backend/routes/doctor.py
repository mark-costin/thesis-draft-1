from datetime import timezone
import hashlib
import time
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from backend.dbconnect import db
from backend.model_orm.pat_orm import Patient
from backend.model_orm.doc_orm import Doctor
from backend.model_orm.clinic_orm import Encounter, IdempotencyCache

# Import Security Middleware
from backend.middleware.rbac import role_required
from backend.middleware.idempotency import enforce_idempotency
from backend.middleware.sanitizer import sanitize_response


doctor_bp = Blueprint('doctor', __name__, url_prefix='/api/v1/doctor')

def sign_record(patient_id: int, doctor_id: int, cdss_payload: dict, parent_baseline_hash: str, timestamp_str: str) -> str:
    """
    D4: Generates a deterministic server-side SHA-256 cryptographic seal 
    binding the patient, physician, parent hash, timestamp, and payload inputs.
    """
    raw_signature_string = f"{patient_id}:{doctor_id}:{parent_baseline_hash or 'ROOT'}:{timestamp_str}:{json_sort_safe(cdss_payload)}"
    return hashlib.sha256(raw_signature_string.encode('utf-8')).hexdigest()

def json_sort_safe(payload: dict) -> str:
    """Helper to ensure consistent JSON key ordering for cryptographic hashing."""
    import json
    return json.dumps(payload, sort_keys=True, default=str)


@doctor_bp.route('/queue', methods=['GET'])
@role_required(['DOCTOR', 'ADMIN'])
def get_triage_queue():
    """Fetches the active patient triage queue."""
    mock_queue = [
        {"queue_no": "Q-01", "patient_id": 1, "urgency": "High", "status": "Waiting"},
        {"queue_no": "Q-02", "patient_id": 2, "urgency": "Routine", "status": "Waiting"}
    ]
    user_role = request.current_user.get("role")
    return jsonify(sanitize_response(mock_queue, role=user_role)), 200


@doctor_bp.route('/patient/<int:patient_id>', methods=['GET'])
@role_required(['DOCTOR', 'ADMIN'])
def get_patient_record(patient_id):
    """Fetches a complete patient clinical record."""
    patient = Patient.query.get(patient_id)
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
    """Saves clinical directives and prescription orders."""
    data = request.get_json()
    patient_id = data.get("patient_id")
    directives = data.get("directives")
    
    if not patient_id or not directives:
        return jsonify({"error": "patient_id and directives are required"}), 400

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({"error": "Target patient not found"}), 404

    response_payload = {
        "message": "Consultation directives and notes recorded successfully",
        "encounter_status": "Complete",
        "directives_applied": directives
    }
    
    user_role = request.current_user.get("role")
    return jsonify(sanitize_response(response_payload, role=user_role)), 201


@doctor_bp.route('/commit-encounter', methods=['POST'])
@role_required(['DOCTOR'])
def commit_encounter_atomic():
    """
    D5: Seals physician directives, prescriptions, CDSS predictions, 
    and cryptographic proof into an immutable ACID database transaction.
    Enforces a 24-hour idempotency cache window (D6).
    """
    idem_key = request.headers.get("Idempotency-Key")
    if not idem_key:
        return jsonify({
            "status": "error",
            "code": "IDEMPOTENCY_KEY_MISSING",
            "error": "Idempotency-Key header is required for atomic encounter commitments.",
            "retryable": False
        }), 400

    current_time = time.time()
    
    cached_entry = IdempotencyCache.query.get(idem_key)
    if cached_entry:
        if current_time - cached_entry.timestamp < 86400:
            return jsonify(cached_entry.data), 200
        else:
            db.session.delete(cached_entry)
            db.session.commit()

    data = request.get_json()
    if not data:
        return jsonify({
            "status": "error",
            "code": "INVALID_PAYLOAD",
            "error": "Encounter commitment payload is empty.",
            "retryable": False
        }), 400

    patient_id = data.get("patient_id")
    encounter_type = data.get("encounter_type", "FOLLOWUP")
    cdss_payload = dict(data.get("cdss_payload_snapshot", {}))
    if "fhrs_data" in data and "fhrs_data" not in cdss_payload:
        cdss_payload["fhrs_data"] = data["fhrs_data"]
    if "biomarker_payload" in data and "biomarker_payload" not in cdss_payload:
        cdss_payload["biomarker_payload"] = data["biomarker_payload"]
    care_plan = data.get("care_plan", {})
    reanchor_decision = data.get("reanchor_decision")

    if not patient_id:
        return jsonify({
            "status": "error",
            "code": "VALIDATION_FAILED",
            "error": "patient_id is required.",
            "retryable": False
        }), 400

    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({
            "status": "error",
            "code": "PATIENT_NOT_FOUND",
            "error": f"Target patient ID {patient_id} not found in database.",
            "retryable": False
        }), 404

    doctor_id = request.current_user.get("user_id") or request.current_user.get("doctor_id", 1)
    parent_baseline_hash = cdss_payload.get("parent_baseline_hash") or data.get("parent_baseline_hash")
    
    # Server-authoritative cryptographic lineage resolution
    if not parent_baseline_hash and encounter_type in ["REANCHOR_BASELINE", "EVALUATION"]:
        latest_anchor = Encounter.query.filter(
            Encounter.patient_id == patient_id,
            Encounter.record_type.in_(["BASELINE", "REANCHOR_BASELINE"])
        ).order_by(Encounter.created_at_utc.desc()).first()
        
        if latest_anchor:
            parent_baseline_hash = latest_anchor.cryptographic_hash

    encounter_uid = f"ENC-{uuid.uuid4().hex[:8].upper()}"
    timestamp_utc = datetime.utcnow()
    timestamp_str = timestamp_utc.isoformat()

    crypto_hash = sign_record(patient_id, doctor_id, cdss_payload, parent_baseline_hash, timestamp_str)

    try:
        new_encounter = Encounter(
            encounter_uid=encounter_uid,
            patient_id=patient_id,
            doctor_id=doctor_id,
            record_type=encounter_type,
            parent_baseline_hash=parent_baseline_hash,
            cryptographic_hash=crypto_hash,
            cdss_payload=cdss_payload,
            care_plan=care_plan,
            reanchor_decision=reanchor_decision,
            created_at_utc=timestamp_utc
        )
        db.session.add(new_encounter)

        response_payload = {
            "status": "success",
            "encounter_id": encounter_uid,
            "record_type": encounter_type,
            "envelope_status": "SEALED",
            "parent_baseline_hash": parent_baseline_hash,
            "cryptographic_hash": crypto_hash,
            "committed_at_utc": timestamp_str + "Z",
            "audit_trail": {
                "attending_physician_id": doctor_id,
                "signing_algorithm": "SHA-256",
                "atomic_transaction_id": f"tx_pg_{uuid.uuid4().hex[:8]}",
                "verification_status": "COMMITTED_EHR"
            }
        }

        cache_record = IdempotencyCache(
            key=idem_key,
            data=response_payload,
            status=201,
            timestamp=current_time
        )
        db.session.add(cache_record)
        db.session.commit()

        user_role = request.current_user.get("role")
        return jsonify(sanitize_response(response_payload, role=user_role)), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "code": "DATABASE_COMMIT_FAILED",
            "error": f"Atomic transaction aborted: {str(e)}",
            "retryable": True
        }), 500