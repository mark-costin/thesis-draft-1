"""Frontend rules for talking to the CDSS backend (Frontend API Guide, 2026-10-15).

No Streamlit imports here, so every rule can be unit-tested. The UI never computes a
risk score, an FHRS weight or a band: this module only translates form choices into
the codes the API expects and reads the API's replies for display.
"""
import datetime
import uuid

# ==============================================================================
# DISEASES
# ==============================================================================
MODALITY_CODES = {
    "Cardiovascular Diseases (Hypertension / CVD)": "cvd",
    "Type 2 Diabetes Mellitus": "t2d",
    "Chronic Respiratory Diseases (COPD & Asthma)": "resp",
    "Mental Health & Neurological Disorders": "neuro",
}
MODALITY_LABELS = {code: label for label, code in MODALITY_CODES.items()}

DISEASE_CHOICES = {  # code -> short label (family history, hazards, FHRS)
    "cvd": "Cardiovascular",
    "t2d": "Type 2 diabetes",
    "resp": "Respiratory (asthma / COPD)",
    "neuro": "Neurological / mental health",
}

# ==============================================================================
# FAMILY HISTORY (send tier + onset codes only; the backend owns the weights)
# ==============================================================================
TIER_CHOICES = {
    "Tier 1 · first-degree (parent, sibling, child)": 1,
    "Tier 2 · second-degree (grandparent, aunt/uncle, half-sibling)": 2,
    "Tier 3 · third-degree (first cousin)": 3,
}
ONSET_CHOICES = {
    "Severe early": "severe_early",
    "Early": "early",
    "Typical": "typical",
    "Late": "late",
}
PATIENT_DISEASE_CHOICES = {
    "Cardiovascular Disease / Hypertension": "cvd",
    "Type 2 Diabetes Mellitus": "t2d",
    "Chronic Respiratory Disease (Asthma/COPD)": "resp",
    "Mental Health / Neurological Disorder": "neuro",
}
PATIENT_TIER_CHOICES = {
    "Immediate Family (Parent, Sibling, Child)": 1,
    "Extended Family (Grandparent, Aunt, Uncle)": 2,
    "Distant Relative (Cousin)": 3,
}
PATIENT_ONSET_CHOICES = {
    "Childhood / Teens (Very Early)": "severe_early",
    "20s - 30s (Early)": "early",
    "40s - 50s (Typical)": "typical",
    "60+ (Late)": "late",
}
TIER_LABELS = {1: "Tier 1", 2: "Tier 2", 3: "Tier 3"}
ONSET_LABELS = {code: label for label, code in ONSET_CHOICES.items()}


def build_family_history_payload(disease, tier, onset, *, specific_diagnosis=None, age_at_diagnosis=None,
                                 shared_environment=None, is_verified=None, patient_id=None):
    """Body for POST /patient/family-history. Never includes weights."""
    if disease not in DISEASE_CHOICES:
        raise ValueError(f"Unknown disease '{disease}'. Use one of: {', '.join(DISEASE_CHOICES)}.")
    if tier not in (1, 2, 3):
        raise ValueError("Relationship tier must be 1, 2 or 3.")
    if onset not in ONSET_LABELS:
        raise ValueError(f"Unknown onset '{onset}'. Use one of: {', '.join(ONSET_LABELS)}.")
    payload = {"disease_domain": disease, "relationship_tier": tier, "onset_classification": onset}
    if specific_diagnosis and str(specific_diagnosis).strip():
        payload["specific_diagnosis"] = str(specific_diagnosis).strip()
    if age_at_diagnosis is not None:
        if not 0 <= age_at_diagnosis <= 120:
            raise ValueError("Age at diagnosis must be between 0 and 120.")
        payload["age_at_diagnosis"] = age_at_diagnosis
    if shared_environment is not None:
        payload["shared_environment"] = bool(shared_environment)
    if is_verified is not None:
        payload["is_verified"] = bool(is_verified)
    if patient_id is not None:
        payload["patient_id"] = patient_id
    return payload


