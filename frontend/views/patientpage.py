import os
import re
import sys

import pandas as pd
import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _ROOT not in sys.path:
    sys.path.append(_ROOT)

from frontend import cdss_logic as L
from frontend import docpage_api
from frontend.views.styles import (basetab_layout_, flash, render_fhrs_panel, render_top_navbar, show_api_error,
                                   show_flash)

# Apply system styling template
basetab_layout_()

# ==============================================================================
# INPUT VALIDATION HELPERS
# ==============================================================================
def is_valid_email(text: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", text.strip()))


# ==============================================================================
# LOGGED-IN PATIENT (the backend always answers with this patient's own records;
# a patient never sends a patient_id except in the queue-cancel URL)
# ==============================================================================
if not st.session_state.get("token"):
    st.error("Session invalid. Please log in.")
    st.stop()

profile = st.session_state.get("user_profile") or {}
pid = profile.get("patient_id") or st.session_state.get("user_id")
header = L.patient_header(dict(profile, patient_id=pid))
display_name = header["name"] if (profile.get("first_name") or profile.get("last_name")) \
    else st.session_state.get("username", f"Patient {pid}")

# Latest sealed encounter -> care plan written by the doctor
enc_resp = docpage_api.get_latest_patient_encounter()
latest = (enc_resp.get("encounter") or {}) if (L.is_ok(enc_resp) and enc_resp.get("has_encounter")) else {}
plan = L.read_care_plan(latest.get("care_plan"))
last_risk = L.summarize_inference(latest.get("cdss_payload")) if latest.get("cdss_payload") else None

# Own queue ticket (GET /patient/queue returns only this patient's ticket)
queue_resp = docpage_api.get_active_queue()
my_ticket = L.own_waiting_ticket(queue_resp)

_, col_main, _ = st.columns([5, 90, 5], gap="small")

with col_main:
    render_top_navbar(
        user_name=display_name,
        user_role="PATIENT PORTAL",
        user_email=profile.get("email", ""),
        badge_label="Patient Access",
        badge_color="#10b981",
    )
    show_flash()

    tab_careplan, tab_vitals, tab_checkin, tab_family, tab_settings = st.tabs([
        "My Care Plan",
        "Vitals Log & History",
        "Pre-Visit Check-In",
        "Family Tree & Hereditary",
        "Account Settings",
    ])

# --------------------------------------------------------------------------
# TAB 1: MY CARE PLAN (from the latest sealed encounter)
# --------------------------------------------------------------------------
with tab_careplan:
    st.write("")
    with st.container(border=True):
        st.markdown(f"### Current Directives & Orders for **{display_name}**")
        if not L.is_ok(enc_resp):
            show_api_error(enc_resp)
        elif not latest:
            st.info("No visit has been recorded yet. Your care plan appears here after your doctor signs your visit.")
        else:
            st.caption(f"From your visit on {latest.get('created_at', '—')} with {latest.get('doctor_name', 'your doctor')}"
                       f"{' · ' + plan['primary_condition'] if plan['primary_condition'] else ''}")
            st.info(f"📋 **Attending Clinical Directive:**\n\n{plan['directive'] or 'No directive recorded.'}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### Active Prescriptions")
                if plan["medications"]:
                    for med in plan["medications"]:
                        st.markdown(f"- {med}")
                else:
                    st.write("No active prescriptions.")
            with c2:
                st.markdown("##### Lifestyle advice")
                st.write(plan["lifestyle"] or "None recorded.")
                if last_risk and last_risk["show_result"]:
                    st.markdown("##### Risk classification at that visit")
                    st.markdown(f"<span style='color:{L.tier_color(last_risk['tier'])};font-weight:700;'>"
                                f"{last_risk['tier']}</span>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("### Visit history")
        hist_resp = docpage_api.get_patient_encounters_list()
        if not L.is_ok(hist_resp):
            show_api_error(hist_resp)
        elif not hist_resp.get("encounters"):
            st.caption("No visits recorded yet.")
        else:
            st.dataframe(pd.DataFrame([{
                "Date": e.get("created_at"), "Type": e.get("record_type"), "Doctor": e.get("doctor_name"),
                "Directive": e.get("summary_directive"),
            } for e in hist_resp["encounters"]]), hide_index=True, use_container_width=True)

# --------------------------------------------------------------------------
# TAB 2: VITALS (latest stored measurements per disease, read from the database)
# --------------------------------------------------------------------------
with tab_vitals:
    st.write("")
    with st.container(border=True):
        st.markdown("### Recorded Biomarkers Snapshot")
        st.caption("Latest values your care team stored for each area.")
        for code, label in L.MODALITY_LABELS.items():
            resp = docpage_api.get_latest_biomarkers(code)
            with st.expander(label, expanded=(code == "cvd")):
                if L.is_ok(resp) and resp.get("values"):
                    labels = {f["column"]: (f["label"], f["unit"]) for f in L.BIOMARKER_FIELDS[code]}
                    st.caption(f"Recorded {resp.get('recorded_at', '')}")
                    st.dataframe(pd.DataFrame([{
                        "Measurement": labels.get(k, (k, ""))[0], "Value": v, "Unit": labels.get(k, (k, ""))[1],
                    } for k, v in resp["values"].items() if v is not None]), hide_index=True, use_container_width=True)
                elif resp is None or ((resp or {}).get("_http_status", 0) >= 500):
                    show_api_error(resp)
                else:
                    st.caption("No measurements on file.")

# --------------------------------------------------------------------------
# TAB 3: PRE-VISIT CHECK-IN (state comes from the backend queue, not the browser)
# --------------------------------------------------------------------------
with tab_checkin:
    st.write("")
    with st.container(border=True):
        st.markdown("### 🏥 Digital Clinic Pre-Check-In & Triage")
        st.caption("Generate your queue ticket to alert the triage team. Walk-ins and pre-check-ins operate strictly on a **First-Come, First-Serve** basis.")
        if not L.is_ok(queue_resp):
            show_api_error(queue_resp)

        if my_ticket:
            st.success(f"🎫 **Your ticket is active: {my_ticket.get('queue_no', '—')}** · "
                       f"{my_ticket.get('lifecycle_status', 'In Waiting Room')} since {my_ticket.get('time_in', '—')}.")
            if st.button("↩ Undo Check-In", use_container_width=True, type="secondary"):
                resp = docpage_api.cancel_patient_checkin(pid)
                if L.is_ok(resp):
                    flash("info", "Your check-in was cancelled.")
                    st.rerun()
                show_api_error(resp)
        else:
            c_complaint = st.selectbox("Primary Chief Complaint*", ["Routine Follow-up / Refill", "New Symptoms / Acute Illness", "Post-Hospitalization Check", "Other"])
            c_symp = st.multiselect("Acute Symptoms Checklist (Select all that apply)", ["Fever", "Cough", "Chest Discomfort", "Shortness of Breath", "Nausea", "Dizziness"])
            arrival_eta = st.selectbox("Current Arrival Status", ["I am currently in the waiting room", "Arriving in 15 minutes", "Arriving in 30 minutes", "Arriving in 1 hour or more"])
            st.info("🕒 **First-Come, First-Serve Scheduling:** Tickets are ordered sequentially upon intake submission.")
            if st.button("📥 Get Queue Ticket (Check-In)", type="primary", use_container_width=True):
                symptoms = ", ".join(c_symp) if c_symp else "none"
                resp = docpage_api.submit_patient_checkin({
                    "name": display_name,
                    "complaint": f"{c_complaint}. Symptoms: {symptoms}. {arrival_eta}.",
                    "vitals": "To be taken on arrival",
                })
                if L.is_ok(resp):
                    ticket = resp.get("ticket") or {}
                    flash("success", f"🎫 Your ticket is {ticket.get('queue_no', 'ready')}.")
                    st.rerun()
                show_api_error(resp)

# --------------------------------------------------------------------------
# TAB 4: FAMILY TREE & HEREDITARY (tier + onset only; the backend owns the weights)
# --------------------------------------------------------------------------
with tab_family:
    st.write("")
    with st.container(border=True):
        st.markdown("### 🧬 Familial Risk Assessment (FHRS) Input")
        st.caption("Log affected relatives. Your doctor confirms each entry; until then it counts half.")

        fh_resp = docpage_api.get_patient_family_history()
        if not L.is_ok(fh_resp):
            show_api_error(fh_resp)
        elif fh_resp.get("family_history"):
            st.dataframe(pd.DataFrame([{
                "Condition": L.DISEASE_CHOICES.get(r.get("disease_domain"), r.get("disease_domain")),
                "Relative": L.TIER_LABELS.get(r.get("relationship_tier"), r.get("relationship_tier")),
                "Onset": L.ONSET_LABELS.get(r.get("onset_classification"), r.get("onset_classification")),
                "Confirmed by doctor": "Yes" if r.get("is_verified") else "Not yet",
            } for r in fh_resp["family_history"]]), hide_index=True, use_container_width=True)

        with st.form("patient_family_risk_form", clear_on_submit=True):
            st.markdown("#### 1. Medical Condition Details")
            disease_label = st.selectbox("Condition / Illness", list(L.PATIENT_DISEASE_CHOICES), key="pf_disease")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                tier_label = st.selectbox("Which family member is affected?", list(L.PATIENT_TIER_CHOICES), key="pf_tier")
            with col_f2:
                onset_label = st.selectbox("At what age were they diagnosed?", list(L.PATIENT_ONSET_CHOICES), key="pf_onset")

            st.markdown("#### 2. Shared Household / Lifestyle Factors")
            st.caption("Did you live with this person and share similar habits?")
            env_exposure = st.multiselect("Select all that apply:", [
                "Shared dietary habits",
                "Second-hand smoke exposure",
                "Shared living environment (same household)",
                "Similar occupational hazards",
            ], key="pf_shared")

            if st.form_submit_button("📥 Save Family Health Record", type="primary", use_container_width=True):
                payload = L.build_family_history_payload(
                    L.PATIENT_DISEASE_CHOICES[disease_label], L.PATIENT_TIER_CHOICES[tier_label],
                    L.PATIENT_ONSET_CHOICES[onset_label], shared_environment=len(env_exposure) > 0)
                fam_resp = docpage_api.submit_patient_family_history(payload)
                if L.is_ok(fam_resp):
                    flash("success", "Saved to your medical record. Your doctor will confirm it at your next visit.")
                    st.rerun()
                show_api_error(fam_resp)

    with st.container(border=True):
        st.markdown("### Your family-risk score and household hazards")
        codes = list(L.DISEASE_CHOICES)
        view_code = st.selectbox("Condition", codes, format_func=L.DISEASE_CHOICES.get, key="pf_fhrs_disease")
        fhrs_resp = docpage_api.get_fhrs(view_code)
        if L.is_ok(fhrs_resp):
            render_fhrs_panel(L.fhrs_view(fhrs_resp.get("fhrs")))
        else:
            show_api_error(fhrs_resp)

        hz_resp = docpage_api.get_hazards()
        if not L.is_ok(hz_resp):
            show_api_error(hz_resp)
        else:
            hazards = hz_resp.get("hazards") or []
            catalogue = hz_resp.get("catalogue") or {}
            mine = L.recorded_hazards(hazards, view_code)
            if mine:
                st.markdown("**Recorded household hazards** (ask your doctor to remove one)")
                cat = {h.get("code"): h for h in catalogue.get(view_code, [])}
                for hz in mine:
                    st.markdown(f"- {hz.get('label') or cat.get(hz.get('hazard_code'), {}).get('label') or hz.get('hazard_code')}")
            choices = L.hazard_choices(catalogue, view_code, hazards)
            if not catalogue.get(view_code):
                st.caption("No household hazards are listed for this condition.")
            elif choices:
                pick = st.selectbox("Add a household hazard", choices, key=f"pf_hz_pick_{view_code}",
                                    format_func=lambda h: h.get("label", h.get("code")))
                if st.button("Add hazard", key="pt_hz_add"):
                    resp = docpage_api.add_hazard(view_code, pick["code"])
                    if L.is_ok(resp):
                        flash("success", "Hazard recorded.")
                        st.rerun()
                    show_api_error(resp)

# --------------------------------------------------------------------------
# TAB 5: ACCOUNT SETTINGS
# --------------------------------------------------------------------------
with tab_settings:
    st.write("")
    with st.container(border=True):
        st.markdown("### Account & Personal Information")
        col_set1, col_set2 = st.columns(2, gap="large")

        with col_set1:
            st.markdown("##### Personal Details")
            st.text_input("Full Name", value=display_name, disabled=True)
            st.text_input("Email Address", value=profile.get("email", ""), disabled=True)
            st.text_input("Contact Number", value=profile.get("contact_number", ""), disabled=True)
            st.text_input("Home Address", value=profile.get("address", ""), disabled=True)
            st.caption("To change these details, please contact the clinic. They can't be edited from the portal yet.")

        with col_set2:
            st.markdown("##### Security & Authentication")
            if st.session_state.get("password_changed"):
                st.success("✅ Password changed. Your old sessions have ended, so please log in again.")
                if st.button("Log in again", key="relogin_btn", type="primary", use_container_width=True):
                    L.clear_auth_state(st.session_state)
                    st.rerun()
            else:
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
                            if L.is_ok(pw_res):
                                st.session_state["password_changed"] = True
                                st.rerun()
                            elif (pw_res or {}).get("_http_status") == 401:
                                st.error("❌ Your current password is incorrect.")
                            else:
                                show_api_error(pw_res)
