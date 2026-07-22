"""
Evidence Engine — grounds source-attribution percentages in checkable
geospatial + meteorological signals, so the Attribution Agent's output
is explainable rather than a black-box percentage.

Design intent
-------------
Every number produced here is either:
  (a) REAL — computed via haversine distance / point-in-radius counts
      against the actual geo_intelligence.csv point layer (roads,
      construction sites, industrial sites), or
  (b) SIMULATED but DETERMINISTIC — a meteorological wind layer, which
      isn't in the source datasets, seeded from (city, date, ward) so
      it's stable across reruns and clearly labeled as such. This is
      the same "simulated ward layer" disclosure already used elsewhere
      in this project (see app/sections/attribution.py caption).

Nothing here is randomly re-rolled per page load — same inputs always
produce the same evidence, which is what makes it usable as "evidence"
at all.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

EARTH_RADIUS_KM = 6371.0
NEARBY_RADIUS_KM = 3.0  # "nearby" = within this radius of the ward centroid

COMPASS_DIRECTIONS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


@dataclass
class WardEvidence:
    ward: str
    city: str
    nearby_roads: int
    traffic_density_index: float  # 0-1, derived from road count + ward type
    wind_direction: str
    wind_direction_deg: int
    wind_speed_kmh: float
    construction_site_count: int
    industrial_distance_km: Optional[float]
    nearest_industrial_site: Optional[str]

    def as_dict(self) -> Dict:
        return {
            "Nearby Roads": self.nearby_roads,
            "Traffic Density": round(self.traffic_density_index, 2),
            "Wind Direction": f"{self.wind_direction} ({self.wind_direction_deg}°) · {self.wind_speed_kmh:.0f} km/h",
            "Construction Count": self.construction_site_count,
            "Industrial Distance": (
                f"{self.industrial_distance_km:.1f} km ({self.nearest_industrial_site})"
                if self.industrial_distance_km is not None else "No industrial site on record"
            ),
        }


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _seeded_wind(city: str, ward: str, date_str: str) -> tuple[str, int, float]:
    """Deterministic pseudo-meteorological wind reading.

    Not present in any source dataset, so it is derived from a stable
    hash of (city, ward, date) rather than left blank — but is always
    the same value for the same day, and is explicitly labeled
    'simulated' everywhere it's displayed.
    """
    h = hashlib.sha256(f"{city}|{ward}|{date_str}".encode()).hexdigest()
    deg = int(h[:4], 16) % 360
    speed = 4 + (int(h[4:6], 16) % 22)  # 4-25 km/h
    idx = round(deg / 22.5) % 16
    return COMPASS_DIRECTIONS[idx], deg, float(speed)


class EvidenceEngine:
    """Computes per-ward evidence used to explain source-attribution shares."""

    def __init__(self, geo_intel_df: pd.DataFrame):
        self.geo_intel = geo_intel_df

    def evidence_for_ward(self, city: str, ward: str, lat: float, lon: float, date_str: str) -> WardEvidence:
        city_points = self.geo_intel[self.geo_intel["city"] == city]

        traffic_pts = city_points[city_points["layer"] == "traffic"].copy()
        construction_pts = city_points[city_points["layer"] == "construction"].copy()
        industrial_pts = city_points[city_points["layer"] == "industrial"].copy()

        def _dist(df: pd.DataFrame) -> pd.Series:
            if df.empty:
                return pd.Series(dtype=float)
            return df.apply(lambda r: _haversine_km(lat, lon, r["lat"], r["lon"]), axis=1)

        traffic_dists = _dist(traffic_pts)
        nearby_roads = int((traffic_dists <= NEARBY_RADIUS_KM).sum()) if len(traffic_dists) else 0

        construction_dists = _dist(construction_pts)
        construction_count = int((construction_dists <= NEARBY_RADIUS_KM).sum()) if len(construction_dists) else 0

        industrial_dists = _dist(industrial_pts)
        if len(industrial_dists):
            nearest_idx = industrial_dists.idxmin()
            industrial_distance = float(industrial_dists.loc[nearest_idx])
            nearest_name = str(industrial_pts.loc[nearest_idx, "name"])
        else:
            industrial_distance = None
            nearest_name = None

        # Traffic density index: normalize road count against the busiest
        # ward in the city so it reads as a relative 0-1 intensity score.
        all_traffic_counts = []
        for _, r in city_points[city_points["layer"] == "hotspot"].iterrows():
            d = traffic_pts.apply(lambda t: _haversine_km(r["lat"], r["lon"], t["lat"], t["lon"]), axis=1) if len(traffic_pts) else pd.Series(dtype=float)
            all_traffic_counts.append(int((d <= NEARBY_RADIUS_KM).sum()) if len(d) else 0)
        max_roads = max(all_traffic_counts) if all_traffic_counts else max(nearby_roads, 1)
        density_index = min(1.0, nearby_roads / max(max_roads, 1))

        wind_dir, wind_deg, wind_speed = _seeded_wind(city, ward, date_str)

        return WardEvidence(
            ward=ward,
            city=city,
            nearby_roads=nearby_roads,
            traffic_density_index=density_index,
            wind_direction=wind_dir,
            wind_direction_deg=wind_deg,
            wind_speed_kmh=wind_speed,
            construction_site_count=construction_count,
            industrial_distance_km=industrial_distance,
            nearest_industrial_site=nearest_name,
        )
