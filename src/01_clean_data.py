"""
Phase 2 (REVISED): Clean the REAL, independently-measured CPCB dataset.

WHY WE SWITCHED DATA SOURCES:
Our first dataset (cp099/India-Air-Quality-Dataset) turned out to have pollutant
values that were mathematically back-calculated from AQI (confirmed: every
pollutant/AQI ratio had a standard deviation of ~0, meaning zero real information
beyond AQI itself). That's fine for a simple forecast, but useless for source
attribution, which NEEDS pollutants that move somewhat independently of each other.

This dataset (adityarc19/aqi-india, originally from Kaggle's well-known
"rohanrao/air-quality-data-in-india", sourced from CPCB) has genuine station
measurements: PM2.5, PM10, NO, NO2, NOx, NH3, CO, SO2, O3, Benzene, Toluene, Xylene.
Correlations between pollutants are realistic (e.g. PM2.5-PM10 correlate at 0.86,
not 1.0), confirming real independent variation - what we need.

Trade-off: this dataset only covers 2015-2020 (vs 2018-2024 before), and has some
missing values (real sensors have outages) - both of which we handle below.
"""

import pandas as pd
import numpy as np

RAW_PATH = "/home/claude/aqi_project/data/city_day_real.csv"
OUT_PATH = "/home/claude/aqi_project/data/clean_aqi_combined.csv"

CITIES = ["Delhi", "Mumbai"]
POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]

df = pd.read_csv(RAW_PATH, parse_dates=["Date"])
df = df[df["City"].isin(CITIES)].copy()

# Keep only rows where AQI is present (our forecast target)
df = df.dropna(subset=["AQI"]).reset_index(drop=True)

# Real sensors have gaps. For pollutant columns, forward-fill small gaps (<=3 days)
# per city, then drop any remaining rows that still have gaps in key pollutants.
df = df.sort_values(["City", "Date"]).reset_index(drop=True)
for city in CITIES:
    mask = df["City"] == city
    df.loc[mask, POLLUTANTS] = df.loc[mask, POLLUTANTS].ffill(limit=3)

df = df.dropna(subset=POLLUTANTS).reset_index(drop=True)
df = df[["City", "Date", "AQI"] + POLLUTANTS].drop_duplicates()

df.to_csv(OUT_PATH, index=False)

print("=" * 60)
print("CLEAN DATA SUMMARY (real, independently-measured pollutants)")
print("=" * 60)
for city in CITIES:
    sub = df[df["City"] == city]
    print(f"\n{city}:")
    print(f"  Rows: {len(sub)}")
    print(f"  Date range: {sub['Date'].min().date()} to {sub['Date'].max().date()}")
    print(f"  AQI  -> min: {sub['AQI'].min():.0f}, max: {sub['AQI'].max():.0f}, mean: {sub['AQI'].mean():.1f}")

print(f"\nSaved -> {OUT_PATH}")
print(f"Total combined rows: {len(df)}")
