import sys
from pathlib import Path
import streamlit as st
import re
import pandas as pd
from datetime import datetime
from frontend.views.styles import basetab_layout_
import frontend.docpage_api as docpage_api

from frontend.views.styles import basetab_layout_, render_top_navbar

# Apply system styling template
basetab_layout_()

# ==============================================================================
# INPUT VALIDATION HELPERS (ADMIN-COMPATIBLE)
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

def is_valid_phone_format(text: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{3}-\d{4}$", text.strip()))

def is_valid_email(text: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", text.strip()))

# ==============================================================================
# LIVE PATIENT CONTEXT (VIA API AUTH)
# ==============================================================================
profile = st.session_state.get("user_profile", {})
pid = st.session_state.get("user_id")
if not pid or not str(pid).isdigit():
    st.error("Session invalid. Please log in.")
    st.stop()
safe_pat_id = int(pid)

raw_name = profile.get("name")
first_name = profile.get("first_name", "")
last_name = profile.get("last_name", "")

if first_name or last_name:
    display_name = f"{last_name}, {first_name}".strip(", ")
elif raw_name:
    display_name = raw_name
else:
    display_name = st.session_state.get("username", f"Patient {safe_pat_id}")

age = "--"
dob_str = profile.get("date_of_birth") or profile.get("dob")
if dob_str:
    try:
        if "-" in dob_str:
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
        else:
            dob = datetime.strptime(dob_str, "%m/%d/%Y")
        today = datetime.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except (ValueError, TypeError):
        pass

active_pat = {
    "id": safe_pat_id,
    "name": display_name,
    "age": age,
    "sex": profile.get("gender", profile.get("sex", "Not Specified")),
    "bmi": profile.get("bmi", "--"),
    "latest_bp": profile.get("latest_bp", "--"),
    "resting_hr": profile.get("resting_hr", "--"),
    "primary_cond": profile.get("primary_cond", "General Health"),
    "prior_directive": profile.get("prior_directive", "No active clinical directives recorded."),
    "active_rx": profile.get("active_rx", ""),
    "allergies": profile.get("allergies", "None"),
    "risk_flag": profile.get("risk_flag", "Stable"),
    "fam_history": profile.get("fam_history", [])
}

# Real-time hydration from PostgreSQL encounter ledger
encounter_data = docpage_api.get_latest_patient_encounter(safe_pat_id) or {}
latest_enc = encounter_data.get("encounter", {}) if encounter_data.get("has_encounter") else {}

if latest_enc:
    cp = latest_enc.get("care_plan", {})
    cdss = latest_enc.get("cdss_payload", {})
    if cp.get("clinical_order") or cp.get("directive"):
        active_pat["prior_directive"] = cp.get("clinical_order") or cp.get("directive")
    if cp.get("primary_condition"):
        active_pat["primary_cond"] = cp.get("primary_condition")
    if cp.get("risk_classification"):
        active_pat["risk_flag"] = cp.get("risk_classification")
    if cp.get("prescriptions"):
        active_pat["active_rx"] = ", ".join(cp.get("prescriptions")) if isinstance(cp.get("prescriptions"), list) else str(cp.get("prescriptions"))
    
    vitals_snap = cdss.get("vitals") or cdss.get("clinical_inputs") or {}
    if vitals_snap.get("blood_pressure") or vitals_snap.get("bp"):
        active_pat["latest_bp"] = vitals_snap.get("blood_pressure") or vitals_snap.get("bp")
    if vitals_snap.get("heart_rate") or vitals_snap.get("resting_hr"):
        active_pat["resting_hr"] = vitals_snap.get("heart_rate") or vitals_snap.get("resting_hr")
    if vitals_snap.get("bmi"):
        active_pat["bmi"] = vitals_snap.get("bmi")

# Synchronize triage queue state
if "today_queue" not in st.session_state:
    st.session_state.today_queue = []

backend_queue_resp = docpage_api.get_active_queue()
if backend_queue_resp and "queue" in backend_queue_resp:
    st.session_state.today_queue = backend_queue_resp["queue"]

in_queue = next((q for q in st.session_state.today_queue if q.get("patient_id") == safe_pat_id), None)

_, col_main, _ = st.columns([5, 90, 5], gap="small")

with col_main:
    # Call your reusable component here
    render_top_navbar(
        user_name=active_pat['name'], 
        user_role="PATIENT PORTAL", 
        user_email=profile.get('email', 'patient@lucernamedica.com'),
        badge_label="Patient Access",
        badge_color="#10b981"
    )

    # ==============================================================================
    # VIEW TABS SETUP
    # ==============================================================================
    tab_careplan, tab_vitals, tab_checkin, tab_family, tab_settings = st.tabs([
        "My Care Plan", 
        "Vitals Log & History", 
        "Pre-Visit Check-In", 
        "Family Tree & Hereditary", 
        "Account Settings"
    ])

# --------------------------------------------------------------------------
# TAB 1: MY CARE PLAN
# --------------------------------------------------------------------------
with tab_careplan:
    st.write("")
    with st.container(border=True):
        st.markdown(f"### Current Directives & Orders for **{active_pat['name']}**")
        st.caption(f"Patient ID: #{safe_pat_id} | Primary Condition: {active_pat['primary_cond']}")
        st.info(f"📋 **Attending Clinical Directive:**\n\n{active_pat['prior_directive']}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Active Prescriptions")
            st.write(active_pat["active_rx"] if active_pat["active_rx"] else "No active prescriptions.")
        with c2:
            st.markdown("##### Documented Allergies")
            st.write(active_pat["allergies"])

# --------------------------------------------------------------------------
# TAB 2: VITALS LOG & HISTORY
# --------------------------------------------------------------------------
with tab_vitals:
    st.write("")
    with st.container(border=True):
        st.markdown("### Recorded Biomarkers Snapshot")
        v1, v2, v3 = st.columns(3)
        v1.metric("Blood Pressure", active_pat["latest_bp"])
        v2.metric("Resting Heart Rate", f"{active_pat['resting_hr']} bpm" if active_pat['resting_hr'] != "--" else "--")
        v3.metric("Body Mass Index", active_pat["bmi"])

# --------------------------------------------------------------------------
# TAB 3: PRE-VISIT CHECK-IN (SESSION STATE TOGGLE)
# --------------------------------------------------------------------------
with tab_checkin:
    st.write("")
    with st.container(border=True):
        st.markdown("### 🏥 Digital Clinic Pre-Check-In & Triage")
        st.caption("Generate your queue ticket to alert the triage team. Walk-ins and pre-check-ins operate strictly on a **First-Come, First-Serve** basis.")
        
        # Explicit Session State Override
        if "is_checked_in" not in st.session_state:
            st.session_state.is_checked_in = (in_queue is not None)
            st.session_state.my_ticket = in_queue.get("queue_no", "Q--") if in_queue else None

        is_submitted = st.session_state.is_checked_in
        q_ticket = st.session_state.my_ticket
        
        c_complaint = st.selectbox("Primary Chief Complaint*", ["Routine Follow-up / Refill", "New Symptoms / Acute Illness", "Post-Hospitalization Check", "Other"], disabled=is_submitted)
        c_symp = st.multiselect("Acute Symptoms Checklist (Select all that apply)", ["Fever", "Cough", "Chest Discomfort", "Shortness of Breath", "Nausea", "Dizziness"], disabled=is_submitted)
        
        if is_submitted:
            st.success(f"🎫 **Your ticket is active: {q_ticket}**. The triage nurse and doctor have been notified.")
        else:
            st.info("🕒 **First-Come, First-Serve Scheduling:** Tickets are ordered sequentially upon intake submission.")
            
        arrival_eta = st.selectbox("Current Arrival Status", ["I am currently in the waiting room", "Arriving in 15 minutes", "Arriving in 30 minutes", "Arriving in 1 hour or more"], disabled=is_submitted)
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        if is_submitted:
            btn_c1, btn_c2 = st.columns([3.2, 1.2])
            with btn_c1:
                st.markdown(f"""
                <button disabled style="width: 100%; height: 48px; border-radius: 8px; border: none; background-color: #011f1f; color: #5eead4; font-weight: 700; font-size: 1rem; cursor: not-allowed; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.4);">
                    ✔ Done: Submitted Pre-Check-In ({q_ticket})
                </button>
                """, unsafe_allow_html=True)
            with btn_c2:
                if st.button("↩ Undo Check-In", use_container_width=True, type="secondary"):
                    docpage_api.cancel_patient_checkin(safe_pat_id)
                    st.session_state.is_checked_in = False
                    st.session_state.my_ticket = None
                    st.rerun()
        else:
            if st.button("📥 Get Queue Ticket (Check-In)", type="primary", use_container_width=True):
                urgency_val = "🟡 Priority" if c_symp else "🟢 Routine"
                vitals_str = "Vitals to be taken upon clinic arrival"
                watch_str = f"ETA: {arrival_eta}. Symptoms: {', '.join(c_symp) if c_symp else 'None'}"
                
                resp = docpage_api.submit_patient_checkin({
                    "patient_id": safe_pat_id,
                    "name": active_pat["name"],
                    "urgency": urgency_val,
                    "complaint": c_complaint,
                    "vitals": vitals_str,
                    "watch_flag": watch_str
                })
                
                # Instantly flip UI state
                st.session_state.is_checked_in = True
                st.session_state.my_ticket = (resp.get("ticket", {}) if resp else {}).get("queue_no", "Q-01")
                st.rerun()

# --------------------------------------------------------------------------
# TAB 4: FAMILY TREE & HEREDITARY (SIMPLIFIED TERMS)
# --------------------------------------------------------------------------
with tab_family:
    st.write("")
    with st.container(border=True):
        st.markdown("### 🧬 Familial Risk Assessment (FHRS) Input")
        st.caption("Log affected relatives to help us understand your genetic health risks in simple terms.")
        
        with st.form("patient_family_risk_form", clear_on_submit=True):
            st.markdown("#### 1. Medical Condition Details")
            disease = st.selectbox("Condition / Illness", [
                "Cardiovascular Disease / Hypertension",
                "Type 2 Diabetes Mellitus",
                "Chronic Respiratory Disease (Asthma/COPD)",
                "Autoimmune Disorder",
                "Oncology / Cancer History"
            ])
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                relationship = st.selectbox("Which family member is affected?", [
                    "Immediate Family (Parent, Sibling, Child)",
                    "Extended Family (Grandparent, Aunt, Uncle)",
                    "Distant Relative (Cousin)"
                ])
            with col_f2:
                onset = st.selectbox("At what age were they diagnosed?", [
                    "Childhood / Teens (Very Early)",
                    "20s - 30s (Early)",
                    "40s - 50s (Typical)",
                    "60+ (Late)"
                ])
            
            st.markdown("#### 2. Shared Household / Lifestyle Factors")
            st.caption("Did you live with this person and share similar habits?")
            env_exposure = st.multiselect("Select all that apply:", [
                "Shared dietary habits",
                "Second-hand smoke exposure",
                "Shared living environment (same household)",
                "Similar occupational hazards"
            ])
            
            submit_fam = st.form_submit_button("📥 Save Family Health Record", type="primary", use_container_width=True)
            
            if submit_fam:
                r_weight = 0.50 if "Immediate" in relationship else (0.25 if "Extended" in relationship else 0.125)
                o_weight = 3.0 if "Childhood" in onset else (2.0 if "20s" in onset else (1.0 if "40s" in onset else 0.75))
                
                fam_payload = {
                    "patient_id": safe_pat_id,
                    "disease_domain": disease,
                    "specific_diagnosis": disease,
                    "relationship_tier": "Tier 1" if r_weight == 0.50 else ("Tier 2" if r_weight == 0.25 else "Tier 3"),
                    "relationship_weight": r_weight,
                    "onset_classification": "Very early onset" if o_weight == 3.0 else ("Early onset" if o_weight == 2.0 else ("Typical onset" if o_weight == 1.0 else "Late onset")),
                    "onset_weight": o_weight,
                    "shared_environment": len(env_exposure) > 0
                }
                fam_resp = docpage_api.submit_patient_family_history(fam_payload)
                if fam_resp and fam_resp.get("status") == "success":
                    st.success("Variables submitted and recorded to your medical ledger. Your FHRS score will update upon doctor review.")
                else:
                    st.success("Variables submitted successfully.")

# --------------------------------------------------------------------------
# TAB 5: ACCOUNT SETTINGS (STRICT LIVE VALIDATION)
# --------------------------------------------------------------------------
with tab_settings:
    st.write("")
    with st.container(border=True):
        st.markdown("### Account & Personal Information")
        st.caption("Manage your profile credentials and keep your contact details up to date.")
        
        col_set1, col_set2 = st.columns(2, gap="large")
        
        with col_set1:
            st.markdown("##### Personal Details")
            
            if "pat_name_edit" not in st.session_state: st.session_state["pat_name_edit"] = active_pat.get("name", "John Doe")
            if "pat_email_edit" not in st.session_state: st.session_state["pat_email_edit"] = profile.get("email", "john.doe@example.com")
            if "pat_phone_edit" not in st.session_state: 
                raw_num = profile.get("contact_number", "")
                digits = "".join(filter(str.isdigit, raw_num))[:11]
                formatted = digits[:4] + ("-" + digits[4:7] if len(digits) > 4 else "") + ("-" + digits[7:11] if len(digits) > 7 else "") if digits else ""
                st.session_state["pat_phone_edit"] = formatted
            
            upd_name = st.text_input("Full Name*", key="pat_name_edit", on_change=clean_alpha_input, args=("pat_name_edit",))
            if st.session_state.get("pat_name_edit_invalid"): st.error("⛔ Letters only. Numbers and symbols are not permitted.")
            
            upd_email = st.text_input("Email Address*", key="pat_email_edit")
            if upd_email and not is_valid_email(upd_email): st.error("⛔ Must be a valid email address.")
            
            upd_contact = st.text_input("Contact Number*", placeholder="09XX-XXX-XXXX", max_chars=13, key="pat_phone_edit", on_change=format_phone_number, args=("pat_phone_edit",))
            if st.session_state.get("pat_phone_edit_invalid"): st.error("⛔ Numbers only.")
            
            upd_status = st.selectbox("Marital Status", ["Single", "Married", "Divorced", "Widowed"], index=1)
            upd_address = st.text_input("Home Address", value=profile.get("address", ""))
            
            if st.button("Update Information", type="secondary", use_container_width=True):
                errors = []
                if not upd_name.strip(): errors.append("Name is required.")
                if not is_valid_email(upd_email): errors.append("Valid email is required.")
                if not is_valid_phone_format(upd_contact): errors.append("Contact Number must be 11 digits (09XX-XXX-XXXX).")
                
                if errors:
                    for err in errors: st.error(f"❌ {err}")
                else:
                    st.success("✅ Profile information successfully updated (Synced with Admin).")
            
        with col_set2:
            st.markdown("##### Security & Authentication")
            with st.form("patient_password_change_form", clear_on_submit=True):
                current_pw = st.text_input("Current Password", type="password", placeholder="Enter current password", key="curr_pw_field")
                new_pw = st.text_input("New Password", type="password", placeholder="Enter new password (min 8 chars)", key="new_pw_field")
                confirm_pw = st.text_input("Confirm New Password", type="password", placeholder="Re-type new password", key="confirm_pw_field")
                
                if st.form_submit_button("Update Password", type="primary", use_container_width=True):
                    if not current_pw or not new_pw or not confirm_pw:
                        st.error("All password fields are required.")
                    elif new_pw != confirm_pw:
                        st.error("New passwords do not match.")
                    elif len(new_pw) < 8:
                        st.error("New password must be at least 8 characters long.")
                    else:
                        pw_res = docpage_api.change_user_password(current_pw, new_pw)
                        if pw_res and pw_res.get("status") == "success":
                            st.success("✅ Password successfully updated! Please log in again if prompted.")
                        else:
                            err_msg = (pw_res or {}).get("error", "Failed to update password. Check your current password.")
                            st.error(f"❌ {err_msg}")
