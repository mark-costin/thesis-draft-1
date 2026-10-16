"""HTTP client for the CDSS Flask backend (all routes in the Frontend API Guide, 2026-10-15).

Every function returns the reply as a dict with "_http_status" added (lists come back
under "_items"), or None when the backend can't be reached. Pages read replies with
cdss_logic.is_ok / friendly_error. Nothing here draws on the page.
"""
import os

import requests
import streamlit as st

try:
    from frontend import cdss_logic
except ImportError:  # running with frontend/ itself on sys.path
    import cdss_logic

# ==========================================
# EXPLICIT API VERSION PINNING (D1)
# ==========================================
API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
API_VERSION = "v1"
BASE_URL = f"{API_BASE}/api/{API_VERSION}"

SESSION_EXPIRED_NOTICE = "Your session ended. Please log in again."


# ==============================================================================
# CORE REQUEST
# ==============================================================================
def _headers(json_body=False, auth=True, idempotency_key=None):
    headers = {}
    if json_body:
        headers["Content-Type"] = "application/json"
    token = st.session_state.get("token") if auth else None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _parse(response):
    try:
        body = response.json() if response.content else {}
    except ValueError:
        body = None
    if isinstance(body, list):
        body = {"_items": body}
    if body is None:
        body = {} if response.status_code < 400 else {
            "status": "error", "code": f"HTTP_{response.status_code}",
            "error": f"The server replied HTTP {response.status_code}."}
    body["_http_status"] = response.status_code
    if str(response.headers.get("X-Idempotent-Replay", "")).lower() == "true":
        body["_replay"] = True
    return body


def _safe_request(method, path, *, json=None, params=None, auth=True, logout_on_401=True,
                  idempotency_key=None, timeout=10, base=None):
    """Send one request. Returns the parsed reply (see module doc) or None if unreachable.

    A 401 on an authenticated call means the token is no longer valid (logout, password
    change, lock): the login is cleared and the app reruns to the login screen.
    """
    url = f"{base or BASE_URL}{path}"
    kwargs = {"headers": _headers(json is not None, auth, idempotency_key), "timeout": timeout}
    if json is not None:
        kwargs["json"] = json
    if params is not None:
        kwargs["params"] = params
    try:
        response = requests.request(method, url, **kwargs)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return None
    except requests.exceptions.RequestException:
        return None

    reply = _parse(response)
    if response.status_code == 401 and auth and logout_on_401 and st.session_state.get("token"):
        cdss_logic.clear_auth_state(st.session_state)
        st.session_state["auth_notice"] = SESSION_EXPIRED_NOTICE
        st.rerun()
    return reply


def _keyed_post(scope, path, body, timeout=15):
    """POST that creates a record: one Idempotency-Key per save, reused on retry, released on success."""
    key = cdss_logic.idempotency_key(st.session_state, scope)
    reply = _safe_request("POST", path, json=body, idempotency_key=key, timeout=timeout)
    if cdss_logic.is_ok(reply):
        cdss_logic.release_idempotency_key(st.session_state, scope)
    return reply


def _staff_params(patient_id=None, **extra):
    """Query string for /patient/... reads: staff send patient_id, a patient sends nothing."""
    params = {k: v for k, v in extra.items() if v is not None}
    if patient_id is not None:
        params["patient_id"] = patient_id
    return params


# ==============================================================================
# AUTH
# ==============================================================================
def perform_backend_logout():
    """POST /auth/logout (every token of this account stops working)."""
    return _safe_request("POST", "/auth/logout", json={}, logout_on_401=False, timeout=5)


def change_user_password(current_password: str, new_password: str):
    """POST /auth/change-password. 401 here means a wrong current password, not an expired login."""
    return _safe_request("POST", "/auth/change-password",
                         json={"current_password": current_password, "new_password": new_password},
                         logout_on_401=False)


def request_password_reset(identifier: str):
    """POST /auth/forgot-password (no login needed)."""
    return _safe_request("POST", "/auth/forgot-password", json={"identifier": identifier}, auth=False)


def reset_password(identifier: str, otp: str, new_password: str):
    """POST /auth/reset-password (no login needed)."""
    return _safe_request("POST", "/auth/reset-password",
                         json={"identifier": identifier, "otp": otp, "new_password": new_password}, auth=False)


# ==============================================================================
# PATIENT RECORDS AND FHRS INPUTS
# ==============================================================================
def get_latest_patient_encounter(patient_id=None):
    return _safe_request("GET", "/patient/latest-encounter", params=_staff_params(patient_id), timeout=5)


def get_patient_encounters_list(patient_id=None):
    return _safe_request("GET", "/patient/encounters", params=_staff_params(patient_id), timeout=5)


def get_patient_family_history(patient_id=None):
    return _safe_request("GET", "/patient/family-history", params=_staff_params(patient_id), timeout=5)


def submit_patient_family_history(payload: dict):
    """POST /patient/family-history. Build the body with cdss_logic.build_family_history_payload."""
    return _safe_request("POST", "/patient/family-history", json=payload)


