import datetime
import re
import streamlit as st

st.set_page_config(layout="centered")

# ==============================================================================
# COMPACT CSS STYLING
# ==============================================================================
st.markdown(
    """
    <style>
    /* Hide input instruction hints */
    [data-testid*="stInputInstructions"] { display: none !important; }
    
    /* Input Background Styling */
    .stTextInput input, .stDateInput input, .stSelectbox select {
        background-color: #f0f2f6 !important;
    }
    
    /* FORCE DISABLED AGE INPUT TEXT TO BE BOLD BLACK */
    .stTextInput input:disabled {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        opacity: 1 !important;
        font-weight: 700 !important;
    }

    /* Global Teal Accents */
    [data-testid="baseButton-secondary"]:hover, 
    [data-testid="baseButton-secondary"]:focus, 
    [data-testid="baseButton-secondary"]:active { 
        border-color: #007979 !important; 
        color: #007979 !important; 
    }
    </style>
""",
    unsafe_allow_html=True,
)


# --- REAL-TIME SANITIZATION CALLBACKS ---
def clean_name_input(key: str):
    """Strips non-letters/digits in real-time while flagging an error if invalid characters were entered."""
    raw_val = st.session_state.get(key, "")

    # Flag invalid state if numbers or non-alphabet characters are present
    if re.search(r"[^A-Za-z\s]", raw_val):
        st.session_state[f"{key}_invalid"] = True
    else:
        st.session_state[f"{key}_invalid"] = False

    # Auto-delete invalid characters
    cleaned_val = re.sub(r"[^A-Za-z\s]", "", raw_val)
    st.session_state[key] = cleaned_val


def format_contact_number():
    """Strips letters/non-digits, formats to XXXX-XXX-XXXX, and caps strictly at 11 digits."""
    raw_val = st.session_state.get("contact_num_key", "")
    digits = "".join(filter(str.isdigit, raw_val))[:11]

    formatted = ""
    if len(digits) > 0:
        formatted += digits[:4]
    if len(digits) > 4:
        formatted += "-" + digits[4:7]
    if len(digits) > 7:
        formatted += "-" + digits[7:11]

    st.session_state.contact_num_key = formatted


# --- VALIDATION HELPERS ---
def is_valid_phone_format(text: str) -> bool:
    """Returns True if string strictly matches XXXX-XXX-XXXX format (11 digits)."""
    return bool(re.match(r"^\d{4}-\d{3}-\d{4}$", text.strip()))


def is_valid_gmail(text: str) -> bool:
    """Returns True if email strictly ends in @gmail.com."""
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", text.strip()))


# --- 1. PATIENT INFORMATION CONTAINER ---
with st.container(border=True):
    st.markdown("##### **PATIENT INFORMATION**")

    # --- FIRST NAME (AUTO-DELETE NUMBERS + ERROR WARNING) ---
    first_name = st.text_input(
        "FIRST NAME*",
        placeholder="First Name...",
        key="fn_key",
        on_change=clean_name_input,
        args=("fn_key",),
    )
    if st.session_state.get("fn_key_invalid"):
        st.error("⛔ Only letters and spaces are permitted for First Name.")

    # --- MIDDLE NAME (AUTO-DELETE NUMBERS + ERROR WARNING) ---
    middle_name = st.text_input(
        "MIDDLE NAME",
        placeholder="MIDDLE NAME",
        key="mn_key",
        on_change=clean_name_input,
        args=("mn_key",),
    )
    if st.session_state.get("mn_key_invalid"):
        st.error("⛔ Only letters and spaces are permitted for Middle Name.")

    # --- LAST NAME (AUTO-DELETE NUMBERS + ERROR WARNING) ---
    last_name = st.text_input(
        "LAST NAME*",
        placeholder="Last Name...",
        key="ln_key",
        on_change=clean_name_input,
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
        gender = st.selectbox(
            "GENDER*", ["Male", "Female", "Prefer not to say"]
        )
    with col_rel:
        religion = st.selectbox(
            "RELIGION*",
            [
                "Roman Catholic",
                "Islam",
                "Christianity",
                "Buddhism",
                "Hinduism",
                "Others",
                "None",
            ],
        )
    with col_suf:
        suffix = st.selectbox(
            "SUFFIX*",
            [
                "N/A",
                "Jr.",
                "Sr.",
                "I",
                "II",
                "III",
                "IV",
                "V",
                "VI",
                "VII",
                "VIII",
                "IX",
                "X",
            ],
        )

    # Permanent Address
    address = st.text_input(
        "PERMANENT ADDRESS / ADDRESS...*",
        placeholder="PERMANENT ADDRESS / ADDRESS...",
    )

    # Age & Contact Number Row (Strict 1 : 4 Column Width Ratio)
    col_age, col_contact = st.columns([1, 4])

    with col_age:
        # Dynamically compute age from DOB
        calculated_age = (
            today.year
            - dob.year
            - ((today.month, today.day) < (dob.month, dob.day))
        )
        st.text_input(
            "AGE", value=str(calculated_age), disabled=True, placeholder="Age..."
        )

    with col_contact:
        # --- CONTACT NUMBER (NO LETTERS ALLOWED + AUTO-FORMAT + INLINE ERROR CHECK) ---
        contact_num = st.text_input(
            "CONTACT NUMBER*",
            placeholder="0923-256-5777",
            max_chars=13,
            key="contact_num_key",
            on_change=format_contact_number,
        )

        digits_only = "".join(filter(str.isdigit, contact_num))
        if contact_num and len(digits_only) < 11:
            st.error(
                f"⛔ Incomplete contact number ({len(digits_only)}/11 digits typed). Exactly 11 digits are required."
            )

    # Email Field
    email = st.text_input("EMAIL ADDRESS*", placeholder="example@gmail.com")
    if email and not is_valid_gmail(email):
        st.error("⛔ Must be a valid Gmail address ending strictly in @gmail.com.")


# --- PATIENT INFO VALIDATION TEST BUTTON ---
if st.button("Validate Patient Info"):
    errors = []

    if not first_name.strip() or not re.match(r"^[A-Za-z\s]+$", first_name):
        errors.append("First Name is required and must contain letters only.")
    if middle_name.strip() and not re.match(r"^[A-Za-z\s]+$", middle_name):
        errors.append("Middle Name must contain letters only.")
    if not last_name.strip() or not re.match(r"^[A-Za-z\s]+$", last_name):
        errors.append("Last Name is required and must contain letters only.")
    if not address.strip():
        errors.append("Permanent Address is required.")

    if not is_valid_phone_format(contact_num):
        errors.append(
            "Contact Number must be exactly 11 digits in XXXX-XXX-XXXX format (e.g., 0923-256-5777)."
        )

    if not is_valid_gmail(email):
        errors.append("Valid Gmail address ending strictly in @gmail.com is required.")

    if errors:
        for err in errors:
            st.error(f"❌ {err}")
    else:
        st.success("✅ Patient Information is valid!")