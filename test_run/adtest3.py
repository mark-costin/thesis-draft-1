"""
Lucerna Medica — Admin Console (Streamlit, FRONTEND-ONLY)
Dark-theme-first redesign with design tokens + gradient card surfaces.

Design principles:
  • Layered backgrounds: #0F172A canvas → gradient cards above it
  • Borders over fills: rgba(255,255,255,0.10) dividers
  • Softened text: #E8EDF4 primary, #94A3B8 muted
  • Muted accents with soft glow instead of hard edges
  • Theme toggle re-skins cards AND tables instantly (via --gdg-* overrides)

Pair with .streamlit/config.toml (base="light", secondaryBackgroundColor="#FFFFFF")
for the dataframe canvas to have a sane fallback before CSS runs.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# CONSTANTS
# ==============================================================================
MAX_LOGIN_ATTEMPTS = 5
PRC_LEN = 7
PHONE_DIGITS = 11
PASSWORD_MIN_LEN = 12

DEFAULT_AVATAR_URL = ("https://images.unsplash.com/photo-1534528741775-53994a69daeb"
                      "?auto=format&fit=crop&w=150&q=80")

SPECIALIZATION_OPTIONS = ["General Physician", "Internal Medicine", "Cardiology",
                          "Pulmonology", "Psychiatry"]
SUFFIX_OPTIONS = ["None", "MD", "PhD", "DO", "MD, PhD", "Jr.", "Sr.", "III"]
RELATION_OPTIONS = ["Mother", "Father", "Spouse", "Son", "Daughter",
                    "Brother", "Sister", "Other"]
ADMIN_ROLE_OPTIONS = ["System Admin", "Super Admin", "IT Support", "Compliance Auditor"]
CRED_TTL_OPTIONS = ["24 Hours", "48 Hours", "7 Days"]

# ==============================================================================
# VALIDATORS
# ==============================================================================
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s\-'.]*$")
GMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@gmail\.com$", re.IGNORECASE)
INST_EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@(?:[a-z0-9\-]+\.)+[a-z]{2,}$", re.IGNORECASE)
PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$")

is_valid_name = lambda s: bool(NAME_RE.match((s or "").strip()))
is_valid_gmail = lambda s: bool(GMAIL_RE.match((s or "").strip()))
is_valid_inst_email = lambda s: bool(INST_EMAIL_RE.match((s or "").strip()))


def normalize_phone(raw: str) -> Optional[str]:
    d = "".join(filter(str.isdigit, raw or ""))[:PHONE_DIGITS]
    return f"{d[:4]}-{d[4:7]}-{d[7:11]}" if len(d) == PHONE_DIGITS else None


def normalize_prc(raw: str) -> Optional[str]:
    d = "".join(filter(str.isdigit, raw or ""))[:PRC_LEN]
    return d if len(d) == PRC_LEN else None


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ==============================================================================
# THEME TOKENS
# ==============================================================================
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"

DARK = {
    "bg":             "#0F172A",
    "bg_soft":        "#0B1220",
    "card":           "#243147",
    "card_soft":      "#2B3A52",
    "card_tint":      "rgba(20,184,166,0.04)",
    "border":         "rgba(255,255,255,0.10)",
    "border_strong":  "rgba(255,255,255,0.16)",
    "text":           "#E8EDF4",
    "text_sub":       "#C7D2E0",
    "text_mute":      "#94A3B8",
    "accent":         "#14B8A6",
    "accent_soft":    "rgba(20,184,166,0.14)",
    "accent_glow":    "rgba(20,184,166,0.35)",
    "success":        "#34D399",
    "warn":           "#FBBF24",
    "danger":         "#F87171",
    "info":           "#60A5FA",
    "chip_bg":        "rgba(20,184,166,0.12)",
    "input_bg":       "#243147",
    "shadow":         "0 6px 20px rgba(0,0,0,0.35)",
    "shadow_soft":    "0 3px 10px rgba(0,0,0,0.22)",
    "table_bg":       "#243147",
    "table_header":   "#2B3A52",
}

LIGHT = {
    "bg":             "#EEF2F7",
    "bg_soft":        "#E2E8F0",
    "card":           "#FFFFFF",
    "card_soft":      "#F7F9FC",
    "card_tint":      "rgba(15,118,110,0.025)",
    "border":         "#E5EAF0",
    "border_strong":  "#CBD5E1",
    "text":           "#0F172A",
    "text_sub":       "#334155",
    "text_mute":      "#64748B",
    "accent":         "#0F766E",
    "accent_soft":    "rgba(15,118,110,0.12)",
    "accent_glow":    "rgba(15,118,110,0.30)",
    "success":        "#059669",
    "warn":           "#D97706",
    "danger":         "#DC2626",
    "info":           "#0284C7",
    "chip_bg":        "rgba(15,118,110,0.10)",
    "input_bg":       "#F8FAFC",
    "shadow":         "0 6px 18px rgba(15,23,42,0.06)",
    "shadow_soft":    "0 2px 8px rgba(15,23,42,0.04)",
    "table_bg":       "#F8FAFC",
    "table_header":   "#F1F5F9",
}

T = DARK if st.session_state.theme_mode == "dark" else LIGHT


# ==============================================================================
# SEED HELPERS
# ==============================================================================
def _doc(i, name, lic, spec, email, phone, aff, **kw):
    return {"doctor_id": i, "name": name, "license_number": lic, "specialization": spec,
            "email": email, "contact_number": phone, "hospital_affiliation": aff,
            "is_verified": True, "failed_attempts": 0, "is_locked": False,
            "mfa_enrolled": False, "token_version": 1, **kw}


def _pat(i, name, email, phone, dob, reg, **kw):
    return {"patient_id": i, "name": name, "email": email, "contact_number": phone,
            "dob": dob, "registered_at": reg, "pending_method": "None",
            "dispatch_count": 1, "is_verified": True, "is_active": True,
            "hipaa_consent": True, "hipaa_consent_at": reg,
            "failed_attempts": 0, "is_locked": False, **kw}


def _emp(eid, name, role, email, dept="Administration", status="Active"):
    return {"emp_id": eid, "name": name, "role": role, "department": dept,
            "email": email, "status": status}


def _aud(t, target, ev, actor, ip, det):
    return {"timestamp": t, "target": target, "event_type": ev,
            "actor": actor, "ip_address": ip, "details": det}


# ==============================================================================
# SESSION BOOTSTRAP
# ==============================================================================
def _seed_state() -> None:
    st.session_state.setdefault("user", {
        "name": "First Name", "email": "admin.system@lucernamedica.com",
        "role": "ADMIN", "avatar_url": DEFAULT_AVATAR_URL,
    })
    st.session_state.setdefault("night_light", False)
    st.session_state.setdefault("night_light_warmth", 8)

    st.session_state.setdefault("doctors", [
        _doc(1, "Smith, John M.", "PRC 1234567", "General Physician",
             "doc.smith@gmail.com", "0917-123-4567", "Lucerna Central", mfa_enrolled=True),
        _doc(2, "Velasco, Maria A.", "PRC 8839210", "Cardiology",
             "m.velasco@gmail.com", "0920-987-6543", "Heart Center",
             is_verified=False, failed_attempts=4, is_locked=True, token_version=3),
    ])
    st.session_state.setdefault("doctor_audit_logs", [
        _aud("2026-09-10 09:12:15", "Smith, John M.", "LOGIN_SUCCESS",
             "Dr. Smith (doc_smith)", "192.168.1.45", "MFA Challenge Passed"),
        _aud("2026-09-10 08:30:00", "Velasco, Maria A.", "ACCOUNT_LOCKED",
             "SYSTEM_GUARD", "112.198.72.10", "Threshold exceeded: 4 attempts."),
        _aud("2026-09-09 14:22:11", "Smith, John M.", "VERIFICATION_APPROVED",
             "Admin (admin.system)", "10.0.4.12", "PRC verified against registry."),
    ])

    st.session_state.setdefault("patients", [
        _pat(1, "Mason, Justin L.", "j.mason@gmail.com", "0917-555-0198",
             "1992-08-14", "2026-09-09 08:15:22"),
        _pat(2, "Reyes, Sofia M.", "sofia.reyes99@gmail.com", "0920-111-4432",
             "1999-11-02", "2026-09-10 10:05:00", is_verified=False, is_active=False,
             hipaa_consent=False, hipaa_consent_at=None,
             pending_method="Pending Phone OTP", dispatch_count=2),
        _pat(3, "Bautista, Carlos T.", "cbautista.tech@gmail.com", "0918-999-8877",
             "1985-03-22", "2026-09-01 14:10:00", is_active=False,
             failed_attempts=5, is_locked=True),
    ])
    st.session_state.setdefault("patient_audit_logs", [
        _aud("2026-09-09 08:20:11", "Mason, Justin L.", "HIPAA_CONSENT_ACCEPTED",
             "System Registration", "112.201.44.9", "Data Privacy Act acknowledged."),
        _aud("2026-09-10 10:15:00", "Reyes, Sofia M.", "OTP_DISPATCHED",
             "Twilio Gateway", "System", "SMS OTP re-sent (Attempt 2)."),
        _aud("2026-09-10 11:30:22", "Bautista, Carlos T.", "ACCOUNT_SUSPENDED",
             "System Guard", "System", "Suspended: 5 failed logins."),
    ])

    st.session_state.setdefault("employees", [
        _emp("ADM-001", "First Name", "System Admin", "admin.system@lucernamedica.com"),
        _emp("EMP-002", "Connor, Sarah", "IT Support", "s.connor@lucernamedica.com"),
        _emp("EMP-003", "Wright, Marcus", "Compliance Auditor",
             "m.wright@lucernamedica.com", status="Suspended"),
    ])
    st.session_state.setdefault("employee_audit_logs", [])

    st.session_state.setdefault("health", {
        "db": {"up": True, "latency_ms": 15, "recycle_state": "Active (1800s pool)"},
        "pool": {"active": 0, "max": 10},
        "nodes": [
            {"PID": "1XXX.XX.X.X1", "Active Sockets": 2, "Status": "🟢 Healthy"},
            {"PID": "1XXX.XX.X.X2", "Active Sockets": 0, "Status": "🟡 Idle"},
            {"PID": "1XXX.XX.X.X3", "Active Sockets": 0, "Status": "🔴 Error: Timeout"},
            {"PID": "1XXX.XX.X.X4", "Active Sockets": 0, "Status": "🔴 Server Down"},
        ],
        "http": {"2xx": 888, "4xx": 338, "5xx": 3},
    })
    st.session_state.setdefault("timeseries", [
        {"date": d, "Patients": p, "Doctors": dc, "Admins": a}
        for d, p, dc, a in [
            ("Mon", 0, 10, 10), ("Tue", 0, 0, 0), ("Wed", 20, 200, 0),
            ("Thu", 0, 0, 300), ("Fri", 0, 300, 0), ("Sat", 0, 30, 0),
            ("Sun", 0, 0, 0),
        ]
    ])


_seed_state()
USER = st.session_state.user


# ==============================================================================
# LOCAL SERVICE LAYER
# ==============================================================================
def _find(coll: str, id_field: str, id_val):
    return next((r for r in st.session_state[coll] if r[id_field] == id_val), None)


def _log(log_key: str, target: str, event: str, details: str) -> None:
    st.session_state[log_key].insert(0, {
        "timestamp": now_utc(), "target": target, "event_type": event,
        "actor": f"Admin ({USER['email']})", "ip_address": "127.0.0.1",
        "details": details,
    })


def svc_create_doctor(p: dict) -> None:
    mid = f" {p['middle_name'][0]}." if p.get("middle_name") else ""
    name = f"{p['last_name']}, {p['first_name']}{mid}"
    st.session_state.doctors.append(_doc(
        max((d["doctor_id"] for d in st.session_state.doctors), default=0) + 1,
        name, f"PRC {p['prc_license']}", p["specialization"], p["email"],
        p["contact_number"], p["hospital_affiliation"], mfa_enrolled=bool(p["enforce_mfa"])))
    _log("doctor_audit_logs", name, "ACCOUNT_PROVISIONED",
         f"TTL: {p['credential_ttl']} | Email: {p['send_onboarding_email']} | MFA: {p['enforce_mfa']}")


def svc_unlock_doctor(did):
    d = _find("doctors", "doctor_id", did)
    if d:
        d.update(is_locked=False, failed_attempts=0)
        _log("doctor_audit_logs", d["name"], "ACCOUNT_UNLOCKED",
             "Administrator cleared login threshold.")


def svc_reset_doctor_otp(did):
    d = _find("doctors", "doctor_id", did)
    if d:
        _log("doctor_audit_logs", d["name"], "PASSWORD_RESET_DISPATCHED",
             f"Temporary OTP sent to {d['email']}.")


def svc_revoke_doctor(did):
    d = _find("doctors", "doctor_id", did)
    if d:
        d["token_version"] += 1
        _log("doctor_audit_logs", d["name"], "SESSION_REVOKED",
             f"Token version incremented to {d['token_version']}.")


def svc_patient_reset_attempts(pid):
    p = _find("patients", "patient_id", pid)
    if p:
        p.update(failed_attempts=0, is_locked=False)
        _log("patient_audit_logs", p["name"], "LOCKOUT_CLEARED",
             "Administrator cleared failed login counter.")


def svc_patient_reset_link(pid):
    p = _find("patients", "patient_id", pid)
    if p:
        _log("patient_audit_logs", p["name"], "PASSWORD_RESET_DISPATCHED",
             f"Temporary reset token sent to {p['email']}.")


def svc_patient_suspend(pid):
    p = _find("patients", "patient_id", pid)
    if p:
        p["is_active"] = False
        _log("patient_audit_logs", p["name"], "ACCOUNT_SUSPENDED",
             "Account deactivated by administrator.")


def svc_patient_restore(pid):
    p = _find("patients", "patient_id", pid)
    if p:
        p["is_active"] = True
        _log("patient_audit_logs", p["name"], "ACCOUNT_RESTORED",
             "Account reactivated by administrator.")


def svc_patient_verify(pid):
    p = _find("patients", "patient_id", pid)
    if p:
        p.update(is_verified=True, is_active=True, pending_method="None")
        _log("patient_audit_logs", p["name"], "MANUAL_VERIFICATION",
             "Identity authorized manually by admin override.")


def svc_patient_redispatch(pid):
    p = _find("patients", "patient_id", pid)
    if p:
        p["dispatch_count"] += 1
        _log("patient_audit_logs", p["name"], "OTP_REDISPATCHED",
             f"Verification token re-dispatched to {p['email']}.")


def svc_purge_pending() -> int:
    before = len(st.session_state.patients)
    st.session_state.patients = [p for p in st.session_state.patients if p.get("is_verified")]
    return before - len(st.session_state.patients)


def svc_create_employee(p: dict) -> None:
    mid = f" {p['middle_name'][0]}." if p.get("middle_name") else ""
    name = f"{p['last_name']}, {p['first_name']}{mid}"
    st.session_state.employees.append(
        _emp(p["emp_id"], name, p["role"], p["email"], p["department"]))
    _log("employee_audit_logs", name, "ADMIN_PROVISIONED",
         f"Role: {p['role']} | Email: {p['send_onboarding_email']} | MFA: {p['enforce_mfa']}")


def svc_employee_reset_otp(eid):
    e = _find("employees", "emp_id", eid)
    if e:
        _log("employee_audit_logs", e["name"], "PASSWORD_RESET_DISPATCHED",
             f"Reset link sent to {e['email']}.")


def svc_employee_toggle_status(eid):
    e = _find("employees", "emp_id", eid)
    if e:
        e["status"] = "Suspended" if e["status"] == "Active" else "Active"
        _log("employee_audit_logs", e["name"], "STATUS_TOGGLED",
             f"Status set to {e['status']}.")


def svc_change_password(current: str, new: str) -> None:
    _log("employee_audit_logs", USER["name"], "ADMIN_PASSWORD_CHANGED",
         "Administrator updated their own password.")


# ==============================================================================
# PAGE CONFIG + THEME CSS
# ==============================================================================
st.set_page_config(layout="wide", page_title="Lucerna Medica — Admin Console")

st.markdown(f"""
<style>
/* ============= Base canvas ============= */
.stApp, [data-testid="stAppViewContainer"] {{
    background-color: {T['bg']} !important;
    color: {T['text']} !important;
}}
[data-testid="stHeader"], [data-testid="stToolbar"] {{ background: transparent !important; }}