def verify_family_history(record_id):
    return _safe_request("POST", f"/patient/family-history/{record_id}/verify", json={})


def get_hazards(patient_id=None):
    return _safe_request("GET", "/patient/hazards", params=_staff_params(patient_id), timeout=5)


def add_hazard(disease_domain, hazard_code, patient_id=None):
    body = {"disease_domain": disease_domain, "hazard_code": hazard_code}
    if patient_id is not None:
        body["patient_id"] = patient_id
    return _safe_request("POST", "/patient/hazards", json=body)


def delete_hazard(hazard_id):
    return _safe_request("DELETE", f"/patient/hazards/{hazard_id}")


def set_biological_sex(patient_id, biological_sex):
    return _safe_request("POST", "/patient/biological-sex",
                         json={"patient_id": patient_id, "biological_sex": biological_sex})


def get_fhrs(disease, patient_id=None):
    return _safe_request("GET", "/patient/fhrs", params=_staff_params(patient_id, disease=disease), timeout=5)


# ==============================================================================
# CLINIC QUEUE
# ==============================================================================
def get_active_queue():
    """GET /patient/queue (a patient gets only their own ticket)."""
    return _safe_request("GET", "/patient/queue", timeout=5)


def submit_patient_checkin(payload: dict):
    return _safe_request("POST", "/patient/queue/checkin", json=payload)


def cancel_patient_checkin(patient_id):
    """DELETE /patient/queue/<patient_id> (kept as history, status CANCELLED)."""
    return _safe_request("DELETE", f"/patient/queue/{patient_id}")


def get_doctor_queue():
    """GET /doctor/queue: {status, queue: [...]}, today's WAITING tickets."""
    return _safe_request("GET", "/doctor/queue", timeout=5)


# ==============================================================================
# BIOMARKERS AND AI
# ==============================================================================
def save_biomarkers(modality, patient_id, values):
    """POST /biomarkers/<modality> with that disease table's column names."""
    return _keyed_post(f"biomarkers:{modality}:{patient_id}", f"/biomarkers/{modality}",
                       {"patient_id": patient_id, "values": values})


def get_latest_biomarkers(modality, patient_id=None):
    return _safe_request("GET", f"/biomarkers/{modality}/latest", params=_staff_params(patient_id), timeout=5)


def infer_cdss(patient_id, modality):
    """POST /predictions/infer. No biomarker_payload: the backend builds the input from stored data."""
    return _safe_request("POST", "/predictions/infer", json={"patient_id": patient_id, "modality": modality},
                         timeout=20)


def get_models_status():
    return _safe_request("GET", "/predictions/models/status", timeout=5)


def reload_models():
    return _safe_request("POST", "/predictions/models/reload", json={}, timeout=30)


# ==============================================================================
# DOCTOR WORKFLOW
# ==============================================================================
def get_doctor_patient(patient_id):
    return _safe_request("GET", f"/doctor/patient/{patient_id}", timeout=5)


def get_baseline(patient_id):
    """GET /doctor/patient/<id>/baseline. 404 {has_baseline: false} means 'start intake', not an error."""
    return _safe_request("GET", f"/doctor/patient/{patient_id}/baseline", timeout=5)


def save_consultation(patient_id, directives, notes=""):
    return _keyed_post(f"consultation:{patient_id}", "/doctor/consultation",
                       {"patient_id": patient_id, "directives": directives, "notes": notes})


def get_consultations(patient_id):
    return _safe_request("GET", f"/doctor/patient/{patient_id}/consultations", timeout=5)


def commit_encounter(patient_id, payload: dict):
    """POST /doctor/commit-encounter. Build the body with cdss_logic.build_commit_payload."""
    return _keyed_post(f"commit:{patient_id}", "/doctor/commit-encounter", payload, timeout=20)


def clear_idempotency_key(patient_id):
    """Start a fresh commit (e.g. after switching patient)."""
    cdss_logic.release_idempotency_key(st.session_state, f"commit:{patient_id}")


def verify_encounter(encounter_uid):
    return _safe_request("GET", f"/doctor/encounter/{encounter_uid}/verify", timeout=5)


# ==============================================================================
# ADMIN
# ==============================================================================
def get_directory():
    return _safe_request("GET", "/admin/directory", timeout=5)


def provision_doctor(payload: dict):
    """POST /admin/provision. Build the body with cdss_logic.build_provision_payload."""
    return _keyed_post("provision", "/admin/provision", payload)


def verify_doctor(doctor_id):
    return _safe_request("POST", f"/admin/doctors/{doctor_id}/verify", json={})


def unlock_user(user_id):
    return _safe_request("POST", f"/admin/users/{user_id}/unlock", json={})


def get_health():
    """GET /api/health/db (outside /api/v1): server and database status."""
    return _safe_request("GET", "/api/health/db", auth=False, base=API_BASE, timeout=5)
