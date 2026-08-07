import streamlit as st

# --- 1. CLEAN THEME & WIDGET CSS ---
st.markdown(
    """<style>
    /* Remove red focus border */
    div[data-baseweb="input"] > div:focus-within { 
        border-color: #1E88E5 !important; 
        box-shadow: 0 0 0 1px #1E88E5 !important; 
    }
    
    /* Hide the + and - buttons ONLY on the Cell Phone input */
    div[class*="st-key-reg_cellphone"] button {
        display: none !important;
    }
    </style>""",
    unsafe_allow_html=True,
)

st.title("Preventive Care Portal - Test Page")

# --- 2. SIMPLE TOP NAVIGATION ---
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

col_left, _, col_right = st.columns([1, 2, 1])
if col_left.button("Log In", use_container_width=True):
    st.session_state.auth_mode = "login"
if col_right.button("Register", use_container_width=True):
    st.session_state.auth_mode = "register"

# --- 3. MAIN FORM CONTAINER ---
with st.container(border=True):

    # ================= LOGIN VIEW =================
    if st.session_state.auth_mode == "login":
        st.subheader("Login to your account")
        st.radio(
            "Select your role:",
            ["Patient", "Doctor", "Admin"],
            horizontal=True,
            key="login_role",
        )

        st.text_input("Username", placeholder="type username", key="login_user")
        st.text_input(
            "Password", type="password", placeholder="type password", key="login_pass"
        )

        if st.button("Log In", type="primary", use_container_width=True):
            st.success("Logging in...")

    # ================= REGISTER VIEW =================
    else:
        st.subheader("Create a new account")

        c1, c2 = st.columns(2)
        fname = c1.text_input("First Name", placeholder="First Name")
        lname = c2.text_input("Last Name", placeholder="Last Name")

        c3, c4 = st.columns([1, 2])
        # Age keeps its +/- stepper buttons
        age = c3.number_input(
            "Age",
            min_value=1,
            max_value=110,
            value=None,
            step=1,
            placeholder="18",
        )
        username = c4.text_input("Username", placeholder="choose a username")

        address = st.text_input("Address", placeholder="enter your address")

        c5, c6 = st.columns(2)
        # +/- buttons are hidden via CSS using key="reg_cellphone"
        phone = c5.number_input(
            "Cell Phone",
            min_value=0,
            max_value=99999999999,
            value=None,
            step=1,
            format="%011d",
            placeholder="09123456789",
            key="reg_cellphone",
        )
        email = c6.text_input("Email", placeholder="username@gmail.com")

        c7, c8 = st.columns(2)
        pass1 = c7.text_input("Password", type="password", placeholder="Password")
        pass2 = c8.text_input(
            "Confirm Password",
            type="password",
            placeholder="Confirm Password",
        )

        # --- BATCH VALIDATION ---
        if st.button("Register", type="primary", use_container_width=True):
            errors = []

            # Format phone to 11 digits with leading zeros
            phone_str = f"{phone:011d}" if phone is not None else ""

            if not all([
                fname,
                lname,
                username,
                address,
                phone_str,
                email,
                pass1,
                pass2,
            ]):
                errors.append("All fields are required.")
            if age is None or not (1 <= age <= 110):
                errors.append("Please enter a valid age (1–110).")
            if len(phone_str) != 11 or not phone_str.startswith("09"):
                errors.append(
                    "Cell Phone must be an 11-digit number starting with 09."
                )
            if not email.lower().endswith("@gmail.com") or len(email) <= 10:
                errors.append(
                    "Please enter a valid Google email address ending in @gmail.com."
                )
            if pass1 and pass2 and pass1 != pass2:
                errors.append("Passwords do not match.")

            if errors:
                for err in errors:
                    st.error(err)
            else:
                st.success("Registration successful!")