/* ============= Text ============= */
h1,h2,h3,h4,h5,h6 {{ color: {T['text']} !important; }}
p, span, label {{ color: {T['text_sub']} !important; }}
small, .stCaption, [data-testid="stCaptionContainer"] * {{
    color: {T['text_mute']} !important;
}}

/* ============= Bordered containers (gradient cards) ============= */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: linear-gradient(135deg, {T['card']} 0%, {T['card_soft']} 100%)
                !important;
    border: 1px solid {T['border']} !important;
    border-radius: 14px !important;
    box-shadow: {T['shadow_soft']} !important;
}}
[data-testid="stVerticalBlockBorderWrapper"] > div {{
    background-color: transparent !important;
}}

/* ============= Tabs ============= */
[data-baseweb="tab-list"] {{
    display: flex !important;
    width: 100% !important;
    margin-top: 14px !important;
    margin-bottom: 16px !important;
    border-bottom: 1px solid {T['border']} !important;
    background: transparent !important;
    gap: 0 !important;
}}
button[data-baseweb="tab"] {{
    flex: 1 1 0 !important;
    height: 52px !important;
    padding: 10px 16px !important;
    justify-content: center !important;
    background-color: transparent !important;
    border-radius: 0 !important;
    transition: background 0.15s ease;
}}
button[data-baseweb="tab"]:hover {{ background-color: {T['card_soft']} !important; }}
button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {{
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.6px !important;
    color: {T['text_mute']} !important;
}}
button[data-baseweb="tab"][aria-selected="true"] p,
button[data-baseweb="tab"][aria-selected="true"] span {{
    color: {T['accent']} !important;
}}
[data-baseweb="tab-highlight"] {{
    background-color: {T['accent']} !important;
    height: 3px !important;
    border-radius: 2px !important;
    box-shadow: 0 0 10px {T['accent_glow']} !important;
}}

