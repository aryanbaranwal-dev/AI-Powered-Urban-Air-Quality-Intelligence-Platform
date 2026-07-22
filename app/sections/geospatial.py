"""
Geospatial Intelligence — interactive Folium map of India covering
Delhi, Mumbai, Chennai, Bangalore and Kolkata.

Layers: AQI Heatmap, Ward Boundaries, Hotspots, Monitoring Stations,
Industrial Areas, Construction Sites, Traffic Density, Schools, Hospitals.
Filters: Heatmap toggle, Satellite toggle, Dark theme toggle, zoom/pan.
"""
import json

import folium
import streamlit as st
from folium.plugins import HeatMap, Fullscreen, MiniMap
from streamlit_folium import st_folium

from app.components.metric_card import metric_card, section_title, badge
from app.theme import get_aqi_meta
from app.config import GEO_CITIES, GEO_CITY_CENTERS, GEO_LAYER_META


SHOW_OPTIONS = [
    "AQI Heatmap", "Ward Boundaries", "Hotspots", "Monitoring Stations",
    "Industrial Areas", "Construction Sites", "Traffic Density", "Schools", "Hospitals",
]
DEFAULT_SHOW = ["AQI Heatmap", "Ward Boundaries", "Hotspots", "Monitoring Stations"]

LAYER_KEY_BY_LABEL = {
    "Hotspots": "hotspot",
    "Monitoring Stations": "monitoring_station",
    "Industrial Areas": "industrial",
    "Construction Sites": "construction",
    "Traffic Density": "traffic",
    "Schools": "school",
    "Hospitals": "hospital",
}


def _popup_html(row) -> str:
    """Rich popup for a pollution hotspot: AQI / PM2.5 / PM10 / source /
    confidence / recommended action."""
    meta = get_aqi_meta(row["aqi"])
    conf = row.get("confidence")
    conf_html = f"{conf*100:.0f}%" if conf == conf and conf is not None else "—"
    return f"""
    <div style="font-family:Inter,Arial,sans-serif; width:250px; color:#0b0f1a;">
      <div style="font-weight:800; font-size:14px; margin-bottom:4px;">📍 {row['name']}</div>
      <div style="display:inline-block; padding:2px 8px; border-radius:20px; font-size:11px;
                  font-weight:700; color:#fff; background:{meta['color']}; margin-bottom:8px;">
        AQI {row['aqi']:.0f} · {meta['label']}
      </div>
      <table style="width:100%; font-size:12px; border-collapse:collapse;">
        <tr><td style="padding:2px 0; color:#556;">PM2.5</td>
            <td style="text-align:right; font-weight:700;">{row['pm25']:.0f} µg/m³</td></tr>
        <tr><td style="padding:2px 0; color:#556;">PM10</td>
            <td style="text-align:right; font-weight:700;">{row['pm10']:.0f} µg/m³</td></tr>
        <tr><td style="padding:2px 0; color:#556;">Main Source</td>
            <td style="text-align:right; font-weight:700;">{row['main_source']}</td></tr>
        <tr><td style="padding:2px 0; color:#556;">Confidence</td>
            <td style="text-align:right; font-weight:700;">{conf_html}</td></tr>
      </table>
      <div style="margin-top:8px; padding:8px; border-radius:8px; background:#f1f5f9; font-size:11.5px; line-height:1.4;">
        <b>Recommended Action</b><br>{row['recommended_action']}
      </div>
    </div>
    """


def _simple_popup_html(row) -> str:
    """Lighter popup for infrastructure / POI layers (industrial,
    construction, schools, hospitals, monitoring stations)."""
    lines = [f"<div style='font-family:Inter,Arial,sans-serif; width:220px; color:#0b0f1a;'>"
             f"<div style='font-weight:800; font-size:13.5px; margin-bottom:4px;'>{row['name']}</div>"]
    if row.get("aqi") == row.get("aqi") and row.get("aqi") is not None:
        meta = get_aqi_meta(row["aqi"])
        lines.append(
            f"<div style='display:inline-block; padding:2px 8px; border-radius:20px; font-size:11px;"
            f"font-weight:700; color:#fff; background:{meta['color']}; margin-bottom:6px;'>"
            f"Nearby AQI {row['aqi']:.0f} · {meta['label']}</div>"
        )
    if row.get("recommended_action") == row.get("recommended_action") and row.get("recommended_action"):
        lines.append(f"<div style='font-size:11.5px; color:#334; margin-top:4px;'>{row['recommended_action']}</div>")
    lines.append("</div>")
    return "".join(lines)


