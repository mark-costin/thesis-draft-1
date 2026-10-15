import logging

from flask import Blueprint, jsonify, request

from backend.biomarker_ranges import CHOICES, RANGES
from backend.biomarker_store import (
    column_spec, latest_row, metric_model, patient_exists, row_values, store_biomarkers,
)
from backend.middleware.idempotency import enforce_idempotency
from backend.middleware.rbac import role_required
from backend.validation import ValidationError, parse_patient_id, validate_biomarkers

log = logging.getLogger(__name__)

biomarkers_bp = Blueprint("biomarkers", __name__, url_prefix="/api/v1/biomarkers")

STAFF = ["DOCTOR", "ADMIN"]


def _error(status_code, code, message, **extra):
    return jsonify({"status": "error", "code": code, "error": message, **extra}), status_code


def _own_patient_id(claims):
    from backend.model_orm.pat_orm import Patient
    pat = Patient.query.filter_by(user_id=claims.get("user_id")).first()
    return pat.patient_id if pat else None


@biomarkers_bp.route("/<modality>", methods=["POST"])
@role_required(STAFF)
@enforce_idempotency
def store(modality):
    """
    Store one set of biomarkers for a patient.
    Body: {"patient_id": 5, "values": {"sbp": 142, "ldl": 150, ...}} using the column
    names of that modality's table (clinic_orm.py).
    """
    model = metric_model(modality)
    if model is None:
        return _error(404, "UNKNOWN_MODALITY", "modality must be one of cvd, t2d, resp, neuro.")

    data = request.get_json(silent=True) or {}
    try:
        patient_id = parse_patient_id(data.get("patient_id"))
        cleaned = validate_biomarkers(column_spec(model), data.get("values"),
                                      ranges=RANGES[modality], choices=CHOICES.get(modality))
    except ValidationError as exc:
        return _error(400, "VALIDATION_FAILED", str(exc), fields=exc.fields)

    if not patient_exists(patient_id):
        return _error(404, "PATIENT_NOT_FOUND", f"Patient {patient_id} not found.")

    try:
        row = store_biomarkers(modality, patient_id, cleaned)
    except Exception:
        log.exception("Storing %s biomarkers failed for patient %s", modality, patient_id)
        from backend.dbconnect import db
        db.session.rollback()
        return _error(500, "STORE_FAILED", "The biomarkers could not be saved. Please retry.")

    return jsonify({
        "status": "success",
        "modality": modality,
        "patient_id": patient_id,
        "metric_id": row.metric_id,
        "values": row_values(row),
    }), 201


@biomarkers_bp.route("/<modality>/latest", methods=["GET"])
@role_required(["PATIENT", "DOCTOR", "ADMIN"])
def latest(modality):
    """The most recent stored biomarkers. A patient always gets their own."""
    if metric_model(modality) is None:
        return _error(404, "UNKNOWN_MODALITY", "modality must be one of cvd, t2d, resp, neuro.")

    claims = request.current_user
    if claims.get("role") == "PATIENT":
        patient_id = _own_patient_id(claims)
    else:
        try:
            patient_id = parse_patient_id(request.args.get("patient_id"))
        except ValidationError as exc:
            return _error(400, "VALIDATION_FAILED", str(exc))
    if patient_id is None:
        return _error(404, "PATIENT_NOT_FOUND", "Patient identity could not be resolved.")

    row = latest_row(modality, patient_id)
    if row is None:
        return _error(404, "NO_BIOMARKERS", f"No {modality} biomarkers stored for this patient.")

    return jsonify({
        "status": "success",
        "modality": modality,
        "patient_id": patient_id,
        "metric_id": row.metric_id,
        "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
        "values": row_values(row),
    }), 200
