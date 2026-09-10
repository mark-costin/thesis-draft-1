import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(layout="wide")

# ==============================================================================
# PROFILE / USER VARIABLES (Ready for DB integration)
# ==============================================================================
user_avatar_url = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80"
user_role = "ADMIN"
user_name = "First Name"
user_email = "admin.system@lucernamedica.com"

# ==============================================================================
# DASHBOARD & HEADER CSS STYLING
# ==============================================================================
st.markdown(f"""
    <style>
    /* Global Theming & Tabs */
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

    /* --- PROFILE POPOVER & HEADER BUTTON FIXES --- */
    div[data-testid="stVerticalBlock"] > div > div > div > div > button {{
        height: 52px !important;
        border-radius: 8px !important;
        border: 1px solid #d0d7de !important;
        background-color: white !important;
    }}
    
    div[data-testid="stPopover"] > button {{
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        padding: 6px 12px !important;
        height: 52px !important;
    }}
    
    /* Target the icon container, hide emoji, and apply avatar image */
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

    /* --- DASHBOARD METRIC CARDS --- */
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
    
    /* Custom Legend UI */
    .status-legend {{
        display: flex;
        justify-content: center;
        gap: 24px;
        padding: 12px;
        margin-top: 10px;
        border: 1px solid #e0e4e8;
        border-radius: 8px;
        background: #ffffff;
    }}
    .status-legend div {{
        display: flex;
        align-items: center;
        font-size: 0.9rem;
        font-weight: 600;
        color: #444;
    }}
    .dot {{
        height: 12px;
        width: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# MAIN APP LAYOUT (10 | 80 | 10)
# ==============================================================================
_, col_main, _ = st.columns([10, 80, 10])

with col_main:
    # --- TOP HEADER ROW ---
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
                st.divider()
                st.markdown("**Theme Preference**")
                th_c1, th_c2 = st.columns(2)
                th_c1.button("☀️ Light", use_container_width=True)
                th_c2.button("🌙 Dark", use_container_width=True)
                st.divider()
                if st.button("⏻ Log Out", type="primary", use_container_width=True):
                    st.session_state.authenticated = False
                    st.rerun()

    # --- MAIN TABS ---
    tab_metric, tab_form, tab_account = st.tabs(["METRIC", "FORM", "ACCOUNTS"])

    # --------------------------------------------------------------------------
    # TAB 1: METRICS DASHBOARD
    # --------------------------------------------------------------------------
    with tab_metric:
        st.write("") 

        # --- 1. SUMMARY METRIC CARDS (TOP) ---
        with st.container(border=True):
            st.markdown("<div style='margin-top: 35px;'></div>", unsafe_allow_html=True)   

            col_left, col_right = st.columns([1.5, 1], gap="large")

            # Left Panel
            with col_left:
                r1_left, = st.columns(1)
                with r1_left:
                    st.markdown("""
                    <div class="metric-card big-card">
                        <div class="b-num">0</div>
                        <div class="b-lbl">Total accounts</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

                r2_left1, r2_left2 = st.columns(2, gap="large")
                with r2_left1:
                    st.markdown("""
                    <div class="metric-card left-small">
                        <div class="s-num">0</div>
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

            # Right Panel
            with col_right:
                r1_right1, r1_right2 = st.columns(2, gap="large")
                with r1_right1:
                    st.markdown("""
                    <div class="metric-card right-small">
                        <div class="s-num">0</div>
                        <div class="s-lbl">Doctors</div>
                    </div>
                    """, unsafe_allow_html=True)
                with r1_right2:
                    st.markdown("""
                    <div class="metric-card right-small">
                        <div class="s-num">0</div>
                        <div class="s-lbl">Admins</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

                r2_right1, r2_right2 = st.columns(2, gap="large")
                with r2_right1:
                    st.markdown("""
                    <div class="metric-card right-small">
                        <div class="s-num">0</div>
                        <div class="s-lbl">Patients</div>
                    </div>
                    """, unsafe_allow_html=True)
                with r2_right2:
                    st.markdown("<div style='height: 195px; width: 100%; opacity: 0;'></div>", unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom: 50px;'></div>", unsafe_allow_html=True)    

        # --- 2. INTAKE ACTIVITY OVER TIME CHART (MIDDLE) ---
        with st.container(border=True):
            st.markdown("##### **INTAKE ACTIVITY OVER TIME**")
            st.caption("Activity tracking for Patients, Doctors, and Admin's accounts")

            chart_data = pd.DataFrame({
                "Patients": [0, 0, 20, 0, 0, 0, 0],
                "Doctors": [10, 0, 200, 0, 300, 30, 0],
                "Admins": [10, 0, 0, 300, 0, 0, 0]
            }, index=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])

            st.line_chart(chart_data, height=350, use_container_width=True)

        # --- 3. CONNECTION POOL & CLUSTER MONITOR (BOTTOM) ---
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
                    mode = "gauge+number",
                    value = active_conn,
                    number = {
                        'suffix': f" / {max_conn}", 
                        'font': {'size': 36, 'color': '#111827'}
                    },
                    title = {
                        'text': (
                            f"<b>Active Connections</b><br>"
                            f"<span style='font-size:14px; color:#6b7280;'>Utilization: {utilization_pct}%</span> • "
                            f"<span style='font-size:14px; font-weight:bold; color:{load_color};'>{load_level} Load</span>"
                        ),
                        'font': {'size': 18, 'color': '#1f2937'}
                    },
                    gauge = {
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

        # --- 4. SECURITY & GATEWAY TELEMETRY (2x2 GRID) ---
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
        SPECIALIZATION_OPTIONS = [
            "General Physician",
            "Internal Medicine",
            "Cardiology",
            "Pulmonology",
            "Psychiatry",
        ]

        if "doctor_directory" not in st.session_state:
            st.session_state.doctor_directory = [
                {
                    "doctor_id": 1,
                    "name": "Smith, John M.",
                    "license_number": "PRC-123456",
                    "specialization": "General Practice",
                    "email": "doc.smith@hospital.com",
                    "contact_number": "09171234567",
                    "hospital_affiliation": "Lucerna Central Hospital",
                    "is_verified": True
                },
                {
                    "doctor_id": 2,
                    "name": "Velasco, Maria A.",
                    "license_number": "PRC-883921",
                    "specialization": "Cardiology",
                    "email": "m.velasco@cardio.med",
                    "contact_number": "09209876543",
                    "hospital_affiliation": "Metropolitan Heart Center",
                    "is_verified": False
                }
            ]

        # --- PART 1: DOCTOR PROVISIONING FORM ---
        with st.container(border=True):
            st.markdown("### 🩺 Provision Clinician Account")
            st.caption("Create a verified practitioner profile and register login credentials in the system.")

            with st.form(key="doctor_provision_form", clear_on_submit=True):
                # Section A: Clinician Identity (Row 1)
                st.markdown("##### **Clinician Identity**")
                col_f_name, col_m_name, col_l_name, col_suffix = st.columns([2.5, 2, 2.5, 1.2])

                with col_f_name:
                    first_name = st.text_input("First Name *", placeholder="e.g., Jonathan", max_chars=50)
                with col_m_name:
                    middle_name = st.text_input("Middle Name", placeholder="e.g., Arthur", max_chars=50)
                with col_l_name:
                    last_name = st.text_input("Last Name *", placeholder="e.g., Reyes", max_chars=50)
                with col_suffix:
                    suffix = st.selectbox("Suffix", options=["None", "MD", "DO", "PhD", "Jr.", "Sr."])

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

                # Section B: Professional Credentials (Row 2)
                st.markdown("##### **Professional Credentials**")
                col_lic, col_spec, col_affil = st.columns([1.8, 2, 2.2])

                with col_lic:
                    license_number = st.text_input("PRC / Medical License # *", placeholder="e.g., PRC-0098412", max_chars=50)
                with col_spec:
                    specialization = st.selectbox("Specialization *", options=SPECIALIZATION_OPTIONS)
                with col_affil:
                    hospital_affiliation = st.text_input("Hospital / Clinic Affiliation", value="Lucerna Medica Main Clinic", max_chars=150)

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

                # Section C: Contact & Access Privileges (Row 3)
                st.markdown("##### **Contact & Account Privileges**")
                col_email, col_phone, col_verify = st.columns([2.2, 1.8, 1.5], vertical_alignment="center")

                with col_email:
                    email = st.text_input("Institutional Email *", placeholder="doctor@lucernamedica.com", max_chars=100)
                with col_phone:
                    contact_number = st.text_input("Contact Number *", placeholder="e.g., 09171234567", max_chars=15)
                with col_verify:
                    is_verified = st.toggle("Instant Verification", value=True, help="Active accounts receive immediate system access. Uncheck to mark as Pending background check.")

                st.divider()

                # Auto-generated preview metadata
                cleaned_last_name = re.sub(r'[^a-zA-Z0-9]', '', last_name.lower()) if last_name else "lastname"
                suggested_username = f"doc_{cleaned_last_name}"
                st.caption(f"**Auto-Generated User Handle:** `{suggested_username}` • **Assigned Role:** `DOCTOR`")

                col_spacer, col_submit = st.columns([3.5, 1.5])
                with col_submit:
                    submit_btn = st.form_submit_button(
                        label="Provision Clinician", 
                        type="primary", 
                        use_container_width=True
                    )

            # --- Form Submission Handling ---
            if submit_btn:
                required_fields = [first_name.strip(), last_name.strip(), license_number.strip(), email.strip(), contact_number.strip()]
                
                if not all(required_fields):
                    st.error("Please complete all required fields marked with an asterisk (*).")
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", email.strip()):
                    st.error("Please enter a valid institutional email address.")
                elif any(doc["license_number"] == license_number.strip() for doc in st.session_state.doctor_directory):
                    st.error(f"License Conflict: `{license_number.strip()}` is already registered to an existing clinician.")
                else:
                    payload = {
                        "first_name": first_name.strip(),
                        "middle_name": middle_name.strip() or None,
                        "last_name": last_name.strip(),
                        "suffix": None if suffix == "None" else suffix,
                        "license_number": license_number.strip(),
                        "specialization": specialization,
                        "hospital_affiliation": hospital_affiliation.strip() or None,
                        "email": email.strip(),
                        "contact_number": contact_number.strip(),
                        "is_verified": is_verified,
                        "role": "DOCTOR"
                    }

                    middle_init = f" {middle_name.strip()[0]}." if middle_name.strip() else ""
                    formatted_name = f"{last_name.strip()}, {first_name.strip()}{middle_init}"
                    
                    st.session_state.doctor_directory.append({
                        "doctor_id": len(st.session_state.doctor_directory) + 1,
                        "name": formatted_name,
                        "license_number": license_number.strip(),
                        "specialization": specialization,
                        "email": email.strip(),
                        "contact_number": contact_number.strip(),
                        "hospital_affiliation": hospital_affiliation.strip(),
                        "is_verified": is_verified
                    })
                    
                    st.success(f"Successfully provisioned **Dr. {first_name.strip()} {last_name.strip()}** (`{suggested_username}`).")
                    st.rerun()

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # --- PART 2: SEARCHABLE DOCTOR DIRECTORY ---
        with st.container(border=True):
            st.markdown("### 📋 Clinician Directory")
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
                display_df["status_badge"] = display_df["is_verified"].apply(
                    lambda v: "🟢 Verified" if v else "🟡 Pending"
                )

                st.dataframe(
                    display_df[[
                        "name", 
                        "license_number", 
                        "specialization", 
                        "contact_number", 
                        "email", 
                        "hospital_affiliation", 
                        "status_badge"
                    ]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "name": st.column_config.TextColumn("Clinician Name", width="medium"),
                        "license_number": st.column_config.TextColumn("License Number", width="small"),
                        "specialization": st.column_config.TextColumn("Specialization", width="medium"),
                        "contact_number": st.column_config.TextColumn("Contact Phone", width="small"),
                        "email": st.column_config.TextColumn("Institutional Email", width="medium"),
                        "hospital_affiliation": st.column_config.TextColumn("Affiliation", width="medium"),
                        "status_badge": st.column_config.TextColumn("Status", width="small")
                    },
                    height=280
                )
                st.caption(f"Showing **{len(display_df)}** of **{len(raw_df)}** total registered clinicians.")
            else:
                st.info("No clinician records found. Use the form above to provision the first account.")

    # --------------------------------------------------------------------------
    # TAB 3: ACCOUNT DIRECTORY
    # --------------------------------------------------------------------------
    with tab_account:
        st.info("Account Management directory goes here.")