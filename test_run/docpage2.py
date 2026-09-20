import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ==============================================================================
# 1. PAGE SETUP & DATA BOOTSTRAP
# ==============================================================================
st.set_page_config(layout="wide", page_title="Lucerna Medica | Clinician Workspace")

user_avatar_url = "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=150&q=80"

doc = {
    "name": "Dr. Maria A. Velasco", "suffix": "MD, PhD", "role": "CLINICIAN",
    "prc": "PRC 8839210", "affiliation": "Lucerna Central Clinic", "specialty": "Cardiology"
}

if "theme_mode" not in st.session_state: st.session_state.theme_mode = "light"
if "active_patient" not in st.session_state: st.session_state.active_patient = None
if "cdss_locked" not in st.session_state: st.session_state.cdss_locked = False
if "cdss_inference_run" not in st.session_state: st.session_state.cdss_inference_run = False

if "today_queue" not in st.session_state:
    st.session_state.today_queue = [
        {"queue_no": "Q-01", "time_in": "08:15 AM", "id": "PAT-9912", "name": "Alvarez, Carlos T.", "urgency": "🔴 Critical", "complaint": "Severe chest pain radiating to left arm."},
        {"queue_no": "Q-02", "time_in": "08:42 AM", "id": "PAT-4421", "name": "Santos, Sofia M.", "urgency": "🟡 Priority", "complaint": "Palpitations and dizziness upon standing."},
        {"queue_no": "Q-03", "time_in": "09:05 AM", "id": "PAT-1102", "name": "Mason, Justin L.", "urgency": "🟢 Routine", "complaint": "Post-op medication adjustment."}
    ]

master_patients = [
    {"id": "PAT-9912", "name": "Alvarez, Carlos T.", "age": 58, "sex": "Male", "bmi": 29.4, "latest_bp": "165/95", "resting_hr": 92, "total_chol": 245, "last_ecg": "2026-09-13", "risk_flag": "High Risk Flagged", "fam_history": ["CVD (Father)", "Hypertension (Mother)"]},
    {"id": "PAT-4421", "name": "Santos, Sofia M.", "age": 42, "sex": "Female", "bmi": 24.1, "latest_bp": "118/76", "resting_hr": 105, "total_chol": 190, "last_ecg": "2026-08-20", "risk_flag": "Awaiting Review", "fam_history": ["Type 2 Diabetes (Mother)"]},
    {"id": "PAT-1102", "name": "Mason, Justin L.", "age": 65, "sex": "Male", "bmi": 26.8, "latest_bp": "125/80", "resting_hr": 68, "total_chol": 175, "last_ecg": "2026-09-01", "risk_flag": "Stable", "fam_history": []},
]

# ==============================================================================
# 2. MASTER DUAL-THEME ENGINE (UNIVERSAL ELEVATED CARDS FIX)
# ==============================================================================
if st.session_state.theme_mode == "dark":
    theme_css = """
    .stApp { background-color: #091540 !important; color: #E5E5E5 !important; }
    h1, h2, h3, h4, h5, h6, p, span, label, legend { color: #E5E5E5 !important; }
    
    /* Target ALL Containers by both legacy testid, modern stContainer, and content */
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stContainer"],
    div[data-testid="stContainer"],
    div[data-testid="stVerticalBlockBorderWrapper"],
    fieldset[data-testid="stFieldset"],
    div:has(> div > [data-testid="stPlotlyChart"]),
    div:has(> div > [data-testid="stDataFrame"]),
    div:has(> div > [data-testid*="VegaLite"]),
    div:has(> div > [data-testid="stLineChart"]),
    div[style*="background-color: #ffffff"], 
    div[style*="background-color: rgb(255, 255, 255)"],
    .metric-card {
        background-color: #232F72 !important;
        background: #232F72 !important;
        border: 1px solid #2F578A !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important;
        padding: 20px 24px !important;
        margin-bottom: 18px !important;
    }
    
    /* Nested Column Mini-Cards */
    [data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="column"] [data-testid="stContainer"],
    [data-testid="column"] fieldset[data-testid="stFieldset"] {
        background-color: #2F578A !important;
        background: #2F578A !important;
        border: 1px solid rgba(229, 229, 229, 0.25) !important;
    }

    /* Prevent double-box nesting and padding overflow on inner widgets */
    [data-testid="stVerticalBlockBorderWrapper"] div:has(> div > [data-testid="stDataFrame"]),
    fieldset[data-testid="stFieldset"] div:has(> div > [data-testid="stDataFrame"]),
    [data-testid="stVerticalBlockBorderWrapper"] div:has(> div > [data-testid="stPlotlyChart"]),
    fieldset[data-testid="stFieldset"] div:has(> div > [data-testid="stPlotlyChart"]) {
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin-bottom: 0 !important;
        background: transparent !important;
    }

    [data-baseweb="base-input"], [data-baseweb="select"] > div { background-color: #091540 !important; border: 1px solid #2F578A !important; border-radius: 8px !important; }
    [data-baseweb="base-input"] input { color: #E5E5E5 !important; }
    [data-baseweb="tab-list"] { border-bottom: 2px solid #2F578A !important; }
    """
