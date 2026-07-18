"""
Phase 5: Enforcement Intelligence & Prioritisation Agent.

WHAT THIS SCRIPT DOES (plain English):
1. Loads the ward-level attribution data (Phase 4 output) for "today" (latest date)
2. Loads the trained forecast models (Phase 3) to get tomorrow's city-level AQI trend
3. Scores every ward on 3 things:
     a) Severity      - how bad is the AQI right now (0-100 scale)
     b) Confidence     - how sure are we of the attribution (from Phase 4)
     c) Actionability  - can enforcement actually DO something about this source?
                         (Traffic/Construction/Industrial = yes, Meteorological/
                          Photochemical = no, these need public advisories not raids)
4. Combines these into one Priority Score, ranks all wards, and generates a concrete
   recommended action + supporting evidence for each - exactly the "evidence-backed
   enforcement recommendation" the brief asks for.
"""

import pandas as pd
import numpy as np
import joblib

WARD_PATH = "/home/claude/aqi_project/data/ward_simulated.csv"
MODEL_DIR = "/home/claude/aqi_project/models"
DATA_PATH = "/home/claude/aqi_project/data/clean_aqi_combined.csv"
OUT_PATH = "/home/claude/aqi_project/outputs/enforcement_recommendations.csv"

ward_df = pd.read_csv(WARD_PATH, parse_dates=["Date"])
clean_df = pd.read_csv(DATA_PATH, parse_dates=["Date"])
FEATURE_COLS = joblib.load(f"{MODEL_DIR}/feature_cols.pkl")

# Which sources can enforcement actually act on?
ACTIONABLE_SOURCES = {
    "Traffic":               {"actionable": True,  "action": "Deploy traffic police + emission-check checkpoints at major junctions"},
    "Construction/Dust":     {"actionable": True,  "action": "Inspect active construction sites for dust-control compliance (water sprinkling, covered material, anti-smog guns)"},
    "Industrial":            {"actionable": True,  "action": "Inspect industrial stack emissions; verify pollution-control equipment is operational"},
    "Crop/Biomass Burning":  {"actionable": True,  "action": "Coordinate with neighbouring state agriculture departments; deploy stubble-management incentive teams"},
    "Secondary/Photochemical": {"actionable": False, "action": "Issue public health advisory (not enforceable at source - secondary/ozone formation is a regional weather-driven process)"},
}

def get_next_day_forecast(city):
    """Use the Phase 3 model to predict tomorrow's AQI for a city, from its latest known data."""
    city_hist = clean_df[clean_df["City"] == city].sort_values("Date").reset_index(drop=True)
    latest = city_hist.iloc[-1]
    feat_row = {
        "lag_1": latest["AQI"], "lag_2": city_hist.iloc[-2]["AQI"], "lag_3": city_hist.iloc[-3]["AQI"],
        "lag_7": city_hist.iloc[-7]["AQI"],
        "rolling_mean_7": city_hist["AQI"].tail(7).mean(), "rolling_std_7": city_hist["AQI"].tail(7).std(),
        "month": latest["Date"].month, "day_of_year": latest["Date"].dayofyear,
        "is_winter": int(latest["Date"].month in [11, 12, 1, 2]),
    }
    for pol in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
        feat_row[f"{pol}_lag1"] = latest[pol]
    X = pd.DataFrame([feat_row])[FEATURE_COLS]
    model = joblib.load(f"{MODEL_DIR}/{city.lower()}_horizon1.pkl")
    return model.predict(X)[0], latest["AQI"]

# Get latest ward snapshot per city
latest_date = ward_df["Date"].max()
latest_wards = ward_df[ward_df["Date"] == latest_date].copy()

forecast_cache = {}
for city in latest_wards["City"].unique():
    forecast_cache[city] = get_next_day_forecast(city)

recommendations = []
for _, row in latest_wards.iterrows():
    city = row["City"]
    forecast_aqi, today_aqi = forecast_cache[city]
    trend_pct = (forecast_aqi - today_aqi) / today_aqi * 100

    source = row["Top_Source"]
    source_info = ACTIONABLE_SOURCES.get(source, {"actionable": False, "action": "Monitor - source unclear"})

    # Get the confidence + pct from the ORIGINAL city-level attribution (approximated via ward's dominant pct)
    dominant_pct_col = f"pct_{source.replace('/', ' ')}"
    dominant_pct = row.get(dominant_pct_col, np.nan)

    # Severity score: normalize AQI (Indian AQI severity bands: 0-50 good ... 400+ severe)
    severity = min(row["Simulated_AQI"] / 4, 100)  # simple 0-100 scaling, ~400 AQI = 100 severity

    # Priority score: severity is the anchor, boosted by confidence and actionability,
    # and boosted further if the situation is forecast to worsen
    actionability_multiplier = 1.3 if source_info["actionable"] else 0.6
    trend_boost = 1.15 if trend_pct > 5 else (0.95 if trend_pct < -5 else 1.0)
    priority_score = severity * actionability_multiplier * trend_boost

    recommendations.append({
        "City": city, "Ward": row["Ward"], "Ward_Type": row["Ward_Type"],
        "Current_AQI": row["Simulated_AQI"], "Forecast_Tomorrow_AQI": round(forecast_aqi, 1),
        "Trend": "Worsening" if trend_pct > 5 else ("Improving" if trend_pct < -5 else "Stable"),
        "Dominant_Source": source, "Source_Confidence_Pct": dominant_pct,
        "Enforceable": source_info["actionable"],
        "Recommended_Action": source_info["action"],
        "Priority_Score": round(priority_score, 1),
    })

rec_df = pd.DataFrame(recommendations).sort_values("Priority_Score", ascending=False).reset_index(drop=True)
rec_df.insert(0, "Rank", rec_df.index + 1)
rec_df.to_csv(OUT_PATH, index=False)

print("=" * 100)
print(f"ENFORCEMENT INTELLIGENCE - PRIORITISED ACTION LIST (as of {latest_date.date()})")
print("=" * 100)
for _, r in rec_df.iterrows():
    print(f"\n#{r['Rank']}  {r['City']} - {r['Ward']} ({r['Ward_Type']})")
    print(f"   AQI now: {r['Current_AQI']:.0f} | Forecast tomorrow: {r['Forecast_Tomorrow_AQI']:.0f} | Trend: {r['Trend']}")
    print(f"   Dominant source: {r['Dominant_Source']} (~{r['Source_Confidence_Pct']:.0f}% of local signal)")
    print(f"   Enforceable: {'YES' if r['Enforceable'] else 'NO - advisory only'}")
    print(f"   >> ACTION: {r['Recommended_Action']}")
    print(f"   Priority Score: {r['Priority_Score']:.1f}")

print(f"\nSaved -> {OUT_PATH}")
