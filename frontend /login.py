import streamlit as st

# 1. Page Configuration
st.set_page_config(page_title="Preventive Care Portal", layout="centered")

# 2. Initialize Session State Defaults (KISS method)
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("user_role", None)

# 3. Define Available Page Views (Pointers to files in views/)
login_view = st.Page("views/login_view.py", title="Login / Register", icon="🔐")
admin_view = st.Page("views/adminpage.py", title="Admin Portal", icon="⚙️")
doctor_view = st.Page("views/doctorpage.py", title="Doctor Workspace", icon="🩺")
patient_view = st.Page("views/patientpage.py", title="Patient Portal", icon="📋")

# 4. RBAC Router Logic
if not st.session_state["authenticated"]:
    # Hide sidebar; restrict unauthenticated users to the login screen
    router = st.navigation([login_view], position="hidden")
else:
    role = st.session_state["user_role"]
    
    # Strictly route to the workspace matching the user's role
    if role == "ADMIN":
        router = st.navigation([admin_view])
    elif role == "DOCTOR":
        router = st.navigation([doctor_view])
    elif role == "PATIENT":
        router = st.navigation([patient_view])
    else:
        # Fallback security check for unrecognized roles
        router = st.navigation([login_view], position="hidden")

# 5. Execute the Selected Page
router.run()