# ==============================================================================
# HAZARDS (choices come only from the backend's catalogue)
# ==============================================================================
def recorded_hazards(hazards, disease):
    return [h for h in (hazards or []) if h.get("disease_domain") == disease]


def hazard_choices(catalogue, disease, recorded=()):
    taken = {h.get("hazard_code") for h in recorded_hazards(recorded, disease)}
    return [h for h in (catalogue or {}).get(disease, []) if h.get("code") not in taken]


# ==============================================================================
# REPLIES AND ERRORS
# ==============================================================================
def is_ok(resp):
    return isinstance(resp, dict) and 200 <= resp.get("_http_status", 0) < 300


def strip_meta(resp):
    return {k: v for k, v in (resp or {}).items() if not str(k).startswith("_")}


def error_info(resp):
    """None for a success; otherwise {code, message, fields, retryable}."""
    if is_ok(resp):
        return None
    if resp is None:
        return {"code": "NETWORK", "message": "Cannot reach the backend server.", "fields": [], "retryable": True}
    return {
        "code": resp.get("code") or "ERROR",
        "message": resp.get("error") or resp.get("message") or f"Request failed (HTTP {resp.get('_http_status', '?')}).",
        "fields": list(resp.get("fields") or []),
        "retryable": bool(resp.get("retryable", False)),
    }


_FRIENDLY = {
    "NETWORK": "Cannot reach the backend. Check that the Flask server is running.",
    "NO_BIOMARKERS": "No biomarkers are stored for this disease yet. Save a set of values first, then run the model.",
    "PATIENT_NOT_FOUND": "Patient not found.",
    "AUDIT_LOG_FAILED": "No result is shown because its audit entry could not be saved. Try again.",
    "BASELINE_EXISTS": "This patient already has a baseline. Reload the page: this visit is a follow-up.",
    "NO_BASELINE": "This patient has no baseline yet. Commit a baseline encounter first.",
    "STALE_PARENT_HASH": "The patient's record changed since you loaded it. Reload, then commit again.",
    "IDEMPOTENCY_IN_PROGRESS": "The first save is still running. Wait a moment, then try again.",
    "ALREADY_RECORDED": "That hazard is already recorded.",
    "DOCTOR_PROFILE_MISSING": "This account has no doctor profile, so it can't save consultations.",
    "FORBIDDEN": "You don't have access to that record.",
}


def friendly_error(resp):
    info = error_info(resp)
    if info is None:
        return ""
    code = info["code"]
    if code in ("OUT_OF_RANGE", "VALIDATION_FAILED", "USERNAME_TAKEN", "LICENSE_EXISTS", "EMAIL_EXISTS"):
        return info["message"]
    return _FRIENDLY.get(code, info["message"])


# ==============================================================================
# IDEMPOTENCY KEYS (one per Save click, the same one on retry)
# ==============================================================================
def _idem_slot(scope):
    return f"_idem::{scope}"


def idempotency_key(state, scope):
    slot = _idem_slot(scope)
    if not state.get(slot):
        state[slot] = str(uuid.uuid4())
    return state[slot]


def release_idempotency_key(state, scope):
    state.pop(_idem_slot(scope), None)


# ==============================================================================
# LOGIN STATE
# ==============================================================================
DISPLAY_PREFERENCES = ("night_light", "night_light_warmth")


def clear_auth_state(state, keep=DISPLAY_PREFERENCES):
    """Forget the login and every patient/clinical value; keep display preferences only."""
    for key in list(state.keys()):
        if key not in keep:
            del state[key]
    state["authenticated"] = False


# ==============================================================================
# BASELINE AND ENCOUNTERS
# ==============================================================================
def baseline_phase(resp):
    """2 = baseline exists, 1 = start intake (404 has_baseline false), None = could not tell."""
    if isinstance(resp, dict) and resp.get("has_baseline") is True and is_ok(resp):
        return 2
    if isinstance(resp, dict) and resp.get("_http_status") == 404:
        return 1
    return None


def encounter_type_for(phase):
    return "BASELINE" if phase == 1 else "FOLLOWUP"


