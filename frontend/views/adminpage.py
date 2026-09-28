import sys
import os

# 1. Add the parent 'frontend' folder to the Python path so 'views' is recognized
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. Standard imports
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime

# 3. Import the shared UI template (Relative import handles subfolder execution)
try:
    from styles import basetab_layout_, render_top_navbar, render_clinician_governance_panel, render_patient_governance_panel, render_admin_governance_panel
except ImportError:
    from views.styles import basetab_layout_, render_top_navbar, render_clinician_governance_panel, render_patient_governance_panel, render_admin_governance_panel

# ==============================================================================
# PAGE CONFIGURATION & THEME INITIALIZATION
# ==============================================================================
# This block must only appear exactly once
st.set_page_config(layout="wide", page_title="HEART | Admin Portal")

# Inject the shared custom UI tab & button styling
basetab_layout_()

# ==============================================================================
# CALLBACKS, HELPERS & REUSABLE COMPONENTS
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
    return bool(re.match(r"^\d{4}-\d{3}-\d{4}$", text.strip()))

def is_valid_gmail(text: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", text.strip()))

def is_valid_admin_email(text: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", text.strip()))


# ==============================================================================
# GLOBALS & DIRECTORIES INITIALIZATION
# ==============================================================================
SPECIALIZATION_OPTIONS = ["General Physician", "Internal Medicine", "Cardiology", "Pulmonology", "Psychiatry"]
SUFFIX_OPTIONS = ["None", "MD", "PhD", "DO", "MD, PhD", "Jr.", "Sr.", "III"]
RELATION_OPTIONS = ["Mother", "Father", "Spouse", "Son", "Daughter", "Brother", "Sister", "Other"]

for key in ["doc_first_name", "doc_middle_name", "doc_last_name", "doc_address", "doc_affiliation", "doc_prc", "doc_email", "doc_contact", "em_name", "em_contact"]:
    if key not in st.session_state: st.session_state[key] = ""

if "form_success" not in st.session_state: st.session_state.form_success = None

# Initialize empty tables for live database population
if "doctor_directory" not in st.session_state: st.session_state.doctor_directory = []
if "doctor_audit_logs" not in st.session_state: st.session_state.doctor_audit_logs = []
if "employee_directory" not in st.session_state: st.session_state.employee_directory = []
if "patient_directory" not in st.session_state: st.session_state.patient_directory = []
if "patient_audit_logs" not in st.session_state: st.session_state.patient_audit_logs = []

# ==============================================================================
# LIVE AUTHENTICATED USER CONTEXT
# ==============================================================================
profile = st.session_state.get("user_profile", {})
user_name = f"{profile.get('first_name', 'System')} {profile.get('last_name', 'Admin')}".strip()
user_role = st.session_state.get("user_role", "ADMIN")
user_email = profile.get("email", "admin.system@lucernamedica.com")


_, col_main, _ = st.columns([5, 90, 5], gap="small")


with col_main:
    # --- RENDER UNIFIED TOP NAVIGATION ---
    render_top_navbar(
        user_name=user_name, 
        user_role=user_role, 
        user_email=user_email,
        badge_label="Admin Access",
        badge_color="#0ea5e9"
    )
    tab_Overview, tab_form, tab_patient, tab_Admin = st.tabs(["Overview", "Doctor Management", "Patient Management", "Admin accounts"])

    # --------------------------------------------------------------------------
    # TAB 1: METRIC DASHBOARD & TELEMETRY
    # --------------------------------------------------------------------------
    with tab_Overview:
        st.write("")
        docs = st.session_state.doctor_directory
        pats = st.session_state.patient_directory

        c_admin = max(len(st.session_state.employee_directory), 1)
        c_doc = len(docs)
        c_pat = len(pats)
        total_accounts = c_admin + c_doc + c_pat

        pct_doc = (c_doc / total_accounts) * 100 if total_accounts else 0
        pct_pat = (c_pat / total_accounts) * 100 if total_accounts else 0
        pct_adm = (c_admin / total_accounts) * 100 if total_accounts else 0

        doc_ver = sum(1 for d in docs if d.get("is_verified", False))
        pat_hipaa = sum(1 for p in pats if p.get("hipaa_consent", False))
        pat_hipaa_pct = int((pat_hipaa / c_pat) * 100) if c_pat > 0 else 0

        pending_ver = sum(1 for p in pats if not p.get("is_verified", False))
        locked_acc = sum(1 for d in docs if d.get("is_locked", False)) + sum(1 for p in pats if p.get("is_locked", False))
        active_sessions = total_accounts - locked_acc
        
        doc_mfa = sum(1 for d in docs if d.get("mfa_enrolled", False))
        mfa_pct = int((doc_mfa / c_doc) * 100) if c_doc > 0 else 0

        with st.container(border=True):
            st.markdown("""
            <div style="margin-bottom: 22px;">
                <h3 style="margin: 0; font-size: 1.45rem; font-weight: 700; letter-spacing: -0.3px;">System Telemetry & Identity Metrics</h3>
                <p style="margin: 5px 0 16px 0; font-size: 0.95rem;">Live platform oversight, role distribution, and compliance monitoring across Lucerna Medica.</p>
                <div style="height: 1px; width: 100%; background-color: rgba(148, 163, 184, 0.2);"></div>
            </div>
            """, unsafe_allow_html=True)

            hero_col, grid_col = st.columns([1.3, 2], gap="medium")
            with hero_col:
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 22px 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.02); height: 295px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-size: 0.85rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; color:#0f172a;">Master Directory</span>
                            <span style="background: #e6f4f1; color: #007979; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 20px;">LIVE REGISTRY</span>
                        </div>
                        <div style="font-size: 4.8rem; font-weight: 800; line-height: 1; letter-spacing: -1.5px; margin: 4px 0; color:#0f172a;">{total_accounts}</div>
                        <div style="font-size: 1.1rem; font-weight: 600; color:#0f172a;">Total Provisioned Identities</div>
                    </div>
                    <div>
                        <div style="display: flex; height: 10px; border-radius: 6px; overflow: hidden; background: #e2e8f0; margin-bottom: 10px;">
                            <div style="width: {pct_doc:.1f}%; background-color: #007979;" title="Doctors: {c_doc}"></div>
                            <div style="width: {pct_pat:.1f}%; background-color: #0284c7;" title="Patients: {c_pat}"></div>
                            <div style="width: {pct_adm:.1f}%; background-color: #64748b;" title="Admins: {c_admin}"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600; color:#0f172a;">
                            <span style="display: flex; align-items: center; gap: 5px;"><span style="height: 8px; width: 8px; border-radius: 50%; background: #007979;"></span> {c_doc} Clinicians</span>
                            <span style="display: flex; align-items: center; gap: 5px;"><span style="height: 8px; width: 8px; border-radius: 50%; background: #0284c7;"></span> {c_pat} Patients</span>
                            <span style="display: flex; align-items: center; gap: 5px;"><span style="height: 8px; width: 8px; border-radius: 50%; background: #64748b;"></span> {c_admin} Admin</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with grid_col:
                sub_r1_c1, sub_r1_c2 = st.columns(2, gap="medium")
                with sub_r1_c1:
                    st.markdown(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="font-size: 0.95rem; font-weight: 600; color:#0f172a;">Doctors</div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1; color:#0f172a;">{c_doc}</div>
                        <div style="font-size: 0.85rem; font-weight: 600; color: #007979;">🟢 {doc_ver}/{c_doc if c_doc else 1} Verified PRC Licenses</div>
                    </div>
                    """, unsafe_allow_html=True)
                with sub_r1_c2:
                    hipaa_badge_color = "#10b981" if pat_hipaa_pct >= 80 else "#f59e0b"
                    st.markdown(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="font-size: 0.95rem; font-weight: 600; color:#0f172a;">Patients</div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1; color:#0f172a;">{c_pat}</div>
                        <div style="font-size: 0.85rem; font-weight: 600; color: {hipaa_badge_color};">📝 {pat_hipaa_pct}% Consented ({pat_hipaa}/{c_pat if c_pat else 1})</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

                sub_r2_c1, sub_r2_c2 = st.columns(2, gap="medium")
                with sub_r2_c1:
                    st.markdown(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="font-size: 0.95rem; font-weight: 600; color:#0f172a;">System Admins</div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1; color:#0f172a;">{c_admin}</div>
                        <div style="font-size: 0.85rem; font-weight: 600; color: #0284c7;">🛡️ Full Audit Privileges</div>
                    </div>
                    """, unsafe_allow_html=True)
                with sub_r2_c2:
                    st.markdown(f"""
                    <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); height: 138px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div style="font-size: 0.95rem; font-weight: 600; color:#0f172a;">Active Sessions</div>
                        <div style="font-size: 2.5rem; font-weight: 800; line-height: 1; color:#0f172a;">{active_sessions}</div>
                        <div style="font-size: 0.85rem; font-weight: 600; color: #10b981;">⚡ Valid Token Versions</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

            gov_c1, gov_c2, gov_c3, gov_c4 = st.columns(4, gap="medium")
            with gov_c1:
                pend_color = "#f59e0b" if pending_ver > 0 else "#10b981"
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="font-size: 0.88rem; font-weight: 600; color:#0f172a;">Pending Queue</div>
                    <div style="font-size: 2rem; font-weight: 800; line-height: 1; color:#0f172a;">{pending_ver}</div>
                    <div style="font-size: 0.8rem; font-weight: 600; color: {pend_color};">⏳ Awaiting OTP/Verification</div>
                </div>
                """, unsafe_allow_html=True)

            with gov_c2:
                lock_color = "#ef4444" if locked_acc > 0 else "#10b981"
                lock_text = f"⚠️ {locked_acc} Account Locked" if locked_acc > 0 else "✔ 0 Brute-Force Flags"
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="font-size: 0.88rem; font-weight: 600; color:#0f172a;">Account Lockouts</div>
                    <div style="font-size: 2rem; font-weight: 800; line-height: 1; color:#0f172a;">{locked_acc}</div>
                    <div style="font-size: 0.8rem; font-weight: 600; color: {lock_color};">{lock_text}</div>
                </div>
                """, unsafe_allow_html=True)

            with gov_c3:
                mfa_color = "#10b981" if mfa_pct == 100 else "#f59e0b"
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="font-size: 0.88rem; font-weight: 600; color:#0f172a;">MFA Adoption</div>
                    <div style="font-size: 2rem; font-weight: 800; line-height: 1; color:#0f172a;">{mfa_pct}%</div>
                    <div style="font-size: 0.8rem; font-weight: 600; color: {mfa_color};">🔐 Clinician 2FA Rate</div>
                </div>
                """, unsafe_allow_html=True)

            with gov_c4:
                st.markdown(f"""
                <div style="background-color: #ffffff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 15px 18px; height: 110px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="font-size: 0.88rem; font-weight: 600; color:#0f172a;">Compliance Index</div>
                    <div style="font-size: 2rem; font-weight: 800; line-height: 1; color:#0f172a;">100%</div>
                    <div style="font-size: 0.8rem; font-weight: 600; color: #10b981;">🛡️ HIPAA/DPA Compliant</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)
            
        with st.container(border=True):
            st.markdown("##### **INTAKE ACTIVITY OVER TIME**")
            st.caption("Activity tracking for Patients, Doctors, and Admin's accounts")
            chart_data = pd.DataFrame({"Patients": [0, 0, 20, 0, 0, 0, 0], "Doctors": [10, 0, 200, 0, 300, 30, 0], "Admins": [10, 0, 0, 300, 0, 0, 0]}, index=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
            st.line_chart(chart_data, width="stretch")

        current_date = datetime.now().strftime("%m/%d/%Y")
        st.markdown(f"<div style='text-align: right; font-size: 0.9rem; margin-bottom: 8px;'>Last Updated: {current_date}</div>", unsafe_allow_html=True)
        pool_col, cluster_col = st.columns([1, 1.5], gap="large")

        with pool_col:
            with st.container(border=True):
                st.markdown("#### Connection Pool Utilization")
                active_conn, max_conn = 0, 10
                utilization_pct = int((active_conn / max_conn) * 100)
                if active_conn <= 6: 
                    load_level, load_color = "Low", "#10b981"
                elif active_conn < 9: 
                    load_level, load_color = "Medium", "#f59e0b"
                else: 
                    load_level, load_color = "High", "#e10123"

                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=active_conn,
                    number={'suffix': f" / {max_conn}", 'font': {'size': 36}},
                    title={'text': f"<b>Active Connections</b><br><span style='font-size:14px;'>Utilization: {utilization_pct}%</span> • <span style='font-size:14px; font-weight:bold; color:{load_color};'>{load_level} Load</span>", 'font': {'size': 18}},
                    gauge={'axis': {'range': [0, max_conn], 'tickmode': 'linear', 'tick0': 0, 'dtick': 2, 'tickwidth': 1.5, 'ticks': "inside", 'tickfont': {'size': 13}}, 'bar': {'color': "#007979"}, 'borderwidth': 0, 'steps': [{'range': [0, 6], 'color': 'rgba(16, 185, 129, 0.2)'}, {'range': [6, 8], 'color': 'rgba(245, 158, 11, 0.2)'}, {'range': [8, 10], 'color': 'rgba(239, 68, 68, 0.2)'}], 'threshold': {'line': {'color': "#b91c1c", 'width': 3}, 'thickness': 0.8, 'value': 9}}
                ))
                fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=15), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, width="stretch", config={'displayModeBar': False})

        with cluster_col:
            with st.container(border=True):
                st.markdown("#### Cluster Monitor")
                def evaluate_node_status(is_connected: bool, is_timeout: bool, active_sockets: int) -> str:
                    if is_timeout: return "🔴 Error: Timeout"
                    if not is_connected: return "🔴 Server Down"
                    if active_sockets == 0: return "🟡 Idle"
                    return "🟢 Healthy"

                raw_nodes_data = [
                    {"pid": "1XXX.XX.X.X1", "sockets": 2, "connected": True,  "timeout": False},
                    {"pid": "1XXX.XX.X.X2", "sockets": 0, "connected": True,  "timeout": False},
                    {"pid": "1XXX.XX.X.X3", "sockets": 0, "connected": False, "timeout": True},
                    {"pid": "1XXX.XX.X.X4", "sockets": 0, "connected": False, "timeout": False}
                ]
                processed_records = [{"PID": node["pid"], "Active Sockets": node["sockets"], "Status": evaluate_node_status(node["connected"], node["timeout"], node["sockets"])} for node in raw_nodes_data]
                st.dataframe(pd.DataFrame(processed_records), width="stretch", hide_index=True, height=180)
                st.markdown("""
                <div style="display: flex; justify-content: center; gap: 12px; margin-top: 14px;">
                    <div style="display: flex; align-items: center; gap: 8px; padding: 6px 16px; border: 1px solid #334155; border-radius: 20px; font-size: 0.85rem; font-weight: 600;"><span style="height: 10px; width: 10px; border-radius: 50%; background-color: #28a745; display: inline-block;"></span>Active</div>
                    <div style="display: flex; align-items: center; gap: 8px; padding: 6px 16px; border: 1px solid #334155; border-radius: 20px; font-size: 0.85rem; font-weight: 600;"><span style="height: 10px; width: 10px; border-radius: 50%; background-color: #ffc107; display: inline-block;"></span>Idle</div>
                    <div style="display: flex; align-items: center; gap: 8px; padding: 6px 16px; border: 1px solid #334155; border-radius: 20px; font-size: 0.85rem; font-weight: 600;"><span style="height: 10px; width: 10px; border-radius: 50%; background-color: #dc3545; display: inline-block;"></span>Error</div>
                </div>
                """, unsafe_allow_html=True)

        grid_row1_col1, grid_row1_col2 = st.columns(2, gap="large")
        with grid_row1_col1:
            with st.container(border=True):
                st.markdown("##### 🛢️ **PostgreSQL Engine Health**")
                is_connected, ping_success, db_latency_ms, db_recycle_state = True, True, 15, "Active (1800s pool)"
                if not is_connected or not ping_success or db_latency_ms is None: db_status, status_icon, status_color, sub_label, latency_text, latency_badge_color = "DOWN", "✖", "#dc2626", "Connection Lost / Timeout", "N/A (Unreachable)", "#dc2626"
                elif db_latency_ms > 100: db_status, status_icon, status_color, sub_label, latency_text, latency_badge_color = "DEGRADED", "⚠", "#f59e0b", "SELECT 1 (High Latency)", f"{db_latency_ms} ms (Slow)", "#f59e0b"
                else: db_status, status_icon, status_color, sub_label, latency_text, latency_badge_color = "UP", "✔", "#16a34a", "SELECT 1", f"{db_latency_ms} ms (Optimal)", "#16a34a"

                st.markdown(f"""
                <div style="text-align: center; margin: 16px 0 10px 0;"><div style="font-size: 2.2rem; font-weight: 800; color: {status_color}; display: inline-flex; align-items: center; gap: 8px;"><span>{status_icon}</span> {db_status}</div><div style="font-size: 0.85rem; font-weight: 600; margin-top: -2px; color:#0f172a;">({sub_label})</div></div>
                <div style="border-top: 1px solid rgba(148, 163, 184, 0.2); padding-top: 14px; margin-top: 14px;"><div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.92rem; margin-bottom: 8px; color:#0f172a;"><span>Database Latency:</span><strong style="color: {latency_badge_color};">{latency_text}</strong></div><div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.92rem; color:#0f172a;"><span>Recycle State:</span><span style="font-weight: 600;">{db_recycle_state}</span></div></div>
                """, unsafe_allow_html=True)
                
        with grid_row1_col2:
            with st.container(border=True):
                st.markdown("##### 🗘 **Idempotency Replay Hit Rate**")
                st.markdown("""<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 138px;"><div style="font-size: 3.6rem; font-weight: 800; line-height: 1; color:#0f172a;">0</div><div style="font-size: 1rem; font-weight: 600; margin-top: 12px; color:#0f172a;">Replays Short-circuited</div></div>""", unsafe_allow_html=True)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        grid_row2_col1, grid_row2_col2 = st.columns(2, gap="large")

        with grid_row2_col1:
            with st.container(border=True):
                st.markdown("##### 🌐 **HTTP Traffic & Error Distribution**")
                fig_donut = go.Figure(data=[go.Pie(labels=["2xx Success", "4xx Client Errors", "5xx Server Exceptions"], values=[888, 338, 3], hole=0.62, marker=dict(colors=["#10b981", "#f59e0b", "#ef4444"]), textinfo="percent", hoverinfo="label+value+percent", showlegend=True)])
                fig_donut.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=11)), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_donut, width="stretch", config={'displayModeBar': False})

        with grid_row2_col2:
            with st.container(border=True):
                st.markdown("##### 🛡️ **Security Middleware Status**")
                st.markdown("""
                <div style="text-align: center; margin: 10px 0 14px 0;"><div style="font-size: 2.2rem; font-weight: 800; color: #16a34a; display: inline-flex; align-items: center; gap: 8px;">✔ ACTIVE</div><div style="font-size: 0.85rem; font-weight: 600; margin-top: -4px; color:#0f172a;">All Filters Intercepting</div></div>
                <div style="border-top: 1px solid rgba(148, 163, 184, 0.2); padding-top: 12px; display: flex; flex-direction: column; gap: 8px; font-size: 0.9rem; color:#0f172a;"><div style="display: flex; align-items: center; gap: 8px;"><span style="color: #16a34a; font-weight: bold;">✔</span> CORS Headers Active</div><div style="display: flex; align-items: center; gap: 8px;"><span style="color: #16a34a; font-weight: bold;">✔</span> Strict Security Headers (CSP, X-Frame-Options)</div><div style="display: flex; align-items: center; gap: 8px;"><span style="color: #16a34a; font-weight: bold;">✔</span> Sanitization Filters</div></div>
                """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # TAB 2: PROVISIONING FORM & CLINICIAN DIRECTORY
    # --------------------------------------------------------------------------
    with tab_form:
        if st.session_state.get("trigger_form_clear"):
            for key in ["doc_first_name", "doc_middle_name", "doc_last_name", "doc_address", "doc_prc", "doc_email", "doc_contact", "em_name", "em_contact", "doc_affiliation"]:
                st.session_state[key] = ""
                st.session_state[f"{key}_invalid"] = False
            st.session_state.trigger_form_clear = False

        if st.session_state.form_success:
            st.success(st.session_state.form_success)
            st.session_state.form_success = None

        with st.container(border=True):
            st.markdown("""
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0; font-size: 1.45rem; font-weight: 700; letter-spacing: -0.3px;">Provision Clinician Account</h3>
                <p style="margin: 4px 0 14px 0; font-size: 0.95rem;">Create a verified practitioner profile and register login credentials in the system.</p>
                <div style="height: 1px; width: 100%; background-color: rgba(148, 163, 184, 0.2); margin-bottom: 18px;"></div>
            </div>
            """, unsafe_allow_html=True)

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

            row4_col1, row4_col2, row4_col3, row4_col4 = st.columns([1.5, 2, 1.3, 1])
            with row4_col1: specialization = st.selectbox("SPECIALIZATION*", options=SPECIALIZATION_OPTIONS)
            with row4_col2: hospital_affiliation = st.text_input("CLINIC AFFILIATION", placeholder="e.g., Manila Doctors Hospital", key="doc_affiliation")
            with row4_col3: 
                prc_license_raw = st.text_input("PRC LICENSE*", placeholder="7 digits only", max_chars=7, key="doc_prc", on_change=clean_prc_license, args=("doc_prc",))
                if st.session_state.get("doc_prc_invalid"): st.error("⛔ Numbers only.")
            with row4_col4: suffix = st.selectbox("SUFFIX*", options=SUFFIX_OPTIONS)

            row5_col1, row5_col2 = st.columns([1, 1])
            with row5_col1:
                email = st.text_input("EMAIL*", placeholder="strictly @gmail.com", key="doc_email")
                if email and not is_valid_gmail(email): 
                    st.error("⛔ Must be a valid Gmail address.")
            with row5_col2:
                contact_number = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="doc_contact", on_change=format_phone_number, args=("doc_contact",))
                if st.session_state.get("doc_contact_invalid"): 
                    st.error("⛔ Numbers only.")

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
            st.markdown("#### **CONTACT IN CASE OF EMERGENCY**")
            emergency_name = st.text_input("FULL NAME*", placeholder="Enter emergency contact's full name", key="em_name", on_change=clean_alpha_input, args=("em_name",))
            if st.session_state.get("em_name_invalid"): st.error("⛔ Letters only.")

            emergency_contact = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="em_contact", on_change=format_phone_number, args=("em_contact",))
            if st.session_state.get("em_contact_invalid"): st.error("⛔ Numbers only.")

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
            st.markdown("#### **CREDENTIAL DISPATCH & SECURITY CONTROLS**")
            col_sec1, col_sec2, col_sec3 = st.columns([1.5, 1.5, 1.2])
            with col_sec1: send_email_toggle = st.toggle("Automated Onboarding Email", value=True)
            with col_sec2: require_mfa_toggle = st.toggle("Enforce MFA on First Login", value=True)
            with col_sec3: cred_ttl = st.selectbox("Credential TTL", options=["24 Hours", "48 Hours", "7 Days"], index=0)

            st.divider()
            submit_btn = st.button("Submit Provisioning", type="primary", width="stretch")
            
        if submit_btn:
            errors = []
            if not first_name.strip(): errors.append("First Name is required.")
            if not last_name.strip(): errors.append("Last Name is required.")
            if not address.strip(): errors.append("Address is required.")
            if len(prc_license_raw) != 7: errors.append("PRC License must be exactly 7 digits.")
            if not is_valid_gmail(email): errors.append("Valid Gmail address is required.")
            if not is_valid_phone_format(contact_number): errors.append("Doctor Contact Number must be exactly 11 digits.")
            if not emergency_name.strip(): errors.append("Emergency Contact Name is required.")
            if not is_valid_phone_format(emergency_contact): errors.append("Emergency Contact Number must be exactly 11 digits.")
            
            formatted_prc = f"PRC {prc_license_raw.strip()}"
            if any(doc.get("license_number") == formatted_prc for doc in st.session_state.doctor_directory):
                errors.append(f"License Conflict: `{formatted_prc}` is already registered.")

            if errors:
                for err in errors: st.error(f"❌ {err}")
            else:
                middle_init = f" {middle_name.strip().title()[0]}." if middle_name.strip() else ""
                formatted_full_name = f"{last_name.strip().title()}, {first_name.strip().title()}{middle_init}"
                
                st.session_state.doctor_directory.append({
                    "doctor_id": len(st.session_state.doctor_directory) + 1, "name": formatted_full_name,
                    "license_number": formatted_prc, "specialization": specialization,
                    "email": email.strip().lower(), "contact_number": contact_number,
                    "hospital_affiliation": hospital_affiliation.strip() or "Lucerna Medica Main Clinic",
                    "is_verified": True, "failed_attempts": 0, "is_locked": False, "mfa_enrolled": False, "token_version": 1
                })

                st.session_state.doctor_audit_logs.insert(0, {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "target_doctor": formatted_full_name,
                    "event_type": "ACCOUNT_PROVISIONED", "actor": f"Admin ({user_email})", "ip_address": "127.0.0.1",
                    "details": f"TTL: {cred_ttl} | Email Dispatched: {send_email_toggle} | MFA Required: {require_mfa_toggle}"
                })

                st.session_state.trigger_form_clear = True
                st.session_state.form_success = f"✅ Successfully provisioned **Dr. {first_name.title()} {last_name.title()}** with license **{formatted_prc}**!"
                st.rerun()

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### Clinician Database & Directory")
            st.caption("Inspect, filter, and manage provisioned clinical accounts.")
            
            raw_df = pd.DataFrame(st.session_state.doctor_directory)

            if not raw_df.empty:
                f_col_search, f_col_spec, f_col_status = st.columns([2.5, 2, 1.5])
                with f_col_search: search_query = st.text_input("Search Clinician", placeholder="Search by name, license #, or email...", label_visibility="collapsed", key="doc_search")
                with f_col_spec: selected_specialties = st.multiselect("Filter by Specialization", options=SPECIALIZATION_OPTIONS, placeholder="All Specialties", label_visibility="collapsed", key="doc_spec_filter")
                with f_col_status: status_filter = st.radio("Status Filter", options=["All", "Verified", "Pending"], horizontal=True, label_visibility="collapsed", key="doc_status_filter")

                filtered_df = raw_df.copy()
                if search_query:
                    query = search_query.lower()
                    filtered_df = filtered_df[filtered_df["name"].str.lower().str.contains(query) | filtered_df["license_number"].str.lower().str.contains(query) | filtered_df["email"].str.lower().str.contains(query)]
                if selected_specialties: filtered_df = filtered_df[filtered_df["specialization"].isin(selected_specialties)]
                if status_filter == "Verified": filtered_df = filtered_df[filtered_df["is_verified"] == True]
                elif status_filter == "Pending": filtered_df = filtered_df[filtered_df["is_verified"] == False]

                display_df = filtered_df.copy()
                display_df["status_badge"] = display_df["is_verified"].apply(lambda v: "🟢 Verified" if v else "🟡 Pending")
                display_df["lock_badge"] = display_df["is_locked"].apply(lambda l: "🔒 Locked" if l else "🟢 Normal")

                clinician_selection = st.dataframe(
                    display_df[["name", "license_number", "specialization", "contact_number", "email", "hospital_affiliation", "status_badge", "lock_badge"]],
                    width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row",
                    column_config={
                        "name": st.column_config.TextColumn("Clinician Name", width="medium"), "license_number": st.column_config.TextColumn("License Number", width="small"),
                        "specialization": st.column_config.TextColumn("Specialization", width="medium"), "contact_number": st.column_config.TextColumn("Contact Phone", width="small"),
                        "email": st.column_config.TextColumn("Institutional Email", width="medium"), "hospital_affiliation": st.column_config.TextColumn("Affiliation", width="medium"),
                        "status_badge": st.column_config.TextColumn("Verification", width="small"), "lock_badge": st.column_config.TextColumn("Access State", width="small")
                    },
                    height=240, key="clinician_directory_table"
                )

                st.divider()
                st.markdown("##### **Account Governance & Security Controls**")
                
                selected_doc_rows = clinician_selection.selection.rows
                target_doc = None
                if selected_doc_rows:
                    selected_license = display_df.iloc[selected_doc_rows[0]]["license_number"]
                    target_doc = next((d for d in st.session_state.doctor_directory if d.get("license_number") == selected_license), None)

                render_clinician_governance_panel(target_doc, user_email)
            else:
                st.info("No clinician accounts registered.")

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### Non-Clinical Identity & Security Audit Trail")
            st.caption("Immutable system log tracking authentication attempts, credential state changes, and verification approvals.")

            audit_df = pd.DataFrame(st.session_state.doctor_audit_logs)
            if not audit_df.empty:
                st.dataframe(
                    audit_df, width="stretch", hide_index=True, key="doctor_audit_logs_table_df",
                    column_config={
                        "timestamp": st.column_config.TextColumn("Timestamp (UTC)", width="medium"), "target_doctor": st.column_config.TextColumn("Clinician", width="medium"),
                        "event_type": st.column_config.TextColumn("Security Event", width="medium"), "actor": st.column_config.TextColumn("Triggered By", width="medium"),
                        "ip_address": st.column_config.TextColumn("Client IP", width="small"), "details": st.column_config.TextColumn("Telemetry & Audit Payload", width="large")
                    },
                    height=240
                )
            else:
                st.info("No security audit events recorded.")

    # --------------------------------------------------------------------------
    # TAB 3: PATIENT MANAGEMENT
    # --------------------------------------------------------------------------
    with tab_patient:
        raw_patients_df = pd.DataFrame(st.session_state.patient_directory)

        with st.container(border=True):
            st.markdown("### Pending Verification Queue")
            st.caption("Newly registered patients awaiting email confirmation or SMS OTP activation.")

            if not raw_patients_df.empty and "is_verified" in raw_patients_df.columns:
                pending_df = raw_patients_df[raw_patients_df["is_verified"] == False].reset_index(drop=True)

                if not pending_df.empty:
                    selection_event = st.dataframe(
                        pending_df[["name", "email", "contact_number", "registered_at", "pending_method", "dispatch_count"]],
                        width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row",
                        key="df_pending_verification_queue",
                        column_config={
                            "name": "Full Name", "email": "Gmail Address", "contact_number": "Contact Number",
                            "registered_at": "Registered At", "pending_method": "Pending Method", "dispatch_count": "Dispatches"
                        },
                        height=160
                    )

                    selected_rows = selection_event.selection.rows
                    target_pending = pending_df.iloc[selected_rows[0]] if selected_rows else None

                    if target_pending is not None:
                        st.markdown(f"Selected: **{target_pending['name']}** (`{target_pending['email']}`)")
                    else:
                        st.caption("👈 *Click on a row in the table above to select a patient for action.*")

                    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        if st.button("🔄 Resend Link / OTP", width="stretch", disabled=(target_pending is None), key="btn_pend_resend"):
                            for p in st.session_state.patient_directory:
                                if p.get("patient_id") == target_pending.get("patient_id"): p["dispatch_count"] = p.get("dispatch_count", 0) + 1
                            st.session_state.patient_audit_logs.insert(0, {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "target_patient": target_pending["name"], "event_type": "OTP_REDISPATCHED", "actor": f"Admin ({user_email})", "ip_address": "127.0.0.1", "details": f"Verification token re-dispatched to {target_pending['email']}."})
                            st.success(f"Verification token re-sent to {target_pending['email']}.")
                            st.rerun()

                    with col_p2:
                        if st.button("✅ Manual Authorization", width="stretch", disabled=(target_pending is None), key="btn_pend_auth"):
                            for p in st.session_state.patient_directory:
                                if p.get("patient_id") == target_pending.get("patient_id"):
                                    p["is_verified"] = True; p["is_active"] = True; p["pending_method"] = "None"
                            st.session_state.patient_audit_logs.insert(0, {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "target_patient": target_pending["name"], "event_type": "MANUAL_VERIFICATION", "actor": f"Admin ({user_email})", "ip_address": "127.0.0.1", "details": "Identity authorized manually by administrative override."})
                            st.success(f"Account for {target_pending['name']} manually verified.")
                            st.rerun()

                    with col_p3:
                        if st.button("🗑️ Purge Expired Requests", width="stretch", key="btn_pend_purge"):
                            purged_count = len([p for p in st.session_state.patient_directory if not p.get("is_verified", False)])
                            st.session_state.patient_directory = [p for p in st.session_state.patient_directory if p.get("is_verified", False)]
                            st.warning(f"Purged {purged_count} unverified registration attempt(s).")
                            st.rerun()
                else:
                    st.info("Queue is clear. No pending verifications.")
            else:
                st.info("Queue is clear. No pending verifications.")

        with st.container(border=True):
            st.markdown("### Master Patient Directory")
            st.caption("Manage active accounts, enforce HIPAA compliance, and control access states.")

            if not raw_patients_df.empty:
                f_col_search, f_col_status, f_col_hipaa = st.columns([2.5, 1.5, 1.5])
                with f_col_search: p_search_query = st.text_input("Search Patient", placeholder="Search by name, email, or phone...", label_visibility="collapsed", key="pat_search_input")   
                with f_col_status: p_status_filter = st.radio("Status Filter", options=["All", "Active", "Pending", "Suspended"], horizontal=True, label_visibility="collapsed", key="pat_status_filter")
                with f_col_hipaa: p_hipaa_filter = st.radio("HIPAA State", options=["All", "Consented", "Pending"], horizontal=True, label_visibility="collapsed", key="pat_hipaa_filter")

                p_filtered_df = raw_patients_df.copy()
                if p_search_query:
                    q = p_search_query.lower()
                    p_filtered_df = p_filtered_df[p_filtered_df["name"].str.lower().str.contains(q) | p_filtered_df["email"].str.lower().str.contains(q) | p_filtered_df.get("contact_number", pd.Series(dtype=str)).str.contains(q)]
                
                if p_status_filter == "Active": p_filtered_df = p_filtered_df[(p_filtered_df.get("is_active", True) == True) & (p_filtered_df.get("is_locked", False) == False)]
                elif p_status_filter == "Pending": p_filtered_df = p_filtered_df[p_filtered_df.get("is_verified", False) == False]
                elif p_status_filter == "Suspended": p_filtered_df = p_filtered_df[(p_filtered_df.get("is_active", True) == False) | (p_filtered_df.get("is_locked", False) == True)]

                if p_hipaa_filter == "Consented": p_filtered_df = p_filtered_df[p_filtered_df.get("hipaa_consent", False) == True]
                elif p_hipaa_filter == "Pending": p_filtered_df = p_filtered_df[p_filtered_df.get("hipaa_consent", False) == False]

                p_display_df = p_filtered_df.copy()
                if not p_display_df.empty:
                    p_display_df["hipaa_badge"] = p_display_df.get("hipaa_consent", pd.Series([False]*len(p_display_df))).apply(lambda v: "📝 Consented" if v else "⏳ Pending")
                    
                    def get_account_state(row):
                        if not row.get("is_verified", False): return "🟡 Pending"
                        if row.get("is_locked", False): return "🔒 Locked"
                        if not row.get("is_active", True): return "🔴 Suspended"
                        return "🟢 Active"
                    
                    p_display_df["account_state"] = p_display_df.apply(get_account_state, axis=1)

                    disp_cols = [c for c in ["name", "email", "contact_number", "dob", "hipaa_badge", "account_state"] if c in p_display_df.columns]

                    patient_selection = st.dataframe(
                        p_display_df[disp_cols],
                        width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row", key="df_master_patient_directory",
                        column_config={
                            "name": "Patient Name", "email": "Gmail Address", "contact_number": "Contact Phone",
                            "dob": "Date of Birth", "hipaa_badge": "HIPAA Status", "account_state": "Account State"
                        },
                        height=240
                    )

                    st.divider()
                    st.markdown("##### **Account Governance Panel**")
                    
                    selected_pat_rows = patient_selection.selection.rows
                    target_patient = None
                    if selected_pat_rows and "email" in p_display_df.columns:
                        selected_email = p_display_df.iloc[selected_pat_rows[0]]["email"]
                        target_patient = next((p for p in st.session_state.patient_directory if p.get("email") == selected_email), None)
                    
                    render_patient_governance_panel(target_patient, user_email)
            else:
                st.info("No patient accounts registered.")

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### Patient IAM & Compliance Audit Trail")
            st.caption("Immutable system event log recording security operations and HIPAA consent milestones.")
            p_audit_df = pd.DataFrame(st.session_state.patient_audit_logs)
            if not p_audit_df.empty:
                st.dataframe(
                    p_audit_df, width="stretch", hide_index=True, key="df_patient_audit_logs",
                    column_config={
                        "timestamp": "Timestamp (UTC)", "target_patient": "Target Patient", 
                        "event_type": "Security Event", "actor": "Triggered By", 
                        "ip_address": "Client IP", "details": st.column_config.TextColumn("Telemetry Payload", width="large")
                    },
                    height=240
                )
            else:
                st.info("No audit events recorded.")

    # --------------------------------------------------------------------------
    # TAB 4: EMPLOYEE / ADMIN ACCOUNTS & SETTINGS
    # --------------------------------------------------------------------------
    with tab_Admin:
        # --- ADMIN SECURITY SETTINGS ---
        with st.container(border=True):
            st.markdown("### Admin Security Settings")
            st.caption("Manage your own administrative credentials and profile security.")
            
            adm_col1, adm_col2 = st.columns([1, 1], gap="large")
            with adm_col1:
                st.markdown("##### Update Password")
                with st.form("account_tab_password_change_form", clear_on_submit=True):
                    st.text_input("Current Password", type="password", placeholder="Enter current password")
                    new_pw_col1, new_pw_col2 = st.columns(2)
                    with new_pw_col1: new_pw = st.text_input("New Password", type="password", placeholder="Enter new password")
                    with new_pw_col2: confirm_pw = st.text_input("Confirm Password", type="password", placeholder="Re-type new password")
                        
                    if st.form_submit_button("Update Admin Password", type="primary", use_container_width=True):
                        if not new_pw or not confirm_pw: st.error("❌ Please fill in all password fields.")
                        elif new_pw != confirm_pw: st.error("❌ New passwords do not match.")
                        else: st.success("✅ Your administrative password has been successfully updated.")
                            
            with adm_col2:
                st.markdown("##### Administrative Profile")
                st.text_input("Registered Name", value=user_name, disabled=True, help="Contact IT to change registered name.")
                st.text_input("Institutional Email", value=user_email, disabled=True)
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.markdown(f"**Current Role:** `<{user_role}>`")
                st.markdown("**MFA Status:** <span style='color: #10b981; font-weight: bold;'>🟢 Active (Authenticator App)</span>", unsafe_allow_html=True)

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # --- PROVISION NEW ADMIN ACCOUNT CONTAINER ---
        with st.container(border=True):
            st.markdown("##### Provision New Admin Account")

            if st.session_state.get("trigger_admin_form_clear"):
                for k in [
                    "adm_first_name", "adm_middle_name", "adm_last_name", "adm_address",
                    "adm_department", "adm_code", "adm_email", "adm_contact",
                    "adm_em_name", "adm_contact_em"
                ]:
                    st.session_state[k] = ""
                    st.session_state[f"{k}_invalid"] = False
                st.session_state.trigger_admin_form_clear = False

            if st.session_state.get("admin_form_success"):
                st.success(st.session_state.admin_form_success)
                st.session_state.admin_form_success = None

            emp_first_name = st.text_input("FIRST NAME*", placeholder="Enter first name", key="adm_first_name", on_change=clean_alpha_input, args=("adm_first_name",))
            if st.session_state.get("adm_first_name_invalid"): 
                st.error("⛔ Letters only. Numbers and symbols are not permitted.")

            emp_last_name = st.text_input("LAST NAME*", placeholder="Enter last name", key="adm_last_name", on_change=clean_alpha_input, args=("adm_last_name",))
            if st.session_state.get("adm_last_name_invalid"): 
                st.error("⛔ Letters only. Numbers and symbols are not permitted.")

            row3_col1, row3_col2 = st.columns([1, 3])
            with row3_col1: 
                emp_middle_name = st.text_input("MIDDLE NAME", placeholder="Optional", key="adm_middle_name", on_change=clean_alpha_input, args=("adm_middle_name",))
                if st.session_state.get("adm_middle_name_invalid"): 
                    st.error("⛔ Letters only.")
            with row3_col2: 
                emp_address = st.text_input("ADDRESS*", placeholder="Residential or office address", key="adm_address")

            row4_col1, row4_col2, row4_col3, row4_col4 = st.columns([1.5, 2, 1.3, 1])
            with row4_col1: 
                emp_role = st.selectbox("ROLE*", ["System Admin", "Super Admin", "IT Support", "Compliance Auditor"], key="adm_role")
            with row4_col2: 
                emp_dept = st.text_input("DEPARTMENT", value="Administration", key="adm_department")
            with row4_col3:
                default_code = f"ADM-{len(st.session_state.employee_directory) + 1:03d}"
                emp_code = st.text_input("ADMIN CODE*", value=st.session_state.get("adm_code") or default_code, placeholder="e.g., ADM-001", key="adm_code")
            with row4_col4: 
                emp_suffix = st.selectbox("SUFFIX*", SUFFIX_OPTIONS, key="adm_suffix")

            row5_col1, row5_col2 = st.columns(2)
            with row5_col1: 
                emp_email = st.text_input("EMAIL*", placeholder="name@hospital.com", key="adm_email")
                if emp_email and not is_valid_admin_email(emp_email): 
                    st.error("⛔ Please enter a valid institutional / hospital email address.")
            with row5_col2: 
                emp_contact = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="adm_contact", on_change=format_phone_number, args=("adm_contact",))
                if st.session_state.get("adm_contact_invalid"): 
                    st.error("⛔ Numbers only.")

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
            st.markdown("#### **CONTACT IN CASE OF EMERGENCY**")
            emp_em_name = st.text_input("FULL NAME*", placeholder="Enter emergency contact's full name", key="adm_em_name", on_change=clean_alpha_input, args=("adm_em_name",))
            if st.session_state.get("adm_em_name_invalid"): 
                st.error("⛔ Letters only.")
            
            row_em1, row_em2 = st.columns(2)
            with row_em1: 
                emp_em_contact = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="adm_contact_em", on_change=format_phone_number, args=("adm_contact_em",))
                if st.session_state.get("adm_contact_em_invalid"): 
                    st.error("⛔ Numbers only.")
            with row_em2: 
                emp_em_relation = st.selectbox("RELATION*", RELATION_OPTIONS, key="adm_em_relation")

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
            st.markdown("#### **CREDENTIAL DISPATCH & SECURITY CONTROLS**")
            col_sec1, col_sec2, col_sec3 = st.columns([1.5, 1.5, 1.2])
            with col_sec1: 
                emp_send_email = st.toggle("Onboarding Email", value=True, key="adm_send_email")
            with col_sec2: 
                emp_require_mfa = st.toggle("Enforce MFA", value=True, key="adm_require_mfa")
            with col_sec3: 
                emp_cred_ttl = st.selectbox("Credential TTL", ["24 Hours", "48 Hours", "7 Days"], key="adm_cred_ttl")

            st.divider()
            submit_emp = st.button("Create Admin Account", type="primary", width="stretch")

            if submit_emp:
                errors = []
                if not emp_first_name.strip(): errors.append("First Name is required.")
                if not emp_last_name.strip(): errors.append("Last Name is required.")
                if not emp_address.strip(): errors.append("Address is required.")
                if not emp_code.strip(): errors.append("Admin Code is required.")
                if not is_valid_admin_email(emp_email): errors.append("Valid Institutional / Hospital Email is required.")
                if not is_valid_phone_format(emp_contact): errors.append("Contact Number must follow 09XX-XXX-XXXX.")
                if not emp_em_name.strip(): errors.append("Emergency Contact Name is required.")
                if not is_valid_phone_format(emp_em_contact): errors.append("Emergency Contact Number must follow 09XX-XXX-XXXX.")

                if any(e.get("emp_id") == emp_code.strip() for e in st.session_state.employee_directory):
                    errors.append(f"Admin Code Conflict: `{emp_code.strip()}` is already assigned.")

                if errors:
                    for err in errors: st.error(f"❌ {err}")
                else:
                    mid_init = f" {emp_middle_name.strip().title()[0]}." if emp_middle_name.strip() else ""
                    full_name = f"{emp_last_name.strip().title()}, {emp_first_name.strip().title()}{mid_init}"

                    st.session_state.employee_directory.append({
                        "emp_id": emp_code.strip(), "name": full_name, "role": emp_role,
                        "department": emp_dept.strip() or "Administration", "email": emp_email.strip().lower(),
                        "contact_number": emp_contact.strip(), "status": "Active"
                    })
                    st.session_state.trigger_admin_form_clear = True
                    st.session_state.admin_form_success = f"✅ Provisioned Admin **{full_name}** (`{emp_code.strip()}`) successfully!"
                    st.rerun()

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # --- STAFF & ADMIN DIRECTORY & GOVERNANCE PANEL ---
        with st.container(border=True):
            st.markdown("##### Staff & Admin Directory")
            
            emp_df = pd.DataFrame(st.session_state.employee_directory)
            if not emp_df.empty:
                emp_display = emp_df.copy()
                emp_display["status_badge"] = emp_display.get("status", pd.Series(["Active"]*len(emp_display))).apply(lambda s: "🟢 Active" if s == "Active" else "🔴 Suspended")
                
                disp_cols = [c for c in ["emp_id", "name", "role", "email", "status_badge"] if c in emp_display.columns]

                emp_selection = st.dataframe(
                    emp_display[disp_cols], 
                    width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row", key="admin_tab_employee_df",
                    column_config={
                        "emp_id": "Emp ID", "name": "Name", "role": "Role", "email": "Email", "status_badge": "Status"
                    },
                    height=220
                )

                st.divider()
                st.markdown("##### 🔑 Credential Management")

                selected_emp_rows = emp_selection.selection.rows
                target_e = None
                if selected_emp_rows and "emp_id" in emp_display.columns:
                    selected_emp_id = emp_display.iloc[selected_emp_rows[0]]["emp_id"]
                    target_e = next((e for e in st.session_state.employee_directory if e.get("emp_id") == selected_emp_id), None)

                render_admin_governance_panel(target_e)
            else:
                st.info("No employee accounts registered.")