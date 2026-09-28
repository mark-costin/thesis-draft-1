import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
import uuid

# ==============================================================================
# 1. PAGE SETUP & DATA BOOTSTRAP
# ==============================================================================
st.set_page_config(layout="wide", page_title="Lucerna Medica | Patient Portal")

user_avatar_url = "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=150&q=80"

# --- Core State Initialization (Synced with doctorpage.py) ---
if "theme_mode" not in st.session_state: st.session_state.theme_mode = "light"
if "logged_in_patient_id" not in st.session_state: st.session_state.logged_in_patient_id = "PAT-9912"

if "today_queue" not in st.session_state:
    st.session_state.today_queue = [
        {"queue_no": "Q-01", "time_in": "08:15 AM", "id": "PAT-9912", "name": "Alvarez, Carlos T.", "urgency": "🔴 Critical", "complaint": "Severe chest pain radiating to left arm.", "lifecycle_status": "In Waiting Room"},
        {"queue_no": "Q-02", "time_in": "08:42 AM", "id": "PAT-4421", "name": "Santos, Sofia M.", "urgency": "🟡 Priority", "complaint": "Palpitations and dizziness upon standing.", "lifecycle_status": "In Waiting Room"},
        {"queue_no": "Q-03", "time_in": "09:05 AM", "id": "PAT-1102", "name": "Mason, Justin L.", "urgency": "🟢 Routine", "complaint": "Post-op medication adjustment.", "lifecycle_status": "In Waiting Room"}
    ]

if "master_patients" not in st.session_state:
    st.session_state.master_patients = [
        {"id": "PAT-9912", "name": "Alvarez, Carlos T.", "age": 58, "sex": "Male", "bmi": 29.4, "latest_bp": "165/95", "resting_hr": 92, "primary_cond": "Cardiovascular Disease & Hypertension", "prior_directive": "Titrated Amlodipine to 10mg on Aug 15. Restrict sodium to <2000mg/day.", "active_rx": "Amlodipine 10mg OD, Atorvastatin 20mg ON", "allergies": "Penicillin", "risk_flag": "High Risk Flagged", "fam_history": ["CVD (Father: Early onset <55)", "Hypertension (Mother)"]},
        {"id": "PAT-4421", "name": "Santos, Sofia M.", "age": 42, "sex": "Female", "bmi": 24.1, "latest_bp": "118/76", "resting_hr": 105, "primary_cond": "Type 2 Diabetes Mellitus", "prior_directive": "Increase Metformin to 1000mg BID. Monitor fasting glucose.", "active_rx": "Metformin 1000mg BID", "allergies": "Sulfa Drugs", "risk_flag": "Awaiting Review", "fam_history": ["Type 2 Diabetes (Mother)"]},
        {"id": "PAT-1102", "name": "Mason, Justin L.", "age": 65, "sex": "Male", "bmi": 26.8, "latest_bp": "125/80", "resting_hr": 68, "primary_cond": "COPD & Mild Cognitive Impairment", "prior_directive": "Continue inhaler regimen. Schedule follow-up pulmonary function test.", "active_rx": "Albuterol Inhaler PRN, Donepezil 5mg OD", "allergies": "None", "risk_flag": "Stable", "fam_history": ["Dementia (Father)", "Depression (Sister)"]},
    ]

# Resolve Active Authenticated Patient
active_pat = next((p for p in st.session_state.master_patients if p["id"] == st.session_state.logged_in_patient_id), st.session_state.master_patients[0])
pid = active_pat["id"]

# ==============================================================================
# 2. MASTER DUAL-THEME ENGINE (Mirrored from Clinician Workspace)
# ==============================================================================
if st.session_state.theme_mode == "dark":
    theme_css = """
    .stApp { background-color: #091540 !important; color: #E5E5E5 !important; }
    h1, h2, h3, h4, h5, h6, p, span, label, legend, li { color: #E5E5E5 !important; }
    [data-testid="stVerticalBlockBorderWrapper"], fieldset[data-testid="stFieldset"] {
        background-color: #232F72 !important; border: 1px solid #2F578A !important; border-radius: 14px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important; padding: 20px 24px !important; margin-bottom: 18px !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] > div, fieldset[data-testid="stFieldset"] > div { background: transparent !important; border: none !important; }
    div[style*="background-color: #ffffff"], .metric-card {
        background-color: #2F578A !important; border: 1px solid rgba(229, 229, 229, 0.25) !important; border-radius: 12px !important;
    }
    [data-baseweb="base-input"], [data-baseweb="select"] > div { background-color: #091540 !important; border: 1px solid #2F578A !important; border-radius: 8px !important; }
    [data-baseweb="base-input"] input { color: #E5E5E5 !important; }
    [data-baseweb="tab-list"] { border-bottom: 2px solid #2F578A !important; }
    """