/* ============= Primary buttons ============= */
.stApp button[kind="primary"],
.stApp button[data-testid="baseButton-primary"],
.stApp button[data-testid="stBaseButton-primary"] {{
    background-color: {T['accent']} !important;
    color: #0B1220 !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    transition: all 0.15s ease;
}}
.stApp button[kind="primary"] p,
.stApp button[data-testid="baseButton-primary"] p,
.stApp button[data-testid="stBaseButton-primary"] p {{
    color: #0B1220 !important;
    font-weight: 700 !important;
}}
.stApp button[kind="primary"]:hover {{
    box-shadow: 0 0 14px {T['accent_glow']} !important;
    filter: brightness(1.08);
}}

/* ============= Secondary buttons ============= */
.stApp button[kind="secondary"],
.stApp button[data-testid="baseButton-secondary"],
.stApp button[data-testid="stBaseButton-secondary"] {{
    background-color: {T['card_soft']} !important;
    border: 1px solid {T['border_strong']} !important;
    color: {T['text']} !important;
    border-radius: 8px !important;
    transition: all 0.15s ease;
}}
.stApp button[kind="secondary"] p,
.stApp button[data-testid="baseButton-secondary"] p,
.stApp button[data-testid="stBaseButton-secondary"] p {{
    color: {T['text']} !important;
}}
.stApp button[kind="secondary"]:hover {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 12px {T['accent_glow']} !important;
}}
.stApp button[kind="secondary"]:hover p {{ color: {T['accent']} !important; }}

/* ============= Inputs ============= */
.stTextInput input, .stTextArea textarea, .stNumberInput input {{
    background-color: {T['input_bg']} !important;
    border: 1px solid {T['border_strong']} !important;
    color: {T['text']} !important;
    border-radius: 8px !important;
}}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {{
    color: {T['text_mute']} !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 2px {T['accent_soft']} !important;
}}
[data-baseweb="select"] > div,
[data-baseweb="select"] [role="button"] {{
    background-color: {T['input_bg']} !important;
    border-color: {T['border_strong']} !important;
    color: {T['text']} !important;
}}
[data-baseweb="select"] * {{ color: {T['text']} !important; }}
[data-baseweb="popover"] ul, [data-baseweb="menu"] {{
    background-color: {T['card']} !important;
    border: 1px solid {T['border_strong']} !important;
}}
[data-baseweb="menu"] li:hover {{ background-color: {T['card_soft']} !important; }}

/* ============= Radios / toggles / sliders ============= */
[role="radiogroup"] label,
[role="radiogroup"] label span {{ color: {T['text_sub']} !important; }}
[data-testid="stSlider"] *, [data-testid="stToggle"] * {{
    color: {T['text_sub']} !important;
}}

