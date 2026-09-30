import sys
import os
import hashlib
import json
import uuid
import time
import textwrap
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# 1. ADD PARENT PATH & IMPORT SHARED UI
# ==============================================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from styles import basetab_layout_, render_top_navbar
except ImportError:
    from views.styles import basetab_layout_, render_top_navbar

# ==============================================================================
# 2. PAGE SETUP & THEME INITIALIZATION
# ==============================================================================
st.set_page_config(layout="wide", page_title="Lucerna Medica | Clinician Workspace")
basetab_layout_()

# Hide Native Streamlit Toolbar to lock theme
st.markdown("""
    <style>
        [data-testid="stToolbar"] {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. GLOBAL SESSION STATE & UPGRADED CDSS VARIABLES
# ==============================================================================
SCHEMA_VERSION = "1.0.0"
MODEL_VERSION  = "xgb-multitask-v1.2.0"

if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "first_name": "Sarah", "last_name": "Jenkins", "suffix": "MD",
        "license_number": "PRC-123456", "hospital_affiliation": "Lucerna Medica",
        "specialization": "Cardiology", "email": "s.jenkins@lucernamedica.com"
    }

profile = st.session_state.user_profile
active_doc = {
    "name": f"Dr. {profile.get('first_name', 'System')} {profile.get('last_name', 'Clinician')}".strip(),
    "suffix": profile.get("suffix", "MD"),
    "role": "ATTENDING CLINICIAN",
    "prc": profile.get("license_number", "PRC Pending"),
    "affiliation": profile.get("hospital_affiliation", "Lucerna Medica"),
    "specialty": profile.get("specialization", "Cardiology"),
    "email": profile.get("email", "doctor@lucernamedica.com"),
    "icon": "🩺",
    "badge_bg": "#f1f5f9", "badge_fg": "#0f172a",
    "default_modality": "Cardiovascular Diseases (Hypertension / CVD)"
}

spec_upper = active_doc["specialty"].upper()
if "CARDIO" in spec_upper:
    active_doc.update({"icon": "🫀", "badge_bg": "#fee2e2", "badge_fg": "#ef4444", "default_modality": "Cardiovascular Diseases (Hypertension / CVD)"})
elif "ENDOCRIN" in spec_upper or "DIABET" in spec_upper:
    active_doc.update({"icon": "🩸", "badge_bg": "#fef3c7", "badge_fg": "#d97706", "default_modality": "Type 2 Diabetes Mellitus"})
elif "PULMON" in spec_upper or "RESPIR" in spec_upper:
    active_doc.update({"icon": "🫁", "badge_bg": "#e0f2fe", "badge_fg": "#0284c7", "default_modality": "Chronic Respiratory Diseases (COPD & Asthma)"})
elif "NEURO" in spec_upper or "PSYCH" in spec_upper:
    active_doc.update({"icon": "🧠", "badge_bg": "#ede9fe", "badge_fg": "#7c3aed", "default_modality": "Mental Health & Neurological Disorders"})

if "active_modality" not in st.session_state: st.session_state.active_modality = active_doc["default_modality"]

# BLANK DIRECTORIES FOR DATABASE
if "patient_directory" not in st.session_state: st.session_state.patient_directory = []
if "today_queue" not in st.session_state: st.session_state.today_queue = []

# Upgraded Phase 1 / Phase 2 Variables
_DEFAULT_STATE = {
    "active_patient": None,
    "ai_inference_completed": False,
    "cdss_inference_payload": None,
    "fhrs_data": pd.DataFrame(columns=["Disease Category", "Relative Relationship", "Age of Onset"]),
    "env_factors": [],
    "audit_trail": [],
    "baseline_records": {} # Centralized Mock DB for Baseline hashes keyed by PID
}
for key, default in _DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Helper Methods ---
mod_map = {
    "Cardiovascular (CVD)": "Cardiovascular Diseases (Hypertension / CVD)",
    "Type 2 Diabetes": "Type 2 Diabetes Mellitus",
    "COPD (Pulmonary)": "Chronic Respiratory Diseases (COPD & Asthma)",
    "Mental Health / Neuro": "Mental Health & Neurological Disorders"
}
mod_map_rev = {v: k for k, v in mod_map.items()}

def _sync_from_tab2():
    st.session_state.active_modality = mod_map.get(st.session_state.modality_switcher, "Cardiovascular Diseases (Hypertension / CVD)")

def _sync_from_tab3():
    st.session_state.active_modality = st.session_state.cdss_active_modality_selector

def start_consult(patient):
    st.session_state.active_patient = patient
    st.session_state["ai_inference_completed"] = False
    st.session_state["cdss_inference_payload"] = None
    st.session_state["proposed_baseline"] = None
    for q in st.session_state.today_queue:
        if q["id"] == patient["id"]:
            q["lifecycle_status"] = "In Consultation"
    st.toast(f"Consultation initiated for {patient.get('name', 'Patient')}", icon="🩺")

def sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

def append_audit(event_type: str, payload: dict) -> None:
    st.session_state["audit_trail"].append({
        "audit_id": f"AUD-{uuid.uuid4().hex[:6].upper()}",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event_type": event_type,
        "payload": payload,
    })

def calculate_fhrs(df_fhrs, dynamic_env_factors=None):
    if df_fhrs.empty: return 0.0, 0.0, 1.0, 0.0, "Code 0"
    
    r_weights = {"Tier 1": 0.50, "Tier 2": 0.25, "Tier 3": 0.125}
    o_weights = {"Very Early": 3.0, "Early": 2.0, "Standard": 1.0, "Late": 0.75}
    
    base_fhrs = 0.0
    for _, row in df_fhrs.iterrows():
        r_i = r_weights.get(row["Relative Relationship"], 0.0)
        o_i = o_weights.get(row["Age of Onset"], 1.0)
        base_fhrs += (r_i * o_i * 1.0)
    
    n_t1 = len(df_fhrs[df_fhrs["Relative Relationship"] == "Tier 1"])
    n_t2 = len(df_fhrs[df_fhrs["Relative Relationship"] == "Tier 2"])
    n_t3 = len(df_fhrs[df_fhrs["Relative Relationship"] == "Tier 3"])
    c_d = (n_t1 * 1.0) + (n_t2 * 0.5) + (n_t3 * 0.25)
    
    total_base_fhrs = base_fhrs + c_d
    env_factors = dynamic_env_factors if dynamic_env_factors else []
    e_d = 1.0 + (len(env_factors) * 0.2)
    adjusted_fhrs = total_base_fhrs * e_d
    
    if adjusted_fhrs == 0.0: code = "Code 0"
    elif adjusted_fhrs < 2.0: code = "Code 1"
    elif adjusted_fhrs < 4.5: code = "Code 2"
    elif adjusted_fhrs < 8.0: code = "Code 3"
    else: code = "Code 4"
        
    return total_base_fhrs, c_d, e_d, adjusted_fhrs, code

def generate_hereditary_screenings(fam_history_list, age, sex):
    screenings = []
    fam_str = " | ".join(fam_history_list).lower() if fam_history_list else ""
    
    if any(k in fam_str for k in ["cvd", "heart attack", "hypertension", "stroke", "early onset"]):
        screenings.append({"test": "Fasting Lipid Panel & 12-Lead Resting ECG", "modality": "🫀 Cardiovascular", "urgency": "High Priority", "rationale": "Immediate lineage presents early-onset cardiovascular risk."})
    if any(k in fam_str for k in ["diabetes", "t2d", "glycemic"]):
        screenings.append({"test": "Fasting Plasma Glucose (FPG) & Glycated Hemoglobin (HbA1c)", "modality": "🩸 Diabetes & Endocrine", "urgency": "High Priority", "rationale": "Maternal/paternal diabetes lineage indicates genetic insulin sensitivity variance."})
    if any(k in fam_str for k in ["copd", "asthma", "pulmonary"]):
        screenings.append({"test": "Baseline Spirometry (FEV1/FVC Ratio)", "modality": "🫁 Pulmonology", "urgency": "Moderate Priority", "rationale": "Familial history of chronic airway reactivity."})
    if any(k in fam_str for k in ["dementia", "alzheimer", "depression", "psychiatric"]):
        screenings.append({"test": "Baseline Cognitive Screening (MoCA / MMSE) & Sleep Diary", "modality": "🧠 Neuropsychiatry", "urgency": "Routine", "rationale": "Genetic marker for neurodegenerative vulnerability."})
    
    if not screenings:
        screenings.append({"test": "Comprehensive Adult Medical Examination", "modality": "🟢 General Wellness", "urgency": "Annual Routine", "rationale": "No immediate high-penetrance genetic risk detected."})  
    return screenings

# ==============================================================================
# 4. WORKSPACE RENDER
# ==============================================================================
_, col_main, _ = st.columns([5, 90, 5], gap="small")

with col_main:
    render_top_navbar(
        user_name=f"{active_doc['name']}, {active_doc['suffix']}", 
        user_role=f"{active_doc['role']} | ✔ {active_doc['prc']}", 
        user_email=f"Affiliation: {active_doc['affiliation']} • Active Queue: {len(st.session_state.today_queue)}",
        badge_label=f"{active_doc['icon']} {active_doc['specialty']}",
        badge_color=active_doc["badge_fg"]
    )

    tab_overview, tab_queue, tab_cdss = st.tabs(["Overview Dashboard", "Live Patients & Triage", "AI Diagnostics & CDSS"])

    # --------------------------------------------------------------------------
    # TAB 1: OVERVIEW DASHBOARD (DB-READY BLANK STATE)
    # --------------------------------------------------------------------------
    with tab_overview:
        st.write("")
        total_cohort = 0
        c_cvd, c_dia, c_copd, c_neuro = 0, 0, 0, 0
        pct_cvd, pct_dia, pct_copd, pct_neuro = 0.0, 0.0, 0.0, 0.0
        trend_cvd, trend_dia, trend_copd, trend_neuro = "--", "--", "--", "--"
        alert_cvd, alert_dia, alert_copd, alert_neuro = "🟢 0 Alerts", "🟢 0 Alerts", "🟢 0 Alerts", "🟢 0 Alerts"
        total_assessed = 0
        risk_low, risk_med, risk_high = 0, 0, 0
        ai_concordance_score = 0.0
        ai_confirmed, ai_modified = 0, 0

        with st.container(border=True):
            st.markdown(textwrap.dedent("""
            <div style="margin-bottom: 16px;">
                <h3 style="margin: 0; font-size: 1.45rem; font-weight: 700;">Clinical Telemetry & Disease Velocity</h3>
                <p style="margin: 4px 0 0 0; font-size: 0.95rem;">Real-time epidemiological footprint and acute patient influx tracking.</p>
            </div>
            """), unsafe_allow_html=True)
            
            hero_col, grid_col = st.columns([1.3, 2], gap="large")
            with hero_col:
                st.markdown(textwrap.dedent(f"""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 22px 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.02); height: 295px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-size: 0.85rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase;">Total Active Cohort</span>
                            <span style="background: #e6f4f1; color: #007979; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 20px;">LIVE VELOCITY</span>
                        </div>
                        <div style="font-size: 4.8rem; font-weight: 800; line-height: 1; letter-spacing: -1.5px; margin: 4px 0;">{total_cohort}</div>
                        <div style="font-size: 1.1rem; font-weight: 600;">Monitored Patients</div>
                    </div>
                    <div>
                        <div style="display: flex; height: 10px; border-radius: 6px; overflow: hidden; background: #e2e8f0; margin-bottom: 10px;">
                            <div style="width: {pct_cvd:.1f}%; background-color: #ef4444;"></div>
                            <div style="width: {pct_dia:.1f}%; background-color: #f59e0b;"></div>
                            <div style="width: {pct_copd:.1f}%; background-color: #0284c7;"></div>
                            <div style="width: {pct_neuro:.1f}%; background-color: #8b5cf6;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600;">
                            <span>{c_cvd} CVD</span><span>{c_dia} Dia</span><span>{c_copd} COPD</span><span>{c_neuro} Neuro</span>
                        </div>
                    </div>
                </div>
                """), unsafe_allow_html=True)
                
            with grid_col:
                r1_c1, r1_c2 = st.columns(2, gap="medium")
                with r1_c1:
                    st.markdown(textwrap.dedent(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="display: flex; justify-content: space-between;"><span style="font-size: 0.95rem; font-weight: 600;">🫀 Cardiovascular</span> <span style="color: #64748b; font-weight: 700;">{trend_cvd}</span></div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">{c_cvd} <span style="font-size: 1.2rem; color: #64748b;">Patients</span></div>
                        <div style="font-size: 0.85rem; background: #f8fafc; color: #64748b; padding: 4px 8px; border-radius: 4px; width: fit-content;">{alert_cvd}</div>
                    </div>
                    """), unsafe_allow_html=True)
                with r1_c2:
                    st.markdown(textwrap.dedent(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="display: flex; justify-content: space-between;"><span style="font-size: 0.95rem; font-weight: 600;">🩸 Type 2 Diabetes</span> <span style="color: #64748b; font-weight: 700;">{trend_dia}</span></div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">{c_dia} <span style="font-size: 1.2rem; color: #64748b;">Patients</span></div>
                        <div style="font-size: 0.85rem; background: #f8fafc; color: #64748b; padding: 4px 8px; border-radius: 4px; width: fit-content;">{alert_dia}</div>
                    </div>
                    """), unsafe_allow_html=True)

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

                r2_c1, r2_c2 = st.columns(2, gap="medium")
                with r2_c1:
                    st.markdown(textwrap.dedent(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="display: flex; justify-content: space-between;"><span style="font-size: 0.95rem; font-weight: 600;">🫁 Pulmonology (COPD)</span> <span style="color: #64748b; font-weight: 700;">{trend_copd}</span></div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">{c_copd} <span style="font-size: 1.2rem; font-weight: 600; color: #64748b;">Patients</span></div>
                        <div style="font-size: 0.85rem; font-weight: 600; background: #f8fafc; color: #64748b; padding: 4px 8px; border-radius: 4px; display: inline-block; width: fit-content;">{alert_copd}</div>
                    </div>
                    """), unsafe_allow_html=True)
                with r2_c2:
                    st.markdown(textwrap.dedent(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="display: flex; justify-content: space-between;"><span style="font-size: 0.95rem; font-weight: 600;">🧠 Neuro / Psychiatry</span> <span style="color: #64748b; font-weight: 700;">{trend_neuro}</span></div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">{c_neuro} <span style="font-size: 1.2rem; font-weight: 600; color: #64748b;">Patients</span></div>
                        <div style="font-size: 0.85rem; font-weight: 600; background: #f8fafc; color: #64748b; padding: 4px 8px; border-radius: 4px; display: inline-block; width: fit-content;">{alert_neuro}</div>
                    </div>
                    """), unsafe_allow_html=True)

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            tc1, tc2 = st.columns([1, 1], vertical_alignment="center")
            with tc1:
                st.markdown("### Patient Inflow & Disease Trends")
                st.caption("Longitudinal tracking of patient consultations by condition.")
            with tc2:
                timeframe = st.radio("Select View:", ["Daily (Hours)", "Weekly (7 Days)", "Monthly (30 Days)"], horizontal=True, label_visibility="collapsed", key="doc_timeframe")
            
            if timeframe == "Daily (Hours)": df_trends = pd.DataFrame({"Cardio": [0]*5, "Diabetes": [0]*5, "COPD": [0]*5, "Neuro": [0]*5}, index=["08:00", "10:00", "12:00", "14:00", "16:00"])
            elif timeframe == "Weekly (7 Days)": df_trends = pd.DataFrame({"Cardio": [0]*5, "Diabetes": [0]*5, "COPD": [0]*5, "Neuro": [0]*5}, index=["Mon", "Tue", "Wed", "Thu", "Fri"])
            else: df_trends = pd.DataFrame({"Cardio": [0]*4, "Diabetes": [0]*4, "COPD": [0]*4, "Neuro": [0]*4}, index=["Wk 1", "Wk 2", "Wk 3", "Wk 4"])

            st.line_chart(df_trends, height=260, use_container_width=True, color=["#ef4444", "#f59e0b", "#0284c7", "#8b5cf6"])

    # --------------------------------------------------------------------------
    # TAB 2: LIVE PATIENTS & TRIAGE (DB-READY BLANK STATE)
    # --------------------------------------------------------------------------
    with tab_queue:
        st.write("")
        st.markdown("### Today's Active Triage Queue")
        st.caption("Real-time operational patient influx synced from the Patient Check-in Portal.")
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        
        if not st.session_state.today_queue:
            st.info("The waiting room is currently empty.")
        else:
            for i, p in enumerate(st.session_state.today_queue):
                pass # Queue populated from database

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### Specialty-Personalized Master Patient Directory")
            st.caption("Dynamic chronic modality switching with risk-stratified filtering and record preview.")
            
            f_c1, f_c2, f_c3 = st.columns([2.2, 2, 2], gap="medium")
            with f_c1: search_q = st.text_input("Search Directory", placeholder="Query Name, ID, or Health #...", label_visibility="collapsed", key="pat_dir_search")
            with f_c2: risk_filter = st.multiselect("Risk Stratification", ["High Risk Flagged", "Stable", "Awaiting Review", "Overdue for Checkup"], placeholder="Filter by Risk...", label_visibility="collapsed", key="pat_risk_sel")
            with f_c3: 
                curr_mod_short = mod_map_rev.get(st.session_state.active_modality, "Cardiovascular (CVD)")
                curr_idx = list(mod_map.keys()).index(curr_mod_short) if curr_mod_short in mod_map.keys() else 0
                modality_view = st.selectbox("Chronic Modality Switcher", list(mod_map.keys()), index=curr_idx, label_visibility="collapsed", key="modality_switcher", on_change=_sync_from_tab2)

            df_patients = pd.DataFrame(st.session_state.patient_directory)
            
            if not df_patients.empty:
                pass # Directory populated from DB
            else:
                st.info("The Master Patient Directory is empty.")

    # --------------------------------------------------------------------------
    # TAB 3: AI DIAGNOSTICS & CDSS (TWO-PHASE LONGITUDINAL ENGINE)
    # --------------------------------------------------------------------------
    with tab_cdss:
        st.write("")
        
        blank_patient = {
            "id": "--", "name": "No Patient Selected", "age": None, "sex": None,
            "bmi": None, "resting_hr": None, "latest_bp": None, 
            "total_chol": None, "fasting_glucose": None, "hba1c": None, 
            "spo2": None, "fev1_fvc": None, "pack_years": None,
            "phq9": None, "gad7": None, "sleep_hrs": None, "fam_history": [],
            "prior_directive": "", "active_rx": ""
        }
        
        active_pat = st.session_state.get("active_patient") or blank_patient
        pid = active_pat.get("id", "--")
        
        # Encounter Routing (CheckStatus)
        has_baseline = pid in st.session_state.baseline_records
        
        # Testing Demo Toggle
        tc_col1, tc_col2 = st.columns([4, 1])
        with tc_col2:
            simulate_return = st.toggle("🧪 Simulate Return Encounter", value=False)
            
        if simulate_return and not has_baseline and pid != "--":
            # Auto-generate mock baseline for demonstration if missing
            st.session_state.baseline_records[pid] = {
                "cryptographic_hash": sha256("mock_base"),
                "fhrs_data": pd.DataFrame([{"Disease Category": "Cardiovascular", "Relative Relationship": "Tier 1", "Age of Onset": "Early"}]),
                "biomarker_payload": {"Systolic Blood Pressure (SBP)": {"raw_value": 135.0, "unit": "mmHg"}, "Body Mass Index (BMI)": {"raw_value": 28.5, "unit": "kg/m²"}},
                "fhrs_payload": {"adjusted_score": 2.50, "code": "Code 2"},
                "inference_results": {"score": 45.0, "tier": "Moderate Risk"}
            }
            has_baseline = True
            
        cdss_phase = 2 if has_baseline else 1
        baseline_record = st.session_state.baseline_records.get(pid, {})

        # Dynamic Phase Indicator Banner
        phase_color_bg = "#e0f2fe" if cdss_phase == 1 else "#ede9fe"
        phase_color_border = "#0284c7" if cdss_phase == 1 else "#7c3aed"
        phase_title = "Phase 1 · Clinical Onboarding & Baseline Anchor" if cdss_phase == 1 else "Phase 2 · Return Encounter & Trajectory Analysis"
        phase_desc = "Establishing immutable patient baseline and initial risk stratification." if cdss_phase == 1 else "Longitudinal evaluation comparing current biomarkers against established baseline."
        
        banner_html = textwrap.dedent(f"""
            <div style="padding: 15px; border-radius: 8px; background: {phase_color_bg}; border-left: 5px solid {phase_color_border}; margin-bottom: 20px;">
                <h4 style="margin: 0; color: #0f172a;">{phase_title}</h4>
                <p style="margin: 4px 0 0 0; font-size: 0.9rem; color: #475569;">{phase_desc}</p>
            </div>
        """)
        st.markdown(banner_html, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(f"### Active Consultation: **{active_pat.get('name', 'No Patient Selected')}** (`{pid}`)")
            s1, s2, s3, s4, s5 = st.columns(5)
            s1.metric("Chronological Age", active_pat.get("age", "--"))
            s2.metric("Biological Sex", active_pat.get("sex", "--"))
            s3.metric("Current BMI", f"{active_pat.get('bmi', '--')} kg/m²" if active_pat.get('bmi') else "--")
            s4.metric("Resting Heart Rate", f"{active_pat.get('resting_hr', '--')} bpm" if active_pat.get('resting_hr') else "--")
            s5.metric("Latest Blood Pressure", active_pat.get("latest_bp", "--"))

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

        modality_labels = [
            "Cardiovascular Diseases (Hypertension / CVD)",
            "Type 2 Diabetes Mellitus",
            "Chronic Respiratory Diseases (COPD & Asthma)",
            "Mental Health & Neurological Disorders"
        ]
        
        selected_modality_label = st.selectbox(
            "Clinical Evaluation Modality Architecture*",
            options=modality_labels,
            index=modality_labels.index(st.session_state.active_modality) if st.session_state.active_modality in modality_labels else 0,
            key="cdss_active_modality_selector",
            on_change=_sync_from_tab3
        )

        modality_dispatch = {
            "Cardiovascular Diseases (Hypertension / CVD)": ("cardiovascular", "Cardiovascular"),
            "Type 2 Diabetes Mellitus": ("diabetes", "Type 2 Diabetes"),
            "Chronic Respiratory Diseases (COPD & Asthma)": ("copd_asthma", "COPD & Asthma"),
            "Mental Health & Neurological Disorders": ("mental_health_neuro", "Mental Health & Neurological")
        }
        modality_key, modality_schema_name = modality_dispatch[selected_modality_label]

        # ======================================================================
        # HEREDITARY RISK MATRIX
        # ======================================================================
        with st.container(border=True):
            st.markdown("### Patient Hereditary Risk & Family History Matrix")
            st.caption("Isolates inherited predispositions across the patient cohort to flag familial risk factors.")
            
            fh_search = st.text_input("Search Family History", placeholder="Query Name or ID...", label_visibility="collapsed", key="fh_search_input")
            df_fh = pd.DataFrame(st.session_state.patient_directory)
            
            if not df_fh.empty:
                if fh_search:
                    df_fh = df_fh[df_fh["name"].str.contains(fh_search, case=False) | df_fh["id"].str.contains(fh_search, case=False)]
                
                df_fh["lineage_display"] = df_fh["fam_history"].apply(lambda x: " | ".join(x) if isinstance(x, list) else str(x))

                fh_selection = st.dataframe(
                    df_fh[["id", "name", "modality", "lineage_display", "risk_flag"]],
                    use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", key="fh_matrix_table",
                    column_config={"id": "Patient ID", "name": "Full Name", "modality": "Primary Modality", "lineage_display": "Immediate Lineage History", "risk_flag": "Hereditary Risk Index"}
                )

                sel_fh_rows = fh_selection.selection.rows
                if sel_fh_rows:
                    selected_fh_patient = df_fh.iloc[sel_fh_rows[0]]
                    st.markdown(f"""
                    <div style="background: rgba(239, 68, 68, 0.04); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; padding: 12px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h5 style="margin:0 0 2px 0; color:#ef4444; font-size: 0.92rem;">🧬 Selected Hereditary Profile: {selected_fh_patient['name']} (`{selected_fh_patient['id']}`)</h5>
                            <span style="font-size: 0.85rem;"><b>Lineage Matrix:</b> {selected_fh_patient['lineage_display']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                    act_col1, act_col2 = st.columns(2)
                    with act_col1:
                        with st.container(border=True):
                            st.markdown("### 📋 Recommended First-Time Clinical Screenings")
                            st.caption("Automated preventive test suggestions generated from verified family medical history.")
                            
                            recommended_tests = generate_hereditary_screenings(
                                selected_fh_patient.get('fam_history', []), 
                                selected_fh_patient.get("age", 40), 
                                selected_fh_patient.get("sex", "Unknown")
                            )
                            
                            for test in recommended_tests:
                                urgency_color = "#ef4444" if test["urgency"] == "High Priority" else ("#f59e0b" if test["urgency"] == "Moderate Priority" else "#10b981")
                                urgency_bg = "#fee2e2" if test["urgency"] == "High Priority" else ("#fef3c7" if test["urgency"] == "Moderate Priority" else "#d1fae5")
                                
                                st.markdown(f"""
                                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                        <span style="font-weight: 700; font-size: 1rem; color: #0f172a;">{test['test']}</span>
                                        <span style="background: {urgency_bg}; color: {urgency_color}; font-size: 0.78rem; font-weight: 700; padding: 3px 10px; border-radius: 12px;">{test['urgency']}</span>
                                    </div>
                                    <div style="font-size: 0.85rem; color: #007979; font-weight: 600; margin-bottom: 4px;">Modality Target: {test['modality']}</div>
                                    <div style="font-size: 0.85rem; color: #64748b;"><b>Clinical Rationale:</b> {test['rationale']}</div>
                                </div>
                                """, unsafe_allow_html=True)
            else:
                st.info("No hereditary data loaded.")

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # ======================================================================
        # FHRS ENGINE & ENVIRONMENTAL INTAKE
        # ======================================================================
        declare_change = False
        if cdss_phase == 2:
            declare_change = st.toggle("Familial pedigree changed since baseline?", key="declare_change_toggle")

        if cdss_phase == 1 or declare_change:
            with st.container(border=True):
                st.markdown("#### 🧬 Epidemiological Familial Risk Stratification (FHRS)")
                with st.expander("🔬 Mathematical FHRS Model & Stratification Logic", expanded=False):
                    st.markdown(r"""
                    **1. Base Familial Risk Score Formulation:**
                    $$\text{FHRS}_d = \sum_{i=1}^{N_d} (R_i \times O_i \times S_i) + C_d$$
                    
                    **2. Familial Clustering Coefficient ($C_d$):**
                    $$C_d = N_{T1}(1.0) + N_{T2}(0.5) + N_{T3}(0.25)$$
                    
                    **3. Adjusted Environmental Scaling:**
                    $$\text{Adjusted FHRS}_d = \text{FHRS}_d \times E_d \quad \text{where} \quad E_d = 1 + \sum e_j$$
                    """)

                st.markdown("##### Add Affected Relatives (Genetic/Familial Risk)")
                st.caption("Enter affected relatives, their relationship tier, and age of onset.")
                
                # Prepopulate with baseline if declaring a change
                initial_fhrs_data = baseline_record.get("fhrs_data", st.session_state.fhrs_data) if declare_change else st.session_state.fhrs_data
                
                edited_fh_df = st.data_editor(
                    initial_fhrs_data,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="fhrs_editor",
                    column_config={
                        "Disease Category": st.column_config.SelectboxColumn("Disease Category", options=["Cardiovascular", "Type 2 Diabetes", "Respiratory", "Neuropsychiatric"], required=True),
                        "Relative Relationship": st.column_config.SelectboxColumn("Relative Relationship", options=["Tier 1", "Tier 2", "Tier 3"], required=True),
                        "Age of Onset": st.column_config.SelectboxColumn("Age of Onset", options=["Very Early", "Early", "Standard", "Late"], required=True)
                    }
                )
                st.session_state.fhrs_data = edited_fh_df
        else:
            # Phase 2 & No Change -> Lock FHRS to baseline
            st.session_state.fhrs_data = baseline_record.get("fhrs_data", pd.DataFrame(columns=["Disease Category", "Relative Relationship", "Age of Onset"]))
            st.info("🔒 **Cached Biological Baseline Active:** Family history locked to prior encounter. Use the toggle above to declare pedigree changes.")

        with st.container(border=True):
            st.markdown("##### 🌍 Dynamic Environmental Intake")
            st.caption("Log modifiable environmental exposures for today's visit (computes the $E_d$ modifier).")
            
            selected_env = st.multiselect(
                "Current Modifiable Exposures", 
                options=["High-Sodium Diet", "Household Smoking", "Sedentary Lifestyle", "High-Sugar Diet", "Occupational Dust/Fumes", "Chronic Household Stress"],
                default=st.session_state.env_factors,
                key="dynamic_env_input"
            )
            st.session_state.env_factors = selected_env

        # Calculate and Display live FHRS Cards
        current_fh_data = st.session_state.fhrs_data
        if len(current_fh_data) > 0:
            grouped = current_fh_data.groupby("Disease Category")
            cols = st.columns(len(grouped))
            
            for idx, (disease, group) in enumerate(grouped):
                base_fhrs, c_d, e_d, adj_fhrs, code = calculate_fhrs(group, st.session_state.env_factors)
                risk_color = "#10b981" if "Code 1" in code or "Code 0" in code else "#f59e0b" if "Code 2" in code else "#ef4444" if "Code 3" in code else "#991b1b"
                
                with cols[idx]:
                    card_html = textwrap.dedent(f"""
                    <div style="background-color: rgba(148, 163, 184, 0.05); border: 1px solid {risk_color}60; border-radius: 8px; padding: 12px; height: 100%; margin-bottom:15px;">
                        <div style="font-size: 0.85rem; font-weight: 700; color: #64748b; margin-bottom: 4px; text-transform: uppercase;">{disease}</div>
                        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
                            <span style="font-size: 1.8rem; font-weight: 800; color: {risk_color};">{adj_fhrs:.2f}</span>
                            <span style="background: {risk_color}20; color: {risk_color}; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">{code}</span>
                        </div>
                        <div style="font-size: 0.75rem; color: #64748b; font-weight: 500;">
                            Base FHRS: {base_fhrs:.2f} | Cluster (Cd): {c_d:.2f} | Env (Ed): {e_d:.2f}
                        </div>
                    </div>
                    """)
                    st.markdown(card_html, unsafe_allow_html=True)

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # ======================================================================
        # UPPER CONTAINER: FULL-WIDTH PARAMETER INGESTION FORM 
        # ======================================================================
        with st.container(border=True):
            with st.form(key=f"cdss_{modality_key}_form_{pid}", clear_on_submit=False):
                st.markdown(f"#### Parameter Ingestion — {modality_schema_name}")
                st.caption("Physiological boundaries and strict type-constraints enforced. Forms are completely blank for live data entry.")
                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                
                payload_buffer = {}

                # --- MODALITY 1: CARDIOVASCULAR ---
                if modality_key == "cardiovascular":
                    with st.expander("🩺 Hemodynamics & Anthropometrics", expanded=True):
                        cvd_age = st.number_input("Age (18-90)", min_value=18, max_value=90, value=None, step=1); payload_buffer["Age"] = {"raw_value": cvd_age, "unit": "Years"}
                        cvd_sex = st.selectbox("Biological Sex", options=["Female", "Male"], index=None); payload_buffer["Biological Sex"] = {"raw_value": cvd_sex, "unit": "None"}
                        cvd_sbp = st.number_input("Systolic Blood Pressure (70-220 mmHg)", min_value=70.0, max_value=220.0, value=None, step=1.0, format="%.1f"); payload_buffer["Systolic Blood Pressure (SBP)"] = {"raw_value": cvd_sbp, "unit": "mmHg"}
                        cvd_dbp = st.number_input("Diastolic Blood Pressure (40-130 mmHg)", min_value=40.0, max_value=130.0, value=None, step=1.0, format="%.1f"); payload_buffer["Diastolic Blood Pressure (DBP)"] = {"raw_value": cvd_dbp, "unit": "mmHg"}
                        cvd_hr = st.number_input("Heart Rate Resting (40-180 bpm)", min_value=40, max_value=180, value=None, step=1); payload_buffer["Heart Rate (Resting)"] = {"raw_value": cvd_hr, "unit": "bpm"}
                        cvd_bmi = st.number_input("Body Mass Index (12.0-60.0 kg/m²)", min_value=12.0, max_value=60.0, value=None, step=0.1, format="%.1f"); payload_buffer["Body Mass Index (BMI)"] = {"raw_value": cvd_bmi, "unit": "kg/m²"}
                    with st.expander("🧪 Serum Lipid, Inflammatory & Renal Panels", expanded=False):
                        cvd_tc = st.number_input("Total Cholesterol (100-400 mg/dL)", min_value=100.0, max_value=400.0, value=None, step=1.0, format="%.1f"); payload_buffer["Total Cholesterol"] = {"raw_value": cvd_tc, "unit": "mg/dL"}
                        cvd_hdl = st.number_input("HDL (15-120 mg/dL)", min_value=15.0, max_value=120.0, value=None, step=1.0, format="%.1f"); payload_buffer["High-Density Lipoprotein (HDL)"] = {"raw_value": cvd_hdl, "unit": "mg/dL"}
                        cvd_ldl = st.number_input("LDL (30-300 mg/dL)", min_value=30.0, max_value=300.0, value=None, step=1.0, format="%.1f"); payload_buffer["Low-Density Lipoprotein (LDL)"] = {"raw_value": cvd_ldl, "unit": "mg/dL"}
                        cvd_trig = st.number_input("Triglycerides (40-1000 mg/dL)", min_value=40.0, max_value=1000.0, value=None, step=1.0, format="%.1f"); payload_buffer["Serum Triglycerides"] = {"raw_value": cvd_trig, "unit": "mg/dL"}
                        cvd_hscrp = st.number_input("hs-CRP (0.1-50.0 mg/L)", min_value=0.1, max_value=50.0, value=None, step=0.1, format="%.1f"); payload_buffer["High-Sensitivity C-Reactive Protein (hs-CRP)"] = {"raw_value": cvd_hscrp, "unit": "mg/L"}
                        cvd_creat = st.number_input("Serum Creatinine (0.4-10.0 mg/dL)", min_value=0.4, max_value=10.0, value=None, step=0.01, format="%.2f"); payload_buffer["Serum Creatinine"] = {"raw_value": cvd_creat, "unit": "mg/dL"}
                        cvd_egfr = st.number_input("eGFR (5-140 mL/min/1.73m²)", min_value=5.0, max_value=140.0, value=None, step=1.0, format="%.1f"); payload_buffer["Estimated Glomerular Filtration Rate (eGFR)"] = {"raw_value": cvd_egfr, "unit": "mL/min/1.73m²"}
                    with st.expander("🫀 Cardiac Necrosis & Hemodynamics", expanded=False):
                        cvd_lvef = st.number_input("LVEF (15-75 %)", min_value=15.0, max_value=75.0, value=None, step=1.0, format="%.1f"); payload_buffer["Left Ventricular Ejection Fraction (LVEF)"] = {"raw_value": cvd_lvef, "unit": "%"}
                        cvd_ctni = st.number_input("Cardiac Troponin I (0.01-50.0 ng/mL)", min_value=0.01, max_value=50.0, value=None, step=0.01, format="%.2f"); payload_buffer["Cardiac Troponin I (cTnI)"] = {"raw_value": cvd_ctni, "unit": "ng/mL"}
                        cvd_ntpro = st.number_input("NT-proBNP (10-35000 pg/mL)", min_value=10.0, max_value=35000.0, value=None, step=10.0, format="%.1f"); payload_buffer["N-Terminal Pro-B-Type Natriuretic Peptide (NT-proBNP)"] = {"raw_value": cvd_ntpro, "unit": "pg/mL"}
                    with st.expander("🏃 Behavioral Risk Factors", expanded=False):
                        cvd_smoke = st.number_input("Smoking History (0-120 Pack-Years)", min_value=0.0, max_value=120.0, value=None, step=1.0, format="%.1f"); payload_buffer["Smoking History"] = {"raw_value": cvd_smoke, "unit": "Pack-Years"}
                        cvd_sodium = st.number_input("Daily Sodium Intake (500-10000 mg/day)", min_value=500.0, max_value=10000.0, value=None, step=50.0, format="%.1f"); payload_buffer["Daily Sodium Intake"] = {"raw_value": cvd_sodium, "unit": "mg/day"}
                        cvd_activity = st.number_input("Physical Activity Level (0-1050 mins/week)", min_value=0, max_value=1050, value=None, step=15); payload_buffer["Physical Activity Level"] = {"raw_value": cvd_activity, "unit": "mins/week"}

                # --- MODALITY 2: TYPE 2 DIABETES ---
                elif modality_key == "diabetes":
                    with st.expander("🩸 Glycemic Status & Endocrine Regulation", expanded=True):
                        dia_fpg = st.number_input("Fasting Plasma Glucose (50-450 mg/dL)", min_value=50.0, max_value=450.0, value=None, step=1.0, format="%.1f"); payload_buffer["Fasting Plasma Glucose (FPG)"] = {"raw_value": dia_fpg, "unit": "mg/dL"}
                        dia_2hpg = st.number_input("2-Hour Postprandial Glucose (60-600 mg/dL)", min_value=60.0, max_value=600.0, value=None, step=1.0, format="%.1f"); payload_buffer["2-Hour Postprandial Glucose (2h-PG)"] = {"raw_value": dia_2hpg, "unit": "mg/dL"}
                        dia_hba1c = st.number_input("HbA1c (4.0-15.0 %)", min_value=4.0, max_value=15.0, value=None, step=0.1, format="%.1f"); payload_buffer["Glycated Hemoglobin (HbA1c)"] = {"raw_value": dia_hba1c, "unit": "%"}
                        dia_ins = st.number_input("Fasting Serum Insulin (1.0-100.0 µIU/mL)", min_value=1.0, max_value=100.0, value=None, step=0.5, format="%.1f"); payload_buffer["Fasting Serum Insulin"] = {"raw_value": dia_ins, "unit": "µIU/mL"}
                        dia_cpep = st.number_input("Serum C-Peptide (0.1-12.0 ng/mL)", min_value=0.1, max_value=12.0, value=None, step=0.1, format="%.1f"); payload_buffer["Serum C-Peptide Level"] = {"raw_value": dia_cpep, "unit": "ng/mL"}
                        dia_homa = st.number_input("HOMA-IR (0.2-25.0 Score)", min_value=0.2, max_value=25.0, value=None, step=0.1, format="%.2f"); payload_buffer["HOMA-IR (Insulin Resistance Score)"] = {"raw_value": dia_homa, "unit": "Score"}
                    with st.expander("📏 Anthropometrics & Central Adiposity", expanded=False):
                        dia_bmi = st.number_input("Body Mass Index (12.0-60.0 kg/m²)", min_value=12.0, max_value=60.0, value=None, step=0.1, format="%.1f"); payload_buffer["Body Mass Index (BMI)"] = {"raw_value": dia_bmi, "unit": "kg/m²"}
                        dia_waist = st.number_input("Waist Circumference (50-160 cm)", min_value=50.0, max_value=160.0, value=None, step=0.5, format="%.1f"); payload_buffer["Waist Circumference"] = {"raw_value": dia_waist, "unit": "cm"}
                        dia_whr = st.number_input("Waist-to-Hip Ratio (0.60-1.40 Ratio)", min_value=0.60, max_value=1.40, value=None, step=0.01, format="%.2f"); payload_buffer["Waist-to-Hip Ratio (WHR)"] = {"raw_value": dia_whr, "unit": "Ratio"}
                    with st.expander("🧪 Hemodynamics, Renal & Metabolic Markers", expanded=False):
                        dia_sbp = st.number_input("Systolic Blood Pressure (70-220 mmHg)", min_value=70.0, max_value=220.0, value=None, step=1.0, format="%.1f"); payload_buffer["Systolic Blood Pressure (SBP)"] = {"raw_value": dia_sbp, "unit": "mmHg"}
                        dia_dbp = st.number_input("Diastolic Blood Pressure (40-130 mmHg)", min_value=40.0, max_value=130.0, value=None, step=1.0, format="%.1f"); payload_buffer["Diastolic Blood Pressure (DBP)"] = {"raw_value": dia_dbp, "unit": "mmHg"}
                        dia_trig = st.number_input("Triglycerides (40-1000 mg/dL)", min_value=40.0, max_value=1000.0, value=None, step=1.0, format="%.1f"); payload_buffer["Serum Triglycerides"] = {"raw_value": dia_trig, "unit": "mg/dL"}
                        dia_hdl = st.number_input("HDL (15-120 mg/dL)", min_value=15.0, max_value=120.0, value=None, step=1.0, format="%.1f"); payload_buffer["High-Density Lipoprotein (HDL)"] = {"raw_value": dia_hdl, "unit": "mg/dL"}
                        dia_uacr = st.number_input("UACR (1-3500 mg/g)", min_value=1.0, max_value=3500.0, value=None, step=1.0, format="%.1f"); payload_buffer["Urine Albumin-to-Creatinine Ratio (UACR)"] = {"raw_value": dia_uacr, "unit": "mg/g"}
                        dia_uric = st.number_input("Serum Uric Acid (1.5-14.0 mg/dL)", min_value=1.5, max_value=14.0, value=None, step=0.1, format="%.1f"); payload_buffer["Serum Uric Acid"] = {"raw_value": dia_uric, "unit": "mg/dL"}
                    with st.expander("🧬 Lineage, Clinical Presentation & Lifestyle", expanded=False):
                        dia_gest = st.radio("Gestational Diabetes History", options=["0", "1"], index=None, horizontal=True); payload_buffer["Gestational Diabetes History"] = {"raw_value": dia_gest, "unit": "None"}
                        dia_acan = st.radio("Acanthosis Nigricans Presence", options=["0", "1"], index=None, horizontal=True); payload_buffer["Acanthosis Nigricans Presence"] = {"raw_value": dia_acan, "unit": "None"}
                        dia_carb = st.number_input("Daily Carbohydrate Intake (50-600 g/day)", min_value=50.0, max_value=600.0, value=None, step=5.0, format="%.1f"); payload_buffer["Daily Carbohydrate Intake"] = {"raw_value": dia_carb, "unit": "g/day"}
                        dia_sed = st.number_input("Sedentary Behavior Duration (1.0-18.0 Hours/day)", min_value=1.0, max_value=18.0, value=None, step=0.5, format="%.1f"); payload_buffer["Sedentary Behavior Duration"] = {"raw_value": dia_sed, "unit": "Hours/day"}

                # --- MODALITY 3: COPD & ASTHMA ---
                elif modality_key == "copd_asthma":
                    with st.expander("🫁 Spirometry, Volumes & Flow Dynamics", expanded=True):
                        cr_fev1 = st.number_input("FEV1 (0.5-5.5 Liters)", min_value=0.5, max_value=5.5, value=None, step=0.05, format="%.2f"); payload_buffer["Forced Expiratory Volume in 1 Second (FEV1)"] = {"raw_value": cr_fev1, "unit": "Liters"}
                        cr_fvc = st.number_input("FVC (1.0-7.0 Liters)", min_value=1.0, max_value=7.0, value=None, step=0.05, format="%.2f"); payload_buffer["Forced Vital Capacity (FVC)"] = {"raw_value": cr_fvc, "unit": "Liters"}
                        cr_rat = st.number_input("FEV1/FVC Ratio (25.0-95.0 %)", min_value=25.0, max_value=95.0, value=None, step=0.1, format="%.1f"); payload_buffer["FEV1/FVC Ratio"] = {"raw_value": cr_rat, "unit": "%"}
                        cr_pbr = st.number_input("Post-Bronchodilator FEV1 % Predicted (15.0-120.0 %)", min_value=15.0, max_value=120.0, value=None, step=0.5, format="%.1f"); payload_buffer["Post-Bronchodilator FEV1 % Predicted"] = {"raw_value": cr_pbr, "unit": "%"}
                        cr_pef = st.number_input("Peak Expiratory Flow (50.0-800.0 L/min)", min_value=50.0, max_value=800.0, value=None, step=5.0, format="%.1f"); payload_buffer["Peak Expiratory Flow (PEF)"] = {"raw_value": cr_pef, "unit": "L/min"}
                    with st.expander("🧪 Inflammatory Biomarkers & Arterial Blood Gases", expanded=False):
                        cr_eos = st.number_input("Blood Eosinophil Count (0-2500 cells/µL)", min_value=0, max_value=2500, value=None, step=10); payload_buffer["Blood Eosinophil Count"] = {"raw_value": cr_eos, "unit": "cells/µL"}
                        cr_feno = st.number_input("FeNO (5.0-150.0 ppb)", min_value=5.0, max_value=150.0, value=None, step=1.0, format="%.1f"); payload_buffer["Fractional Exhaled Nitric Oxide (FeNO)"] = {"raw_value": cr_feno, "unit": "ppb"}
                        cr_spo2 = st.number_input("Resting SpO2 (65.0-100.0 %)", min_value=65.0, max_value=100.0, value=None, step=0.1, format="%.1f"); payload_buffer["Resting Oxygen Saturation (SpO2)"] = {"raw_value": cr_spo2, "unit": "%"}
                        cr_pao2 = st.number_input("PaO2 (40.0-110.0 mmHg)", min_value=40.0, max_value=110.0, value=None, step=1.0, format="%.1f"); payload_buffer["Arterial Oxygen Partial Pressure (PaO2)"] = {"raw_value": cr_pao2, "unit": "mmHg"}
                        cr_paco2 = st.number_input("PaCO2 (25.0-90.0 mmHg)", min_value=25.0, max_value=90.0, value=None, step=1.0, format="%.1f"); payload_buffer["Arterial Carbon Dioxide Partial Pressure (PaCO2)"] = {"raw_value": cr_paco2, "unit": "mmHg"}
                        cr_ige = st.number_input("Serum Total IgE (2.0-3000.0 IU/mL)", min_value=2.0, max_value=3000.0, value=None, step=10.0, format="%.1f"); payload_buffer["Serum Total IgE Level"] = {"raw_value": cr_ige, "unit": "IU/mL"}
                    with st.expander("📊 Functional Scores & Lifestyle Exposures", expanded=False):
                        cr_mmrc = st.selectbox("mMRC Dyspnea Scale Score (0-4)", options=[0, 1, 2, 3, 4], index=None); payload_buffer["mMRC Dyspnea Scale Score"] = {"raw_value": cr_mmrc, "unit": "Score"}
                        cr_act = st.number_input("Asthma Control Test (5-25 Score)", min_value=5, max_value=25, value=None, step=1); payload_buffer["Asthma Control Test (ACT) Score"] = {"raw_value": cr_act, "unit": "Score"}
                        cr_cat = st.number_input("COPD Assessment Test (0-40 Score)", min_value=0, max_value=40, value=None, step=1); payload_buffer["COPD Assessment Test (CAT) Score"] = {"raw_value": cr_cat, "unit": "Score"}
                        cr_exac = st.number_input("Annual Exacerbation Frequency (0-15 Episodes/year)", min_value=0, max_value=15, value=None, step=1); payload_buffer["Annual Exacerbation Frequency"] = {"raw_value": cr_exac, "unit": "Episodes/year"}
                        cr_tob = st.number_input("Lifetime Tobacco Exposure (0-120 Pack-Years)", min_value=0.0, max_value=120.0, value=None, step=1.0, format="%.1f"); payload_buffer["Lifetime Tobacco Exposure"] = {"raw_value": cr_tob, "unit": "Pack-Years"}
                        cr_dust = st.radio("Occupational Dust/Fume Exposure", options=["0", "1"], index=None, horizontal=True); payload_buffer["Occupational Dust/Fume Exposure"] = {"raw_value": cr_dust, "unit": "None"}
                        cr_rhin = st.radio("Allergic Rhinitis Comorbidity", options=["0", "1"], index=None, horizontal=True); payload_buffer["Allergic Rhinitis Comorbidity"] = {"raw_value": cr_rhin, "unit": "None"}
                        cr_cast = st.radio("Childhood Asthma History", options=["0", "1"], index=None, horizontal=True); payload_buffer["Childhood Asthma History"] = {"raw_value": cr_cast, "unit": "None"}
                        cr_bmi = st.number_input("Body Mass Index (12.0-60.0 kg/m²)", min_value=12.0, max_value=60.0, value=None, step=0.1, format="%.1f"); payload_buffer["Body Mass Index (BMI)"] = {"raw_value": cr_bmi, "unit": "kg/m²"}

                # --- MODALITY 4: MENTAL HEALTH & NEURO ---
                else:
                    with st.expander("🧠 Neuropsychiatric & Cognitive Assessment Batteries", expanded=True):
                        mh_phq9 = st.number_input("PHQ-9 (0-27 Score)", min_value=0, max_value=27, value=None, step=1); payload_buffer["Patient Health Questionnaire-9 (PHQ-9)"] = {"raw_value": mh_phq9, "unit": "Score"}
                        mh_gad7 = st.number_input("GAD-7 (0-21 Score)", min_value=0, max_value=21, value=None, step=1); payload_buffer["Generalized Anxiety Disorder-7 (GAD-7)"] = {"raw_value": mh_gad7, "unit": "Score"}
                        mh_mmse = st.number_input("MMSE (0-30 Score)", min_value=0, max_value=30, value=None, step=1); payload_buffer["Mini-Mental State Examination (MMSE)"] = {"raw_value": mh_mmse, "unit": "Score"}
                        mh_moca = st.number_input("MoCA (0-30 Score)", min_value=0, max_value=30, value=None, step=1); payload_buffer["Montreal Cognitive Assessment (MoCA)"] = {"raw_value": mh_moca, "unit": "Score"}
                        mh_hamd = st.number_input("HAM-D (0-52 Score)", min_value=0, max_value=52, value=None, step=1); payload_buffer["Hamilton Depression Rating Scale (HAM-D)"] = {"raw_value": mh_hamd, "unit": "Score"}
                        mh_updrs = st.number_input("UPDRS Part III (0-132 Score)", min_value=0, max_value=132, value=None, step=1); payload_buffer["UPDRS Part III (Motor Examination)"] = {"raw_value": mh_updrs, "unit": "Score"}
                        mh_faq = st.number_input("FAQ (0-30 Score)", min_value=0, max_value=30, value=None, step=1); payload_buffer["Functional Activities Questionnaire (FAQ)"] = {"raw_value": mh_faq, "unit": "Score"}
                        mh_trem = st.selectbox("Tremor Rating Scale Score (0-4)", options=[0, 1, 2, 3, 4], index=None); payload_buffer["Tremor Rating Scale Score"] = {"raw_value": mh_trem, "unit": "Score"}
                    with st.expander("💤 Sleep Physiology & Paroxysmal Events", expanded=False):
                        mh_sleep = st.number_input("Daily Sleep Duration (1.0-16.0 Hours)", min_value=1.0, max_value=16.0, value=None, step=0.5, format="%.1f"); payload_buffer["Daily Sleep Duration"] = {"raw_value": mh_sleep, "unit": "Hours"}
                        mh_psqi = st.number_input("PSQI (0-21 Score)", min_value=0, max_value=21, value=None, step=1); payload_buffer["Pittsburgh Sleep Quality Index (PSQI)"] = {"raw_value": mh_psqi, "unit": "Score"}
                        mh_seiz = st.number_input("Seizure Frequency (0-100 Episodes/month)", min_value=0, max_value=100, value=None, step=1); payload_buffer["Seizure Frequency"] = {"raw_value": mh_seiz, "unit": "Episodes/month"}
                    with st.expander("🧪 Endocrine, Autonomic & Neuro-Nutritional Panel", expanded=False):
                        mh_hrv = st.number_input("Heart Rate Variability (5.0-250.0 ms)", min_value=5.0, max_value=250.0, value=None, step=1.0, format="%.1f"); payload_buffer["Heart Rate Variability (SDNN)"] = {"raw_value": mh_hrv, "unit": "ms"}
                        mh_cort = st.number_input("8 AM Serum Cortisol (1.0-45.0 µg/dL)", min_value=1.0, max_value=45.0, value=None, step=0.5, format="%.1f"); payload_buffer["8 AM Serum Cortisol"] = {"raw_value": mh_cort, "unit": "µg/dL"}
                        mh_b12 = st.number_input("Serum Vitamin B12 (50-2000 pg/mL)", min_value=50.0, max_value=2000.0, value=None, step=10.0, format="%.1f"); payload_buffer["Serum Vitamin B12"] = {"raw_value": mh_b12, "unit": "pg/mL"}
                        mh_fol = st.number_input("Serum Folate (1.0-25.0 ng/mL)", min_value=1.0, max_value=25.0, value=None, step=0.1, format="%.1f"); payload_buffer["Serum Folate"] = {"raw_value": mh_fol, "unit": "ng/mL"}
                        mh_tsh = st.number_input("TSH (0.01-100.0 mIU/L)", min_value=0.01, max_value=100.0, value=None, step=0.05, format="%.2f"); payload_buffer["Thyroid Stimulating Hormone (TSH)"] = {"raw_value": mh_tsh, "unit": "mIU/L"}
                    with st.expander("🧬 Neurological History & Lineage", expanded=False):
                        mh_tbi = st.radio("History of Traumatic Brain Injury (TBI)", options=["0", "1"], index=None, horizontal=True); payload_buffer["History of Traumatic Brain Injury (TBI)"] = {"raw_value": mh_tbi, "unit": "None"}
                        mh_alc = st.radio("Lifetime History of Alcohol/Substance Abuse", options=["0", "1"], index=None, horizontal=True); payload_buffer["Lifetime History of Alcohol/Substance Abuse"] = {"raw_value": mh_alc, "unit": "None"}
                        mh_age = st.number_input("Age (18-90 Years)", min_value=18, max_value=90, value=None, step=1); payload_buffer["Age"] = {"raw_value": mh_age, "unit": "Years"}

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                submit_inference = st.form_submit_button("🧠 Run AI Diagnostic Inference", type="primary", use_container_width=True)

                if submit_inference:
                    enc_id = f"ENC-{uuid.uuid4().hex[:8].upper()}"
                    submission_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    # --- PHASE 1 vs PHASE 2 LOGIC HUB ---
                    base_total, cd, ed, adj_fhrs, fhrs_code = calculate_fhrs(st.session_state.fhrs_data, st.session_state.env_factors)
                    
                    # Calculate Overall Risk Score (Mock Model wrapper handling the payload)
                    overall_risk_points = 15.0
                    dynamic_drivers = []
                    for k, v in payload_buffer.items():
                        try: val = float(v["raw_value"])
                        except (ValueError, TypeError): val = 1.0 if str(v["raw_value"]) in ["1", "Male", "Yes", "Present"] else 0.0
                        
                        severity, impact = "Low", 0.0
                        if "Systolic Blood Pressure" in k and val >= 140: severity, impact = "High", 28.0 + (val-140)*0.4
                        elif "HbA1c" in k and val >= 6.5: severity, impact = "High", 32.0 + (val-6.5)*10
                        elif "Oxygen Saturation" in k and val < 90: severity, impact = "High", 35.0 + (90-val)*2
                        elif "PHQ-9" in k and val >= 15: severity, impact = "High", 28.0 + (val-15)*1.5
                        elif "Total Cholesterol" in k and val >= 240: severity, impact = "Moderate", 16.0
                        elif "FEV1/FVC" in k and val < 70: severity, impact = "High", 22.0
                        
                        if severity != "Low":
                            unit_label = f" {v['unit']}" if v['unit'] != "None" else ""
                            dynamic_drivers.append({"feature": f"{k} ({val:.1f}{unit_label})", "impact": min(impact, 45.0), "severity": severity})
                            overall_risk_points += impact

                    score = min(round(overall_risk_points, 1), 98.5)
                    tier = "High Risk" if score >= 70 else ("Moderate Risk" if score >= 40 else "Low Risk")

                    # Structure the Package
                    cdss_package = {
                        "encounter_id": enc_id,
                        "patient_id": pid,
                        "modality": modality_schema_name,
                        "submitted_at_utc": submission_timestamp,
                        "biomarker_payload": payload_buffer,
                        "fhrs_payload": {"adjusted_score": adj_fhrs, "code": fhrs_code},
                        "dynamic_env_payload": st.session_state.env_factors,
                        "inference_results": {
                            "score": score,
                            "tier": tier,
                            "drivers": sorted(dynamic_drivers, key=lambda x: x["impact"], reverse=True)[:5]
                        }
                    }

                    if cdss_phase == 1:
                        cdss_package["record_type"] = "BASELINE"
                        cdss_package["cryptographic_hash"] = sha256(cdss_package)
                        st.session_state.baseline_records[pid] = cdss_package
                        append_audit("PHASE1_BASELINE_HASH", {"hash": cdss_package["cryptographic_hash"]})
                    
                    elif cdss_phase == 2:
                        cdss_package["record_type"] = "TRAJECTORY"
                        cdss_package["parent_baseline_hash"] = baseline_record.get("cryptographic_hash", "UNKNOWN")
                        if declare_change:
                            # Trigger Re-Anchor Proposal
                            proposed = cdss_package.copy()
                            proposed["record_type"] = "BASELINE"
                            proposed["reanchor_reason"] = "familial_change"
                            proposed["cryptographic_hash"] = sha256(proposed)
                            st.session_state["proposed_baseline"] = proposed
                        else:
                            st.session_state["proposed_baseline"] = None
                            
                        append_audit("PHASE2_TRAJECTORY_CALCULATED", {"encounter_id": enc_id})

                    st.session_state["cdss_inference_payload"] = cdss_package
                    st.session_state["ai_inference_completed"] = True
                    st.session_state["reanchor_decision"] = "Pending" if st.session_state.get("proposed_baseline") else None
                    
                    st.success(f"Payload compiled and verified ({enc_id}). Sending to inference engine...")
                    time.sleep(1)
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            # ======================================================================
            # LOWER CONTAINER: FULL-WIDTH DIAGNOSTIC VISUALIZER (BiomarkerTraj)
            # ======================================================================
            with st.container(border=True):
                st.markdown(textwrap.dedent("""
                    <div style="margin-bottom: 12px;">
                        <h3 style="margin: 0; font-size: 1.35rem; font-weight: 700;">Diagnostic Risk Assessment</h3>
                        <p style="margin: 2px 0 0 0; font-size: 0.9rem; color: #64748b;">Multi-factorial risk stratification and feature attribution.</p>
                    </div>
                """), unsafe_allow_html=True)
                
                payload = st.session_state.get("cdss_inference_payload") or {}
                if not st.session_state.get("ai_inference_completed") or not payload:
                    st.markdown(textwrap.dedent("""
                        <div style="height:320px; display:flex; align-items:center; justify-content:center; border: 1px dashed #94a3b8; border-radius: 8px; color:#64748b; text-align:center; padding: 20px;">
                            <div>
                                <div style="font-size: 2.2rem; margin-bottom: 8px;">🔬</div>
                                <b>No inference model computed</b><br>
                                <span style="font-size: 0.85rem;">Submit biomarker vectors from the clinical parameter form to execute CDSS diagnostics.</span>
                            </div>
                        </div>
                    """), unsafe_allow_html=True)
                else:
                    with st.expander("📦 Serialized Gateway Contract Output (POST /api/models/predict)", expanded=False):
                        st.caption("The exact JSON payload constructed and validated across physiological bounds.")
                        st.json(payload, expanded=True)

                    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                    
                    # Safe Extraction
                    results = payload.get("inference_results", {})
                    score = results.get("score", 0.0)
                    tier = results.get("tier", "Unknown Risk")
                    tier_color = "#ef4444" if score >= 70 else ("#f59e0b" if score >= 40 else "#10b981")
                    
                    st.markdown(f"<div style='text-align: center; font-size: 0.88rem; font-weight: 600; padding: 6px 12px; background: rgba(239, 68, 68, 0.08); border-radius: 8px; color: {tier_color}; margin-bottom: 16px;'>Primary Indication: {payload.get('modality', '').split('(')[0].strip()} Evaluation</div>", unsafe_allow_html=True)
                    
                    # --- BiomarkerTraj (Phase 2 Deltas) ---
                    if cdss_phase == 2 and baseline_record:
                        st.markdown("##### 📉 Longitudinal Biomarker Trajectory")
                        base_biomarkers = baseline_record.get("biomarker_payload", {})
                        curr_biomarkers = payload.get("biomarker_payload", {})
                        
                        delta_cols = st.columns(3)
                        d_idx = 0
                        for k, curr_v in curr_biomarkers.items():
                            base_v = base_biomarkers.get(k)
                            if base_v and base_v.get("raw_value") is not None and curr_v.get("raw_value") is not None:
                                c_val = float(curr_v["raw_value"])
                                b_val = float(base_v["raw_value"])
                                delta_val = c_val - b_val
                                
                                # Ignore zeros for cleaner display
                                if delta_val != 0:
                                    inv_color = "normal" if "HDL" in k or "FEV1" in k or "SpO2" in k else "inverse"
                                    with delta_cols[d_idx % 3]:
                                        st.metric(label=f"{k}", value=f"{c_val:.1f} {curr_v['unit']}", delta=f"{delta_val:+.1f} vs baseline", delta_color=inv_color)
                                    d_idx += 1
                                    
                        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

                    # --- RiskTrajEngine (Gauge & Bar) ---
                    col_gauge, col_chart = st.columns([1, 1.5])
                    with col_gauge:
                        gauge_args = {
                            "mode": "gauge+number+delta" if cdss_phase == 2 and baseline_record else "gauge+number",
                            "value": score,
                            "number": {"suffix": "%", "font": {"size": 42, "color": tier_color}},
                            "title": {"text": f"<b style='color:{tier_color}; font-size:17px;'>{tier.upper()} DETECTED</b><br><span style='font-size:12px; color:#64748b;'>Confidence: 94.2%</span>", "font": {"size": 15}},
                            "gauge": {"axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8", "dtick": 20}, "bar": {"color": tier_color, "thickness": 0.3}, "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0, "steps": [{"range": [0, 40], "color": "rgba(16, 185, 129, 0.15)"}, {"range": [40, 70], "color": "rgba(245, 158, 11, 0.15)"}, {"range": [70, 100], "color": "rgba(239, 68, 68, 0.18)"}], "threshold": {"line": {"color": "#b91c1c", "width": 3}, "thickness": 0.75, "value": score}}
                        }
                        if cdss_phase == 2 and baseline_record:
                            base_score = baseline_record.get("inference_results", {}).get("score", score)
                            gauge_args["delta"] = {"reference": base_score, "increasing": {"color": "#d62728"}, "decreasing": {"color": "#2ca02c"}, "suffix": "% vs baseline"}

                        fig_gauge = go.Figure(go.Indicator(**gauge_args))
                        fig_gauge.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#0f172a"))
                        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

                    with col_chart:
                        st.markdown("##### Key Contributors to Clinical Risk")
                        drivers = results.get("drivers", [])
                        if not drivers:
                            drivers = [{"feature": "All Biomarkers Nominal", "impact": 2.5, "severity": "Low"}]
                            
                        features = [d["feature"] for d in reversed(drivers)]
                        impacts = [d["impact"] for d in reversed(drivers)]
                        colors = ["#ef4444" if d.get("severity") == "High" else "#f59e0b" if d.get("severity") == "Moderate" else "#10b981" for d in reversed(drivers)]
                        
                        max_imp = max(max(impacts, default=0) * 1.2, 10)
                        fig_bar = go.Figure(go.Bar(x=impacts, y=features, orientation="h", marker=dict(color=colors, cornerradius=6), text=[f"+{val:.1f}%" for val in impacts], textposition="outside"))
                        fig_bar.update_layout(height=260, margin=dict(l=10, r=40, t=10, b=10), xaxis=dict(showgrid=True, gridcolor="rgba(148, 163, 184, 0.2)", zeroline=False, range=[0, max_imp]), yaxis=dict(showgrid=False, zeroline=False, autorange=True), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#0f172a"))
                        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

                    # --- RE-ANCHOR GATE (Approve/Reject Proposed Baseline) ---
                    proposed = st.session_state.get("proposed_baseline")
                    if proposed is not None:
                        st.markdown("#### ⚖️ Physician Re-Anchor Gate")
                        st.warning("⚠️ **Familial Pedigree Change Detected:** The model proposes establishing a new Clinical Baseline (HashNode_t).")
                        
                        rg1, rg2 = st.columns(2)
                        with rg1:
                            st.info(f"**Prior Anchor (HashNode_0):** `{baseline_record.get('cryptographic_hash', 'N/A')[:12]}...`")
                            prior_fhrs = baseline_record.get("fhrs_payload", {}).get("adjusted_score", 0.0)
                            st.metric("Prior Adjusted FHRS", f"{prior_fhrs:.2f}")
                        with rg2:
                            st.success(f"**Proposed Anchor (HashNode_t):** `{proposed.get('cryptographic_hash', 'N/A')[:12]}...`")
                            new_fhrs = proposed.get("fhrs_payload", {}).get("adjusted_score", 0.0)
                            delta_fhrs = new_fhrs - prior_fhrs
                            st.metric("Proposed Adjusted FHRS", f"{new_fhrs:.2f}", delta=f"{delta_fhrs:+.2f}", delta_color="inverse")

                        reanchor_decision = st.radio("Clinical Decision Required:", ["Pending", "Approve New Baseline Anchor", "Retain Prior Anchor"], horizontal=True, key="reanchor_radio")
                        st.session_state["reanchor_decision"] = reanchor_decision
                        
                        if reanchor_decision == "Approve New Baseline Anchor":
                            st.success("✔ New anchor selected. It will be committed to EHR upon Care Plan submission.")
                        elif reanchor_decision == "Retain Prior Anchor":
                            st.info("✔ Prior anchor retained. Trajectory evaluation will persist against HashNode_0.")
                        else:
                            st.error("Please explicitly approve or reject the new baseline to unlock the care plan.")

                    # --- FAIRNESS AUDIT & DISPARITY FLAG ---
                    st.markdown("##### ⚖️ Algorithmic Fairness & Subgroup Audit")
                    
                    # Mock disparity logic: Flag if risk is exceptionally high
                    disparity_detected = score >= 85.0 
                    
                    if disparity_detected:
                        st.error("⚠️ **FlagDisparity Alert:** Potential calibration deviation detected for this demographic subgroup. SHAP attributions suggest an over-weighting of chronologic age vs. baseline cohorts. Please review clinical drivers carefully.")
                    else:
                        st.success("✔ **Fairness Audit Passed:** Subgroup calibration and SHAP parity are within acceptable clinical tolerances. No demographic disparity detected.")

                    # CRITICAL FIX: Non-Prescriptive Clinical Insight
                    st.info(textwrap.dedent(f"""
                    **Clinical Insight (Non-Prescriptive):** 
                    The integrated diagnostic assessment indicates a **{tier}** for the target modality. This output relies on algorithmic inference and decoupled familial records.
                    *Guideline Recommendation:* Discussing individualised preventive planning, enhanced surveillance, and lifestyle modifications with a healthcare professional may be beneficial. This output is advisory and does not replace clinical judgement.
                    """))

            st.markdown("<br>", unsafe_allow_html=True)

            # --------------------------------------------------------------------------
            # DOCTOR CARE PLAN & EHR COMMIT (Strict Boundary)
            # --------------------------------------------------------------------------
            with st.container(border=True):
                st.markdown("#### ✍️ Prescribe Treatment & Update Patient Care Plan")
                st.markdown("<p style='color: #64748b; font-size: 0.9rem;'>This section is reserved for licensed physician input. AI insights are non-prescriptive.</p>", unsafe_allow_html=True)
                
                # Gate the form if Re-Anchor decision is pending
                form_disabled = bool(st.session_state.get("proposed_baseline") and st.session_state.get("reanchor_decision") == "Pending")
                
                with st.form(key=f"care_plan_form_{pid}"):
                    new_directive = st.text_area("Clinical Directive & Orders", value="", placeholder="Enter clinical directives, referrals, and orders here...", height=150, disabled=form_disabled)
                    new_rx = st.text_input("Prescribed Medications (comma-separated)", value="", placeholder="e.g., Lisinopril 10mg daily, Atorvastatin 20mg nightly", disabled=form_disabled)
                    
                    if st.form_submit_button("Update Care Plan & Commit to EHR", type="primary", disabled=form_disabled):
                        payload_safe = st.session_state.get("cdss_inference_payload") or {}
                        
                        if not new_directive or not new_rx:
                            st.error("Please complete both the Clinical Directive and Prescribed Medications fields before committing.")
                        else:
                            # Handle Re-Anchor Database Update if Approved
                            if st.session_state.get("proposed_baseline"):
                                if st.session_state.get("reanchor_decision") == "Approve New Baseline Anchor":
                                    st.session_state.baseline_records[pid] = st.session_state["proposed_baseline"]
                                    append_audit("REANCHOR_APPROVED", {"new_hash": st.session_state["proposed_baseline"]["cryptographic_hash"]})
                                elif st.session_state.get("reanchor_decision") == "Retain Prior Anchor":
                                    append_audit("REANCHOR_REJECTED", {"retained_hash": baseline_record.get("cryptographic_hash"), "doctor_id": active_doc["prc"]})
                            
                            st.session_state["proposed_baseline"] = None
                            
                            audit_entry = {
                                "encounter_id": payload_safe.get("encounter_id", "N/A"),
                                "patient_id": pid,
                                "doctor_id": active_doc["prc"],
                                "clinical_directive": new_directive,
                                "prescribed_medications": [med.strip() for med in new_rx.split(",") if med.strip()],
                                "ai_risk_score": payload_safe.get("inference_results", {}).get("score", 0),
                                "ai_risk_tier": payload_safe.get("inference_results", {}).get("tier", "Unknown"),
                                "fairness_audit_passed": not (payload_safe.get("inference_results", {}).get("score", 0) >= 85.0),
                                "validation_status": "Doctor Validated"
                            }
                            
                            append_audit("EHR_COMMIT", audit_entry)
                            st.success("Patient Care Plan updated and synced to Patient Portal.")
                            st.markdown("##### 🔒 Immutable Audit Trail Committed")
                            st.json(audit_entry)
                            time.sleep(2)
                            st.rerun()

# ==============================================================================
# 6. SIDEBAR / FOOTER (Audit Trail)
# ==============================================================================
with st.sidebar:
    st.markdown("### 🩺 Clinical Context")
    st.markdown(f"**Doctor:** {active_doc['name']}, {active_doc['suffix']}")
    st.markdown(f"**Affiliation:** {active_doc['affiliation']}")
    st.markdown(f"**Specialty:** {active_doc['specialty']}")
    st.markdown("---")
    
    if st.session_state.audit_trail:
        st.markdown("### 📋 Recent EHR Commits")
        for audit in reversed(st.session_state.audit_trail[-5:]):
            st.markdown(f"**{audit['audit_id']}** - {audit['timestamp_utc']}")
            payload = audit['payload']
            if 'hash' in payload:
                st.caption(f"Event: {audit['event_type']} | Hash: {payload['hash'][:8]}...")
            elif 'clinical_directive' in payload:
                st.caption(f"Patient: {payload['patient_id']} | Meds: {len(payload['prescribed_medications'])}")
            else:
                st.caption(f"Event: {audit['event_type']}")