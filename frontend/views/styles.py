import frontend.docpage_api as docpage_api
from frontend import cdss_logic
import streamlit as st

def basetab_layout_():
    """
    Injects custom wide-tab layout, primary button theme, 
    layout ratios, and popover typography across all workspaces.
    """
    st.markdown("""
        <style>
        /* Hide input instruction hints */
        [data-testid*="stInputInstructions"] { display: none !important; }

        /* Layout Spacing: 10/90/10 Ratio */
        .block-container {
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            padding-top: 1.5rem !important;
            max-width: 96% !important;
        }

        /* ----------------------------------------------------
           STRETCHED TAB BAR LAYOUT 
           ---------------------------------------------------- */
        [data-baseweb="tab-list"] {
            display: flex !important;
            width: 100% !important;
            margin-top: 10px !important;
            margin-bottom: 24px !important;
            gap: 14px !important;
        }
        button[data-baseweb="tab"], [data-testid="stTab"] {
            flex: 1 1 0 !important;
            height: 62px !important;
            padding: 14px 20px !important;
            justify-content: center !important;
            background-color: transparent !important;
        }
        button[data-baseweb="tab"]:hover {
            background-color: rgba(0, 121, 121, 0.08) !important;
        }
        button[data-baseweb="tab"] p, 
        button[data-baseweb="tab"] span, 
        [data-testid="stTab"] * {
            font-size: 1.45rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.5px !important;
        }

        /* Active Tab Color Accents */
        [aria-selected="true"] * { color: #010736 !important; }
        [data-baseweb="tab-highlight"] {
            background-color: #010736 !important;
            height: 4px !important;
            border-radius: 3px !important;
        }

        /* PRIMARY BUTTON STYLING */
        button[data-testid="baseButton-primary"] {
            background-color: #010736 !important;
            color: #ffffff !important;
            border: none !important;
            font-weight: 700 !important;
            height: 48px !important;
            border-radius: 8px !important;
        }
        button[data-testid="baseButton-primary"]:hover {
            background-color: #22396F !important;
            color: #ffffff !important;
        }
        
        /* Popover Icon Styling */
        div[data-testid="stPopover"] > button p { 
            margin: 0 !important; 
            text-align: left !important; 
            line-height: 1.2 !important; 
            font-size: 0.85rem !important; 
        }
        div[data-testid="stPopover"] > button p strong { 
            font-size: 1rem !important; 
            font-weight: 800 !important; 
        }
        </style>
    """, unsafe_allow_html=True)

