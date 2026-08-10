import datetime
import re
import base64
import os
import streamlit as st

# MUST BE AT THE VERY TOP, AND ONLY CALLED ONCE
st.set_page_config(layout="centered")

# ==============================================================================
# SMART ASSET LOCATOR (FOR CUSTOM PASSWORD ICONS)
# ==============================================================================
def get_icon(f):
    d = os.path.dirname(os.path.abspath(__file__))
    # Checks multiple possible paths to guarantee it finds your assets folder
    for p in [f"{d}/../assets/{f}", f"{d}/assets/{f}", f"assets/{f}"]:
        if os.path.exists(p): return base64.b64encode(open(p, "rb").read()).decode()
    return ""

c_b64, o_b64 = get_icon("close_l.png"), get_icon("open_l.png")


# ==============================================================================
# COMPACT CSS STYLING (UPDATED WITH LOCK ICON LOGIC)
# ==============================================================================
# Note: Using f-string here requires all standard CSS braces {} to be doubled {{}}
st.markdown(f"""
    <style>
    /* Hide input instruction hints */
    [data-testid*="stInputInstructions"] {{ display: none !important; }}
    
    /* Input Background Styling */
    .stTextInput input, .stDateInput input, .stSelectbox select {{
        background-color: #f0f2f6 !important;
    }}
    
    /* FORCE DISABLED AGE INPUT TEXT TO BE BOLD BLACK */
    .stTextInput input:disabled {{
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        opacity: 1 !important;
        font-weight: 700 !important;
    }}

    /* Global Teal Accents */
    [data-testid="baseButton-secondary"]:hover, 
    [data-testid="baseButton-secondary"]:focus, 
    [data-testid="baseButton-secondary"]:active {{ 
        border-color: #007979 !important; 
        color: #007979 !important; 
    }}

    /* --- CUSTOM PASSWORD LOCK ICON STYLING --- */
    /* Hide native SVGs */
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
    .stTextInput input {{ padding-right: 2.5rem !important; }}
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# REAL-TIME SANITIZATION CALLBACKS
# ==============================================================================
def clean_alpha_input(key: str):
    """Strips non-letters/digits in real-time and flags an error if numbers were typed."""
    raw_val = st.session_state.get(key, "")

    if re.search(r"[^A-Za-z\s]", raw_val):
        st.session_state[f"{key}_invalid"] = True
    else:
        st.session_state[f"{key}_invalid"] = False

    cleaned_val = re.sub(r"[^A-Za-z\s]", "", raw_val)
    st.session_state[key] = cleaned_val


def format_phone_number(key: str):
    """Strips letters, formats to XXXX-XXX-XXXX, and caps strictly at 11 digits."""
    raw_val = st.session_state.get(key, "")
    digits = "".join(filter(str.isdigit, raw_val))[:11]

    formatted = ""
    if len(digits) > 0:
        formatted += digits[:4]
    if len(digits) > 4:
        formatted += "-" + digits[4:7]
    if len(digits) > 7:
        formatted += "-" + digits[7:11]

    st.session_state[key] = formatted


# ==============================================================================
# VALIDATION HELPERS
# ==============================================================================
def is_valid_phone_format(text: str) -> bool:
    """Returns True if string strictly matches XXXX-XXX-XXXX format (11 digits)."""
    return bool(re.match(r"^\d{4}-\d{3}-\d{4}$", text.strip()))


def is_valid_gmail(text: str) -> bool:
    """Returns True if email strictly ends in @gmail.com."""
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", text.strip()))


# ==============================================================================
# 1. PATIENT INFORMATION CONTAINER
# ==============================================================================
with st.container(border=True):
    st.markdown("##### **PATIENT INFORMATION**")

    # --- FIRST NAME ---
    first_name = st.text_input(
        "FIRST NAME*",
        placeholder="First Name...",
        key="fn_key",
        on_change=clean_alpha_input,
        args=("fn_key",),
    )
    if st.session_state.get("fn_key_invalid"):
        st.error("⛔ Only letters and spaces are permitted for First Name.")

    # --- MIDDLE NAME ---
    middle_name = st.text_input(
        "MIDDLE NAME",
        placeholder="MIDDLE NAME",
        key="mn_key",
        on_change=clean_alpha_input,
        args=("mn_key",),
    )
    if st.session_state.get("mn_key_invalid"):
        st.error("⛔ Only letters and spaces are permitted for Middle Name.")

    # --- LAST NAME ---
    last_name = st.text_input(
        "LAST NAME*",
        placeholder="Last Name...",
        key="ln_key",
        on_change=clean_alpha_input,
        args=("ln_key",),
    )
    if st.session_state.get("ln_key_invalid"):
        st.error("⛔ Only letters and spaces are permitted for Last Name.")

    # 4-Column Row (DOB, Gender, Religion, Suffix)
    col_dob, col_gen, col_rel, col_suf = st.columns(4)

    with col_dob:
        today = datetime.date.today()
        dob = st.date_input(
            "DATE OF BIRTH*",
            min_value=datetime.date(1900, 1, 1),
            max_value=today,
            format="MM/DD/YYYY",
        )
    with col_gen:
        gender = st.selectbox("GENDER*", ["Male", "Female", "Prefer not to say"])
    with col_rel:
        religion = st.selectbox(
            "RELIGION*",
            ["Roman Catholic", "Islam", "Christianity", "Buddhism", "Hinduism", "Others", "None"],
        )
    with col_suf:
        suffix = st.selectbox(
            "SUFFIX*",
            ["N/A", "Jr.", "Sr.", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"],
        )

    # Permanent Address
    address = st.text_input(
        "PERMANENT ADDRESS / ADDRESS...*",
        placeholder="PERMANENT ADDRESS / ADDRESS...",
    )

    # Age & Contact Number Row
    col_age, col_contact = st.columns([1, 4])

    with col_age:
        calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        st.text_input("AGE", value=str(calculated_age), disabled=True, placeholder="Age...")

    with col_contact:
        contact_num = st.text_input(
            "CONTACT NUMBER*",
            placeholder="0923-256-5777",
            max_chars=13,
            key="contact_num_key",
            on_change=format_phone_number,
            args=("contact_num_key",),
        )

        digits_only = "".join(filter(str.isdigit, contact_num))
        if contact_num and len(digits_only) < 11:
            st.error(f"⛔ Incomplete contact number ({len(digits_only)}/11 digits typed). Exactly 11 digits are required.")

    # Email Field
    email = st.text_input("EMAIL ADDRESS*", placeholder="example@gmail.com")
    if email and not is_valid_gmail(email):
        st.error("⛔ Must be a valid Gmail address ending strictly in @gmail.com.")


# ==============================================================================
# 2. PERSON IN CASE OF EMERGENCY CONTAINER
# ==============================================================================
with st.container(border=True):
    st.markdown("##### **PERSON IN CASE OF EMERGENCY**")

    # Full Name
    em_full_name = st.text_input(
        "Full Name*",
        placeholder="Input full name",
        key="em_fn_key",
        on_change=clean_alpha_input,
        args=("em_fn_key",),
    )
    if st.session_state.get("em_fn_key_invalid"):
        st.error("⛔ Full name must contain words only (no numbers allowed).")

    # Emergency Contact Number
    em_contact_num = st.text_input(
        "Contact Number*",
        placeholder="Input contact number (e.g., 0912-345-6789)",
        max_chars=13,
        key="em_contact_num_key",
        on_change=format_phone_number,
        args=("em_contact_num_key",),
    )
    
    em_digits_only = "".join(filter(str.isdigit, em_contact_num))
    if em_contact_num and len(em_digits_only) < 11:
        st.error(f"⛔ Incomplete contact number ({len(em_digits_only)}/11 digits typed). Exactly 11 digits are required.")

    # Relation to Patient
    em_relation = st.text_input(
        "Relation to Patient*",
        placeholder="(mother, father, son, etc.)",
        key="em_rel_key",
        on_change=clean_alpha_input,
        args=("em_rel_key",),
    )
    if st.session_state.get("em_rel_key_invalid"):
        st.error("⛔ Relation to patient must contain words only (no numbers allowed).")


# ==============================================================================
# 3. PASSWORD CONTAINER
# ==============================================================================
with st.container(border=True):
    st.markdown("##### **PASSWORD**")

    type_password = st.text_input(
        "Type Password*", 
        type="password", 
        placeholder="type password"
    )
    
    confirm_password = st.text_input(
        "Confirm Password*", 
        type="password", 
        placeholder="confirm password"
    )

    if type_password and confirm_password:
        if type_password != confirm_password:
            st.error("⛔ Passwords do not match. Please ensure both fields are identical.")
        else:
            st.success("✅ Passwords match.")


# ==============================================================================
# 4. HIPAA AGREEMENT & CONFIRMATION CONTAINER
# ==============================================================================
with st.container(border=True):
    st.markdown("##### **HIPAA AGREEMENT**")

    # Mandatory Checkbox
    hipaa_agreement = st.checkbox(
        "I acknowledge and agree to the HIPAA Privacy Policy and the Data Privacy Act of 2012 "
        "(Republic Act No. 10173). I consent to the processing of my health information."
    )

    st.write("") # Spacer

    # Confirm Button
    submit_btn = st.button(
        "Confirm Registration",
        disabled=not hipaa_agreement,
        use_container_width=True
    )

    # ==========================================================================
    # FINAL SUBMISSION LOGIC
    # ==========================================================================
    if submit_btn:
        errors = []

        if not first_name.strip() or not re.match(r"^[A-Za-z\s]+$", first_name):
            errors.append("Patient First Name is required and must contain letters only.")
        if middle_name.strip() and not re.match(r"^[A-Za-z\s]+$", middle_name):
            errors.append("Patient Middle Name must contain letters only.")
        if not last_name.strip() or not re.match(r"^[A-Za-z\s]+$", last_name):
            errors.append("Patient Last Name is required and must contain letters only.")
        if not address.strip():
            errors.append("Permanent Address is required.")
        if not is_valid_phone_format(contact_num):
            errors.append("Patient Contact Number must be exactly 11 digits.")
        if not is_valid_gmail(email):
            errors.append("Valid Gmail address ending strictly in @gmail.com is required.")

        if not em_full_name.strip() or not re.match(r"^[A-Za-z\s]+$", em_full_name):
            errors.append("Emergency Contact Full Name is required and must contain letters only.")
        if not is_valid_phone_format(em_contact_num):
            errors.append("Emergency Contact Number must be exactly 11 digits.")
        if not em_relation.strip() or not re.match(r"^[A-Za-z\s]+$", em_relation):
            errors.append("Relation to Patient is required and must contain letters only.")

        if not type_password or not confirm_password:
            errors.append("Both password fields must be filled out.")
        elif type_password != confirm_password:
            errors.append("Type Password and Confirm Password do not match.")

        if errors:
            for err in errors:
                st.error(f"❌ {err}")
        else:
            st.info("⏳ Processing account details...")
            st.success("✅ Registration submitted! Credentials will be verified and sent to your Gmail by the IT Admin.")