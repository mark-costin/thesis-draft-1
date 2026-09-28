import streamlit as st


def basetab_layout_():
    st.markdown(
        """
        <style>
        [data-baseweb="tab-list"] {
            display: flex;
            gap: 12px;
            margin: 10px 0 24px;
        }
        button[data-baseweb="tab"] {
            flex: 1 1 0;
            min-height: 56px;
            justify-content: center;
        }
        [aria-selected="true"] * {
            color: #007979 !important;
        }
        [data-baseweb="tab-highlight"] {
            background-color: #007979 !important;
            height: 4px;
        }
        button[data-testid="baseButton-primary"] {
            background-color: #007979;
            border: 0;
        }
        button[data-testid="baseButton-primary"]:hover {
            background-color: #005f5f;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_navbar(user_name, user_role, user_email, badge_label, badge_color):
    st.session_state.setdefault("theme_mode", "light")
    st.session_state.setdefault("night_light", False)
    st.session_state.setdefault("night_light_warmth", 8)

    identity_col, actions_col = st.columns([5.5, 4.5], vertical_alignment="center")
    with identity_col:
        st.markdown(
            f"""
            <div style="padding: 4px 0;">
                <h3 style="margin: 0; font-size: 1.6rem; font-weight: 800;">
                    {user_name} <span style="font-size: 1rem; font-weight: 600;">| {user_role}</span>
                </h3>
                <div style="font-size: 0.9rem; font-weight: 600; margin-top: 4px;">
                    Lucerna Medica Administration &bull; {user_email}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with actions_col:
        badge_col, notification_col, settings_col = st.columns([2.5, 1, 2.5])
        with badge_col:
            st.markdown(
                f"<div style='background:{badge_color}20; color:{badge_color}; padding:8px; border-radius:20px; font-weight:700; text-align:center;'>{badge_label}</div>",
                unsafe_allow_html=True,
            )
        with notification_col:
            with st.popover("🔔", use_container_width=True):
                st.markdown("##### Notifications")
                st.caption("No new alerts at this time.")
        with settings_col:
            with st.popover("⚙️ Settings", use_container_width=True):
                st.markdown("Theme")
                dark_col, light_col = st.columns(2)
                if dark_col.button("DARK", use_container_width=True):
                    st.session_state.theme_mode = "dark"
                    st.rerun()
                if light_col.button("LIGHT", use_container_width=True):
                    st.session_state.theme_mode = "light"
                    st.rerun()

                st.markdown("Night light")
                on_col, off_col = st.columns(2)
                if on_col.button("ON", key="admin_night_light_on", use_container_width=True):
                    st.session_state.night_light = True
                    st.rerun()
                if off_col.button("OFF", key="admin_night_light_off", use_container_width=True):
                    st.session_state.night_light = False
                    st.rerun()
                if st.session_state.night_light:
                    st.session_state.night_light_warmth = st.slider(
                        "Warmth Intensity", 5, 25, st.session_state.night_light_warmth
                    )

                st.divider()
                st.caption(user_email)
                if st.button("⏻ Log Out", type="primary", use_container_width=True):
                    for key in (
                        "authenticated",
                        "user_role",
                        "jwt_token",
                        "user_id",
                        "user_profile",
                        "user_email",
                    ):
                        st.session_state.pop(key, None)
                    st.rerun()
