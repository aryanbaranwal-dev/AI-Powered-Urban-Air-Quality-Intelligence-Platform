import streamlit as st

from app.config import NAV_ITEMS
from app.theme import theme_toggle_button


def render_sidebar() -> str:
    """Renders the left nav and returns the active page key."""
    if "page" not in st.session_state:
        st.session_state.page = "overview"

    with st.sidebar:
        st.markdown(
            """
            <div class="brand-wrap">
              <div class="brand-badge">🌫️</div>
              <div>
                <div class="brand-title">AQI Intelligence</div>
                <div class="brand-sub">Smart-City Platform</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="sidebar_theme_toggle"):
            st.markdown('<div class="theme-toggle-wrap">', unsafe_allow_html=True)
            theme_toggle_button(key="sidebar_theme_toggle_btn")
            st.markdown('</div>', unsafe_allow_html=True)

        for item in NAV_ITEMS:
            active = st.session_state.page == item["key"]
            if st.button(
                f"{item['icon']}   {item['label']}",
                key=f"nav_{item['key']}",
                type="primary" if active else "secondary",
                use_container_width=True,
            ):
                st.session_state.page = item["key"]
                st.rerun()

        st.markdown(
            """
            <div class="sidebar-foot">
              <b>Data source</b><br/>
              Real CPCB air quality data (2015-2020).<br/>
              5 independent AI agents + Coordinator: Forecast →
              Attribution → Enforcement → Advisory → Decision.
              See <b>Multi-Agent AI Console</b>.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state.page
