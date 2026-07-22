"""
Builds a single, standalone, professional HTML geospatial dashboard
covering Delhi, Mumbai, Chennai, Bangalore and Kolkata on one
interactive India map — no server required, just open the .html file.
"""
import json
import numpy as np
import pandas as pd
import folium
from folium.plugins import HeatMap, Fullscreen, MiniMap, MarkerCluster
from folium import MacroElement
from jinja2 import Template

import os
BASE = os.path.dirname(os.path.abspath(__file__))
geo = pd.read_csv(f"{BASE}/../data/geo_intelligence.csv")
wards = pd.read_csv(f"{BASE}/../data/geo_wards.csv")

CITY_CENTERS = {
    "Delhi":     (28.6139, 77.2090),
    "Mumbai":    (19.0760, 72.8777),
    "Chennai":   (13.0827, 80.2707),
    "Bangalore": (12.9716, 77.5946),
    "Kolkata":   (22.5726, 88.3639),
}

AQI_BANDS = [
    (0,   50,  "Good",         "#22c55e"),
    (51,  100, "Satisfactory", "#84cc16"),
    (101, 200, "Moderate",     "#facc15"),
    (201, 300, "Poor",         "#fb923c"),
    (301, 400, "Very Poor",    "#f87171"),
    (401, 10_000, "Severe",    "#c026d3"),
]


def aqi_meta(v):
    if v is None or v != v:
        v = 0
    for lo, hi, label, color in AQI_BANDS:
        if lo <= v <= hi:
            return label, color
    return AQI_BANDS[-1][2], AQI_BANDS[-1][3]


LAYER_META = {
    "hotspot":            {"icon": "🔥", "label": "Hotspots"},
    "monitoring_station": {"icon": "📡", "label": "Monitoring Stations"},
    "industrial":         {"icon": "🏭", "label": "Industrial Areas"},
    "construction":       {"icon": "🏗️", "label": "Construction Sites"},
    "school":             {"icon": "🏫", "label": "Schools"},
    "hospital":           {"icon": "🏥", "label": "Hospitals"},
}

# ------------------------------------------------------------------ map --
fmap = folium.Map(
    location=[22.6, 80.5], zoom_start=5, tiles=None,
    zoom_control=True, control_scale=True, scrollWheelZoom=True, dragging=True,
    prefer_canvas=True,
)

folium.TileLayer("CartoDB dark_matter", name="🌙 Dark Theme", control=True, show=True).add_to(fmap)
folium.TileLayer("CartoDB positron", name="☀️ Light Theme", control=True, show=False).add_to(fmap)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery", name="🛰️ Satellite", control=True, show=False,
).add_to(fmap)

Fullscreen(position="topleft", title="Fullscreen", title_cancel="Exit fullscreen").add_to(fmap)
MiniMap(toggle_display=True, position="bottomleft").add_to(fmap)

# ---- AQI Heatmap (all cities: hotspots + monitoring stations) ----
heat_pts = []
for _, r in geo[geo["layer"].isin(["hotspot", "monitoring_station"])].dropna(subset=["aqi"]).iterrows():
    heat_pts.append([r["lat"], r["lon"], min(r["aqi"] / 500.0, 1.0)])
fg_heat = folium.FeatureGroup(name="🌡️ AQI Heatmap", show=True)
HeatMap(heat_pts, radius=28, blur=22, min_opacity=0.35,
        gradient={"0.2": "#22c55e", "0.4": "#facc15", "0.6": "#fb923c",
                  "0.8": "#f87171", "1.0": "#c026d3"}).add_to(fg_heat)
fg_heat.add_to(fmap)

# ---- Traffic Density heatmap ----
traf = geo[geo["layer"] == "traffic"]
fg_traf = folium.FeatureGroup(name="🚗 Traffic Density", show=False)
HeatMap([[r["lat"], r["lon"], r["weight"] / 100.0] for _, r in traf.iterrows()],
        radius=18, blur=15, min_opacity=0.25,
        gradient={"0.2": "#1e3a8a", "0.5": "#3b82f6", "1.0": "#93c5fd"}).add_to(fg_traf)
fg_traf.add_to(fmap)

# ---- Ward boundaries ----
fg_ward = folium.FeatureGroup(name="🧭 Ward Boundaries", show=True)
for _, r in wards.iterrows():
    ring = json.loads(r["polygon"])
    latlon_ring = [(pt[1], pt[0]) for pt in ring]
    label, color = aqi_meta(r["aqi"])
    folium.Polygon(
        locations=latlon_ring, color=color, weight=1.6,
        fill=True, fill_color=color, fill_opacity=0.14,
        tooltip=f"<b>{r['ward']}</b> ({r['city']})<br>AQI {r['aqi']:.0f} · {label}",
    ).add_to(fg_ward)
fg_ward.add_to(fmap)

