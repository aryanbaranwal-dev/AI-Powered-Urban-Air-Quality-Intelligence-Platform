import streamlit as st

from app.components.metric_card import section_title
from app.theme import get_theme_name, set_theme


def render(ctx):
    col1, col2 = st.columns([1, 1])

    with col1:
        with st.container(key="set_appearance_card"):
            section_title("Appearance", "🎨")
            current = get_theme_name()
            choice = st.selectbox(
                "Theme",
                ["Dark", "Light"],
                index=0 if current == "dark" else 1,
                key="set_theme_choice",
            )
            picked = "dark" if choice == "Dark" else "light"
            if picked != current:
                set_theme(picked)
                st.rerun()
            st.select_slider("Accent intensity", options=["Subtle", "Balanced", "Vivid"], value="Balanced")
            st.toggle("Reduce motion / animations", value=False)
            st.markdown(
                "<div class='card-caption'>Dark mode is tuned for control-room / SOC-style displays; "
                "Light mode is tuned for daytime office use — both meet WCAG AA text contrast.</div>",
                unsafe_allow_html=True,
            )

        with st.container(key="set_data_card"):
            section_title("Data & Cache", "🗄️")
            st.markdown("<div class='small-caption'>Data and trained models are cached in memory for performance.</div>", unsafe_allow_html=True)
            if st.button("♻️ Clear cache & reload data", use_container_width=True):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("Cache cleared. Data will reload on next interaction.")

    with col2:
        with st.container(key="set_about_card"):
            section_title("About this platform", "ℹ️")
            st.markdown(
                """
                <div class="small-caption" style="line-height:1.8;">
                <b style="color:var(--text-1);">AI-Powered Urban Air Quality Intelligence Platform</b><br/>
                A 6-agent AI pipeline built on real CPCB (Central Pollution Control Board) air quality
                data for Delhi and Mumbai.<br/><br/>
                <b style="color:var(--text-1);">The chain:</b><br/>
                1. Data Pipeline → 2. Forecasting Agent → 3. Source Attribution Agent →
                4. Enforcement Agent → 5. Citizen Advisory Agent → 6. Intelligence Dashboard
                <br/><br/>
                <b style="color:var(--text-1);">Documented limitations:</b><br/>
                • Ward/zone-level breakdown is a simulated layer (real ward-level sensor data isn't public);
                city-level source attribution is chemistry-derived from real pollutant readings.<br/>
                • Forecasts are city-level, applied uniformly across wards.<br/>
                • Citizen advisory translations are hand-written, not machine-translated.<br/>
                • Data covers 2015–2020 (Delhi) / 2018–2020 (Mumbai) — the most recent public CPCB dataset available.
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.container(key="set_source_card"):
            section_title("Data Source", "📚")
            st.markdown(
                "<div class='small-caption'>Real Air Quality Data in India (CPCB), via Kaggle: "
                "<b style='color:var(--text-2);'>rohanrao/air-quality-data-in-india</b></div>",
                unsafe_allow_html=True,
            )
