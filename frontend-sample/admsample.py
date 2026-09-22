import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime

# ==============================================================================
# PAGE CONFIGURATION & STATE INITIALIZATION
# ==============================================================================
st.set_page_config(layout="wide")

user_avatar_url = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80"


# --- THEME & NIGHT LIGHT STATE ---
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "light"

if "night_light" not in st.session_state:
    st.session_state.night_light = False

if "night_light_warmth" not in st.session_state:
    st.session_state.night_light_warmth = 8 

# ==============================================================================
# UNIFIED DUAL-THEME ENGINE
# ==============================================================================
if st.session_state.theme_mode == "dark":
    theme_css = """
    /* App Canvas & Global Typography */
    .stApp { background-color: #091540 !important; color: #E5E5E5 !important; }
    h1, h2, h3, h4, h5, h6, p, span, label { color: #E5E5E5 !important; }

    /* Level 1: Primary Div Containers (Main sections, Forms, Directory Wrappers) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #232F72 !important;
        border: 1px solid #2F578A !important;
        border-radius: 14px !important;
        padding: 20px 24px !important;
        margin-bottom: 18px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: transparent !important;
    }

    /* Level 2: Elevated Mini Cards (Top Metrics, Lower Column Cards) */
    div[style*="background-color: #ffffff"], 
    div[style*="background-color: rgb(255, 255, 255)"],
    [data-testid="column"] div[data-testid="stVerticalBlockBorderWrapper"],
    .metric-card {
        background-color: #2F578A !important;
        border: 1px solid rgba(229, 229, 229, 0.25) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
    }

    /* Text & Metric Overrides for High Contrast */
    .stApp [style*="color: #1e293b"], .stApp [style*="color:#1e293b"],
    .stApp [style*="color: #111"], .stApp [style*="color:#111"],
    .stApp [style*="color: #111827"], .stApp [style*="color:#111827"],
    .stApp [style*="color: #334155"], .stApp [style*="color:#334155"],
    .stApp [style*="color: #0f172a"], .stApp [style*="color:#0f172a"] {
        color: #E5E5E5 !important;
    }
    .stApp [style*="color: #64748b"], .stApp [style*="color:#64748b"],
    .stApp [style*="color: #475569"], .stApp [style*="color:#475569"],
    .stApp [style*="color: #4b5563"], .stApp [style*="color:#4b5563"] {
        color: #B0B8C4 !important;
    }

    /* Form Input Fields */
    [data-baseweb="base-input"], 
    [data-baseweb="input"], 
    [data-baseweb="select"] > div {
        background-color: #091540 !important;
        border: 1px solid #2F578A !important;
        border-radius: 8px !important;
    }
    [data-baseweb="base-input"] input, 
    [data-baseweb="input"] input {
        color: #E5E5E5 !important;
        -webkit-text-fill-color: #E5E5E5 !important;
    }

    /* Popovers & Secondary Action Buttons */
    div[data-testid="stPopoverBody"] {
        background-color: #232F72 !important;
        border: 1px solid #2F578A !important;
    }
    .stApp button[data-testid="baseButton-secondary"] {
        background-color: #232F72 !important;
        border: 1px solid #2F578A !important;
        color: #E5E5E5 !important;
    }
    .stApp button[data-testid="baseButton-secondary"] p { color: #E5E5E5 !important; }
    [data-baseweb="tab-list"] { border-bottom: 2px solid #2F578A !important; }
    """
else:
    theme_css = """
    /* App Canvas & Typography */
    .stApp { background-color: #f1f5f9 !important; color: #0f172a !important; }
    h1, h2, h3, h4, h5, h6, p, span, label { color: #0f172a !important; }

    /* Light Containers & Cards */
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[style*="background-color: #ffffff"], 
    div[style*="background-color: rgb(255, 255, 255)"],
    .metric-card {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 20px 24px !important;
        margin-bottom: 18px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: transparent !important;
    }

    /* Light Inputs */
    [data-baseweb="base-input"], 
    [data-baseweb="input"], 
    [data-baseweb="select"] > div {
        background-color: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    [data-baseweb="base-input"] input, 
    [data-baseweb="input"] input {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    /* Popovers & Secondary Buttons */
    div[data-testid="stPopoverBody"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
    }
    .stApp button[data-testid="baseButton-secondary"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #1e293b !important;
    }
    .stApp button[data-testid="baseButton-secondary"] p { color: #1e293b !important; }
    [data-baseweb="tab-list"] { border-bottom: 2px solid #e2e8f0 !important; }
    """
night_light_html = ""
if st.session_state.night_light:
    opacity = st.session_state.night_light_warmth / 100
    night_light_html = f'<div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(255, 145, 0, {opacity}); pointer-events: none; z-index: 999999;"></div>'


# ==============================================================================
# MASTER, CSS THEME & NIGHT LIGHT INJECTION
# ==============================================================================

st.markdown(f"""
    <style>
    {theme_css}

    [data-testid*="stInputInstructions"] {{ display: none !important; }}

    /* Layout Spacing: 10/90/10 Ratio */
    .block-container {{
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-top: 1.5rem !important;
        max-width: 96% !important;
    }}

    /* TAB BAR */
    [data-baseweb="tab-list"] {{
        display: flex !important;
        width: 100% !important;
        margin-top: 10px !important;
        margin-bottom: 24px !important;
        gap: 14px !important;
    }}
    button[data-baseweb="tab"], [data-testid="stTab"] {{
        flex: 1 1 0 !important;
        height: 62px !important;
        padding: 14px 20px !important;
        justify-content: center !important;
        background-color: transparent !important;
    }}
    button[data-baseweb="tab"]:hover {{
        background-color: rgba(0, 121, 121, 0.08) !important;
    }}
    button[data-baseweb="tab"] p, 
    button[data-baseweb="tab"] span, 
    [data-testid="stTab"] * {{
        font-size: 1.45rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px !important;
    }}
    [aria-selected="true"] * {{ color: #007979 !important; }}

    /* TAB HIGHLIGHT */
    [data-baseweb="tab-highlight"] {{
        background-color: #007979 !important;
        height: 4px !important;
        border-radius: 3px !important;
    }}

    /* PRIMARY BUTTON */
    button[data-testid="baseButton-primary"] {{
        background-color: #007979 !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 700 !important;
        height: 48px !important;
        border-radius: 8px !important;
    }}
    button[data-testid="baseButton-primary"]:hover {{
        background-color: #005f5f !important;
        color: #ffffff !important;
    }}

    div[data-testid="stSelectbox"] input {{ caret-color: transparent !important; cursor: pointer !important; }}

    div[data-testid="stPopover"] > button [data-testid="stIconEmoji"] {{
        display: inline-block !important; width: 38px !important; height: 38px !important; min-width: 38px !important;
        border-radius: 50% !important; border: 2px solid #007979 !important;
        background-image: url('{user_avatar_url}') !important; background-size: cover !important;
        background-position: center !important; background-repeat: no-repeat !important;
        font-size: 0 !important; color: transparent !important; margin-right: 12px !important; margin-bottom: 0 !important;
    }}
    div[data-testid="stPopover"] > button p {{ margin: 0 !important; text-align: left !important; line-height: 1.2 !important; font-size: 0.85rem !important; }}
    div[data-testid="stPopover"] > button p strong {{ font-size: 1rem !important; font-weight: 800 !important; }}
    </style>
    {night_light_html}
""", unsafe_allow_html=True)


# ==============================================================================
# CALLBACKS, HELPERS & REUSABLE COMPONENTS
# ==============================================================================
def clean_alpha_input(key: str):
    raw_val = st.session_state.get(key, "")
    st.session_state[f"{key}_invalid"] = bool(re.search(r"[^A-Za-z\s\-]", raw_val))
    st.session_state[key] = re.sub(r"[^A-Za-z\s\-]", "", raw_val)

def format_phone_number(key: str):
    raw_val = st.session_state.get(key, "")
    st.session_state[f"{key}_invalid"] = bool(re.search(r"[^0-9\-]", raw_val))
    digits = "".join(filter(str.isdigit, raw_val))[:11]
    formatted = digits[:4] + ("-" + digits[4:7] if len(digits) > 4 else "") + ("-" + digits[7:11] if len(digits) > 7 else "")
    st.session_state[key] = formatted

def clean_prc_license(key: str):
    raw_val = st.session_state.get(key, "")
    st.session_state[f"{key}_invalid"] = bool(re.search(r"[^0-9]", raw_val))
    st.session_state[key] = "".join(filter(str.isdigit, raw_val))[:7]

