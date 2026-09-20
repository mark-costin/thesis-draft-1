import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
import uuid

# ==============================================================================
# 1. PAGE SETUP & DATA BOOTSTRAP
# ==============================================================================
st.set_page_config(layout="wide", page_title="Lucerna Medica | Clinician Workspace")

user_avatar_url = "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=150&q=80"

doc = {
    "name": "Dr. Maria A. Velasco", "suffix": "MD, PhD", "role": "CLINICIAN",
    "prc": "PRC 8839210", "affiliation": "Lucerna Central Clinic", "specialty": "Cardiology"
}

# --- Core State Initialization ---
if "theme_mode" not in st.session_state: st.session_state.theme_mode = "light"
if "active_patient" not in st.session_state: st.session_state.active_patient = None
if "cdss_locked" not in st.session_state: st.session_state.cdss_locked = False
if "ai_inference_completed" not in st.session_state: st.session_state.ai_inference_completed = False
if "cdss_inference_payload" not in st.session_state: st.session_state.cdss_inference_payload = None
if "active_modality" not in st.session_state: st.session_state.active_modality = "Cardiovascular Diseases (Hypertension / CVD)"

if "today_queue" not in st.session_state:
    st.session_state.today_queue = [
        {"queue_no": "Q-01", "time_in": "08:15 AM", "id": "PAT-9912", "name": "Alvarez, Carlos T.", "urgency": "🔴 Critical", "complaint": "Severe chest pain radiating to left arm."},
        {"queue_no": "Q-02", "time_in": "08:42 AM", "id": "PAT-4421", "name": "Santos, Sofia M.", "urgency": "🟡 Priority", "complaint": "Palpitations and dizziness upon standing."},
        {"queue_no": "Q-03", "time_in": "09:05 AM", "id": "PAT-1102", "name": "Mason, Justin L.", "urgency": "🟢 Routine", "complaint": "Post-op medication adjustment."}
    ]

master_patients = [
    {"id": "PAT-9912", "name": "Alvarez, Carlos T.", "age": 58, "sex": "Male", "bmi": 29.4, "latest_bp": "165/95", "resting_hr": 92, "total_chol": 245, "fasting_glucose": 115.0, "hba1c": 6.4, "spo2": 96.0, "fev1_fvc": "74%", "pack_years": 25.0, "phq9": 4, "gad7": 3, "sleep_hrs": 6.5, "last_ecg": "2026-09-13", "risk_flag": "High Risk Flagged", "fam_history": ["CVD (Father: Early onset <55)", "Hypertension (Mother)"]},
    {"id": "PAT-4421", "name": "Santos, Sofia M.", "age": 42, "sex": "Female", "bmi": 24.1, "latest_bp": "118/76", "resting_hr": 105, "total_chol": 190, "fasting_glucose": 142.0, "hba1c": 7.8, "spo2": 98.0, "fev1_fvc": "82%", "pack_years": 0.0, "phq9": 8, "gad7": 9, "sleep_hrs": 5.0, "last_ecg": "2026-08-20", "risk_flag": "Awaiting Review", "fam_history": ["Type 2 Diabetes (Mother)"]},
    {"id": "PAT-1102", "name": "Mason, Justin L.", "age": 65, "sex": "Male", "bmi": 26.8, "latest_bp": "125/80", "resting_hr": 68, "total_chol": 175, "fasting_glucose": 95.0, "hba1c": 5.4, "spo2": 88.0, "fev1_fvc": "62%", "pack_years": 40.0, "phq9": 16, "gad7": 12, "sleep_hrs": 4.5, "last_ecg": "2026-09-01", "risk_flag": "Stable", "fam_history": ["Dementia (Father)", "Depression (Sister)"]},
]

# --- State Sync & Helper Methods ---
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
    st.session_state.cdss_locked = False
    st.session_state["ai_inference_completed"] = False
    st.session_state["cdss_inference_payload"] = None
    st.toast(f"Consultation initiated for {patient['name']}", icon="🩺")

# ==============================================================================
# 2. MASTER DUAL-THEME ENGINE
# ==============================================================================
if st.session_state.theme_mode == "dark":
    theme_css = """
    .stApp { background-color: #091540 !important; color: #E5E5E5 !important; }
    h1, h2, h3, h4, h5, h6, p, span, label, legend { color: #E5E5E5 !important; }
    [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stContainer"], div[data-testid="stContainer"],
    div[data-testid="stVerticalBlockBorderWrapper"], fieldset[data-testid="stFieldset"],
    div:has(> div > [data-testid="stPlotlyChart"]), div:has(> div > [data-testid="stDataFrame"]),
    div:has(> div > [data-testid*="VegaLite"]), div:has(> div > [data-testid="stLineChart"]),
    div[style*="background-color: #ffffff"], div[style*="background-color: rgb(255, 255, 255)"], .metric-card {
        background-color: #232F72 !important; background: #232F72 !important; border: 1px solid #2F578A !important;
        border-radius: 14px !important; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important; padding: 20px 24px !important; margin-bottom: 18px !important;
    }
    [data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"], [data-testid="column"] [data-testid="stContainer"], [data-testid="column"] fieldset[data-testid="stFieldset"] {
        background-color: #2F578A !important; background: #2F578A !important; border: 1px solid rgba(229, 229, 229, 0.25) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] div:has(> div > [data-testid="stDataFrame"]), fieldset[data-testid="stFieldset"] div:has(> div > [data-testid="stDataFrame"]),
    [data-testid="stVerticalBlockBorderWrapper"] div:has(> div > [data-testid="stPlotlyChart"]), fieldset[data-testid="stFieldset"] div:has(> div > [data-testid="stPlotlyChart"]) {
        border: none !important; box-shadow: none !important; padding: 0 !important; margin-bottom: 0 !important; background: transparent !important;
    }
    [data-baseweb="base-input"], [data-baseweb="select"] > div { background-color: #091540 !important; border: 1px solid #2F578A !important; border-radius: 8px !important; }
    [data-baseweb="base-input"] input { color: #E5E5E5 !important; }
    [data-baseweb="tab-list"] { border-bottom: 2px solid #2F578A !important; }
    """
