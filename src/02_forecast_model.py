"""
Phase 3: Hyperlocal-style AQI Forecasting Agent (city-level proxy).

WHAT THIS SCRIPT DOES (plain English):
1. Loads the clean data
2. Builds "features" - clues the model can learn from:
   - AQI from 1, 2, 3, 7 days ago (recent history)
   - Rolling 7-day average (smoothed trend)
   - Day of year / month (season/festival/winter patterns)
3. Builds a PERSISTENCE BASELINE: "tomorrow's AQI = today's AQI"
4. Trains a Random Forest model to predict AQI 1, 2, and 3 days ahead
5. Compares RMSE of model vs baseline -> proves our model adds real value
6. Saves the trained models so the dashboard can reuse them
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
import joblib

DATA_PATH = "/home/claude/aqi_project/data/clean_aqi_combined.csv"
MODEL_DIR = "/home/claude/aqi_project/models"

df = pd.read_csv(DATA_PATH, parse_dates=["Date"])

def build_features(city_df):
    city_df = city_df.sort_values("Date").reset_index(drop=True)
    city_df["lag_1"] = city_df["AQI"].shift(1)
    city_df["lag_2"] = city_df["AQI"].shift(2)
    city_df["lag_3"] = city_df["AQI"].shift(3)
    city_df["lag_7"] = city_df["AQI"].shift(7)
    city_df["rolling_mean_7"] = city_df["AQI"].shift(1).rolling(7).mean()
    city_df["rolling_std_7"] = city_df["AQI"].shift(1).rolling(7).std()
    city_df["month"] = city_df["Date"].dt.month
    city_df["day_of_year"] = city_df["Date"].dt.dayofyear
    city_df["is_winter"] = city_df["month"].isin([11, 12, 1, 2]).astype(int)
    # Pollutant lags (yesterday's readings are legitimate "known" inputs)
    for pol in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
        city_df[f"{pol}_lag1"] = city_df[pol].shift(1)
    return city_df

FEATURE_COLS = [
    "lag_1", "lag_2", "lag_3", "lag_7", "rolling_mean_7", "rolling_std_7",
    "month", "day_of_year", "is_winter",
    "PM2.5_lag1", "PM10_lag1", "NO2_lag1", "SO2_lag1", "CO_lag1", "O3_lag1"
]

all_results = {}

for city in ["Delhi", "Mumbai"]:
    city_df = df[df["City"] == city].copy()
    city_df = build_features(city_df)

    for horizon in [1, 2, 3]:  # predicting 1, 2, 3 days ahead
        city_df[f"target_{horizon}"] = city_df["AQI"].shift(-horizon)

    model_data = city_df.dropna(subset=FEATURE_COLS + [f"target_{h}" for h in [1,2,3]]).reset_index(drop=True)

    # Time-based split: train on first 85%, test on last 15% (never shuffle time series randomly!)
    split_idx = int(len(model_data) * 0.85)
    train, test = model_data.iloc[:split_idx], model_data.iloc[split_idx:]

    city_results = {"n_train": len(train), "n_test": len(test), "horizons": {}}

    for horizon in [1, 2, 3]:
        target_col = f"target_{horizon}"
        X_train, y_train = train[FEATURE_COLS], train[target_col]
        X_test, y_test = test[FEATURE_COLS], test[target_col]

        # --- Baseline: persistence (tomorrow = today) ---
        baseline_pred = X_test["lag_1"]  # yesterday's known value used as "today" proxy at day 0
        # Actually correct persistence for horizon h: last known AQI repeated forward
        baseline_pred = test["lag_1"]  # "last known AQI" naive forecast
        baseline_rmse = np.sqrt(mean_squared_error(y_test, baseline_pred))

        # --- Real model: Random Forest ---
        model = RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        model_rmse = np.sqrt(mean_squared_error(y_test, preds))

        improvement = (1 - model_rmse / baseline_rmse) * 100

        city_results["horizons"][horizon] = {
            "baseline_rmse": round(baseline_rmse, 2),
            "model_rmse": round(model_rmse, 2),
            "improvement_pct": round(improvement, 1)
        }

        # Save model
        joblib.dump(model, f"{MODEL_DIR}/{city.lower()}_horizon{horizon}.pkl")

    all_results[city] = city_results

# Save feature columns list for reuse in dashboard
joblib.dump(FEATURE_COLS, f"{MODEL_DIR}/feature_cols.pkl")

print("=" * 70)
print("FORECASTING MODEL RESULTS (RMSE = average AQI-point error, lower=better)")
print("=" * 70)
for city, res in all_results.items():
    print(f"\n{city}  (train: {res['n_train']} days, test: {res['n_test']} days)")
    for h, metrics in res["horizons"].items():
        print(f"  {h}-day ahead -> Baseline RMSE: {metrics['baseline_rmse']:>6} | "
              f"Model RMSE: {metrics['model_rmse']:>6} | "
              f"Improvement: {metrics['improvement_pct']:>5}%")

import json
with open("/home/claude/aqi_project/outputs/model_results.json", "w") as f:
    json.dump(all_results, f, indent=2)
print("\nSaved results -> outputs/model_results.json")
print("Saved trained models -> models/*.pkl")
