import datetime

@doctor_bp.route('/patient/<int:patient_id>/baseline', methods=['GET'])
@role_required(['DOCTOR', 'ADMIN'])
def get_patient_baseline(patient_id):
    """
    Queries encounters for the latest valid baseline record (Phase C / D2 resolution).
    """
    baseline_encounter = Encounter.query.filter_by(
        patient_id=patient_id, 
        record_type='BASELINE'
    ).order_by(Encounter.created_at_utc.desc()).first()
    
    if not baseline_encounter:
        return jsonify({
            "status": "success",
            "has_baseline": False,
            "message": "No established clinical baseline found. Initiate Phase 1 Intake."
        }), 404
        
    payload = baseline_encounter.cdss_payload or {}

    # 1. Biomarkers resolution (handles both nested and flat payloads)
    biomarkers = payload.get("biomarker_payload")
    if biomarkers is None:
        known_meta = {
            "risk_assessment", "fhrs_decomposition", "fhrs_data", 
            "fairness_audit", "shap_explanations", "modality", 
            "model_version", "patient_id", "status"
        }
        biomarkers = {k: v for k, v in payload.items() if k not in known_meta}

    # 2. FHRS data resolution
    fhrs_data = payload.get("fhrs_data") or payload.get("fhrs_decomposition") or {}

    # 3. Risk domains resolution
    risk_data = payload.get("risk_assessment", {})
    if isinstance(risk_data, dict) and "domains" in risk_data:
        baseline_risk = risk_data.get("domains", {})
    elif isinstance(risk_data, dict):
        baseline_risk = risk_data
    else:
        baseline_risk = {}

    # 4. Standard ISO-8601 UTC timestamp format (resolves +08:00Z bug)
    ts = baseline_encounter.created_at_utc
    if ts:
        if ts.tzinfo is not None:
            ts = ts.astimezone(datetime.timezone.utc)
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