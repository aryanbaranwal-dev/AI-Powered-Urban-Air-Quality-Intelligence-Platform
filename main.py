"""
AI-Powered Urban Air Quality Intelligence Dashboard
Modern glassmorphic dark-theme SaaS redesign.

Run with:
    streamlit run main.py
"""
import streamlit as st

from app.theme import inject_css, register_plotly_theme
from app.data_loader import load_all, load_models
from app.components.navbar import render_navbar
from app.components.sidebar import render_sidebar
from app.components.skeleton import skeleton_dashboard_preview
from app.config import APP_NAME

from app.sections import overview, forecast, attribution, enforcement, advisory, geospatial, multi_city, settings, ai_agents, intervention_simulator, assistant, executive

st.set_page_config(page_title=f"{APP_NAME} — Urban AQI Platform", layout="wide", page_icon="🌫️", initial_sidebar_state="expanded")

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

inject_css()
register_plotly_theme()

# ---------------- Load data & models (cached) ----------------
_boot_placeholder = st.empty()
with _boot_placeholder.container():
    st.markdown(
        "<div class='card-caption' style='margin-bottom:10px;'>⚡ Booting AI intelligence layer…</div>",
        unsafe_allow_html=True,
    )
    skeleton_dashboard_preview()
data = load_all()
models = load_models()
_boot_placeholder.empty()

# ---------------- Sidebar navigation ----------------
page = render_sidebar()

# ---------------- Top navbar (logo, live clock, city selector) ----------------
city = render_navbar()

ctx = {
    "city": city,
    "clean": data["clean"],
    "attribution": data["attribution"],
    "ward": data["ward"],
    "geo_intel": data["geo_intel"],
    "geo_wards": data["geo_wards"],
    "enforcement": data["enforcement"],
    "advisory": data["advisory"],
    "model_results": data["model_results"],
    "feature_cols": data["feature_cols"],
    "models": models,
}

PAGES = {
    "executive": executive,
    "overview": overview,
    "forecast": forecast,
    "attribution": attribution,
    "enforcement": enforcement,
    "intervention": intervention_simulator,
    "ai_agents": ai_agents,
    "assistant": assistant,
    "advisory": advisory,
    "geospatial": geospatial,
    "multi_city": multi_city,
    "settings": settings,
}

PAGES[page].render(ctx)

# ---------------- Floating AI Assistant (reachable from every page) ----------------
if page != "assistant":
    with st.container(key="floating_assistant_fab"):
        if st.button("💬", key="floating_assistant_fab_btn", help="Ask the AI Assistant"):
            st.session_state.page = "assistant"
            st.rerun()

st.markdown(
    """
    <div style="text-align:center; padding:24px 0 6px 0; color:var(--text-3); font-size:11.5px;">
      Prototype built on real CPCB air quality data · Ward-level and enforcement-source layers are simulated
      for demonstration · Smart Cities / Environmental Intelligence platform
    </div>
    """,
    unsafe_allow_html=True,
)
