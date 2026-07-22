import plotly.express as px
import plotly.graph_objects as go

from app.theme import apply_fig_theme, get_aqi_meta, get_theme, mapbox_style
from app.config import SOURCE_COLORS


def hex_to_rgba(hex_color: str, alpha: float = 0.2) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def aqi_trend_chart(city_data, days=60, height=340):
    t = get_theme()
    tail = city_data.tail(days)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=tail["Date"], y=tail["AQI"], mode="lines", name="AQI",
        line=dict(color=t["primary"], width=2.4, shape="spline"),
        fill="tozeroy", fillcolor=hex_to_rgba(t["primary"], 0.14),
    ))
    fig.update_layout(showlegend=False, title=None)
    return apply_fig_theme(fig, height)


def forecast_chart(city_data, latest, forecasts, future_dates, height=380):
    t = get_theme()
    hist_tail = city_data.tail(21)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist_tail["Date"], y=hist_tail["AQI"], mode="lines+markers", name="Historical AQI",
        line=dict(color=t["primary"], width=2.4), marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=[latest["Date"]] + future_dates, y=[latest["AQI"]] + forecasts,
        mode="lines+markers", name="AI Forecast",
        line=dict(color=t["secondary"], width=2.6, dash="dash"), marker=dict(size=7, symbol="diamond"),
    ))
    fig.add_trace(go.Scatter(
        x=[latest["Date"]] + future_dates, y=[latest["AQI"]] * (len(future_dates) + 1),
        mode="lines", name="Persistence Baseline",
        line=dict(color=t["text3"], width=1.6, dash="dot"),
    ))
    fig.update_layout(xaxis_title="Date", yaxis_title="AQI")
    return apply_fig_theme(fig, height)


def source_pie(source_vals: dict, height=330):
    t = get_theme()
    colors = [SOURCE_COLORS.get(k, t["primary"]) for k in source_vals.keys()]
    fig = px.pie(
        names=list(source_vals.keys()), values=list(source_vals.values()),
        hole=0.58, color_discrete_sequence=colors,
    )
    # Percent labels sit on top of vivid wedge colors, not the page
    # background, so a fixed dark label + light stroke stays readable
    # in both themes.
    fig.update_traces(
        textinfo="percent", textfont=dict(color="#0b0f1a", size=12, family="Inter"),
        marker=dict(line=dict(color=t["card"], width=2)),
    )
    fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1.0, y=0.5))
    return apply_fig_theme(fig, height)


def pollutant_timeline_chart(city_data, days=45, height=330):
    t = get_theme()
    tail = city_data.tail(days)
    fig = go.Figure()
    pollutants = [("PM2.5", t["primary"]), ("PM10", t["secondary"]), ("NO2", "#a855f7"),
                  ("O3", t["warning"])]
    for pol, color in pollutants:
        fig.add_trace(go.Scatter(x=tail["Date"], y=tail[pol], mode="lines", name=pol,
                                  line=dict(width=2, color=color)))
    fig.update_layout(xaxis_title="Date", yaxis_title="Concentration (µg/m³)")
    return apply_fig_theme(fig, height)


def hotspot_bar(ward_df, height=340):
    t = get_theme()
    d = ward_df.sort_values("Simulated_AQI", ascending=True).tail(8)
    colors = [get_aqi_meta(v)["color"] for v in d["Simulated_AQI"]]
    fig = go.Figure(go.Bar(
        x=d["Simulated_AQI"], y=d["Ward"], orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:.0f}" for v in d["Simulated_AQI"]], textposition="outside",
        textfont=dict(color=t["text2"]),
    ))
    fig.update_layout(xaxis_title="AQI", yaxis_title=None)
    return apply_fig_theme(fig, height)


def multi_city_trend(clean_df, cities, days=90, height=380):
    t = get_theme()
    fig = go.Figure()
    palette = [t["primary"], "#a855f7", t["secondary"]]
    for i, c in enumerate(cities):
        cd = clean_df[clean_df["City"] == c].tail(days)
        fig.add_trace(go.Scatter(x=cd["Date"], y=cd["AQI"], mode="lines", name=c,
                                  line=dict(width=2.4, color=palette[i % len(palette)])))
    fig.update_layout(xaxis_title="Date", yaxis_title="AQI")
    return apply_fig_theme(fig, height)


def improvement_bar(comp_df, height=340):
    t = get_theme()
    fig = px.bar(
        comp_df, x="Horizon", y="Improvement over Baseline", color="City", barmode="group",
        color_discrete_sequence=[t["primary"], "#a855f7"],
    )
    fig.update_layout(xaxis_title=None, yaxis_title="% RMSE Improvement")
    return apply_fig_theme(fig, height)


def pollutant_radar(city_means: dict, height=380):
    """city_means: {city: {pollutant: value}}"""
    t = get_theme()
    cats = list(next(iter(city_means.values())).keys())
    fig = go.Figure()
    palette = [t["primary"], "#a855f7"]
    for i, (city, vals) in enumerate(city_means.items()):
        values = list(vals.values())
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]], theta=cats + [cats[0]], fill="toself", name=city,
            line=dict(color=palette[i % len(palette)], width=2),
            fillcolor=hex_to_rgba(palette[i % len(palette)], 0.18),
        ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(showticklabels=True, gridcolor=t["chart_grid"], color=t["text3"]),
            angularaxis=dict(gridcolor=t["chart_grid"], color=t["text2"]),
        ),
        showlegend=True,
    )
    return apply_fig_theme(fig, height)


