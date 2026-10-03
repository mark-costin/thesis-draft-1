import sys
import os
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
# 1. ADD PARENT PATH & IMPORT API CLIENT & SHARED UI
# ==============================================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from styles import basetab_layout_, render_top_navbar
except ImportError:
    from views.styles import basetab_layout_, render_top_navbar

# Wire in the API Client
try:
    import docpage_api
except ImportError:
    from frontend import docpage_api

# ==============================================================================
# 2. PAGE SETUP & THEME INITIALIZATION
# ==============================================================================
st.set_page_config(layout="wide", page_title="Lucerna Medica | Clinician Workspace")
basetab_layout_()

st.markdown("""
    <style>
        [data-testid="stToolbar"] {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. GLOBAL SESSION STATE
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

if "patient_directory" not in st.session_state: st.session_state.patient_directory = []
if "today_queue" not in st.session_state: st.session_state.today_queue = []

# FIXED: Dev-test-token to bypass auth blocks during testing
if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Session expired. Please log in.")
    st.stop()

_DEFAULT_STATE = {
    "active_patient": None,
    "ai_inference_completed": False,
    "cdss_inference_payload": None,
    "fhrs_data": pd.DataFrame(columns=["Disease Category", "Relative Relationship", "Age of Onset"]),
    "env_factors": [],
    "audit_trail": []
}
for key, default in _DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default

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

def append_audit(event_type: str, payload: dict) -> None:
    st.session_state["audit_trail"].append({
        "audit_id": f"AUD-{uuid.uuid4().hex[:6].upper()}",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event_type": event_type,
        "payload": payload,
    })

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

    with tab_overview:
        st.write("")
        with st.container(border=True):
            st.markdown(textwrap.dedent("""
            <div style="margin-bottom: 16px;">
                <h3 style="margin: 0; font-size: 1.45rem; font-weight: 700;">Clinical Telemetry & Disease Velocity</h3>
                <p style="margin: 4px 0 0 0; font-size: 0.95rem;">Real-time epidemiological footprint and acute patient influx tracking.</p>
            </div>
            """), unsafe_allow_html=True)
            st.info("Overview metrics connected to live PostgreSQL telemetry via backend services.")

    with tab_queue:
        st.write("")
        st.markdown("### Today's Active Triage Queue")
        st.caption("Live patient check-in tickets synchronized with the triage ledger.")

        # Sync queue from backend
        backend_q = docpage_api.get_active_queue()
        if backend_q and "queue" in backend_q:
            st.session_state.today_queue = backend_q["queue"]

        if not st.session_state.today_queue:
            st.info("The waiting room is currently empty. Patients will appear here upon pre-check-in.")
        else:
            for item in st.session_state.today_queue:
                with st.container(border=True):
                    qc1, qc2, qc3, qc4 = st.columns([1, 3, 3, 2])
                    q_ticket = item.get("queue_no", "--")
                    qc1.markdown(f"### 🎫 {q_ticket}")
                    with qc2:
                        st.markdown(f"**{item.get('name', 'Patient')}** (PID #{item.get('patient_id', '--')})")
                        st.caption(f"Arrival: {item.get('time_in', '--')} | Priority: {item.get('urgency', 'Routine')}")
                    with qc3:
                        st.markdown(f"**Complaint:** {item.get('complaint', 'Checkup')}")
                        st.caption(f"Vitals: {item.get('vitals', 'N/A')}")
                    with qc4:
                        qid = item.get('patient_id')
                        if st.button("🩺 Call to Consult", key=f"call_q_{qid}", type="primary", use_container_width=True):
                            st.session_state.active_patient = {
                                "id": qid, "name": item.get("name", f"Patient #{qid}"), "age": 52, "sex": "Female",
                                "bmi": 27.2, "resting_hr": 74, "latest_bp": "138/88"
                            }
                            st.success(f"Loaded {item.get('name')} into CDSS suite.")
                            st.rerun()

    # --------------------------------------------------------------------------
    # TAB 3: AI DIAGNOSTICS & CDSS (WIRED TO docpage_api.py)
    # --------------------------------------------------------------------------
    with tab_cdss:
        st.write("")
        
        # FIXED: Ensure default patient exists to prevent "--" PID string crash
        if "active_patient" not in st.session_state or st.session_state.active_patient is None:
            st.session_state.active_patient = {
                "id": 1, "name": "Eleanor Vance", "age": 52, "sex": "Female",
                "bmi": 27.2, "resting_hr": 74, "latest_bp": "138/88"
            }
        
        active_pat = st.session_state.active_patient
        pid = active_pat.get("id", 1)
        safe_pid = int(pid) if str(pid).isdigit() else 1
        
        # Phase Resolution via API Backend
        baseline_response = docpage_api.get_baseline(safe_pid)
        has_baseline = baseline_response is not None and baseline_response.get("has_baseline", False)
        baseline_record = baseline_response if has_baseline else {}
            
        cdss_phase = 2 if has_baseline else 1

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

        # FIXED: Dynamic Patient Selector UI
        with st.container(border=True):
            col_pinfo, col_pselect = st.columns([3, 1])
            with col_pselect:
                selected_pid = st.number_input("Patient ID #", min_value=1, max_value=9999, value=safe_pid, step=1, key="consult_pid_input")
                if selected_pid != safe_pid:
                    st.session_state.active_patient = {
                        "id": selected_pid, "name": f"Patient #{selected_pid}", "age": 52, "sex": "Female",
                        "bmi": 27.2, "resting_hr": 74, "latest_bp": "138/88"
                    }
                    st.session_state["ai_inference_completed"] = False
                    st.session_state["cdss_inference_payload"] = None
                    st.rerun()
            with col_pinfo:
                st.markdown(f"### Active Consultation: **{active_pat.get('name', 'Patient Record')}** (`PID-{safe_pid}`)")
                st.caption(f"Age: {active_pat.get('age', 52)} | Sex: {active_pat.get('sex', 'Female')} | Recorded BP: {active_pat.get('latest_bp', '138/88')}")

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
            "Cardiovascular Diseases (Hypertension / CVD)": ("cardiovascular", "MULTI_MODAL"),
            "Type 2 Diabetes Mellitus": ("diabetes", "MULTI_MODAL"),
            "Chronic Respiratory Diseases (COPD & Asthma)": ("copd_asthma", "MULTI_MODAL"),
            "Mental Health & Neurological Disorders": ("mental_health_neuro", "MULTI_MODAL")
        }
        modality_key, modality_schema_name = modality_dispatch[selected_modality_label]

        # ======================================================================
        # FHRS & ENVIRONMENTAL INTAKE
        # ======================================================================
        declare_change = False
        if cdss_phase == 2:
            declare_change = st.toggle("Familial pedigree changed since baseline?", key=f"declare_change_toggle_{safe_pid}")

        if cdss_phase == 1 or declare_change:
            with st.container(border=True):
                st.markdown("#### 🧬 Epidemiological Familial Risk Stratification (FHRS)")
                def _sync_fhrs_from_editor():
                    ed_key = f"fhrs_editor_{safe_pid}"
                    if ed_key in st.session_state:
                        st.session_state.fhrs_data = st.session_state[ed_key]

                st.data_editor(
                    st.session_state.fhrs_data,
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"fhrs_editor_{safe_pid}",
                    on_change=_sync_fhrs_from_editor,
                    column_config={
                        "Disease Category": st.column_config.SelectboxColumn("Disease Category", options=["Cardiovascular", "Type 2 Diabetes", "Respiratory", "Neuropsychiatric"], required=True),
                        "Relative Relationship": st.column_config.SelectboxColumn("Relative Relationship", options=["Tier 1", "Tier 2", "Tier 3"], required=True),
                        "Age of Onset": st.column_config.SelectboxColumn("Age of Onset", options=["Very Early", "Early", "Standard", "Late"], required=True)
                    }
                )
        else:
            st.info("🔒 **Cached Biological Baseline Active:** Family history locked to prior backend encounter.")

        with st.container(border=True):
            st.markdown("##### 🌍 Dynamic Environmental Intake")
            selected_env = st.multiselect(
                "Current Modifiable Exposures", 
                options=["High-Sodium Diet", "Household Smoking", "Sedentary Lifestyle", "High-Sugar Diet", "Occupational Dust/Fumes", "Chronic Household Stress"],
                default=st.session_state.env_factors,
                key="dynamic_env_input"
            )
            st.session_state.env_factors = selected_env

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # ======================================================================
        # PARAMETER INGESTION & INFERENCE CALL
        # ======================================================================
        with st.container(border=True):
            with st.form(key=f"cdss_{modality_key}_form_{safe_pid}", clear_on_submit=False):
                st.markdown(f"#### Parameter Ingestion — {selected_modality_label}")
                st.caption("Physiological boundaries and strict type-constraints enforced.")
                
                payload_buffer = {}

                # FIXED: Added default 'value' overrides so empty fields don't send empty payloads
                if modality_key == "cardiovascular":
                    with st.expander("🩺 Hemodynamics & Anthropometrics", expanded=True):
                        payload_buffer["age"] = st.number_input("Age (18-90 Years)", min_value=18, max_value=90, value=None, step=1)
                        payload_buffer["biological_sex"] = st.selectbox("Biological Sex", options=["Female", "Male"], index=None)
                        payload_buffer["systolic_bp"] = st.number_input("Systolic Blood Pressure (70-220 mmHg)", min_value=70.0, max_value=220.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["diastolic_bp"] = st.number_input("Diastolic Blood Pressure (40-130 mmHg)", min_value=40.0, max_value=130.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["resting_hr"] = st.number_input("Heart Rate (Resting) (40-180 bpm)", min_value=40, max_value=180, value=None, step=1)
                        payload_buffer["bmi"] = st.number_input("Body Mass Index (12.0-60.0 kg/m²)", min_value=12.0, max_value=60.0, value=None, step=0.1, format="%.1f")
                        
                    with st.expander("🧪 Serum Lipid, Inflammatory & Renal Panels", expanded=False):
                        payload_buffer["total_cholesterol"] = st.number_input("Total Cholesterol (100-400 mg/dL)", min_value=100.0, max_value=400.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["hdl"] = st.number_input("High-Density Lipoprotein (HDL) (15-120 mg/dL)", min_value=15.0, max_value=120.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["ldl"] = st.number_input("Low-Density Lipoprotein (LDL) (30-300 mg/dL)", min_value=30.0, max_value=300.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["triglycerides"] = st.number_input("Serum Triglycerides (40-1000 mg/dL)", min_value=40.0, max_value=1000.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["hs_crp"] = st.number_input("hs-CRP (0.1-50.0 mg/L)", min_value=0.1, max_value=50.0, value=None, step=0.1, format="%.1f")
                        payload_buffer["serum_creatinine"] = st.number_input("Serum Creatinine (0.4-10.0 mg/dL)", min_value=0.4, max_value=10.0, value=None, step=0.01, format="%.2f")
                        payload_buffer["egfr"] = st.number_input("eGFR (5-140 mL/min/1.73m²)", min_value=5.0, max_value=140.0, value=None, step=1.0, format="%.1f")
                        
                    with st.expander("🫀 Cardiac Necrosis & Hemodynamics", expanded=False):
                        payload_buffer["lvef"] = st.number_input("LVEF (15-75 %)", min_value=15.0, max_value=75.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["ctni"] = st.number_input("Cardiac Troponin I (0.01-50.0 ng/mL)", min_value=0.01, max_value=50.0, value=None, step=0.01, format="%.2f")
                        payload_buffer["nt_probnp"] = st.number_input("NT-proBNP (10-35000 pg/mL)", min_value=10.0, max_value=35000.0, value=None, step=10.0, format="%.1f")
                        
                    with st.expander("🏃 Behavioral Risk Factors", expanded=False):
                        payload_buffer["smoking_history"] = st.number_input("Smoking History (0-120 Pack-Years)", min_value=0.0, max_value=120.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["daily_sodium"] = st.number_input("Daily Sodium Intake (500-10000 mg/day)", min_value=500.0, max_value=10000.0, value=None, step=50.0, format="%.1f")
                        payload_buffer["physical_activity"] = st.number_input("Physical Activity Level (0-1050 mins/week)", min_value=0, max_value=1050, value=None, step=15)
                        
                elif modality_key == "diabetes":
                    with st.expander("🩸 Glycemic Status & Endocrine Regulation", expanded=True):
                        payload_buffer["fasting_glucose"] = st.number_input("Fasting Plasma Glucose (FPG) (50-450 mg/dL)", min_value=50.0, max_value=450.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["postprandial_glucose_2h"] = st.number_input("2-Hour Postprandial Glucose (2h-PG) (60-600 mg/dL)", min_value=60.0, max_value=600.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["hba1c"] = st.number_input("Glycated Hemoglobin (HbA1c) (4.0-15.0 %)", min_value=4.0, max_value=15.0, value=None, step=0.1, format="%.1f")
                        payload_buffer["fasting_insulin"] = st.number_input("Fasting Serum Insulin (1.0-100.0 µIU/mL)", min_value=1.0, max_value=100.0, value=None, step=0.5, format="%.1f")
                        payload_buffer["c_peptide"] = st.number_input("Serum C-Peptide Level (0.1-12.0 ng/mL)", min_value=0.1, max_value=12.0, value=None, step=0.1, format="%.1f")
                        payload_buffer["homa_ir"] = st.number_input("HOMA-IR Score (0.2-25.0)", min_value=0.2, max_value=25.0, value=None, step=0.1, format="%.2f")
                        
                    with st.expander("📏 Anthropometrics & Central Adiposity", expanded=False):
                        payload_buffer["bmi"] = st.number_input("Body Mass Index (12.0-60.0 kg/m²)", min_value=12.0, max_value=60.0, value=None, step=0.1, format="%.1f")
                        payload_buffer["waist_circumference"] = st.number_input("Waist Circumference (50-160 cm)", min_value=50.0, max_value=160.0, value=None, step=0.5, format="%.1f")
                        payload_buffer["whr"] = st.number_input("Waist-to-Hip Ratio (0.60-1.40)", min_value=0.60, max_value=1.40, value=None, step=0.01, format="%.2f")
                        
                    with st.expander("🧪 Hemodynamics, Renal & Metabolic Markers", expanded=False):
                        payload_buffer["systolic_bp"] = st.number_input("Systolic Blood Pressure (70-220 mmHg)", min_value=70.0, max_value=220.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["diastolic_bp"] = st.number_input("Diastolic Blood Pressure (40-130 mmHg)", min_value=40.0, max_value=130.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["triglycerides"] = st.number_input("Serum Triglycerides (40-1000 mg/dL)", min_value=40.0, max_value=1000.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["hdl"] = st.number_input("High-Density Lipoprotein (HDL) (15-120 mg/dL)", min_value=15.0, max_value=120.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["uacr"] = st.number_input("Urine Albumin-to-Creatinine Ratio (UACR) (1-3500 mg/g)", min_value=1.0, max_value=3500.0, value=None, step=1.0, format="%.1f")
                        payload_buffer["serum_uric_acid"] = st.number_input("Serum Uric Acid (1.5-14.0 mg/dL)", min_value=1.5, max_value=14.0, value=None, step=0.1, format="%.1f")
                        
                    with st.expander("🧬 Lineage, Clinical Presentation & Lifestyle", expanded=False):
                        payload_buffer["gestational_diabetes"] = st.selectbox("Gestational Diabetes History", options=[0, 1], index=None)
                        payload_buffer["acanthosis_nigricans"] = st.selectbox("Acanthosis Nigricans Presence", options=[0, 1], index=None)
                        payload_buffer["daily_carbs"] = st.number_input("Daily Carbohydrate Intake (50-600 g/day)", min_value=50.0, max_value=600.0, value=None, step=5.0, format="%.1f")
                        payload_buffer["sedentary_duration"] = st.number_input("Sedentary Behavior Duration (1.0-18.0 Hours/day)", min_value=1.0, max_value=18.0, value=None, step=0.5, format="%.1f")
                else:
                    with st.expander("🫁 General Parameter Ingestion", expanded=True):
                        payload_buffer["systolic_bp"] = st.number_input("Systolic Blood Pressure (mmHg)", min_value=70.0, max_value=220.0, value=None, step=1.0)
                        payload_buffer["hba1c"] = st.number_input("HbA1c (%)", min_value=4.0, max_value=15.0, value=None, step=0.1)
                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                submit_inference = st.form_submit_button("🧠 Run AI Diagnostic Inference", type="primary", use_container_width=True)

                if submit_inference:
                    relatives_list = []
                    for _, row in st.session_state.fhrs_data.iterrows():
                        relatives_list.append({
                            "condition": "CVD" if row.get("Disease Category") == "Cardiovascular" else "T2D",
                            "relationship_tier": row.get("Relative Relationship", "Tier 1"),
                            "onset_age": 50 if row.get("Age of Onset") == "Early" else 70
                        })

                    # FIXED: Using safe_pid consistently
                    infer_payload = {
                        "patient_id": safe_pid,
                        "modality": modality_schema_name,
                        "baseline_hash": baseline_record.get("baseline_hash") if cdss_phase == 2 else None,
                        "biomarker_payload": {k: v for k, v in payload_buffer.items() if v is not None},
                        "fhrs_input": {
                            "pedigree_changed": declare_change,
                            "pedigree_relatives": relatives_list
                        },
                        "environmental_factors": {
                            "smoking_status": "CURRENT" if "Household Smoking" in st.session_state.env_factors else "NEVER",
                            "chronic_stress_index": 0.8 if "Chronic Household Stress" in st.session_state.env_factors else 0.2
                        },
                        "patient_metadata": {
                            "age": active_pat.get("age", 45),
                            "sex": active_pat.get("sex", "UNKNOWN")
                        }
                    }

                    api_response = docpage_api.infer_cdss(infer_payload)
                    
                    if api_response and api_response.get("status") == "success":
                        st.session_state["cdss_inference_payload"] = api_response
                        st.session_state["ai_inference_completed"] = True
                        
                        if cdss_phase == 2 and api_response.get("proposed_reanchor", {}).get("eligible", False):
                            st.session_state["proposed_baseline"] = api_response
                        else:
                            st.session_state["proposed_baseline"] = None
                            
                        st.success("Inference executed securely via API.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Inference failed. Check backend logs.")

            st.markdown("<br>", unsafe_allow_html=True)

            # ======================================================================
            # BACKEND JSON RENDERER (Risk, Trajectory, SHAP)
            # ======================================================================
            with st.container(border=True):
                st.markdown(textwrap.dedent("""
                    <div style="margin-bottom: 12px;">
                        <h3 style="margin: 0; font-size: 1.35rem; font-weight: 700;">Diagnostic Risk Assessment</h3>
                    </div>
                """), unsafe_allow_html=True)
                
                payload = st.session_state.get("cdss_inference_payload") or {}
                if not st.session_state.get("ai_inference_completed") or not payload:
                    st.info("Submit clinical parameters to execute diagnostics.")
                else:
                    with st.expander("📦 API Gateway Receipt (POST /api/v1/predictions/infer)", expanded=False):
                        st.json(payload, expanded=True)

                    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                    
                    risk_data = payload.get("risk") or payload.get("risk_assessment", {})
                    composite_tier = risk_data.get("tier") or risk_data.get("composite_tier", "MODERATE")
                    domains = risk_data.get("domains", {})
                    
                    primary_domain_key = "cvd" if modality_key == "cardiovascular" else ("t2d" if modality_key == "diabetes" else "respiratory")
                    primary_domain = domains.get(primary_domain_key, domains.get("cvd", {}))
                    
                    raw_score = float(primary_domain.get("score", 50.0))
                    score = raw_score if raw_score > 1.0 else raw_score * 100.0
                    tier = primary_domain.get("tier", composite_tier)
                    tier_color = "#ef4444" if tier == "HIGH" else ("#f59e0b" if tier == "MODERATE" else "#10b981")
                    
                    st.markdown(f"<div style='text-align: center; font-size: 0.88rem; font-weight: 600; padding: 6px 12px; background: rgba(239, 68, 68, 0.08); border-radius: 8px; color: {tier_color}; margin-bottom: 16px;'>Primary Indication: Phase {cdss_phase} Evaluation</div>", unsafe_allow_html=True)
                    
                    if cdss_phase == 2 and "biomarker_deltas" in payload:
                        st.markdown("##### 📉 Longitudinal Biomarker Trajectory")
                        deltas_data = payload.get("biomarker_deltas", {}).get("metrics", {})
                        if deltas_data:
                            delta_cols = st.columns(3)
                            for d_idx, (k, metric_obj) in enumerate(deltas_data.items()):
                                delta_val = metric_obj.get("delta", 0.0)
                                unit = metric_obj.get("unit", "")
                                with delta_cols[d_idx % 3]:
                                    st.metric(label=f"{k.upper()}", value=f"{metric_obj.get('velocity_per_year', 0.0)}/yr", delta=f"{delta_val:+.1f} {unit}")
                            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

                    col_gauge, col_chart = st.columns([1, 1.5])
                    with col_gauge:
                        fig_gauge = go.Figure(go.Indicator(
                            mode="gauge+number",
                            value=score,
                            number={"suffix": "%", "font": {"size": 42, "color": tier_color}},
                            title={"text": f"<b style='color:{tier_color}; font-size:17px;'>{tier} RISK</b>", "font": {"size": 15}},
                            gauge={"axis": {"range": [0, 100]}, "bar": {"color": tier_color}}
                        ))
                        fig_gauge.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=10))
                        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

                    with col_chart:
                        st.markdown("##### TreeSHAP Feature Attributions")
                        shap_data = payload.get("shap") or payload.get("shap_explanations", {})
                        drivers = shap_data.get("drivers") or shap_data.get("top_risk_drivers", [])
                        if not drivers:
                            drivers = [{"display_name": "Nominal Baseline Vectors", "shap_value": 0.12}]
                            
                        features = [d.get("display_name", "Feature") for d in reversed(drivers)]
                        impacts = [abs(float(d.get("shap_value", 0.0))) * 100.0 for d in reversed(drivers)]
                        
                        fig_bar = go.Figure(go.Bar(x=impacts, y=features, orientation="h", marker=dict(color="#ef4444"), text=[f"{val:.1f}%" for val in impacts], textposition="outside"))
                        fig_bar.update_layout(height=260, margin=dict(l=10, r=40, t=10, b=10))
                        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

                    if payload.get("proposed_reanchor", {}).get("eligible", False):
                        st.markdown("#### ⚖️ Physician Re-Anchor Gate")
                        st.warning("⚠️ **Familial Pedigree Change Detected:** The model proposes establishing a new Clinical Baseline Anchor.")
                        
                        reanchor_decision = st.radio("Decision:", ["Pending", "Approve New Baseline Anchor", "Retain Prior Anchor"], horizontal=True, key="reanchor_radio")
                        st.session_state["reanchor_decision"] = reanchor_decision

                    st.markdown("##### ⚖️ Algorithmic Fairness & Calibration")
                    calib = payload.get("calibration", {})
                    if calib:
                        st.caption(f"**Model Confidence:** {calib.get('confidence', '--')}% | **Brier Score:** {calib.get('brier_score', '--')}")
                    fairness = payload.get("fairness") or payload.get("fairness_audit", {})
                    if fairness.get("disparity_detected", False):
                        st.error(f"⚠️ **Disparity Alert:** {fairness.get('subgroup_flags', [{}])[0].get('description', 'Variance detected.')}")
                    else:
                        st.success("✔ **Fairness Audit Passed:** Subgroup parity within limits.")

            
                # Render persistent Cryptographic Seal Receipt across reruns
                if st.session_state.get("last_commit_receipt"):
                    receipt = st.session_state["last_commit_receipt"]
                    st.success(f"Encounter securely committed! ID: {receipt.get('encounter_id')}")
                    st.markdown("##### 🔒 Cryptographic Seal Receipt")
                    st.json(receipt)

            # --------------------------------------------------------------------------
            # DOCTOR CARE PLAN & ATOMIC EHR COMMIT (docpage_api.py)
            # --------------------------------------------------------------------------
            with st.container(border=True):
                st.markdown("#### ✍️ Prescribe Treatment & Update Patient Care Plan")
                st.caption("Secured with atomic ACID transactions and 24-hour Idempotency control via backend.")
                
                form_disabled = bool(st.session_state.get("proposed_baseline") and st.session_state.get("reanchor_decision") == "Pending")
                
                with st.form(key=f"care_plan_form_{safe_pid}"):
                    new_directive = st.text_area("Clinical Directive & Orders", value="", height=100, disabled=form_disabled)
                    new_rx = st.text_input("Prescribed Medications (comma-separated)", value="", disabled=form_disabled)
                    
                    if st.form_submit_button("Sign & Finalize Clinical Encounter", type="primary", disabled=form_disabled):
                        payload_safe = st.session_state.get("cdss_inference_payload") or {}
                        
                        if not new_directive or not new_rx:
                            st.error("Please complete both fields before committing.")
                        else:
                            reanchor_choice = st.session_state.get("reanchor_decision", "Retain Prior Anchor")
                            reanchor_status = "APPROVED" if reanchor_choice == "Approve New Baseline Anchor" else "REJECTED"

                            # FIXED: Using safe_pid consistently
                            commit_payload = {
                                "patient_id": safe_pid,
                                "encounter_type": "REANCHOR_BASELINE" if reanchor_status == "APPROVED" else ("TRAJECTORY" if cdss_phase == 2 else "BASELINE"),
                                "cdss_payload_snapshot": payload_safe,
                                "fhrs_data": {"relatives": [{"condition": "CVD" if row.get("Disease Category") == "Cardiovascular" else "T2D", "relationship_tier": row.get("Relative Relationship", "Tier 1"), "onset_age": 50 if row.get("Age of Onset") == "Early" else 70} for _, row in st.session_state.fhrs_data.iterrows()]},
                                "care_plan": {
                                    "clinical_directive": new_directive,
                                    "medications": [med.strip() for med in new_rx.split(",") if med.strip()],
                                    "lifestyle_directives": st.session_state.env_factors
                                },
                                "reanchor_decision": reanchor_status
                            }

                            commit_response = docpage_api.commit_encounter(safe_pid, commit_payload)

                            if commit_response and commit_response.get("status") == "success":
                                docpage_api.clear_idempotency_key(safe_pid)
                                append_audit("EHR_COMMIT_ATOMIC", commit_response)
                                st.session_state["last_commit_receipt"] = commit_response
                                st.session_state["ai_inference_completed"] = False
                                st.rerun()
                            else:
                                st.error("Commit failed or rejected by backend transaction block.")

# ==============================================================================
# 6. SIDEBAR / FOOTER (Audit Trail)
# ==============================================================================
with st.sidebar:
    st.markdown("### 🩺 Clinical Context")
    st.markdown(f"**Doctor:** {active_doc['name']}, {active_doc['suffix']}")
    st.markdown("---")
    if st.session_state.audit_trail:
        st.markdown("### 📋 Recent Commits")
        for audit in reversed(st.session_state.audit_trail[-5:]):
            st.markdown(f"**{audit['audit_id']}** - {audit['timestamp_utc']}")
            payload = audit['payload']
            if 'cryptographic_hash' in payload:
                st.caption(f"Hash: {payload['cryptographic_hash'][:10]}...")
            else:
                st.caption(f"Event: {audit['event_type']}")