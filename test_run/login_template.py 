import streamlit as st

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(layout="wide")

# ==============================================================================
# TAB & CONTAINER CSS STYLING ONLY
# ==============================================================================
st.markdown("""
    <style>
    /* Global Theming & Accents */
    [data-testid="baseButton-secondary"]:hover, 
    [data-testid="baseButton-secondary"]:focus, 
    [data-testid="baseButton-secondary"]:active { 
        border-color: #007979 !important; 
        color: #007979 !important; 
    }
    
    /* Tabs Stretching */
    [data-baseweb="tab-list"] { 
        display: flex !important; 
        width: 100% !important; 
        margin-top: 12px !important; 
    }
    [data-testid="stTab"] { 
        flex: 1 !important; 
        justify-content: center !important; 
    }
    [data-testid="stTab"] * { 
        font-size: 1.35rem !important; 
        font-weight: 900 !important; 
        letter-spacing: 0.5px !important; 
    }
    [aria-selected="true"] * { 
        color: #007979 !important; 
    }
    [data-baseweb="tab-highlight"] { 
        background-color: #007979 !important; 
        height: 3px !important; 
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# MAIN APP LAYOUT (20 | 60 | 20)
# ==============================================================================
_, col_main, _ = st.columns([20, 60, 20])

with col_main:
    with st.container(border=True):
        # Header text
        st.markdown(
            "<h2 style='text-align:center; margin:0;'>Welcome to Lucerna Medica!</h2>"
            "<p style='text-align:center; color:#666; margin: 6px 0 16px 0;'>A simple, secure way for patients, doctors, and staff to stay connected.</p>",
            unsafe_allow_html=True,
        )

        # --- ISOLATED TABS ---
        tab_login, tab_reg = st.tabs(["Log In", "Patient Registration"])

        with tab_login:
            st.info("Log In form components will go here.")

        with tab_reg:
            st.info("Patient Registration form components will go here.")