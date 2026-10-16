import os
import re
import sys

import pandas as pd
import streamlit as st

# 1. Paths: frontend/ (for 'views') and the project root (for 'frontend.*')
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.abspath(os.path.join(_HERE, "..")), os.path.abspath(os.path.join(_HERE, "..", ".."))):
    if _p not in sys.path:
        sys.path.append(_p)

try:
    from styles import basetab_layout_, render_top_navbar, show_api_error, flash, show_flash
except ImportError:
    from views.styles import basetab_layout_, render_top_navbar, show_api_error, flash, show_flash

from frontend import cdss_logic as L
from frontend import docpage_api

# ==============================================================================
# PAGE CONFIGURATION & THEME INITIALIZATION
# ==============================================================================
st.set_page_config(layout="wide", page_title="HEART | Admin Portal")
basetab_layout_()

if not st.session_state.get("token"):
    st.warning("Session expired. Please log in.")
    st.stop()

# ==============================================================================
# CALLBACKS & VALIDATION HELPERS
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
    return bool(re.match(r"^\d{4}-\d{3}-\d{4}$", (text or "").strip()))


def is_valid_gmail(text: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", (text or "").strip()))


def card(title, value, note, note_color="#0f172a", height=138):
    st.markdown(f"""
    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: {height}px; display: flex; flex-direction: column; justify-content: space-between;">
        <div style="font-size: 0.95rem; font-weight: 600; color:#0f172a;">{title}</div>
        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1; color:#0f172a;">{value}</div>
        <div style="font-size: 0.85rem; font-weight: 600; color: {note_color};">{note}</div>
    </div>""", unsafe_allow_html=True)


def accounts_table(rows):
    st.dataframe(pd.DataFrame([{
        "User ID": r.get("user_id"), "Username": r.get("username"), "Role": r.get("role"),
        "Access": "🔒 Locked" if r.get("is_locked") else "🟢 Normal", "Created": r.get("created_at"),
    } for r in rows]), hide_index=True, use_container_width=True)


# ==============================================================================
# GLOBALS
# ==============================================================================
SPECIALIZATION_OPTIONS = ["General Physician", "Internal Medicine", "Cardiology", "Pulmonology", "Psychiatry"]
SUFFIX_OPTIONS = ["None", "MD", "PhD", "DO", "MD, PhD", "Jr.", "Sr.", "III"]
RELATION_OPTIONS = ["Mother", "Father", "Spouse", "Son", "Daughter", "Brother", "Sister", "Other"]
DOC_FORM_KEYS = ["doc_username", "doc_password", "doc_first_name", "doc_middle_name", "doc_last_name", "doc_address",
                 "doc_affiliation", "doc_prc", "doc_email", "doc_contact", "em_name", "em_contact"]

for key in DOC_FORM_KEYS:
    st.session_state.setdefault(key, "")
st.session_state.setdefault("provisioned_doctors", [])  # doctors created in this session, for quick verify

profile = st.session_state.get("user_profile") or {}
user_name = f"{profile.get('first_name', 'System')} {profile.get('last_name', 'Admin')}".strip()
user_role = st.session_state.get("user_role", "ADMIN")
user_email = profile.get("email", "")

# ==============================================================================
# LIVE DATA (GET /admin/directory)
# ==============================================================================
directory_resp = docpage_api.get_directory()
accounts = L.directory_rows(directory_resp)
doctors = [a for a in accounts if str(a.get("role", "")).upper() == "DOCTOR"]
patients = [a for a in accounts if str(a.get("role", "")).upper() == "PATIENT"]
admins = [a for a in accounts if str(a.get("role", "")).upper() in ("ADMIN", "SYSTEM_ADMIN")]
locked = [a for a in accounts if a.get("is_locked")]

_, col_main, _ = st.columns([5, 90, 5], gap="small")

with col_main:
    render_top_navbar(user_name=user_name, user_role=user_role, user_email=user_email,
                      badge_label="Admin Access", badge_color="#0ea5e9")
    show_flash()
    tab_Overview, tab_form, tab_patient, tab_Admin = st.tabs(["Overview", "Doctor Management", "Patient Management", "Admin accounts"])

    # --------------------------------------------------------------------------
    # TAB 1: OVERVIEW (only numbers the backend reports)
    # --------------------------------------------------------------------------
    with tab_Overview:
        st.write("")
        if not L.is_ok(directory_resp):
            show_api_error(directory_resp)

        with st.container(border=True):
            st.markdown("### Accounts")
            c1, c2, c3, c4 = st.columns(4, gap="medium")
            with c1:
                card("Doctors", len(doctors), "Provisioned clinicians", "#007979")
            with c2:
                card("Patients", len(patients), "Self-registered", "#0284c7")
            with c3:
                card("Admins", len(admins), "Directory and provisioning", "#64748b")
            with c4:
                card("Locked accounts", len(locked), "Too many failed logins" if locked else "✔ None locked",
                     "#ef4444" if locked else "#10b981")

        with st.container(border=True):
            st.markdown("### 🔓 Locked accounts")
            if not locked:
                st.caption("No account is locked.")
            for acc in locked:
                l1, l2 = st.columns([4, 1], vertical_alignment="center")
                l1.markdown(f"**{acc.get('username')}** · {acc.get('role')} · user #{acc.get('user_id')}")
                if l2.button("Unlock", key=f"unlock_{acc.get('user_id')}", use_container_width=True):
                    resp = docpage_api.unlock_user(acc.get("user_id"))
                    if L.is_ok(resp):
                        flash("success", f"Unlocked {acc.get('username')}.")
                        st.rerun()
                    show_api_error(resp)

        g1, g2 = st.columns(2, gap="large")
        with g1:
            with st.container(border=True):
                st.markdown("##### 🛢️ Server and database")
                health = docpage_api.get_health()
                if L.is_ok(health):
                    st.success("Server reachable · " + ", ".join(f"{k}: {v}" for k, v in L.strip_meta(health).items()))
                else:
                    st.warning("Health check not available. " + L.friendly_error(health))
        with g2:
            with st.container(border=True):
                st.markdown("##### 🧠 Disease models")
                models_resp = docpage_api.get_models_status()
                rows = L.models_status_rows(models_resp)
                if not L.is_ok(models_resp):
                    show_api_error(models_resp)
                for r in rows:
                    st.markdown(f"{'🟢' if r['loaded'] else '🔴'} **{L.MODALITY_LABELS[r['disease']]}** · "
                                f"{r['model_version'] or 'not loaded'}"
                                f"{' · ' + (r['problem'] or '; '.join(r['warnings'])) if (r['problem'] or r['warnings']) else ''}")
                if st.button("Reload model files", key="reload_models_btn"):
                    resp = docpage_api.reload_models()
                    if L.is_ok(resp):
                        flash("success", f"Models reloaded (audit {resp.get('audit_id')}).")
                        st.rerun()
                    show_api_error(resp)

    # --------------------------------------------------------------------------
    # TAB 2: DOCTOR MANAGEMENT (POST /admin/provision, POST /admin/doctors/<id>/verify)
    # --------------------------------------------------------------------------
    with tab_form:
        if st.session_state.get("trigger_form_clear"):
            for key in DOC_FORM_KEYS:
                st.session_state[key] = ""
                st.session_state[f"{key}_invalid"] = False
            st.session_state.trigger_form_clear = False

        with st.container(border=True):
            st.markdown("""
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0; font-size: 1.45rem; font-weight: 700; letter-spacing: -0.3px;">Provision Clinician Account</h3>
                <p style="margin: 4px 0 14px 0; font-size: 0.95rem;">Creates the doctor's login. They can log in only after you verify them below.</p>
                <div style="height: 1px; width: 100%; background-color: rgba(148, 163, 184, 0.2); margin-bottom: 18px;"></div>
            </div>
            """, unsafe_allow_html=True)

            a1, a2 = st.columns(2)
            with a1:
                username = st.text_input("USERNAME*", placeholder="Login name for the doctor", key="doc_username")
            with a2:
                temp_password = st.text_input("TEMPORARY PASSWORD*", type="password", placeholder="At least 8 characters",
                                              key="doc_password")

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

            row4_col1, row4_col2, row4_col3 = st.columns([1.5, 2, 1.3])
            with row4_col1:
                specialization = st.selectbox("SPECIALIZATION*", options=SPECIALIZATION_OPTIONS, key="doc_specialization")
            with row4_col2:
                hospital_affiliation = st.text_input("CLINIC AFFILIATION", placeholder="e.g., Manila Doctors Hospital", key="doc_affiliation")
            with row4_col3:
                prc_license_raw = st.text_input("PRC LICENSE*", placeholder="7 digits only", max_chars=7, key="doc_prc", on_change=clean_prc_license, args=("doc_prc",))
                if st.session_state.get("doc_prc_invalid"): st.error("⛔ Numbers only.")

            row5_col1, row5_col2 = st.columns([1, 1])
            with row5_col1:
                email = st.text_input("EMAIL*", placeholder="strictly @gmail.com", key="doc_email")
                if email and not is_valid_gmail(email):
                    st.error("⛔ Must be a valid Gmail address.")
            with row5_col2:
                contact_number = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="doc_contact", on_change=format_phone_number, args=("doc_contact",))
                if st.session_state.get("doc_contact_invalid"):
                    st.error("⛔ Numbers only.")

            st.markdown("#### **CONTACT IN CASE OF EMERGENCY**")
            e1, e2, e3 = st.columns([2, 1.5, 1])
            with e1:
                emergency_name = st.text_input("FULL NAME*", placeholder="Enter emergency contact's full name", key="em_name", on_change=clean_alpha_input, args=("em_name",))
                if st.session_state.get("em_name_invalid"): st.error("⛔ Letters only.")
            with e2:
                emergency_contact = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="em_contact", on_change=format_phone_number, args=("em_contact",))
                if st.session_state.get("em_contact_invalid"): st.error("⛔ Numbers only.")
            with e3:
                emergency_relation = st.selectbox("RELATION*", RELATION_OPTIONS, key="doc_em_relation")

            st.divider()
            submit_btn = st.button("Submit Provisioning", type="primary", use_container_width=True)

        if submit_btn:
            errors = []
            if len(temp_password or "") < 8: errors.append("Temporary password must be at least 8 characters.")
            if len(prc_license_raw or "") != 7: errors.append("PRC License must be exactly 7 digits.")
            if not is_valid_gmail(email): errors.append("Valid Gmail address is required.")
            if not is_valid_phone_format(contact_number): errors.append("Doctor Contact Number must be exactly 11 digits.")
            if not is_valid_phone_format(emergency_contact): errors.append("Emergency Contact Number must be exactly 11 digits.")
            payload, missing = L.build_provision_payload({
                "username": username, "password": temp_password, "first_name": first_name, "last_name": last_name,
                "address": address, "specialization": specialization,
                "license_number": f"PRC {prc_license_raw.strip()}" if prc_license_raw else "",
                "contact_number": contact_number, "email": (email or "").strip().lower(),
                "emergency_contact_name": emergency_name, "emergency_contact_number": emergency_contact,
                "emergency_relation": emergency_relation, "middle_name": middle_name,
                "hospital_affiliation": hospital_affiliation,
            })
            if missing:
                errors.append("Required: " + ", ".join(m.replace("_", " ") for m in missing) + ".")
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                resp = docpage_api.provision_doctor(payload)
                if L.is_ok(resp):
                    st.session_state["provisioned_doctors"].append({
                        "doctor_id": resp.get("doctor_id"), "user_id": resp.get("user_id"),
                        "username": payload["username"], "name": f"Dr. {payload['first_name']} {payload['last_name']}",
                        "verified": False})
                    st.session_state.trigger_form_clear = True
                    flash("success", f"✅ Created **{payload['username']}** (doctor #{resp.get('doctor_id')}). "
                                     "Verify them below so they can log in.")
                    st.rerun()
                show_api_error(resp)

        with st.container(border=True):
            st.markdown("### Verify a doctor")
            st.caption("A doctor can't log in until verified (403 ACCOUNT_PENDING_VERIFICATION).")
            for doc in [d for d in st.session_state["provisioned_doctors"] if not d.get("verified")]:
                v1, v2 = st.columns([4, 1], vertical_alignment="center")
                v1.markdown(f"**{doc['name']}** · {doc['username']} · doctor #{doc['doctor_id']}")
                if v2.button("Verify", key=f"verify_doc_{doc['doctor_id']}", use_container_width=True):
                    resp = docpage_api.verify_doctor(doc["doctor_id"])
                    if L.is_ok(resp):
                        doc["verified"] = True
                        flash("success", f"{doc['name']} can now log in.")
                        st.rerun()
                    show_api_error(resp)
            m1, m2 = st.columns([4, 1], vertical_alignment="bottom")
            doc_id = m1.number_input("Doctor ID (from provisioning)", min_value=1, step=1, value=None, key="verify_doc_id")
            if m2.button("Verify", key="verify_doc_btn", use_container_width=True, disabled=doc_id is None):
                resp = docpage_api.verify_doctor(int(doc_id))
                if L.is_ok(resp):
                    flash("success", f"Doctor #{int(doc_id)} verified.")
                    st.rerun()
                show_api_error(resp)

        with st.container(border=True):
            st.markdown("### Clinician accounts")
            if doctors:
                accounts_table(doctors)
            else:
                st.info("No doctor accounts yet.")

    # --------------------------------------------------------------------------
    # TAB 3: PATIENT MANAGEMENT
    # --------------------------------------------------------------------------
    with tab_patient:
        with st.container(border=True):
            st.markdown("### Patient accounts")
            st.caption("Patients register themselves (HIPAA/DPA consent is required at sign-up). "
                       "Locked accounts are unlocked from the Overview tab.")
            if patients:
                accounts_table(patients)
            else:
                st.info("No patient accounts yet.")
            st.caption("Deactivating a patient arrives with backend batch 4 (soft delete).")

    # --------------------------------------------------------------------------
    # TAB 4: ADMIN ACCOUNTS & OWN SETTINGS
    # --------------------------------------------------------------------------
    with tab_Admin:
        with st.container(border=True):
            st.markdown("### Admin Security Settings")
            adm_col1, adm_col2 = st.columns([1, 1], gap="large")
            with adm_col1:
                st.markdown("##### Update Password")
                with st.form("account_tab_password_change_form", clear_on_submit=True):
                    current_pw = st.text_input("Current Password", type="password", placeholder="Enter current password")
                    new_pw_col1, new_pw_col2 = st.columns(2)
                    with new_pw_col1: new_pw = st.text_input("New Password", type="password", placeholder="Enter new password")
                    with new_pw_col2: confirm_pw = st.text_input("Confirm Password", type="password", placeholder="Re-type new password")
                    if st.form_submit_button("Update Admin Password", type="primary", use_container_width=True):
                        if not current_pw or not new_pw or not confirm_pw:
                            st.error("❌ Please fill in all password fields.")
                        elif new_pw != confirm_pw:
                            st.error("❌ New passwords do not match.")
                        elif len(new_pw) < 8:
                            st.error("❌ New password must be at least 8 characters long.")
                        else:
                            res = docpage_api.change_user_password(current_pw, new_pw)
                            if L.is_ok(res):
                                st.success("✅ Password changed. Your old sessions have ended; log in again with the new password.")
                            elif (res or {}).get("_http_status") == 401:
                                st.error("❌ Your current password is incorrect.")
                            else:
                                show_api_error(res)
            with adm_col2:
                st.markdown("##### Administrative Profile")
                st.text_input("Registered Name", value=user_name, disabled=True)
                st.text_input("Institutional Email", value=user_email, disabled=True)
                st.markdown(f"**Current Role:** `{user_role}`")

        with st.container(border=True):
            st.markdown("##### Staff & Admin Directory")
            if admins:
                accounts_table(admins)
            else:
                st.info("No admin accounts listed.")
            st.caption("Admin accounts can't be created from the app yet: POST /admin/provision creates doctor accounts.")