else:
    theme_css = """
    .stApp { background-color: #f1f5f9 !important; color: #0f172a !important; }
    h1, h2, h3, h4, h5, h6, p, span, label, legend { color: #0f172a !important; }
    
    /* UNIVERSAL SOLID WHITE ON ALL CONTAINER WRAPPERS */
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stContainer"],
    div[data-testid="stContainer"],
    div[data-testid="stVerticalBlockBorderWrapper"],
    fieldset[data-testid="stFieldset"],
    div:has(> div > [data-testid="stPlotlyChart"]),
    div:has(> div > [data-testid="stDataFrame"]),
    div:has(> div > [data-testid*="VegaLite"]),
    div:has(> div > [data-testid="stLineChart"]),
    div[style*="background-color: #ffffff"],
    div[style*="background-color: rgb(255, 255, 255)"],
    .metric-card {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border: 1px solid #e0e4e8 !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05) !important;
        padding: 20px 24px !important;
        margin-bottom: 18px !important;
    }
    
    /* Clear internal container wrappers to avoid double background borders */
    [data-testid="stVerticalBlockBorderWrapper"] > div,
    [data-testid="stContainer"] > div {
        background: transparent !important;
        border: none !important;
    }

    /* Prevent double-box nesting and padding overflow on inner widgets */
    [data-testid="stVerticalBlockBorderWrapper"] div:has(> div > [data-testid="stDataFrame"]),
    fieldset[data-testid="stFieldset"] div:has(> div > [data-testid="stDataFrame"]),
    [data-testid="stVerticalBlockBorderWrapper"] div:has(> div > [data-testid="stPlotlyChart"]),
    fieldset[data-testid="stFieldset"] div:has(> div > [data-testid="stPlotlyChart"]) {
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin-bottom: 0 !important;
        background: transparent !important;
    }

    [data-baseweb="base-input"], [data-baseweb="select"] > div { background-color: #f8fafc !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important; }
    [data-baseweb="base-input"] input { color: #0f172a !important; }
    [data-baseweb="tab-list"] { border-bottom: 2px solid #e2e8f0 !important; }
    """

