import streamlit as st

# 1. Page Config
st.set_page_config("Lucerna", "🏥", layout="wide", initial_sidebar_state="collapsed")

# 2. Session State Initialization
for key, val in [("authenticated", False), ("user_role", None), ("jwt_token", None), ("user_id", None)]:
    st.session_state.setdefault(key, val)

# 3. Define Pages & Role Mapping
login_page = st.Page("views/login.py", title="Authentication", icon="🔐")
role_pages = {
    "ADMIN": st.Page("views/adminpage.py", title="Admin Portal", icon="⚙️"),
    "DOCTOR": st.Page("views/docpage.py", title="Doctor Workspace", icon="🩺"),
    "PATIENT": st.Page("views/patientpage.py", title="Patient Portal", icon="📋"),
}

# 4. RBAC Router Logic
role = st.session_state.get("user_role")
if st.session_state["authenticated"] and role in role_pages:
    nav = st.navigation([role_pages[role]])
else:
    st.session_state["authenticated"] = False
    nav = st.navigation([login_page], position="hidden")

# 5. Run Selected Page
nav.run()