/* ============= Dataframes (theme-aware) ============= */
[data-testid="stDataFrame"] {{
    --gdg-bg-cell:                {T['table_bg']};
    --gdg-bg-cell-medium:         {T['card_soft']};
    --gdg-bg-header:              {T['table_header']};
    --gdg-bg-header-hovered:      {T['card_soft']};
    --gdg-bg-header-has-focus:    {T['card_soft']};
    --gdg-bg-bubble:              {T['card']};
    --gdg-bg-bubble-selected:     {T['accent_soft']};
    --gdg-bg-search-result:       {T['accent_soft']};
    --gdg-text-dark:              {T['text']};
    --gdg-text-medium:            {T['text_sub']};
    --gdg-text-light:             {T['text_mute']};
    --gdg-text-header:            {T['text_mute']};
    --gdg-text-group-header:      {T['text']};
    --gdg-text-bubble:            {T['text']};
    --gdg-accent-color:           {T['accent']};
    --gdg-accent-light:           {T['accent_soft']};
    --gdg-accent-fg:              #FFFFFF;
    --gdg-border-color:           {T['border']};
    --gdg-horizontal-border-color:{T['border']};
    --gdg-drilldown-border:       {T['border_strong']};
    --gdg-link-color:             {T['accent']};
    --gdg-cell-horizontal-padding: 12px;
    --gdg-font-family:            inherit;
    background-color: {T['card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}
[data-testid="stDataFrame"] > div {{ background-color: {T['card']} !important; }}
[data-testid="stDataFrame"] ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb {{
    background: {T['border_strong']}; border-radius: 6px;
}}
[data-testid="stDataFrame"] ::-webkit-scrollbar-track {{ background: transparent; }}

/* ============= Popover ============= */
div[data-testid="stPopoverBody"] {{
    background: linear-gradient(135deg, {T['card']} 0%, {T['card_soft']} 100%)
                !important;
    border: 1px solid {T['border_strong']} !important;
    border-radius: 14px !important;
    box-shadow: 0 12px 32px rgba(0,0,0,0.45) !important;
}}
div[data-testid="stPopover"] > button {{
    background-color: {T['card']} !important;
    border: 1px solid {T['border_strong']} !important;
    color: {T['text']} !important;
    border-radius: 10px !important;
}}
div[data-testid="stPopover"] > button p {{ color: {T['text']} !important; }}
div[data-testid="stPopover"] > button:hover {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 12px {T['accent_glow']} !important;
}}
div[data-testid="stPopover"] > button [data-testid="stIconEmoji"] {{
    display: inline-block !important;
    width: 38px !important; height: 38px !important; min-width: 38px !important;
    border-radius: 50% !important;
    border: 2px solid {T['accent']} !important;
    background-image: url('{USER["avatar_url"]}') !important;
    background-size: cover !important;
    background-position: center !important;
    background-repeat: no-repeat !important;
    font-size: 0 !important;
    color: transparent !important;
    margin-right: 12px !important;
    box-shadow: 0 0 10px {T['accent_glow']} !important;
}}

/* ============= Alerts / forms / dividers ============= */
[data-testid="stAlert"] {{
    background-color: {T['card']} !important;
    border: 1px solid {T['border_strong']} !important;
    border-radius: 10px !important;
}}
[data-testid="stAlert"] p {{ color: {T['text']} !important; }}
[data-testid="stForm"] {{
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}}
hr {{ border-color: {T['border']} !important; }}

/* ============= Misc ============= */
[data-testid*="stInputInstructions"] {{ display: none !important; }}
</style>
""", unsafe_allow_html=True)

if st.session_state.night_light:
    op = st.session_state.night_light_warmth / 100
    st.markdown(f'<div style="position:fixed;top:0;left:0;width:100vw;height:100vh;'
                f'background-color:rgba(255,145,0,{op});pointer-events:none;'
                f'z-index:999999;"></div>', unsafe_allow_html=True)


# ==============================================================================
# UI HELPERS
# ==============================================================================
def metric_card(label: str, value: str, sub: str, sub_color: Optional[str] = None) -> str:
    sub_color = sub_color or T["text_mute"]
    return (
        f'<div style="'
        f'background:linear-gradient(135deg, {T["card"]} 0%, {T["card_soft"]} 100%);'
        f'border:1px solid {T["border"]};'
        f'border-radius:14px;padding:18px 20px;'
        f'box-shadow:{T["shadow_soft"]};'
        f'height:138px;display:flex;flex-direction:column;'
        f'justify-content:space-between;'
        f'transition:box-shadow .15s ease;'
        f'">'
        f'<div style="font-size:.78rem;font-weight:700;color:{T["text_mute"]};'
        f'letter-spacing:.6px;text-transform:uppercase;">{label}</div>'
        f'<div style="font-size:2.2rem;font-weight:800;color:{T["text"]};'
        f'line-height:1;letter-spacing:-0.5px;">{value}</div>'
        f'<div style="font-size:.82rem;font-weight:600;color:{sub_color};">{sub}</div>'
        f'</div>'
    )


def section_header(title: str, subtitle: str) -> str:
    return (
        f'<div style="margin-bottom:22px;">'
        f'<h3 style="margin:0;font-size:1.3rem;font-weight:700;color:{T["text"]};'
        f'letter-spacing:-.2px;">{title}</h3>'
        f'<p style="margin:4px 0 14px;font-size:.9rem;color:{T["text_mute"]};">{subtitle}</p>'
        f'<div style="height:1px;width:100%;background:{T["border"]};"></div></div>'
    )


# ==============================================================================
# GOVERNANCE PANELS
# ==============================================================================
def render_clinician_panel(doc: Optional[dict]) -> None:
    sel = doc is not None
    if sel:
        st.markdown(f"Selected Clinician: **{doc['name']}** (`{doc['license_number']}`)")
    else:
        st.caption("👈 *Click a row above to select a clinician for action.*")

    c1, c2, c3 = st.columns(3)
    with c1:
        failed = doc.get("failed_attempts", 0) if sel else 0
        locked = doc.get("is_locked", False) if sel else False
        st.markdown(f"**Failed Logins:** `{failed}/{MAX_LOGIN_ATTEMPTS}`")
        if st.button("🔓 Clear Lockout", use_container_width=True,
                     disabled=not (sel and locked), key="btn_doc_unlock"):
            svc_unlock_doctor(doc["doctor_id"])
            st.success(f"Unlocked account for {doc['name']}.")
            st.rerun()
    with c2:
        st.markdown("**Credential Reset:**")
        if st.button("🔑 Dispatch Reset OTP", use_container_width=True,
                     disabled=not sel, key="btn_doc_otp"):
            svc_reset_doctor_otp(doc["doctor_id"])
            st.success(f"One-time reset dispatched to {doc['email']}.")
    with c3:
        ver = doc.get("token_version", 0) if sel else 0
        st.markdown(f"**Session Version:** `v{ver}`")
        if st.button("🛑 Revoke Active Sessions", use_container_width=True,
                     disabled=not sel, key="btn_doc_revoke"):
            svc_revoke_doctor(doc["doctor_id"])
            st.warning(f"All bearer tokens invalidated for {doc['name']}.")
            st.rerun()


def render_patient_panel(pat: Optional[dict]) -> None:
    sel = pat is not None
    if sel:
        st.markdown(f"Selected Patient: **{pat['name']}** (`{pat['email']}`)")
    else:
        st.caption("👈 *Click a row above to select a patient for action.*")

    c1, c2, c3 = st.columns(3)
    with c1:
        failed = pat.get("failed_attempts", 0) if sel else 0
        locked = pat.get("is_locked", False) if sel else False
        st.markdown(f"**Lockout Control:** `{failed}/{MAX_LOGIN_ATTEMPTS}`")
        if st.button("🔓 Reset Failed Attempts", use_container_width=True,
                     disabled=not (sel and (failed > 0 or locked)),
                     key="btn_pat_reset"):
            svc_patient_reset_attempts(pat["patient_id"])
            st.success(f"Counter reset for {pat['name']}.")
            st.rerun()
    with c2:
        st.markdown("**Credential Dispatch:**")
        if st.button("🔑 Dispatch Secure Reset Link", use_container_width=True,
                     disabled=not sel, key="btn_pat_link"):
            svc_patient_reset_link(pat["patient_id"])
            st.success(f"Reset link sent to {pat['email']}.")
    with c3:
        st.markdown("**Access Freeze:**")
        active = pat.get("is_active", True) if sel else True
        if active:
            if st.button("🛑 Suspend Account", use_container_width=True,
                         disabled=not sel, key="btn_pat_suspend"):
                svc_patient_suspend(pat["patient_id"])
                st.warning(f"Account suspended for {pat['name']}.")
                st.rerun()
        else:
            if st.button("✅ Restore Access", use_container_width=True,
                         disabled=not sel, key="btn_pat_restore"):
                svc_patient_restore(pat["patient_id"])
                st.success(f"Access restored for {pat['name']}.")
                st.rerun()


def render_employee_panel(emp: Optional[dict]) -> None:
    sel = emp is not None
    if sel:
        st.markdown(f"Selected Staff: **{emp['name']}** (`{emp['emp_id']}`)")
    else:
        st.caption("👈 *Click a row above to select an employee for action.*")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📧 Dispatch Password Reset OTP", use_container_width=True,
                     disabled=not sel, key="emp_otp"):
            svc_employee_reset_otp(emp["emp_id"])
            st.success(f"Reset link sent to {emp['email']}.")
    with c2:
        status = emp.get("status", "Active") if sel else "Active"
        label = "Suspend Account Access" if status == "Active" else "Restore Account Access"
        if st.button(f"🛑 {label}", use_container_width=True,
                     type="secondary" if status == "Active" else "primary",
                     disabled=not sel, key="emp_toggle"):
            svc_employee_toggle_status(emp["emp_id"])
            st.rerun()


# ==============================================================================
# HEADER
# ==============================================================================
def render_header() -> None:
    with st.container(border=True):
        h1, h2 = st.columns([5.5, 4.5], vertical_alignment="center")
        with h1:
            st.markdown(f"""
            <div style="padding:4px 0;">
              <h3 style="margin:0;color:{T['text']};font-size:1.7rem;font-weight:800;
                   letter-spacing:-.3px;">
                {USER['name']}
                <span style="font-size:1.05rem;color:{T['text_mute']};font-weight:600;">
                  &nbsp;|&nbsp; {USER['role']}</span></h3>
              <div style="font-size:.92rem;color:{T['text_mute']};font-weight:600;
                   margin-top:4px;">
                ✔ Lucerna Medica Administration • {USER['email']}</div>
            </div>""", unsafe_allow_html=True)
        with h2:
            b, _, n, g = st.columns([2.5, .6, 1, 1.6])
            with b:
                st.markdown(
                    f'<div style="background:{T["chip_bg"]};color:{T["accent"]};'
                    f'padding:8px 0;border-radius:20px;font-weight:700;font-size:.85rem;'
                    f'text-align:center;margin-top:5px;border:1px solid {T["accent_soft"]};">'
                    f'🛡️ Superuser Access</div>', unsafe_allow_html=True)
            with n:
                with st.popover("🔔", use_container_width=True):
                    st.markdown("##### Notifications")
                    st.caption("No new alerts at this time.")
            with g:
                with st.popover("⚙️ Settings", use_container_width=True):
                    st.markdown("**Theme**")
                    t1, t2 = st.columns(2)
                    if t1.button("DARK", use_container_width=True, key="theme_dark",
                                 type="primary" if st.session_state.theme_mode == "dark" else "secondary"):
                        st.session_state.theme_mode = "dark"; st.rerun()
                    if t2.button("LIGHT", use_container_width=True, key="theme_light",
                                 type="primary" if st.session_state.theme_mode == "light" else "secondary"):
                        st.session_state.theme_mode = "light"; st.rerun()

                    st.markdown("**Night light**")
                    n1, n2 = st.columns(2)
                    if n1.button("ON", use_container_width=True, key="nl_on",
                                 type="primary" if st.session_state.night_light else "secondary"):
                        st.session_state.night_light = True; st.rerun()
                    if n2.button("OFF", use_container_width=True, key="nl_off",
                                 type="secondary" if st.session_state.night_light else "primary"):
                        st.session_state.night_light = False; st.rerun()
                    if st.session_state.night_light:
                        st.session_state.night_light_warmth = st.slider(
                            "Warmth Intensity", 5, 25,
                            st.session_state.night_light_warmth, key="nl_warmth")
                    st.divider()
                    st.markdown(f"<div style='text-align:center;color:{T['accent']};"
                                f"font-size:.85rem;margin-bottom:10px;'>{USER['email']}</div>",
                                unsafe_allow_html=True)


# ==============================================================================
# TAB: OVERVIEW
# ==============================================================================
def render_tab_overview() -> None:
    docs, pats, emps = st.session_state.doctors, st.session_state.patients, st.session_state.employees
    c_admin = sum(1 for e in emps if "Admin" in e.get("role", ""))
    c_doc, c_pat = len(docs), len(pats)
    total = max(c_admin + c_doc + c_pat, 1)
    doc_ver = sum(1 for d in docs if d.get("is_verified"))
    hipaa = sum(1 for p in pats if p.get("hipaa_consent"))
    hipaa_pct = int(hipaa / c_pat * 100) if c_pat else 0
    pending = sum(1 for p in pats if not p.get("is_verified"))
    locked = (sum(1 for d in docs if d.get("is_locked"))
              + sum(1 for p in pats if p.get("is_locked")))
    mfa_pct = int(sum(1 for d in docs if d.get("mfa_enrolled")) / c_doc * 100) if c_doc else 0

    with st.container(border=True):
        st.markdown(f"""
        <div style="margin-bottom:22px;">
          <h3 style="margin:0;font-size:1.3rem;font-weight:700;color:{T['text']};
               letter-spacing:-.2px;">System Telemetry &amp; Identity Metrics</h3>
          <p style="margin:5px 0 16px;font-size:.9rem;color:{T['text_mute']};">
            Live platform oversight, role distribution, and compliance monitoring.</p>
          <div style="height:1px;width:100%;background:{T['border']};"></div>
        </div>""", unsafe_allow_html=True)

        hero, grid = st.columns([1.3, 2], gap="medium")
        with hero:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, {T['card']} 0%, {T['card_soft']} 100%);
                 border:1px solid {T['border']};
                 border-radius:14px;padding:22px 24px;box-shadow:{T['shadow']};
                 height:295px;display:flex;flex-direction:column;justify-content:space-between;">
              <div>
                <div style="display:flex;justify-content:space-between;align-items:center;
                     margin-bottom:6px;">
                  <span style="font-size:.78rem;font-weight:700;color:{T['text_mute']};
                        letter-spacing:.8px;text-transform:uppercase;">Master Directory</span>
                  <span style="background:{T['chip_bg']};color:{T['accent']};font-size:.7rem;
                        font-weight:700;padding:3px 10px;border-radius:20px;
                        border:1px solid {T['accent_soft']};">LIVE REGISTRY</span></div>
                <div style="font-size:4.5rem;font-weight:800;color:{T['text']};line-height:1;
                     letter-spacing:-2px;margin:6px 0;">{total}</div>
                <div style="font-size:1rem;font-weight:600;color:{T['text_sub']};">
                  Total Provisioned Identities</div></div>
              <div style="font-size:.8rem;color:{T['text_mute']};font-weight:600;
                   border-top:1px solid {T['border']};padding-top:12px;">
                {c_doc} Clinicians &nbsp;·&nbsp; {c_pat} Patients &nbsp;·&nbsp; {c_admin} Admin</div>
            </div>""", unsafe_allow_html=True)

        with grid:
            r1a, r1b = st.columns(2, gap="medium")
            with r1a:
                st.markdown(metric_card("Doctors", str(c_doc),
                                        f"● {doc_ver}/{max(c_doc,1)} Verified", T["accent"]),
                            unsafe_allow_html=True)
            with r1b:
                st.markdown(metric_card("Patients", str(c_pat), f"◆ {hipaa_pct}% Consented",
                                        T["success"] if hipaa_pct >= 80 else T["warn"]),
                            unsafe_allow_html=True)
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            r2a, r2b = st.columns(2, gap="medium")
            with r2a:
                st.markdown(metric_card("System Admins", str(c_admin),
                                        "● Full Audit Privileges", T["info"]),
                            unsafe_allow_html=True)
            with r2b:
                st.markdown(metric_card("Active Sessions", str(total - locked),
                                        "◆ Valid Token Versions", T["success"]),
                            unsafe_allow_html=True)

        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
        g1, g2, g3, g4 = st.columns(4, gap="medium")
        with g1:
            st.markdown(metric_card("Pending Queue", str(pending), "Awaiting Verification",
                                    T["warn"] if pending else T["success"]),
                        unsafe_allow_html=True)
        with g2:
            st.markdown(metric_card("Account Lockouts", str(locked),
                                    f"⚠ {locked} Locked" if locked else "✓ 0 Flags",
                                    T["danger"] if locked else T["success"]),
                        unsafe_allow_html=True)
        with g3:
            st.markdown(metric_card("MFA Adoption", f"{mfa_pct}%", "Clinician 2FA Rate",
                                    T["success"] if mfa_pct == 100 else T["warn"]),
                        unsafe_allow_html=True)
        with g4:
            st.markdown(metric_card("Compliance Index", "100%", "HIPAA / DPA Compliant",
                                    T["success"]), unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("##### **INTAKE ACTIVITY OVER TIME**")
        st.caption("Activity tracking for Patients, Doctors, and Admins")
        df = pd.DataFrame(st.session_state.timeseries)
        if not df.empty:
            df = df.set_index("date")
        st.line_chart(df, height=340, use_container_width=True)

    health = st.session_state.health
    with st.container(border=True):
        st.markdown(f"<div style='text-align:right;color:{T['text_mute']};font-size:.85rem;'>"
                    f"Last Updated: {now_utc()}</div>", unsafe_allow_html=True)
        pc, cc = st.columns([1, 1.5], gap="large")
        with pc:
            st.markdown("#### Connection Pool Utilization")
            pool = health["pool"]
            active, mx = pool["active"], max(pool["max"], 1)
            util = int(active / mx * 100)
            level, color = (("Low", T["success"]) if active <= mx * .6
                            else ("Medium", T["warn"]) if active < mx * .9
                            else ("High", T["danger"]))
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=active,
                number={"suffix": f" / {mx}", "font": {"size": 36, "color": T["text"]}},
                title={"text": (f"<b>Active Connections</b><br>"
                                f"<span style='font-size:13px;color:{T['text_mute']};'>"
                                f"Utilization: {util}%</span> • "
                                f"<span style='font-size:13px;font-weight:bold;"
                                f"color:{color};'>{level} Load</span>"),
                       "font": {"size": 18, "color": T["text"]}},
                gauge={"axis": {"range": [0, mx], "ticks": "inside",
                                "tickfont": {"color": T["text_mute"], "size": 12}},
                       "bar": {"color": T["accent"]},
                       "bgcolor": "rgba(0,0,0,0)",
                       "bordercolor": T["border"],
                       "steps": [{"range": [0, mx * .6], "color": "rgba(52,211,153,0.10)"},
                                 {"range": [mx * .6, mx * .8], "color": "rgba(251,191,36,0.10)"},
                                 {"range": [mx * .8, mx], "color": "rgba(248,113,113,0.10)"}],
                       "threshold": {"line": {"color": T["danger"], "width": 3},
                                     "thickness": .8, "value": mx * .9}}))
            fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=15),
                              paper_bgcolor="rgba(0,0,0,0)",
                              font={"color": T["text_mute"]})
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False}, key="chart_pool_gauge")
        with cc:
            st.markdown("#### Cluster Monitor")
            st.dataframe(pd.DataFrame(health["nodes"]), use_container_width=True,
                         hide_index=True, height=180, key="tbl_nodes")
            st.markdown(f"""
            <div style="display:flex;justify-content:center;gap:12px;margin-top:14px;">
              <div style="display:flex;align-items:center;gap:8px;padding:6px 16px;
                   border:1px solid {T['border_strong']};border-radius:20px;
                   background:{T['card_soft']};font-size:.83rem;font-weight:600;
                   color:{T['text_sub']};">
                <span style="height:9px;width:9px;border-radius:50%;background:{T['success']};
                      display:inline-block;box-shadow:0 0 6px {T['success']};"></span>Active</div>
              <div style="display:flex;align-items:center;gap:8px;padding:6px 16px;
                   border:1px solid {T['border_strong']};border-radius:20px;
                   background:{T['card_soft']};font-size:.83rem;font-weight:600;
                   color:{T['text_sub']};">
                <span style="height:9px;width:9px;border-radius:50%;background:{T['warn']};
                      display:inline-block;box-shadow:0 0 6px {T['warn']};"></span>Idle</div>
              <div style="display:flex;align-items:center;gap:8px;padding:6px 16px;
                   border:1px solid {T['border_strong']};border-radius:20px;
                   background:{T['card_soft']};font-size:.83rem;font-weight:600;
                   color:{T['text_sub']};">
                <span style="height:9px;width:9px;border-radius:50%;background:{T['danger']};
                      display:inline-block;box-shadow:0 0 6px {T['danger']};"></span>Error</div>
            </div>""", unsafe_allow_html=True)

    db = health["db"]
    lat = db["latency_ms"]
    state, icon, color, sub = (("UP", "✔", T["success"], "SELECT 1 (Optimal)")
                               if db["up"] and lat <= 100 else
                               ("DEGRADED", "⚠", T["warn"], "SELECT 1 (Slow)")
                               if db["up"] else
                               ("DOWN", "✖", T["danger"], "Unreachable"))

    ca, cb = st.columns(2, gap="large")
    with ca:
        with st.container(border=True):
            st.markdown("##### 🛢️ **PostgreSQL Engine Health**")
            st.markdown(f"""
            <div style="text-align:center;margin:16px 0 10px;">
              <div style="font-size:2.2rem;font-weight:800;color:{color};
                   display:inline-flex;align-items:center;gap:8px;
                   text-shadow:0 0 18px {color}44;">
                <span>{icon}</span> {state}</div>
              <div style="font-size:.85rem;color:{T['text_mute']};font-weight:600;
                   margin-top:-2px;">({sub})</div></div>
            <div style="border-top:1px solid {T['border']};padding-top:14px;margin-top:14px;">
              <div style="display:flex;justify-content:space-between;font-size:.9rem;
                   margin-bottom:8px;"><span style="color:{T['text_mute']};">Latency:</span>
                <strong style="color:{color};">{lat} ms</strong></div>
              <div style="display:flex;justify-content:space-between;font-size:.9rem;">
                <span style="color:{T['text_mute']};">Recycle State:</span>
                <span style="color:{T['text_sub']};font-weight:600;">
                  {db['recycle_state']}</span></div></div>
            """, unsafe_allow_html=True)
    with cb:
        with st.container(border=True):
            st.markdown("##### 🌐 **HTTP Traffic & Error Distribution**")
            http = health["http"]
            vals = [http["2xx"], http["4xx"], http["5xx"]]
            if sum(vals) == 0:
                st.caption("No traffic recorded yet.")
            else:
                fig = go.Figure(data=[go.Pie(
                    labels=["2xx Success", "4xx Client", "5xx Server"], values=vals,
                    hole=.62, marker=dict(colors=[T["success"], T["warn"], T["danger"]]),
                    textinfo="percent", hoverinfo="label+value+percent",
                    textfont=dict(color=T["text"]))])
                fig.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10),
                                  legend=dict(orientation="h", y=-.1, x=.5, xanchor="center",
                                              font=dict(color=T["text_mute"])),
                                  paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False}, key="chart_http_donut")