def render_top_navbar(user_name, user_role, user_email, badge_label="System Access", badge_color="#0ea5e9"):
    """Renders the unified top navigation bar, night-light, and settings popover."""
    
    if "night_light" not in st.session_state:
        st.session_state.night_light = False
    if "night_light_warmth" not in st.session_state:
        st.session_state.night_light_warmth = 8 

    if st.session_state.night_light:
        opacity = st.session_state.night_light_warmth / 100
        st.markdown(f'<div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(255, 145, 0, {opacity}); pointer-events: none; z-index: 999999;"></div>', unsafe_allow_html=True)

    with st.container(border=False):
        h_col1, h_col2 = st.columns([5.5, 4.5], vertical_alignment="center")
        
        with h_col1:
            st.markdown(f"""
            <div style="padding: 4px 0px;">
                <h3 style="margin: 0; font-size: 1.85rem; font-weight: 800;">{user_name} <span style="font-size: 1.1rem; font-weight: 600;">&nbsp;|&nbsp; {user_role}</span></h3>
                <div style="font-size: 0.95rem; font-weight: 600; margin-top: 4px;">✔ Lucerna Medica • {user_email}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with h_col2:
            badge_col, btn1, btn2, btn3 = st.columns([2.5, 1, 1, 2.5])
            with badge_col:
                st.markdown(f"""<div style="background: {badge_color}20; color: {badge_color}; padding: 8px 0px; border-radius: 20px; font-weight: 700; font-size: 0.85rem; text-align: center; margin-top: 5px;">🛡️ {badge_label}</div>""", unsafe_allow_html=True)
            with btn1:
                st.button("☰", use_container_width=True, key="nav_btn_menu")
            with btn2:
                with st.popover("🔔", use_container_width=True):
                    st.markdown("##### Notifications")
                    st.caption("No new alerts at this time.")
            with btn3:
                with st.popover("⚙️ Settings", use_container_width=True):
                    st.markdown("<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 5px;'>Theme Settings</div>", unsafe_allow_html=True)
                    st.caption("Dark/Light mode is handled natively by Streamlit via your browser settings.")
                    
                    st.markdown("<div style='font-size: 0.95rem; font-weight: 600; margin-top: 10px; margin-bottom: 5px;'>Night light</div>", unsafe_allow_html=True)
                    nl_col1, nl_col2 = st.columns(2)
                    on_type = "primary" if st.session_state.night_light else "secondary"
                    off_type = "secondary" if st.session_state.night_light else "primary"
                    
                    if nl_col1.button("ON", type=on_type, use_container_width=True, key="nl_on_btn"):
                        st.session_state.night_light = True
                        st.rerun()
                    if nl_col2.button("OFF", type=off_type, use_container_width=True, key="nl_off_btn"):
                        st.session_state.night_light = False
                        st.rerun()
                    if st.session_state.night_light:
                        st.session_state.night_light_warmth = st.slider("Warmth Intensity", 5, 25, st.session_state.night_light_warmth, key="nl_warmth_slider")
                    
                    st.divider()
                    st.markdown(f"<div style='text-align: center; color: #007979; font-size: 0.85rem; margin-bottom: 10px;'>{user_email}</div>", unsafe_allow_html=True)
                    if st.button("⏻ Log Out", type="primary", use_container_width=True, key="nav_btn_logout"):
                        # Ends every token of this account on the server, then forgets the login and
                        # all patient data in this browser session (display preferences are kept).
                        docpage_api.perform_backend_logout()
                        cdss_logic.clear_auth_state(st.session_state)
                        st.rerun()


# ==============================================================================
# SHARED HELPERS FOR BACKEND REPLIES
# ==============================================================================
def show_api_error(resp, disease=None):
    """Show a failed reply the way the API guide asks: the message, plus the fields to fix."""
    info = cdss_logic.error_info(resp)
    if info is None:
        return None
    message = cdss_logic.friendly_error(resp)
    if info["fields"]:
        names = cdss_logic.field_labels(disease, info["fields"]) if disease else info["fields"]
        message += "\n\nCheck: " + ", ".join(names)
    if info["retryable"]:
        message += "\n\nThis can be retried."
    st.error(message)
    return info


def flash(kind, message):
    """Keep a message across st.rerun() (shown once by show_flash)."""
    st.session_state["_flash"] = (kind, message)


def show_flash():
    item = st.session_state.pop("_flash", None)
    if item:
        getattr(st, item[0])(item[1])


def render_fhrs_panel(view, title="Family-history risk (FHRS)"):
    """Show the backend's FHRS breakdown as-is. The UI never computes a weight or a band."""
    if not view:
        st.caption("No FHRS breakdown was returned.")
        return
    st.markdown(f"##### {title}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Adjusted FHRS", view.get("adjusted_fhrs") if view.get("adjusted_fhrs") is not None else "—")
    c2.metric("Band", f"{view.get('band', '—')} · {view.get('band_label') or '—'}")
    c3.metric("Relatives counted", view.get("relatives_counted") if view.get("relatives_counted") is not None else "—")
    st.caption(f"Biological FHRS {view.get('bio_fhrs', '—')} = relatives {view.get('pedigree_sum', '—')} "
               f"+ clustering {view.get('clustering', '—')} · household hazards modifier "
               f"{view.get('environmental_modifier', '—')}")
    if view.get("skipped_records"):
        st.warning("Some family-history entries could not be scored; please fix them: "
                   + "; ".join(str(r) for r in view["skipped_records"]))
