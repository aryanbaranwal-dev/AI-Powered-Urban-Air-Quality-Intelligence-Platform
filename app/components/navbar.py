import streamlit as st

from app.config import APP_NAME, APP_TAGLINE, CITIES
from app.components.clock import live_clock_html
from app.theme import theme_toggle_button


def render_navbar() -> str:
    """Renders the sticky top bar: logo/title on the left, live clock +
    city selector + theme toggle on the right. Returns the selected city."""
    with st.container(key="navbar_shell"):
        left, mid, right, toggle_col = st.columns([3.2, 2.0, 1.2, 1.0], vertical_alignment="center")

        with left:
            st.markdown(
                f"""
                <div class="navbar-left">
                  <div class="navbar-logo">🌫️</div>
                  <div>
                    <div class="navbar-title"><span class="grad">{APP_NAME}</span></div>
                    <div class="navbar-sub">{APP_TAGLINE}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with mid:
            live_clock_html(height=42)

        with right:
            city = st.selectbox("City", CITIES, key="city_choice", label_visibility="collapsed")

        with toggle_col:
            st.markdown('<div class="theme-toggle-wrap">', unsafe_allow_html=True)
            theme_toggle_button(key="navbar_theme_toggle_btn", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    return city
