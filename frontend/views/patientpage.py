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
if "active_patient" not in st.session_state: st.session_state.active_patient = None

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

# Fallback Identity Initialization
if not st.session_state.active_patient:
    st.session_state.active_patient = st.session_state.master_patients[0]

active_pat = st.session_state.active_patient
pid = active_pat["id"]

def set_patient():
    selected_id = st.session_state.patient_switcher_dropdown.split(" ")[0]
    st.session_state.active_patient = next((p for p in st.session_state.master_patients if p["id"] == selected_id), st.session_state.master_patients[0])

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
# 3. HEADER & LIVE CLINIC STATUS
# ==============================================================================
_, col_main, _ = st.columns([5, 90, 5], gap="small")

with col_main:
    # Top Navigation & Theme Switcher
    with st.container(border=False):
        h1, h2 = st.columns([7, 3], vertical_alignment="center")
        with h1:
            st.markdown(f"### Lucerna Medica Patient Portal &nbsp;|&nbsp; <span style='font-size: 1.15rem; color: #64748b;'>My Health Overview</span>", unsafe_allow_html=True)
        with h2:
            sc1, sc2 = st.columns([3, 1])
            with sc1:
                pat_opts = [f"{p['id']} - {p['name']}" for p in st.session_state.master_patients]
                curr_idx = pat_opts.index(f"{active_pat['id']} - {active_pat['name']}")
                st.selectbox("Simulate Patient Login", options=pat_opts, index=curr_idx, key="patient_switcher_dropdown", on_change=set_patient, label_visibility="collapsed")
            with sc2:
                with st.popover("⚙️"):
                    if st.button("Dark Mode", use_container_width=True, key=f"btn_dark_{pid}"): st.session_state.theme_mode = "dark"; st.rerun()
                    if st.button("Light Mode", use_container_width=True, key=f"btn_light_{pid}"): st.session_state.theme_mode = "light"; st.rerun()

    # Demographic Card & Live Queue Status
    with st.container(border=True):
        st.markdown(f"## Welcome back, {active_pat['name'].split(',')[1].strip()} 👋")
        
        d1, d2, d3, d4 = st.columns([1, 1, 1, 2])
        d1.metric("Patient ID", pid)
        d2.metric("Chronological Age", f"{active_pat['age']} Yrs")
        d3.metric("Biological Sex", active_pat["sex"])
        
        # Check active queue status
        in_queue = next((q for q in st.session_state.today_queue if q["id"] == pid), None)
        with d4:
            st.markdown("<div style='font-size: 0.85rem; font-weight: 600; color: #64748b; margin-bottom: 4px;'>Live Clinic Status</div>", unsafe_allow_html=True)
            if in_queue:
                q_num = in_queue['queue_no']
                q_stat = in_queue['lifecycle_status']
                st.markdown(f"<div style='background:#d1fae5; color:#059669; padding:8px 12px; border-radius:8px; font-weight:700; font-size:0.95rem;'>🎫 Ticket: {q_num} · {q_stat} · Est. Wait: 12m</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background:rgba(148, 163, 184, 0.1); color:#64748b; padding:8px 12px; border-radius:8px; font-weight:700; font-size:0.95rem;'>⚪ Not Currently Checked In</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin: 16px 0; border-color: rgba(148, 163, 184, 0.2);'>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;'>
            <div><b>Primary Condition Tracked:</b> <span style='background: rgba(0, 121, 121, 0.1); color: #007979; padding: 4px 10px; border-radius: 12px; font-weight: 700; margin-left: 8px;'>🩺 {active_pat['primary_cond']}</span></div>
            <div><b>Primary Clinician:</b> Dr. Maria A. Velasco, MD, PhD (Cardiology)</div>
        </div>
        """, unsafe_allow_html=True)

    # ==============================================================================
    # 4. TABBED INTERFACE
    # ==============================================================================
    tab_care, tab_vitals, tab_checkin, tab_family = st.tabs(["My Care Plan", "Vitals Log & History", "Pre-Visit Check-In", "Family Tree & Hereditary"])

    # --------------------------------------------------------------------------
    # TAB 1: MY CARE PLAN
    # --------------------------------------------------------------------------
    with tab_care:
        st.write("")
        
        with st.container(border=True):
            st.markdown("### 📝 Attending Physician Directives")
            st.info(f"**Latest Entry (Dr. Velasco):** {active_pat['prior_directive']}")
            
        with st.container(border=True):
            st.markdown("### 💊 Interactive Medication Cabinet & Adherence")
            st.caption("Mark your daily doses as taken to log adherence in your clinical record.")
            
            meds = [m.strip() for m in active_pat.get("active_rx", "").split(",") if m.strip()]
            if meds:
                for i, med in enumerate(meds):
                    st.checkbox(f"✅ I have taken **{med}** today.", key=f"med_{i}_{pid}")
            else:
                st.markdown("No active prescriptions recorded.")
                
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            if active_pat.get("allergies") and active_pat.get("allergies") != "None":
                st.markdown(f"<div style='background:#fee2e2; color:#ef4444; border-left: 4px solid #ef4444; padding:10px 14px; border-radius:4px; font-weight:600; font-size:0.9rem;'>⚠️ Confirmed Allergies: {active_pat['allergies']}</div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### 🤖 Plain-Language AI Diagnostic Insights")
            if "High Risk" in active_pat["risk_flag"]:
                st.markdown(f"""
                <div style="font-size: 0.95rem; line-height: 1.6;">
                    Based on your latest clinical readings, your AI risk indicator is currently <b>Elevated</b>. 
                    <br><br>
                    <b>What this means:</b> Some of your baseline markers (such as your blood pressure or glycemic indices) are running higher than your personal target zone. This is common and manageable.
                    <br><br>
                    <b>Action Plan:</b> Please ensure strict adherence to your medication cabinet above, prioritize low-sodium/low-glycemic meals, and complete your daily vitals log so Dr. Velasco can review your trends.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="font-size: 0.95rem; line-height: 1.6;">
                    Based on your latest clinical readings, your AI risk indicator is currently <b>Stable</b>. Excellent job maintaining your health targets! Continue with your current lifestyle and medication routine.
                </div>
                """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### 🚨 Emergency Red-Flag Warning")
            st.markdown("""
            <div style="border: 2px solid #ef4444; border-radius: 8px; padding: 16px; background: rgba(239, 68, 68, 0.05);">
                <div style="color: #ef4444; font-weight: 800; font-size: 1.1rem; margin-bottom: 8px;">SEEK IMMEDIATE EMERGENCY CARE IF YOU EXPERIENCE:</div>
                <ul style="margin: 0 0 12px 16px; color: #ef4444; font-weight: 600;">
                    <li>Crushing chest pain radiating to the left arm or jaw.</li>
                    <li>Sudden, severe shortness of breath or inability to breathe.</li>
                    <li>Sudden weakness, numbness in face/limbs, or slurred speech.</li>
                    <li>Severe hypoglycemia (confusion, fainting, unresponsiveness).</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            st.button("☎️ Contact 24/7 Emergency Helpline", type="primary", key=f"btn_emg_{pid}", use_container_width=True)

    # --------------------------------------------------------------------------
    # TAB 2: VITALS LOG & HISTORY
    # --------------------------------------------------------------------------
    with tab_vitals:
        st.write("")
        
        with st.container(border=True):
            with st.form(key=f"vitals_form_{pid}", clear_on_submit=True):
                st.markdown("### 📊 Daily Home Reading Ingestion")
                st.caption("Submit your home monitor readings to instantly synchronize with Dr. Velasco's dashboard.")
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                
                # Render comprehensive vitals inputs based on general tracking
                v1, v2, v3 = st.columns(3)
                with v1:
                    st.number_input("Systolic Blood Pressure (mmHg)", min_value=50, max_value=250, value=120, step=1, key=f"v_sbp_{pid}")
                    st.caption("Healthy Target: 90 – 120 mmHg")
                with v2:
                    st.number_input("Diastolic Blood Pressure (mmHg)", min_value=30, max_value=150, value=80, step=1, key=f"v_dbp_{pid}")
                    st.caption("Healthy Target: 60 – 80 mmHg")
                with v3:
                    st.number_input("Resting Heart Rate (bpm)", min_value=30, max_value=200, value=75, step=1, key=f"v_hr_{pid}")
                    st.caption("Healthy Target: 60 – 100 bpm")

                v4, v5, v6 = st.columns(3)
                with v4:
                    st.number_input("Fasting Glucose (mg/dL)", min_value=40.0, max_value=500.0, value=95.0, step=1.0, format="%.1f", key=f"v_glu_{pid}")
                    st.caption("Healthy Target: 70 – 99 mg/dL")
                with v5:
                    st.number_input("Resting SpO2 (%)", min_value=60.0, max_value=100.0, value=98.0, step=0.1, format="%.1f", key=f"v_spo2_{pid}")
                    st.caption("Healthy Target: > 95 %")
                with v6:
                    st.number_input("Body Weight (kg)", min_value=30.0, max_value=300.0, value=80.0, step=0.1, format="%.1f", key=f"v_wt_{pid}")
                    st.caption("Log daily for fluid retention tracking.")

                submit_vitals = st.form_submit_button("📤 Submit Daily Readings", type="primary", use_container_width=True)
                if submit_vitals:
                    st.success("Readings successfully uploaded and synchronized with the clinical database.")

        with st.container(border=True):
            st.markdown("### 📈 Interactive Longitudinal Trend Chart")
            st.caption("Your 30-day baseline tracker. The green shaded area represents your physician-assigned target corridor.")
            
            # Generate mock longitudinal data based on primary condition
            days = [f"Day {i}" for i in range(1, 31)]
            if "Cardiovascular" in active_pat["primary_cond"]:
                y_vals = [145, 142, 140, 138, 144, 150, 155, 160, 158, 152, 148, 145, 142, 140, 139, 138, 140, 145, 148, 150, 155, 160, 162, 165, 160, 158, 155, 150, 145, 142]
                target_min, target_max = 90, 120
                y_label = "Systolic Blood Pressure (mmHg)"
            elif "Diabetes" in active_pat["primary_cond"]:
                y_vals = [135, 130, 125, 120, 125, 130, 135, 140, 145, 150, 145, 140, 135, 130, 125, 122, 125, 130, 135, 140, 145, 150, 148, 145, 140, 135, 130, 125, 120, 118]
                target_min, target_max = 70, 100
                y_label = "Fasting Glucose (mg/dL)"
            else:
                y_vals = [94, 95, 95, 96, 96, 95, 94, 93, 92, 91, 90, 91, 92, 93, 94, 95, 96, 95, 94, 93, 92, 91, 90, 89, 88, 89, 90, 92, 94, 95]
                target_min, target_max = 95, 100
                y_label = "Resting SpO2 (%)"

            fig = go.Figure()
            # Add shaded target corridor
            fig.add_hrect(y0=target_min, y1=target_max, line_width=0, fillcolor="rgba(16, 185, 129, 0.15)", layer="below")
            # Add Line
            fig.add_trace(go.Scatter(
                x=days, y=y_vals, mode="lines+markers",
                line=dict(color="#007979", width=3),
                marker=dict(size=6, color="#007979"),
                name="Home Reading"
            ))
            fig.update_layout(
                height=300, margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis_title=y_label,
                xaxis=dict(showgrid=True, gridcolor="rgba(148, 163, 184, 0.1)"),
                yaxis=dict(showgrid=True, gridcolor="rgba(148, 163, 184, 0.1)", autorange=True)
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            st.button("📄 Export Home Log Summary", key=f"btn_export_{pid}", use_container_width=True)

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
                        
                    submit_checkin = st.form_submit_button("📥 Check In for Today's Visit", type="primary", use_container_width=True)
                    
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
                        st.rerun()

    # --------------------------------------------------------------------------
    # TAB 4: FAMILY TREE & HEREDITARY
    # --------------------------------------------------------------------------
    with tab_family:
        st.write("")
        
        with st.container(border=True):
            st.markdown("### 🧬 Genomic Linkage & Verified Hereditary Risk")
            st.caption("This profile dictates your baseline risk multipliers in the CDSS AI engine.")
            
            fam_hist_list = active_pat.get("fam_history", [])
            fam_hist_str = " | ".join(fam_hist_list).lower() if fam_hist_list else ""
            
            # Determine Risk based on generic keywords
            if any(kw in fam_hist_str for kw in ["early", "<55", "heart attack", "stroke"]):
                risk_badge = "🔴 High Genetic Load"
                risk_bg, risk_fg = "#fee2e2", "#ef4444"
            elif fam_hist_list:
                risk_badge = "🟡 Moderate Risk"
                risk_bg, risk_fg = "#fef3c7", "#d97706"
            else:
                risk_badge = "🟢 Low Risk"
                risk_bg, risk_fg = "#d1fae5", "#059669"
                
            st.markdown(f"""
            <div style="background: rgba(0, 121, 121, 0.04); border: 1px solid rgba(0, 121, 121, 0.2); border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="font-weight: 700; font-size: 1.1rem; color: #007979;">Active Clinical Registry Profile</div>
                    <div style="background: {risk_bg}; color: {risk_fg}; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">{risk_badge}</div>
                </div>
                <div style="font-size: 0.95rem;"><b>Recorded Lineage:</b> {', '.join(fam_hist_list) if fam_hist_list else 'No significant familial conditions recorded.'}</div>
                <div style="margin-top: 12px; font-size: 0.8rem; font-weight: 600; color: #64748b;">✔ Verified by Attending Clinician on Record</div>
            </div>
            """, unsafe_allow_html=True)
            
        with st.container(border=True):
            with st.form(key=f"fam_form_{pid}", clear_on_submit=False):
                st.markdown("#### Update Patient-Reported Familial History")
                st.caption("Ensure your lineage data remains up to date. Changes submitted here will be queued for physician review.")
                st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
                
                with st.expander("👨 Paternal History (Father's Lineage)", expanded=True):
                    st.checkbox("Premature Heart Attack or CVD (Before age 55)", key=f"fh_pat_cvd_{pid}")
                    st.checkbox("Hypertension (High Blood Pressure)", key=f"fh_pat_hyp_{pid}")
                    st.checkbox("Type 2 Diabetes", key=f"fh_pat_t2d_{pid}")
                    st.checkbox("Neurological (Dementia, Alzheimer's, Parkinson's)", key=f"fh_pat_neuro_{pid}")
                    
                with st.expander("👩 Maternal History (Mother's Lineage)", expanded=False):
                    st.checkbox("Premature Heart Attack or CVD (Before age 65)", key=f"fh_mat_cvd_{pid}")
                    st.checkbox("Hypertension (High Blood Pressure)", key=f"fh_mat_hyp_{pid}")
                    st.checkbox("Type 2 Diabetes", key=f"fh_mat_t2d_{pid}")
                    st.checkbox("Autoimmune or Pulmonary Disorders", key=f"fh_mat_auto_{pid}")
                    
                with st.expander("👧👦 Sibling Lineage", expanded=False):
                    st.checkbox("Sibling with Early-Onset CVD or Stroke", key=f"fh_sib_cvd_{pid}")
                    st.checkbox("Sibling with Severe Psychiatric / Depression History", key=f"fh_sib_psych_{pid}")

                submit_fam = st.form_submit_button("📤 Submit Updates for Review", type="primary", use_container_width=True)
                if submit_fam:
                    st.success("Hereditary updates submitted successfully. Pending clinician verification.")