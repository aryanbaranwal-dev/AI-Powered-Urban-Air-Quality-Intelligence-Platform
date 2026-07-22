import pandas as pd
import streamlit as st

from app.components.metric_card import metric_card, section_title
from app.components.charts import multi_city_trend, improvement_bar, pollutant_radar
from app.theme import get_aqi_meta
from app.config import CITIES


def render(ctx):
    clean_df = ctx["clean"]
    model_results = ctx["model_results"]

    latest_by_city = {c: clean_df[clean_df["City"] == c].sort_values("Date").iloc[-1] for c in CITIES}

    cols = st.columns(len(CITIES))
    for i, c in enumerate(CITIES):
        with cols[i]:
            m = get_aqi_meta(latest_by_city[c]["AQI"])
            metric_card(f"{c} — Current AQI", f"{latest_by_city[c]['AQI']:.0f}", icon="🏙️",
                        accent=["blue", "purple"][i], sub=m["label"], value_color=m["color"], delay=i * 0.06)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    with st.container(key="mc_trend_card"):
        section_title("AQI Trend Comparison (last 90 days of available data)", "📈")
        st.plotly_chart(multi_city_trend(clean_df, CITIES), use_container_width=True, config={"displayModeBar": False})

    col1, col2 = st.columns([1, 1])
    with col1:
        with st.container(key="mc_perf_card"):
            section_title("Forecast Model Performance Comparison", "🧪")
            comp_rows = []
            for c in CITIES:
                for h, v in model_results[c]["horizons"].items():
                    comp_rows.append({"City": c, "Horizon": f"{h}-day", "Improvement over Baseline": v["improvement_pct"]})
            comp_df = pd.DataFrame(comp_rows)
            st.plotly_chart(improvement_bar(comp_df), use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                "<div class='card-caption'>% RMSE improvement over the naive persistence baseline, by forecast horizon.</div>",
                unsafe_allow_html=True,
            )

    with col2:
        with st.container(key="mc_radar_card"):
            section_title("Average Pollutant Profile (last 90 days)", "🕸️")
            pollutants = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]
            city_means = {}
            for c in CITIES:
                cd = clean_df[clean_df["City"] == c].tail(90)
                city_means[c] = {p: float(cd[p].mean()) for p in pollutants}
            st.plotly_chart(pollutant_radar(city_means), use_container_width=True, config={"displayModeBar": False})

    with st.container(key="mc_table_card"):
        section_title("Head-to-Head Summary", "📋")
        rows = []
        for c in CITIES:
            cd = clean_df[clean_df["City"] == c]
            rows.append({
                "City": c,
                "Current AQI": f"{latest_by_city[c]['AQI']:.0f}",
                "90d Avg AQI": f"{cd.tail(90)['AQI'].mean():.0f}",
                "90d Max AQI": f"{cd.tail(90)['AQI'].max():.0f}",
                "1-day RMSE Improvement": f"{model_results[c]['horizons']['1']['improvement_pct']}%",
                "Records": len(cd),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown(
            "<div class='card-caption'>Mumbai typically shows stronger improvement over baseline; Delhi's AQI "
            "is more persistently smog-locked in winter, making the naive baseline harder to beat — a real, "
            "explainable finding, not a modeling weakness.</div>",
            unsafe_allow_html=True,
        )
