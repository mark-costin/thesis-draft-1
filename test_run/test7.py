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
    /* Hide hints */
    [data-testid*="stInputInstructions"] { display: none !important; }
    
    /* Input Styling */
    .stTextInput input, .stDateInput input, .stSelectbox select {
        background-color: #f0f2f6 !important;
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


# ==============================================================================
# VALIDATION HELPER FUNCTIONS
# ==============================================================================
def is_alpha_only(text: str) -> bool:
    """Returns True if string contains only letters and spaces."""
    return bool(re.match(r"^[A-Za-z\s]+$", text.strip()))


def is_valid_phone_format(text: str) -> bool:
    """Returns True if string exactly matches the XXXX-XXX-XXXX numeric format."""
    return bool(re.match(r"^\d{4}-\d{3}-\d{4}$", text.strip()))


def is_valid_gmail(text: str) -> bool:
    """Returns True if string is a valid email ending with @gmail.com."""
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", text.strip()))


# ==============================================================================
# PATIENT REGISTRATION FORM
# ==============================================================================
with st.container(border=True):
    st.markdown(
        "<h2 style='text-align:center; margin:0;'>Patient Registration</h2>"
        "<p style='text-align:center; color:#666; margin: 6px 0 16px 0;'>"
        "Please complete all required fields below to create your patient profile."
        "</p>",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------------------
    # 1. PATIENT INFORMATION CONTAINER
    # --------------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("##### **PATIENT INFORMATION**")

        # Names stacked full-width
        first_name = st.text_input("FIRST NAME*", placeholder="First Name...")
        middle_name = st.text_input("MIDDLE NAME", placeholder="MIDDLE NAME")
        last_name = st.text_input("LAST NAME*", placeholder="Last Name...")

        # 4-Column Row
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

        # Full-width Address
        address = st.text_input(
            "PERMANENT ADDRESS / ADDRESS...*",
            placeholder="PERMANENT ADDRESS / ADDRESS...",
        )

        # Age and Contact Number Row (Age column is smaller)
        col_age, col_contact = st.columns([1, 3])
        
        with col_age:
            # Dynamically compute age from DOB and current date
            calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            st.text_input("AGE", value=str(calculated_age), disabled=True, placeholder="Age...")
            
        with col_contact:
            # Updated Max Chars (13) and Placeholder for the new format
            contact_num = st.text_input(
                "CONTACT NUMBER*",
                placeholder="0912-345-6789",
                max_chars=13,
            )
            
        # Email appended at the bottom
        email = st.text_input("EMAIL ADDRESS*", placeholder="example@gmail.com")

    # --------------------------------------------------------------------------
    # 2. EMERGENCY CONTACT CONTAINER
    # --------------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("##### **EMERGENCY CONTACT PERSON (IN CASE OF EMERGENCY)**")

        col_em_name, col_em_num, col_em_rel = st.columns(3)
        with col_em_name:
            em_full_name = st.text_input("FULL NAME*", placeholder="e.g. Maria Dela Cruz")
        with col_em_num:
            # Updated Max Chars (13) and Placeholder for the new format
            em_contact_num = st.text_input(
                "CONTACT NUMBER*",
                placeholder="0912-345-6789",
                max_chars=13,
            )
        with col_em_rel:
            em_relation = st.text_input("RELATION TO PATIENT*", placeholder="e.g. Mother")

    # --------------------------------------------------------------------------
    # 3. PASSWORD CONTAINER
    # --------------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("##### **ACCOUNT PASSWORD**")

        col_pwd, col_pwd_confirm = st.columns(2)
        with col_pwd:
            password = st.text_input(
                "TYPE PASSWORD*",
                type="password",
                placeholder="Enter new password",
            )
        with col_pwd_confirm:
            confirm_password = st.text_input(
                "CONFIRM PASSWORD*",
                type="password",
                placeholder="Re-enter new password",
            )

    # --------------------------------------------------------------------------
    # 4. CONFIRMATION & HIPAA CONTAINER
    # --------------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("##### **HIPAA AGREEMENT & SUBMISSION**")

        hipaa_agree = st.checkbox(
            "I acknowledge that I have read and agree to the HIPAA Privacy Policy "
            "and consent to the processing of my health information."
        )

        st.write("")  # Spacer

        # Button remains disabled until HIPAA agreement checkbox is ticked
        submit_btn = st.button(
            "Submit Registration",
            disabled=not hipaa_agree,
            use_container_width=True,
        )

        # ----------------------------------------------------------------------
        # FORM VALIDATION & PROCESSING LOGIC
        # ----------------------------------------------------------------------
        if submit_btn:
            errors = []

            # 1. Patient Name Validation
            if not first_name.strip() or not is_alpha_only(first_name):
                errors.append("First Name is required and must contain letters only.")
            if middle_name.strip() and not is_alpha_only(middle_name):
                errors.append("Middle Name must contain letters only.")
            if not last_name.strip() or not is_alpha_only(last_name):
                errors.append("Last Name is required and must contain letters only.")

            # 2. Address Validation
            if not address.strip():
                errors.append("Permanent Address is required.")

            # 3. Contact Number Validation (Strict format check)
            if not is_valid_phone_format(contact_num):
                errors.append("Patient Contact Number must exactly follow the format: XXXX-XXX-XXXX (numbers only).")

            # 4. Email Validation
            if not is_valid_gmail(email):
                errors.append("Valid Gmail address ending in @gmail.com is required.")

            # 5. Emergency Contact Validation (Strict format check added)
            if not em_full_name.strip() or not is_alpha_only(em_full_name):
                errors.append("Emergency Contact Full Name is required and must contain letters only.")
            if not is_valid_phone_format(em_contact_num):
                errors.append("Emergency Contact Number must exactly follow the format: XXXX-XXX-XXXX (numbers only).")
            if not em_relation.strip() or not is_alpha_only(em_relation):
                errors.append("Emergency Contact Relation is required and must contain letters only.")

            # 6. Password Validation
            if not password:
                errors.append("Password field cannot be empty.")
            elif password != confirm_password:
                errors.append("Type Password and Confirm Password fields do not match.")

            # Display Validation Errors or Proceed
            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                st.info(
                    "⏳ **Account Processing Notice:** Your registration details have been submitted. "
                    "Credentials will be verified and sent to your Gmail by the IT Admin."
                )
                st.success("✅ Patient registration request created successfully!")