import datetime
import re
import base64
import os
import streamlit as st

# ==============================================================================
# SMART ASSET LOCATOR
# ==============================================================================
def get_icon(f):
    d = os.path.dirname(os.path.abspath(__file__))
    for p in [f"{d}/../assets/{f}", f"{d}/assets/{f}", f"assets/{f}"]:
        if os.path.exists(p): return base64.b64encode(open(p, "rb").read()).decode()
    return ""

c_b64, o_b64 = get_icon("close_l.png"), get_icon("open_l.png")

# ==============================================================================
# COMPACT CSS STYLING
# ==============================================================================
st.markdown(f"""
    <style>
    /* Hide input instruction hints */
    [data-testid*="stInputInstructions"] {{ display: none !important; }}
    
    /* --- STRICT PURGE OF NATIVE STREAMLIT PASSWORD EYE ICONS --- */
    div[data-testid="stTextInput"] button *,
    div[data-testid="stTextInput"] button *::before,
    div[data-testid="stTextInput"] button *::after,
    div[data-testid="stTextInput"] button::before,
    div[data-testid="stTextInput"] button::after {{ 
        display: none !important; 
        opacity: 0 !important;
        visibility: hidden !important;
    }}
    
    /* --- CUSTOM PASSWORD LOCK ICON STYLING --- */
    div[data-testid="stTextInput"] > div > div {{ position: relative !important; }}
    div[data-testid="stTextInput"] button {{
        position: absolute !important; 
        right: 0.6rem !important; 
        top: 50% !important; 
        transform: translateY(-50%) !important;
        display: flex !important; 
        border: none !important; 
        width: 1.25rem !important; 
        height: 1.25rem !important; 
        z-index: 2 !important; 
        padding: 0 !important;
        background-color: transparent !important; 
        background-repeat: no-repeat !important; 
        background-position: center !important; 
        background-size: contain !important;
    }}
    
    /* Target "Show password" and "Hide password" toggle buttons */
    button[aria-label*="how password"], button[title*="how password"] {{ 
        background-image: url('data:image/png;base64,{c_b64}') !important; 
    }}
    button[aria-label*="ide password"], button[title*="ide password"] {{ 
        background-image: url('data:image/png;base64,{o_b64}') !important; 
    }}
    
    /* Input Styling */
    .stTextInput input, .stDateInput input, .stSelectbox select {{ background-color: #f0f2f6 !important; }}
    div[data-testid="stTextInput"]:has(input[type="password"]) input {{ padding-right: 2.5rem !important; }}
    
    /* FORCE DISABLED AGE INPUT TEXT TO BE BOLD BLACK */
    .stTextInput input:disabled {{
        color: #000000 !important; 
        -webkit-text-fill-color: #000000 !important;
        opacity: 1 !important; 
        font-weight: 700 !important;
    }}

    /* Global Theming & Accents */
    [data-testid="baseButton-secondary"]:hover, 
    [data-testid="baseButton-secondary"]:focus, 
    [data-testid="baseButton-secondary"]:active {{ 
        border-color: #007979 !important; 
        color: #007979 !important; 
    }}
    
    /* Tabs Stretching */
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

if "login_err" not in st.session_state: 
    st.session_state.login_err = False

# ==============================================================================
# CALLBACKS & VALIDATION HELPERS
# ==============================================================================
def clean_alpha_input(key: str):
    raw_val = st.session_state.get(key, "")
    st.session_state[f"{key}_invalid"] = bool(re.search(r"[^A-Za-z\s]", raw_val))
    st.session_state[key] = re.sub(r"[^A-Za-z\s]", "", raw_val)

def format_phone_number(key: str):
    digits = "".join(filter(str.isdigit, st.session_state.get(key, "")))[:11]
    formatted = digits[:4] + ("-" + digits[4:7] if len(digits) > 4 else "") + ("-" + digits[7:11] if len(digits) > 7 else "")
    st.session_state[key] = formatted

def is_valid_phone_format(text: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{3}-\d{4}$", text.strip()))

def is_valid_gmail(text: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", text.strip()))

# ==============================================================================
# MAIN APP LAYOUT (20 | 60 | 20)
# ==============================================================================
_, col_main, _ = st.columns([20, 60, 20])

with col_main:
    with st.container(border=True):
        st.markdown(
            "<h2 style='text-align:center; margin:0;'>Welcome to the Lucerna Medica!</h2>"
            "<p style='text-align:center; color:#666; margin: 6px 0 16px 0;'>A simple, secure way for patients, doctors, and staff to stay connected.</p>",
            unsafe_allow_html=True,
        )

        tab_login, tab_reg = st.tabs(["Log In", "Patient Registration"])

        # ----------------------------------------------------------------------
        # TAB 1: LOG IN
        # ----------------------------------------------------------------------
        with tab_login:
            with st.container(border=True):
                st.markdown("##### **Account Type**")
                role = st.radio("Role", ["ADMIN", "DOCTOR", "PATIENT"], horizontal=True, label_visibility="collapsed", key="login_role")
                
            with st.container(border=True):
                st.markdown("##### **Username**")
                user = st.text_input("User", placeholder="username", label_visibility="collapsed", key="login_user")
                
                st.markdown("##### **Password**")
                pwd = st.text_input("Pwd", placeholder="password", type="password", label_visibility="collapsed", key="login_pwd")

                if st.session_state.login_err and not (user and pwd):
                    st.error("Please fill in all missing fields before confirming!")
                
                st.write("") 
                
                _, col_btn, _ = st.columns([1, 2, 1])
                if col_btn.button("Confirm", use_container_width=True, key="login_confirm_btn"):
                    if not (user and pwd):
                        st.session_state.login_err = True
                        st.rerun()
                    else:
                        st.session_state.login_err = False
                        # Update session state to trigger the router
                        st.session_state.authenticated = True
                        st.session_state.user_role = role
                        st.success(f"Logged in as {role}: {user}")
                        st.rerun()

        # ----------------------------------------------------------------------
        # TAB 2: PATIENT REGISTRATION
        # ----------------------------------------------------------------------
        with tab_reg:
            
            # --- 1. PATIENT INFORMATION ---
            with st.container(border=True):
                st.markdown("##### **PATIENT INFORMATION**")

                first_name = st.text_input("FIRST NAME*", placeholder="First Name...", key="fn_key", on_change=clean_alpha_input, args=("fn_key",))
                if st.session_state.get("fn_key_invalid"): st.error("⛔ Only letters and spaces are permitted for First Name.")

                middle_name = st.text_input("MIDDLE NAME", placeholder="MIDDLE NAME", key="mn_key", on_change=clean_alpha_input, args=("mn_key",))
                if st.session_state.get("mn_key_invalid"): st.error("⛔ Only letters and spaces are permitted for Middle Name.")

                last_name = st.text_input("LAST NAME*", placeholder="Last Name...", key="ln_key", on_change=clean_alpha_input, args=("ln_key",))
                if st.session_state.get("ln_key_invalid"): st.error("⛔ Only letters and spaces are permitted for Last Name.")

                col_dob, col_gen, col_rel, col_suf = st.columns(4)
                with col_dob:
                    today = datetime.date.today()
                    dob = st.date_input("DATE OF BIRTH*", min_value=datetime.date(1900, 1, 1), max_value=today, format="MM/DD/YYYY")
                with col_gen:
                    gender = st.selectbox("GENDER*", ["Male", "Female", "Prefer not to say"])
                with col_rel:
                    religion = st.selectbox("RELIGION*", ["Roman Catholic", "Islam", "Christianity", "Buddhism", "Hinduism", "Others", "None"])
                with col_suf:
                    suffix = st.selectbox("SUFFIX*", ["N/A", "Jr.", "Sr.", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"])

                address = st.text_input("PERMANENT ADDRESS / ADDRESS...*", placeholder="PERMANENT ADDRESS / ADDRESS...")

                col_age, col_contact = st.columns([1, 4])
                with col_age:
                    calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    st.text_input("AGE", value=str(calculated_age), disabled=True, placeholder="Age...")
                with col_contact:
                    contact_num = st.text_input("CONTACT NUMBER*", placeholder="0923-256-5777", max_chars=13, key="contact_num_key", on_change=format_phone_number, args=("contact_num_key",))
                    digits_only = "".join(filter(str.isdigit, contact_num))
                    if contact_num and len(digits_only) < 11:
                        st.error(f"⛔ Incomplete contact number ({len(digits_only)}/11 digits typed). Exactly 11 digits are required.")

                email = st.text_input("EMAIL ADDRESS*", placeholder="example@gmail.com")
                if email and not is_valid_gmail(email):
                    st.error("⛔ Must be a valid Gmail address ending strictly in @gmail.com.")

            # --- 2. PERSON IN CASE OF EMERGENCY ---
            with st.container(border=True):
                st.markdown("##### **PERSON IN CASE OF EMERGENCY**")

                em_full_name = st.text_input("Full Name*", placeholder="Input full name", key="em_fn_key", on_change=clean_alpha_input, args=("em_fn_key",))
                if st.session_state.get("em_fn_key_invalid"): st.error("⛔ Full name must contain words only (no numbers allowed).")

                em_contact_num = st.text_input("Contact Number*", placeholder="Input contact number (e.g., 0912-345-6789)", max_chars=13, key="em_contact_num_key", on_change=format_phone_number, args=("em_contact_num_key",))
                em_digits_only = "".join(filter(str.isdigit, em_contact_num))
                if em_contact_num and len(em_digits_only) < 11:
                    st.error(f"⛔ Incomplete contact number ({len(em_digits_only)}/11 digits typed). Exactly 11 digits are required.")

                em_relation = st.text_input("Relation to Patient*", placeholder="(mother, father, son, etc.)", key="em_rel_key", on_change=clean_alpha_input, args=("em_rel_key",))
                if st.session_state.get("em_rel_key_invalid"): st.error("⛔ Relation to patient must contain words only (no numbers allowed).")

            # --- 3. PASSWORD ---
            with st.container(border=True):
                st.markdown("##### **PASSWORD**")

                type_password = st.text_input("Type Password*", type="password", placeholder="type password", key="reg_pwd1")
                confirm_password = st.text_input("Confirm Password*", type="password", placeholder="confirm password", key="reg_pwd2")

                if type_password and confirm_password:
                    if type_password != confirm_password:
                        st.error("⛔ Passwords do not match. Please ensure both fields are identical.")
                    else:
                        st.success("✅ Passwords match.")

            # --- 4. HIPAA & SUBMISSION ---
            with st.container(border=True):
                st.markdown("##### **HIPAA AGREEMENT**")
                hipaa_agreement = st.checkbox("I acknowledge and agree to the HIPAA Privacy Policy and the Data Privacy Act of 2012 (Republic Act No. 10173). I consent to the processing of my health information.")
                
                st.write("") 
                submit_btn = st.button("Confirm Registration", disabled=not hipaa_agreement, use_container_width=True)

                if submit_btn:
                    errors = []
                    
                    if not first_name.strip() or not re.match(r"^[A-Za-z\s]+$", first_name): errors.append("Patient First Name is required and must contain letters only.")
                    if middle_name.strip() and not re.match(r"^[A-Za-z\s]+$", middle_name): errors.append("Patient Middle Name must contain letters only.")
                    if not last_name.strip() or not re.match(r"^[A-Za-z\s]+$", last_name): errors.append("Patient Last Name is required and must contain letters only.")
                    if not address.strip(): errors.append("Permanent Address is required.")
                    if not is_valid_phone_format(contact_num): errors.append("Patient Contact Number must be exactly 11 digits.")
                    if not is_valid_gmail(email): errors.append("Valid Gmail address ending strictly in @gmail.com is required.")
                    
                    if not em_full_name.strip() or not re.match(r"^[A-Za-z\s]+$", em_full_name): errors.append("Emergency Contact Full Name is required and must contain letters only.")
                    if not is_valid_phone_format(em_contact_num): errors.append("Emergency Contact Number must be exactly 11 digits.")
                    if not em_relation.strip() or not re.match(r"^[A-Za-z\s]+$", em_relation): errors.append("Relation to Patient is required and must contain letters only.")
                    
                    if not type_password or not confirm_password: errors.append("Both password fields must be filled out.")
                    elif type_password != confirm_password: errors.append("Type Password and Confirm Password do not match.")

                    if errors:
                        for err in errors: st.error(f"❌ {err}")
                    else:
                        st.info("⏳ Processing account details...")
                        st.success("✅ Registration submitted! Credentials will be verified and sent to your Gmail by the IT Admin.")