# ==============================================================================
# INFERENCE RESULT
# ==============================================================================
def fhrs_view(fhrs):
    if not isinstance(fhrs, dict):
        return None
    return {
        "bio_fhrs": fhrs.get("bio_fhrs", fhrs.get("base_score")),
        "pedigree_sum": fhrs.get("pedigree_sum"),
        "clustering": fhrs.get("clustering"),
        "environmental_modifier": fhrs.get("environmental_modifier"),
        "adjusted_fhrs": fhrs.get("adjusted_fhrs"),
        "band": fhrs.get("band"),
        "band_label": fhrs.get("band_label"),
        "relatives_counted": fhrs.get("relatives_counted"),
        "hazards": fhrs.get("hazards") or [],
        "skipped_records": fhrs.get("skipped_records") or [],
    }


def summarize_inference(resp):
    resp = resp or {}
    risk = resp.get("risk") or resp.get("risk_assessment") or {}
    score = risk.get("score")
    if score is None and risk.get("probability") is not None:
        score = float(risk["probability"]) * 100.0
    tier = risk.get("tier")
    is_stub = bool(resp.get("is_stub")) or tier == "UNAVAILABLE"
    shap = resp.get("shap") or resp.get("shap_explanations") or {}
    raw_drivers = shap.get("drivers") or shap.get("top_risk_drivers") or []
    drivers = []
    for d in raw_drivers:
        try:
            drivers.append((d.get("display_name") or d.get("feature") or "Feature", float(d.get("shap_value"))))
        except (TypeError, ValueError):
            continue
    drivers.sort(key=lambda item: abs(item[1]), reverse=True)
    return {
        "show_result": (not is_stub) and score is not None and tier not in (None, "UNAVAILABLE"),
        "is_stub": is_stub,
        "score": None if is_stub else score,
        "tier": tier,
        "missing_features": list(resp.get("missing_features") or []),
        "source": resp.get("biomarker_source"),
        "drivers": drivers,
        "fhrs": fhrs_view(resp.get("fhrs_decomposition")),
        "fairness": resp.get("fairness") or resp.get("fairness_audit") or {},
        "calibration": resp.get("calibration") or {},
        "trace": {k: resp.get(k) for k in ("audit_id", "model_version", "encounter_id", "cryptographic_hash")
                  if resp.get(k) is not None},
    }


def tier_color(tier):
    return {"HIGH": "#ef4444", "MODERATE": "#f59e0b", "LOW": "#10b981"}.get(tier, "#64748b")


# ==============================================================================
# BIOMARKERS (column names of each disease table; ranges are display hints only,
# the backend enforces the dictionary ranges and names the bad field)
# ==============================================================================
def _f(column, label, unit="", lo=None, hi=None, step=0.1, kind="float", model_input=False):
    return {"column": column, "label": label, "unit": unit, "min": lo, "max": hi, "step": step,
            "kind": kind, "model_input": model_input}


