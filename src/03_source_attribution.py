"""
Phase 4: Geospatial Pollution Source Attribution Engine (simplified proxy version).

WHAT THIS SCRIPT DOES (plain English):
Real "source attribution" (like Chemical Mass Balance / PMF receptor modeling) needs
detailed speciated sensor networks we don't have access to for a prototype.
Instead, we use a scientifically-grounded PROXY: pollutant RATIOS are known indicators
of different source types. This is a real, published lightweight technique used in
early-stage air quality science - just less precise than full receptor modeling.

For each day, we compute a "source score" (0-100) for each of 5 source categories:
  - Traffic       (NO2, CO heavy)
  - Construction/Dust (PM10 >> PM2.5)
  - Industrial    (SO2 heavy)
  - Crop/Biomass Burning (PM2.5 heavy, low NO2/CO, Oct-Nov season in Delhi)
  - Secondary/Photochemical (O3 heavy, everything else moderate)

Then we assign a CONFIDENCE score based on how "clean" the signal is (a day with one
dominant ratio = high confidence; a mixed day = lower confidence). This mirrors how
real attribution systems report uncertainty rather than false precision.

We also simulate WARD-LEVEL variation: since we only have city-level station data,
we distribute city AQI across synthetic wards using realistic land-use weighting
(e.g. industrial wards get an industrial-activity multiplier). This is clearly a
SIMULATED layer for demo purposes - flagged as such in the output.
"""

import pandas as pd
import numpy as np

DATA_PATH = "/home/claude/aqi_project/data/clean_aqi_combined.csv"
OUT_PATH = "/home/claude/aqi_project/data/attribution_output.csv"
WARD_OUT_PATH = "/home/claude/aqi_project/data/ward_simulated.csv"

df = pd.read_csv(DATA_PATH, parse_dates=["Date"])

# ---------- STEP 1: City-day level source attribution using pollutant ratios ----------
# IMPORTANT CALIBRATION NOTE:
# This dataset's pollutant concentrations are mathematically back-estimated from AQI
# (the source repo flags this explicitly), so they don't sit on standard real-world
# ug/m3 scales. Using fixed real-world thresholds (e.g. "SO2 > 60 = industrial") breaks
# down here. Instead we normalize each pollutant by its PERCENTILE RANK within this
# city's own data (0-1 scale) - this makes signals comparable regardless of the
# dataset's absolute scale, and is a more defensible approach given this limitation.

PERCENTILE_CACHE = {}

def get_percentile_ranks(city_name):
    """Precompute percentile rank (0-1) for each signal, per city, once.
    CRITICAL: every signal - including the PM10/PM2.5 coarse-fraction ratio - must be
    converted to a percentile rank so they're all on the same 0-1 scale. Without this,
    whichever raw signal happens to have a larger natural average (e.g. dust ratio
    averaged 1.18 vs ~0.5 for the others) wins almost every day regardless of the
    actual air chemistry - a scaling artifact, not a real finding."""
    if city_name in PERCENTILE_CACHE:
        return PERCENTILE_CACHE[city_name]
    city_data = df[df["City"] == city_name].copy()
    city_data["dust_ratio_raw"] = (
        (city_data["PM10"] - city_data["PM2.5"]) / city_data["PM2.5"].clip(lower=1)
    ).clip(lower=0)
    ranks = {}
    for col in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "dust_ratio_raw"]:
        ranks[col] = city_data[col].rank(pct=True)
        ranks[col].index = city_data.index
    PERCENTILE_CACHE[city_name] = ranks
    return ranks

def compute_raw_signals(city_df):
    """Pass 1: compute the 5 raw (un-ranked) source signals for every day of one city."""
    ranks = get_percentile_ranks(city_df["City"].iloc[0])
    idx = city_df.index
    month = city_df["Date"].dt.month
    city_name = city_df["City"].iloc[0]

    out = pd.DataFrame(index=idx)
    out["Traffic"] = (ranks["NO2"][idx] + ranks["CO"][idx]) / 2
    out["Construction/Dust"] = ranks["dust_ratio_raw"][idx]
    out["Industrial"] = ranks["SO2"][idx]
    seasonal_boost = np.where((city_name == "Delhi") & month.isin([10, 11]), 1.6, 0.5)
    out["Crop/Biomass Burning"] = ranks["PM2.5"][idx] * seasonal_boost
    out["Secondary/Photochemical"] = ranks["O3"][idx]
    return out

