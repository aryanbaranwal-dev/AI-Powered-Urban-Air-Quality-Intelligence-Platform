"""
All disk I/O in one place. Paths are resolved relative to this file so the
app runs the same way regardless of the machine / working directory it's
launched from.
"""
import json
import os

import joblib
import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # aqi_project/


@st.cache_data(show_spinner=False)
def load_all():
    clean = pd.read_csv(f"{BASE}/data/clean_aqi_combined.csv", parse_dates=["Date"])
    attribution = pd.read_csv(f"{BASE}/data/attribution_output.csv", parse_dates=["Date"])
    ward = pd.read_csv(f"{BASE}/data/ward_simulated_geo.csv", parse_dates=["Date"])
    geo_intel = pd.read_csv(f"{BASE}/data/geo_intelligence.csv")
    geo_wards = pd.read_csv(f"{BASE}/data/geo_wards.csv")
    enforcement = pd.read_csv(f"{BASE}/outputs/enforcement_recommendations.csv")
    advisory = pd.read_csv(f"{BASE}/outputs/citizen_advisories.csv")
    with open(f"{BASE}/outputs/model_results.json") as f:
        model_results = json.load(f)
    feature_cols = joblib.load(f"{BASE}/models/feature_cols.pkl")
    return {
        "clean": clean,
        "attribution": attribution,
        "ward": ward,
        "geo_intel": geo_intel,
        "geo_wards": geo_wards,
        "enforcement": enforcement,
        "advisory": advisory,
        "model_results": model_results,
        "feature_cols": feature_cols,
    }


@st.cache_resource(show_spinner=False)
def load_models():
    models = {}
    for city in ["delhi", "mumbai"]:
        for h in [1, 2, 3]:
            models[f"{city}_h{h}"] = joblib.load(f"{BASE}/models/{city}_horizon{h}.pkl")
    return models


def build_feature_row(city_data: pd.DataFrame, latest: pd.Series, feature_cols) -> pd.DataFrame:
    """Rebuild the exact feature row the forecasting models were trained on."""
    feat_row = {
        "lag_1": latest["AQI"],
        "lag_2": city_data.iloc[-2]["AQI"],
        "lag_3": city_data.iloc[-3]["AQI"],
        "lag_7": city_data.iloc[-7]["AQI"],
        "rolling_mean_7": city_data["AQI"].tail(7).mean(),
        "rolling_std_7": city_data["AQI"].tail(7).std(),
        "month": latest["Date"].month,
        "day_of_year": latest["Date"].dayofyear,
        "is_winter": int(latest["Date"].month in [11, 12, 1, 2]),
    }
    for pol in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
        feat_row[f"{pol}_lag1"] = latest[pol]
    return pd.DataFrame([feat_row])[feature_cols]


def get_forecasts(city_choice: str, city_data: pd.DataFrame, latest: pd.Series, models, feature_cols):
    """Returns list of predicted AQI for horizon 1, 2, 3 days ahead."""
    X = build_feature_row(city_data, latest, feature_cols)
    preds = []
    for h in [1, 2, 3]:
        m = models[f"{city_choice.lower()}_h{h}"]
        preds.append(float(m.predict(X)[0]))
    return preds, X
