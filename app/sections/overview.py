import pandas as pd
import streamlit as st

from app.components.metric_card import metric_card, section_title, badge, empty_state
from app.components.charts import aqi_trend_chart, source_pie, pollutant_timeline_chart, hotspot_bar, ward_map
from app.components.alerts import alert_row
from app.theme import get_aqi_meta, get_source_icon
from app.data_loader import get_forecasts


def render(ctx):
    city = ctx["city"]
    clean_df = ctx["clean"]
    attribution_df = ctx["attribution"]
    ward_df = ctx["ward"]
    enforcement_df = ctx["enforcement"]
    models = ctx["models"]
    feature_cols = ctx["feature_cols"]

    city_data = clean_df[clean_df["City"] == city].sort_values("Date")
    latest = city_data.iloc[-1]
    aqi_meta = get_aqi_meta(latest["AQI"])

    forecasts, _ = get_forecasts(city, city_data, latest, models, feature_cols)
    forecast_1d = forecasts[0]
    delta = forecast_1d - latest["AQI"]

    latest_ward_date = ward_df["Date"].max()
    city_wards = ward_df[(ward_df["City"] == city) & (ward_df["Date"] == latest_ward_date)]
    high_risk = int((city_wards["Simulated_AQI"] > 200).sum())
    if high_risk == 0:
        high_risk = int((city_wards["Simulated_AQI"] > 100).sum())

    city_enf = enforcement_df[enforcement_df["City"] == city]
    inspection_priority = int(city_enf["Enforceable"].sum())

    latest_att = attribution_df[attribution_df["City"] == city].sort_values("Date").iloc[-1]
    model_confidence = latest_att["confidence_pct"]

    # ---------------- Top metric row ----------------
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Current AQI", f"{latest['AQI']:.0f}", icon="🌫️", accent="blue",
                     sub=f"{aqi_meta['label']}", value_color=aqi_meta["color"], delay=0.00,
                     trend=city_data["AQI"].tail(14).tolist())
    with c2:
        metric_card("Forecast AQI (24h)", f"{forecast_1d:.0f}", icon="📈", accent="cyan",
                     delta=f"{delta:+.0f}", sub="vs. today", delay=0.05,
                     trend=city_data["AQI"].tail(7).tolist() + list(forecasts))
    with c3:
        metric_card("High Risk Areas", f"{high_risk}", icon="⚠️", accent="red",
                     sub=f"of {city_wards['Ward'].nunique()} wards monitored", delay=0.10)
    with c4:
        metric_card("Inspection Priority", f"{inspection_priority}", icon="🚨", accent="amber",
                     sub="sites flagged for action", delay=0.15)
    with c5:
        metric_card("Model Confidence", f"{model_confidence:.0f}%", icon="🧠", accent="purple",
                     sub="source attribution", delay=0.20)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # ---------------- Charts row 1 ----------------
    col1, col2 = st.columns([1.55, 1])
    with col1:
        with st.container(key="ov_trend_card"):
            section_title(f"{city} — AQI Trend (last 60 days)", "📊",
                          trailing_html=badge(f"Now: {latest['AQI']:.0f}", aqi_meta["color"]))
            st.plotly_chart(aqi_trend_chart(city_data), use_container_width=True, config={"displayModeBar": False})

    with col2:
        with st.container(key="ov_pie_card"):
            latest_att_row = attribution_df[attribution_df["City"] == city].sort_values("Date").iloc[-1]
            pct_cols = [c for c in attribution_df.columns if c.startswith("pct_")]
            source_vals = {c.replace("pct_", "").replace("_", " "): latest_att_row[c] for c in pct_cols}
            section_title("Pollution Sources (city-wide)", "🛰️")
            st.plotly_chart(source_pie(source_vals), use_container_width=True, config={"displayModeBar": False})

    # ---------------- Charts row 2 ----------------
    col3, col4 = st.columns([1, 1])
    with col3:
        with st.container(key="ov_forecast_card"):
            section_title("3-Day Forecast Snapshot", "🔮")
            fh1, fh2, fh3 = st.columns(3)
            for i, (col, h) in enumerate(zip([fh1, fh2, fh3], [1, 2, 3])):
                with col:
                    m = get_aqi_meta(forecasts[i])
                    st.markdown(
                        f"""
                        <div style="text-align:center; padding:12px 4px; border-radius:14px;
                                    background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);">
                          <div style="font-size:11px; color:var(--text-3); font-weight:600;">DAY +{h}</div>
                          <div style="font-size:24px; font-weight:800; color:{m['color']}; margin:4px 0;">{forecasts[i]:.0f}</div>
                          <div style="font-size:10.5px; color:var(--text-3);">{m['label']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.markdown("<div class='card-caption'>Powered by the horizon-1/2/3 gradient boosted forecasting models.</div>", unsafe_allow_html=True)

    with col4:
        with st.container(key="ov_weather_card"):
            section_title("Environmental Timeline", "🌤️")
            st.plotly_chart(pollutant_timeline_chart(city_data), use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                "<div class='card-caption'>Live temperature/humidity feeds aren't in the CPCB dataset — "
                "this tracks real pollutant concentrations (PM2.5, PM10, NO2, O3) as an environmental proxy.</div>",
                unsafe_allow_html=True,
            )

    # ---------------- Hotspot ranking ----------------
    with st.container(key="ov_hotspot_card"):
        section_title(f"{city} — Ward Hotspot Ranking", "🏆")
        st.plotly_chart(hotspot_bar(city_wards), use_container_width=True, config={"displayModeBar": False})
        st.markdown("<div class='card-caption'>Top wards ranked by simulated AQI severity (most recent snapshot).</div>", unsafe_allow_html=True)

    # ---------------- Bottom row: map + alerts + actions + predictions ----------------
    bcol1, bcol2 = st.columns([1.5, 1])
    with bcol1:
        with st.container(key="ov_map_card"):
            section_title(f"{city} — Live Pollution Map", "🗺️")
            st.plotly_chart(ward_map(city_wards, color_by="Top_Source", height=420), use_container_width=True, config={"displayModeBar": False})

    with bcol2:
        with st.container(key="ov_alerts_card"):
            section_title("Recent Alerts", "🔔")
            risky = city_wards.sort_values("Simulated_AQI", ascending=False).head(4)
            if risky.empty:
                empty_state("No active alerts", icon="✅", sub="All monitored wards are within normal range.")
            for i, (_, r) in enumerate(risky.iterrows()):
                m = get_aqi_meta(r["Simulated_AQI"])
                alert_row(
                    "🚨" if r["Simulated_AQI"] > 200 else "⚠️",
                    f"{r['Ward']} — AQI {r['Simulated_AQI']:.0f} ({m['label']})",
                    f"Dominant source: {r['Top_Source']} {get_source_icon(r['Top_Source'])}",
                    delay=i * 0.05,
                )

    ccol1, ccol2 = st.columns([1, 1])
    with ccol1:
        with st.container(key="ov_actions_card"):
            section_title("Recommended Actions", "✅")
            top_actions = city_enf.sort_values("Priority_Score", ascending=False).head(4)
            for i, (_, r) in enumerate(top_actions.iterrows()):
                alert_row("🛠️", f"{r['Ward']} — Priority {r['Priority_Score']:.0f}", r["Recommended_Action"], delay=i * 0.05)

    with ccol2:
        with st.container(key="ov_predictions_card"):
            section_title("Latest Predictions", "🔮")
            future_dates = [latest["Date"] + pd.Timedelta(days=h) for h in [1, 2, 3]]
            for i, (d, f) in enumerate(zip(future_dates, forecasts)):
                m = get_aqi_meta(f)
                alert_row(
                    "📅",
                    f"{d.strftime('%a, %d %b')} — AQI {f:.0f}",
                    f"Predicted category: {m['label']}",
                    delay=i * 0.05,
                )
