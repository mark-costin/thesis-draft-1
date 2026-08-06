import streamlit as st

st.set_page_config(page_title="App Login", page_icon="🔒", layout="centered")

USER_DB = {
    "admin": "password123",
    "mark": "thesis2026"
}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user" not in st.session_state:
    st.session_state["user"] = ""

def show_login_page():
    st.title("🔒 Sign In")
    st.caption("Please enter your credentials to continue.")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit = st.form_submit_button("Log In", use_container_width=True)
        
        if submit:
            # Check for empty inputs first
            if not username.strip() or not password.strip():
                st.warning("Please enter both username and password.")
            # Only authenticate if both fields have values
            elif username in USER_DB and USER_DB[username] == password:
                st.session_state["logged_in"] = True
                st.session_state["user"] = username
                st.success("Success! Redirecting...")
                st.rerun()
            else:
                st.error("Invalid username or password")

def show_dashboard():
    st.title(f"Welcome back, {st.session_state['user']}! 👋")
    if st.button("Log Out"):
        st.session_state["logged_in"] = False
        st.session_state["user"] = ""
        st.rerun()

if st.session_state["logged_in"]:
    show_dashboard()
else:
    show_login_page()