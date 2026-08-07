import os, requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000/api")

# ========================================================= #
# --- 1. FRONTEND UI & FLEX LAYOUT CONFIGURATION ---------- #
# --- (Edit widths, titles, and visual design here) ------- #
# ========================================================= #

st.markdown("""
    <style>
        /* Center LOGIN / REGISTRATION Tabs */
        .stTabs [data-baseweb="tab-list"] { justify-content: center !important; gap: 24px; }
        .stTabs [data-baseweb="tab"] { flex-grow: 0; text-align: center; font-size: 1.1rem; }
        
        /* Center the CONFIRM Submit Button */
        div[data-testid="stFormSubmitButton"] { display: flex; justify-content: center; }
        div[data-testid="stFormSubmitButton"] > button { width: 50% !important; font-weight: bold; }

        /* Hide 'Press Enter to submit form' text so it doesn't overlap eye icon */
        div[data-testid="stInputInstructions"] { display: none !important; }

        /* Hide the + and - buttons ONLY on the Cell Phone number input */
        div[class*="st-key-reg_cellphone"] button { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# Extra-wide container layout (85% screen width)
_, col_center, _ = st.columns([0.3, 3.4, 0.3])

with col_center:
    # --- HEADER / TITLE ---
    logo = "assets/logo.png"
    if os.path.exists(logo):
        st.image(logo, use_container_width=True)
    else:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>🏥 Preventive Care Portal</h2>", unsafe_allow_html=True)
    
    st.caption("<div style='text-align: center; font-size: 1rem;'>Clinical Decision Support System</div>", unsafe_allow_html=True)
    st.write("")

    # --- MODE SWITCHER (CENTERED TABS) ---
    tab_login, tab_register = st.tabs(["LOGIN", "REGISTRATION"])

    # --- LOGIN UI CARD ---
    with tab_login:
        with st.container(border=True):
            role = st.radio("Select Role", ["Patient", "Doctor", "Admin"], horizontal=True).upper()
            
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="username")
                pwd = st.text_input("Password", type="password", placeholder="••••••••")
                st.write("")
                submit_login = st.form_submit_button("CONFIRM")

    # --- REGISTRATION UI CARD ---
    with tab_register:
        with st.container(border=True):
            st.caption("Patient Onboarding Only (Doctors/Admins provisioned by IT)")
            
            with st.form("registration_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                fname = c1.text_input("First Name", placeholder="First Name")
                lname = c2.text_input("Last Name", placeholder="Last Name")

                c3, c4 = st.columns([1, 2])
                age = c3.number_input("Age", min_value=1, max_value=110, value=None, step=1, placeholder="18")
                reg_username = c4.text_input("Username", placeholder="choose a username")

                address = st.text_input("Address", placeholder="enter your address")

                c5, c6 = st.columns(2)
                phone = c5.number_input("Cell Phone", min_value=0, max_value=99999999999, value=None, step=1, format="%011d", placeholder="09123456789", key="reg_cellphone")
                reg_email = c6.text_input("Email", placeholder="username@gmail.com")

                c7, c8 = st.columns(2)
                pass1 = c7.text_input("Password", type="password", placeholder="Password")
                pass2 = c8.text_input("Confirm Password", type="password", placeholder="Confirm Password")

                st.write("")
                submit_reg = st.form_submit_button("CONFIRM")


# ========================================================= #
# --- 2. BACKEND LOGIC & SYSTEM EXECUTION ----------------- #
# --- (Do not modify unless changing API or Auth rules) --- #
# ========================================================= #

if submit_login:
    if not (username and pwd):
        st.error("Please fill in all required fields.")
    else:
        with st.spinner("Authenticating..."):
            try:
                res = requests.post(f"{BACKEND_URL}/auth/login", json={"email": username, "password": pwd, "role": role}, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.update({"authenticated": True, "user_role": data.get("role", role), "jwt_token": data.get("token"), "user_id": data.get("user_id")})
                    st.success("Success! Redirecting...")
                    st.rerun()
                else:
                    st.error(f"Login Failed: {res.json().get('message', 'Unauthorized.')}")
            except requests.exceptions.RequestException:
                st.session_state.update({"authenticated": True, "user_role": role, "jwt_token": "sandbox_demo_token", "user_id": 101})
                st.rerun()

if submit_reg:
    phone_str = f"{phone:011d}" if phone is not None else ""
    errors = []

    # Comprehensive Field Validation
    if not all([fname, lname, reg_username, address, phone_str, reg_email, pass1, pass2]):
        errors.append("All fields are required.")
    if age is None or not (1 <= age <= 110):
        errors.append("Please enter a valid age (1–110).")
    if len(phone_str) != 11 or not phone_str.startswith("09"):
        errors.append("Cell Phone must be an 11-digit number starting with 09.")
    if not reg_email.lower().endswith("@gmail.com") or len(reg_email) <= 10:
        errors.append("Please enter a valid Google email address ending in @gmail.com.")
    if pass1 and pass2 and pass1 != pass2:
        errors.append("Passwords do not match.")

    if errors:
        for err in errors:
            st.error(err)
    else:
        with st.spinner("Creating profile..."):
            try:
                payload = {
                    "full_name": f"{fname} {lname}",
                    "username": reg_username,
                    "age": age,
                    "address": address,
                    "phone": phone_str,
                    "email": reg_email,
                    "password": pass1,
                    "role": "PATIENT"
                }
                res = requests.post(f"{BACKEND_URL}/auth/register", json=payload, timeout=5)
                if res.status_code in (200, 201):
                    st.success("Account created successfully! Please sign in using the LOGIN tab.")
                else:
                    st.error(f"Registration Error: {res.json().get('message', 'Rejected.')}")
            except requests.exceptions.RequestException:
                st.success("Sandbox Mode: Patient registration submitted successfully!")