# ---- Hotspots (rich popup) ----


def hotspot_popup(r):
    label, color = aqi_meta(r["aqi"])
    conf = r["confidence"]
    conf_html = f"{conf*100:.0f}%" if conf == conf else "—"
    return f"""
    <div style="font-family:Inter,Arial,sans-serif; width:260px; color:#0b0f1a;">
      <div style="font-weight:800; font-size:14.5px; margin-bottom:2px;">📍 {r['name']}</div>
      <div style="font-size:11px; color:#667; margin-bottom:6px;">{r['city']} · {r['ward_type'].replace('_',' ').title()}</div>
      <div style="display:inline-block; padding:3px 10px; border-radius:20px; font-size:11.5px;
                  font-weight:700; color:#fff; background:{color}; margin-bottom:8px;">
        AQI {r['aqi']:.0f} · {label}
      </div>
      <table style="width:100%; font-size:12px; border-collapse:collapse;">
        <tr><td style="padding:3px 0; color:#556;">PM2.5</td>
            <td style="text-align:right; font-weight:700;">{r['pm25']:.0f} µg/m³</td></tr>
        <tr><td style="padding:3px 0; color:#556;">PM10</td>
            <td style="text-align:right; font-weight:700;">{r['pm10']:.0f} µg/m³</td></tr>
        <tr><td style="padding:3px 0; color:#556;">Main Pollution Source</td>
            <td style="text-align:right; font-weight:700;">{r['main_source']}</td></tr>
        <tr><td style="padding:3px 0; color:#556;">Confidence Score</td>
            <td style="text-align:right; font-weight:700;">{conf_html}</td></tr>
      </table>
      <div style="margin-top:9px; padding:9px; border-radius:8px; background:#f1f5f9; font-size:11.5px; line-height:1.4;">
        <b>Recommended Action</b><br>{r['recommended_action']}
      </div>
    </div>
    """


fg_hot = folium.FeatureGroup(name="🔥 Hotspots", show=True)
for _, r in geo[geo["layer"] == "hotspot"].iterrows():
    label, color = aqi_meta(r["aqi"])
    folium.CircleMarker(
        location=[r["lat"], r["lon"]],
        radius=7 + (r["aqi"] / 500) * 9,
        color=color, weight=2, fill=True, fill_color=color, fill_opacity=0.78,
        popup=folium.Popup(hotspot_popup(r), max_width=290),
        tooltip=f"🔥 {r['name']} ({r['city']}) — AQI {r['aqi']:.0f}",
    ).add_to(fg_hot)
fg_hot.add_to(fmap)


def simple_popup(r):
    parts = [f"<div style='font-family:Inter,Arial,sans-serif; width:230px; color:#0b0f1a;'>"
             f"<div style='font-weight:800; font-size:13.5px;'>{r['name']}</div>"
             f"<div style='font-size:11px; color:#667; margin-bottom:6px;'>{r['city']}</div>"]
    if r["aqi"] == r["aqi"]:
        label, color = aqi_meta(r["aqi"])
        parts.append(f"<div style='display:inline-block; padding:2px 9px; border-radius:20px; font-size:11px;"
                      f"font-weight:700; color:#fff; background:{color}; margin-bottom:6px;'>"
                      f"Nearby AQI {r['aqi']:.0f} · {label}</div>")
    if isinstance(r["recommended_action"], str):
        parts.append(f"<div style='font-size:11.5px; color:#334;'>{r['recommended_action']}</div>")
    parts.append("</div>")
    return "".join(parts)


for key, meta in LAYER_META.items():
    if key == "hotspot":
        continue
    subset = geo[geo["layer"] == key]
    fg = folium.FeatureGroup(name=f"{meta['icon']} {meta['label']}", show=False)
    cluster = MarkerCluster(disableClusteringAtZoom=12).add_to(fg) if key in ("monitoring_station",) else fg
    for _, r in subset.iterrows():
        folium.Marker(
            location=[r["lat"], r["lon"]],
            popup=folium.Popup(simple_popup(r), max_width=260),
            tooltip=f"{meta['icon']} {r['name']} ({r['city']})",
            icon=folium.DivIcon(html=f"""
                <div style="font-size:19px; text-align:center; line-height:24px;
                            transform:translate(-50%,-50%);
                            filter:drop-shadow(0 1px 2px rgba(0,0,0,.65));">
                  {meta['icon']}
                </div>"""),
        ).add_to(cluster)
    fg.add_to(fmap)

folium.LayerControl(collapsed=False, position="topright").add_to(fmap)

# ------------------------------------------------------- header overlay --
stats = {
    "cities": len(CITY_CENTERS),
    "hotspots": int((geo["layer"] == "hotspot").sum()),
    "stations": int((geo["layer"] == "monitoring_station").sum()),
    "avg_aqi": geo[geo["layer"] == "hotspot"]["aqi"].mean(),
    "peak_aqi": geo[geo["layer"] == "hotspot"]["aqi"].max(),
}

