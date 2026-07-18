"""
Phase 7: AI-Powered Urban Air Quality Intelligence Dashboard
Ties together all 6 agents built in Phases 1-6 into one interactive app.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import joblib
import json
import os

st.set_page_config(page_title="Urban AQI Intelligence Platform", layout="wide", page_icon="🌫️")

# BASE is computed relative to this script's own location, so it works on any machine
# (previously hardcoded to the build sandbox path, which wouldn't exist elsewhere)
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------- Load all data (cached so it's fast) ----------------
@st.cache_data
def load_all():
    clean = pd.read_csv(f"{BASE}/data/clean_aqi_combined.csv", parse_dates=["Date"])
    attribution = pd.read_csv(f"{BASE}/data/attribution_output.csv", parse_dates=["Date"])
    ward = pd.read_csv(f"{BASE}/data/ward_simulated_geo.csv", parse_dates=["Date"])
    enforcement = pd.read_csv(f"{BASE}/outputs/enforcement_recommendations.csv")
    advisory = pd.read_csv(f"{BASE}/outputs/citizen_advisories.csv")
    with open(f"{BASE}/outputs/model_results.json") as f:
        model_results = json.load(f)
    feature_cols = joblib.load(f"{BASE}/models/feature_cols.pkl")
    return clean, attribution, ward, enforcement, advisory, model_results, feature_cols

clean_df, attribution_df, ward_df, enforcement_df, advisory_df, model_results, FEATURE_COLS = load_all()

@st.cache_resource
def load_models():
    models = {}
    for city in ["delhi", "mumbai"]:
        for h in [1, 2, 3]:
            models[f"{city}_h{h}"] = joblib.load(f"{BASE}/models/{city}_horizon{h}.pkl")
    return models

models = load_models()

# ---------------- Sidebar ----------------
st.sidebar.title("🌫️ AQI Intelligence Platform")
st.sidebar.caption("AI-powered urban air quality intelligence for smart-city intervention")
city_choice = st.sidebar.selectbox("Select City", ["Delhi", "Mumbai"])
st.sidebar.markdown("---")
st.sidebar.markdown("**Built on real CPCB data** (rohanrao/air-quality-data-in-india)")
st.sidebar.markdown("6 chained AI agents: Forecast → Attribution → Enforcement → Advisory")

# ---------------- Header ----------------
st.title("AI-Powered Urban Air Quality Intelligence")
st.caption("Geospatial attribution, hyperlocal forecasting, and enforcement intelligence for smart cities")

city_data = clean_df[clean_df["City"] == city_choice].sort_values("Date")
latest = city_data.iloc[-1]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current AQI", f"{latest['AQI']:.0f}")
col2.metric("PM2.5", f"{latest['PM2.5']:.0f} µg/m³")
col3.metric("PM10", f"{latest['PM10']:.0f} µg/m³")
model_1d = models[f"{city_choice.lower()}_h1"]
feat_row = {
    "lag_1": latest["AQI"], "lag_2": city_data.iloc[-2]["AQI"], "lag_3": city_data.iloc[-3]["AQI"],
    "lag_7": city_data.iloc[-7]["AQI"], "rolling_mean_7": city_data["AQI"].tail(7).mean(),
    "rolling_std_7": city_data["AQI"].tail(7).std(), "month": latest["Date"].month,
    "day_of_year": latest["Date"].dayofyear, "is_winter": int(latest["Date"].month in [11,12,1,2]),
}
for pol in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
    feat_row[f"{pol}_lag1"] = latest[pol]
X = pd.DataFrame([feat_row])[FEATURE_COLS]
forecast_1d = model_1d.predict(X)[0]
delta = forecast_1d - latest["AQI"]
col4.metric("Tomorrow's Forecast", f"{forecast_1d:.0f}", f"{delta:+.0f}")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Hyperlocal Forecast", "🔬 Source Attribution", "🚨 Enforcement Intelligence",
    "📢 Citizen Advisory", "🌆 Multi-City Comparison"
])

# ==================== TAB 1: FORECAST ====================
with tab1:
    st.subheader(f"{city_choice}: 24-72 Hour AQI Forecast vs. Persistence Baseline")

    horizons = [1, 2, 3]
    forecasts = []
    for h in horizons:
        m = models[f"{city_choice.lower()}_h{h}"]
        forecasts.append(m.predict(X)[0])

    hist_tail = city_data.tail(30)
    future_dates = [latest["Date"] + pd.Timedelta(days=h) for h in horizons]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist_tail["Date"], y=hist_tail["AQI"], mode="lines+markers",
                              name="Historical AQI", line=dict(color="#4C78A8")))
    fig.add_trace(go.Scatter(x=[latest["Date"]] + future_dates, y=[latest["AQI"]] + forecasts,
                              mode="lines+markers", name="Forecast", line=dict(color="#E45756", dash="dash")))
    fig.add_trace(go.Scatter(x=[latest["Date"]] + future_dates, y=[latest["AQI"]]*4,
                              mode="lines", name="Persistence Baseline", line=dict(color="gray", dash="dot")))
    fig.update_layout(height=420, xaxis_title="Date", yaxis_title="AQI", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Model Performance vs. Baseline (RMSE = avg. AQI-point error, lower is better)")
    res = model_results[city_choice]["horizons"]
    perf_df = pd.DataFrame([
        {"Horizon": f"{h}-day", "Baseline RMSE": v["baseline_rmse"], "Model RMSE": v["model_rmse"],
         "Improvement": f"{v['improvement_pct']}%"} for h, v in res.items()
    ])
    st.dataframe(perf_df, use_container_width=True, hide_index=True)
    st.caption("Model trained on 85% historical data, tested on the most recent 15% (strict time-based split, no data leakage).")

# ==================== TAB 2: SOURCE ATTRIBUTION ====================
with tab2:
    st.subheader(f"{city_choice}: Ward-Level Pollution Source Attribution")
    latest_ward_date = ward_df["Date"].max()
    city_wards = ward_df[(ward_df["City"] == city_choice) & (ward_df["Date"] == latest_ward_date)]

    map_col, chart_col = st.columns([1.2, 1])
    with map_col:
        fig_map = px.scatter_mapbox(
            city_wards, lat="lat", lon="lon", size="Simulated_AQI", color="Top_Source",
            hover_name="Ward", hover_data={"Simulated_AQI": True, "lat": False, "lon": False},
            zoom=10, height=450, size_max=30,
        )
        fig_map.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_map, use_container_width=True)
        st.caption("Bubble size = AQI severity. Color = dominant pollution source. Zone-level split is a simulated layer (real ward sensor data isn't public); city-level attribution is chemistry-derived from real pollutant readings.")

    with chart_col:
        selected_ward = st.selectbox("Select a ward for detailed breakdown", city_wards["Ward"].unique())
        ward_row = city_wards[city_wards["Ward"] == selected_ward].iloc[0]
        pct_cols = [c for c in ward_df.columns if c.startswith("pct_")]
        source_vals = {c.replace("pct_", ""): ward_row[c] for c in pct_cols}
        fig_pie = px.pie(names=list(source_vals.keys()), values=list(source_vals.values()),
                          title=f"{selected_ward} - Source Breakdown", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
        st.metric("Dominant Source", ward_row["Top_Source"])

# ==================== TAB 3: ENFORCEMENT ====================
with tab3:
    st.subheader("Prioritised Enforcement Action List")
    city_enf = enforcement_df[enforcement_df["City"] == city_choice].sort_values("Priority_Score", ascending=False)
    for _, r in city_enf.iterrows():
        badge = "🟢 Enforceable" if r["Enforceable"] else "🔵 Advisory Only"
        with st.expander(f"#{r['Rank']} — {r['Ward']} | AQI {r['Current_AQI']:.0f} | Priority Score {r['Priority_Score']:.1f} | {badge}"):
            c1, c2 = st.columns(2)
            c1.write(f"**Dominant source:** {r['Dominant_Source']} (~{r['Source_Confidence_Pct']:.0f}%)")
            c1.write(f"**Trend:** {r['Trend']} (tomorrow forecast: {r['Forecast_Tomorrow_AQI']:.0f})")
            c2.write(f"**Recommended action:**")
            c2.info(r["Recommended_Action"])
    st.caption("Priority = severity × actionability × forecast trend. Sources tagged 'Advisory Only' (e.g. photochemical/weather-driven) route to public health alerts instead of enforcement, since there's no physical site to inspect.")

# ==================== TAB 4: CITIZEN ADVISORY ====================
with tab4:
    st.subheader("Citizen Health Advisory — Multi-Channel, Multi-Language")
    city_adv = advisory_df[advisory_df["City"] == city_choice]
    ward_pick = st.selectbox("Ward", city_adv["Ward"].unique(), key="adv_ward")
    lang_pick = st.radio("Language", city_adv["Language"].unique(), horizontal=True)
    channel_pick = st.selectbox("Channel", city_adv["Channel"].unique())

    msg_row = city_adv[(city_adv["Ward"] == ward_pick) & (city_adv["Language"] == lang_pick) &
                        (city_adv["Channel"] == channel_pick)]
    if not msg_row.empty:
        r = msg_row.iloc[0]
        st.markdown(f"**AQI: {r['AQI']:.0f} — {r['Category']}**")
        st.success(r["Message"].replace("\\n", "\n\n"))
    st.caption("Health-advisory translations are hand-written (not machine-translated) since mistranslated health guidance carries real risk.")

# ==================== TAB 5: MULTI-CITY COMPARISON ====================
with tab5:
    st.subheader("Multi-City Comparative Intelligence")
    fig_cmp = go.Figure()
    for c in ["Delhi", "Mumbai"]:
        cd = clean_df[clean_df["City"] == c].tail(90)
        fig_cmp.add_trace(go.Scatter(x=cd["Date"], y=cd["AQI"], mode="lines", name=c))
    fig_cmp.update_layout(height=420, title="AQI Trend (last 90 days of available data)", xaxis_title="Date", yaxis_title="AQI")
    st.plotly_chart(fig_cmp, use_container_width=True)

    st.markdown("#### Forecast Model Performance Comparison")
    comp_rows = []
    for c in ["Delhi", "Mumbai"]:
        for h, v in model_results[c]["horizons"].items():
            comp_rows.append({"City": c, "Horizon": f"{h}-day", "Improvement over Baseline": v["improvement_pct"]})
    comp_df = pd.DataFrame(comp_rows)
    fig_bar = px.bar(comp_df, x="Horizon", y="Improvement over Baseline", color="City", barmode="group",
                      title="% RMSE Improvement over Naive Baseline")
    st.plotly_chart(fig_bar, use_container_width=True)
    st.caption("Mumbai shows stronger improvement over baseline; Delhi's AQI is more persistently smog-locked in winter, making the naive baseline harder to beat — a real, explainable finding, not a modeling weakness.")

st.markdown("---")
st.caption("Prototype built on real CPCB air quality data. Ward-level and enforcement-source layers are simulated for demonstration (documented in project report). Built for Smart Cities / Environmental Intelligence hackathon submission.")
