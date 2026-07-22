import pandas as pd
import streamlit as st

from app.components.metric_card import metric_card, section_title
from app.components.charts import forecast_chart
from app.components.xai_card import xai_forecast_card
from app.theme import get_aqi_meta
from app.data_loader import get_forecasts, build_feature_row
from agents.forecast_agent import ForecastAgent


def render(ctx):
    city = ctx["city"]
    clean_df = ctx["clean"]
    models = ctx["models"]
    feature_cols = ctx["feature_cols"]
    model_results = ctx["model_results"]

    city_data = clean_df[clean_df["City"] == city].sort_values("Date")
    latest = city_data.iloc[-1]

    forecasts, _ = get_forecasts(city, city_data, latest, models, feature_cols)
    future_dates = [latest["Date"] + pd.Timedelta(days=h) for h in [1, 2, 3]]

    c1, c2, c3 = st.columns(3)
    for i, (col, h) in enumerate(zip([c1, c2, c3], [1, 2, 3])):
        with col:
            m = get_aqi_meta(forecasts[i])
            delta = forecasts[i] - latest["AQI"]
            metric_card(
                f"Day +{h} Forecast", f"{forecasts[i]:.0f}", icon="📈",
                accent=["blue", "cyan", "purple"][i], delta=f"{delta:+.0f}",
                sub=m["label"], value_color=m["color"], delay=i * 0.06,
            )

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------- Explainable AI cards ----
    section_title("Explainable AI — Why the model predicts this", "🔍")
    fc_msg = ForecastAgent().run(
        city=city, city_data=city_data, latest=latest, models=models,
        feature_cols=feature_cols, build_feature_row=build_feature_row,
    )
    if fc_msg.status == "ok":
        xcols = st.columns(3)
        for i, pred in enumerate(fc_msg.payload["predictions"]):
            with xcols[i]:
                xai_forecast_card(pred["horizon"], pred, delay=i * 0.07)
        st.markdown(
            "<div class='card-caption' style='margin-top:8px;'>Every prediction is explained with a "
            "SHAP-like feature-attribution method — see the <b>Multi-Agent AI Console</b> page for the "
            "full agent pipeline and raw JSON.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning(f"Explainability layer unavailable: {fc_msg.payload.get('error')}")

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    with st.container(key="fc_chart_card"):
        section_title(f"{city}: 24–72 Hour AQI Forecast vs. Persistence Baseline", "📊")
        st.plotly_chart(forecast_chart(city_data, latest, forecasts, future_dates), use_container_width=True, config={"displayModeBar": False})

    with st.container(key="fc_perf_card"):
        section_title("Model Performance vs. Baseline", "🧪")
        st.markdown("<div class='card-caption'>RMSE = average AQI-point error across the held-out test window (lower is better).</div>", unsafe_allow_html=True)
        res = model_results[city]["horizons"]
        perf_df = pd.DataFrame([
            {"Horizon": f"{h}-day", "Baseline RMSE": v["baseline_rmse"], "Model RMSE": v["model_rmse"],
             "Improvement": f"{v['improvement_pct']}%"} for h, v in res.items()
        ])
        st.dataframe(perf_df, use_container_width=True, hide_index=True)
        st.markdown(
            "<div class='card-caption'>Model trained on 85% historical data, tested on the most recent 15% "
            "(strict time-based split — no data leakage).</div>",
            unsafe_allow_html=True,
        )

    with st.container(key="fc_notes_card"):
        section_title("How this forecast works", "ℹ️")
        st.markdown(
            """
            <div class="small-caption" style="line-height:1.7;">
            Three gradient-boosted regressors (1-day, 2-day, 3-day horizon) are trained on lagged AQI values,
            rolling statistics, seasonality features, and same-day pollutant concentrations. Each horizon is
            benchmarked against a naive <b>persistence baseline</b> (tomorrow = today) — the model must beat
            that baseline to be useful, which is what the RMSE comparison above verifies.
            </div>
            """,
            unsafe_allow_html=True,
        )