def source_sankey(contributions: dict, ward_name: str, aqi: float, height=380):
    """Sankey flow: each pollution source -> the ward's current AQI level,
    with link width proportional to that source's % contribution."""
    from app.theme import get_source_color

    t = get_theme()
    sources = list(contributions.keys())
    node_labels = sources + [f"{ward_name}\nAQI {aqi:.0f}"]
    node_colors = [get_source_color(s) for s in sources] + [t["text1"]]
    target_idx = len(sources)

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            label=node_labels,
            color=node_colors,
            pad=22,
            thickness=16,
            line=dict(color=t["chart_axisline"], width=0.5),
        ),
        link=dict(
            source=list(range(len(sources))),
            target=[target_idx] * len(sources),
            value=[max(contributions[s], 0.5) for s in sources],
            color=[hex_to_rgba(get_source_color(s), 0.45) for s in sources],
            customdata=[f"{contributions[s]:.1f}%" for s in sources],
            hovertemplate="%{source.label} → %{target.label}<br>Contribution: %{customdata}<extra></extra>",
        ),
        textfont=dict(color=t["text1"], size=12, family="Inter"),
    ))
    fig.update_layout(margin=dict(l=8, r=8, t=8, b=8))
    return apply_fig_theme(fig, height)


def intervention_comparison_bar(contributions_before: dict, contributions_after: dict, height=360):
    """Grouped bar: each source's share before vs after the simulated
    intervention(s) - the direct visual evidence behind the AQI delta."""
    from app.theme import get_source_color

    t = get_theme()
    cats = list(contributions_before.keys())
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=cats, y=[contributions_before[c] for c in cats], name="Before",
        marker=dict(color=t["fill3"], line=dict(width=0)),
    ))
    fig.add_trace(go.Bar(
        x=cats, y=[contributions_after[c] for c in cats], name="After",
        marker=dict(color=[get_source_color(c) for c in cats], line=dict(width=0)),
    ))
    fig.update_layout(barmode="group", xaxis_title=None, yaxis_title="Share of pollution load (%)")
    return apply_fig_theme(fig, height)


def aqi_before_after_gauge(aqi_before: float, aqi_after: float, height=280):
    """Single gauge showing projected AQI after intervention, with the
    current AQI marked as a threshold line for instant before/after read."""
    t = get_theme()
    meta_after = get_aqi_meta(aqi_after)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=aqi_after,
        number=dict(suffix=" AQI", font=dict(color=meta_after["text_color"], size=34)),
        delta=dict(reference=aqi_before, decreasing=dict(color=t["success"]), increasing=dict(color=t["danger"])),
        gauge=dict(
            axis=dict(range=[0, max(500, aqi_before * 1.15)], tickcolor=t["text3"]),
            bar=dict(color=meta_after["color"]),
            bgcolor=t["fill1"],
            borderwidth=0,
            steps=[
                {"range": [0, 50], "color": "rgba(34,197,94,0.18)"},
                {"range": [50, 100], "color": "rgba(132,204,22,0.18)"},
                {"range": [100, 200], "color": "rgba(250,204,21,0.18)"},
                {"range": [200, 300], "color": "rgba(251,146,60,0.18)"},
                {"range": [300, 400], "color": "rgba(248,113,113,0.18)"},
                {"range": [400, max(500, aqi_before * 1.15)], "color": "rgba(192,38,211,0.18)"},
            ],
            threshold=dict(line=dict(color=t["text1"], width=3), thickness=0.85, value=aqi_before),
        ),
    ))
    fig.update_layout(margin=dict(l=20, r=20, t=30, b=10))
    return apply_fig_theme(fig, height)


def kpi_gauge(value: float, title: str, max_value: float = 100, suffix: str = "",
              bands=None, height=200, value_font=30):
    """Generic single-value gauge for executive KPI cards (0..max_value).

    bands: optional list of (lo, hi, rgba_color) segments; defaults to a
    green to red ramp appropriate for a 0-100 "score" style metric.
    """
    t = get_theme()
    if bands is None:
        bands = [
            (0, max_value * 0.4, "rgba(248,113,113,0.20)"),
            (max_value * 0.4, max_value * 0.7, "rgba(250,204,21,0.20)"),
            (max_value * 0.7, max_value, "rgba(34,197,94,0.20)"),
        ]
    bar_color = t["success"]
    for lo, hi, c in bands:
        if lo <= value <= hi:
            bar_color = c.replace("0.20", "1").replace("rgba", "rgb").rsplit(",", 1)[0] + ")"
            break
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=title, font=dict(size=12, color=t["text3"])),
        number=dict(suffix=suffix, font=dict(color=bar_color, size=value_font)),
        gauge=dict(
            axis=dict(range=[0, max_value], tickcolor=t["text3"], tickfont=dict(size=9)),
            bar=dict(color=bar_color, thickness=0.28),
            bgcolor=t["fill1"],
            borderwidth=0,
            steps=[{"range": [lo, hi], "color": c} for lo, hi, c in bands],
        ),
    ))
    fig.update_layout(margin=dict(l=18, r=18, t=36, b=6))
    return apply_fig_theme(fig, height)


def ward_map(city_wards, color_by="Top_Source", height=460):
    t = get_theme()
    color_map = SOURCE_COLORS if color_by == "Top_Source" else None
    fig = px.scatter_mapbox(
        city_wards, lat="lat", lon="lon", size="Simulated_AQI", color=color_by,
        hover_name="Ward",
        hover_data={"Simulated_AQI": True, "lat": False, "lon": False},
        zoom=10.2, height=height, size_max=32,
        color_discrete_map=color_map,
    )
    fig.update_layout(
        mapbox_style=mapbox_style(),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=t["chart_paper"],
        legend=dict(bgcolor=t["card"], font=dict(color=t["text1"]), bordercolor=t["border"], borderwidth=1),
    )
    return fig