SOURCE_NAMES = ["Traffic", "Construction/Dust", "Industrial", "Crop/Biomass Burning", "Secondary/Photochemical"]

# Literature-informed baseline split for Indian metro pollution sources (broadly consistent
# with published SAFAR/TERI-style source-apportionment ranges for Indian cities - used here
# as a stabilizing PRIOR, not an exact citation). Anchoring to a realistic prior stops any
# single noisy day-level metric (like the dust ratio) from statistically dominating just
# because it happens to have more independent variance - a known failure mode of pure
# "winner-take-all" scoring, and the reason real hybrid attribution models blend a prior
# emission inventory with day-specific observed adjustments instead of relying on raw
# signal comparison alone.
BASELINE_PRIOR = {
    "Traffic": 0.30, "Construction/Dust": 0.20, "Industrial": 0.15,
    "Crop/Biomass Burning": 0.12, "Secondary/Photochemical": 0.23,
}
PRIOR_WEIGHT = 0.55   # how much we trust the general baseline vs. today's specific chemistry signal

all_city_attribution = []
for city in ["Delhi", "Mumbai"]:
    city_df = df[df["City"] == city].copy()
    raw_signals = compute_raw_signals(city_df)

    # Re-rank each *combined* source signal against its own history (per city) before
    # comparing across sources - so no source is favored just for having a lot of natural
    # spread (still useful for day-to-day sensitivity, now blended with the prior below).
    fair_ranked = raw_signals.rank(pct=True)  # each column now independently 0-1, equal spread
    day_specific = fair_ranked.div(fair_ranked.sum(axis=1), axis=0)  # normalize to sum 1 per day

    prior_row = pd.Series(BASELINE_PRIOR)[SOURCE_NAMES]
    blended = day_specific[SOURCE_NAMES] * (1 - PRIOR_WEIGHT) + prior_row.values * PRIOR_WEIGHT

    pct_df = (blended.div(blended.sum(axis=1), axis=0) * 100).round(1)
    pct_df.columns = [f"pct_{c.replace('/', '_')}" for c in pct_df.columns]

    sorted_vals = np.sort(pct_df.values, axis=1)[:, ::-1]
    dominance_gap = sorted_vals[:, 0] - sorted_vals[:, 1]
    confidence = np.clip(50 + dominance_gap * 1.3, 50, 95).round(1)

    top_source = pct_df.idxmax(axis=1).str.replace("pct_", "").str.replace("_", "/")

    city_attribution = pd.concat([
        city_df[["City", "Date", "AQI"]].reset_index(drop=True),
        pct_df.reset_index(drop=True)
    ], axis=1)
    city_attribution["top_source"] = top_source.values
    city_attribution["confidence_pct"] = confidence
    all_city_attribution.append(city_attribution)

attribution_df = pd.concat(all_city_attribution, ignore_index=True)
attribution_df.to_csv(OUT_PATH, index=False)

print("=" * 70)
print("SOURCE ATTRIBUTION - sample output (most recent 5 days per city)")
print("=" * 70)
for city in ["Delhi", "Mumbai"]:
    print(f"\n{city}:")
    print(attribution_df[attribution_df.City == city].tail(5)[
        ["Date", "AQI", "top_source", "confidence_pct"]].to_string(index=False))

print("\nTop-source distribution (how often each source 'wins', all days):")
print(attribution_df.groupby(["City", "top_source"]).size().unstack(fill_value=0))

# ---------- STEP 2: Simulate ward-level breakdown (SYNTHETIC - clearly labeled) ----------
# We don't have real ward-level sensors, so we simulate realistic wards with land-use
# character, and distribute the city's AQI + dominant source across them with noise.

