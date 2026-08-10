import streamlit as st

st.set_page_config(layout="centered")

# ==============================================================================
# 1. COMPACT CSS STYLING
# ==============================================================================
st.markdown(
    """
    <style>
    /* -------------------------------------------------------------------------- */
    /* HIDE 'PRESS ENTER TO APPLY' HINT & STYLE PASSWORD EYE                      */
    /* -------------------------------------------------------------------------- */
    [data-testid="stInputInstructions"],
    div[data-testid="stInputInstructions"],
    small[data-testid="stInputInstructions"] {
        display: none !important;
    }
    
    button[aria-label="Show password text"],
    button[aria-label="Hide password text"] {
        color: #007979 !important; 
    }

    /* -------------------------------------------------------------------------- */
    /* FORCE BUTTON HOVER TO TEAL (DESTROY DEFAULT RED HOVER)                     */
    /* -------------------------------------------------------------------------- */
    [data-testid="baseButton-secondary"]:hover,
    [data-testid="baseButton-secondary"]:focus,
    [data-testid="baseButton-secondary"]:active {
        border-color: #007979 !important;
        color: #007979 !important;
    }

    /* -------------------------------------------------------------------------- */
    /* TABS & RADIOS LAYOUT STRETCHING                                            */
    /* -------------------------------------------------------------------------- */
    /* TABS: 50/50 Stretch + Big Bold Fonts */
    [data-baseweb="tab-list"] { display: flex !important; width: 100% !important; margin-top: 12px !important;}
    [data-testid="stTab"] { flex: 1 !important; justify-content: center !important; }
    [data-testid="stTab"] * { font-size: 1.35rem !important; font-weight: 900 !important; letter-spacing: 0.5px !important; }
    [aria-selected="true"] * { color: #007979 !important; }
    [data-baseweb="tab-highlight"] { background-color: #007979 !important; height: 3px !important; }

    /* RADIOS: 33.3% Spread & Centered Content */
    [data-testid="stElementContainer"], [data-testid="stRadio"], [data-testid="stRadio"]>div, [data-testid="stRadio"]>div>div { width: 100% !important; }
    [role="radiogroup"] { display: flex !important; width: 100% !important; gap: 10px !important; }
    
    [role="radiogroup"] > label { 
        display: flex !important; 
        align-items: center !important; 
        justify-content: center !important; 
        flex: 1 !important; 
        background: #f8f9fa; 
        border-radius: 6px; 
        border: 1px solid #d0d0d0; 
        padding: 10px 0 !important; 
        margin: 0 !important; 
    }

    /* INPUTS: Gray background */
    .stTextInput input { background-color: #f0f2f6; }
    </style>
    """,
    unsafe_allow_html=True
)

if "err" not in st.session_state: 
    st.session_state.err = False

# ==============================================================================
# 2. MAIN APP LAYOUT
# ==============================================================================
with st.container(border=True):
    
    # --- HEADER LAYER ---
    with st.container(border=False):
        st.markdown(
            """
            <h2 style='text-align:center; margin:0;'>Welcome to the Health Hub</h2>
            <p style='text-align:center; color:#666; margin: 6px 0 16px 0;'>
                A simple, secure way for patients, doctors, and staff to stay connected.
            </p>
            """, 
            unsafe_allow_html=True
        )

    # --- TAB LAYER ---
    with st.container(border=False):
        tab_login, tab_reg = st.tabs(["Log In", "Patient Registration"])

        # --- LOG IN TAB ---
        with tab_login:
            
            # ACCOUNT TYPE LAYER
            with st.container(border=True):
                st.markdown("##### **Account Type**")
                role_con = st.radio("Role", ["ADMIN", "DOCTOR", "PATIENT"], horizontal=True, label_visibility="collapsed")

            # CREDENTIALS LAYER
            with st.container(border=True):
                st.markdown("##### **Username**")
                user_con = st.text_input("User", placeholder="username", label_visibility="collapsed")
                
                st.markdown("##### **Password**")
                pass_con = st.text_input("Pwd", placeholder="password", type="password", label_visibility="collapsed")

                # Validation & Confirmation
                if st.session_state.err and not (user_con and pass_con):
                    st.error("Please fill in all missing fields before confirming!")

                st.write("") # Spacer
                _, center_col, _ = st.columns([1, 2, 1])
                
                if center_col.button("confirm...", use_container_width=True):
                    if not (user_con and pass_con):
                        st.session_state.err = True
                        st.rerun()
                    else:
                        st.session_state.err = False
                        st.success(f"Logged in as {role_con}: {user_con}")

        # --- REGISTER TAB ---
        with tab_reg:
            with st.container(border=True):
                st.info("Registration contents go here.")