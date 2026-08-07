import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Healthcare Portal",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 1. SLEEK MEDICAL THEME & OVERRIDE CSS ---
st.markdown("""
    <style>
    /* Center and constrain layout width */
    .block-container {
        padding-top: 3rem;
        max-width: 480px;
    }
    
    /* 100% KILL THE RED: Override Radio Button Dot Color to Healthcare Blue */
    div[role="radiogroup"] label > div:first-child {
        background-color: #38bdf8 !important;
        border-color: #38bdf8 !important;
    }
    [data-baseweb="radio"] input:checked + div {
        background-color: #38bdf8 !important;
        border-color: #38bdf8 !important;
    }
    
    /* Center the Radio Buttons inside the box */

    div[role="radiogroup"] {
       justify-content: center !important;
       gap: 20px !important;
       margin-bottom: 10px !important;
    }

    /* Input border focus color (Blue instead of Red) */
    div[data-baseweb="input"]:focus-within {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 1px #38bdf8 !important;
    }
    input::placeholder {
        color: #64748b !important;
    }
    
    /* Style the main container as ONE unified floating card */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4);
    }
    
    /* Remove double border from form inside container */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        background: transparent !important;
    }
    
    /* Custom Medical-Blue Gradient Submit Button */
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: #ffffff;
        border: 1px solid #0284c7;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.6rem 1rem;
        transition: all 0.2s ease-in-out;
    }
    [data-testid="stFormSubmitButton"] button:hover {
        background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
        border-color: #38bdf8;
        color: #f8fafc;
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2);
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CREDENTIALS DATABASE ---
USER_DB = {
    "Admin": {"admin": "admin123"},
    "Doctor": {"dr_smith": "doctor123"},
    "Patient": {"john_doe": "patient123"}
}

# --- 3. SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user" not in st.session_state:
    st.session_state["user"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""
if "error_msg" not in st.session_state:
    st.session_state["error_msg"] = None

# --- 4. LOGIN SCREEN UI ---
def login_screen():
    # Centered Header
    st.markdown("""
        <div style="text-align: center; margin-bottom: 25px;">
            <h1 style="color: #f8fafc; margin-bottom: 4px; font-size: 34px;">🏥 MediPortal</h1>
            <p style="color: #94a3b8; font-size: 14px;">Secure Healthcare Management System</p>
        </div>
    """, unsafe_allow_html=True)
    
    # SINGLE UNIFIED CENTERED BOX
    with st.container(border=True):
        st.markdown("<p style='text-align: center; color: #cbd5e1; font-size: 14px; margin-bottom: 5px;'>Select Account Type</p>", unsafe_allow_html=True)
        
        # Centered Role Selection inside the card
        selected_role = st.radio(
            "Select Portal Access:",
            ["Patient", "Doctor", "Admin"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Form inside the same card
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder=f"Enter {selected_role.lower()} username")
            password = st.text_input("Password", type="password", placeholder="••••••••••••")
            
            st.write("") # Spacing before button
            submit = st.form_submit_button("Sign In", use_container_width=True)
            
            if submit:
                st.session_state["error_msg"] = None
                
                # Check for missing input
                if not username.strip() or not password.strip():
                    st.session_state["error_msg"] = "Missing data: Please enter both username and password."
                else:
                    role_users = USER_DB.get(selected_role, {})
                    # Check for invalid credentials
                    if username in role_users and role_users[username] == password:
                        st.session_state["logged_in"] = True
                        st.session_state["user"] = username
                        st.session_state["role"] = selected_role
                        st.session_state["error_msg"] = None
                        st.rerun()
                    else:
                        st.session_state["error_msg"] = f"Invalid credentials for {selected_role}."

    # RED ALERT: Appears below the card ONLY when login fails
    if st.session_state["error_msg"]:
        st.error(st.session_state["error_msg"])

# --- 5. APPLICATION ROUTER ---
if not st.session_state["logged_in"]:
    login_screen()
else:
    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"**User:** {st.session_state['user']}")
        st.markdown(f"**Role:** `{st.session_state['role']}`")
        st.divider()
        if st.button("Log Out", type="secondary", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["user"] = ""
            st.session_state["role"] = ""
            st.session_state["error_msg"] = None
            st.rerun()

    # Dynamic File Linking
    role = st.session_state["role"]
    if role == "Admin":
        page = st.Page("adminpage.py", title="Admin Dashboard", icon="🔧")
    elif role == "Doctor":
        page = st.Page("Docpage.py", title="Doctor Dashboard", icon="🩺")
    elif role == "Patient":
        page = st.Page("userpage.py", title="Patient Dashboard", icon="📋")
    
    pg = st.navigation([page])
    pg.run()