# ==============================================================================
# TAB: DOCTORS
# ==============================================================================
DOCTOR_FORM_KEYS = ["doc_first_name", "doc_middle_name", "doc_last_name", "doc_address",
                    "doc_affiliation", "doc_prc", "doc_email", "doc_contact",
                    "em_name", "em_contact"]


def render_tab_doctors() -> None:
    if st.session_state.pop("_reset_doctor_form", False):
        for k in DOCTOR_FORM_KEYS:
            st.session_state.pop(k, None)
    if st.session_state.pop("_doctor_form_success", False):
        st.success("✅ Clinician account provisioned successfully.")

    with st.container(border=True):
        st.markdown(section_header("Provision Clinician Account",
                                   "Create a verified practitioner profile and register "
                                   "login credentials."), unsafe_allow_html=True)

        first = st.text_input("FIRST NAME*", placeholder="Enter first name", key="doc_first_name")
        last = st.text_input("LAST NAME*", placeholder="Enter last name", key="doc_last_name")
        r1, r2 = st.columns([1, 3])
        with r1:
            middle = st.text_input("MIDDLE NAME", placeholder="Optional", key="doc_middle_name")
        with r2:
            addr = st.text_input("ADDRESS*", placeholder="Residential or clinic address",
                                 key="doc_address")

        r1, r2, r3, r4 = st.columns([1.5, 2, 1.3, 1])
        with r1:
            spec = st.selectbox("SPECIALIZATION*", SPECIALIZATION_OPTIONS, key="doc_specialization")
        with r2:
            aff = st.text_input("CLINIC AFFILIATION", placeholder="e.g., Manila Doctors Hospital",
                                key="doc_affiliation")
        with r3:
            prc = st.text_input("PRC LICENSE*", placeholder="7 digits only",
                                max_chars=PRC_LEN, key="doc_prc")
        with r4:
            suffix = st.selectbox("SUFFIX*", SUFFIX_OPTIONS, key="doc_suffix")

        r1, r2 = st.columns(2)
        with r1:
            email = st.text_input("EMAIL*", placeholder="strictly @gmail.com", key="doc_email")
            if email and not is_valid_gmail(email):
                st.error("⛔ Must be a valid @gmail.com address.")
        with r2:
            contact = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX",
                                    max_chars=13, key="doc_contact")

        st.markdown("<div style='height:18px;'></div>#### **CONTACT IN CASE OF EMERGENCY**",
                    unsafe_allow_html=True)
        em_name = st.text_input("FULL NAME*", placeholder="Emergency contact full name",
                                key="em_name")
        em_contact = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX",
                                   max_chars=13, key="em_contact")
        em_rel = st.selectbox("RELATION*", RELATION_OPTIONS, key="em_relation")

        st.markdown("<div style='height:18px;'></div>"
                    "#### **CREDENTIAL DISPATCH & SECURITY CONTROLS**",
                    unsafe_allow_html=True)
        s1, s2, s3 = st.columns([1.5, 1.5, 1.2])
        with s1:
            send_email = st.toggle("Automated Onboarding Email", value=True, key="doc_send_email")
        with s2:
            require_mfa = st.toggle("Enforce MFA on First Login", value=True, key="doc_require_mfa")
        with s3:
            cred_ttl = st.selectbox("Credential TTL", CRED_TTL_OPTIONS, key="doc_cred_ttl")

        st.divider()
        submitted = st.button("Submit Provisioning", type="primary",
                              use_container_width=True, key="doc_submit")

    if submitted:
        errors = []
        if not first.strip() or not is_valid_name(first): errors.append("Valid first name required.")
        if not last.strip() or not is_valid_name(last): errors.append("Valid last name required.")
        if middle and not is_valid_name(middle): errors.append("Middle name invalid.")
        if not addr.strip(): errors.append("Address required.")
        prc_d = normalize_prc(prc)
        if not prc_d: errors.append(f"PRC License must be exactly {PRC_LEN} digits.")
        if not is_valid_gmail(email): errors.append("Valid @gmail.com address required.")
        cn = normalize_phone(contact)
        if not cn: errors.append("Contact Number must be 11 digits.")
        if not em_name.strip(): errors.append("Emergency contact name required.")
        ecn = normalize_phone(em_contact)
        if not ecn: errors.append("Emergency contact must be 11 digits.")
        if prc_d and any(d["license_number"] == f"PRC {prc_d}" for d in st.session_state.doctors):
            errors.append(f"License Conflict: PRC {prc_d} already registered.")
        if email and any(d["email"].lower() == email.strip().lower()
                         for d in st.session_state.doctors):
            errors.append(f"Email Conflict: {email.strip().lower()} already in use.")

        if errors:
            for e in errors:
                st.error(f"❌ {e}")
            return

        svc_create_doctor({"first_name": first.strip().title(),
                           "middle_name": middle.strip().title() or None,
                           "last_name": last.strip().title(), "address": addr.strip(),
                           "specialization": spec,
                           "hospital_affiliation": aff.strip() or "Lucerna Medica Main Clinic",
                           "prc_license": prc_d, "suffix": suffix,
                           "email": email.strip().lower(), "contact_number": cn,
                           "emergency_contact": {"name": em_name.strip().title(),
                                                 "contact_number": ecn, "relation": em_rel},
                           "send_onboarding_email": bool(send_email),
                           "enforce_mfa": bool(require_mfa), "credential_ttl": cred_ttl})
        st.session_state["_reset_doctor_form"] = True
        st.session_state["_doctor_form_success"] = True
        st.rerun()

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("### Clinician Database & Directory")
        st.caption("Inspect, filter, and manage provisioned clinical accounts.")

        docs = st.session_state.doctors
        if not docs:
            st.info("No clinicians provisioned yet.")
        else:
            df = pd.DataFrame(docs)
            f1, f2, f3 = st.columns([2.5, 2, 1.5])
            with f1:
                search = st.text_input("Search", placeholder="Name, license #, or email...",
                                       label_visibility="collapsed", key="doc_search")
            with f2:
                spec_f = st.multiselect("Specialization", SPECIALIZATION_OPTIONS,
                                        placeholder="All Specialties",
                                        label_visibility="collapsed", key="doc_spec_filter")
            with f3:
                st_f = st.radio("Status", ["All", "Verified", "Pending"], horizontal=True,
                                label_visibility="collapsed", key="doc_status_filter")

            flt = df.copy()
            if search:
                q = search.strip().lower()
                m = (flt["name"].fillna("").str.lower().str.contains(q, regex=False)
                     | flt["license_number"].fillna("").str.lower().str.contains(q, regex=False)
                     | flt["email"].fillna("").str.lower().str.contains(q, regex=False))
                flt = flt[m]
            if spec_f: flt = flt[flt["specialization"].isin(spec_f)]
            if st_f == "Verified": flt = flt[flt["is_verified"] == True]      # noqa: E712
            elif st_f == "Pending": flt = flt[flt["is_verified"] == False]    # noqa: E712

            disp = flt.copy()
            disp["status_badge"] = disp["is_verified"].map(lambda v: "🟢 Verified" if v else "🟡 Pending")
            disp["lock_badge"] = disp["is_locked"].map(lambda l: "🔒 Locked" if l else "🟢 Normal")

            ev = st.dataframe(
                disp[["name", "license_number", "specialization", "contact_number",
                      "email", "hospital_affiliation", "status_badge", "lock_badge"]],
                use_container_width=True, hide_index=True, on_select="rerun",
                selection_mode="single-row", key="tbl_clinicians", height=240,
                column_config={
                    "name": st.column_config.TextColumn("Clinician Name", width="medium"),
                    "license_number": st.column_config.TextColumn("License", width="small"),
                    "specialization": st.column_config.TextColumn("Specialization", width="medium"),
                    "contact_number": st.column_config.TextColumn("Phone", width="small"),
                    "email": st.column_config.TextColumn("Email", width="medium"),
                    "hospital_affiliation": st.column_config.TextColumn("Affiliation", width="medium"),
                    "status_badge": st.column_config.TextColumn("Verification", width="small"),
                    "lock_badge": st.column_config.TextColumn("Access", width="small")})

            rows = ev.selection.rows
            if rows:
                try: st.session_state.selected_doctor_id = disp.iloc[rows[0]]["doctor_id"]
                except (IndexError, KeyError): st.session_state.pop("selected_doctor_id", None)

            sel_id = st.session_state.get("selected_doctor_id")
            target = next((d for d in docs if d.get("doctor_id") == sel_id), None)
            st.divider()
            st.markdown("##### **Account Governance & Security Controls**")
            render_clinician_panel(target)

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("### Identity & Security Audit Trail")
        st.caption("Immutable system log of authentication and credential events.")
        logs = st.session_state.doctor_audit_logs
        if not logs:
            st.info("No audit events recorded.")
        else:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True,
                         height=240, key="tbl_doctor_audit",
                         column_config={
                             "timestamp": st.column_config.TextColumn("Timestamp (UTC)", width="medium"),
                             "target": st.column_config.TextColumn("Clinician", width="medium"),
                             "event_type": st.column_config.TextColumn("Event", width="medium"),
                             "actor": st.column_config.TextColumn("Triggered By", width="medium"),
                             "ip_address": st.column_config.TextColumn("Client IP", width="small"),
                             "details": st.column_config.TextColumn("Payload", width="large")})


