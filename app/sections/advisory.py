import streamlit as st

from agents.personal_advisory_agent import PersonalAdvisoryAgent, MEDICAL_CONDITIONS, OCCUPATIONS, SUPPORTED_LANGUAGES
from app.components.metric_card import metric_card, section_title
from app.components.xai_card import health_advisory_card
from app.theme import get_aqi_meta

_personal_agent = PersonalAdvisoryAgent()


def _forecast_aqi_for(city, ward_row, clean_df, city_col="City"):
    """Best-effort forward-looking AQI for the personal advisory: ward's
    current simulated AQI if available, else the city's latest reading."""
    if ward_row is not None:
        return float(ward_row["Simulated_AQI"])
    city_rows = clean_df[clean_df[city_col] == city].sort_values("Date")
    return float(city_rows.iloc[-1]["AQI"]) if len(city_rows) else 150.0


def render(ctx):
    city = ctx["city"]
    advisory_df = ctx["advisory"]
    ward_df = ctx["ward"]
    geo_intel = ctx["geo_intel"]
    clean_df = ctx["clean"]

    city_adv = advisory_df[advisory_df["City"] == city]
    latest_ward_date = ward_df["Date"].max()
    city_wards = ward_df[(ward_df["City"] == city) & (ward_df["Date"] == latest_ward_date)]

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Wards Covered", f"{city_adv['Ward'].nunique()}", icon="📍", accent="blue", delay=0.0)
    with c2:
        metric_card("Languages", f"{len(SUPPORTED_LANGUAGES)}", icon="🌐", accent="cyan", delay=0.05)
    with c3:
        metric_card("Delivery Channels", f"{city_adv['Channel'].nunique()}", icon="📡", accent="purple", delay=0.10)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # ------------------------------------------------ Personalized advisory --
    with st.container(key="personal_adv_form_card"):
        section_title("Personalized Citizen Health Advisory", "🧑‍⚕️")
        st.markdown(
            "<div class='card-caption' style='margin-top:-8px;'>Enter a citizen's profile to generate a "
            "personal risk score and tailored recommendations, available in 5 languages.</div>",
            unsafe_allow_html=True,
        )

        f1, f2, f3, f4 = st.columns(4)
        with f1:
            age = st.number_input("Age", min_value=1, max_value=110, value=35, key="padv_age")
        with f2:
            condition = st.selectbox("Medical Condition", MEDICAL_CONDITIONS, key="padv_condition")
        with f3:
            location_options = ["City-wide (no specific ward)"] + list(city_wards["Ward"].unique())
            location = st.selectbox("Location (Ward)", location_options, key="padv_location")
        with f4:
            occupation = st.selectbox("Occupation", OCCUPATIONS, key="padv_occupation")

        lang_pick = st.radio("Output language", SUPPORTED_LANGUAGES, horizontal=True, key="padv_lang")
        generate = st.button("🩺  Generate Advisory", type="primary", key="padv_generate")

    result_key = f"padv_result_{city}"
    if generate:
        ward_row = None
        ward_lat = ward_lon = None
        ward_name = None
        if location != "City-wide (no specific ward)":
            ward_row = city_wards[city_wards["Ward"] == location].iloc[0]
            ward_lat, ward_lon = float(ward_row["lat"]), float(ward_row["lon"])
            ward_name = location

        forecast_aqi = _forecast_aqi_for(city, ward_row, clean_df)
        msg = _personal_agent.run(
            city=city, age=int(age), medical_condition=condition, occupation=occupation,
            forecast_aqi=forecast_aqi, ward=ward_name, ward_lat=ward_lat, ward_lon=ward_lon,
            geo_intel_df=geo_intel,
        )
        if msg.status != "ok":
            st.error(msg.payload.get("error", "Could not generate advisory."))
        else:
            st.session_state[result_key] = msg.payload

    result = st.session_state.get(result_key)
    if result:
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
        card_col, lang_col = st.columns([1.3, 1])
        with card_col:
            health_advisory_card(result, st.session_state.get("padv_lang", "English"))
        with lang_col:
            with st.container(key="personal_adv_alllang_card"):
                section_title("Health Alert — All Languages", "🌐")
                for lang in SUPPORTED_LANGUAGES:
                    reco = result["recommendations"][lang]
                    st.markdown(
                        f"<div class='card-caption'><b style='color:var(--text-1);'>{lang}:</b> {reco['health_alert']}</div>"
                        "<div style='height:8px;'></div>",
                        unsafe_allow_html=True,
                    )

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # ------------------------------------------------ Broadcast advisory (existing) --
    with st.container(key="adv_card"):
        section_title("Citizen Health Advisory — Multi-Channel, Multi-Language Broadcast", "🏥")

        ward_pick = st.selectbox("Ward", city_adv["Ward"].unique(), key="adv_ward")
        lang_pick2 = st.radio("Language", city_adv["Language"].unique(), horizontal=True, key="adv_lang")
        channel_pick = st.selectbox("Channel", city_adv["Channel"].unique(), key="adv_channel")

        msg_row = city_adv[
            (city_adv["Ward"] == ward_pick) & (city_adv["Language"] == lang_pick2) & (city_adv["Channel"] == channel_pick)
        ]
        if not msg_row.empty:
            r = msg_row.iloc[0]
            m = get_aqi_meta(r["AQI"])
            st.markdown(
                f"""
                <div style="margin-top:14px; padding:16px 18px; border-radius:14px;
                            background:{m['color']}14; border:1px solid {m['color']}44;">
                  <div style="font-size:13px; font-weight:700; color:{m['color']}; margin-bottom:8px;">
                    AQI {r['AQI']:.0f} — {r['Category']}
                  </div>
                  <div style="font-size:13.5px; color:var(--text-1); line-height:1.7; white-space:pre-line;">{r['Message'].replace(chr(92)+'n', chr(10))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown("<div class='small-caption'>No advisory found for this combination.</div>", unsafe_allow_html=True)

        st.markdown(
            "<div class='card-caption' style='margin-top:14px;'>Health-advisory translations are hand-written "
            "(not machine-translated) since mistranslated health guidance carries real risk.</div>",
            unsafe_allow_html=True,
        )

    with st.container(key="adv_all_card"):
        section_title(f"All Advisories — {city}", "📋")
        st.dataframe(
            city_adv[["Ward", "AQI", "Category", "Language", "Channel"]],
            use_container_width=True, hide_index=True,
        )
