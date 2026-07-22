import streamlit as st

from app.components.metric_card import metric_card, section_title, badge
from app.theme import get_source_color, get_source_icon, get_theme


def render(ctx):
    city = ctx["city"]
    enforcement_df = ctx["enforcement"]

    city_enf = enforcement_df[enforcement_df["City"] == city].sort_values("Priority_Score", ascending=False)
    enforceable_n = int(city_enf["Enforceable"].sum())
    advisory_only_n = int((~city_enf["Enforceable"]).sum())
    avg_priority = city_enf["Priority_Score"].mean()

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Enforceable Sites", f"{enforceable_n}", icon="🟢", accent="green", delay=0.0)
    with c2:
        metric_card("Advisory-Only Sites", f"{advisory_only_n}", icon="🔵", accent="blue", delay=0.05)
    with c3:
        metric_card("Avg. Priority Score", f"{avg_priority:.1f}", icon="🎯", accent="amber", delay=0.10)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    with st.container(key="enf_list_card"):
        section_title(f"{city} — Prioritised Enforcement Action List", "🚨")
        for _, r in city_enf.iterrows():
            t = get_theme()
            enforceable = bool(r["Enforceable"])
            status_badge = badge("Enforceable", t["success"], icon="🟢") if enforceable else badge("Advisory Only", t["primary"], icon="🔵")
            trend_color = t["danger"] if r["Trend"] == "Worsening" else t["success"]
            source_badge = badge(r["Dominant_Source"], get_source_color(r["Dominant_Source"]), icon=get_source_icon(r["Dominant_Source"]))

            with st.expander(f"#{int(r['Rank'])} — {r['Ward']}   |   AQI {r['Current_AQI']:.0f}   |   Priority {r['Priority_Score']:.1f}"):
                top = st.columns([1, 1, 1])
                top[0].markdown(status_badge, unsafe_allow_html=True)
                top[1].markdown(source_badge, unsafe_allow_html=True)
                top[2].markdown(
                    f'<span class="badge" style="background:{trend_color}22;color:{trend_color};border:1px solid {trend_color}55;">'
                    f'{"📉" if r["Trend"]=="Worsening" else "📈"} {r["Trend"]}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Dominant source confidence:** {r['Source_Confidence_Pct']:.0f}%")
                    st.markdown(f"**Forecast tomorrow:** AQI {r['Forecast_Tomorrow_AQI']:.0f}")
                with c2:
                    st.markdown("**Recommended action**")
                    st.info(r["Recommended_Action"])

        st.markdown(
            "<div class='card-caption'>Priority = severity × actionability × forecast trend. Sources tagged "
            "'Advisory Only' (e.g. photochemical/weather-driven) route to public health alerts instead of "
            "enforcement, since there's no physical site to inspect.</div>",
            unsafe_allow_html=True,
        )

    with st.container(key="enf_table_card"):
        section_title("Full Enforcement Register", "📋")
        st.dataframe(
            city_enf[["Rank", "Ward", "Ward_Type", "Current_AQI", "Forecast_Tomorrow_AQI", "Trend",
                      "Dominant_Source", "Priority_Score", "Enforceable"]],
            use_container_width=True, hide_index=True,
        )