# ==============================================================================
# TAB: PATIENTS
# ==============================================================================
def render_tab_patients() -> None:
    pats = st.session_state.patients
    df = pd.DataFrame(pats) if pats else pd.DataFrame()

    with st.container(border=True):
        st.markdown("### Pending Verification Queue")
        st.caption("Newly registered patients awaiting activation.")
        pending = df[df["is_verified"] == False].reset_index(drop=True) if not df.empty else df  # noqa: E712

        if pending.empty:
            st.info("Queue is clear. No pending verifications.")
        else:
            ev = st.dataframe(
                pending[["name", "email", "contact_number", "registered_at",
                         "pending_method", "dispatch_count"]],
                use_container_width=True, hide_index=True, on_select="rerun",
                selection_mode="single-row", key="tbl_pending", height=180,
                column_config={"name": "Full Name", "email": "Email",
                               "contact_number": "Contact", "registered_at": "Registered At",
                               "pending_method": "Pending Method", "dispatch_count": "Dispatches"})
            rows = ev.selection.rows
            target = None
            if rows:
                try: target = pending.iloc[rows[0]].to_dict()
                except IndexError: target = None

            if target:
                st.markdown(f"Selected: **{target['name']}** (`{target['email']}`)")
            else:
                st.caption("👈 *Select a patient above to take action.*")

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🔄 Resend Link / OTP", use_container_width=True,
                             disabled=target is None, key="btn_pend_resend"):
                    svc_patient_redispatch(target["patient_id"])
                    st.success(f"Token re-sent to {target['email']}.")
                    st.rerun()
            with c2:
                if st.button("✅ Manual Authorization", use_container_width=True,
                             disabled=target is None, key="btn_pend_auth"):
                    svc_patient_verify(target["patient_id"])
                    st.success(f"Account for {target['name']} verified.")
                    st.rerun()
            with c3:
                if st.button("🗑️ Purge Expired Requests", use_container_width=True,
                             key="btn_pend_purge"):
                    n = svc_purge_pending()
                    st.warning(f"Purged {n} unverified registration(s).")
                    st.rerun()

    with st.container(border=True):
        st.markdown("### Master Patient Directory")
        st.caption("Manage active accounts, HIPAA compliance, and access states.")
        if df.empty:
            st.info("No patients registered.")
            return

        f1, f2, f3 = st.columns([2.5, 1.5, 1.5])
        with f1:
            search = st.text_input("Search", placeholder="Name, email, or phone…",
                                   label_visibility="collapsed", key="pat_search")
        with f2:
            stf = st.radio("Status", ["All", "Active", "Pending", "Suspended"],
                           horizontal=True, label_visibility="collapsed", key="pat_status_filter")
        with f3:
            hf = st.radio("HIPAA", ["All", "Consented", "Pending"], horizontal=True,
                          label_visibility="collapsed", key="pat_hipaa_filter")

        flt = df.copy()
        if search:
            q = search.strip().lower()
            m = (flt["name"].fillna("").str.lower().str.contains(q, regex=False)
                 | flt["email"].fillna("").str.lower().str.contains(q, regex=False)
                 | flt["contact_number"].fillna("").str.contains(q, regex=False))
            flt = flt[m]
        if stf == "Active":
            flt = flt[(flt["is_active"] == True) & (flt["is_locked"] == False)]   # noqa: E712
        elif stf == "Pending":
            flt = flt[flt["is_verified"] == False]                                # noqa: E712
        elif stf == "Suspended":
            flt = flt[(flt["is_active"] == False) | (flt["is_locked"] == True)]   # noqa: E712
        if hf == "Consented": flt = flt[flt["hipaa_consent"] == True]             # noqa: E712
        elif hf == "Pending": flt = flt[flt["hipaa_consent"] == False]            # noqa: E712

        disp = flt.copy()
        disp["hipaa_badge"] = disp["hipaa_consent"].map(
            lambda v: "📝 Consented" if v else "⏳ Pending")

        def _state(r):
            return ("🟡 Pending" if not r["is_verified"] else
                    "🔒 Locked" if r["is_locked"] else
                    "🔴 Suspended" if not r["is_active"] else "🟢 Active")

        disp["account_state"] = disp.apply(_state, axis=1)

        ev = st.dataframe(
            disp[["name", "email", "contact_number", "dob", "hipaa_badge", "account_state"]],
            use_container_width=True, hide_index=True, on_select="rerun",
            selection_mode="single-row", key="tbl_patients", height=240,
            column_config={"name": "Patient Name", "email": "Email",
                           "contact_number": "Contact Phone", "dob": "Date of Birth",
                           "hipaa_badge": "HIPAA Status", "account_state": "Account State"})

        rows = ev.selection.rows
        if rows:
            try: st.session_state.selected_patient_id = disp.iloc[rows[0]]["patient_id"]
            except (IndexError, KeyError): st.session_state.pop("selected_patient_id", None)

        sel_id = st.session_state.get("selected_patient_id")
        target = next((p for p in pats if p.get("patient_id") == sel_id), None)
        st.divider()
        st.markdown("##### **Account Governance Panel**")
        render_patient_panel(target)

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("### Patient IAM & Compliance Audit Trail")
        st.caption("Immutable log of security operations and HIPAA consent milestones.")
        logs = st.session_state.patient_audit_logs
        if not logs:
            st.info("No audit events recorded.")
        else:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True,
                         height=240, key="tbl_patient_audit",
                         column_config={"timestamp": "Timestamp (UTC)", "target": "Patient",
                                        "event_type": "Event", "actor": "Triggered By",
                                        "ip_address": "Client IP",
                                        "details": st.column_config.TextColumn(
                                            "Payload", width="large")})