WARDS = {
    "Delhi": [
        ("Anand Vihar",      "traffic_hub",     1.25),
        ("Okhla Industrial",  "industrial",      1.30),
        ("Dwarka",            "residential",     0.85),
        ("RK Puram",          "mixed",           1.00),
        ("Rohini",            "construction",    1.15),
        ("Lodhi Road",        "green_belt",      0.70),
    ],
    "Mumbai": [
        ("Andheri East",      "traffic_hub",     1.20),
        ("Chembur",           "industrial",      1.35),
        ("Bandra West",       "residential",     0.80),
        ("Powai",             "mixed",           0.95),
        ("Kurla",             "construction",    1.10),
        ("Colaba",            "green_belt",      0.75),
    ],
}

WARD_MULTIPLIER_BY_TYPE_SOURCE = {
    # ward_type: {source: extra multiplier} - encodes realistic land-use logic
    "traffic_hub":  {"Traffic": 1.6, "Construction/Dust": 1.0, "Industrial": 0.8, "Crop/Biomass Burning": 1.0, "Secondary/Photochemical": 1.0},
    "industrial":   {"Traffic": 0.9, "Construction/Dust": 1.0, "Industrial": 1.8, "Crop/Biomass Burning": 1.0, "Secondary/Photochemical": 1.0},
    "residential":  {"Traffic": 0.8, "Construction/Dust": 0.8, "Industrial": 0.6, "Crop/Biomass Burning": 1.0, "Secondary/Photochemical": 1.1},
    "mixed":        {"Traffic": 1.0, "Construction/Dust": 1.0, "Industrial": 1.0, "Crop/Biomass Burning": 1.0, "Secondary/Photochemical": 1.0},
    "construction": {"Traffic": 1.0, "Construction/Dust": 1.9, "Industrial": 0.9, "Crop/Biomass Burning": 1.0, "Secondary/Photochemical": 1.0},
    "green_belt":   {"Traffic": 0.6, "Construction/Dust": 0.6, "Industrial": 0.5, "Crop/Biomass Burning": 0.9, "Secondary/Photochemical": 1.0},
}

np.random.seed(42)
recent = attribution_df.groupby("City").tail(30)  # simulate wards for the most recent 30 days

ward_rows = []
for _, row in recent.iterrows():
    for ward_name, ward_type, base_mult in WARDS[row["City"]]:
        noise = np.random.normal(1.0, 0.06)
        ward_aqi = row["AQI"] * base_mult * noise
        source_mults = WARD_MULTIPLIER_BY_TYPE_SOURCE[ward_type]
        # Re-weight the city's source percentages using this ward's land-use multipliers
        pct_cols = {s: row[f"pct_{s.replace('/', '_')}"] for s in source_mults}
        weighted = {s: pct_cols[s] * source_mults[s] for s in pct_cols}
        total_w = sum(weighted.values()) or 1e-6
        weighted_pct = {s: round((v / total_w) * 100, 1) for s, v in weighted.items()}
        ward_top_source = max(weighted_pct, key=weighted_pct.get)

        ward_rows.append({
            "City": row["City"], "Date": row["Date"], "Ward": ward_name, "Ward_Type": ward_type,
            "Simulated_AQI": round(ward_aqi, 1), "Top_Source": ward_top_source,
            **{f"pct_{s.replace('/', ' ')}": v for s, v in weighted_pct.items()}
        })

ward_df = pd.DataFrame(ward_rows)
ward_df.to_csv(WARD_OUT_PATH, index=False)

print("\n" + "=" * 70)
print("SIMULATED WARD-LEVEL DATA (for dashboard maps) - sample, latest date")
print("=" * 70)
latest_date = ward_df["Date"].max()
print(ward_df[ward_df.Date == latest_date][["City", "Ward", "Ward_Type", "Simulated_AQI", "Top_Source"]].to_string(index=False))
print(f"\nSaved: {OUT_PATH}")
print(f"Saved: {WARD_OUT_PATH}  (NOTE: ward-level data is SIMULATED for demo purposes)")