st.markdown(f"""
    <style>
    {theme_css}
    [data-testid*="stInputInstructions"] {{ display: none !important; }}
    .block-container {{ padding: 1.5rem !important; max-width: 96% !important; }}
    [data-baseweb="tab-list"] {{ display: flex !important; width: 100% !important; gap: 14px !important; }}
    button[data-baseweb="tab"], [data-testid="stTab"] {{ flex: 1 1 0 !important; height: 60px !important; font-size: 1.45rem !important; font-weight: 800 !important; }}
    [aria-selected="true"] * {{ color: #007979 !important; }}
    [data-baseweb="tab-highlight"] {{ background-color: #007979 !important; height: 4px !important; }}
    button[data-testid="baseButton-primary"] {{ background-color: #007979 !important; color: #ffffff !important; border-radius: 8px !important; font-weight: 700 !important; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. HELPER FUNCTIONS
# ==============================================================================
def start_consult(patient):
    st.session_state.active_patient = patient
    st.session_state.cdss_locked = False
    st.session_state.cdss_inference_run = False
    st.toast(f"Consultation initiated for {patient['name']}", icon="🩺")

# ==============================================================================
# 4. HEADER (BORDERLESS)
# ==============================================================================
_, col_main, _ = st.columns([5, 90, 5], gap="small")

with col_main:
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
                if st.button("Dark Mode", use_container_width=True):
                    st.session_state.theme_mode = "dark"; st.rerun()
                if st.button("Light Mode", use_container_width=True):
                    st.session_state.theme_mode = "light"; st.rerun()

    # ==============================================================================
    # 5. TABS
    # ==============================================================================
    tab_overview, tab_queue, tab_cdss = st.tabs(["Overview Dashboard", "Patients & Triage", "AI Diagnostics & CDSS"])

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

            # 4 Metric Summary Cards
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
                    <div style="font-size: 2rem; font-weight: 800; line-height: 1; color: #ef4444;">3 Critical 🔴</div>
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
                fig.update_layout(height=200, margin=dict(l=15, r=15, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
        with triage_col:
            with st.container(border=True):
                st.markdown("#### Live Waiting Room Acuity")
                # Removed height=230 so the table hugs its 3 rows with no overflow
                st.dataframe(
                    pd.DataFrame(st.session_state.today_queue)[["queue_no", "name", "time_in", "urgency"]],
                    use_container_width=True, hide_index=True,
                    column_config={"queue_no": "Queue", "name": "Patient", "time_in": "Time In", "urgency": "Acuity Status"}
                )

    # --------------------------------------------------------------------------
    # TAB 2: PATIENTS & TRIAGE QUEUE
    # --------------------------------------------------------------------------
    with tab_queue:
        st.write("")
        with st.container(border=True):
            st.markdown("### Today's Triage Queue")
            for p in st.session_state.today_queue:
                c1, c2, c3, c4 = st.columns([1, 2, 4, 2], vertical_alignment="center")
                c1.write(f"**{p['queue_no']}**")
                c2.write(p['urgency'])
                c3.write(f"{p['name']} - {p['complaint']}")
                if c4.button("🩺 Start Consult", key=f"btn_{p['id']}", use_container_width=True):
                    record = next((pat for pat in master_patients if pat["id"] == p["id"]), None)
                    if record: start_consult(record)
                st.divider()

        with st.container(border=True):
            st.markdown("### Master Patient Directory")
            selected_pat = st.dataframe(pd.DataFrame(master_patients), use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun")

    # --------------------------------------------------------------------------
    # TAB 3: AI DIAGNOSTICS & CDSS
    # --------------------------------------------------------------------------
    with tab_cdss:
        st.write("")
        active = st.session_state.active_patient
        
        if not active:
            st.info("👈 Please select a patient from the 'Patients & Triage' tab to start a consultation.")
        else:
            with st.container(border=True):
                st.markdown(f"### Consultation: {active['name']} (`{active['id']}`)")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Age/Sex", f"{active['age']} / {active['sex']}")
                col2.metric("Latest BP", active['latest_bp'])
                col3.metric("Resting HR", f"{active['resting_hr']} bpm")
                col4.metric("Total Chol", active['total_chol'])

            st.write("")
            grid_col, ai_col = st.columns([1.2, 1], gap="large")
            with grid_col:
                with st.container(border=True):
                    st.markdown("### Disease Parameters (CVD Modality)")
                    bp = st.text_input("Systolic / Diastolic BP (mmHg)", value=active['latest_bp'], disabled=st.session_state.cdss_locked)
                    chest_pain = st.selectbox("Chest Pain Classification", ["Asymptomatic", "Typical Angina"], disabled=st.session_state.cdss_locked)
                    
                    if st.button("🧠 Run AI Inference", type="primary", use_container_width=True, disabled=st.session_state.cdss_locked):
                        st.session_state.cdss_inference_run = True
                        st.rerun()

            with ai_col:
                with st.container(border=True):
                    st.markdown("### Diagnostic AI Analytics")
                    if not st.session_state.cdss_inference_run:
                        st.caption("Awaiting inference trigger...")
                    else:
                        st.markdown("<h2 style='color:#ef4444; margin:0;'>82% High Risk</h2>", unsafe_allow_html=True)
                        st.markdown("**Confidence:** `94.2%` | **Benchmark:** `98.1%`")
                        st.markdown("1. Typical Angina Classification\n2. Elevated SBP")

            st.write("")
            with st.container(border=True):
                st.markdown("### Clinical Decision & Verification")
                decision = st.selectbox("Status", ["Agree with AI", "Modify AI", "Reject AI"], disabled=st.session_state.cdss_locked)
                notes = st.text_area("Treatment Directives", disabled=st.session_state.cdss_locked)
                
                if st.button("🔒 Lock & Commit Diagnosis", type="primary", disabled=st.session_state.cdss_locked):
                    if notes:
                        st.session_state.cdss_locked = True
                        st.success("Assessment locked to electronic health record.")
                        st.rerun()
                    else:
                        st.error("Treatment notes required.")