BIOMARKER_FIELDS = {
    "cvd": [
        _f("sbp", "Systolic blood pressure", "mmHg", 70, 220, 1.0, model_input=True),
        _f("dbp", "Diastolic blood pressure", "mmHg", 40, 130, 1.0, model_input=True),
        _f("resting_hr", "Resting heart rate", "bpm", 40, 180, 1.0, model_input=True),
        _f("total_cholesterol", "Total cholesterol", "mg/dL", 100, 400, 1.0, model_input=True),
        _f("hdl", "HDL cholesterol", "mg/dL", 15, 120, 1.0, model_input=True),
        _f("ldl", "LDL cholesterol", "mg/dL", 30, 300, 1.0, model_input=True),
        _f("triglycerides", "Triglycerides", "mg/dL", 40, 1000, 1.0, model_input=True),
        _f("egfr", "eGFR", "mL/min/1.73m²", 5, 140, 1.0, model_input=True),
        _f("bmi", "Body mass index", "kg/m²", 12.0, 60.0),
        _f("hs_crp", "hs-CRP", "mg/L", 0.1, 50.0),
        _f("serum_creatinine", "Serum creatinine", "mg/dL", 0.4, 10.0, 0.01),
        _f("lvef", "LVEF", "%", 15, 75, 1.0),
        _f("ctni", "Cardiac troponin I", "ng/mL", 0.01, 50.0, 0.01),
        _f("nt_probnp", "NT-proBNP", "pg/mL", 10, 35000, 10.0),
        _f("smoking_history", "Smoking history", "pack-years", 0, 120, 1.0),
        _f("daily_sodium", "Daily sodium intake", "mg/day", 500, 10000, 50.0),
        _f("physical_activity", "Physical activity", "min/week", 0, 1050, 15.0),
    ],
    "t2d": [
        _f("hba1c", "HbA1c", "%", 4.0, 15.0, model_input=True),
        _f("fpg", "Fasting plasma glucose", "mg/dL", 50, 450, 1.0, model_input=True),
        _f("bmi", "Body mass index", "kg/m²", 12.0, 60.0, model_input=True),
        _f("triglycerides", "Triglycerides", "mg/dL", 40, 1000, 1.0, model_input=True),
        _f("hdl", "HDL cholesterol", "mg/dL", 15, 120, 1.0, model_input=True),
        _f("postprandial_glucose_2h", "2-hour postprandial glucose", "mg/dL", 60, 600, 1.0),
        _f("fasting_insulin", "Fasting insulin", "µIU/mL", 1.0, 100.0, 0.5),
        _f("c_peptide", "C-peptide", "ng/mL", 0.1, 12.0),
        _f("homa_ir", "HOMA-IR", "", 0.2, 25.0),
        _f("waist_circumference", "Waist circumference", "cm", 50, 160, 0.5),
        _f("whr", "Waist-to-hip ratio", "", 0.60, 1.40, 0.01),
        _f("sbp", "Systolic blood pressure", "mmHg", 70, 220, 1.0),
        _f("dbp", "Diastolic blood pressure", "mmHg", 40, 130, 1.0),
        _f("uacr", "Urine albumin-to-creatinine ratio", "mg/g", 1, 3500, 1.0),
        _f("serum_uric_acid", "Serum uric acid", "mg/dL", 1.5, 14.0),
        _f("gestational_diabetes", "History of gestational diabetes", kind="flag"),
        _f("acanthosis_nigricans", "Acanthosis nigricans present", kind="flag"),
        _f("daily_carbs", "Daily carbohydrate intake", "g/day", 50, 600, 5.0),
        _f("sedentary_duration", "Daily sedentary time", "h/day", 1.0, 18.0, 0.5),
    ],
    "resp": [
        _f("fev1", "FEV1", "L", 0.5, 5.5, model_input=True),
        _f("fvc", "FVC", "L", 1.0, 7.0, model_input=True),
        _f("fev1_fvc_ratio", "FEV1/FVC ratio", "%", 25.0, 95.0, model_input=True),
        _f("spo2", "Oxygen saturation (SpO2)", "%", 65.0, 100.0, model_input=True),
        _f("post_bd_fev1_pred", "Post-bronchodilator FEV1", "% predicted", 15.0, 120.0),
        _f("pef", "Peak expiratory flow", "L/min", 50, 800, 1.0),
        _f("eosinophil_count", "Blood eosinophil count", "cells/µL", 0, 2500, 1.0),
        _f("feno", "FeNO", "ppb", 5, 150, 1.0),
        _f("pao2", "PaO2", "mmHg", 40, 110, 1.0),
        _f("paco2", "PaCO2", "mmHg", 25, 90, 1.0),
        _f("mmrc_score", "mMRC breathlessness", "", 0, 4, 1, kind="int"),
        _f("act_score", "Asthma Control Test", "", 5, 25, 1, kind="int"),
        _f("cat_score", "COPD Assessment Test", "", 0, 40, 1, kind="int"),
        _f("serum_ige", "Serum IgE", "IU/mL", 2, 3000, 1.0),
        _f("annual_exacerbations", "Flare-ups per year", "", 0, 15, 1, kind="int"),
        _f("tobacco_exposure", "Tobacco exposure", "pack-years", 0, 120, 1.0),
        _f("occupational_dust", "Occupational dust exposure", kind="flag"),
        _f("allergic_rhinitis", "Allergic rhinitis", kind="flag"),
        _f("childhood_asthma", "Asthma in childhood", kind="flag"),
        _f("bmi", "Body mass index", "kg/m²", 12.0, 60.0),
    ],
    "neuro": [
        _f("mmse", "MMSE", "", 0, 30, 1, kind="int", model_input=True),
        _f("phq9", "PHQ-9", "", 0, 27, 1, kind="int", model_input=True),
        _f("gad7", "GAD-7", "", 0, 21, 1, kind="int", model_input=True),
        _f("daily_sleep", "Sleep per day", "h", 1.0, 16.0, model_input=True),
        _f("moca", "MoCA", "", 0, 30, 1, kind="int"),
        _f("ham_d", "Hamilton Depression Rating", "", 0, 52, 1, kind="int"),
        _f("updrs_part3", "UPDRS part III", "", 0, 132, 1, kind="int"),
        _f("psqi", "Pittsburgh Sleep Quality Index", "", 0, 21, 1, kind="int"),
        _f("seizure_frequency", "Seizure frequency", "", 0, 100, 1.0),
        _f("hrv_sdnn", "Heart rate variability (SDNN)", "ms", 5.0, 250.0),
        _f("serum_cortisol", "Serum cortisol", "µg/dL", 1.0, 45.0),
        _f("vitamin_b12", "Vitamin B12", "pg/mL", 50, 2000, 1.0),
        _f("serum_folate", "Serum folate", "ng/mL", 1.0, 25.0),
        _f("tsh", "TSH", "mIU/L", 0.01, 100.0, 0.01),
        _f("faq_score", "Functional Activities Questionnaire", "", 0, 30, 1, kind="int"),
        _f("tremor_rating", "Tremor severity", "", 0, 4, 1, kind="int"),
        _f("tbi_history", "History of traumatic brain injury", kind="flag"),
        _f("substance_abuse", "Substance abuse", kind="flag"),
    ],
}


