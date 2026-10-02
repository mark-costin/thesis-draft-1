import time
import uuid
import json
import hashlib
import datetime
from flask import request, jsonify
from backend.dbconnect import db
from backend.model_orm.pat_orm import Patient
from backend.model_orm.clinic_orm import Encounter, IdempotencyCache
from backend.routes.doctor import doctor_bp
from backend.middleware.auth import role_required
# Ensure role_required is imported from your auth middleware
# from backend.middleware.auth import role_required


def json_sort_safe(obj):
    """Deterministic JSON serialization helper for cryptographic hashing."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)


def sign_record(patient_id: int, doctor_id: int, cdss_payload: dict, parent_baseline_hash: str, timestamp_str: str) -> str:
    """
    D4: Deterministic SHA-256 cryptographic seal binding clinical entities,
    prior anchor hash, timestamp, and multi-modal payload snapshot.
    """
    raw_signature_string = f"{patient_id}:{doctor_id}:{parent_baseline_hash or 'ROOT'}:{timestamp_str}:{json_sort_safe(cdss_payload)}"
    return hashlib.sha256(raw_signature_string.encode('utf-8')).hexdigest()


@doctor_bp.route('/commit-encounter', methods=['POST'])
@role_required(['DOCTOR'])
def commit_encounter_atomic():
    """
    D5: Seals physician directives, prescriptions, CDSS predictions, 
    and cryptographic proof into an immutable ACID database transaction.
    Enforces a 24-hour idempotency cache window (D6).
    """
    # 1. Enforce Idempotency-Key Header
    idem_key = request.headers.get("Idempotency-Key")
    if not idem_key:
        return jsonify({
            "status": "error",
            "code": "IDEMPOTENCY_KEY_MISSING",
            "error": "Idempotency-Key header is required for atomic encounter commitments.",
            "retryable": False
        }), 400

    current_time = time.time()

    # 2. Check 24-Hour Idempotency Cache Window
    cached_entry = IdempotencyCache.query.get(idem_key)
    if cached_entry:
        if current_time - cached_entry.timestamp < 86400:
            return jsonify(cached_entry.data), 200
        else:
            # TTL Expired: Purge stale entry and proceed
            db.session.delete(cached_entry)
            db.session.commit()

    # 3. Payload Extraction & Validation
    data = request.get_json()
    if not data:
        return jsonify({
            "status": "error",
            "code": "INVALID_PAYLOAD",
            "error": "Encounter commitment payload is empty.",
            "retryable": False
        }), 400

    patient_id = data.get("patient_id")
    if not patient_id:
        return jsonify({
            "status": "error",
            "code": "MISSING_PATIENT_ID",
            "error": "Field 'patient_id' is required.",
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

    # Doctor ID resolved from auth context or fallback
    doctor_id = getattr(request, "doctor_id", None) or data.get("doctor_id", 1)

    # 4. Snapshot Preparation & Round-Trip Preservation (D3 fix)
    raw_snapshot = data.get("cdss_payload_snapshot", {})
    cdss_payload = dict(raw_snapshot) if isinstance(raw_snapshot, dict) else {}

    # Merge fhrs_data into snapshot if sent at root level
    if "fhrs_data" in data and "fhrs_data" not in cdss_payload:
        cdss_payload["fhrs_data"] = data["fhrs_data"]

    # Merge root biomarker payload if sent separately
    if "biomarker_payload" in data and "biomarker_payload" not in cdss_payload:
        cdss_payload["biomarker_payload"] = data["biomarker_payload"]

    # 5. Timestamp & Deterministic Cryptographic Seal (D4)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    timestamp_str = now_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    encounter_uid = f"ENC-{uuid.uuid4().hex[:8].upper()}"
    record_type = data.get("encounter_type", "BASELINE").upper()
    parent_baseline_hash = data.get("parent_baseline_hash") or cdss_payload.get("parent_baseline_hash")

    crypto_hash = sign_record(
        patient_id=patient_id,
        doctor_id=doctor_id,
        cdss_payload=cdss_payload,
        parent_baseline_hash=parent_baseline_hash,
        timestamp_str=timestamp_str
    )

    # 6. Response Receipt Construction
    receipt_data = {
        "status": "success",
        "envelope_status": "SEALED",
        "encounter_id": encounter_uid,
        "record_type": record_type,
        "cryptographic_hash": crypto_hash,
        "parent_baseline_hash": parent_baseline_hash,
        "committed_at_utc": timestamp_str,
        "audit_trail": {
            "atomic_transaction_id": f"tx_pg_{uuid.uuid4().hex[:8]}",
            "attending_physician_id": doctor_id,
            "signing_algorithm": "SHA-256",
            "verification_status": "COMMITTED_EHR"
        }
    }

    # 7. Atomic Transaction Boundary (D5 & D6)
    new_encounter = Encounter(
        encounter_uid=encounter_uid,
        patient_id=patient_id,
        doctor_id=doctor_id,
        record_type=record_type,
        parent_baseline_hash=parent_baseline_hash,
        cryptographic_hash=crypto_hash,
        cdss_payload=cdss_payload,
        care_plan=data.get("care_plan", {}),
        reanchor_decision=data.get("reanchor_decision"),
        created_at_utc=now_utc
    )

    cache_record = IdempotencyCache(
        key=idem_key,
        timestamp=current_time,
        data=receipt_data
    )

    try:
        db.session.add(new_encounter)
        db.session.add(cache_record)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "code": "DATABASE_COMMIT_FAILED",
            "error": f"Transaction rolled back due to error: {str(e)}",
            "retryable": True
        }), 500

    return jsonify(receipt_data), 201