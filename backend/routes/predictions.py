import hashlib
import json
import logging
import uuid

from flask import Blueprint, jsonify, request

import backend.cdss.engine as engine
from backend.audit import log_event
from backend.biomarker_ranges import out_of_range
from backend.biomarkers import latest_biomarkers, patient_exists
from backend.cdss.features import FeatureError
from backend.middleware.rbac import role_required

log = logging.getLogger(__name__)

predictions_bp = Blueprint("predictions", __name__, url_prefix="/api/v1/predictions")

MODALITIES = ["cvd", "t2d", "resp", "neuro"]
FAIRNESS_GAP_THRESHOLD = 0.05  # same threshold as cdss/fairness.py


def _error(status_code, code, message, **extra):
    return jsonify({"status": "error", "code": code, "error": message, "retryable": False, **extra}), status_code


def _calibration(meta: dict, is_stub: bool) -> dict:
    """Calibration facts saved with the trained model (cross-validation metrics)."""
    if is_stub:
        return {"source": "deterministic_fallback", "method": None,
                "brier_score": None, "ece": None, "confidence": None}
    cv = meta.get("cv_metrics", {})
    return {
        "source": "trained_model",
        "method": meta.get("calibration_method"),
        "brier_score": cv.get("brier"),
        "ece": cv.get("ece"),
        "confidence": None,  # no per-prediction confidence is computed yet
    }


def _fairness(meta: dict, is_stub: bool) -> dict:
    """
    Model-level fairness from training cross-validation (not a per-patient check):
    the largest AUROC gap between subgroups, compared with the 0.05 threshold.
    """
    gap = None if is_stub else meta.get("cv_metrics", {}).get("subgroup_gap")
    if gap is None:
        return {"source": "not_available", "passed": None, "disparity_detected": None,
                "gap": None, "threshold": FAIRNESS_GAP_THRESHOLD, "subgroup_flags": []}
    gap = round(float(gap), 4)
    disparity = gap >= FAIRNESS_GAP_THRESHOLD
    return {
        "source": "training_cv",
        "passed": not disparity,
        "disparity_detected": disparity,
        "gap": gap,
        "threshold": FAIRNESS_GAP_THRESHOLD,
        "subgroup_flags": [f"Subgroup AUROC gap {gap:.3f} exceeds {FAIRNESS_GAP_THRESHOLD} threshold"] if disparity else [],
    }