def is_valid_phone_format(text: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{3}-\d{4}$", text.strip()))

def is_valid_gmail(text: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", text.strip()))

def is_valid_admin_email(text: str) -> bool:
    """Accepts any valid hospital or institutional email."""
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", text.strip()))

# --- REUSABLE CLINICIAN COMPONENT ---
def render_clinician_governance_panel(target_doc, current_admin_email):
    """Reusable UI component for clinician account governance actions."""
    is_selected = target_doc is not None

    if is_selected:
        st.markdown(f"Selected Clinician: **{target_doc['name']}** (`{target_doc['license_number']}`)")
    else:
        st.caption("👈 *Click on a row in the table above to select a clinician for action.*")

    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        failed_count = target_doc['failed_attempts'] if is_selected else 0
        st.markdown(f"**Failed Logins:** `{failed_count}/5`")
        
        is_locked = target_doc.get("is_locked", False) if is_selected else False
        unlock_disabled = not (is_selected and is_locked)
        
        if st.button("🔓 Clear Lockout", use_container_width=True, disabled=unlock_disabled, key=f"btn_doc_unlock_{target_doc['doctor_id'] if is_selected else 'none'}"):
            target_doc["is_locked"] = False
            target_doc["failed_attempts"] = 0
            st.session_state.doctor_audit_logs.insert(0, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "target_doctor": target_doc["name"],
                "event_type": "ACCOUNT_UNLOCKED",
                "actor": f"Admin ({current_admin_email})",
                "ip_address": "127.0.0.1",
                "details": "Administrator manually cleared login threshold."
            })
            st.success(f"Unlocked account for {target_doc['name']}.")
            st.rerun()

    with action_col2:
        st.markdown("**Credential Reset:**")
        if st.button("🔑 Dispatch Reset OTP", use_container_width=True, disabled=not is_selected, key=f"btn_doc_otp_{target_doc['doctor_id'] if is_selected else 'none'}"):
            st.session_state.doctor_audit_logs.insert(0, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "target_doctor": target_doc["name"],
                "event_type": "PASSWORD_RESET_DISPATCHED",
                "actor": f"Admin ({current_admin_email})",
                "ip_address": "127.0.0.1",
                "details": f"Temporary OTP sent to {target_doc['email']}."
            })
            st.success(f"One-time reset dispatched to {target_doc['email']}.")

    with action_col3:
        token_ver = target_doc['token_version'] if is_selected else 0
        st.markdown(f"**Session Version:** `v{token_ver}`")
        if st.button("🛑 Revoke Active Sessions", use_container_width=True, disabled=not is_selected, key=f"btn_doc_revoke_{target_doc['doctor_id'] if is_selected else 'none'}"):
            target_doc["token_version"] += 1
            st.session_state.doctor_audit_logs.insert(0, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "target_doctor": target_doc["name"],
                "event_type": "SESSION_REVOKED",
                "actor": f"Admin ({current_admin_email})",
                "ip_address": "127.0.0.1",
                "details": f"Token version incremented to {target_doc['token_version']}."
            })
            st.warning(f"All active bearer tokens invalidated for {target_doc['name']}.")
            st.rerun()

# --- REUSABLE PATIENT COMPONENT ---
def render_patient_governance_panel(target_patient, current_admin_email):
    """Reusable UI component for patient account governance actions."""
    is_selected = target_patient is not None

    if is_selected:
        st.markdown(f"Selected Patient: **{target_patient['name']}** (`{target_patient['email']}`)")
    else:
        st.caption("👈 *Click on a row in the table above to select a patient for action.*")

    act_col1, act_col2, act_col3 = st.columns(3)
    
    with act_col1:
        failed_count = target_patient['failed_attempts'] if is_selected else 0
        st.markdown(f"**Lockout Control:** `{failed_count}/5` failed attempts")
        if st.button("🔓 Reset Failed Attempts", use_container_width=True, disabled=not is_selected or failed_count == 0, key=f"btn_pat_reset_{target_patient['patient_id'] if is_selected else 'none'}"):
            target_patient["failed_attempts"] = 0
            target_patient["is_locked"] = False
            st.session_state.patient_audit_logs.insert(0, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "target_patient": target_patient["name"],
                "event_type": "LOCKOUT_CLEARED",
                "actor": f"Admin ({current_admin_email})",
                "ip_address": "127.0.0.1",
                "details": "Administrator manually cleared failed login counter."
            })
            st.success(f"Counter reset for {target_patient['name']}.")
            st.rerun()
    
    with act_col2:
        st.markdown("**Credential Dispatch:**")
        if st.button("🔑 Dispatch Secure Reset Link", use_container_width=True, disabled=not is_selected, key=f"btn_pat_link_{target_patient['patient_id'] if is_selected else 'none'}"):
            st.session_state.patient_audit_logs.insert(0, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "target_patient": target_patient["name"],
                "event_type": "PASSWORD_RESET_DISPATCHED",
                "actor": f"Admin ({current_admin_email})",
                "ip_address": "127.0.0.1",
                "details": f"Temporary reset token sent to {target_patient['email']}."
            })
            st.success(f"Reset link sent to {target_patient['email']}.")

    with act_col3:
        st.markdown("**Access Freeze:**")
        is_active = target_patient["is_active"] if is_selected else True
        if is_active:
            if st.button("🛑 Suspend Account", use_container_width=True, disabled=not is_selected, key=f"btn_pat_suspend_{target_patient['patient_id'] if is_selected else 'none'}"):
                target_patient["is_active"] = False
                st.session_state.patient_audit_logs.insert(0, {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "target_patient": target_patient["name"],
                    "event_type": "ACCOUNT_SUSPENDED",
                    "actor": f"Admin ({current_admin_email})",
                    "ip_address": "127.0.0.1",
                    "details": "Account deactivated by administrator."
                })
                st.warning(f"Account suspended for {target_patient['name']}.")
                st.rerun()
        else:
            if st.button("✅ Restore Access", use_container_width=True, disabled=not is_selected, key=f"btn_pat_restore_{target_patient['patient_id'] if is_selected else 'none'}"):
                target_patient["is_active"] = True
                st.session_state.patient_audit_logs.insert(0, {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "target_patient": target_patient["name"],
                    "event_type": "ACCOUNT_RESTORED",
                    "actor": f"Admin ({current_admin_email})",
                    "ip_address": "127.0.0.1",
                    "details": "Account reactivated by administrator."
                })
                st.success(f"Access restored for {target_patient['name']}.")
                st.rerun()

# --- REUSABLE ADMIN COMPONENT ---
def render_admin_governance_panel(target_e):
    """Reusable UI component for staff & admin account governance actions."""
    is_selected = target_e is not None

    if is_selected:
        st.markdown(f"Selected Staff: **{target_e['name']}** (`{target_e['emp_id']}`)")
    else:
        st.caption("👈 *Click on a row in the table above to select an employee for action.*")

    e_col1, e_col2 = st.columns(2)
    with e_col1:
        if st.button("📧 Dispatch Password Reset OTP", use_container_width=True, disabled=not is_selected, key=f"emp_otp_{target_e['emp_id'] if is_selected else 'none'}"):
            st.success(f"Temporary password reset link sent to {target_e['email']}.")
            
    with e_col2:
        status = target_e["status"] if is_selected else "Active"
        toggle_state = "Suspend Account Access" if status == "Active" else "Restore Account Access"
        btn_type = "secondary" if status == "Active" else "primary"
        
        if st.button(f"🛑 {toggle_state}", use_container_width=True, type=btn_type, disabled=not is_selected, key=f"emp_toggle_{target_e['emp_id'] if is_selected else 'none'}"):
            target_e["status"] = "Suspended" if status == "Active" else "Active"
            st.rerun()

# ==============================================================================
# GLOBALS & DIRECTORIES
# ==============================================================================
SPECIALIZATION_OPTIONS = ["General Physician", "Internal Medicine", "Cardiology", "Pulmonology", "Psychiatry"]
SUFFIX_OPTIONS = ["None", "MD", "PhD", "DO", "MD, PhD", "Jr.", "Sr.", "III"]
RELATION_OPTIONS = ["Mother", "Father", "Spouse", "Son", "Daughter", "Brother", "Sister", "Other"]

for key in ["doc_first_name", "doc_middle_name", "doc_last_name", "doc_address", "doc_affiliation", "doc_prc", "doc_email", "doc_contact", "em_name", "em_contact"]:
    if key not in st.session_state: st.session_state[key] = ""

if "form_success" not in st.session_state: st.session_state.form_success = None

if "doctor_directory" not in st.session_state:
    st.session_state.doctor_directory = [
        {"doctor_id": 1, "name": "Smith, John M.", "license_number": "PRC 1234567", "specialization": "General Physician", "email": "doc.smith@gmail.com", "contact_number": "0917-123-4567", "hospital_affiliation": "Lucerna Central", "is_verified": True, "failed_attempts": 0, "is_locked": False, "mfa_enrolled": True, "token_version": 1},
        {"doctor_id": 2, "name": "Velasco, Maria A.", "license_number": "PRC 8839210", "specialization": "Cardiology", "email": "m.velasco@gmail.com", "contact_number": "0920-987-6543", "hospital_affiliation": "Heart Center", "is_verified": False, "failed_attempts": 4, "is_locked": True, "mfa_enrolled": False, "token_version": 3}
    ]