else:
    theme_css = """
    .stApp { background-color: #f1f5f9 !important; color: #0f172a !important; }
    h1, h2, h3, h4, h5, h6, p, span, label, legend { color: #0f172a !important; }
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
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span, [data-testid="stTab"] * {{ font-size: 1.45rem !important; font-weight: 800 !important; letter-spacing: 0.5px !important; }}
    [aria-selected="true"] * {{ color: #007979 !important; }}
    [data-baseweb="tab-highlight"] {{ background-color: #007979 !important; height: 4px !important; border-radius: 3px !important; }}
    button[data-testid="baseButton-primary"] {{ background-color: #007979 !important; color: #ffffff !important; border: none !important; font-weight: 700 !important; height: 48px !important; border-radius: 8px !important; }}
    button[data-testid="baseButton-primary"]:hover {{ background-color: #005f5f !important; color: #ffffff !important; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. HEADER (BORDERLESS)
# ==============================================================================
_, col_main, _ = st.columns([5, 90, 5], gap="small")

with col_main:
    with st.container(border=False):
        h1, h2 = st.columns([6.5, 3.5], vertical_alignment="center")
        with h1:
            st.markdown(f"### {doc['name']}, {doc['suffix']} &nbsp;|&nbsp; <span style='font-size: 1.15rem;'>{doc['role']}</span>", unsafe_allow_html=True)
            st.caption(f"✔ Verified {doc['prc']} • {doc['affiliation']}")
        with h2:
            sc1, sc2, sc3 = st.columns([2.5, 1.8, 1.5])
            sc1.markdown("<div style='background:#fee2e2; color:#ef4444; padding:6px 12px; border-radius:20px; font-weight:700; font-size:0.85rem; text-align:center;'>🫀 Cardiology</div>", unsafe_allow_html=True)
            sc2.markdown(f"<div style='background:#0f172a; color:#fff; padding:6px 12px; border-radius:8px; font-weight:700; font-size:0.85rem; text-align:center;'>Queue: {len(st.session_state.today_queue)}</div>", unsafe_allow_html=True)
            with sc3:
                with st.popover("⚙️"):
                    if st.button("Dark Mode", use_container_width=True): st.session_state.theme_mode = "dark"; st.rerun()
                    if st.button("Light Mode", use_container_width=True): st.session_state.theme_mode = "light"; st.rerun()

    tab_overview, tab_queue, tab_cdss = st.tabs(["Overview", "Patients & Triage", "AI Diagnostics & CDSS"])

    # --------------------------------------------------------------------------
    # TAB 1: OVERVIEW DASHBOARD
    # --------------------------------------------------------------------------
    with tab_overview:
               st.write("")
               
               # CONTAINER 1: Clinical Telemetry & Disease Velocity
               with st.container(border=True):
                   st.markdown("""
                   <div style="margin-bottom: 16px;">
                       <h3 style="margin: 0; font-size: 1.45rem; font-weight: 700;">Clinical Telemetry & Disease Velocity</h3>
                       <p style="margin: 4px 0 0 0; font-size: 0.95rem;">Real-time epidemiological footprint and acute patient influx tracking.</p>
                   </div>
                   """, unsafe_allow_html=True)
                   
                   hero_col, grid_col = st.columns([1.3, 2], gap="large")
                   
                   with hero_col:
                       pct_cvd = (14/38)*100; pct_dia = (10/38)*100; pct_copd = (8/38)*100; pct_neuro = (6/38)*100
                       st.markdown(f"""
                       <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 22px 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.02); height: 295px; display: flex; flex-direction: column; justify-content: space-between;">
                           <div>
                               <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                   <span style="font-size: 0.85rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase;">Total Active Cohort</span>
                                   <span style="background: #e6f4f1; color: #007979; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 20px;">LIVE VELOCITY</span>
                               </div>
                               <div style="font-size: 4.8rem; font-weight: 800; line-height: 1; letter-spacing: -1.5px; margin: 4px 0;">38</div>
                               <div style="font-size: 1.1rem; font-weight: 600;">Monitored Patients</div>
                           </div>
                           <div>
                               <div style="display: flex; height: 10px; border-radius: 6px; overflow: hidden; background: #e2e8f0; margin-bottom: 10px;">
                                   <div style="width: {pct_cvd:.1f}%; background-color: #ef4444;" title="CVD: 14"></div>
                                   <div style="width: {pct_dia:.1f}%; background-color: #f59e0b;" title="Diabetes: 10"></div>
                                   <div style="width: {pct_copd:.1f}%; background-color: #0284c7;" title="COPD: 8"></div>
                                   <div style="width: {pct_neuro:.1f}%; background-color: #8b5cf6;" title="Neuro: 6"></div>
                               </div>
                               <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600;">
                                   <span style="display: flex; align-items: center; gap: 5px;"><span style="height: 8px; width: 8px; border-radius: 50%; background: #ef4444;"></span> 14 CVD</span>
                                   <span style="display: flex; align-items: center; gap: 5px;"><span style="height: 8px; width: 8px; border-radius: 50%; background: #f59e0b;"></span> 10 Dia</span>
                                   <span style="display: flex; align-items: center; gap: 5px;"><span style="height: 8px; width: 8px; border-radius: 50%; background: #0284c7;"></span> 8 COPD</span>
                                   <span style="display: flex; align-items: center; gap: 5px;"><span style="height: 8px; width: 8px; border-radius: 50%; background: #8b5cf6;"></span> 6 Neuro</span>
                               </div>
                           </div>
                       </div>
                       """, unsafe_allow_html=True)
                       
                   with grid_col:
                       r1_c1, r1_c2 = st.columns(2, gap="medium")
                       with r1_c1:
                           st.markdown("""
                           <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                               <div style="display: flex; justify-content: space-between;"><span style="font-size: 0.95rem; font-weight: 600;">🫀 Cardiovascular</span> <span style="color: #ef4444; font-weight: 700; font-size: 0.9rem;">▲ +18%</span></div>
                               <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">14 <span style="font-size: 1.2rem; font-weight: 600; color: #64748b;">Patients</span></div>
                               <div style="font-size: 0.85rem; font-weight: 600; background: #fee2e2; color: #ef4444; padding: 4px 8px; border-radius: 4px; display: inline-block; width: fit-content;">🔴 4 New Stage-2 HTN Onsets</div>
                           </div>
                           """, unsafe_allow_html=True)
                       with r1_c2:
                           st.markdown("""
                           <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                               <div style="display: flex; justify-content: space-between;"><span style="font-size: 0.95rem; font-weight: 600;">🩸 Type 2 Diabetes</span> <span style="color: #f59e0b; font-weight: 700; font-size: 0.9rem;">▲ +12%</span></div>
                               <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">10 <span style="font-size: 1.2rem; font-weight: 600; color: #64748b;">Patients</span></div>
                               <div style="font-size: 0.85rem; font-weight: 600; background: #fef3c7; color: #d97706; padding: 4px 8px; border-radius: 4px; display: inline-block; width: fit-content;">🟡 2 Rapid Glycemic Spikes</div>
                           </div>
                           """, unsafe_allow_html=True)
       
                       st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
       
                       r2_c1, r2_c2 = st.columns(2, gap="medium")
                       with r2_c1:
                           st.markdown("""
                           <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                               <div style="display: flex; justify-content: space-between;"><span style="font-size: 0.95rem; font-weight: 600;">🫁 Pulmonology (COPD)</span> <span style="color: #10b981; font-weight: 700; font-size: 0.9rem;">▼ -5%</span></div>
                               <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">8 <span style="font-size: 1.2rem; font-weight: 600; color: #64748b;">Patients</span></div>
                               <div style="font-size: 0.85rem; font-weight: 600; background: #d1fae5; color: #059669; padding: 4px 8px; border-radius: 4px; display: inline-block; width: fit-content;">🟢 0 Acute Exacerbations</div>
                           </div>
                           """, unsafe_allow_html=True)
                       with r2_c2:
                           st.markdown("""
                           <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                               <div style="display: flex; justify-content: space-between;"><span style="font-size: 0.95rem; font-weight: 600;">🧠 Neuro / Psychiatry</span> <span style="color: #ef4444; font-weight: 700; font-size: 0.9rem;">▲ +25%</span></div>
                               <div style="font-size: 2.5rem; font-weight: 800; line-height: 1;">6 <span style="font-size: 1.2rem; font-weight: 600; color: #64748b;">Patients</span></div>
                               <div style="font-size: 0.85rem; font-weight: 600; background: #fee2e2; color: #ef4444; padding: 4px 8px; border-radius: 4px; display: inline-block; width: fit-content;">🔴 3 Urgent Referrals</div>
                           </div>
                           """, unsafe_allow_html=True)
       
                   st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
       
                   risk_c1, risk_c2, risk_c3, risk_c4 = st.columns(4, gap="medium")
                   with risk_c1:
                       st.markdown("""
                       <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                           <div style="font-size: 0.88rem; font-weight: 600;">Total Assessed</div>
                           <div style="font-size: 2rem; font-weight: 800; line-height: 1;">12 Today</div>
                       </div>
                       """, unsafe_allow_html=True)
                   with risk_c2:
                       st.markdown("""
                       <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                           <div style="font-size: 0.88rem; font-weight: 600;">Low Risk</div>
                           <div style="font-size: 2rem; font-weight: 800; line-height: 1; color: #10b981;">5 Patients</div>
                       </div>
                       """, unsafe_allow_html=True)
                   with risk_c3:
                       st.markdown("""
                       <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                           <div style="font-size: 0.88rem; font-weight: 600;">Medium Risk</div>
                           <div style="font-size: 2rem; font-weight: 800; line-height: 1; color: #f59e0b;">4 Patients</div>
                       </div>
                       """, unsafe_allow_html=True)
                   with risk_c4:
                       st.markdown("""
                       <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                           <div style="font-size: 0.88rem; font-weight: 600;">High Risk</div>
                           <div style="font-size: 2rem; font-weight: 800; line-height: 1; color: #ef4444;">3 Patients 🔴</div>
                       </div>
                       """, unsafe_allow_html=True)
       
               st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
       
               # CONTAINER 2: Patient Inflow & Disease Trends (SOLID ELEVATED CARD)
               with st.container(border=True):
                   tc1, tc2 = st.columns([1, 1], vertical_alignment="center")
                   with tc1:
                       st.markdown("### Patient Inflow & Disease Trends")
                       st.caption("Longitudinal tracking of patient consultations by condition.")
                   with tc2:
                       timeframe = st.radio("Select View:", ["Daily (Hours)", "Weekly (7 Days)", "Monthly (30 Days)"], horizontal=True, label_visibility="collapsed", key="doc_timeframe")
                   
                   if timeframe == "Daily (Hours)":
                       df_trends = pd.DataFrame({"Cardio": [1,3,4,2,3], "Diabetes": [0,2,2,3,1], "COPD": [2,1,0,1,2]}, index=["08:00", "10:00", "12:00", "14:00", "16:00"])
                   elif timeframe == "Weekly (7 Days)":
                       df_trends = pd.DataFrame({"Cardio": [5,7,8,4,6], "Diabetes": [3,4,5,6,4], "COPD": [4,2,3,2,5]}, index=["Mon", "Tue", "Wed", "Thu", "Fri"])
                   else:
                       df_trends = pd.DataFrame({"Cardio": [25,30,28,42], "Diabetes": [18,22,20,26], "COPD": [15,12,14,10]}, index=["Wk 1", "Wk 2", "Wk 3", "Wk 4"])
       
                   st.line_chart(df_trends, height=260, use_container_width=True, color=["#ef4444", "#f59e0b", "#0284c7"])
       
               st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
       
               # CONTAINER 3: AI Concordance & Live Waiting Room (SIDE-BY-SIDE ELEVATED CARDS)
               ai_col, triage_col = st.columns([1, 1.8], gap="large")
               with ai_col:
                   with st.container(border=True):
                       st.markdown("#### AI Concordance Meter")
                       fig = go.Figure(go.Indicator(
                           mode="gauge+number", value=88.5, number={'suffix': "%", 'font': {'size': 36}},
                           title={'text': "<span style='font-size:14px; color:#10b981; font-weight:bold;'>24 Confirmed / 3 Modified</span>", 'font': {'size': 18}},
                           gauge={'bar': {'color': "#007979"}, 'axis': {'range': [0, 100]}, 'steps': [
                               {'range': [0, 50], 'color': 'rgba(239, 68, 68, 0.2)'},
                               {'range': [50, 80], 'color': 'rgba(245, 158, 11, 0.2)'},
                               {'range': [80, 100], 'color': 'rgba(16, 185, 129, 0.2)'}
                           ]}
                       ))
                       fig.update_layout(height=230, margin=dict(l=15, r=15, t=35, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                       st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                       
               with triage_col:
                   with st.container(border=True):
                       st.markdown("#### Live Waiting Room Acuity")
                       st.dataframe(
                           pd.DataFrame(st.session_state.today_queue)[["queue_no", "name", "time_in", "urgency"]],
                           use_container_width=True, hide_index=True,
                           column_config={"queue_no": "Queue", "name": "Patient", "time_in": "Time In", "urgency": "Acuity Status"}
                       )

    # --------------------------------------------------------------------------
    # TAB 2: PATIENTS & TRIAGE
    # --------------------------------------------------------------------------
    with tab_queue:
        st.write("")
        st.markdown("### Today's Active Triage Queue")
        st.caption("Operational patient influx, elapsed wait clocks, and clinical safety flags.")
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        
        for p in st.session_state.today_queue:
            if "wait_mins" not in p: p["wait_mins"] = 24 if "Critical" in p['urgency'] else 12
            if "vitals" not in p: p["vitals"] = "BP: 165/95 mmHg · HR: 104 bpm · O2: 96%" if "Alvarez" in p['name'] else "RBS: 280 mg/dL · Temp: 37.1°C"
            if "prior_directive" not in p: p["prior_directive"] = "Titrated Amlodipine to 10mg on Aug 15 — assess for lower limb edema."
            if "watch_flag" not in p: p["watch_flag"] = "Patient was non-adherent with statin regimen."
            if "lifecycle_status" not in p: p["lifecycle_status"] = "In Waiting Room"

        for i, p in enumerate(st.session_state.today_queue):
            is_critical = "Critical" in p['urgency']
            is_breach = is_critical and p["wait_mins"] > 15
            
            with st.container(border=True):
                qc1, qc2, qc3, qc4, qc5 = st.columns([1.2, 1.8, 1.5, 3.5, 2], vertical_alignment="center")
                
                with qc1:
                    timer_color = "#ef4444" if is_breach else "#64748b"
                    timer_weight = "800" if is_breach else "600"
                    st.markdown(f"**{p['queue_no']}**<br><span style='font-size:0.8rem; color:#64748b;'>In: {p['time_in']}</span><br><span style='font-size:0.8rem; color:{timer_color}; font-weight:{timer_weight};'>Wait: {p['wait_mins']}m</span>", unsafe_allow_html=True)
                
                with qc2:
                    st.markdown(f"**{p['id']}**<br><span style='font-size:0.9rem; font-weight:700;'>{p['name']}</span>", unsafe_allow_html=True)
                
                with qc3:
                    badge_bg = "#fee2e2" if is_critical else "#fef3c7" if "Priority" in p['urgency'] else "#d1fae5"
                    badge_fg = "#ef4444" if is_critical else "#d97706" if "Priority" in p['urgency'] else "#059669"
                    st.markdown(f"<div style='background:{badge_bg}; color:{badge_fg}; padding:4px 8px; border-radius:6px; font-weight:700; font-size:0.8rem; display:inline-block; margin-bottom: 4px;'>{p['urgency']}</div>", unsafe_allow_html=True)
                    if is_breach:
                        st.markdown("<div style='color:#ef4444; font-size:0.75rem; font-weight:bold; padding: 2px 0;'>⚠️ 15m Breach Alert</div>", unsafe_allow_html=True)
                
                with qc4:
                    st.markdown(f"""
                    <div style="font-size: 0.85rem; line-height: 1.4;">
                        <b>Chief:</b> {p['complaint']}<br>
                        <span style="color: #007979; font-weight: 700; font-size: 0.8rem;">🩺 Vitals: {p['vitals']}</span><br>
                        <span style="color: #475569; font-size: 0.78rem;">📌 <b>Directive:</b> {p['prior_directive']}</span><br>
                        <span style="color: #d97706; font-size: 0.78rem;">⚡ <b>Watch:</b> {p['watch_flag']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with qc5:
                    status_options = ["In Waiting Room", "In Consultation", "On Hold / Labs Dispatched"]
                    current_status = p.get("lifecycle_status", "In Waiting Room")
                    selected_status = st.selectbox("Lifecycle", options=status_options, index=status_options.index(current_status) if current_status in status_options else 0, key=f"status_{p['id']}", label_visibility="collapsed")
                    p["lifecycle_status"] = selected_status
                    
                    is_active = st.session_state.active_patient and st.session_state.active_patient['id'] == p['id']
                    if st.button("🩺 Consult", key=f"q_btn_{p['id']}", type="primary" if is_active else "secondary", use_container_width=True):
                        full_record = next((pat for pat in master_patients if pat["id"] == p["id"]), None)
                        if full_record: 
                            p["lifecycle_status"] = "In Consultation"
                            start_consult(full_record)
                            st.rerun()
                    
                    if st.button("🚨 ER Bypass", key=f"er_btn_{p['id']}", use_container_width=True):
                        st.error(f"🚨 ER Bypass Slip generated for {p['name']}. Transporting to Emergency Department immediately.")

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### Specialty-Personalized Master Patient Directory")
            st.caption("Dynamic chronic modality switching with risk-stratified filtering and record preview.")
            
            f_c1, f_c2, f_c3 = st.columns([2.2, 2, 2], gap="medium")
            with f_c1: 
                search_q = st.text_input("Search Directory", placeholder="Query Name, ID, or Health #...", label_visibility="collapsed", key="pat_dir_search")
            with f_c2: 
                risk_filter = st.multiselect("Risk Stratification", ["High Risk Flagged", "Stable", "Awaiting Review", "Overdue for Checkup"], placeholder="Filter by Risk...", label_visibility="collapsed", key="pat_risk_sel")
            with f_c3: 
                curr_mod_short = mod_map_rev.get(st.session_state.active_modality, "Cardiovascular (CVD)")
                curr_idx = list(mod_map.keys()).index(curr_mod_short) if curr_mod_short in mod_map else 0
                modality_view = st.selectbox(
                    "Chronic Modality Switcher", 
                    list(mod_map.keys()), 
                    index=curr_idx, 
                    label_visibility="collapsed", 
                    key="modality_switcher",
                    on_change=_sync_from_tab2
                )

            df_patients = pd.DataFrame(master_patients)
            
            if search_q: 
                df_patients = df_patients[df_patients["name"].str.contains(search_q, case=False) | df_patients["id"].str.contains(search_q, case=False)]
            if risk_filter: 
                df_patients = df_patients[df_patients["risk_flag"].isin(risk_filter)]

            if "Cardiovascular" in modality_view:
                display_cols = ["id", "name", "latest_bp", "resting_hr", "total_chol", "last_ecg", "risk_flag"]
                col_cfg = {"id": "Patient ID", "name": "Full Name", "latest_bp": "Latest BP (mmHg)", "resting_hr": "Resting HR", "total_chol": "Total Chol", "last_ecg": "Last ECG", "risk_flag": "Risk Status"}
            elif "Diabetes" in modality_view:
                display_cols = ["id", "name", "fasting_glucose", "hba1c", "bmi", "last_ecg", "risk_flag"]
                col_cfg = {"id": "Patient ID", "name": "Full Name", "fasting_glucose": "Fast Glucose (mg/dL)", "hba1c": "HbA1c (%)", "bmi": "Current BMI", "last_ecg": "Last Lab Date", "risk_flag": "Risk Status"}
            elif "COPD" in modality_view:
                display_cols = ["id", "name", "spo2", "fev1_fvc", "pack_years", "risk_flag"]
                col_cfg = {"id": "Patient ID", "name": "Full Name", "spo2": "Resting SpO2 (%)", "fev1_fvc": "FEV1/FVC Ratio", "pack_years": "Pack-Years", "risk_flag": "Risk Status"}
            else:
                display_cols = ["id", "name", "phq9", "gad7", "sleep_hrs", "risk_flag"]
                col_cfg = {"id": "Patient ID", "name": "Full Name", "phq9": "PHQ-9 Score", "gad7": "GAD-7 Score", "sleep_hrs": "Sleep (hrs)", "risk_flag": "Risk Status"}

            dir_selection = st.dataframe(
                df_patients[display_cols], use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", key="master_dir_table",
                column_config=col_cfg
            )

            sel_dir_rows = dir_selection.selection.rows
            
            # Record Preview & Dual Action Buttons
            enq_c1, enq_c2 = st.columns([3, 2], vertical_alignment="center")
            with enq_c1:
                if sel_dir_rows:
                    selected_dir_patient = df_patients.iloc[sel_dir_rows[0]]
                    st.markdown(f"""
                    <div style="background: rgba(0, 121, 121, 0.05); border: 1px solid rgba(0, 121, 121, 0.2); border-radius: 8px; padding: 12px; margin-top: 10px; margin-bottom: 12px;">
                        <h5 style="margin:0 0 6px 0; color:#007979; font-size: 0.95rem;">📋 Record Preview: {selected_dir_patient['name']} (`{selected_dir_patient['id']}`)</h5>
                        <div style="display: flex; gap: 18px; font-size: 0.85rem;">
                            <div><b>Active Rx:</b> {selected_dir_patient.get('active_rx', 'None')}</div>
                            <div><b>Allergies:</b> <span style="color:#ef4444; font-weight:700;">{selected_dir_patient.get('allergies', 'None')}</span></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.caption("*(Select a patient row to preview records and unlock consultation actions)*")

            with enq_c2:
                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                act_c1, act_c2 = st.columns(2)
                with act_c1:
                    if st.button("➕ Enqueue to Queue", type="secondary", use_container_width=True, disabled=not bool(sel_dir_rows)):
                        if sel_dir_rows:
                            target_p = df_patients.iloc[sel_dir_rows[0]]
                            new_q = f"Q-{len(st.session_state.today_queue)+1:02d}"
                            st.session_state.today_queue.append({
                                "queue_no": new_q, "time_in": datetime.now().strftime("%I:%M %p"), "id": target_p["id"],
                                "name": target_p["name"], "urgency": "🟡 Priority", "complaint": "Walk-in unscheduled clinic evaluation.",
                                "wait_mins": 1, "vitals": f"BP: {target_p.get('latest_bp','120/80')} · HR: {target_p.get('resting_hr','75')} bpm",
                                "prior_directive": "Scheduled walk-in checkup.", "watch_flag": "None declared.", "lifecycle_status": "In Waiting Room"
                            })
                            st.success(f"Successfully injected {target_p['name']} into active queue as {new_q}.")
                            st.rerun()
                with act_c2:
                    if st.button("🩺 Immediate Consult", type="primary", use_container_width=True, disabled=not bool(sel_dir_rows)):
                        if sel_dir_rows:
                            target_dict = df_patients.iloc[sel_dir_rows[0]].to_dict()
                            target_dict["lifecycle_status"] = "In Consultation"
                            start_consult(target_dict)
                            st.rerun()

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # --- 2.5 FAMILY HISTORY MATRIX ---
        with st.container(border=True):
            st.markdown("### Patient Hereditary Risk & Family History Matrix")
            st.caption("Isolates inherited predispositions across the patient cohort to flag familial risk factors.")
            
            fh_c1, fh_c2, fh_c3 = st.columns([2.2, 2, 2], gap="medium")
            with fh_c1:
                fh_search = st.text_input("Search Family History", placeholder="Query Name or ID...", label_visibility="collapsed", key="fh_search_input")
            with fh_c2:
                fh_mod_filter = st.selectbox("Genetic Category Filter", ["All Categories", "Cardiovascular Hereditary", "Diabetes Lineage", "Pulmonary/Asthma History", "Neurodegenerative/Psychiatric"], label_visibility="collapsed", key="fh_mod_sel")
            with fh_c3:
                fh_risk_filter = st.selectbox("Hereditary Risk Filter", ["All Risk Levels", "🔴 High Genetic Load", "🟡 Moderate Risk", "🟢 Low Risk"], label_visibility="collapsed", key="fh_risk_sel")

            family_history_data = [
                {"id": "PAT-9912", "name": "Alvarez, Carlos T.", "modality": "Cardiovascular Hereditary", "lineage": "Father: Early CVD <55 yrs | Mother: Hypertension", "onset": "Early Onset (<55 yrs)", "risk_status": "🔴 High Genetic Load"},
                {"id": "PAT-4421", "name": "Santos, Sofia M.", "modality": "Diabetes Lineage", "lineage": "Mother: Type 2 Diabetes (Diagnosed at 48)", "onset": "Adult Onset (>40 yrs)", "risk_status": "🟡 Moderate Risk"},
                {"id": "PAT-1102", "name": "Mason, Justin L.", "modality": "Neurodegenerative/Psychiatric", "lineage": "Father: Dementia | Sister: Depression", "onset": "Adult Onset (>50 yrs)", "risk_status": "🟡 Moderate Risk"},
            ]
            
            df_fh = pd.DataFrame(family_history_data)
            if fh_search:
                df_fh = df_fh[df_fh["name"].str.contains(fh_search, case=False) | df_fh["id"].str.contains(fh_search, case=False)]
            if fh_mod_filter != "All Categories":
                df_fh = df_fh[df_fh["modality"] == fh_mod_filter]
            if fh_risk_filter != "All Risk Levels":
                df_fh = df_fh[df_fh["risk_status"] == fh_risk_filter]

            fh_selection = st.dataframe(
                df_fh[["id", "name", "modality", "lineage", "onset", "risk_status"]],
                use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", key="fh_matrix_table",
                column_config={
                    "id": "Patient ID", "name": "Full Name", "modality": "Primary Modality",
                    "lineage": "Immediate Lineage History", "onset": "Age of Onset Flag", "risk_status": "Hereditary Risk Index"
                }
            )

            sel_fh_rows = fh_selection.selection.rows
            if sel_fh_rows:
                selected_fh_patient = df_fh.iloc[sel_fh_rows[0]]
                st.markdown(f"""
                <div style="background: rgba(239, 68, 68, 0.04); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; padding: 12px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h5 style="margin:0 0 2px 0; color:#ef4444; font-size: 0.92rem;">🧬 Selected Hereditary Profile: {selected_fh_patient['name']} (`{selected_fh_patient['id']}`)</h5>
                        <span style="font-size: 0.85rem;"><b>Lineage Matrix:</b> {selected_fh_patient['lineage']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                act_col1, act_col2 = st.columns(2)
                with act_col1:
                    if st.button("🧬 View Full Genomic / Family Tree Profile", use_container_width=True, key="btn_view_genomic"):
                        st.info(f"Opening detailed genomic pedigree tree mapping for {selected_fh_patient['name']}...")
                with act_col2:
                    if st.button("➕ Add Hereditary Note", use_container_width=True, key="btn_add_hereditary_note"):
                        st.success(f"Hereditary note modal unlocked for {selected_fh_patient['name']}.")
            else:
                st.caption("*(Select a row in the Family History matrix above to review genomic governance options)*")

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        with st.expander("📈 Longitudinal Timeline & Clinical Encounter History", expanded=False):
            if sel_dir_rows:
                timeline_pat = df_patients.iloc[sel_dir_rows[0]]
                st.markdown(f"#### Patient Record: {timeline_pat['name']} (`{timeline_pat['id']}`)")
                
                t_col1, t_col2 = st.columns([1.2, 1.8], gap="large")
                with t_col1:
                    st.markdown("##### Chronological Consultation Feed")
                    st.markdown("""
                    * **Sep 13, 2026** — *ICD-10: I10 (Essential Hypertension)*
                      * *Notes:* Patient reported mild headaches. Adjusted Losartan dosage.
                    * **Jun 20, 2026** — *ICD-10: E78.5 (Hyperlipidemia)*
                      * *Notes:* Routine lipid panel check. Statin therapy sustained.
                    * **Jan 10, 2026** — *ICD-10: Z00.00 (General Adult Medical Exam)*
                      * *Notes:* Baseline annual physical clear. Vitals stable.
                    """)
                with t_col2:
                    st.markdown(f"##### Biomarker Trajectory ({modality_view})")
                    if "Cardiovascular" in modality_view:
                        traj_df = pd.DataFrame({"Month": ["Jan", "Mar", "Jun", "Aug", "Sep"], "Systolic BP": [130, 135, 142, 150, 165], "Diastolic BP": [82, 85, 88, 90, 95]}).set_index("Month")
                        st.line_chart(traj_df, height=210, color=["#ef4444", "#38bdf8"])
                    elif "Diabetes" in modality_view:
                        traj_df = pd.DataFrame({"Month": ["Jan", "Mar", "Jun", "Aug", "Sep"], "HbA1c (%)": [8.4, 8.1, 7.9, 8.0, 7.8], "Fast Glucose": [160, 150, 145, 150, 142]}).set_index("Month")
                        st.line_chart(traj_df, height=210, color=["#f59e0b", "#10b981"])
                    elif "COPD" in modality_view:
                        traj_df = pd.DataFrame({"Month": ["Jan", "Mar", "Jun", "Aug", "Sep"], "SpO2 (%)": [94, 93, 92, 91, 95], "FEV1 (%)": [75, 74, 73, 72, 72]}).set_index("Month")
                        st.line_chart(traj_df, height=210, color=["#0284c7", "#8b5cf6"])
                    else:
                        traj_df = pd.DataFrame({"Month": ["Jan", "Mar", "Jun", "Aug", "Sep"], "PHQ-9 Score": [9, 8, 7, 6, 6], "GAD-7 Score": [7, 6, 5, 4, 4]}).set_index("Month")
                        st.line_chart(traj_df, height=210, color=["#a855f7", "#ec4899"])
            else:
                st.info("No patient selected. Please highlight a row in the Master Patient Directory table above to load timelines.")

    # --------------------------------------------------------------------------
    # TAB 3: AI DIAGNOSTICS & CDSS (VERTICAL STACK)
    # --------------------------------------------------------------------------
    with tab_cdss:
        st.write("")
        
        # Identity Context Fallback
        if not st.session_state.get("active_patient") and master_patients:
            st.session_state.active_patient = master_patients[0]
            
        active_pat = st.session_state.active_patient
        pid = active_pat["id"]

        with st.container(border=True):
            st.markdown(f"### Active Consultation: **{active_pat['name']}** (`{pid}`)")
            s1, s2, s3, s4, s5 = st.columns(5)
            s1.metric("Chronological Age", f"{active_pat.get('age', '--')} Yrs")
            s2.metric("Biological Sex", active_pat.get("sex", "--"))
            s3.metric("Current BMI", active_pat.get("bmi", "--"))
            s4.metric("Resting Heart Rate", f"{active_pat.get('resting_hr', '--')} bpm")
            s5.metric("Latest Blood Pressure", active_pat.get("latest_bp", "--"))

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

        modality_labels = [
            "Cardiovascular Diseases (Hypertension / CVD)",
            "Type 2 Diabetes Mellitus",
            "Chronic Respiratory Diseases (COPD & Asthma)",
            "Mental Health & Neurological Disorders"
        ]
        
        # Synchronized Modality Selector
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

        # Cross-Modality Hereditary Parser
        fam_hist_list = active_pat.get("fam_history", [])
        fam_hist_str = " | ".join(fam_hist_list).lower()
        has_cvd_history = any(kw in fam_hist_str for kw in ["cvd", "hypertension", "cardiac"])
        has_dia_history = any(kw in fam_hist_str for kw in ["diabetes", "t2d", "glycemic"])
        has_neuro_history = any(kw in fam_hist_str for kw in ["neurological", "psychiatric", "depression", "dementia"])
        registry_caption = f"🧬 Linked from Registry: {' | '.join(fam_hist_list)}" if fam_hist_list else "No relevant familial risk declared in registry."

        # Parse Spirometry Float
        try: fev_ratio_val = float(str(active_pat.get("fev1_fvc", "70.5")).replace("%", ""))
        except: fev_ratio_val = 70.5

        # ======================================================================
        # UPPER CONTAINER: FULL-WIDTH PARAMETER INGESTION FORM
        # ======================================================================
        with st.container(border=True):
            with st.form(key=f"cdss_{modality_key}_form_{pid}", clear_on_submit=False):
                st.markdown(f"#### Parameter Ingestion — {modality_schema_name}")
                st.caption("Physiological boundaries and strict type-constraints enforced. Free-text biomarker inputs are locked.")
                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                
                payload_buffer = {}

                # ==========================================================
                # MODALITY 1: CARDIOVASCULAR DISEASES (CVD)
                # ==========================================================
                if modality_key == "cardiovascular":
                    with st.expander("🩺 Hemodynamics & Anthropometrics", expanded=True):
                        cvd_age = st.number_input("Age", min_value=18, max_value=90, value=int(active_pat.get("age", 58)), step=1, key=f"cvd_age_{pid}")
                        st.caption("Expected Clinical Range: 18 – 90 Years")
                        payload_buffer["Age"] = {"raw_value": cvd_age, "unit": "Years"}

                        cvd_sex = st.selectbox("Biological Sex", options=["Female", "Male"], index=1 if active_pat.get("sex") == "Male" else 0, key=f"cvd_sex_{pid}")
                        st.caption("Reference: Female / Male")
                        payload_buffer["Biological Sex"] = {"raw_value": cvd_sex, "unit": "None"}

                        cvd_sbp = st.number_input("Systolic Blood Pressure (SBP)", min_value=70.0, max_value=220.0, value=float(active_pat.get("latest_bp", "120/80").split("/")[0]), step=1.0, format="%.1f", key=f"cvd_sbp_{pid}")
                        st.caption("Expected Clinical Range: 70 – 220 mmHg")
                        payload_buffer["Systolic Blood Pressure (SBP)"] = {"raw_value": cvd_sbp, "unit": "mmHg"}

                        cvd_dbp = st.number_input("Diastolic Blood Pressure (DBP)", min_value=40.0, max_value=130.0, value=float(active_pat.get("latest_bp", "120/80").split("/")[1]), step=1.0, format="%.1f", key=f"cvd_dbp_{pid}")
                        st.caption("Expected Clinical Range: 40 – 130 mmHg")
                        payload_buffer["Diastolic Blood Pressure (DBP)"] = {"raw_value": cvd_dbp, "unit": "mmHg"}

                        cvd_hr = st.number_input("Heart Rate (Resting)", min_value=40, max_value=180, value=int(active_pat.get("resting_hr", 75)), step=1, key=f"cvd_hr_{pid}")
                        st.caption("Expected Clinical Range: 40 – 180 bpm")
                        payload_buffer["Heart Rate (Resting)"] = {"raw_value": cvd_hr, "unit": "bpm"}

                        cvd_bmi = st.number_input("Body Mass Index (BMI)", min_value=12.0, max_value=60.0, value=float(active_pat.get("bmi", 26.5)), step=0.1, format="%.1f", key=f"cvd_bmi_{pid}")
                        st.caption("Expected Clinical Range: 12.0 – 60.0 kg/m²")
                        payload_buffer["Body Mass Index (BMI)"] = {"raw_value": cvd_bmi, "unit": "kg/m²"}

                    with st.expander("🧪 Serum Lipid, Inflammatory & Renal Panels", expanded=False):
                        cvd_tc = st.number_input("Total Cholesterol", min_value=100.0, max_value=400.0, value=float(active_pat.get("total_chol", 200.0)), step=1.0, format="%.1f", key=f"cvd_tc_{pid}")
                        st.caption("Expected Clinical Range: 100 – 400 mg/dL")
                        payload_buffer["Total Cholesterol"] = {"raw_value": cvd_tc, "unit": "mg/dL"}

                        cvd_hdl = st.number_input("High-Density Lipoprotein (HDL)", min_value=15.0, max_value=120.0, value=45.0, step=1.0, format="%.1f", key=f"cvd_hdl_{pid}")
                        st.caption("Expected Clinical Range: 15 – 120 mg/dL")
                        payload_buffer["High-Density Lipoprotein (HDL)"] = {"raw_value": cvd_hdl, "unit": "mg/dL"}

                        cvd_ldl = st.number_input("Low-Density Lipoprotein (LDL)", min_value=30.0, max_value=300.0, value=130.0, step=1.0, format="%.1f", key=f"cvd_ldl_{pid}")
                        st.caption("Expected Clinical Range: 30 – 300 mg/dL")
                        payload_buffer["Low-Density Lipoprotein (LDL)"] = {"raw_value": cvd_ldl, "unit": "mg/dL"}

                        cvd_trig = st.number_input("Serum Triglycerides", min_value=40.0, max_value=1000.0, value=160.0, step=1.0, format="%.1f", key=f"cvd_trig_{pid}")
                        st.caption("Expected Clinical Range: 40 – 1000 mg/dL")
                        payload_buffer["Serum Triglycerides"] = {"raw_value": cvd_trig, "unit": "mg/dL"}

                        cvd_hscrp = st.number_input("High-Sensitivity C-Reactive Protein (hs-CRP)", min_value=0.1, max_value=50.0, value=2.5, step=0.1, format="%.1f", key=f"cvd_hscrp_{pid}")
                        st.caption("Expected Clinical Range: 0.1 – 50.0 mg/L")
                        payload_buffer["High-Sensitivity C-Reactive Protein (hs-CRP)"] = {"raw_value": cvd_hscrp, "unit": "mg/L"}

                        cvd_creat = st.number_input("Serum Creatinine", min_value=0.4, max_value=10.0, value=1.00, step=0.01, format="%.2f", key=f"cvd_creat_{pid}")
                        st.caption("Expected Clinical Range: 0.4 – 10.0 mg/dL")
                        payload_buffer["Serum Creatinine"] = {"raw_value": cvd_creat, "unit": "mg/dL"}

                        cvd_egfr = st.number_input("Estimated Glomerular Filtration Rate (eGFR)", min_value=5.0, max_value=140.0, value=85.0, step=1.0, format="%.1f", key=f"cvd_egfr_{pid}")
                        st.caption("Expected Clinical Range: 5 – 140 mL/min/1.73m²")
                        payload_buffer["Estimated Glomerular Filtration Rate (eGFR)"] = {"raw_value": cvd_egfr, "unit": "mL/min/1.73m²"}

                    with st.expander("🫀 Cardiac Necrosis & Hemodynamics", expanded=False):
                        cvd_lvef = st.number_input("Left Ventricular Ejection Fraction (LVEF)", min_value=15.0, max_value=75.0, value=55.0, step=1.0, format="%.1f", key=f"cvd_lvef_{pid}")
                        st.caption("Expected Clinical Range: 15 – 75 %")
                        payload_buffer["Left Ventricular Ejection Fraction (LVEF)"] = {"raw_value": cvd_lvef, "unit": "%"}

                        cvd_ctni = st.number_input("Cardiac Troponin I (cTnI)", min_value=0.01, max_value=50.0, value=0.02, step=0.01, format="%.2f", key=f"cvd_ctni_{pid}")
                        st.caption("Expected Clinical Range: 0.01 – 50.0 ng/mL")
                        payload_buffer["Cardiac Troponin I (cTnI)"] = {"raw_value": cvd_ctni, "unit": "ng/mL"}

                        cvd_ntpro = st.number_input("N-Terminal Pro-B-Type Natriuretic Peptide (NT-proBNP)", min_value=10.0, max_value=35000.0, value=95.0, step=10.0, format="%.1f", key=f"cvd_ntpro_{pid}")
                        st.caption("Expected Clinical Range: 10 – 35,000 pg/mL")
                        payload_buffer["N-Terminal Pro-B-Type Natriuretic Peptide (NT-proBNP)"] = {"raw_value": cvd_ntpro, "unit": "pg/mL"}

                    with st.expander("🏃 Behavioral Risk Factors & Hereditary Predisposition", expanded=False):
                        cvd_smoke = st.number_input("Smoking History", min_value=0.0, max_value=120.0, value=float(active_pat.get("pack_years", 0.0)), step=1.0, format="%.1f", key=f"cvd_smoke_{pid}")
                        st.caption("Expected Clinical Range: 0 – 120 Pack-Years")
                        payload_buffer["Smoking History"] = {"raw_value": cvd_smoke, "unit": "Pack-Years"}

                        cvd_sodium = st.number_input("Daily Sodium Intake", min_value=500.0, max_value=10000.0, value=2500.0, step=50.0, format="%.1f", key=f"cvd_sodium_{pid}")
                        st.caption("Expected Clinical Range: 500 – 10,000 mg/day")
                        payload_buffer["Daily Sodium Intake"] = {"raw_value": cvd_sodium, "unit": "mg/day"}

                        cvd_famhist = st.radio("Family History of Premature CVD", options=["0", "1"], index=1 if has_cvd_history else 0, horizontal=True, key=f"cvd_famhist_{pid}")
                        st.caption(registry_caption)
                        payload_buffer["Family History of Premature CVD"] = {"raw_value": cvd_famhist, "unit": "None"}

                        cvd_activity = st.number_input("Physical Activity Level", min_value=0, max_value=1050, value=150, step=15, key=f"cvd_activity_{pid}")
                        st.caption("Expected Clinical Range: 0 – 1050 mins/week")
                        payload_buffer["Physical Activity Level"] = {"raw_value": cvd_activity, "unit": "mins/week"}

                # ==========================================================
                # MODALITY 2: TYPE 2 DIABETES MELLITUS
                # ==========================================================
                elif modality_key == "diabetes":
                    with st.expander("🩸 Glycemic Status & Endocrine Regulation", expanded=True):
                        dia_fpg = st.number_input("Fasting Plasma Glucose (FPG)", min_value=50.0, max_value=450.0, value=float(active_pat.get("fasting_glucose", 115.0)), step=1.0, format="%.1f", key=f"dia_fpg_{pid}")
                        st.caption("Expected Clinical Range: 50 – 450 mg/dL")
                        payload_buffer["Fasting Plasma Glucose (FPG)"] = {"raw_value": dia_fpg, "unit": "mg/dL"}

                        dia_2hpg = st.number_input("2-Hour Postprandial Glucose (2h-PG)", min_value=60.0, max_value=600.0, value=155.0, step=1.0, format="%.1f", key=f"dia_2hpg_{pid}")
                        st.caption("Expected Clinical Range: 60 – 600 mg/dL")
                        payload_buffer["2-Hour Postprandial Glucose (2h-PG)"] = {"raw_value": dia_2hpg, "unit": "mg/dL"}

                        dia_hba1c = st.number_input("Glycated Hemoglobin (HbA1c)", min_value=4.0, max_value=15.0, value=float(active_pat.get("hba1c", 6.5)), step=0.1, format="%.1f", key=f"dia_hba1c_{pid}")
                        st.caption("Expected Clinical Range: 4.0 – 15.0 %")
                        payload_buffer["Glycated Hemoglobin (HbA1c)"] = {"raw_value": dia_hba1c, "unit": "%"}

                        dia_ins = st.number_input("Fasting Serum Insulin", min_value=1.0, max_value=100.0, value=15.0, step=0.5, format="%.1f", key=f"dia_ins_{pid}")
                        st.caption("Expected Clinical Range: 1.0 – 100.0 µIU/mL")
                        payload_buffer["Fasting Serum Insulin"] = {"raw_value": dia_ins, "unit": "µIU/mL"}

                        dia_cpep = st.number_input("Serum C-Peptide Level", min_value=0.1, max_value=12.0, value=2.4, step=0.1, format="%.1f", key=f"dia_cpep_{pid}")
                        st.caption("Expected Clinical Range: 0.1 – 12.0 ng/mL")
                        payload_buffer["Serum C-Peptide Level"] = {"raw_value": dia_cpep, "unit": "ng/mL"}

                        dia_homa = st.number_input("HOMA-IR (Insulin Resistance Score)", min_value=0.2, max_value=25.0, value=2.80, step=0.1, format="%.2f", key=f"dia_homa_{pid}")
                        st.caption("Expected Clinical Range: 0.2 – 25.0 Score")
                        payload_buffer["HOMA-IR (Insulin Resistance Score)"] = {"raw_value": dia_homa, "unit": "Score"}

                    with st.expander("📏 Anthropometrics & Central Adiposity", expanded=False):
                        dia_bmi = st.number_input("Body Mass Index (BMI)", min_value=12.0, max_value=60.0, value=float(active_pat.get("bmi", 26.5)), step=0.1, format="%.1f", key=f"dia_bmi_{pid}")
                        st.caption("Expected Clinical Range: 12.0 – 60.0 kg/m²")
                        payload_buffer["Body Mass Index (BMI)"] = {"raw_value": dia_bmi, "unit": "kg/m²"}

                        dia_waist = st.number_input("Waist Circumference", min_value=50.0, max_value=160.0, value=92.0, step=0.5, format="%.1f", key=f"dia_waist_{pid}")
                        st.caption("Expected Clinical Range: 50 – 160 cm")
                        payload_buffer["Waist Circumference"] = {"raw_value": dia_waist, "unit": "cm"}

                        dia_whr = st.number_input("Waist-to-Hip Ratio (WHR)", min_value=0.60, max_value=1.40, value=0.88, step=0.01, format="%.2f", key=f"dia_whr_{pid}")
                        st.caption("Expected Clinical Range: 0.60 – 1.40")
                        payload_buffer["Waist-to-Hip Ratio (WHR)"] = {"raw_value": dia_whr, "unit": "Ratio"}

                    with st.expander("🧪 Hemodynamics, Renal & Metabolic Markers", expanded=False):
                        dia_sbp = st.number_input("Systolic Blood Pressure (SBP)", min_value=70.0, max_value=220.0, value=float(active_pat.get("latest_bp", "120/80").split("/")[0]), step=1.0, format="%.1f", key=f"dia_sbp_{pid}")
                        st.caption("Expected Clinical Range: 70 – 220 mmHg")
                        payload_buffer["Systolic Blood Pressure (SBP)"] = {"raw_value": dia_sbp, "unit": "mmHg"}

                        dia_dbp = st.number_input("Diastolic Blood Pressure (DBP)", min_value=40.0, max_value=130.0, value=float(active_pat.get("latest_bp", "120/80").split("/")[1]), step=1.0, format="%.1f", key=f"dia_dbp_{pid}")
                        st.caption("Expected Clinical Range: 40 – 130 mmHg")
                        payload_buffer["Diastolic Blood Pressure (DBP)"] = {"raw_value": dia_dbp, "unit": "mmHg"}

                        dia_trig = st.number_input("Serum Triglycerides", min_value=40.0, max_value=1000.0, value=175.0, step=1.0, format="%.1f", key=f"dia_trig_{pid}")
                        st.caption("Expected Clinical Range: 40 – 1000 mg/dL")
                        payload_buffer["Serum Triglycerides"] = {"raw_value": dia_trig, "unit": "mg/dL"}

                        dia_hdl = st.number_input("High-Density Lipoprotein (HDL)", min_value=15.0, max_value=120.0, value=42.0, step=1.0, format="%.1f", key=f"dia_hdl_{pid}")
                        st.caption("Expected Clinical Range: 15 – 120 mg/dL")
                        payload_buffer["High-Density Lipoprotein (HDL)"] = {"raw_value": dia_hdl, "unit": "mg/dL"}

                        dia_uacr = st.number_input("Urine Albumin-to-Creatinine Ratio (UACR)", min_value=1.0, max_value=3500.0, value=35.0, step=1.0, format="%.1f", key=f"dia_uacr_{pid}")
                        st.caption("Expected Clinical Range: 1 – 3500 mg/g")
                        payload_buffer["Urine Albumin-to-Creatinine Ratio (UACR)"] = {"raw_value": dia_uacr, "unit": "mg/g"}

                        dia_uric = st.number_input("Serum Uric Acid", min_value=1.5, max_value=14.0, value=6.2, step=0.1, format="%.1f", key=f"dia_uric_{pid}")
                        st.caption("Expected Clinical Range: 1.5 – 14.0 mg/dL")
                        payload_buffer["Serum Uric Acid"] = {"raw_value": dia_uric, "unit": "mg/dL"}

                    with st.expander("🧬 Lineage, Clinical Presentation & Lifestyle", expanded=False):
                        dia_gest = st.radio("Gestational Diabetes History", options=["0", "1"], index=0, horizontal=True, key=f"dia_gest_{pid}")
                        st.caption("Input Basis: 0 = Negative / No, 1 = Positive / Yes")
                        payload_buffer["Gestational Diabetes History"] = {"raw_value": dia_gest, "unit": "None"}

                        dia_fam = st.radio("Family History of Diabetes", options=["0", "1"], index=1 if has_dia_history else 0, horizontal=True, key=f"dia_fam_{pid}")
                        st.caption(registry_caption)
                        payload_buffer["Family History of Diabetes"] = {"raw_value": dia_fam, "unit": "None"}

                        dia_acan = st.radio("Acanthosis Nigricans Presence", options=["0", "1"], index=0, horizontal=True, key=f"dia_acan_{pid}")
                        st.caption("Input Basis: 0 = Absent, 1 = Present")
                        payload_buffer["Acanthosis Nigricans Presence"] = {"raw_value": dia_acan, "unit": "None"}

                        dia_carb = st.number_input("Daily Carbohydrate Intake", min_value=50.0, max_value=600.0, value=250.0, step=5.0, format="%.1f", key=f"dia_carb_{pid}")
                        st.caption("Expected Clinical Range: 50 – 600 g/day")
                        payload_buffer["Daily Carbohydrate Intake"] = {"raw_value": dia_carb, "unit": "g/day"}

                        dia_sed = st.number_input("Sedentary Behavior Duration", min_value=1.0, max_value=18.0, value=7.0, step=0.5, format="%.1f", key=f"dia_sed_{pid}")
                        st.caption("Expected Clinical Range: 1.0 – 18.0 Hours/day")
                        payload_buffer["Sedentary Behavior Duration"] = {"raw_value": dia_sed, "unit": "Hours/day"}

                # ==========================================================
                # MODALITY 3: CHRONIC RESPIRATORY DISEASES (COPD & ASTHMA)
                # ==========================================================
                elif modality_key == "copd_asthma":
                    with st.expander("🫁 Spirometry, Volumes & Flow Dynamics", expanded=True):
                        cr_fev1 = st.number_input("Forced Expiratory Volume in 1 Second (FEV1)", min_value=0.5, max_value=5.5, value=2.40, step=0.05, format="%.2f", key=f"cr_fev1_{pid}")
                        st.caption("Expected Clinical Range: 0.5 – 5.5 Liters")
                        payload_buffer["Forced Expiratory Volume in 1 Second (FEV1)"] = {"raw_value": cr_fev1, "unit": "Liters"}

                        cr_fvc = st.number_input("Forced Vital Capacity (FVC)", min_value=1.0, max_value=7.0, value=3.40, step=0.05, format="%.2f", key=f"cr_fvc_{pid}")
                        st.caption("Expected Clinical Range: 1.0 – 7.0 Liters")
                        payload_buffer["Forced Vital Capacity (FVC)"] = {"raw_value": cr_fvc, "unit": "Liters"}

                        cr_rat = st.number_input("FEV1/FVC Ratio", min_value=25.0, max_value=95.0, value=fev_ratio_val, step=0.1, format="%.1f", key=f"cr_rat_{pid}")
                        st.caption("Expected Clinical Range: 25.0 – 95.0 %")
                        payload_buffer["FEV1/FVC Ratio"] = {"raw_value": cr_rat, "unit": "%"}

                        cr_pbr = st.number_input("Post-Bronchodilator FEV1 % Predicted", min_value=15.0, max_value=120.0, value=78.0, step=0.5, format="%.1f", key=f"cr_pbr_{pid}")
                        st.caption("Expected Clinical Range: 15.0 – 120.0 %")
                        payload_buffer["Post-Bronchodilator FEV1 % Predicted"] = {"raw_value": cr_pbr, "unit": "%"}

                        cr_pef = st.number_input("Peak Expiratory Flow (PEF)", min_value=50.0, max_value=800.0, value=420.0, step=5.0, format="%.1f", key=f"cr_pef_{pid}")
                        st.caption("Expected Clinical Range: 50 – 800 L/min")
                        payload_buffer["Peak Expiratory Flow (PEF)"] = {"raw_value": cr_pef, "unit": "L/min"}

                    with st.expander("🧪 Inflammatory Biomarkers & Arterial Blood Gases", expanded=False):
                        cr_eos = st.number_input("Blood Eosinophil Count", min_value=0, max_value=2500, value=180, step=10, key=f"cr_eos_{pid}")
                        st.caption("Expected Clinical Range: 0 – 2500 cells/µL")
                        payload_buffer["Blood Eosinophil Count"] = {"raw_value": cr_eos, "unit": "cells/µL"}

                        cr_feno = st.number_input("Fractional Exhaled Nitric Oxide (FeNO)", min_value=5.0, max_value=150.0, value=22.0, step=1.0, format="%.1f", key=f"cr_feno_{pid}")
                        st.caption("Expected Clinical Range: 5 – 150 ppb")
                        payload_buffer["Fractional Exhaled Nitric Oxide (FeNO)"] = {"raw_value": cr_feno, "unit": "ppb"}

                        cr_spo2 = st.number_input("Resting Oxygen Saturation (SpO2)", min_value=65.0, max_value=100.0, value=float(active_pat.get("spo2", 96.0)), step=0.1, format="%.1f", key=f"cr_spo2_{pid}")
                        st.caption("Expected Clinical Range: 65.0 – 100.0 %")
                        payload_buffer["Resting Oxygen Saturation (SpO2)"] = {"raw_value": cr_spo2, "unit": "%"}

                        cr_pao2 = st.number_input("Arterial Oxygen Partial Pressure (PaO2)", min_value=40.0, max_value=110.0, value=85.0, step=1.0, format="%.1f", key=f"cr_pao2_{pid}")
                        st.caption("Expected Clinical Range: 40 – 110 mmHg")
                        payload_buffer["Arterial Oxygen Partial Pressure (PaO2)"] = {"raw_value": cr_pao2, "unit": "mmHg"}

                        cr_paco2 = st.number_input("Arterial Carbon Dioxide Partial Pressure (PaCO2)", min_value=25.0, max_value=90.0, value=40.0, step=1.0, format="%.1f", key=f"cr_paco2_{pid}")
                        st.caption("Expected Clinical Range: 25 – 90 mmHg")
                        payload_buffer["Arterial Carbon Dioxide Partial Pressure (PaCO2)"] = {"raw_value": cr_paco2, "unit": "mmHg"}

                        cr_ige = st.number_input("Serum Total IgE Level", min_value=2.0, max_value=3000.0, value=85.0, step=10.0, format="%.1f", key=f"cr_ige_{pid}")
                        st.caption("Expected Clinical Range: 2 – 3000 IU/mL")
                        payload_buffer["Serum Total IgE Level"] = {"raw_value": cr_ige, "unit": "IU/mL"}

                    with st.expander("📊 Functional Scores & Lifestyle Exposures", expanded=False):
                        cr_mmrc = st.selectbox("mMRC Dyspnea Scale Score", options=[0, 1, 2, 3, 4], index=1, key=f"cr_mmrc_{pid}")
                        st.caption("Clinical Scale: 0 (Dyspnea only with strenuous exercise) to 4 (Too breathless to leave house)")
                        payload_buffer["mMRC Dyspnea Scale Score"] = {"raw_value": cr_mmrc, "unit": "Score"}

                        cr_act = st.number_input("Asthma Control Test (ACT) Score", min_value=5, max_value=25, value=21, step=1, key=f"cr_act_{pid}")
                        st.caption("Expected Clinical Range: 5 – 25 Score")
                        payload_buffer["Asthma Control Test (ACT) Score"] = {"raw_value": cr_act, "unit": "Score"}

                        cr_cat = st.number_input("COPD Assessment Test (CAT) Score", min_value=0, max_value=40, value=8, step=1, key=f"cr_cat_{pid}")
                        st.caption("Expected Clinical Range: 0 – 40 Score")
                        payload_buffer["COPD Assessment Test (CAT) Score"] = {"raw_value": cr_cat, "unit": "Score"}

                        cr_exac = st.number_input("Annual Exacerbation Frequency", min_value=0, max_value=15, value=0, step=1, key=f"cr_exac_{pid}")
                        st.caption("Expected Clinical Range: 0 – 15 Episodes/year")
                        payload_buffer["Annual Exacerbation Frequency"] = {"raw_value": cr_exac, "unit": "Episodes/year"}

                        cr_tob = st.number_input("Lifetime Tobacco Exposure", min_value=0.0, max_value=120.0, value=float(active_pat.get("pack_years", 0.0)), step=1.0, format="%.1f", key=f"cr_tob_{pid}")
                        st.caption("Expected Clinical Range: 0 – 120 Pack-Years")
                        payload_buffer["Lifetime Tobacco Exposure"] = {"raw_value": cr_tob, "unit": "Pack-Years"}

                        cr_dust = st.radio("Occupational Dust/Fume Exposure", options=["0", "1"], index=0, horizontal=True, key=f"cr_dust_{pid}")
                        st.caption("Input Basis: 0 = Negative / No, 1 = Positive / Yes")
                        payload_buffer["Occupational Dust/Fume Exposure"] = {"raw_value": cr_dust, "unit": "None"}

                        cr_rhin = st.radio("Allergic Rhinitis Comorbidity", options=["0", "1"], index=0, horizontal=True, key=f"cr_rhin_{pid}")
                        st.caption("Input Basis: 0 = Negative / No, 1 = Positive / Yes")
                        payload_buffer["Allergic Rhinitis Comorbidity"] = {"raw_value": cr_rhin, "unit": "None"}

                        cr_cast = st.radio("Childhood Asthma History", options=["0", "1"], index=0, horizontal=True, key=f"cr_cast_{pid}")
                        st.caption("Input Basis: 0 = Negative / No, 1 = Positive / Yes")
                        payload_buffer["Childhood Asthma History"] = {"raw_value": cr_cast, "unit": "None"}

                        cr_bmi = st.number_input("Body Mass Index (BMI)", min_value=12.0, max_value=60.0, value=float(active_pat.get("bmi", 24.0)), step=0.1, format="%.1f", key=f"cr_bmi_{pid}")
                        st.caption("Expected Clinical Range: 12.0 – 60.0 kg/m²")
                        payload_buffer["Body Mass Index (BMI)"] = {"raw_value": cr_bmi, "unit": "kg/m²"}

                # ==========================================================
                # MODALITY 4: MENTAL HEALTH & NEUROLOGICAL DISORDERS
                # ==========================================================
                else:
                    with st.expander("🧠 Neuropsychiatric & Cognitive Assessment Batteries", expanded=True):
                        mh_phq9 = st.number_input("Patient Health Questionnaire-9 (PHQ-9)", min_value=0, max_value=27, value=int(active_pat.get("phq9", 4)), step=1, key=f"mh_phq9_{pid}")
                        st.caption("Clinical Scale Range: 0 – 27 Score")
                        payload_buffer["Patient Health Questionnaire-9 (PHQ-9)"] = {"raw_value": mh_phq9, "unit": "Score"}

                        mh_gad7 = st.number_input("Generalized Anxiety Disorder-7 (GAD-7)", min_value=0, max_value=21, value=int(active_pat.get("gad7", 3)), step=1, key=f"mh_gad7_{pid}")
                        st.caption("Clinical Scale Range: 0 – 21 Score")
                        payload_buffer["Generalized Anxiety Disorder-7 (GAD-7)"] = {"raw_value": mh_gad7, "unit": "Score"}

                        mh_mmse = st.number_input("Mini-Mental State Examination (MMSE)", min_value=0, max_value=30, value=28, step=1, key=f"mh_mmse_{pid}")
                        st.caption("Clinical Scale Range: 0 – 30 Score")
                        payload_buffer["Mini-Mental State Examination (MMSE)"] = {"raw_value": mh_mmse, "unit": "Score"}

                        mh_moca = st.number_input("Montreal Cognitive Assessment (MoCA)", min_value=0, max_value=30, value=27, step=1, key=f"mh_moca_{pid}")
                        st.caption("Clinical Scale Range: 0 – 30 Score")
                        payload_buffer["Montreal Cognitive Assessment (MoCA)"] = {"raw_value": mh_moca, "unit": "Score"}

                        mh_hamd = st.number_input("Hamilton Depression Rating Scale (HAM-D)", min_value=0, max_value=52, value=6, step=1, key=f"mh_hamd_{pid}")
                        st.caption("Clinical Scale Range: 0 – 52 Score")
                        payload_buffer["Hamilton Depression Rating Scale (HAM-D)"] = {"raw_value": mh_hamd, "unit": "Score"}

                        mh_updrs = st.number_input("UPDRS Part III (Motor Examination)", min_value=0, max_value=132, value=8, step=1, key=f"mh_updrs_{pid}")
                        st.caption("Clinical Scale Range: 0 – 132 Score")
                        payload_buffer["UPDRS Part III (Motor Examination)"] = {"raw_value": mh_updrs, "unit": "Score"}

                        mh_faq = st.number_input("Functional Activities Questionnaire (FAQ)", min_value=0, max_value=30, value=2, step=1, key=f"mh_faq_{pid}")
                        st.caption("Clinical Scale Range: 0 – 30 Score")
                        payload_buffer["Functional Activities Questionnaire (FAQ)"] = {"raw_value": mh_faq, "unit": "Score"}

                        mh_trem = st.selectbox("Tremor Rating Scale Score", options=[0, 1, 2, 3, 4], index=0, key=f"mh_trem_{pid}")
                        st.caption("Clinical Scale: 0 (None) to 4 (Severe amplitude / marked impairment)")
                        payload_buffer["Tremor Rating Scale Score"] = {"raw_value": mh_trem, "unit": "Score"}

                    with st.expander("💤 Sleep Physiology & Paroxysmal Events", expanded=False):
                        mh_sleep = st.number_input("Daily Sleep Duration", min_value=1.0, max_value=16.0, value=float(active_pat.get("sleep_hrs", 7.5)), step=0.5, format="%.1f", key=f"mh_sleep_{pid}")
                        st.caption("Expected Clinical Range: 1.0 – 16.0 Hours")
                        payload_buffer["Daily Sleep Duration"] = {"raw_value": mh_sleep, "unit": "Hours"}

                        mh_psqi = st.number_input("Pittsburgh Sleep Quality Index (PSQI)", min_value=0, max_value=21, value=4, step=1, key=f"mh_psqi_{pid}")
                        st.caption("Clinical Scale Range: 0 – 21 Score")
                        payload_buffer["Pittsburgh Sleep Quality Index (PSQI)"] = {"raw_value": mh_psqi, "unit": "Score"}

                        mh_seiz = st.number_input("Seizure Frequency", min_value=0, max_value=100, value=0, step=1, key=f"mh_seiz_{pid}")
                        st.caption("Expected Clinical Range: 0 – 100 Episodes/month")
                        payload_buffer["Seizure Frequency"] = {"raw_value": mh_seiz, "unit": "Episodes/month"}

                    with st.expander("🧪 Endocrine, Autonomic & Neuro-Nutritional Panel", expanded=False):
                        mh_hrv = st.number_input("Heart Rate Variability (SDNN)", min_value=5.0, max_value=250.0, value=65.0, step=1.0, format="%.1f", key=f"mh_hrv_{pid}")
                        st.caption("Expected Clinical Range: 5.0 – 250.0 ms")
                        payload_buffer["Heart Rate Variability (SDNN)"] = {"raw_value": mh_hrv, "unit": "ms"}

                        mh_cort = st.number_input("8 AM Serum Cortisol", min_value=1.0, max_value=45.0, value=14.5, step=0.5, format="%.1f", key=f"mh_cort_{pid}")
                        st.caption("Expected Clinical Range: 1.0 – 45.0 µg/dL")
                        payload_buffer["8 AM Serum Cortisol"] = {"raw_value": mh_cort, "unit": "µg/dL"}

                        mh_b12 = st.number_input("Serum Vitamin B12", min_value=50.0, max_value=2000.0, value=450.0, step=10.0, format="%.1f", key=f"mh_b12_{pid}")
                        st.caption("Expected Clinical Range: 50 – 2000 pg/mL")
                        payload_buffer["Serum Vitamin B12"] = {"raw_value": mh_b12, "unit": "pg/mL"}

                        mh_fol = st.number_input("Serum Folate", min_value=1.0, max_value=25.0, value=7.5, step=0.1, format="%.1f", key=f"mh_fol_{pid}")
                        st.caption("Expected Clinical Range: 1.0 – 25.0 ng/mL")
                        payload_buffer["Serum Folate"] = {"raw_value": mh_fol, "unit": "ng/mL"}

                        mh_tsh = st.number_input("Thyroid Stimulating Hormone (TSH)", min_value=0.01, max_value=100.0, value=1.85, step=0.05, format="%.2f", key=f"mh_tsh_{pid}")
                        st.caption("Expected Clinical Range: 0.01 – 100.00 mIU/L")
                        payload_buffer["Thyroid Stimulating Hormone (TSH)"] = {"raw_value": mh_tsh, "unit": "mIU/L"}

                    with st.expander("🧬 Neurological History & Lineage", expanded=False):
                        mh_tbi = st.radio("History of Traumatic Brain Injury (TBI)", options=["0", "1"], index=0, horizontal=True, key=f"mh_tbi_{pid}")
                        st.caption("Input Basis: 0 = Negative / No, 1 = Positive / Yes")
                        payload_buffer["History of Traumatic Brain Injury (TBI)"] = {"raw_value": mh_tbi, "unit": "None"}

                        mh_alc = st.radio("Lifetime History of Alcohol/Substance Abuse", options=["0", "1"], index=0, horizontal=True, key=f"mh_alc_{pid}")
                        st.caption("Input Basis: 0 = Negative / No, 1 = Positive / Yes")
                        payload_buffer["Lifetime History of Alcohol/Substance Abuse"] = {"raw_value": mh_alc, "unit": "None"}

                        mh_fam = st.radio("Family History of Neurological/Psychiatric Illness", options=["0", "1"], index=1 if has_neuro_history else 0, horizontal=True, key=f"mh_fam_{pid}")
                        st.caption(registry_caption)
                        payload_buffer["Family History of Neurological/Psychiatric Illness"] = {"raw_value": mh_fam, "unit": "None"}

                        mh_age = st.number_input("Age", min_value=18, max_value=90, value=int(active_pat.get("age", 58)), step=1, key=f"mh_age_{pid}")
                        st.caption("Expected Clinical Range: 18 – 90 Years")
                        payload_buffer["Age"] = {"raw_value": mh_age, "unit": "Years"}

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                
                submit_inference = st.form_submit_button("🧠 Run AI Diagnostic Inference", type="primary", use_container_width=True)

                if submit_inference:
                    enc_id = f"ENC-{uuid.uuid4().hex[:8].upper()}"
                    submission_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                    cdss_package = {
                        "encounter_id": enc_id,
                        "patient_id": active_pat["id"],
                        "modality": modality_schema_name,
                        "submitted_at_utc": submission_timestamp,
                        "biomarker_payload": payload_buffer
                    }

                    st.session_state["cdss_inference_payload"] = cdss_package
                    st.session_state["ai_inference_completed"] = True
                    st.rerun()

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # ======================================================================
        # LOWER CONTAINER: FULL-WIDTH DIAGNOSTIC VISUALIZER (VERTICAL STACK)
        # ======================================================================
        with st.container(border=True):
            st.markdown(
                """
                <div style="margin-bottom: 12px;">
                    <h3 style="margin: 0; font-size: 1.35rem; font-weight: 700;">Diagnostic Risk Assessment</h3>
                    <p style="margin: 2px 0 0 0; font-size: 0.9rem; color: #64748b;">Multi-factorial risk stratification and feature attribution.</p>
                </div>
                """, unsafe_allow_html=True
            )
            
            # Strict Execution Gate
            if not st.session_state.get("ai_inference_completed") or not st.session_state.get("cdss_inference_payload"):
                st.markdown(
                    """
                    <div style="height:320px; display:flex; align-items:center; justify-content:center; border: 1px dashed #94a3b8; border-radius: 8px; color:#64748b; text-align:center; padding: 20px;">
                        <div>
                            <div style="font-size: 2.2rem; margin-bottom: 8px;">🔬</div>
                            <b>No inference model computed</b><br>
                            <span style="font-size: 0.85rem;">Submit biomarker vectors from the clinical parameter form to execute CDSS diagnostics.</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True
                )
            else:
                payload = st.session_state["cdss_inference_payload"]
                biomarkers = payload.get("biomarker_payload", {})
                
                # Serialized JSON Telemetry View
                with st.expander("📦 Serialized Gateway Contract Output (`POST /api/models/predict`)", expanded=False):
                    st.caption("The exact JSON payload constructed and validated across physiological bounds.")
                    st.json(payload, expanded=True)

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                
                # Dynamic Risk Evaluator Logic
                dynamic_drivers = []
                overall_risk_points = 15.0  # Baseline population variance

                for k, v in biomarkers.items():
                    try: val = float(v["raw_value"])
                    except (ValueError, TypeError): val = 1.0 if str(v["raw_value"]) in ["1", "Male", "Yes", "Present"] else 0.0
                    
                    severity = "Low"
                    impact = 0.0
                    
                    if "Systolic Blood Pressure" in k and val >= 140: severity, impact = "High", 28.0 + (val-140)*0.4
                    elif "HbA1c" in k and val >= 6.5: severity, impact = "High", 32.0 + (val-6.5)*10
                    elif "Oxygen Saturation" in k and val < 90: severity, impact = "High", 35.0 + (90-val)*2
                    elif "PHQ-9" in k and val >= 15: severity, impact = "High", 28.0 + (val-15)*1.5
                    elif "Total Cholesterol" in k and val >= 240: severity, impact = "Moderate", 16.0
                    elif "FEV1/FVC" in k and val < 70: severity, impact = "High", 22.0
                    elif "Smoking" in k and val >= 20: severity, impact = "High", 18.0
                    elif "Family History" in k and val == 1.0: severity, impact = "Moderate", 14.0
                    elif "Fasting Plasma Glucose" in k and val >= 126: severity, impact = "High", 25.0
                    elif "Resting Heart Rate" in k and (val > 100 or val < 50): severity, impact = "Moderate", 12.0
                    
                    if severity != "Low":
                        unit_label = f" {v['unit']}" if v['unit'] != "None" else ""
                        dynamic_drivers.append({"feature": f"{k} ({val:.1f}{unit_label})", "impact": min(impact, 45.0), "severity": severity})
                        overall_risk_points += impact
                        
                dynamic_drivers = sorted(dynamic_drivers, key=lambda x: x["impact"], reverse=True)[:5]
                
                if not dynamic_drivers:
                    dynamic_drivers = [{"feature": "All Ingested Biomarkers Within Healthy Target", "impact": 2.5, "severity": "Low"}]
                    overall_risk_points = 8.5
                    
                score = min(round(overall_risk_points, 1), 98.5)
                tier = "High Risk" if score >= 70 else ("Moderate Risk" if score >= 40 else "Low Risk")
                tier_color = "#ef4444" if score >= 70 else ("#f59e0b" if score >= 40 else "#10b981")
                primary_cond = payload["modality"].split("(")[0].strip()

                st.markdown(f"<div style='text-align: center; font-size: 0.88rem; font-weight: 600; padding: 6px 12px; background: rgba(239, 68, 68, 0.08); border-radius: 8px; color: {tier_color}; margin-bottom: 16px;'>Primary Indication: {primary_cond} Evaluation</div>", unsafe_allow_html=True)
                
                # Plotly Semicircular Gauge (Full Width / No Columns)
                fig_gauge = go.Figure(
                    go.Indicator(
                        mode="gauge+number",
                        value=score,
                        number={"suffix": "%", "font": {"size": 42, "color": tier_color}},
                        title={
                            "text": f"<b style='color:{tier_color}; font-size:17px;'>{tier.upper()} DETECTED</b><br><span style='font-size:12px; color:#64748b;'>Confidence: 94.2%</span>",
                            "font": {"size": 15},
                        },
                        gauge={
                            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8", "dtick": 20},
                            "bar": {"color": tier_color, "thickness": 0.3},
                            "bgcolor": "rgba(0,0,0,0)",
                            "borderwidth": 0,
                            "steps": [
                                {"range": [0, 40], "color": "rgba(16, 185, 129, 0.15)"},
                                {"range": [40, 70], "color": "rgba(245, 158, 11, 0.15)"},
                                {"range": [70, 100], "color": "rgba(239, 68, 68, 0.18)"},
                            ],
                            "threshold": {
                                "line": {"color": "#b91c1c", "width": 3},
                                "thickness": 0.75,
                                "value": score,
                            },
                        },
                    )
                )
                fig_gauge.update_layout(
                    height=260, margin=dict(l=20, r=20, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#0f172a" if st.session_state.get("theme_mode") == "light" else "#E5E5E5")
                )
                st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

                st.markdown("##### Key Contributors to Clinical Risk")
                features = [d["feature"] for d in reversed(dynamic_drivers)]
                impacts = [d["impact"] for d in reversed(dynamic_drivers)]
                colors = ["#ef4444" if d["severity"] == "High" else "#f59e0b" if d["severity"] == "Moderate" else "#10b981" for d in reversed(dynamic_drivers)]
                
                max_impact = max(impacts) if impacts else 0.0
                fig_bar = go.Figure(
                    go.Bar(
                        x=impacts, y=features, orientation="h",
                        marker=dict(color=colors, line=dict(color="rgba(0, 0, 0, 0)", width=0), cornerradius=6),
                        text=[f"+{val:.1f}%" for val in impacts], textposition="outside",
                        textfont=dict(size=12), cliponaxis=False,
                    )
                )
                fig_bar.update_layout(
                    height=260, margin=dict(l=10, r=40, t=10, b=10),
                    xaxis=dict(showgrid=True, gridcolor="rgba(148, 163, 184, 0.2)", zeroline=False, showticklabels=True, range=[0, max(max_impact * 1.28, 10.0)]),
                    yaxis=dict(showgrid=False, zeroline=False, autorange=True, tickfont=dict(size=12)),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#0f172a" if st.session_state.get("theme_mode") == "light" else "#E5E5E5")
                )
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})