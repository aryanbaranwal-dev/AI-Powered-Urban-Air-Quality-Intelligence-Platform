"""
Phase 7 helper: attach real lat/lon coordinates to our named wards.
(The ward_simulated.csv from Phase 4 has ward names/types but no coordinates -
 needed here so the dashboard can plot them on a map.)
"""
import pandas as pd

WARD_PATH = "/home/claude/aqi_project/data/ward_simulated.csv"
OUT_PATH = "/home/claude/aqi_project/data/ward_simulated_geo.csv"

# Real approximate coordinates for these well-known Delhi/Mumbai localities
WARD_COORDS = {
    "Anand Vihar": (28.6469, 77.3152),
    "Okhla Industrial": (28.5309, 77.2641),
    "Dwarka": (28.5730, 77.0720),
    "RK Puram": (28.5647, 77.1761),
    "Rohini": (28.7495, 77.0565),
    "Lodhi Road": (28.5918, 77.2273),
    "Andheri East": (19.1136, 72.8697),
    "Chembur": (19.0546, 72.8992),
    "Bandra West": (19.0596, 72.8295),
    "Powai": (19.1176, 72.9060),
    "Kurla": (19.0728, 72.8826),
    "Colaba": (18.9067, 72.8147),
}

df = pd.read_csv(WARD_PATH, parse_dates=["Date"])
df["lat"] = df["Ward"].map(lambda w: WARD_COORDS[w][0])
df["lon"] = df["Ward"].map(lambda w: WARD_COORDS[w][1])
df.to_csv(OUT_PATH, index=False)
print(f"Added coordinates for {df['Ward'].nunique()} wards. Saved -> {OUT_PATH}")
print(df[["City", "Ward", "lat", "lon"]].drop_duplicates().to_string(index=False))