# ==============================================================================
# TAB: ADMIN ACCOUNTS
# ==============================================================================
def render_tab_admin() -> None:
    with st.container(border=True):
        st.markdown("### Admin Security Settings")
        st.caption("Manage your own administrative credentials.")
        a1, a2 = st.columns([1, 1], gap="large")

        with a1:
            st.markdown("##### Update Password")
            with st.form("pw_change_form", clear_on_submit=True):
                cur = st.text_input("Current Password", type="password", key="pw_current")
                pc1, pc2 = st.columns(2)
                with pc1:
                    new = st.text_input("New Password", type="password", key="pw_new")
                with pc2:
                    confirm = st.text_input("Confirm Password", type="password", key="pw_confirm")
                if st.form_submit_button("Update Admin Password", type="primary",
                                         use_container_width=True):
                    errs = []
                    if not cur: errs.append("Current password required.")
                    if len(new) < PASSWORD_MIN_LEN or not PASSWORD_RE.match(new):
                        errs.append(f"New password must be ≥ {PASSWORD_MIN_LEN} chars with "
                                    "letters, digits, and a symbol.")
                    if new != confirm: errs.append("New passwords do not match.")
                    if errs:
                        for e in errs: st.error(f"❌ {e}")
                    else:
                        svc_change_password(cur, new)
                        st.success("✅ Administrative password updated.")

        with a2:
            st.markdown("##### Administrative Profile")
            st.text_input("Registered Name", value=USER["name"], disabled=True, key="prof_name")
            st.text_input("Institutional Email", value=USER["email"], disabled=True, key="prof_email")
            st.markdown(f"**Current Role:** `<{USER['role']}>`")
            st.markdown(f"**MFA Status:** <span style='color:{T['success']};font-weight:bold;'>"
                        "🟢 Active (Authenticator App)</span>", unsafe_allow_html=True)

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("##### Provision New Admin Account")
        with st.form("new_admin_form", clear_on_submit=True):
            f = st.text_input("FIRST NAME*", key="af_first")
            l = st.text_input("LAST NAME*", key="af_last")
            r1, r2 = st.columns([1, 3])
            with r1:
                mid = st.text_input("MIDDLE NAME", placeholder="Optional", key="af_middle")
            with r2:
                addr = st.text_input("ADDRESS*", key="af_address")

            r1, r2, r3, r4 = st.columns([1.5, 2, 1.3, 1])
            with r1:
                role = st.selectbox("ROLE*", ADMIN_ROLE_OPTIONS, key="af_role")
            with r2:
                dept = st.text_input("DEPARTMENT", value="Administration", key="af_department")
            with r3:
                code = st.text_input("ADMIN CODE*", placeholder="e.g., ADM-001", key="af_code")
            with r4:
                sfx = st.selectbox("SUFFIX*", SUFFIX_OPTIONS, key="af_suffix")

            r1, r2 = st.columns(2)
            with r1:
                em = st.text_input("EMAIL*", placeholder="name@lucernamedica.com", key="af_email")
            with r2:
                ph = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX",
                                   max_chars=13, key="af_contact")

            st.markdown("<div style='height:18px;'></div>"
                        "#### **CONTACT IN CASE OF EMERGENCY**", unsafe_allow_html=True)
            em_name = st.text_input("FULL NAME*", key="af_em_name")
            e1, e2 = st.columns(2)
            with e1:
                em_ph = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX",
                                      max_chars=13, key="af_em_contact")
            with e2:
                em_rel = st.selectbox("RELATION*", RELATION_OPTIONS, key="af_em_relation")

            st.markdown("<div style='height:18px;'></div>"
                        "#### **CREDENTIAL DISPATCH & SECURITY CONTROLS**",
                        unsafe_allow_html=True)
            s1, s2, s3 = st.columns([1.5, 1.5, 1.2])
            with s1:
                snd = st.toggle("Onboarding Email", value=True, key="af_send_email")
            with s2:
                mfa = st.toggle("Enforce MFA", value=True, key="af_require_mfa")
            with s3:
                ttl = st.selectbox("Credential TTL", CRED_TTL_OPTIONS, key="af_cred_ttl")

            st.divider()
            sub = st.form_submit_button("Create Admin Account", type="primary",
                                        use_container_width=True)

        if sub:
            errs = []
            if not f.strip() or not is_valid_name(f): errs.append("Valid first name required.")
            if not l.strip() or not is_valid_name(l): errs.append("Valid last name required.")
            if not addr.strip(): errs.append("Address required.")
            if not code.strip(): errs.append("Admin Code required.")
            if not is_valid_inst_email(em): errs.append("Valid institutional email required.")
            cn = normalize_phone(ph)
            if not cn: errs.append("Contact Number must be 11 digits.")
            if not em_name.strip(): errs.append("Emergency contact name required.")
            ecn = normalize_phone(em_ph)
            if not ecn: errs.append("Emergency contact number must be 11 digits.")
            if any(e["emp_id"] == code.strip() for e in st.session_state.employees):
                errs.append(f"Admin Code Conflict: `{code.strip()}` already exists.")

            if errs:
                for e in errs: st.error(f"❌ {e}")
            else:
                svc_create_employee({"emp_id": code.strip(),
                                     "first_name": f.strip().title(),
                                     "middle_name": mid.strip().title() or None,
                                     "last_name": l.strip().title(), "address": addr.strip(),
                                     "role": role, "department": dept.strip() or "Administration",
                                     "suffix": sfx, "email": em.strip().lower(),
                                     "contact_number": cn,
                                     "emergency_contact": {"name": em_name.strip().title(),
                                                           "contact_number": ecn,
                                                           "relation": em_rel},
                                     "send_onboarding_email": bool(snd),
                                     "enforce_mfa": bool(mfa), "credential_ttl": ttl})
                st.success(f"✅ Provisioned admin `{code.strip()}` successfully!")
                st.rerun()

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("##### Staff & Admin Directory")
        emps = st.session_state.employees
        if not emps:
            st.info("No staff accounts found.")
            return

        df = pd.DataFrame(emps)
        df["status_badge"] = df["status"].map(
            lambda s: "🟢 Active" if s == "Active" else "🔴 Suspended")

        ev = st.dataframe(df[["emp_id", "name", "role", "email", "status_badge"]],
                          use_container_width=True, hide_index=True, on_select="rerun",
                          selection_mode="single-row", key="tbl_employees", height=220,
                          column_config={"emp_id": "Emp ID", "name": "Name", "role": "Role",
                                         "email": "Email", "status_badge": "Status"})

        rows = ev.selection.rows
        if rows:
            try: st.session_state.selected_employee_id = df.iloc[rows[0]]["emp_id"]
            except (IndexError, KeyError): st.session_state.pop("selected_employee_id", None)

        sel_id = st.session_state.get("selected_employee_id")
        target = next((e for e in emps if e.get("emp_id") == sel_id), None)
        st.divider()
        st.markdown("##### 🔑 Credential Management")
        render_employee_panel(target)

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("### Staff Audit Trail")
        st.caption("Immutable log of staff account operations.")
        logs = st.session_state.employee_audit_logs
        if not logs:
            st.info("No audit events recorded.")
        else:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True,
                         height=240, key="tbl_employee_audit")


# ==============================================================================
# MAIN
# ==============================================================================
def main() -> None:
    _, col, _ = st.columns([5, 90, 5], gap="small")
    with col:
        render_header()
        tabs = st.tabs(["Overview", "Doctor Management", "Patient Management", "Admin accounts"])
        with tabs[0]: render_tab_overview()
        with tabs[1]: render_tab_doctors()
        with tabs[2]: render_tab_patients()
        with tabs[3]: render_tab_admin()


if __name__ == "__main__":
    main()