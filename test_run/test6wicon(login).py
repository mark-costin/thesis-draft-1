import base64, os, streamlit as st

st.set_page_config(layout="centered")

# --- SMART ASSET LOCATOR ---
def get_icon(f):
    d = os.path.dirname(os.path.abspath(__file__))
    # Checks multiple possible paths to guarantee it finds your assets folder
    for p in [f"{d}/../assets/{f}", f"{d}/assets/{f}", f"assets/{f}"]:
        if os.path.exists(p): return base64.b64encode(open(p, "rb").read()).decode()
    return ""

c_b64, o_b64 = get_icon("close_l.png"), get_icon("open_l.png")

# --- COMPACT CSS STYLING ---
st.markdown(f"""
    <style>
    /* Hide hints & native SVGs */
    [data-testid*="stInputInstructions"] {{ display: none !important; }}
    div[data-testid="stTextInput"] button * {{ display: none !important; opacity: 0 !important; }}
    div[data-testid="stTextInput"] button::after, div[data-testid="stTextInput"] button::before {{ display: none !important; }}
    
    /* Custom Icon Rightmost Alignment */
    div[data-testid="stTextInput"] > div > div {{ position: relative !important; }}
    div[data-testid="stTextInput"] button {{
        position: absolute !important; right: 0.6rem !important; top: 50% !important; transform: translateY(-50%) !important;
        display: flex !important; border: none !important; width: 1.25rem !important; height: 1.25rem !important; z-index: 2 !important; padding: 0 !important;
        background-color: transparent !important; background-repeat: no-repeat !important; background-position: center !important; background-size: contain !important;
    }}
    button[aria-label*="how password"], button[title*="how password"] {{ background-image: url('data:image/png;base64,{c_b64}') !important; }}
    button[aria-label*="ide password"], button[title*="ide password"] {{ background-image: url('data:image/png;base64,{o_b64}') !important; }}
    .stTextInput input {{ background-color: #f0f2f6 !important; padding-right: 2.5rem !important; }}
    
    /* Global Theming */
    [data-testid="baseButton-secondary"]:hover, [data-testid="baseButton-secondary"]:focus, [data-testid="baseButton-secondary"]:active {{ border-color: #007979 !important; color: #007979 !important; }}
    [data-baseweb="tab-list"] {{ display: flex !important; width: 100% !important; margin-top: 12px !important; }}
    [data-testid="stTab"] {{ flex: 1 !important; justify-content: center !important; }}
    [data-testid="stTab"] * {{ font-size: 1.35rem !important; font-weight: 900 !important; letter-spacing: 0.5px !important; }}
    [aria-selected="true"] * {{ color: #007979 !important; }}
    [data-baseweb="tab-highlight"] {{ background-color: #007979 !important; height: 3px !important; }}
    
    /* Radios Stretching */
    [data-testid="stElementContainer"], [data-testid="stRadio"], [data-testid="stRadio"]>div, [data-testid="stRadio"]>div>div {{ width: 100% !important; }}
    [role="radiogroup"] {{ display: flex !important; width: 100% !important; gap: 10px !important; }}
    [role="radiogroup"] > label {{ display: flex !important; align-items: center !important; justify-content: center !important; flex: 1 !important; background: #f8f9fa; border-radius: 6px; border: 1px solid #d0d0d0; padding: 10px 0 !important; margin: 0 !important; }}
    </style>
""", unsafe_allow_html=True)

if "err" not in st.session_state: st.session_state.err = False

# --- MAIN APP LAYOUT ---
with st.container(border=True):
    st.markdown("<h2 style='text-align:center; margin:0;'>Welcome to the Health Hub</h2><p style='text-align:center; color:#666; margin: 6px 0 16px 0;'>A simple, secure way for patients, doctors, and staff to stay connected.</p>", unsafe_allow_html=True)

    tab_login, tab_reg = st.tabs(["Log In", "Patient Registration"])

    with tab_login:
        with st.container(border=True):
            st.markdown("##### **Account Type**")
            role = st.radio("Role", ["ADMIN", "DOCTOR", "PATIENT"], horizontal=True, label_visibility="collapsed")
            
        with st.container(border=True):
            st.markdown("##### **Username**")
            user = st.text_input("User", placeholder="username", label_visibility="collapsed")
            
            st.markdown("##### **Password**")
            pwd = st.text_input("Pwd", placeholder="password", type="password", label_visibility="collapsed")

            if st.session_state.err and not (user and pwd):
                st.error("Please fill in all missing fields before confirming!")
            
            st.write("") # Spacer
            if st.columns([1, 2, 1])[1].button("Confirm", use_container_width=True):
                st.session_state.err = not (user and pwd)
                if st.session_state.err:
                    st.rerun()
                else:
                    st.success(f"Logged in as {role}: {user}")

    with tab_reg:
        with st.container(border=True):
            st.info("Registration contents go here.")