@predictions_bp.route("/infer", methods=["POST"])
@role_required(["DOCTOR", "ADMIN"])
def run_cdss_inference():
    """
    Executes CDSS inference and TreeSHAP attributions using the loaded XGBoost model artifacts.
    Calibration and fairness are reported from the trained model's metadata.
    """
    req_data = request.get_json(silent=True) or {}

    try:
        patient_id = int(req_data["patient_id"])
    except (KeyError, TypeError, ValueError):
        return _error(400, "MISSING_PATIENT_ID", "Field 'patient_id' is required and must be an integer.")

    modality = str(req_data.get("modality", "cvd")).lower()
    if modality not in MODALITIES:
        return _error(400, "UNKNOWN_MODALITY", f"modality must be one of {MODALITIES}.")

    if not patient_exists(patient_id):
        return _error(404, "PATIENT_NOT_FOUND", f"Patient {patient_id} not found.")

    baseline_hash = req_data.get("baseline_hash")
    biomarker_payload = req_data.get("biomarker_payload") or {}
    if not isinstance(biomarker_payload, dict):
        return _error(400, "INVALID_FEATURE", "biomarker_payload must be an object.")

    # Values sent with the request must be inside the dictionary ranges the models were
    # trained on (stored values were already checked when they were saved).
    biomarker_source = "request"
    outside = out_of_range(modality, biomarker_payload)
    if outside:
        return _error(400, "OUT_OF_RANGE", "; ".join(outside.values()), fields=list(outside))

    # No biomarkers in the request: use the patient's latest stored values for this modality.
    if not biomarker_payload:
        stored = latest_biomarkers(modality, patient_id)
        if not stored:
            return _error(404, "NO_BIOMARKERS",
                          f"No biomarker_payload sent and no {modality} biomarkers stored for this patient.")
        biomarker_payload, biomarker_source = stored, "database"

    try:
        risk = engine.evaluate_biomarkers(modality, biomarker_payload)
    except FeatureError as exc:
        return _error(400, "INVALID_FEATURE", str(exc))

    meta = engine.registry.metadata(modality)
    is_stub = risk["is_stub"]
    score_val, tier_val = risk["score"], risk["tier"]

    # Reference hash of this inference's inputs and outputs (not a tamper-proof seal).
    fingerprint = json.dumps(
        {"patient_id": patient_id, "modality": modality, "inputs": biomarker_payload,
         "score": score_val, "tier": tier_val, "model_version": risk["model_version"]},
        sort_keys=True, separators=(",", ":"), default=str,
    )
    inf_hash = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    encounter_uid = req_data.get("encounter_id") or f"ENC-INF-{uuid.uuid4().hex[:8].upper()}"

    risk_dict = {
        "score": score_val,
        "probability": risk["probability"],
        "tier": tier_val,
        "domains": {modality: {"score": score_val, "tier": tier_val}},
    }
    fairness_dict = _fairness(meta, is_stub)

    # FHRS is not computed by the backend yet; values stay empty until it is.
    fhrs_dict = {"base_score": None, "environmental_modifier": None, "placeholder": True}

    response_payload = {
        "status": "success",
        "encounter_id": encounter_uid,
        "cryptographic_hash": inf_hash,
        "patient_id": patient_id,
        "modality": modality,
        "model_version": risk["model_version"],
        "is_stub": is_stub,
        "missing_features": risk["missing_features"],
        "biomarker_source": biomarker_source,
        "biomarker_payload": biomarker_payload,
        "risk": risk_dict,
        "shap": {"drivers": risk["drivers"]},
        "fairness": fairness_dict,
        "calibration": _calibration(meta, is_stub),
        "fhrs_decomposition": fhrs_dict,
        # Backward-compatibility aliases
        "risk_assessment": risk_dict,
        "shap_explanations": {"top_risk_drivers": risk["drivers"]},
        "fairness_audit": fairness_dict,
    }

    if baseline_hash is not None:
        # Trajectory comparison against the baseline is not implemented yet.
        response_payload["biomarker_deltas"] = {"metrics": {}, "placeholder": True}
        response_payload["proposed_reanchor"] = {
            "eligible": None,
            "placeholder": True,
            "reason": "Trajectory comparison against the baseline is not implemented yet.",
        }

    # Every inference is written to the sealed audit ledger. If that fails, the result is
    # not returned: an AI result with no audit trail must not reach a clinician.
    claims = request.current_user
    try:
        response_payload["audit_id"] = log_event(
            "INFERENCE",
            {
                "modality": modality,
                "model_version": risk["model_version"],
                "is_stub": is_stub,
                "biomarker_source": biomarker_source,
                "inputs": biomarker_payload,
                "score": score_val,
                "probability": risk["probability"],
                "tier": tier_val,
                "missing_features": risk["missing_features"],
                "drivers": risk["drivers"],
                "inference_hash": inf_hash,
            },
            patient_id=patient_id,
            doctor_id=claims.get("doctor_id"),
            actor_user_id=claims.get("user_id"),
        )
    except Exception:
        log.exception("Audit log failed for inference on patient %s", patient_id)
        return _error(500, "AUDIT_LOG_FAILED", "The inference could not be recorded in the audit ledger. Please retry.")

    return jsonify(response_payload), 200


@predictions_bp.route("/models/status", methods=["GET"])
@role_required(["DOCTOR", "ADMIN"])
def models_status():
    """Loaded state, integrity problems and version warnings for every disease head."""
    return jsonify(engine.registry.status()), 200


@predictions_bp.route("/models/reload", methods=["POST"])
@role_required(["ADMIN"])
def models_reload():
    """Clear the cache of the registry inference uses, so the next call reloads from disk."""
    engine.registry.clear_cache()
    try:
        audit_id = log_event("MODELS_RELOADED", {"message": "Model cache cleared"},
                             actor_user_id=request.current_user.get("user_id"))
    except Exception:
        log.exception("Audit log failed for model reload")
        return _error(500, "AUDIT_LOG_FAILED", "Models were reloaded but the audit entry could not be written.")
    return jsonify({"status": "success", "message": "Model cache cleared", "audit_id": audit_id}), 200
