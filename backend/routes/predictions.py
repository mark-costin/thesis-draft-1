import hashlib
import json
import uuid

from flask import Blueprint, jsonify, request

import backend.cdss.engine as engine
from backend.cdss.features import FeatureError
from backend.middleware.rbac import role_required

predictions_bp = Blueprint("predictions", __name__, url_prefix="/api/v1/predictions")

MODALITIES = ["cvd", "t2d", "resp", "neuro"]
FAIRNESS_GAP_THRESHOLD = 0.05  # same threshold as cdss/fairness.py


def _error(status_code, code, message):
    return jsonify({"status": "error", "code": code, "error": message, "retryable": False}), status_code


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

    baseline_hash = req_data.get("baseline_hash")
    biomarker_payload = req_data.get("biomarker_payload") or {}
    if not isinstance(biomarker_payload, dict):
        return _error(400, "INVALID_FEATURE", "biomarker_payload must be an object.")

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
    return jsonify({"status": "success", "message": "Model cache cleared"}), 200
