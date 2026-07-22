import streamlit as st
import plotly.graph_objects as go

from agents.attribution_agent import AttributionAgent
from app.components.metric_card import metric_card, section_title, badge
from app.components.charts import source_pie, source_sankey, ward_map, hex_to_rgba
from app.components.xai_card import xai_attribution_card
from app.theme import apply_fig_theme, get_source_color, get_source_icon
from app.config import ACCENT_BLUE, ACCENT_CYAN, ACCENT_PURPLE

_attribution_agent = AttributionAgent()


def render(ctx):
    city = ctx["city"]
    ward_df = ctx["ward"]
    attribution_df = ctx["attribution"]

    latest_ward_date = ward_df["Date"].max()
    city_wards = ward_df[(ward_df["City"] == city) & (ward_df["Date"] == latest_ward_date)]

    latest_att = attribution_df[attribution_df["City"] == city].sort_values("Date").iloc[-1]

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Dominant City Source", latest_att["top_source"], icon=get_source_icon(latest_att["top_source"]),
                     accent="blue", sub=f"{latest_att['confidence_pct']:.0f}% confidence", delay=0.0)
    with c2:
        metric_card("Wards Monitored", f"{city_wards['Ward'].nunique()}", icon="📍", accent="cyan", delay=0.05)
    with c3:
        dominant_ward_source = city_wards["Top_Source"].mode()[0] if not city_wards.empty else "—"
        metric_card("Most Common Ward Source", dominant_ward_source, icon=get_source_icon(dominant_ward_source),
                     accent="purple", delay=0.10)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    selected_ward = st.selectbox("Select a ward for detailed source attribution", city_wards["Ward"].unique())
    ward_row = city_wards[city_wards["Ward"] == selected_ward].iloc[0]

    # Explainable AI: contributions + confidence + real geospatial evidence
    # (nearby roads, traffic density, wind, construction count, industrial
    # distance) + a per-source natural-language justification.
    explanation = _attribution_agent.explain_ward(city, ward_row, ctx["geo_intel"]).payload

    map_col, chart_col = st.columns([1.3, 1])
    with map_col:
        with st.container(key="attr_map_card"):
            section_title(f"{city}: Ward-Level Pollution Source Map", "🛰️")
            st.plotly_chart(ward_map(city_wards, color_by="Top_Source", height=440), use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                "<div class='card-caption'>Bubble size = AQI severity. Color = dominant pollution source. "
                "Zone-level split is a simulated layer (real ward sensor data isn't public); city-level "
                "attribution is chemistry-derived from real pollutant readings.</div>",
                unsafe_allow_html=True,
            )

    with chart_col:
        with st.container(key="attr_pie_card"):
            section_title(f"{selected_ward}: Source Breakdown", "🔬")
            pct_cols = [c for c in ward_df.columns if c.startswith("pct_")]
            source_vals = {c.replace("pct_", ""): ward_row[c] for c in pct_cols}
            st.plotly_chart(source_pie(source_vals, height=280), use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                badge(ward_row["Top_Source"], get_source_color(ward_row["Top_Source"]), icon=get_source_icon(ward_row["Top_Source"])),
                unsafe_allow_html=True,
            )

    sankey_col, evidence_col = st.columns([1.3, 1])
    with sankey_col:
        with st.container(key="attr_sankey_card"):
            section_title(f"{selected_ward}: Source → AQI Flow", "🌊")
            st.plotly_chart(
                source_sankey(explanation["contributions_pct"], selected_ward, explanation["aqi"], height=380),
                use_container_width=True, config={"displayModeBar": False},
            )
            st.markdown(
                "<div class='card-caption'>Flow width = each source's share of the ward's current pollution "
                "load. Same underlying percentages as the pie chart, read as a causal flow into today's AQI.</div>",
                unsafe_allow_html=True,
            )

    with evidence_col:
        xai_attribution_card(explanation)

    with st.container(key="attr_trend_card"):
        section_title(f"{city}: City-Wide Source Mix Trend (last 60 days)", "📈")
        city_att = attribution_df[attribution_df["City"] == city].sort_values("Date").tail(60)
        pct_cols = [c for c in attribution_df.columns if c.startswith("pct_")]
        colors = [ACCENT_BLUE, "#f59e0b", "#ef4444", "#84cc16", ACCENT_PURPLE]
        fig = go.Figure()
        for i, c in enumerate(pct_cols):
            fig.add_trace(go.Scatter(
                x=city_att["Date"], y=city_att[c], mode="lines", name=c.replace("pct_", "").replace("_", " "),
                stackgroup="one", line=dict(width=0.6, color=colors[i % len(colors)]),
                fillcolor=hex_to_rgba(colors[i % len(colors)], 0.35),
            ))
        fig.update_layout(xaxis_title="Date", yaxis_title="Share (%)")
        st.plotly_chart(apply_fig_theme(fig, 360), use_container_width=True, config={"displayModeBar": False})
        st.markdown("<div class='card-caption'>Stacked share of each pollution source in the city-level attribution model over time.</div>", unsafe_allow_html=True)
