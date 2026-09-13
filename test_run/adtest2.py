import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime

# ==============================================================================
# PAGE CONFIGURATION & STATE INITIALIZATION
# ==============================================================================
st.set_page_config(layout="wide")

user_avatar_url = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80"
user_role = "ADMIN"
user_name = "First Name"
user_email = "admin.system@lucernamedica.com"

# ==============================================================================
# CALLBACKS & VALIDATION HELPERS
# ==============================================================================
def clean_alpha_input(key: str):
    """Instantly strips numbers and symbols, leaving only letters, spaces, and hyphens."""
    raw_val = st.session_state.get(key, "")
    st.session_state[f"{key}_invalid"] = bool(re.search(r"[^A-Za-z\s\-]", raw_val))
    st.session_state[key] = re.sub(r"[^A-Za-z\s\-]", "", raw_val)

def format_phone_number(key: str):
    """Instantly formats input into a 09XX-XXX-XXXX string."""
    digits = "".join(filter(str.isdigit, st.session_state.get(key, "")))[:11]
    formatted = digits[:4] + ("-" + digits[4:7] if len(digits) > 4 else "") + ("-" + digits[7:11] if len(digits) > 7 else "")
    st.session_state[key] = formatted

def clean_prc_license(key: str):
    """Instantly strips letters and caps input at 7 digits."""
    raw_val = st.session_state.get(key, "")
    st.session_state[f"{key}_invalid"] = bool(re.search(r"[^0-9]", raw_val))
    st.session_state[key] = "".join(filter(str.isdigit, raw_val))[:7]