def field_labels(disease, columns):
    """Form labels for the columns a validation error names (unknown names pass through)."""
    labels = {f["column"]: f["label"] for f in BIOMARKER_FIELDS.get(disease, [])}
    return [labels.get(c, c) for c in columns or []]


def clean_biomarker_values(values):
    """Drop untested values (None / empty). A 0 typed on purpose stays."""
    return {k: v for k, v in (values or {}).items() if v is not None and v != ""}


# ==============================================================================
# PATIENT HEADER
# ==============================================================================
def _age_on(dob_text, today):
    try:
        dob = datetime.date.fromisoformat(str(dob_text)[:10])
    except (TypeError, ValueError):
        return None
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def patient_profile(resp):
    """The patient row from GET /doctor/patient/<id> (bare or under 'patient'/'profile'), or None."""
    if not is_ok(resp):
        return None
    for key in ("patient", "profile"):
        if isinstance(resp.get(key), dict):
            return resp[key]
    return strip_meta(resp)


def models_status_rows(resp):
    """One row per loaded/unloaded disease head from GET /predictions/models/status."""
    if not is_ok(resp):
        return []
    models = resp.get("models") if isinstance(resp.get("models"), dict) else resp
    rows = []
    for disease in MODALITY_LABELS:
        info = models.get(disease)
        if isinstance(info, dict):
            rows.append({"disease": disease, "loaded": bool(info.get("loaded")),
                         "model_version": info.get("model_version"), "problem": info.get("problem"),
                         "warnings": list(info.get("version_warnings") or [])})
    return rows


