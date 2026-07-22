import streamlit as st

from agents.intervention_agent import InterventionAgent, INTERVENTION_CATALOG
from app.components.metric_card import metric_card, section_title, badge
from app.components.charts import intervention_comparison_bar, aqi_before_after_gauge
from app.theme import get_aqi_meta, get_source_color, get_source_icon

_intervention_agent = InterventionAgent()

# attribution_output.csv (city-wide) and ward_simulated_geo.csv (per-ward)
# use slightly different column-name punctuation for the same 5
# categories; normalize both onto the same key set the InterventionAgent
# and INTERVENTION_CATALOG use ("Traffic", "Construction/Dust", ...).
def _city_contributions(row):
    return {
        "Traffic": float(row["pct_Traffic"]),
        "Construction/Dust": float(row["pct_Construction_Dust"]),
        "Industrial": float(row["pct_Industrial"]),
        "Crop/Biomass Burning": float(row["pct_Crop_Biomass Burning"]),
        "Secondary/Photochemical": float(row["pct_Secondary_Photochemical"]),
    }


def _ward_contributions(row):
    return {
        "Traffic": float(row["pct_Traffic"]),
        "Construction/Dust": float(row["pct_Construction Dust"]),
        "Industrial": float(row["pct_Industrial"]),
        "Crop/Biomass Burning": float(row["pct_Crop Biomass Burning"]),
        "Secondary/Photochemical": float(row["pct_Secondary Photochemical"]),
    }


def render(ctx):
    city = ctx["city"]
    attribution_df = ctx["attribution"]
    ward_df = ctx["ward"]

    latest_att = attribution_df[attribution_df["City"] == city].sort_values("Date").iloc[-1]

    latest_ward_date = ward_df["Date"].max()
    city_wards = ward_df[(ward_df["City"] == city) & (ward_df["Date"] == latest_ward_date)]

    with st.container(key="sim_scope_card"):
        section_title(f"{city}: Simulation Scope", "🎯")
        scope = st.radio("Simulate for", [f"{city} (city-wide)"] + list(city_wards["Ward"].unique()),
                          horizontal=True, label_visibility="collapsed")

        if scope == f"{city} (city-wide)":
            current_aqi = float(latest_att["AQI"])
            contributions = _city_contributions(latest_att)
            ward_type = None
        else:
            ward_row = city_wards[city_wards["Ward"] == scope].iloc[0]
            current_aqi = float(ward_row["Simulated_AQI"])
            contributions = _ward_contributions(ward_row)
            ward_type = ward_row["Ward_Type"]

        meta = get_aqi_meta(current_aqi)
        st.markdown(
            f"<div class='card-caption'>Baseline: <b style='color:{meta['color']};'>AQI {current_aqi:.0f} "
            f"({meta['label']})</b> · scenario starts from today's attributed source mix.</div>",
            unsafe_allow_html=True,
        )

    with st.container(key="sim_picker_card"):
        section_title("Select Interventions to Simulate", "🧪")
        cols = st.columns(4)
        selected = []
        for i, (name, spec) in enumerate(INTERVENTION_CATALOG.items()):
            with cols[i % 4]:
                checked = st.checkbox(f"{spec['icon']} {name}", key=f"sim_chk_{name}")
                st.markdown(f"<div class='card-caption' style='margin-top:-8px;'>{spec['description']}</div>",
                            unsafe_allow_html=True)
                if checked:
                    selected.append(name)

        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
        predict = st.button("▶️  Predict Impact", type="primary", use_container_width=False)

    result_key = f"sim_result_{city}_{scope}"
    if predict:
        if not selected:
            st.warning("Select at least one intervention before predicting.")
        else:
            msg = _intervention_agent.simulate(city, current_aqi, contributions, selected, ward_type=ward_type)
            if msg.status != "ok":
                st.error(msg.payload.get("error", "Simulation failed."))
            else:
                st.session_state[result_key] = msg.payload

    result = st.session_state.get(result_key)
    if not result:
        st.info("Pick one or more interventions above and click **Predict Impact** to see projected results.")
        return

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        m = get_aqi_meta(result["aqi_before"])
        metric_card("AQI Before", f"{result['aqi_before']:.0f}", icon="📍", accent="blue",
                     sub=m["label"], value_color=m["color"], delay=0.0)
    with c2:
        m = get_aqi_meta(result["aqi_after"])
        metric_card("AQI After", f"{result['aqi_after']:.0f}", icon="🎯", accent="green",
                     sub=m["label"], value_color=m["color"], delay=0.05)
    with c3:
        metric_card("Expected Reduction", f"{result['expected_reduction_points']:.0f} pts",
                     icon="📉", accent="cyan", sub=f"{result['expected_reduction_pct']:.1f}% lower", delay=0.10)
    with c4:
        metric_card("Effectiveness Score", f"{result['estimated_effectiveness_score']:.0f}/100",
                     icon="⚡", accent="amber", sub="reduction & health per cost unit", delay=0.15)

    c5, c6 = st.columns(2)
    with c5:
        metric_card("Estimated Health Benefit", result["estimated_health_benefit_band"],
                     icon="🏥", accent="purple",
                     sub=f"benefit index {result['estimated_health_benefit_index']:.0f}/100 (illustrative)", delay=0.0)
    with c6:
        lo, hi = result["estimated_cost_inr_per_day_range"]
        metric_card("Estimated Cost / Day", f"₹{lo/100000:.1f}L – ₹{hi/100000:.1f}L",
                     icon="💰", accent="red",
                     sub=f"{result['estimated_cost_tier']} tier · {result['estimated_lead_time_days']}d lead time", delay=0.05)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    chips = "".join(
        badge(name, "#3b82f6", icon=INTERVENTION_CATALOG[name]["icon"]) + " "
        for name in result["selected_interventions"]
    )
    st.markdown(f"<div style='margin:4px 0 14px 2px;'>{chips}</div>", unsafe_allow_html=True)

    gauge_col, bar_col = st.columns([1, 1.3])
    with gauge_col:
        with st.container(key="sim_gauge_card"):
            section_title("AQI Before → After", "🌡️")
            st.plotly_chart(
                aqi_before_after_gauge(result["aqi_before"], result["aqi_after"], height=300),
                use_container_width=True, config={"displayModeBar": False},
            )
            st.markdown(
                "<div class='card-caption'>White marker = current AQI. Colored bar = projected AQI after the "
                "selected interventions take effect.</div>", unsafe_allow_html=True,
            )

    with bar_col:
        with st.container(key="sim_bar_card"):
            section_title("Source Mix: Before vs After", "📊")
            st.plotly_chart(
                intervention_comparison_bar(result["contributions_before"], result["contributions_after"], height=340),
                use_container_width=True, config={"displayModeBar": False},
            )
            st.markdown(
                "<div class='card-caption'>Only the sources targeted by your selected interventions shrink — "
                "others stay at their baseline share.</div>", unsafe_allow_html=True,
            )

    with st.container(key="sim_note_card"):
        st.markdown(
            "<div class='card-caption'>⚠️ This simulator is a decision-support model: intervention effect "
            "sizes are informed, order-of-magnitude estimates from published Indian air-quality intervention "
            "studies, not measured outcomes. Health-benefit and cost figures are illustrative indices for "
            "comparing options, not epidemiological or procurement-grade numbers.</div>",
            unsafe_allow_html=True,
        )