if "doctor_audit_logs" not in st.session_state:
    st.session_state.doctor_audit_logs = [
        {"timestamp": "2026-09-10 09:12:15", "target_doctor": "Smith, John M.", "event_type": "LOGIN_SUCCESS", "actor": "Dr. Smith (doc_smith)", "ip_address": "192.168.1.45", "details": "MFA Challenge Passed (Authenticator App)"},
        {"timestamp": "2026-09-10 08:30:00", "target_doctor": "Velasco, Maria A.", "event_type": "ACCOUNT_LOCKED", "actor": "SYSTEM_GUARD", "ip_address": "112.198.72.10", "details": "Threshold exceeded: 4 consecutive invalid password submissions."},
        {"timestamp": "2026-09-09 14:22:11", "target_doctor": "Smith, John M.", "event_type": "VERIFICATION_APPROVED", "actor": "Admin (admin.system)", "ip_address": "10.0.4.12", "details": "PRC credential verified against national registry."}
    ]

if "active_admin_id" not in st.session_state:
    st.session_state.active_admin_id = "EMP-001"

if "employee_directory" not in st.session_state:
    st.session_state.employee_directory = [
        {"emp_id": "EMP-001", "name": "First Name", "role": "System Admin", "email": "admin.system@lucernamedica.com", "status": "Active"},
        {"emp_id": "EMP-002", "name": "Connor, Sarah", "role": "IT Support", "email": "s.connor@lucernamedica.com", "status": "Active"},
        {"emp_id": "EMP-003", "name": "Wright, Marcus", "role": "Compliance Auditor", "email": "m.wright@lucernamedica.com", "status": "Suspended"}
    ]

if "patient_directory" not in st.session_state:
    st.session_state.patient_directory = [
        {"patient_id": 1, "name": "Mason, Justin L.", "email": "j.mason@gmail.com", "contact_number": "0917-555-0198", "dob": "1992-08-14", "registered_at": "2026-09-09 08:15:22", "pending_method": "None", "dispatch_count": 1, "is_verified": True, "is_active": True, "hipaa_consent": True, "hipaa_consent_at": "2026-09-09 08:20:11", "failed_attempts": 0, "is_locked": False},
        {"patient_id": 2, "name": "Reyes, Sofia M.", "email": "sofia.reyes99@gmail.com", "contact_number": "0920-111-4432", "dob": "1999-11-02", "registered_at": "2026-09-10 10:05:00", "pending_method": "Pending Phone OTP", "dispatch_count": 2, "is_verified": False, "is_active": False, "hipaa_consent": False, "hipaa_consent_at": None, "failed_attempts": 0, "is_locked": False},
        {"patient_id": 3, "name": "Bautista, Carlos T.", "email": "cbautista.tech@gmail.com", "contact_number": "0918-999-8877", "dob": "1985-03-22", "registered_at": "2026-09-01 14:10:00", "pending_method": "None", "dispatch_count": 1, "is_verified": True, "is_active": False, "hipaa_consent": True, "hipaa_consent_at": "2026-09-01 14:15:00", "failed_attempts": 5, "is_locked": True}
    ]

if "patient_audit_logs" not in st.session_state:
    st.session_state.patient_audit_logs = [
        {"timestamp": "2026-09-09 08:20:11", "target_patient": "Mason, Justin L.", "event_type": "HIPAA_CONSENT_ACCEPTED", "actor": "System Registration", "ip_address": "112.201.44.9", "details": "Terms and Data Privacy Act acknowledged."},
        {"timestamp": "2026-09-10 10:15:00", "target_patient": "Reyes, Sofia M.", "event_type": "OTP_DISPATCHED", "actor": "Twilio Gateway", "ip_address": "System", "details": "SMS OTP re-sent (Attempt 2)."},
        {"timestamp": "2026-09-10 11:30:22", "target_patient": "Bautista, Carlos T.", "event_type": "ACCOUNT_SUSPENDED", "actor": "System Guard", "ip_address": "System", "details": "Suspended due to 5 consecutive failed logins."}
    ]



# Resolve active admin object dynamically
active_admin = next((e for e in st.session_state.employee_directory if e["emp_id"] == st.session_state.active_admin_id), st.session_state.employee_directory[0])
user_name = active_admin["name"]
user_role = active_admin["role"]
user_email = active_admin["email"]

# Helper callback for the sandbox
def _sync_sandbox_admin():
    selected_label = st.session_state.sandbox_admin_selector
    # Re-map the label back to the exact EMP ID
    emp_options_map_local = {f"{e['name']} ({e['role']})": e['emp_id'] for e in st.session_state.employee_directory}
    st.session_state.active_admin_id = emp_options_map_local.get(selected_label)

# ==============================================================================
# SIDEBAR EVALUATOR SANDBOX (THESIS DEMO MODE)
# ==============================================================================
with st.sidebar:
    with st.expander("🛠️ Evaluator Sandbox (Demo Mode)", expanded=False):
        st.caption("Instantly switch active administrative roles to demonstrate RBAC (Role-Based Access Control) and system logging during thesis evaluation.")
        
        # Create mapping of "Name (Role)" -> "ID"
        emp_options_map = {f"{e['name']} ({e['role']})": e['emp_id'] for e in st.session_state.employee_directory}
        current_selection_label = next((k for k, v in emp_options_map.items() if v == st.session_state.active_admin_id), list(emp_options_map.keys())[0])
        
        st.selectbox(
            "Switch Active Administrator",
            options=list(emp_options_map.keys()),
            index=list(emp_options_map.keys()).index(current_selection_label),
            key="sandbox_admin_selector",
            on_change=_sync_sandbox_admin
        )
count_admins = 1
count_patients = len(st.session_state.patient_directory)
count_doctors = len(st.session_state.doctor_directory)
count_verified_docs = sum(1 for d in st.session_state.doctor_directory if d.get("is_verified", False))

_, col_main, _ = st.columns([5, 90, 5], gap="small")