city_buttons = "".join(
    f'<button class="city-btn" onclick="flyToCity({lat},{lon})">{city}</button>'
    for city, (lat, lon) in CITY_CENTERS.items()
)

overlay_template = Template("""
{% macro html(this, kwargs) %}
<style>
  .aqi-header {
    position: absolute; top: 12px; left: 60px; z-index: 9999;
    background: rgba(10,14,24,0.88); backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.10); border-radius: 16px;
    padding: 14px 20px; color: #eef1f8; font-family: 'Inter', Arial, sans-serif;
    box-shadow: 0 8px 30px rgba(0,0,0,0.45); max-width: 560px;
  }
  .aqi-header h1 { font-size: 16px; margin: 0 0 2px 0; font-weight: 800;
    background: linear-gradient(90deg,#3b82f6,#22d3ee); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; }
  .aqi-header p { margin: 0 0 10px 0; font-size: 11px; color: #8b96ab; }
  .aqi-stats { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 10px; }
  .aqi-stat { text-align: left; }
  .aqi-stat .v { font-size: 17px; font-weight: 800; color: #fff; }
  .aqi-stat .l { font-size: 9.5px; color: #8b96ab; text-transform: uppercase; letter-spacing: .04em; }
  .city-nav { display: flex; gap: 6px; flex-wrap: wrap; }
  .city-btn {
    background: rgba(59,130,246,0.14); border: 1px solid rgba(59,130,246,0.35);
    color: #93c5fd; font-size: 11px; font-weight: 600; padding: 5px 11px;
    border-radius: 20px; cursor: pointer; transition: all .15s ease;
  }
  .city-btn:hover { background: rgba(59,130,246,0.32); color: #fff; }
  .aqi-legend {
    position: absolute; bottom: 22px; right: 12px; z-index: 9999;
    background: rgba(10,14,24,0.88); backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.10); border-radius: 12px;
    padding: 10px 14px; color: #eef1f8; font-family: 'Inter', Arial, sans-serif; font-size: 10.5px;
  }
  .aqi-legend .row { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
  .aqi-legend .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
  @media (max-width: 760px) {
    .aqi-header { left: 8px; right: 8px; max-width: none; }
  }
</style>
<div class="aqi-header">
  <h1>🌫️ AQI Intelligence — National Geospatial Dashboard</h1>
  <p>Real-time style pollution intelligence across 5 major Indian metros · simulated demo data</p>
  <div class="aqi-stats">
    <div class="aqi-stat"><div class="v">{{ this.stats['cities'] }}</div><div class="l">Cities</div></div>
    <div class="aqi-stat"><div class="v">{{ this.stats['hotspots'] }}</div><div class="l">Hotspots</div></div>
    <div class="aqi-stat"><div class="v">{{ this.stats['stations'] }}</div><div class="l">Sensors</div></div>
    <div class="aqi-stat"><div class="v">{{ '%.0f'|format(this.stats['avg_aqi']) }}</div><div class="l">Avg Hotspot AQI</div></div>
    <div class="aqi-stat"><div class="v">{{ '%.0f'|format(this.stats['peak_aqi']) }}</div><div class="l">Peak AQI</div></div>
  </div>
  <div class="city-nav">{{ this.city_buttons|safe }}</div>
</div>
<div class="aqi-legend">
  <div style="font-weight:700; margin-bottom:4px; font-size:11px;">AQI Scale</div>
  <div class="row"><span class="dot" style="background:#22c55e;"></span>Good (0–50)</div>
  <div class="row"><span class="dot" style="background:#84cc16;"></span>Satisfactory (51–100)</div>
  <div class="row"><span class="dot" style="background:#facc15;"></span>Moderate (101–200)</div>
  <div class="row"><span class="dot" style="background:#fb923c;"></span>Poor (201–300)</div>
  <div class="row"><span class="dot" style="background:#f87171;"></span>Very Poor (301–400)</div>
  <div class="row"><span class="dot" style="background:#c026d3;"></span>Severe (400+)</div>
</div>
<script>
  var {{ this.get_name() }}_map = {{ this._parent.get_name() }};
  function flyToCity(lat, lon) {
    {{ this._parent.get_name() }}.flyTo([lat, lon], 11, {duration: 1.1});
  }
</script>
{% endmacro %}
""")


class HeaderOverlay(MacroElement):
    def __init__(self, stats, city_buttons):
        super().__init__()
        self._name = "HeaderOverlay"
        self.stats = stats
        self.city_buttons = city_buttons
        self._template = overlay_template


fmap.get_root().add_child(HeaderOverlay(stats, city_buttons))

fmap.save(f"{BASE}/aqi_geospatial_dashboard.html")
print("saved")
