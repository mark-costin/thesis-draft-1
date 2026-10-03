import os
import requests
import uuid
import streamlit as st

# ==========================================
# EXPLICIT API VERSION PINNING (D1)
# ==========================================
API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
API_VERSION = "v1"
BASE_URL = f"{API_BASE}/api/{API_VERSION}"

def _get_standard_headers(patient_id=None, require_idempotency=False):
    """Constructs headers, providing a dev fallback token and enforcing idempotency caching."""
    # Use active session token or provide a fallback for testing without full login flow
    token = st.session_state.get("token", "")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    if require_idempotency and patient_id:
        sess_token_key = f"encounter_sid_{patient_id}"
        if sess_token_key not in st.session_state:
            st.session_state[sess_token_key] = uuid.uuid4().hex[:8]
        sid = st.session_state[sess_token_key]
        
        cache_key = f"idem_key_{patient_id}_{sid}"
        if cache_key not in st.session_state:
            st.session_state[cache_key] = str(uuid.uuid4())
        headers["Idempotency-Key"] = st.session_state[cache_key]
        
    return headers

def clear_idempotency_key(patient_id: int):
    """Clears the session token and idempotency key on successful commit or encounter reset."""
    sess_token_key = f"encounter_sid_{patient_id}"
    sid = st.session_state.pop(sess_token_key, None)
    if sid:
        st.session_state.pop(f"idem_key_{patient_id}_{sid}", None)

def _safe_request(method, url, ignore_404=False, **kwargs):
    """
    Safely executes HTTP requests, catching errors and rendering UI alerts instead of crashing.
    If ignore_404=True, returns None cleanly without triggering an error alert.
    """
    try:
        response = requests.request(method, url, **kwargs)
        
        # 404 is an expected normal state when checking if a patient has an existing baseline
        if ignore_404 and response.status_code == 404:
            return None

        if response.status_code >= 400:
            try:
                return response.json()
            except:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        return response.json() if response.content else {}
    except requests.exceptions.HTTPError as e:
        try:
            error_data = response.json()
        except Exception:
            error_data = {"error": str(e), "code": "UNKNOWN_ERROR", "retryable": False}
        
        st.error(f"API Error ({response.status_code}): {error_data.get('error', 'Unknown failure')}")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Network Error: Could not connect to the backend server. Is it running on http://127.0.0.1:5000?")
        return None
    except requests.exceptions.Timeout:
        st.error("Network Error: The request timed out.")
        return None

def get_baseline(patient_id: int):
    """
    GET /api/v1/doctor/patient/<id>/baseline
    Queries the database for existing baseline. Returns None if 404 (initiates Phase 1).
    """
    url = f"{BASE_URL}/doctor/patient/{patient_id}/baseline"
    headers = _get_standard_headers()
    headers.pop("Content-Type", None)  # GET requests do not require a content type
    
    # Executes a single protected request; returns None cleanly on 404
    return _safe_request("GET", url, ignore_404=True, headers=headers, timeout=5)

def infer_cdss(payload: dict):
    """POST /api/v1/predictions/infer"""
    url = f"{BASE_URL}/predictions/infer"
    return _safe_request("POST", url, json=payload, headers=_get_standard_headers(), timeout=15)

def commit_encounter(patient_id: int, payload: dict):
    """POST /api/v1/doctor/commit-encounter"""
    url = f"{BASE_URL}/doctor/commit-encounter"
    headers = _get_standard_headers(patient_id=patient_id, require_idempotency=True)
    return _safe_request("POST", url, json=payload, headers=headers, timeout=20)

# ==============================================================================
# PATIENT PORTAL API METHODS
# ==============================================================================
def get_latest_patient_encounter(patient_id: int):
    """GET /api/v1/patient/latest-encounter?patient_id=<id>"""
    url = f"{BASE_URL}/patient/latest-encounter?patient_id={patient_id}"
    headers = _get_standard_headers()
    headers.pop("Content-Type", None)
    return _safe_request("GET", url, headers=headers, timeout=5)

def get_patient_encounters_list(patient_id: int):
    """GET /api/v1/patient/encounters?patient_id=<id>"""
    url = f"{BASE_URL}/patient/encounters?patient_id={patient_id}"
    headers = _get_standard_headers()
    headers.pop("Content-Type", None)
    return _safe_request("GET", url, headers=headers, timeout=5)

def get_patient_family_history(patient_id: int):
    """GET /api/v1/patient/family-history?patient_id=<id>"""
    url = f"{BASE_URL}/patient/family-history?patient_id={patient_id}"
    headers = _get_standard_headers()
    headers.pop("Content-Type", None)
    return _safe_request("GET", url, headers=headers, timeout=5)

def submit_patient_family_history(payload: dict):
    """POST /api/v1/patient/family-history"""
    url = f"{BASE_URL}/patient/family-history"
    return _safe_request("POST", url, json=payload, headers=_get_standard_headers(), timeout=10)

def get_active_queue():
    """GET /api/v1/patient/queue"""
    url = f"{BASE_URL}/patient/queue"
    headers = _get_standard_headers()
    headers.pop("Content-Type", None)
    return _safe_request("GET", url, headers=headers, timeout=5)

def submit_patient_checkin(payload: dict):
    """POST /api/v1/patient/queue/checkin"""
    url = f"{BASE_URL}/patient/queue/checkin"
    return _safe_request("POST", url, json=payload, headers=_get_standard_headers(), timeout=10)

def cancel_patient_checkin(patient_id: int):
    import requests
    import streamlit as st
    token = st.session_state.get("token", "")
    base_url = globals().get("BASE_URL", "http://127.0.0.1:5000")
    try:
        res = requests.delete(
            f"{base_url}/api/v1/patient/queue/{patient_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        return res.json() if res.status_code == 200 else {"status": "error"}
    except Exception:
        return {"status": "error"}

def change_user_password(current_password: str, new_password: str):
    """POST /api/v1/auth/change-password"""
    url = f"{BASE_URL}/auth/change-password"
    payload = {"current_password": current_password, "new_password": new_password}
    return _safe_request("POST", url, json=payload, headers=_get_standard_headers(), timeout=10)

def perform_backend_logout():
    """POST /api/v1/auth/logout"""
    url = f"{BASE_URL}/auth/logout"
    return _safe_request("POST", url, headers=_get_standard_headers(), timeout=5)