with col_main:
    # --- ADMIN HEADER (NO BORDER) ---
    with st.container(border=False):
        h_col1, h_col2 = st.columns([5.5, 4.5], vertical_alignment="center")
        
        with h_col1:
            st.markdown(f"""
            <div style="padding: 4px 0px;">
                <h3 style="margin: 0; font-size: 1.85rem; font-weight: 800;">{user_name} <span style="font-size: 1.1rem; font-weight: 600;">&nbsp;|&nbsp; {user_role}</span></h3>
                <div style="font-size: 0.95rem; font-weight: 600; margin-top: 4px;">✔ Lucerna Medica Administration • {user_email}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with h_col2:
            badge_col, btn1, btn2, btn3 = st.columns([2.5, 1, 1, 2.5])
            with badge_col:
                st.markdown("""<div style="background: #0ea5e920; color: #0ea5e9; padding: 8px 0px; border-radius: 20px; font-weight: 700; font-size: 0.85rem; text-align: center; margin-top: 5px;">🛡️ Superuser Access</div>""", unsafe_allow_html=True)
            with btn1:
                st.button("☰", use_container_width=True)
            with btn2:
                with st.popover("🔔", use_container_width=True):
                    st.markdown("##### Notifications")
                    st.caption("No new alerts at this time.")
            with btn3:
                with st.popover("⚙️ Settings", use_container_width=True):
                    st.markdown("<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 5px;'>Theme</div>", unsafe_allow_html=True)
                    t_col1, t_col2 = st.columns(2)
                    dark_type = "primary" if st.session_state.theme_mode == "dark" else "secondary"
                    light_type = "primary" if st.session_state.theme_mode == "light" else "secondary"
                    if t_col1.button("DARK", type=dark_type, use_container_width=True):
                        st.session_state.theme_mode = "dark"
                        st.rerun()
                    if t_col2.button("LIGHT", type=light_type, use_container_width=True):
                        st.session_state.theme_mode = "light"
                        st.rerun()
                    
                    st.markdown("<div style='font-size: 0.95rem; font-weight: 600; margin-top: 10px; margin-bottom: 5px;'>Night light</div>", unsafe_allow_html=True)
                    nl_col1, nl_col2 = st.columns(2)
                    on_type = "primary" if st.session_state.night_light else "secondary"
                    off_type = "secondary" if st.session_state.night_light else "primary"
                    if nl_col1.button("ON", type=on_type, use_container_width=True, key="nl_on"):
                        st.session_state.night_light = True
                        st.rerun()
                    if nl_col2.button("OFF", type=off_type, use_container_width=True, key="nl_off"):
                        st.session_state.night_light = False
                        st.rerun()
                    if st.session_state.night_light:
                        st.session_state.night_light_warmth = st.slider("Warmth Intensity", 5, 25, st.session_state.night_light_warmth)
                    st.divider()
                    st.markdown(f"<div style='text-align: center; color: #007979; font-size: 0.85rem; margin-bottom: 10px;'>{user_email}</div>", unsafe_allow_html=True)
                    if st.button("⏻ Log Out", type="primary", use_container_width=True):
                        st.session_state.authenticated = False
                        st.rerun()

    tab_Overview, tab_form, tab_patient, tab_Admin = st.tabs(["Overview", "Doctor Management", "Patient Management", "Admin accounts"])

    # --------------------------------------------------------------------------
    # TAB 1: METRIC DASHBOARD
    # --------------------------------------------------------------------------
    with tab_Overview:
        st.write("")
        docs = st.session_state.doctor_directory
        pats = st.session_state.patient_directory

        c_admin = 1
        c_doc = len(docs)
        c_pat = len(pats)
        total_accounts = c_admin + c_doc + c_pat

        pct_doc = (c_doc / total_accounts) * 100 if total_accounts else 0
        pct_pat = (c_pat / total_accounts) * 100 if total_accounts else 0
        pct_adm = (c_admin / total_accounts) * 100 if total_accounts else 0

        doc_ver = sum(1 for d in docs if d.get("is_verified", False))
        pat_hipaa = sum(1 for p in pats if p.get("hipaa_consent", False))
        pat_hipaa_pct = int((pat_hipaa / c_pat) * 100) if c_pat > 0 else 0

        pending_ver = sum(1 for p in pats if not p.get("is_verified", False))
        locked_acc = sum(1 for d in docs if d.get("is_locked", False)) + sum(1 for p in pats if p.get("is_locked", False))
        active_sessions = total_accounts - locked_acc
        
        doc_mfa = sum(1 for d in docs if d.get("mfa_enrolled", False))
        mfa_pct = int((doc_mfa / c_doc) * 100) if c_doc > 0 else 0

        with st.container(border=True):
            st.markdown("""
            <div style="margin-bottom: 22px;">
                <h3 style="margin: 0; font-size: 1.45rem; font-weight: 700; letter-spacing: -0.3px;">System Telemetry & Identity Metrics</h3>
                <p style="margin: 5px 0 16px 0; font-size: 0.95rem;">Live platform oversight, role distribution, and compliance monitoring across Lucerna Medica.</p>
                <div style="height: 1px; width: 100%; background-color: rgba(148, 163, 184, 0.2);"></div>
            </div>
            """, unsafe_allow_html=True)

            hero_col, grid_col = st.columns([1.3, 2], gap="medium")
            with hero_col:
                st.markdown(f"""<div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 22px 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.02); height: 295px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 0.85rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase;">Master Directory</span>
            <span style="background: #e6f4f1; color: #007979; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 20px;">LIVE REGISTRY</span>
            </div>
            <div style="font-size: 4.8rem; font-weight: 800; line-height: 1; letter-spacing: -1.5px; margin: 4px 0;">{total_accounts}</div>
            <div style="font-size: 1.1rem; font-weight: 600;">Total Provisioned Identities</div>
            </div>
            <div>
            <div style="display: flex; height: 10px; border-radius: 6px; overflow: hidden; background: #e2e8f0; margin-bottom: 10px;">
            <div style="width: {pct_doc:.1f}%; background-color: #007979;" title="Doctors: {c_doc}"></div>
            <div style="width: {pct_pat:.1f}%; background-color: #0284c7;" title="Patients: {c_pat}"></div>
            <div style="width: {pct_adm:.1f}%; background-color: #64748b;" title="Admins: {c_admin}"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600;">
            <span style="display: flex; align-items: center; gap: 5px;"><span style="height: 8px; width: 8px; border-radius: 50%; background: #007979;"></span> {c_doc} Clinicians</span>
            <span style="display: flex; align-items: center; gap: 5px;"><span style="height: 8px; width: 8px; border-radius: 50%; background: #0284c7;"></span> {c_pat} Patients</span>
            <span style="display: flex; align-items: center; gap: 5px;"><span style="height: 8px; width: 8px; border-radius: 50%; background: #64748b;"></span> {c_admin} Admin</span>
            </div>
            </div>
            </div>""", unsafe_allow_html=True)

            with grid_col:
                sub_r1_c1, sub_r1_c2 = st.columns(2, gap="medium")
                with sub_r1_c1:
                    st.markdown(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="font-size: 0.95rem; font-weight: 600;">Doctors</div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">{c_doc}</div>
                        <div style="font-size: 0.85rem; font-weight: 600; color: #007979;">🟢 {doc_ver}/{c_doc} Verified PRC Licenses</div>
                    </div>
                    """, unsafe_allow_html=True)
                with sub_r1_c2:
                    hipaa_badge_color = "#10b981" if pat_hipaa_pct >= 80 else "#f59e0b"
                    st.markdown(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="font-size: 0.95rem; font-weight: 600;">Patients</div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">{c_pat}</div>
                        <div style="font-size: 0.85rem; font-weight: 600; color: {hipaa_badge_color};">📝 {pat_hipaa_pct}% Consented ({pat_hipaa}/{c_pat})</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

                sub_r2_c1, sub_r2_c2 = st.columns(2, gap="medium")
                with sub_r2_c1:
                    st.markdown(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="font-size: 0.95rem; font-weight: 600;">System Admins</div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">{c_admin}</div>
                        <div style="font-size: 0.85rem; font-weight: 600; color: #0284c7;">🛡️ Full Audit Privileges</div>
                    </div>
                    """, unsafe_allow_html=True)
                with sub_r2_c2:
                    st.markdown(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="font-size: 0.95rem; font-weight: 600;">Active Sessions</div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">{active_sessions}</div>
                        <div style="font-size: 0.85rem; font-weight: 600; color: #10b981;">⚡ Valid Token Versions</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

            gov_c1, gov_c2, gov_c3, gov_c4 = st.columns(4, gap="medium")
            with gov_c1:
                pend_color = "#f59e0b" if pending_ver > 0 else "#10b981"
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="font-size: 0.88rem; font-weight: 600;">Pending Queue</div>
                    <div style="font-size: 2rem; font-weight: 800; line-height: 1;">{pending_ver}</div>
                    <div style="font-size: 0.8rem; font-weight: 600; color: {pend_color};">⏳ Awaiting OTP/Verification</div>
                </div>
                """, unsafe_allow_html=True)

            with gov_c2:
                lock_color = "#ef4444" if locked_acc > 0 else "#10b981"
                lock_text = f"⚠️ {locked_acc} Account Locked" if locked_acc > 0 else "✔ 0 Brute-Force Flags"
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="font-size: 0.88rem; font-weight: 600;">Account Lockouts</div>
                    <div style="font-size: 2rem; font-weight: 800; line-height: 1;">{locked_acc}</div>
                    <div style="font-size: 0.8rem; font-weight: 600; color: {lock_color};">{lock_text}</div>
                </div>
                """, unsafe_allow_html=True)

            with gov_c3:
                mfa_color = "#10b981" if mfa_pct == 100 else "#f59e0b"
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="font-size: 0.88rem; font-weight: 600;">MFA Adoption</div>
                    <div style="font-size: 2rem; font-weight: 800; line-height: 1;">{mfa_pct}%</div>
                    <div style="font-size: 0.8rem; font-weight: 600; color: {mfa_color};">🔐 Clinician 2FA Rate</div>
                </div>
                """, unsafe_allow_html=True)

            with gov_c4:
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="font-size: 0.88rem; font-weight: 600;">Compliance Index</div>
                    <div style="font-size: 2rem; font-weight: 800; line-height: 1;">100%</div>
                    <div style="font-size: 0.8rem; font-weight: 600; color: #10b981;">🛡️ HIPAA/DPA Compliant</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)
            
        with st.container(border=True):
            st.markdown("##### **INTAKE ACTIVITY OVER TIME**")
            st.caption("Activity tracking for Patients, Doctors, and Admin's accounts")
            chart_data = pd.DataFrame({"Patients": [0, 0, 20, 0, 0, 0, 0], "Doctors": [10, 0, 200, 0, 300, 30, 0], "Admins": [10, 0, 0, 300, 0, 0, 0]}, index=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
            st.line_chart(chart_data, height=350, use_container_width=True)

        current_date = datetime.now().strftime("%m/%d/%Y")
        st.markdown(f"<div style='text-align: right; font-size: 0.9rem; margin-bottom: 8px;'>Last Updated: {current_date}</div>", unsafe_allow_html=True)
        pool_col, cluster_col = st.columns([1, 1.5], gap="large")

        with pool_col:
            with st.container(border=True):
                st.markdown("#### Connection Pool Utilization")
                active_conn, max_conn = 0, 10
                utilization_pct = int((active_conn / max_conn) * 100)
                if active_conn <= 6: 
                    load_level, load_color = "Low", "#10b981"
                elif active_conn < 9: 
                    load_level, load_color = "Medium", "#f59e0b"
                else: 
                    load_level, load_color = "High", "#e10123"

                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=active_conn,
                    number={'suffix': f" / {max_conn}", 'font': {'size': 36}},
                    title={'text': f"<b>Active Connections</b><br><span style='font-size:14px;'>Utilization: {utilization_pct}%</span> • <span style='font-size:14px; font-weight:bold; color:{load_color};'>{load_level} Load</span>", 'font': {'size': 18}},
                    gauge={'axis': {'range': [0, max_conn], 'tickmode': 'linear', 'tick0': 0, 'dtick': 2, 'tickwidth': 1.5, 'ticks': "inside", 'tickfont': {'size': 13}}, 'bar': {'color': "#007979"}, 'borderwidth': 0, 'steps': [{'range': [0, 6], 'color': 'rgba(16, 185, 129, 0.2)'}, {'range': [6, 8], 'color': 'rgba(245, 158, 11, 0.2)'}, {'range': [8, 10], 'color': 'rgba(239, 68, 68, 0.2)'}], 'threshold': {'line': {'color': "#b91c1c", 'width': 3}, 'thickness': 0.8, 'value': 9}}
                ))
                fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=15), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with cluster_col:
            with st.container(border=True):
                st.markdown("#### Cluster Monitor")
                def evaluate_node_status(is_connected: bool, is_timeout: bool, active_sockets: int) -> str:
                    if is_timeout: return "🔴 Error: Timeout"
                    if not is_connected: return "🔴 Server Down"
                    if active_sockets == 0: return "🟡 Idle"
                    return "🟢 Healthy"

                raw_nodes_data = [
                    {"pid": "1XXX.XX.X.X1", "sockets": 2, "connected": True,  "timeout": False},
                    {"pid": "1XXX.XX.X.X2", "sockets": 0, "connected": True,  "timeout": False},
                    {"pid": "1XXX.XX.X.X3", "sockets": 0, "connected": False, "timeout": True},
                    {"pid": "1XXX.XX.X.X4", "sockets": 0, "connected": False, "timeout": False}
                ]
                processed_records = [{"PID": node["pid"], "Active Sockets": node["sockets"], "Status": evaluate_node_status(node["connected"], node["timeout"], node["sockets"])} for node in raw_nodes_data]
                st.dataframe(pd.DataFrame(processed_records), use_container_width=True, hide_index=True, height=180)
                st.markdown("""
                <div style="display: flex; justify-content: center; gap: 12px; margin-top: 14px;">
                    <div style="display: flex; align-items: center; gap: 8px; padding: 6px 16px; border: 1px solid #334155; border-radius: 20px; font-size: 0.85rem; font-weight: 600;"><span style="height: 10px; width: 10px; border-radius: 50%; background-color: #28a745; display: inline-block;"></span>Active</div>
                    <div style="display: flex; align-items: center; gap: 8px; padding: 6px 16px; border: 1px solid #334155; border-radius: 20px; font-size: 0.85rem; font-weight: 600;"><span style="height: 10px; width: 10px; border-radius: 50%; background-color: #ffc107; display: inline-block;"></span>Idle</div>
                    <div style="display: flex; align-items: center; gap: 8px; padding: 6px 16px; border: 1px solid #334155; border-radius: 20px; font-size: 0.85rem; font-weight: 600;"><span style="height: 10px; width: 10px; border-radius: 50%; background-color: #dc3545; display: inline-block;"></span>Error</div>
                </div>
                """, unsafe_allow_html=True)

        grid_row1_col1, grid_row1_col2 = st.columns(2, gap="large")
        with grid_row1_col1:
            with st.container(border=True):
                st.markdown("##### 🛢️ **PostgreSQL Engine Health**")
                is_connected, ping_success, db_latency_ms, db_recycle_state = True, True, 15, "Active (1800s pool)"
                if not is_connected or not ping_success or db_latency_ms is None: db_status, status_icon, status_color, sub_label, latency_text, latency_badge_color = "DOWN", "✖", "#dc2626", "Connection Lost / Timeout", "N/A (Unreachable)", "#dc2626"
                elif db_latency_ms > 100: db_status, status_icon, status_color, sub_label, latency_text, latency_badge_color = "DEGRADED", "⚠", "#f59e0b", "SELECT 1 (High Latency)", f"{db_latency_ms} ms (Slow)", "#f59e0b"
                else: db_status, status_icon, status_color, sub_label, latency_text, latency_badge_color = "UP", "✔", "#16a34a", "SELECT 1", f"{db_latency_ms} ms (Optimal)", "#16a34a"

                st.markdown(f"""
                <div style="text-align: center; margin: 16px 0 10px 0;"><div style="font-size: 2.2rem; font-weight: 800; color: {status_color}; display: inline-flex; align-items: center; gap: 8px;"><span>{status_icon}</span> {db_status}</div><div style="font-size: 0.85rem; font-weight: 600; margin-top: -2px;">({sub_label})</div></div>
                <div style="border-top: 1px solid rgba(148, 163, 184, 0.2); padding-top: 14px; margin-top: 14px;"><div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.92rem; margin-bottom: 8px;"><span>Database Latency:</span><strong style="color: {latency_badge_color};">{latency_text}</strong></div><div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.92rem;"><span>Recycle State:</span><span style="font-weight: 600;">{db_recycle_state}</span></div></div>
                """, unsafe_allow_html=True)
                
        with grid_row1_col2:
            with st.container(border=True):
                st.markdown("##### 🗘 **Idempotency Replay Hit Rate**")
                st.markdown("""<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 138px;"><div style="font-size: 3.6rem; font-weight: 800; line-height: 1;">0</div><div style="font-size: 1rem; font-weight: 600; margin-top: 12px;">Replays Short-circuited</div></div>""", unsafe_allow_html=True)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        grid_row2_col1, grid_row2_col2 = st.columns(2, gap="large")

        with grid_row2_col1:
            with st.container(border=True):
                st.markdown("##### 🌐 **HTTP Traffic & Error Distribution**")
                fig_donut = go.Figure(data=[go.Pie(labels=["2xx Success", "4xx Client Errors", "5xx Server Exceptions"], values=[888, 338, 3], hole=0.62, marker=dict(colors=["#10b981", "#f59e0b", "#ef4444"]), textinfo="percent", hoverinfo="label+value+percent", showlegend=True)])
                fig_donut.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=11)), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

        with grid_row2_col2:
            with st.container(border=True):
                st.markdown("##### 🛡️ **Security Middleware Status**")
                st.markdown("""
                <div style="text-align: center; margin: 10px 0 14px 0;"><div style="font-size: 2.2rem; font-weight: 800; color: #16a34a; display: inline-flex; align-items: center; gap: 8px;">✔ ACTIVE</div><div style="font-size: 0.85rem; font-weight: 600; margin-top: -4px;">All Filters Intercepting</div></div>
                <div style="border-top: 1px solid rgba(148, 163, 184, 0.2); padding-top: 12px; display: flex; flex-direction: column; gap: 8px; font-size: 0.9rem;"><div style="display: flex; align-items: center; gap: 8px;"><span style="color: #16a34a; font-weight: bold;">✔</span> CORS Headers Active</div><div style="display: flex; align-items: center; gap: 8px;"><span style="color: #16a34a; font-weight: bold;">✔</span> Strict Security Headers (CSP, X-Frame-Options)</div><div style="display: flex; align-items: center; gap: 8px;"><span style="color: #16a34a; font-weight: bold;">✔</span> Sanitization Filters</div></div>
                """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # TAB 2: PROVISIONING FORM & CLINICIAN DIRECTORY
    # --------------------------------------------------------------------------
    with tab_form:
        if st.session_state.get("trigger_form_clear"):
            for key in ["doc_first_name", "doc_middle_name", "doc_last_name", "doc_address", "doc_prc", "doc_email", "doc_contact", "em_name", "em_contact", "doc_affiliation"]:
                st.session_state[key] = ""
                st.session_state[f"{key}_invalid"] = False
            st.session_state.trigger_form_clear = False

        if st.session_state.form_success:
            st.success(st.session_state.form_success)
            st.session_state.form_success = None

        with st.container(border=True):
            st.markdown("""
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0; font-size: 1.45rem; font-weight: 700; letter-spacing: -0.3px;">Provision Clinician Account</h3>
                <p style="margin: 4px 0 14px 0; font-size: 0.95rem;">Create a verified practitioner profile and register login credentials in the system.</p>
                <div style="height: 1px; width: 100%; background-color: rgba(148, 163, 184, 0.2); margin-bottom: 18px;"></div>
            </div>
            """, unsafe_allow_html=True)

            first_name = st.text_input("FIRST NAME*", placeholder="Enter first name", key="doc_first_name", on_change=clean_alpha_input, args=("doc_first_name",))
            if st.session_state.get("doc_first_name_invalid"): st.error("⛔ Letters only. Numbers and symbols are not permitted.")
            
            last_name = st.text_input("LAST NAME*", placeholder="Enter last name", key="doc_last_name", on_change=clean_alpha_input, args=("doc_last_name",))
            if st.session_state.get("doc_last_name_invalid"): st.error("⛔ Letters only. Numbers and symbols are not permitted.")

            row3_col1, row3_col2 = st.columns([1, 3])
            with row3_col1: 
                middle_name = st.text_input("MIDDLE NAME", placeholder="Optional", key="doc_middle_name", on_change=clean_alpha_input, args=("doc_middle_name",))
                if st.session_state.get("doc_middle_name_invalid"): st.error("⛔ Letters only.")
            with row3_col2: 
                address = st.text_input("ADDRESS*", placeholder="Residential or clinic address", key="doc_address")

            row4_col1, row4_col2, row4_col3, row4_col4 = st.columns([1.5, 2, 1.3, 1])
            with row4_col1: specialization = st.selectbox("SPECIALIZATION*", options=SPECIALIZATION_OPTIONS)
            with row4_col2: hospital_affiliation = st.text_input("CLINIC AFFILIATION", placeholder="e.g., Manila Doctors Hospital", key="doc_affiliation")
            with row4_col3: 
                prc_license_raw = st.text_input("PRC LICENSE*", placeholder="7 digits only", max_chars=7, key="doc_prc", on_change=clean_prc_license, args=("doc_prc",))
                if st.session_state.get("doc_prc_invalid"): st.error("⛔ Numbers only.")
            with row4_col4: suffix = st.selectbox("SUFFIX*", options=SUFFIX_OPTIONS)

            row5_col1, row5_col2 = st.columns([1, 1])
            with row5_col1:
                email = st.text_input("EMAIL*", placeholder="strictly @gmail.com", key="doc_email")
                if email and not is_valid_gmail(email): 
                    st.error("⛔ Must be a valid Gmail address.")
            with row5_col2:
                contact_number = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="doc_contact", on_change=format_phone_number, args=("doc_contact",))
                if st.session_state.get("doc_contact_invalid"): 
                    st.error("⛔ Numbers only.")

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
            st.markdown("#### **CONTACT IN CASE OF EMERGENCY**")
            emergency_name = st.text_input("FULL NAME*", placeholder="Enter emergency contact's full name", key="em_name", on_change=clean_alpha_input, args=("em_name",))
            if st.session_state.get("em_name_invalid"): st.error("⛔ Letters only.")

            emergency_contact = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="em_contact", on_change=format_phone_number, args=("em_contact",))
            if st.session_state.get("em_contact_invalid"): st.error("⛔ Numbers only.")

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
            st.markdown("#### **CREDENTIAL DISPATCH & SECURITY CONTROLS**")
            col_sec1, col_sec2, col_sec3 = st.columns([1.5, 1.5, 1.2])
            with col_sec1: send_email_toggle = st.toggle("Automated Onboarding Email", value=True)
            with col_sec2: require_mfa_toggle = st.toggle("Enforce MFA on First Login", value=True)
            with col_sec3: cred_ttl = st.selectbox("Credential TTL", options=["24 Hours", "48 Hours", "7 Days"], index=0)

            st.divider()
            submit_btn = st.button("Submit Provisioning", type="primary", use_container_width=True)
            
        if submit_btn:
            errors = []
            if not first_name.strip(): errors.append("First Name is required.")
            if not last_name.strip(): errors.append("Last Name is required.")
            if not address.strip(): errors.append("Address is required.")
            if len(prc_license_raw) != 7: errors.append("PRC License must be exactly 7 digits.")
            if not is_valid_gmail(email): errors.append("Valid Gmail address is required.")
            if not is_valid_phone_format(contact_number): errors.append("Doctor Contact Number must be exactly 11 digits.")
            if not emergency_name.strip(): errors.append("Emergency Contact Name is required.")
            if not is_valid_phone_format(emergency_contact): errors.append("Emergency Contact Number must be exactly 11 digits.")
            
            formatted_prc = f"PRC {prc_license_raw.strip()}"
            if any(doc["license_number"] == formatted_prc for doc in st.session_state.doctor_directory):
                errors.append(f"License Conflict: `{formatted_prc}` is already registered.")

            if errors:
                for err in errors: st.error(f"❌ {err}")
            else:
                middle_init = f" {middle_name.strip().title()[0]}." if middle_name.strip() else ""
                formatted_full_name = f"{last_name.strip().title()}, {first_name.strip().title()}{middle_init}"
                
                st.session_state.doctor_directory.append({
                    "doctor_id": len(st.session_state.doctor_directory) + 1, "name": formatted_full_name,
                    "license_number": formatted_prc, "specialization": specialization,
                    "email": email.strip().lower(), "contact_number": contact_number,
                    "hospital_affiliation": hospital_affiliation.strip() or "Lucerna Medica Main Clinic",
                    "is_verified": True, "failed_attempts": 0, "is_locked": False, "mfa_enrolled": False, "token_version": 1
                })

                st.session_state.doctor_audit_logs.insert(0, {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "target_doctor": formatted_full_name,
                    "event_type": "ACCOUNT_PROVISIONED", "actor": f"Admin ({user_email})", "ip_address": "127.0.0.1",
                    "details": f"TTL: {cred_ttl} | Email Dispatched: {send_email_toggle} | MFA Required: {require_mfa_toggle}"
                })

                st.session_state.trigger_form_clear = True
                st.session_state.form_success = f"✅ Successfully provisioned **Dr. {first_name.title()} {last_name.title()}** with license **{formatted_prc}**!"
                st.rerun()

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### Clinician Database & Directory")
            st.caption("Inspect, filter, and manage provisioned clinical accounts.")
            
            raw_df = pd.DataFrame(st.session_state.doctor_directory)

            if not raw_df.empty:
                f_col_search, f_col_spec, f_col_status = st.columns([2.5, 2, 1.5])
                with f_col_search: search_query = st.text_input("Search Clinician", placeholder="Search by name, license #, or email...", label_visibility="collapsed", key="doc_search")
                with f_col_spec: selected_specialties = st.multiselect("Filter by Specialization", options=SPECIALIZATION_OPTIONS, placeholder="All Specialties", label_visibility="collapsed", key="doc_spec_filter")
                with f_col_status: status_filter = st.radio("Status Filter", options=["All", "Verified", "Pending"], horizontal=True, label_visibility="collapsed", key="doc_status_filter")

                filtered_df = raw_df.copy()
                if search_query:
                    query = search_query.lower()
                    filtered_df = filtered_df[filtered_df["name"].str.lower().str.contains(query) | filtered_df["license_number"].str.lower().str.contains(query) | filtered_df["email"].str.lower().str.contains(query)]
                if selected_specialties: filtered_df = filtered_df[filtered_df["specialization"].isin(selected_specialties)]
                if status_filter == "Verified": filtered_df = filtered_df[filtered_df["is_verified"] == True]
                elif status_filter == "Pending": filtered_df = filtered_df[filtered_df["is_verified"] == False]

                display_df = filtered_df.copy()
                display_df["status_badge"] = display_df["is_verified"].apply(lambda v: "🟢 Verified" if v else "🟡 Pending")
                display_df["lock_badge"] = display_df["is_locked"].apply(lambda l: "🔒 Locked" if l else "🟢 Normal")

                clinician_selection = st.dataframe(
                    display_df[["name", "license_number", "specialization", "contact_number", "email", "hospital_affiliation", "status_badge", "lock_badge"]],
                    use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
                    column_config={
                        "name": st.column_config.TextColumn("Clinician Name", width="medium"), "license_number": st.column_config.TextColumn("License Number", width="small"),
                        "specialization": st.column_config.TextColumn("Specialization", width="medium"), "contact_number": st.column_config.TextColumn("Contact Phone", width="small"),
                        "email": st.column_config.TextColumn("Institutional Email", width="medium"), "hospital_affiliation": st.column_config.TextColumn("Affiliation", width="medium"),
                        "status_badge": st.column_config.TextColumn("Verification", width="small"), "lock_badge": st.column_config.TextColumn("Access State", width="small")
                    },
                    height=240, key="clinician_directory_table"
                )

                st.divider()
                st.markdown("##### **Account Governance & Security Controls**")
                
                selected_doc_rows = clinician_selection.selection.rows
                target_doc = None
                if selected_doc_rows:
                    selected_license = display_df.iloc[selected_doc_rows[0]]["license_number"]
                    target_doc = next((d for d in st.session_state.doctor_directory if d["license_number"] == selected_license), None)

                render_clinician_governance_panel(target_doc, user_email)

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### Non-Clinical Identity & Security Audit Trail")
            st.caption("Immutable system log tracking authentication attempts, credential state changes, and verification approvals.")

            audit_df = pd.DataFrame(st.session_state.doctor_audit_logs)
            if not audit_df.empty:
                st.dataframe(
                    audit_df, use_container_width=True, hide_index=True, key="doctor_audit_logs_table_df",
                    column_config={
                        "timestamp": st.column_config.TextColumn("Timestamp (UTC)", width="medium"), "target_doctor": st.column_config.TextColumn("Clinician", width="medium"),
                        "event_type": st.column_config.TextColumn("Security Event", width="medium"), "actor": st.column_config.TextColumn("Triggered By", width="medium"),
                        "ip_address": st.column_config.TextColumn("Client IP", width="small"), "details": st.column_config.TextColumn("Telemetry & Audit Payload", width="large")
                    },
                    height=240
                )
            else:
                st.info("No security audit events recorded.")

    # --------------------------------------------------------------------------
    # TAB 3: PATIENT MANAGEMENT
    # --------------------------------------------------------------------------
    with tab_patient:
        raw_patients_df = pd.DataFrame(st.session_state.patient_directory)

        with st.container(border=True):
            st.markdown("### Pending Verification Queue")
            st.caption("Newly registered patients awaiting email confirmation or SMS OTP activation.")

            if not raw_patients_df.empty:
                pending_df = raw_patients_df[raw_patients_df["is_verified"] == False].reset_index(drop=True)

                if not pending_df.empty:
                    selection_event = st.dataframe(
                        pending_df[["name", "email", "contact_number", "registered_at", "pending_method", "dispatch_count"]],
                        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
                        key="df_pending_verification_queue",
                        column_config={
                            "name": "Full Name", "email": "Gmail Address", "contact_number": "Contact Number",
                            "registered_at": "Registered At", "pending_method": "Pending Method", "dispatch_count": "Dispatches"
                        },
                        height=160
                    )

                    selected_rows = selection_event.selection.rows
                    target_pending = pending_df.iloc[selected_rows[0]] if selected_rows else None

                    if target_pending is not None:
                        st.markdown(f"Selected: **{target_pending['name']}** (`{target_pending['email']}`)")
                    else:
                        st.caption("👈 *Click on a row in the table above to select a patient for action.*")

                    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        if st.button("🔄 Resend Link / OTP", use_container_width=True, disabled=(target_pending is None), key="btn_pend_resend"):
                            for p in st.session_state.patient_directory:
                                if p["patient_id"] == target_pending["patient_id"]: p["dispatch_count"] += 1
                            st.session_state.patient_audit_logs.insert(0, {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "target_patient": target_pending["name"], "event_type": "OTP_REDISPATCHED", "actor": f"Admin ({user_email})", "ip_address": "127.0.0.1", "details": f"Verification token re-dispatched to {target_pending['email']}."})
                            st.success(f"Verification token re-sent to {target_pending['email']}.")
                            st.rerun()

                    with col_p2:
                        if st.button("✅ Manual Authorization", use_container_width=True, disabled=(target_pending is None), key="btn_pend_auth"):
                            for p in st.session_state.patient_directory:
                                if p["patient_id"] == target_pending["patient_id"]:
                                    p["is_verified"] = True; p["is_active"] = True; p["pending_method"] = "None"
                            st.session_state.patient_audit_logs.insert(0, {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "target_patient": target_pending["name"], "event_type": "MANUAL_VERIFICATION", "actor": f"Admin ({user_email})", "ip_address": "127.0.0.1", "details": "Identity authorized manually by administrative override."})
                            st.success(f"Account for {target_pending['name']} manually verified.")
                            st.rerun()

                    with col_p3:
                        if st.button("🗑️ Purge Expired Requests", use_container_width=True, key="btn_pend_purge"):
                            purged_count = len([p for p in st.session_state.patient_directory if not p.get("is_verified", False)])
                            st.session_state.patient_directory = [p for p in st.session_state.patient_directory if p.get("is_verified", False)]
                            st.warning(f"Purged {purged_count} unverified registration attempt(s).")
                            st.rerun()
                else:
                    st.info("Queue is clear. No pending verifications.")

        with st.container(border=True):
            st.markdown("### Master Patient Directory")
            st.caption("Manage active accounts, enforce HIPAA compliance, and control access states.")

            if not raw_patients_df.empty:
                f_col_search, f_col_status, f_col_hipaa = st.columns([2.5, 1.5, 1.5])
                with f_col_search: p_search_query = st.text_input("Search Patient", placeholder="Search by name, email, or phone...", label_visibility="collapsed", key="pat_search_input")   
                with f_col_status: p_status_filter = st.radio("Status Filter", options=["All", "Active", "Pending", "Suspended"], horizontal=True, label_visibility="collapsed", key="pat_status_filter")
                with f_col_hipaa: p_hipaa_filter = st.radio("HIPAA State", options=["All", "Consented", "Pending"], horizontal=True, label_visibility="collapsed", key="pat_hipaa_filter")

                p_filtered_df = raw_patients_df.copy()
                if p_search_query:
                    q = p_search_query.lower()
                    p_filtered_df = p_filtered_df[p_filtered_df["name"].str.lower().str.contains(q) | p_filtered_df["email"].str.lower().str.contains(q) | p_filtered_df["contact_number"].str.contains(q)]
                
                if p_status_filter == "Active": p_filtered_df = p_filtered_df[(p_filtered_df["is_active"] == True) & (p_filtered_df["is_locked"] == False)]
                elif p_status_filter == "Pending": p_filtered_df = p_filtered_df[p_filtered_df["is_verified"] == False]
                elif p_status_filter == "Suspended": p_filtered_df = p_filtered_df[(p_filtered_df["is_active"] == False) | (p_filtered_df["is_locked"] == True)]

                if p_hipaa_filter == "Consented": p_filtered_df = p_filtered_df[p_filtered_df["hipaa_consent"] == True]
                elif p_hipaa_filter == "Pending": p_filtered_df = p_filtered_df[p_filtered_df["hipaa_consent"] == False]

                p_display_df = p_filtered_df.copy()
                p_display_df["hipaa_badge"] = p_display_df["hipaa_consent"].apply(lambda v: "📝 Consented" if v else "⏳ Pending")
                
                def get_account_state(row):
                    if not row["is_verified"]: return "🟡 Pending"
                    if row["is_locked"]: return "🔒 Locked"
                    if not row["is_active"]: return "🔴 Suspended"
                    return "🟢 Active"
                
                p_display_df["account_state"] = p_display_df.apply(get_account_state, axis=1)

                patient_selection = st.dataframe(
                    p_display_df[["name", "email", "contact_number", "dob", "hipaa_badge", "account_state"]],
                    use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="df_master_patient_directory",
                    column_config={
                        "name": "Patient Name", "email": "Gmail Address", "contact_number": "Contact Phone",
                        "dob": "Date of Birth", "hipaa_badge": "HIPAA Status", "account_state": "Account State"
                    },
                    height=240
                )

                st.divider()
                st.markdown("##### **Account Governance Panel**")
                
                selected_pat_rows = patient_selection.selection.rows
                target_patient = None
                if selected_pat_rows:
                    selected_email = p_display_df.iloc[selected_pat_rows[0]]["email"]
                    target_patient = next((p for p in st.session_state.patient_directory if p["email"] == selected_email), None)
                
                render_patient_governance_panel(target_patient, user_email)

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### Patient IAM & Compliance Audit Trail")
            st.caption("Immutable system event log recording security operations and HIPAA consent milestones.")
            p_audit_df = pd.DataFrame(st.session_state.patient_audit_logs)
            if not p_audit_df.empty:
                st.dataframe(
                    p_audit_df, use_container_width=True, hide_index=True, key="df_patient_audit_logs",
                    column_config={
                        "timestamp": "Timestamp (UTC)", "target_patient": "Target Patient", 
                        "event_type": "Security Event", "actor": "Triggered By", 
                        "ip_address": "Client IP", "details": st.column_config.TextColumn("Telemetry Payload", width="large")
                    },
                    height=240
                )
            else:
                st.info("No audit events recorded.")
    # --------------------------------------------------------------------------
    # TAB 4: EMPLOYEE / ADMIN ACCOUNTS & SETTINGS
    # --------------------------------------------------------------------------
    with tab_Admin:
        # --- ADMIN SECURITY SETTINGS ---
        with st.container(border=True):
            st.markdown("### Admin Security Settings")
            st.caption("Manage your own administrative credentials and profile security.")
            
            adm_col1, adm_col2 = st.columns([1, 1], gap="large")
            with adm_col1:
                st.markdown("##### Update Password")
                with st.form("account_tab_password_change_form", clear_on_submit=True):
                    st.text_input("Current Password", type="password", placeholder="Enter current password")
                    new_pw_col1, new_pw_col2 = st.columns(2)
                    with new_pw_col1: new_pw = st.text_input("New Password", type="password", placeholder="Enter new password")
                    with new_pw_col2: confirm_pw = st.text_input("Confirm Password", type="password", placeholder="Re-type new password")
                        
                    if st.form_submit_button("Update Admin Password", type="primary", use_container_width=True):
                        if not new_pw or not confirm_pw: st.error("❌ Please fill in all password fields.")
                        elif new_pw != confirm_pw: st.error("❌ New passwords do not match.")
                        else: st.success("✅ Your administrative password has been successfully updated.")
                            
            with adm_col2:
                st.markdown("##### Administrative Profile")
                st.text_input("Registered Name", value=user_name, disabled=True, help="Contact IT to change registered name.")
                st.text_input("Institutional Email", value=user_email, disabled=True)
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.markdown(f"**Current Role:** `<{user_role}>`")
                st.markdown("**MFA Status:** <span style='color: #10b981; font-weight: bold;'>🟢 Active (Authenticator App)</span>", unsafe_allow_html=True)

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # --- PROVISION NEW ADMIN ACCOUNT CONTAINER ---
        with st.container(border=True):
            st.markdown("##### Provision New Admin Account")

            if st.session_state.get("trigger_admin_form_clear"):
                for k in [
                    "adm_first_name", "adm_middle_name", "adm_last_name", "adm_address",
                    "adm_department", "adm_code", "adm_email", "adm_contact",
                    "adm_em_name", "adm_contact_em"
                ]:
                    st.session_state[k] = ""
                    st.session_state[f"{k}_invalid"] = False
                st.session_state.trigger_admin_form_clear = False

            if st.session_state.get("admin_form_success"):
                st.success(st.session_state.admin_form_success)
                st.session_state.admin_form_success = None

            emp_first_name = st.text_input("FIRST NAME*", placeholder="Enter first name", key="adm_first_name", on_change=clean_alpha_input, args=("adm_first_name",))
            if st.session_state.get("adm_first_name_invalid"): 
                st.error("⛔ Letters only. Numbers and symbols are not permitted.")

            emp_last_name = st.text_input("LAST NAME*", placeholder="Enter last name", key="adm_last_name", on_change=clean_alpha_input, args=("adm_last_name",))
            if st.session_state.get("adm_last_name_invalid"): 
                st.error("⛔ Letters only. Numbers and symbols are not permitted.")

            row3_col1, row3_col2 = st.columns([1, 3])
            with row3_col1: 
                emp_middle_name = st.text_input("MIDDLE NAME", placeholder="Optional", key="adm_middle_name", on_change=clean_alpha_input, args=("adm_middle_name",))
                if st.session_state.get("adm_middle_name_invalid"): 
                    st.error("⛔ Letters only.")
            with row3_col2: 
                emp_address = st.text_input("ADDRESS*", placeholder="Residential or office address", key="adm_address")

            row4_col1, row4_col2, row4_col3, row4_col4 = st.columns([1.5, 2, 1.3, 1])
            with row4_col1: 
                emp_role = st.selectbox("ROLE*", ["System Admin", "Super Admin", "IT Support", "Compliance Auditor"], key="adm_role")
            with row4_col2: 
                emp_dept = st.text_input("DEPARTMENT", value="Administration", key="adm_department")
            with row4_col3:
                default_code = f"ADM-{len(st.session_state.employee_directory) + 1:03d}"
                emp_code = st.text_input("ADMIN CODE*", value=st.session_state.get("adm_code") or default_code, placeholder="e.g., ADM-001", key="adm_code")
            with row4_col4: 
                emp_suffix = st.selectbox("SUFFIX*", SUFFIX_OPTIONS, key="adm_suffix")

            row5_col1, row5_col2 = st.columns(2)
            with row5_col1: 
                emp_email = st.text_input("EMAIL*", placeholder="name@hospital.com", key="adm_email")
                if emp_email and not is_valid_admin_email(emp_email): 
                    st.error("⛔ Please enter a valid institutional / hospital email address.")
            with row5_col2: 
                emp_contact = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="adm_contact", on_change=format_phone_number, args=("adm_contact",))
                if st.session_state.get("adm_contact_invalid"): 
                    st.error("⛔ Numbers only.")

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
            st.markdown("#### **CONTACT IN CASE OF EMERGENCY**")
            emp_em_name = st.text_input("FULL NAME*", placeholder="Enter emergency contact's full name", key="adm_em_name", on_change=clean_alpha_input, args=("adm_em_name",))
            if st.session_state.get("adm_em_name_invalid"): 
                st.error("⛔ Letters only.")
            
            row_em1, row_em2 = st.columns(2)
            with row_em1: 
                emp_em_contact = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="adm_contact_em", on_change=format_phone_number, args=("adm_contact_em",))
                if st.session_state.get("adm_contact_em_invalid"): 
                    st.error("⛔ Numbers only.")
            with row_em2: 
                emp_em_relation = st.selectbox("RELATION*", RELATION_OPTIONS, key="adm_em_relation")

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
            st.markdown("#### **CREDENTIAL DISPATCH & SECURITY CONTROLS**")
            col_sec1, col_sec2, col_sec3 = st.columns([1.5, 1.5, 1.2])
            with col_sec1: 
                emp_send_email = st.toggle("Onboarding Email", value=True, key="adm_send_email")
            with col_sec2: 
                emp_require_mfa = st.toggle("Enforce MFA", value=True, key="adm_require_mfa")
            with col_sec3: 
                emp_cred_ttl = st.selectbox("Credential TTL", ["24 Hours", "48 Hours", "7 Days"], key="adm_cred_ttl")

            st.divider()
            submit_emp = st.button("Create Admin Account", type="primary", use_container_width=True)

            if submit_emp:
                errors = []
                if not emp_first_name.strip(): errors.append("First Name is required.")
                if not emp_last_name.strip(): errors.append("Last Name is required.")
                if not emp_address.strip(): errors.append("Address is required.")
                if not emp_code.strip(): errors.append("Admin Code is required.")
                if not is_valid_admin_email(emp_email): errors.append("Valid Institutional / Hospital Email is required.")
                if not is_valid_phone_format(emp_contact): errors.append("Contact Number must follow 09XX-XXX-XXXX.")
                if not emp_em_name.strip(): errors.append("Emergency Contact Name is required.")
                if not is_valid_phone_format(emp_em_contact): errors.append("Emergency Contact Number must follow 09XX-XXX-XXXX.")

                if any(e["emp_id"] == emp_code.strip() for e in st.session_state.employee_directory):
                    errors.append(f"Admin Code Conflict: `{emp_code.strip()}` is already assigned.")

                if errors:
                    for err in errors: st.error(f"❌ {err}")
                else:
                    mid_init = f" {emp_middle_name.strip().title()[0]}." if emp_middle_name.strip() else ""
                    full_name = f"{emp_last_name.strip().title()}, {emp_first_name.strip().title()}{mid_init}"

                    st.session_state.employee_directory.append({
                        "emp_id": emp_code.strip(), "name": full_name, "role": emp_role,
                        "department": emp_dept.strip() or "Administration", "email": emp_email.strip().lower(),
                        "contact_number": emp_contact.strip(), "status": "Active"
                    })
                    st.session_state.trigger_admin_form_clear = True
                    st.session_state.admin_form_success = f"✅ Provisioned Admin **{full_name}** (`{emp_code.strip()}`) successfully!"
                    st.rerun()

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # --- STAFF & ADMIN DIRECTORY & GOVERNANCE PANEL ---
        with st.container(border=True):
            st.markdown("##### Staff & Admin Directory")
            
            emp_df = pd.DataFrame(st.session_state.employee_directory)
            emp_display = emp_df.copy()
            emp_display["status_badge"] = emp_display["status"].apply(lambda s: "🟢 Active" if s == "Active" else "🔴 Suspended")
            
            emp_selection = st.dataframe(
                emp_display[["emp_id", "name", "role", "email", "status_badge"]], 
                use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="admin_tab_employee_df",
                column_config={
                    "emp_id": "Emp ID", "name": "Name", "role": "Role", "email": "Email", "status_badge": "Status"
                },
                height=220
            )

            st.divider()
            st.markdown("##### 🔑 Credential Management")

            selected_emp_rows = emp_selection.selection.rows
            target_e = None
            if selected_emp_rows:
                selected_emp_id = emp_display.iloc[selected_emp_rows[0]]["emp_id"]
                target_e = next((e for e in st.session_state.employee_directory if e["emp_id"] == selected_emp_id), None)

            render_admin_governance_panel(target_e)