def patient_header(profile, today=None):
    profile = profile or {}
    today = today or datetime.date.today()
    first, last = (profile.get("first_name") or "").strip(), (profile.get("last_name") or "").strip()
    pid = profile.get("patient_id")
    name = f"{last}, {first}".strip(", ") if (first or last) else f"Patient #{pid}"
    dob = profile.get("date_of_birth")
    return {
        "patient_id": pid,
        "name": name,
        "dob": dob,
        "age": _age_on(dob, today) if dob else None,
        "sex": profile.get("biological_sex") or "Not set",
    }


# ==============================================================================
# CARE PLAN, ENCOUNTER COMMIT, CONSULTATION
# ==============================================================================
def split_medications(text):
    if isinstance(text, list):
        return [str(m).strip() for m in text if str(m).strip()]
    return [m.strip() for m in str(text or "").split(",") if m.strip()]


def build_care_plan(directive, medications_text, lifestyle_text, tier=None, condition=None):
    return {
        "clinical_directive": (directive or "").strip(),
        "medications": split_medications(medications_text),
        "lifestyle_directives": (lifestyle_text or "").strip(),
        "primary_condition": condition,
        "risk_classification": tier,
    }


def read_care_plan(cp):
    """Reads both the current names and the older ones (clinical_order, prescriptions, directive)."""
    cp = cp or {}
    lifestyle = cp.get("lifestyle_directives")
    if isinstance(lifestyle, list):
        lifestyle = ", ".join(str(x) for x in lifestyle)
    return {
        "directive": cp.get("clinical_directive") or cp.get("clinical_order") or cp.get("directive"),
        "medications": split_medications(cp.get("medications") or cp.get("prescriptions")),
        "lifestyle": lifestyle or "",
        "primary_condition": cp.get("primary_condition"),
        "risk_classification": cp.get("risk_classification"),
    }


def commit_blockers(phase, inference, inference_patient_id, patient_id):
    reasons = []
    if phase is None:
        reasons.append("Could not check whether this patient has a baseline. Reload the page.")
    if not is_ok(inference) or inference_patient_id != patient_id:
        reasons.append("Run the model for this patient first. The result is saved as part of the encounter.")
    elif not summarize_inference(inference)["show_result"]:
        reasons.append("The model was not loaded (stub result). A stub can't be committed as a clinical result.")
    return reasons


def build_commit_payload(patient_id, phase, inference, care_plan):
    return {
        "patient_id": patient_id,
        "encounter_type": encounter_type_for(phase),
        "cdss_payload_snapshot": strip_meta(inference),
        "care_plan": care_plan,
    }


def build_consultation_payload(patient_id, directives, notes=""):
    directives = (directives or "").strip()
    notes = (notes or "").strip()
    if not directives:
        raise ValueError("Write at least one directive.")
    if len(notes) > 5000:
        raise ValueError("Notes can be at most 5000 characters.")
    return {"patient_id": patient_id, "directives": directives, "notes": notes}


# ==============================================================================
# QUEUE, DIRECTORY, PROVISIONING
# ==============================================================================
def queue_tickets(resp):
    return list(resp.get("queue") or []) if is_ok(resp) else []


def own_waiting_ticket(resp):
    return next((t for t in queue_tickets(resp) if t.get("status", "WAITING") == "WAITING"), None)


def directory_rows(resp):
    if not is_ok(resp):
        return []
    for key in ("_items", "users", "accounts", "directory"):
        if isinstance(resp.get(key), list):
            return resp[key]
    return []


PROVISION_REQUIRED = ["username", "password", "first_name", "last_name", "address", "specialization",
                      "license_number", "contact_number", "email", "emergency_contact_name",
                      "emergency_contact_number", "emergency_relation"]
PROVISION_OPTIONAL = ["middle_name", "hospital_affiliation"]


def build_provision_payload(form):
    """Body for POST /admin/provision, plus the list of required fields still empty."""
    payload, missing = {}, []
    for name in PROVISION_REQUIRED:
        value = str(form.get(name) or "").strip() if name != "password" else (form.get(name) or "")
        if not value:
            missing.append(name)
        else:
            payload[name] = value
    for name in PROVISION_OPTIONAL:
        value = str(form.get(name) or "").strip()
        if value:
            payload[name] = value
    return payload, missing