else:
    theme_css = """
    .stApp { background-color: #f1f5f9 !important; color: #0f172a !important; }
    h1, h2, h3, h4, h5, h6, p, span, label, legend, li { color: #0f172a !important; }
    [data-testid="stVerticalBlockBorderWrapper"], fieldset[data-testid="stFieldset"], div[style*="background-color: #ffffff"] {
        background-color: #ffffff !important; border: 1px solid #e0e4e8 !important; border-radius: 14px !important;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05) !important; padding: 20px 24px !important; margin-bottom: 18px !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] > div, fieldset[data-testid="stFieldset"] > div { background: transparent !important; border: none !important; }
    [data-baseweb="base-input"], [data-baseweb="select"] > div { background-color: #f8fafc !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important; }
    [data-baseweb="base-input"] input { color: #0f172a !important; }
    [data-baseweb="tab-list"] { border-bottom: 2px solid #e2e8f0 !important; }
    """

st.markdown(f"""
    <style>
    {theme_css}
    [data-testid*="stInputInstructions"] {{ display: none !important; }}
    .block-container {{ padding-left: 1.5rem !important; padding-right: 1.5rem !important; padding-top: 1.5rem !important; max-width: 96% !important; }}
    [data-baseweb="tab-list"] {{ display: flex !important; width: 100% !important; margin-top: 10px !important; margin-bottom: 24px !important; gap: 14px !important; }}
    button[data-baseweb="tab"], [data-testid="stTab"] {{ flex: 1 1 0 !important; height: 62px !important; padding: 14px 20px !important; justify-content: center !important; background-color: transparent !important; }}
    button[data-baseweb="tab"]:hover {{ background-color: rgba(0, 121, 121, 0.08) !important; }}
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span, [data-testid="stTab"] * {{ font-size: 1.35rem !important; font-weight: 800 !important; letter-spacing: 0.5px !important; }}
    [aria-selected="true"] * {{ color: #007979 !important; }}
    [data-baseweb="tab-highlight"] {{ background-color: #007979 !important; height: 4px !important; border-radius: 3px !important; }}
    button[data-testid="baseButton-primary"] {{ background-color: #007979 !important; color: #ffffff !important; border: none !important; font-weight: 700 !important; height: 48px !important; border-radius: 8px !important; }}
    button[data-testid="baseButton-primary"]:hover {{ background-color: #005f5f !important; color: #ffffff !important; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. SIDEBAR EVALUATOR SANDBOX (THESIS DEMO MODE)
# ==============================================================================
with st.sidebar:
    with st.expander("🛠️ Evaluator Sandbox (Demo Mode)", expanded=False):
        st.caption("Simulate authentic patient logins across different chronic cohorts for thesis evaluation.")
        pat_options_map = {f"{p['name']} ({p['id']})": p['id'] for p in st.session_state.master_patients}
        current_selection_label = next((k for k, v in pat_options_map.items() if v == st.session_state.logged_in_patient_id), list(pat_options_map.keys())[0])
        
        selected_sandbox_pat = st.selectbox("Switch Active Patient", options=list(pat_options_map.keys()), index=list(pat_options_map.keys()).index(current_selection_label), key="sandbox_patient_selector")
        st.session_state.logged_in_patient_id = pat_options_map[selected_sandbox_pat]
        if st.button("🔄 Apply Account Switch", use_container_width=True):
            st.rerun()

# ==============================================================================
# 4. TOP NAVIGATION HEADER & CLINIC STATUS CARD
# ==============================================================================
_, col_main, _ = st.columns([5, 90, 5], gap="small")

with col_main:
    # Top Bar Header
    with st.container(border=False):
        h1, h2 = st.columns([7, 3], vertical_alignment="center")
        with h1:
            st.markdown("### Lucerna Medica Patient Portal &nbsp;|&nbsp; <span style='font-size: 1.15rem; color: #64748b;'>My Health Overview</span>", unsafe_allow_html=True)
        with h2:
            sc1, sc2 = st.columns([3, 1], vertical_alignment="center")
            with sc1:
                st.markdown(f"<div style='background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); padding: 6px 12px; border-radius: 20px; font-weight: 700; font-size: 0.85rem; text-align: center;'>🟢 {active_pat['name'].split(',')[0]} 👤</div>", unsafe_allow_html=True)
            with sc2:
                with st.popover("⚙️"):
                    st.markdown(f"**Signed in as:** `{pid}`")
                    st.divider()
                    if st.button("Dark Mode", use_container_width=True, key=f"btn_dark_{pid}"): st.session_state.theme_mode = "dark"; st.rerun()
                    if st.button("Light Mode", use_container_width=True, key=f"btn_light_{pid}"):
                        st.divider()
                    if st.button("🚪 Log Out", use_container_width=True, key=f"btn_logout_{pid}"):
                        st.session_state.logged_in_patient_id = "PAT-9912"
                        st.rerun()

    # Welcome Card & Live Clinic Status
    with st.container(border=True):
        st.markdown(f"## Welcome back, {active_pat['name'].split(',')[1].strip()} 👋")
        
        d1, d2, d3, d4 = st.columns([1, 1, 1, 2])
        d1.metric("Patient ID", pid)
        d2.metric("Chronological Age", f"{active_pat['age']} Yrs")
        d3.metric("Biological Sex", active_pat["sex"])
        
        in_queue = next((q for q in st.session_state.today_queue if q["id"] == pid), None)
        with d4:
            st.markdown("<div style='font-size: 0.85rem; font-weight: 600; color: #64748b; margin-bottom: 4px;'>Live Clinic Status</div>", unsafe_allow_html=True)
            if in_queue:
                st.markdown(f"<div style='background:#d1fae5; color:#059669; padding:8px 12px; border-radius:8px; font-weight:700; font-size:0.9rem;'>🎫 Ticket: {in_queue['queue_no']} · {in_queue['lifecycle_status']}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background:rgba(148, 163, 184, 0.1); color:#64748b; padding:8px 12px; border-radius:8px; font-weight:700; font-size:0.9rem;'>⚪ Not Currently Checked In</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin: 16px 0; border-color: rgba(148, 163, 184, 0.2);'>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;'>
            <div><b>Primary Condition Tracked:</b> <span style='background: rgba(0, 121, 121, 0.1); color: #007979; padding: 4px 10px; border-radius: 12px; font-weight: 700; margin-left: 8px;'>🩺 {active_pat['primary_cond']}</span></div>
            <div><b>Primary Clinician:</b> Dr. Maria A. Velasco, MD, PhD (Cardiology)</div>
        </div>
        """, unsafe_allow_html=True)

    # ==============================================================================
    # 5. FIVE-TAB ARCHITECTURE
    # ==============================================================================
    tab_care, tab_vitals, tab_checkin, tab_family, tab_settings = st.tabs(["My Care Plan", "Vitals Log & History", "Pre-Visit Check-In", "Family Tree & Hereditary", "Account Settings"])
    # --------------------------------------------------------------------------
    # TAB 1: MY CARE PLAN & DOCTOR'S DIRECTIVES
    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # TAB 1: MY CARE PLAN (RESTRUCTURED: ACTION PLAN & CLINICAL DIRECTIVES)
    # --------------------------------------------------------------------------
    with tab_care:
        st.write("")
        
        # CARD 1: ATTENDING PHYSICIAN ASSESSMENT & ORDERS
        with st.container(border=True):
            st.markdown("### 🩺 Attending Physician Directives")
            st.caption("Official orders and clinical impressions issued by Dr. Maria A. Velasco, MD, PhD.")
            
            st.info(f"**Latest Clinical Order:** {active_pat.get('prior_directive', 'No active clinical directives recorded.')}")
            
            c_meta1, c_meta2 = st.columns(2)
            with c_meta1:
                st.markdown(f"**Primary Focus:** `{active_pat.get('primary_cond', 'General Health')}`")
            with c_meta2:
                st.markdown(f"**Current Care Classification:** `{active_pat.get('risk_flag', 'Stable')}`")

        # CARD 2: "HOW TO GET BETTER" - LIFESTYLE & PREVENTIVE ACTION PLAN
        with st.container(border=True):
            st.markdown("### 🎯 Your Recovery & Wellness Action Plan")
            st.caption("Personalized lifestyle corridors prescribed to lower your clinical risk indicators.")
            
            col_act1, col_act2, col_act3 = st.columns(3, gap="medium")
            
            with col_act1:
                st.markdown("""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 16px; height: 100%;">
                    <div style="font-size: 1.1rem; font-weight: 700; color: #007979; margin-bottom: 6px;">🥗 Nutrition & Diet</div>
                    <ul style="font-size: 0.85rem; padding-left: 18px; margin: 0; line-height: 1.5;">
                        <li><b>Sodium Target:</b> Strictly &lt; 2,000 mg/day (DASH Protocol).</li>
                        <li><b>Glycemic Control:</b> Eliminate sugar-sweetened beverages.</li>
                        <li><b>Hydration:</b> 2.0 – 2.5 Liters of water daily.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
            with col_act2:
                st.markdown("""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 16px; height: 100%;">
                    <div style="font-size: 1.1rem; font-weight: 700; color: #007979; margin-bottom: 6px;">🏃 Physical Activity</div>
                    <ul style="font-size: 0.85rem; padding-left: 18px; margin: 0; line-height: 1.5;">
                        <li><b>Moderate Aerobic:</b> 30 mins brisk walk, 5 days/wk.</li>
                        <li><b>Exertion Ceiling:</b> Keep resting HR &lt; 100 bpm during workouts.</li>
                        <li><b>Sedentary Break:</b> 5-min walk every 60 mins of sitting.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

            with col_act3:
                st.markdown("""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 16px; height: 100%;">
                    <div style="font-size: 1.1rem; font-weight: 700; color: #007979; margin-bottom: 6px;">💤 Sleep & Recovery</div>
                    <ul style="font-size: 0.85rem; padding-left: 18px; margin: 0; line-height: 1.5;">
                        <li><b>Sleep Window:</b> 7.0 – 8.0 hours uninterrupted.</li>
                        <li><b>Evening Screen Cutoff:</b> 45 minutes before sleep.</li>
                        <li><b>Stress Reduction:</b> 10-minute diaphragmatic breathing.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

        # CARD 3: ACTIVE MEDICATIONS & ADHERENCE
        with st.container(border=True):
            st.markdown("### 💊 Prescribed Medications")
            st.caption("Follow the dosing schedule as prescribed. Contact the clinic if adverse effects occur.")
            
            meds = [m.strip() for m in active_pat.get("active_rx", "").split(",") if m.strip()]
            if meds:
                for i, med in enumerate(meds):
                    st.checkbox(f"✅ Logged dose: **{med}**", key=f"rx_dose_log_{i}_{pid}")
            else:
                st.info("No active prescription medications recorded.")
                
            if active_pat.get("allergies") and active_pat.get("allergies") != "None":
                st.markdown(f"<div style='background:#fee2e2; color:#ef4444; border-left: 4px solid #ef4444; padding:8px 12px; border-radius:4px; font-weight:600; font-size:0.85rem; margin-top:12px;'>⚠️ Documented Drug Allergies: {active_pat['allergies']}</div>", unsafe_allow_html=True)

        # CARD 4: NEXT MILESTONE & RED FLAGS
        with st.container(border=True):
            col_m1, col_m2 = st.columns([1.2, 1.8], gap="large")
            with col_m1:
                st.markdown("#### 📅 Next Follow-Up Checkpoint")
                st.markdown("""
                * **Scheduled Visit:** October 15, 2026 (In-Clinic)
                * **Pre-Visit Requirement:** Fasting blood test 48 hours prior.
                * **Assigned Doctor:** Dr. Maria A. Velasco
                """)
            with col_m2:
                st.markdown("#### 🚨 When to Seek Emergency Care")
                st.markdown("""
                <div style="background: rgba(239, 68, 68, 0.05); border: 1px solid #ef4444; border-radius: 8px; padding: 12px; font-size: 0.85rem; color: #b91c1c;">
                    <b>Go to the nearest emergency department immediately if experiencing:</b>
                    <ul style="margin: 4px 0 0 16px; padding: 0;">
                        <li>Chest tightness, pressure, or radiating pain to jaw or left arm.</li>
                        <li>Sudden difficulty breathing or resting SpO2 &lt; 90%.</li>
                        <li>Sudden numbness, facial drooping, or speech difficulty.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # TAB 2: VITALS LOG & HISTORY (READ-ONLY)
    # --------------------------------------------------------------------------
    with tab_vitals:
        st.write("")
        
        with st.container(border=True):
            st.markdown("### 📊 Latest Clinical Findings")
            st.caption("These vitals were recorded by your attending physician during your last check-up.")
            
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("Blood Pressure", active_pat.get("latest_bp", "N/A"))
            v2.metric("Resting Heart Rate", f"{active_pat.get('resting_hr', 'N/A')} bpm")
            v3.metric("BMI", active_pat.get("bmi", "N/A"))
            v4.metric("Risk Status", active_pat.get("risk_flag", "N/A"))
            
        # ... (Keep the "Interactive Longitudinal Trend Chart" code below this) ...

    # --------------------------------------------------------------------------
    # TAB 3: PRE-VISIT CHECK-IN
    # --------------------------------------------------------------------------
    with tab_checkin:
        st.write("")
        
        in_queue = next((q for q in st.session_state.today_queue if q["id"] == pid), None)
        
        if in_queue:
            with st.container(border=True):
                st.markdown(f"""
                <div style="text-align: center; padding: 20px;">
                    <div style="font-size: 1.2rem; font-weight: 600; color: #64748b; margin-bottom: 8px;">Your Digital Clinic Ticket</div>
                    <div style="font-size: 5rem; font-weight: 800; color: #007979; line-height: 1; margin-bottom: 12px;">{in_queue['queue_no']}</div>
                    <div style="font-size: 1.1rem; font-weight: 700; background: #fef3c7; color: #d97706; display: inline-block; padding: 6px 16px; border-radius: 20px;">Status: {in_queue['lifecycle_status']}</div>
                    <div style="margin-top: 16px; font-size: 0.95rem; color: #64748b;">Check-in time: {in_queue['time_in']}</div>
                </div>
                """, unsafe_allow_html=True)
                st.info("Please remain in the digital waiting room. Dr. Velasco will call you shortly.")
                
                if st.button("❌ Cancel Check-In / Withdraw", key=f"cancel_q_{pid}", use_container_width=True):
                    st.session_state.today_queue = [q for q in st.session_state.today_queue if q["id"] != pid]
                    st.rerun()
        else:
            with st.container(border=True):
                with st.form(key=f"checkin_form_{pid}", clear_on_submit=True):
                    st.markdown("### 🏥 Digital Clinic Pre-Check-In")
                    st.caption("Complete this intake form to generate your queue ticket and alert the clinic of your arrival.")
                    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                    
                    c_complaint = st.selectbox("Primary Chief Complaint*", ["Routine Follow-up / Refill", "Worsening Chronic Symptoms", "New Acute Pain / Discomfort", "Post-Surgical Check", "Other"], key=f"ci_comp_{pid}")
                    c_symp = st.multiselect("Acute Symptoms Checklist (Select all that apply)", ["Palpitations", "Dizziness / Lightheadedness", "Persistent Cough", "Ankle/Leg Edema", "Severe Fatigue", "Shortness of Breath"], key=f"ci_symp_{pid}")
                    
                    ci1, ci2 = st.columns(2)
                    with ci1:
                        c_bp = st.text_input("Today's Intake Blood Pressure (e.g., 130/85)", placeholder="120/80", key=f"ci_bp_{pid}")
                    with ci2:
                        c_hr = st.number_input("Today's Intake Heart Rate (bpm)", min_value=30, max_value=200, value=75, step=1, key=f"ci_hr_{pid}")
                        
                    submit_checkin = st.form_submit_button("📥 Submit Pre-Visit Check-In & Get Queue Ticket", type="primary", use_container_width=True)
                    
                    if submit_checkin:
                        new_q = f"Q-{len(st.session_state.today_queue)+1:02d}"
                        st.session_state.today_queue.append({
                            "queue_no": new_q, 
                            "time_in": datetime.now().strftime("%I:%M %p"), 
                            "id": pid,
                            "name": active_pat["name"], 
                            "urgency": "🟡 Priority" if c_symp else "🟢 Routine", 
                            "complaint": c_complaint,
                            "wait_mins": 1, 
                            "vitals": f"BP: {c_bp if c_bp else 'Not Provided'} · HR: {c_hr} bpm",
                            "prior_directive": active_pat.get("prior_directive", "N/A"), 
                            "watch_flag": "Reported acute symptoms." if c_symp else "None declared.", 
                            "lifecycle_status": "In Waiting Room"
                        })
                        st.success("Check-in complete! Your queue ticket has been issued.")
                        st.rerun()

    # --------------------------------------------------------------------------
    # TAB 4: FAMILY TREE & HEREDITARY (THESIS FRAMEWORK)
    # --------------------------------------------------------------------------
    with tab_family:
        st.write("")
        
        with st.container(border=True):
            st.markdown("### 🧬 Familial Risk Assessment (FHRS) Input")
            st.caption("Log affected relatives to calculate your disease-specific Risk-Stratification Score.")
            
            with st.form(key=f"fam_framework_form_{pid}", clear_on_submit=True):
                st.markdown("#### 1. Clinical & Biological Variables")
                disease = st.selectbox("Disease Category", [
                    "Cardiovascular Disease / Hypertension", 
                    "Type 2 Diabetes Mellitus", 
                    "Chronic Respiratory Disease", 
                    "Neurological Disorder", 
                    "Mental Health Disorder"
                ])
                
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    relationship = st.selectbox("Relationship Weight (Ri)", [
                        "Tier 1 (Parents, full siblings, children) - 0.50",
                        "Tier 2 (Grandparents, aunts/uncles) - 0.25",
                        "Tier 3 (First cousins, great-grandparents) - 0.125"
                    ])
                with col_r2:
                    onset = st.selectbox("Age of Onset Weight (Oi)", [
                        "Very early onset - 3.0",
                        "Early onset - 2.0",
                        "Typical/standard onset - 1.0",
                        "Late onset - 0.75"
                    ])
                
                st.markdown("#### 2. Shared Environmental Exposure (Ed)")
                env_exposure = st.multiselect("Select all relevant lifestyle/household exposures:", [
                    "High-sodium or high-sugar diet",
                    "Sedentary household lifestyle",
                    "Household smoking / secondhand smoke",
                    "Indoor air pollution / biomass fuel",
                    "Adverse childhood experiences / chronic stress"
                ])
                
                submit_fam = st.form_submit_button("📥 Calculate & Submit Risk Variables", type="primary", use_container_width=True)
                
                if submit_fam:
                    st.success("Variables submitted successfully. Your FHRS score will be updated upon doctor review.")
    # --------------------------------------------------------------------------
    # TAB 5: ACCOUNT SETTINGS
    # --------------------------------------------------------------------------
    with tab_settings:
        st.write("")
        with st.container(border=True):
            st.markdown("### Account & Personal Information")
            st.caption("Manage your profile credentials. Security changes will sync with Lucerna Medica administration.")
            
            col_set1, col_set2 = st.columns(2, gap="large")
            
            with col_set1:
                st.markdown("##### Personal Details")
                st.text_input("Full Name", value=active_pat["name"], disabled=True, help="Contact clinic administration to change registered name.")
                st.text_input("Biological Sex", value=active_pat["sex"], disabled=True)
                st.text_input("Contact Number", placeholder="09XX-XXX-XXXX")
                
            with col_set2:
                st.markdown("##### Security & Authentication")
                with st.form("patient_password_change_form", clear_on_submit=True):
                    st.text_input("Current Password", type="password", placeholder="Enter current password")
                    st.text_input("New Password", type="password", placeholder="Enter new password")
                    st.text_input("Confirm New Password", type="password", placeholder="Re-type new password")
                    
                    if st.form_submit_button("Update Password", type="primary", use_container_width=True):
                        st.success("✅ Password update request submitted to system administration.")
                        