def is_valid_phone_format(text: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{3}-\d{4}$", text.strip()))

def is_valid_gmail(text: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", text.strip()))

# ==============================================================================
# DASHBOARD CSS STYLING
# ==============================================================================
st.markdown(f"""
    <style>
    /* Hide input instruction hints */
    [data-testid*="stInputInstructions"] {{ display: none !important; }}
    
    [data-testid="baseButton-secondary"]:hover, 
    [data-testid="baseButton-secondary"]:focus, 
    [data-testid="baseButton-secondary"]:active {{ 
        border-color: #007979 !important; 
        color: #007979 !important; 
    }}
    [data-baseweb="tab-list"] {{ display: flex !important; width: 100% !important; margin-top: 12px !important; }}
    [data-testid="stTab"] {{ flex: 1 !important; justify-content: center !important; }}
    [data-testid="stTab"] * {{ font-size: 1.25rem !important; font-weight: 800 !important; letter-spacing: 0.5px !important; }}
    [aria-selected="true"] * {{ color: #007979 !important; }}
    [data-baseweb="tab-highlight"] {{ background-color: #007979 !important; height: 3px !important; }}

    /* Target ONLY header secondary buttons (prevents overwriting primary submit button) */
    div[data-testid="stVerticalBlock"] > div > div > div > div > button[data-testid="baseButton-secondary"] {{
        height: 52px !important;
        border-radius: 8px !important;
        border: 1px solid #d0d7de !important;
        background-color: white !important;
    }}

    /* Make Primary Submit button clearly visible */
    button[data-testid="baseButton-primary"] {{
        background-color: #007979 !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 700 !important;
        height: 48px !important;
        border-radius: 8px !important;
    }}
    button[data-testid="baseButton-primary"]:hover {{
        background-color: #005f5f !important;
        color: #ffffff !important;
    }}

    /* Disable typing cursor inside selectbox dropdowns to make them click-only */
    div[data-testid="stSelectbox"] input {{
        caret-color: transparent !important;
        cursor: pointer !important;
    }}
    
    div[data-testid="stPopover"] > button {{
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        padding: 6px 12px !important;
        height: 52px !important;
    }}
    
    div[data-testid="stPopover"] > button [data-testid="stIconEmoji"] {{
        display: inline-block !important;
        width: 38px !important;
        height: 38px !important;
        min-width: 38px !important;
        border-radius: 50% !important;
        border: 2px solid #007979 !important;
        background-image: url('{user_avatar_url}') !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        font-size: 0 !important;
        color: transparent !important;
        margin-right: 12px !important;
        margin-bottom: 0 !important;
    }}

    div[data-testid="stPopover"] > button p {{
        margin: 0 !important;
        text-align: left !important;
        line-height: 1.2 !important;
        font-size: 0.85rem !important;
        color: #444 !important;
    }}
    div[data-testid="stPopover"] > button p strong {{
        font-size: 1rem !important;
        color: #1a1a1a !important;
        font-weight: 800 !important;
    }}

    .metric-card {{
        background-color: #ffffff;
        border: 1px solid #e0e4e8;
        border-radius: 12px;
        padding: 30px 34px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        width: 100%;
    }}
    .big-card {{ height: 230px; }}
    .left-small {{ height: 160px; }}
    .right-small {{ height: 195px; }}
    .b-num {{ font-size: 6rem; font-weight: 800; color: #111; line-height: 1; margin-bottom: 8px; }}
    .b-lbl {{ font-size: 1.6rem; font-weight: 600; color: #444; margin-top: auto; }}
    .s-num {{ font-size: 3.4rem; font-weight: 800; color: #111; line-height: 1; margin-bottom: 12px; }}
    .s-lbl {{ font-size: 1.15rem; font-weight: 500; color: #666; margin-top: auto; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# MAIN APP LAYOUT & GLOBALS
# ==============================================================================
SPECIALIZATION_OPTIONS = ["General Physician", "Internal Medicine", "Cardiology", "Pulmonology", "Psychiatry"]
SUFFIX_OPTIONS = ["None", "MD", "PhD", "DO", "MD, PhD", "Jr.", "Sr.", "III"]
RELATION_OPTIONS = ["Mother", "Father", "Spouse", "Son", "Daughter", "Brother", "Sister", "Other"]

# Initialize Form Keys
for key in [
    "doc_first_name", "doc_middle_name", "doc_last_name", "doc_address",
    "doc_affiliation", "doc_prc", "doc_email", "doc_contact", "em_name", "em_contact"
]:
    if key not in st.session_state:
        st.session_state[key] = ""

if "form_success" not in st.session_state:
    st.session_state.form_success = None

if "doctor_directory" not in st.session_state:
    st.session_state.doctor_directory = [
        {"doctor_id": 1, "name": "Smith, John M.", "license_number": "PRC 1234567", "specialization": "General Physician", "email": "doc.smith@gmail.com", "contact_number": "0917-123-4567", "hospital_affiliation": "Lucerna Central", "is_verified": True, "failed_attempts": 0, "is_locked": False, "mfa_enrolled": True, "token_version": 1},
        {"doctor_id": 2, "name": "Velasco, Maria A.", "license_number": "PRC 8839210", "specialization": "Cardiology", "email": "m.velasco@gmail.com", "contact_number": "0920-987-6543", "hospital_affiliation": "Heart Center", "is_verified": False, "failed_attempts": 4, "is_locked": True, "mfa_enrolled": False, "token_version": 3}
    ]

# Non-Clinical IAM Security Audit Trail

if "patient_directory" not in st.session_state:
    st.session_state.patient_directory = [
        {
            "patient_id": 1, "name": "Mason, Justin L.", "email": "j.mason@gmail.com", "contact_number": "0917-555-0198",
            "dob": "1992-08-14", "registered_at": "2026-09-09 08:15:22", "pending_method": "None", "dispatch_count": 1,
            "is_verified": True, "is_active": True, "hipaa_consent": True, "hipaa_consent_at": "2026-09-09 08:20:11",
            "failed_attempts": 0, "is_locked": False
        },
        {
            "patient_id": 2, "name": "Reyes, Sofia M.", "email": "sofia.reyes99@gmail.com", "contact_number": "0920-111-4432",
            "dob": "1999-11-02", "registered_at": "2026-09-10 10:05:00", "pending_method": "Pending Phone OTP", "dispatch_count": 2,
            "is_verified": False, "is_active": False, "hipaa_consent": False, "hipaa_consent_at": None,
            "failed_attempts": 0, "is_locked": False
        },
        {
            "patient_id": 3, "name": "Bautista, Carlos T.", "email": "cbautista.tech@gmail.com", "contact_number": "0918-999-8877",
            "dob": "1985-03-22", "registered_at": "2026-09-01 14:10:00", "pending_method": "None", "dispatch_count": 1,
            "is_verified": True, "is_active": False, "hipaa_consent": True, "hipaa_consent_at": "2026-09-01 14:15:00",
            "failed_attempts": 5, "is_locked": True
        }
    ]

if "patient_audit_logs" not in st.session_state:
    st.session_state.patient_audit_logs = [
        {"timestamp": "2026-09-09 08:20:11", "target_patient": "Mason, Justin L.", "event_type": "HIPAA_CONSENT_ACCEPTED", "actor": "System Registration", "ip_address": "112.201.44.9", "details": "Terms and Data Privacy Act acknowledged."},
        {"timestamp": "2026-09-10 10:15:00", "target_patient": "Reyes, Sofia M.", "event_type": "OTP_DISPATCHED", "actor": "Twilio Gateway", "ip_address": "System", "details": "SMS OTP re-sent (Attempt 2)."},
        {"timestamp": "2026-09-10 11:30:22", "target_patient": "Bautista, Carlos T.", "event_type": "ACCOUNT_SUSPENDED", "actor": "System Guard", "ip_address": "System", "details": "Suspended due to 5 consecutive failed logins."}
    ]
    ]

count_admins = 1
count_patients = 1
count_doctors = len(st.session_state.doctor_directory)
count_verified_docs = sum(1 for d in st.session_state.doctor_directory if d.get("is_verified", False))

_, col_main, _ = st.columns([10, 80, 10])

with col_main:
    # --- HEADER ---
    header_col, action_col = st.columns([3, 1.2], vertical_alignment="bottom")
    with header_col:
        st.markdown("<h3 style='margin-bottom:0; padding-bottom:0;'>Welcome Admin!</h3>", unsafe_allow_html=True)
    with action_col:
        col_icon1, col_icon2, col_profile = st.columns([1, 1, 3])
        with col_icon1:
            st.button("☰", use_container_width=True)
        with col_icon2:
            st.button("🔔", use_container_width=True)
        with col_profile:
            with st.popover(f"**{user_role}**  \n{user_name}", icon="👤", use_container_width=True):
                st.caption(user_email)
                if st.button("⏻ Log Out", type="primary", use_container_width=True):
                    st.session_state.authenticated = False
                    st.rerun()

    tab_metric, tab_form, tab_account = st.tabs(["METRIC", "FORM", "ACCOUNTS"])

    # --------------------------------------------------------------------------
    # TAB 1: METRIC DASHBOARD
    # --------------------------------------------------------------------------
    with tab_metric:
        st.write("") 
        # --- 1. SUMMARY METRIC CARDS (TOP) ---
        with st.container(border=True):
            st.markdown("<div style='margin-top: 35px;'></div>", unsafe_allow_html=True)   

            col_left, col_right = st.columns([1.5, 1], gap="large")

            # Left Panel: System Aggregates
            with col_left:
                r1_left, = st.columns(1)
                with r1_left:
                    st.markdown(f"""
                    <div class="metric-card big-card">
                        <div class="b-num">{count_admins + count_patients + count_doctors}</div>
                        <div class="b-lbl">Total accounts</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

                r2_left1, r2_left2 = st.columns(2, gap="large")
                with r2_left1:
                    st.markdown(f"""
                    <div class="metric-card left-small">
                        <div class="s-num">{count_admins + count_patients + count_verified_docs}</div>
                        <div class="s-lbl">Active Users</div>
                    </div>
                    """, unsafe_allow_html=True)
                with r2_left2:
                    st.markdown("""
                    <div class="metric-card left-small">
                        <div class="s-num">0</div>
                        <div class="s-lbl">Assessment</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Right Panel: Role Breakdowns
            with col_right:
                r1_right1, r1_right2 = st.columns(2, gap="large")
                with r1_right1:
                    st.markdown(f"""
                    <div class="metric-card right-small">
                        <div class="s-num">{count_doctors}</div>
                        <div class="s-lbl">Doctors</div>
                    </div>
                    """, unsafe_allow_html=True)
                with r1_right2:
                    st.markdown(f"""
                    <div class="metric-card right-small">
                        <div class="s-num">{count_admins}</div>
                        <div class="s-lbl">Admins</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

                r2_right1, _ = st.columns(2, gap="large")
                with r2_right1:
                    st.markdown(f"""
                    <div class="metric-card right-small">
                        <div class="s-num">{count_patients}</div>
                        <div class="s-lbl">Patients</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<div style='margin-bottom: 50px;'></div>", unsafe_allow_html=True)    

        # --- 2. INTAKE ACTIVITY OVER TIME CHART (MIDDLE) ---
        with st.container(border=True):
            st.markdown("##### **INTAKE ACTIVITY OVER TIME**")
            st.caption("Activity tracking for Patients, Doctors, and Admin's accounts")

            chart_data = pd.DataFrame(
                {"Patients": [0, 0, 20, 0, 0, 0, 0], "Doctors": [10, 0, 200, 0, 300, 30, 0], "Admins": [10, 0, 0, 300, 0, 0, 0]},
                index=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            )
            st.line_chart(chart_data, height=350, use_container_width=True)

        # --- 3. CONNECTION POOL & CLUSTER MONITOR (RESTORED) ---
        with st.container(border=True):
            current_date = datetime.now().strftime("%m/%d/%Y")
            st.markdown(f"<div style='text-align: right; color: #666; font-size: 0.9rem; margin-bottom: -15px;'>Last Updated: {current_date}</div>", unsafe_allow_html=True)
            
            pool_col, cluster_col = st.columns([1, 1.5], gap="large")
            
            with pool_col:
                st.markdown("#### Connection Pool Utilization")
                
                active_conn = 0
                max_conn = 10
                utilization_pct = int((active_conn / max_conn) * 100)
                
                if active_conn <= 6:
                    load_level = "Low"
                    load_color = "#10b981"
                elif active_conn < 9:
                    load_level = "Medium"
                    load_color = "#f59e0b"
                else:
                    load_level = "High"
                    load_color = "#e10123"

                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=active_conn,
                    number={
                        'suffix': f" / {max_conn}", 
                        'font': {'size': 36, 'color': '#111827'}
                    },
                    title={
                        'text': (
                            f"<b>Active Connections</b><br>"
                            f"<span style='font-size:14px; color:#6b7280;'>Utilization: {utilization_pct}%</span> • "
                            f"<span style='font-size:14px; font-weight:bold; color:{load_color};'>{load_level} Load</span>"
                        ),
                        'font': {'size': 18, 'color': '#1f2937'}
                    },
                    gauge={
                        'axis': {
                            'range': [0, max_conn], 
                            'tickmode': 'linear',
                            'tick0': 0,
                            'dtick': 2,
                            'tickwidth': 1.5, 
                            'tickcolor': "#555",
                            'ticks': "inside",
                            'tickfont': {'size': 13, 'color': '#555'}
                        },
                        'bar': {'color': "#007979"},
                        'bgcolor': "#f9fafb",
                        'borderwidth': 0,
                        'steps': [
                            {'range': [0, 6], 'color': '#d1fae5'},
                            {'range': [6, 8], 'color': '#fef3c7'},
                            {'range': [8, 10], 'color': '#fee2e2'}
                        ],
                        'threshold': {
                            'line': {'color': "#b91c1c", 'width': 3},
                            'thickness': 0.8,
                            'value': 9
                        }
                    }
                ))

                fig.update_layout(
                    height=280, 
                    margin=dict(l=20, r=20, t=40, b=15), 
                    paper_bgcolor="rgba(0,0,0,0)"
                )

                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            with cluster_col:
                st.markdown("#### Cluster Monitor")

                def evaluate_node_status(is_connected: bool, is_timeout: bool, active_sockets: int) -> str:
                    if is_timeout:
                        return "🔴 Error: Timeout"
                    if not is_connected:
                        return "🔴 Server Down"
                    if active_sockets == 0:
                        return "🟡 Idle"
                    return "🟢 Healthy"

                raw_nodes_data = [
                    {"pid": "1XXX.XX.X.X1", "sockets": 2, "connected": True,  "timeout": False},
                    {"pid": "1XXX.XX.X.X2", "sockets": 0, "connected": True,  "timeout": False},
                    {"pid": "1XXX.XX.X.X3", "sockets": 0, "connected": False, "timeout": True},
                    {"pid": "1XXX.XX.X.X4", "sockets": 0, "connected": False, "timeout": False}
                ]

                processed_records = []
                for node in raw_nodes_data:
                    computed_status = evaluate_node_status(
                        is_connected=node["connected"],
                        is_timeout=node["timeout"],
                        active_sockets=node["sockets"]
                    )
                    processed_records.append({
                        "PID": node["pid"],
                        "Active Sockets": node["sockets"],
                        "Status": computed_status
                    })

                cluster_df = pd.DataFrame(processed_records)

                st.dataframe(
                    cluster_df,
                    use_container_width=True,
                    hide_index=True,
                    height=180
                )
                
                st.markdown("""
                <div style="display: flex; justify-content: center; gap: 12px; margin-top: 14px;">
                    <div style="display: flex; align-items: center; gap: 8px; padding: 6px 16px; border: 1px solid #e0e4e8; border-radius: 20px; background: #ffffff; font-size: 0.85rem; font-weight: 600; color: #333;">
                        <span style="height: 10px; width: 10px; border-radius: 50%; background-color: #28a745; display: inline-block;"></span>
                        Active
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; padding: 6px 16px; border: 1px solid #e0e4e8; border-radius: 20px; background: #ffffff; font-size: 0.85rem; font-weight: 600; color: #333;">
                        <span style="height: 10px; width: 10px; border-radius: 50%; background-color: #ffc107; display: inline-block;"></span>
                        Idle
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; padding: 6px 16px; border: 1px solid #e0e4e8; border-radius: 20px; background: #ffffff; font-size: 0.85rem; font-weight: 600; color: #333;">
                        <span style="height: 10px; width: 10px; border-radius: 50%; background-color: #dc3545; display: inline-block;"></span>
                        Error
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # --- 4. SECURITY & GATEWAY TELEMETRY (RESTORED 2x2 GRID) ---
        grid_row1_col1, grid_row1_col2 = st.columns(2, gap="large")

        # Card 1: PostgreSQL Engine Health
        with grid_row1_col1:
            with st.container(border=True):
                st.markdown("##### 🛢️ **PostgreSQL Engine Health**")
        
                is_connected = True
                ping_success = True
                db_latency_ms = 15
                db_recycle_state = "Active (1800s pool)"

                if not is_connected or not ping_success or db_latency_ms is None:
                    db_status = "DOWN"
                    status_icon = "✖"
                    status_color = "#dc2626"
                    sub_label = "Connection Lost / Timeout"
                    latency_text = "N/A (Unreachable)"
                    latency_badge_color = "#dc2626"
                elif db_latency_ms > 100:
                    db_status = "DEGRADED"
                    status_icon = "⚠"
                    status_color = "#f59e0b"
                    sub_label = "SELECT 1 (High Latency)"
                    latency_text = f"{db_latency_ms} ms (Slow)"
                    latency_badge_color = "#f59e0b"
                else:
                    db_status = "UP"
                    status_icon = "✔"
                    status_color = "#16a34a"
                    sub_label = "SELECT 1"
                    latency_text = f"{db_latency_ms} ms (Optimal)"
                    latency_badge_color = "#16a34a"

                st.markdown(f"""
                <div style="text-align: center; margin: 16px 0 10px 0;">
                    <div style="font-size: 2.2rem; font-weight: 800; color: {status_color}; display: inline-flex; align-items: center; gap: 8px;">
                        <span>{status_icon}</span> {db_status}
                    </div>
                    <div style="font-size: 0.85rem; color: #6b7280; font-weight: 600; margin-top: -2px;">({sub_label})</div>
                </div>
                <div style="border-top: 1px solid #f0f2f6; padding-top: 14px; margin-top: 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.92rem; margin-bottom: 8px;">
                        <span style="color: #4b5563;">Database Latency:</span>
                        <strong style="color: {latency_badge_color};">{latency_text}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.92rem;">
                        <span style="color: #4b5563;">Recycle State:</span>
                        <span style="color: #374151; font-weight: 600;">{db_recycle_state}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        # Card 2: Idempotency Replay Hit Rate
        with grid_row1_col2:
            with st.container(border=True):
                st.markdown("##### 🗘 **Idempotency Replay Hit Rate**")
                
                replays_blocked = 0

                st.markdown(f"""
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 138px;">
                    <div style="font-size: 3.6rem; font-weight: 800; color: #111827; line-height: 1;">
                        {replays_blocked:,}
                    </div>
                    <div style="font-size: 1rem; font-weight: 600; color: #4b5563; margin-top: 12px;">
                        Replays Short-circuited
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        grid_row2_col1, grid_row2_col2 = st.columns(2, gap="large")

        # Card 3: HTTP Traffic & Error Distribution
        with grid_row2_col1:
            with st.container(border=True):
                st.markdown("##### 🌐 **HTTP Traffic & Error Distribution**")
                
                traffic_labels = ["2xx Success", "4xx Client Errors", "5xx Server Exceptions"]
                traffic_counts = [888, 338, 3]
                traffic_colors = ["#10b981", "#f59e0b", "#ef4444"]

                fig_donut = go.Figure(data=[go.Pie(
                    labels=traffic_labels,
                    values=traffic_counts,
                    hole=0.62,
                    marker=dict(colors=traffic_colors),
                    textinfo="percent",
                    hoverinfo="label+value+percent",
                    showlegend=True
                )])

                fig_donut.update_layout(
                    height=200,
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.1,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=11, color="#4b5563")
                    ),
                    paper_bgcolor="rgba(0,0,0,0)"
                )

                st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

        # Card 4: Security Middleware Status
        with grid_row2_col2:
            with st.container(border=True):
                st.markdown("##### 🛡️ **Security Middleware Status**")

                st.markdown("""
                <div style="text-align: center; margin: 10px 0 14px 0;">
                    <div style="font-size: 2.2rem; font-weight: 800; color: #16a34a; display: inline-flex; align-items: center; gap: 8px;">
                        ✔ ACTIVE
                    </div>
                    <div style="font-size: 0.85rem; color: #6b7280; font-weight: 600; margin-top: -4px;">
                        All Filters Intercepting
                    </div>
                </div>
                <div style="border-top: 1px solid #f0f2f6; padding-top: 12px; display: flex; flex-direction: column; gap: 8px; font-size: 0.9rem; color: #374151;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="color: #16a34a; font-weight: bold;">✔</span> CORS Headers Active
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="color: #16a34a; font-weight: bold;">✔</span> Strict Security Headers (CSP, X-Frame-Options)
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="color: #16a34a; font-weight: bold;">✔</span> Sanitization Filters
                    </div>
                </div>
                """, unsafe_allow_html=True)
    # --------------------------------------------------------------------------
    # TAB 2: PROVISIONING FORM & CLINICIAN DIRECTORY
    # --------------------------------------------------------------------------
    with tab_form:
        # Reset form keys before widgets render to prevent StreamlitAPIException
        if st.session_state.get("trigger_form_clear"):
            keys_to_clear = [
                "doc_first_name", "doc_middle_name", "doc_last_name", "doc_address",
                "doc_prc", "doc_email", "doc_contact", "em_name", "em_contact", "doc_affiliation"
            ]
            for key in keys_to_clear:
                st.session_state[key] = ""
                st.session_state[f"{key}_invalid"] = False
            st.session_state.trigger_form_clear = False

        st.markdown("""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.6rem; line-height: 1;">🩺</span>
                <h3 style="margin: 0; font-size: 1.45rem; font-weight: 700; color: #1e293b; letter-spacing: -0.3px;">Provision Clinician Account</h3>
            </div>
            <p style="margin: 6px 0 16px 0; font-size: 0.92rem; color: #64748b;">Create a verified practitioner profile and register login credentials in the system.</p>
            <div style="height: 1px; width: 100%; background-color: #e2e8f0;"></div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.form_success:
            st.success(st.session_state.form_success)
            st.session_state.form_success = None

        with st.container(border=True):
            first_name = st.text_input("FIRST NAME*", placeholder="Enter first name", key="doc_first_name", on_change=clean_alpha_input, args=("doc_first_name",))
            if st.session_state.get("doc_first_name_invalid"):
                st.error("⛔ Only letters and spaces are permitted.")
            
            last_name = st.text_input("LAST NAME*", placeholder="Enter last name", key="doc_last_name", on_change=clean_alpha_input, args=("doc_last_name",))
            if st.session_state.get("doc_last_name_invalid"):
                st.error("⛔ Only letters and spaces are permitted.")

            row3_col1, row3_col2 = st.columns([1, 3])
            with row3_col1:
                middle_name = st.text_input("MIDDLE NAME", placeholder="Optional", key="doc_middle_name", on_change=clean_alpha_input, args=("doc_middle_name",))
                if st.session_state.get("doc_middle_name_invalid"):
                    st.error("⛔ Only letters permitted.")
            with row3_col2:
                address = st.text_input("ADDRESS*", placeholder="Residential or clinic address", key="doc_address")

            row4_col1, row4_col2, row4_col3, row4_col4 = st.columns([1.5, 2, 1.3, 1])
            with row4_col1:
                specialization = st.selectbox("SPECIALIZATION*", options=SPECIALIZATION_OPTIONS)
            with row4_col2:
                hospital_affiliation = st.text_input("CLINIC AFFILIATION", placeholder="e.g., Manila Doctors Hospital", key="doc_affiliation")
            with row4_col3:
                prc_license_raw = st.text_input("PRC LICENSE*", placeholder="7 digits only", max_chars=7, key="doc_prc", on_change=clean_prc_license, args=("doc_prc",))
                if st.session_state.get("doc_prc_invalid"):
                    st.error("⛔ Digits only.")
            with row4_col4:
                suffix = st.selectbox("SUFFIX*", options=SUFFIX_OPTIONS)

            row5_col1, row5_col2 = st.columns([1.5, 1.5])
            with row5_col1:
                email = st.text_input("EMAIL*", placeholder="strictly @gmail.com", key="doc_email")
                if email and not is_valid_gmail(email):
                    st.error("⛔ Must be a valid Gmail address.")
            with row5_col2:
                contact_number = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="doc_contact", on_change=format_phone_number, args=("doc_contact",))
                doc_digits = "".join(filter(str.isdigit, contact_number))
                if contact_number and len(doc_digits) < 11:
                    st.error(f"⛔ Incomplete ({len(doc_digits)}/11 digits typed).")

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

            st.markdown("#### **CONTACT IN CASE OF EMERGENCY**")
            emergency_name = st.text_input("FULL NAME*", placeholder="Enter emergency contact's full name", key="em_name", on_change=clean_alpha_input, args=("em_name",))
            if st.session_state.get("em_name_invalid"):
                st.error("⛔ Only letters permitted.")
            
            emergency_contact = st.text_input("CONTACT NUMBER*", placeholder="09XX-XXX-XXXX", max_chars=13, key="em_contact", on_change=format_phone_number, args=("em_contact",))
            em_digits = "".join(filter(str.isdigit, emergency_contact))
            if emergency_contact and len(em_digits) < 11:
                st.error(f"⛔ Incomplete ({len(em_digits)}/11 digits typed).")
            
            emergency_relation = st.selectbox("RELATION*", options=RELATION_OPTIONS)

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

            # --- CREDENTIAL DISPATCH & SECURITY ONBOARDING CONTROLS ---
            st.markdown("#### **CREDENTIAL DISPATCH & SECURITY CONTROLS**")
            col_sec1, col_sec2, col_sec3 = st.columns([1.5, 1.5, 1.2])
            with col_sec1:
                send_email_toggle = st.toggle("Automated Onboarding Email", value=True, help="Dispatches temporary login credentials and institutional portal link.")
            with col_sec2:
                require_mfa_toggle = st.toggle("Enforce MFA on First Login", value=True, help="Requires TOTP Authenticator binding before patient charts can be viewed.")
            with col_sec3:
                cred_ttl = st.selectbox("Credential TTL", options=["24 Hours", "48 Hours", "7 Days"], index=0, help="Lifespan of initial temporary password.")

            st.divider()
            submit_btn = st.button("Submit Provisioning", type="primary", use_container_width=True)

        if submit_btn:
            errors = []
        if submit_btn:
            errors = []
            if not first_name.strip():
                errors.append("First Name is required.")
            if not last_name.strip():
                errors.append("Last Name is required.")
            if not address.strip():
                errors.append("Address is required.")
            if len(prc_license_raw) != 7:
                errors.append("PRC License must be exactly 7 digits.")
            if not is_valid_gmail(email):
                errors.append("Valid Gmail address is required.")
            if not is_valid_phone_format(contact_number):
                errors.append("Doctor Contact Number must be exactly 11 digits.")
            if not emergency_name.strip():
                errors.append("Emergency Contact Name is required.")
            if not is_valid_phone_format(emergency_contact):
                errors.append("Emergency Contact Number must be exactly 11 digits.")
            
            formatted_prc = f"PRC {prc_license_raw.strip()}"
            if any(doc["license_number"] == formatted_prc for doc in st.session_state.doctor_directory):
                errors.append(f"License Conflict: `{formatted_prc}` is already registered.")

            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                middle_init = f" {middle_name.strip().title()[0]}." if middle_name.strip() else ""
                formatted_full_name = f"{last_name.strip().title()}, {first_name.strip().title()}{middle_init}"
                
                # Update Clinician Directory
                st.session_state.doctor_directory.append({
                    "doctor_id": len(st.session_state.doctor_directory) + 1,
                    "name": formatted_full_name,
                    "license_number": formatted_prc,
                    "specialization": specialization,
                    "email": email.strip().lower(),
                    "contact_number": contact_number,
                    "hospital_affiliation": hospital_affiliation.strip() or "Lucerna Medica Main Clinic",
                    "is_verified": True,
                    "failed_attempts": 0,
                    "is_locked": False,
                    "mfa_enrolled": False,
                    "token_version": 1
                })

                # Append IAM Audit Log
                st.session_state.doctor_audit_logs.insert(0, {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "target_doctor": formatted_full_name,
                    "event_type": "ACCOUNT_PROVISIONED",
                    "actor": f"Admin ({user_email})",
                    "ip_address": "127.0.0.1",
                    "details": f"TTL: {cred_ttl} | Email Dispatched: {send_email_toggle} | MFA Required: {require_mfa_toggle}"
                })

                st.session_state.trigger_form_clear = True
                # ... (rest of your success and rerun logic)

       # ======================================================================
        # PART 2: SEARCHABLE CLINICIAN DATABASE & DIRECTORY
        # ======================================================================
        with st.container(border=True):
            st.markdown("### 📋 Clinician Database & Directory")
            st.caption("Inspect, filter, and manage provisioned clinical accounts.")
            
            raw_df = pd.DataFrame(st.session_state.doctor_directory)

            if not raw_df.empty:
                f_col_search, f_col_spec, f_col_status = st.columns([2.5, 2, 1.5])
                
                with f_col_search:
                    search_query = st.text_input(
                        "Search Clinician", 
                        placeholder="Search by name, license #, or email...", 
                        label_visibility="collapsed"
                    )
                with f_col_spec:
                    selected_specialties = st.multiselect(
                        "Filter by Specialization", 
                        options=SPECIALIZATION_OPTIONS, 
                        placeholder="All Specialties", 
                        label_visibility="collapsed"
                    )
                with f_col_status:
                    status_filter = st.radio(
                        "Status Filter", 
                        options=["All", "Verified", "Pending"], 
                        horizontal=True, 
                        label_visibility="collapsed"
                    )

                filtered_df = raw_df.copy()
                
                if search_query:
                    query = search_query.lower()
                    filtered_df = filtered_df[
                        filtered_df["name"].str.lower().str.contains(query) |
                        filtered_df["license_number"].str.lower().str.contains(query) |
                        filtered_df["email"].str.lower().str.contains(query)
                    ]
                
                if selected_specialties:
                    filtered_df = filtered_df[filtered_df["specialization"].isin(selected_specialties)]
                
                if status_filter == "Verified":
                    filtered_df = filtered_df[filtered_df["is_verified"] == True]
                elif status_filter == "Pending":
                    filtered_df = filtered_df[filtered_df["is_verified"] == False]

                display_df = filtered_df.copy()
                display_df["status_badge"] = display_df["is_verified"].apply(lambda v: "🟢 Verified" if v else "🟡 Pending")
                display_df["lock_badge"] = display_df["is_locked"].apply(lambda l: "🔒 Locked" if l else "🟢 Normal")

                st.dataframe(
                    display_df[["name", "license_number", "specialization", "contact_number", "email", "hospital_affiliation", "status_badge", "lock_badge"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "name": st.column_config.TextColumn("Clinician Name", width="medium"),
                        "license_number": st.column_config.TextColumn("License Number", width="small"),
                        "specialization": st.column_config.TextColumn("Specialization", width="medium"),
                        "contact_number": st.column_config.TextColumn("Contact Phone", width="small"),
                        "email": st.column_config.TextColumn("Institutional Email", width="medium"),
                        "hospital_affiliation": st.column_config.TextColumn("Affiliation", width="medium"),
                        "status_badge": st.column_config.TextColumn("Verification", width="small"),
                        "lock_badge": st.column_config.TextColumn("Access State", width="small")
                    },
                    height=240
                )

                st.divider()

                # --- ACCOUNT GOVERNANCE ACTIONS PANEL ---
                st.markdown("##### ⚙️ **Account Governance & Security Controls**")
                doctor_options = {doc["doctor_id"]: f"{doc['name']} ({doc['license_number']})" for doc in st.session_state.doctor_directory}
                selected_doc_id = st.selectbox("Select Clinician to Manage:", options=list(doctor_options.keys()), format_func=lambda x: doctor_options[x])
                
                target_doc = next((d for d in st.session_state.doctor_directory if d["doctor_id"] == selected_doc_id), None)

                if target_doc:
                    action_col1, action_col2, action_col3 = st.columns(3)
                    
                    with action_col1:
                        st.markdown(f"**Failed Logins:** `{target_doc['failed_attempts']}/5`")
                        if target_doc["is_locked"]:
                            st.warning("⚠️ Account locked.")
                            if st.button("🔓 Clear Lockout", use_container_width=True):
                                target_doc["is_locked"] = False
                                target_doc["failed_attempts"] = 0
                                st.success(f"Unlocked account for {target_doc['name']}.")
                                st.rerun()
                        else:
                            st.info("Account is in good standing.")

                    with action_col2:
                        st.markdown("**Credential Reset:**")
                        if st.button("🔑 Dispatch Reset OTP", use_container_width=True):
                            st.success(f"One-time reset dispatched to {target_doc['email']}.")

                    with action_col3:
                        st.markdown(f"**Session Version:** `v{target_doc['token_version']}`")
                        if st.button("🛑 Revoke Active Sessions", use_container_width=True):
                            target_doc["token_version"] += 1
                            st.warning(f"All active bearer tokens invalidated for {target_doc['name']}.")
                            st.rerun()
            else:
                st.info("No clinician records found.")

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # --- NON-CLINICAL DOCTOR AUDIT LOGS ---
        with st.container(border=True):
            st.markdown("### 🛡️ Non-Clinical Identity & Security Audit Trail")
            audit_df = pd.DataFrame(st.session_state.doctor_audit_logs)
            if not audit_df.empty:
                st.dataframe(audit_df, use_container_width=True, hide_index=True, height=240)
            else:
                st.info("No security audit events recorded.")
                          

    # --------------------------------------------------------------------------
    # TAB 3: ACCOUNT DIRECTORY
    # --------------------------------------------------------------------------
    with tab_account:
        raw_patients_df = pd.DataFrame(st.session_state.patient_directory)

        # ======================================================================
        # TIER 1: PENDING VERIFICATION QUEUE
        # ======================================================================
        with st.container(border=True):
            st.markdown("### 🕒 Tier 1: Pending Verification Queue")
            st.caption("Newly registered patients awaiting email confirmation or SMS OTP activation.")

            if not raw_patients_df.empty:
                pending_df = raw_patients_df[raw_patients_df["is_verified"] == False].copy()

                if not pending_df.empty:
                    st.dataframe(
                        pending_df[["name", "email", "contact_number", "registered_at", "pending_method", "dispatch_count"]],
                        use_container_width=True, hide_index=True,
                        column_config={
                            "name": "Full Name", "email": "Gmail Address", "contact_number": "Contact Number",
                            "registered_at": "Registered At", "pending_method": "Pending Method", "dispatch_count": "Dispatches"
                        },
                        height=150
                    )
                    
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        if st.button("🔄 Resend Link / OTP", use_container_width=True):
                            st.success("Verification tokens re-dispatched.")
                    with col_p2:
                        if st.button("✅ Manual Authorization", use_container_width=True):
                            st.success("Patient manually verified.")
                    with col_p3:
                        if st.button("🗑️ Purge Expired Requests", use_container_width=True):
                            st.warning("Expired registrations purged.")
                else:
                    st.info("Queue is clear. No pending verifications.")

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # ======================================================================
        # TIER 2: MASTER PATIENT DIRECTORY & GOVERNANCE PANEL
        # ======================================================================
        with st.container(border=True):
            st.markdown("### 🗃️ Tier 2: Master Patient Directory")
            st.caption("Manage active accounts, enforce HIPAA compliance, and control access states.")

            if not raw_patients_df.empty:
                f_col_search, f_col_status, f_col_hipaa = st.columns([2.5, 1.5, 1.5])
                with f_col_search:
                    p_search_query = st.text_input("Search Patient", placeholder="Search by name, email, or phone...", label_visibility="collapsed")
                with f_col_status:
                    p_status_filter = st.radio("Status Filter", options=["All", "Active", "Pending", "Suspended"], horizontal=True, label_visibility="collapsed")
                with f_col_hipaa:
                    p_hipaa_filter = st.radio("HIPAA State", options=["All", "Consented", "Pending"], horizontal=True, label_visibility="collapsed")

                # Filter Engine
                p_filtered_df = raw_patients_df.copy()
                if p_search_query:
                    q = p_search_query.lower()
                    p_filtered_df = p_filtered_df[p_filtered_df["name"].str.lower().str.contains(q) | p_filtered_df["email"].str.lower().str.contains(q) | p_filtered_df["contact_number"].str.contains(q)]
                
                if p_status_filter == "Active":
                    p_filtered_df = p_filtered_df[(p_filtered_df["is_active"] == True) & (p_filtered_df["is_locked"] == False)]
                elif p_status_filter == "Pending":
                    p_filtered_df = p_filtered_df[p_filtered_df["is_verified"] == False]
                elif p_status_filter == "Suspended":
                    p_filtered_df = p_filtered_df[(p_filtered_df["is_active"] == False) | (p_filtered_df["is_locked"] == True)]

                if p_hipaa_filter == "Consented":
                    p_filtered_df = p_filtered_df[p_filtered_df["hipaa_consent"] == True]
                elif p_hipaa_filter == "Pending":
                    p_filtered_df = p_filtered_df[p_filtered_df["hipaa_consent"] == False]

                # Badges
                p_display_df = p_filtered_df.copy()
                p_display_df["hipaa_badge"] = p_display_df["hipaa_consent"].apply(lambda v: "📝 Consented" if v else "⏳ Pending")
                
                def get_account_state(row):
                    if not row["is_verified"]: return "🟡 Pending"
                    if row["is_locked"]: return "🔒 Locked"
                    if not row["is_active"]: return "🔴 Suspended"
                    return "🟢 Active"
                
                p_display_df["account_state"] = p_display_df.apply(get_account_state, axis=1)

                st.dataframe(
                    p_display_df[["name", "email", "contact_number", "dob", "hipaa_badge", "account_state"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "name": "Patient Name", "email": "Gmail Address", "contact_number": "Contact Phone",
                        "dob": "Date of Birth", "hipaa_badge": "HIPAA Status", "account_state": "Account State"
                    },
                    height=240
                )

                st.divider()

                # --- SINGLE-TARGET GOVERNANCE PANEL ---
                st.markdown("##### ⚙️ **Account Governance Panel**")
                patient_options = {p["patient_id"]: f"{p['name']} ({p['email']})" for p in st.session_state.patient_directory}
                selected_patient_id = st.selectbox("Select Patient to Manage:", options=list(patient_options.keys()), format_func=lambda x: patient_options[x])
                
                target_patient = next((p for p in st.session_state.patient_directory if p["patient_id"] == selected_patient_id), None)

                if target_patient:
                    act_col1, act_col2, act_col3 = st.columns(3)
                    
                    with act_col1:
                        st.markdown(f"**Lockout Control:** `{target_patient['failed_attempts']}/5` failed attempts")
                        if st.button("🔓 Reset Failed Attempts", use_container_width=True, disabled=target_patient['failed_attempts'] == 0):
                            st.success(f"Counter reset for {target_patient['name']}.")
                    
                    with act_col2:
                        st.markdown("**Credential Dispatch:**")
                        if st.button("🔑 Dispatch Secure Reset Link", use_container_width=True):
                            st.success(f"Reset link sent to {target_patient['email']}.")
                    
                    with act_col3:
                        st.markdown("**Access Freeze:**")
                        if target_patient["is_active"]:
                            if st.button("🛑 Suspend Account", use_container_width=True):
                                st.warning(f"Account suspended for {target_patient['name']}.")
                        else:
                            if st.button("✅ Restore Access", use_container_width=True):
                                st.success(f"Access restored for {target_patient['name']}.")

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # ======================================================================
        # TIER 3: PATIENT IAM & COMPLIANCE AUDIT TRAIL
        # ======================================================================
        with st.container(border=True):
            st.markdown("### 🛡️ Tier 3: Patient IAM & Compliance Audit Trail")
            st.caption("Immutable system event log recording security operations and HIPAA consent milestones.")

            p_audit_df = pd.DataFrame(st.session_state.patient_audit_logs)
            if not p_audit_df.empty:
                st.dataframe(
                    p_audit_df,
                    use_container_width=True, hide_index=True,
                    column_config={
                        "timestamp": "Timestamp (UTC)", "target_patient": "Target Patient", 
                        "event_type": "Security Event", "actor": "Triggered By", 
                        "ip_address": "Client IP", "details": st.column_config.TextColumn("Telemetry Payload", width="large")
                    },
                    height=240
                )
            else:
                st.info("No audit events recorded.")