def render(ctx):
    geo = ctx["geo_intel"]
    geo_wards = ctx["geo_wards"]

    # ------------------------------------------------------------ header --
    top = st.columns([2.2, 1])
    with top[0]:
        section_title("Geospatial Intelligence Map", "🗺️")
    with top[1]:
        geo_city = st.selectbox("City", GEO_CITIES, key="geo_city_choice", label_visibility="collapsed")

    st.caption(
        "🌐 Prefer a single all-India view with city quick-nav? Open the standalone "
        "**`standalone_dashboard/aqi_geospatial_dashboard.html`** file in this project "
        "directly in your browser — no server required."
    )

    city_geo = geo[geo["city"] == geo_city].copy()
    city_wards = geo_wards[geo_wards["city"] == geo_city].copy()
    hotspots = city_geo[city_geo["layer"] == "hotspot"]

    # ------------------------------------------------------------ metrics --
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Hotspots Tracked", f"{len(hotspots)}", icon="🔥", accent="red", delay=0.0)
    with c2:
        metric_card("Peak Hotspot AQI", f"{hotspots['aqi'].max():.0f}", icon="🔺", accent="amber", delay=0.05)
    with c3:
        top_src = hotspots["main_source"].mode().iloc[0] if len(hotspots) else "—"
        metric_card("Dominant Source", top_src, icon="🛰️", accent="purple", delay=0.10)
    with c4:
        metric_card("Monitoring Points", f"{len(city_geo[city_geo['layer']=='monitoring_station'])}",
                     icon="📡", accent="cyan", delay=0.15)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------ filters --
    with st.container(key="geo_filters_card"):
        f1, f2, f3 = st.columns([2.6, 1, 1])
        with f1:
            show = st.multiselect("Show layers", SHOW_OPTIONS, default=DEFAULT_SHOW,
                                   key="geo_show_layers", label_visibility="collapsed",
                                   placeholder="Select layers to display…")
        with f2:
            satellite = st.toggle("🛰️ Satellite", value=False, key="geo_satellite")
        with f3:
            dark_theme = st.toggle("🌙 Dark Theme", value=True, key="geo_dark_theme",
                                    disabled=satellite)

    # ------------------------------------------------------------ map -----
    lat0, lon0 = GEO_CITY_CENTERS[geo_city]

    if satellite:
        tiles, attr = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
                        "World_Imagery/MapServer/tile/{z}/{y}/{x}", "Esri World Imagery")
    elif dark_theme:
        tiles, attr = "CartoDB dark_matter", None
    else:
        tiles, attr = "CartoDB positron", None

    fmap = folium.Map(
        location=[lat0, lon0], zoom_start=11, tiles=tiles, attr=attr,
        zoom_control=True, control_scale=True, scrollWheelZoom=True, dragging=True,
    )
    Fullscreen(position="topleft").add_to(fmap)
    MiniMap(toggle_display=True, position="bottomleft").add_to(fmap)

    # ---- AQI Heatmap (hotspots + monitoring stations, weighted by AQI) ----
    if "AQI Heatmap" in show:
        heat_pts = []
        for _, r in city_geo[city_geo["layer"].isin(["hotspot", "monitoring_station"])].dropna(subset=["aqi"]).iterrows():
            heat_pts.append([r["lat"], r["lon"], min(r["aqi"] / 500.0, 1.0)])
        if heat_pts:
            HeatMap(heat_pts, radius=32, blur=24, min_opacity=0.35,
                    gradient={"0.2": "#22c55e", "0.4": "#facc15", "0.6": "#fb923c",
                              "0.8": "#f87171", "1.0": "#c026d3"}).add_to(
                folium.FeatureGroup(name="AQI Heatmap").add_to(fmap)
            )

    # ---- Traffic Density heatmap (weighted by congestion) ----
    if "Traffic Density" in show:
        traf = city_geo[city_geo["layer"] == "traffic"]
        if len(traf):
            pts = [[r["lat"], r["lon"], r["weight"] / 100.0] for _, r in traf.iterrows()]
            fg_traf = folium.FeatureGroup(name="Traffic Density")
            HeatMap(pts, radius=22, blur=18, min_opacity=0.25,
                    gradient={"0.2": "#1e3a8a", "0.5": "#3b82f6", "1.0": "#93c5fd"}).add_to(fg_traf)
            fg_traf.add_to(fmap)

    # ---- Ward boundaries (simulated polygons colored by AQI band) ----
    if "Ward Boundaries" in show and len(city_wards):
        fg_ward = folium.FeatureGroup(name="Ward Boundaries")
        for _, r in city_wards.iterrows():
            ring = json.loads(r["polygon"])  # list of [lon, lat]
            latlon_ring = [(pt[1], pt[0]) for pt in ring]
            meta = get_aqi_meta(r["aqi"])
            folium.Polygon(
                locations=latlon_ring, color=meta["color"], weight=1.6,
                fill=True, fill_color=meta["color"], fill_opacity=0.14,
                tooltip=f"{r['ward']} — AQI {r['aqi']:.0f} ({meta['label']})",
            ).add_to(fg_ward)
        fg_ward.add_to(fmap)

    # ---- Hotspots (rich popup) ----
    if "Hotspots" in show:
        fg_hot = folium.FeatureGroup(name="Hotspots")
        for _, r in hotspots.iterrows():
            meta = get_aqi_meta(r["aqi"])
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=8 + (r["aqi"] / 500) * 10,
                color=meta["color"], weight=2, fill=True,
                fill_color=meta["color"], fill_opacity=0.75,
                popup=folium.Popup(_popup_html(r), max_width=280),
                tooltip=f"🔥 {r['name']} — AQI {r['aqi']:.0f}",
            ).add_to(fg_hot)
        fg_hot.add_to(fmap)

    # ---- Generic POI layers ----
    for label, key in LAYER_KEY_BY_LABEL.items():
        if label in ("Hotspots", "Traffic Density") or label not in show:
            continue
        subset = city_geo[city_geo["layer"] == key]
        if not len(subset):
            continue
        meta = GEO_LAYER_META[key]
        fg = folium.FeatureGroup(name=label)
        for _, r in subset.iterrows():
            folium.Marker(
                location=[r["lat"], r["lon"]],
                popup=folium.Popup(_simple_popup_html(r), max_width=250),
                tooltip=f"{meta['icon']} {r['name']}",
                icon=folium.DivIcon(html=f"""
                    <div style="font-size:20px; text-align:center; line-height:26px;
                                transform:translate(-50%,-50%);
                                filter:drop-shadow(0 1px 2px rgba(0,0,0,.6));">
                      {meta['icon']}
                    </div>"""),
            ).add_to(fg)
        fg.add_to(fmap)

    folium.LayerControl(collapsed=False, position="topright").add_to(fmap)

    with st.container(key="geo_map_card"):
        st_folium(fmap, use_container_width=True, height=560, returned_objects=[])
        legend_badges = "".join(
            badge(l["label"], l["color"], icon=l["icon"]) + " "
            for l in [GEO_LAYER_META[k] for k in LAYER_KEY_BY_LABEL.values()]
        )
        st.markdown(
            f"<div class='card-caption' style='margin-top:8px;'>{legend_badges}</div>"
            "<div class='card-caption'>Hotspot geometry, ward boundaries and infrastructure "
            "layers are simulated for demonstration; use the layer control (top-right of the "
            "map) or the filters above to toggle overlays. Click any marker for full details.</div>",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------ table ---
    with st.container(key="geo_table_card"):
        section_title("Hotspot Registry", "📋")
        display_cols = ["name", "ward_type", "aqi", "aqi_band", "pm25", "pm10",
                         "main_source", "confidence", "recommended_action"]
        st.dataframe(
            hotspots[display_cols].sort_values("aqi", ascending=False).rename(columns={
                "name": "Location", "ward_type": "Type", "aqi": "AQI", "aqi_band": "Category",
                "pm25": "PM2.5", "pm10": "PM10", "main_source": "Main Source",
                "confidence": "Confidence", "recommended_action": "Recommended Action",
            }),
            use_container_width=True, hide_index=True,
        )
