"""
Central configuration: navigation, colors, breakpoints, icon maps.
Keeping every "magic value" here means the rest of the app never
hardcodes strings/colors, which is what makes the UI easy to re-theme.
"""

APP_NAME = "AQI Intelligence"
APP_TAGLINE = "AI Powered Urban Air Quality Intelligence"

CITIES = ["Delhi", "Mumbai"]

# Cities supported on the Geospatial Intelligence map (independent of the
# forecasting models, which are only trained for CITIES above).
GEO_CITIES = ["Delhi", "Mumbai", "Chennai", "Bangalore", "Kolkata"]

GEO_CITY_CENTERS = {
    "Delhi":     (28.6139, 77.2090),
    "Mumbai":    (19.0760, 72.8777),
    "Chennai":   (13.0827, 80.2707),
    "Bangalore": (12.9716, 77.5946),
    "Kolkata":   (22.5726, 88.3639),
}

# Map layer -> (icon glyph, marker color) used on the geospatial dashboard
GEO_LAYER_META = {
    "hotspot":            {"icon": "🔥", "color": "#ef4444", "label": "Hotspots"},
    "monitoring_station": {"icon": "📡", "color": "#22d3ee", "label": "Monitoring Stations"},
    "industrial":         {"icon": "🏭", "color": "#f97316", "label": "Industrial Areas"},
    "construction":       {"icon": "🏗️", "color": "#eab308", "label": "Construction Sites"},
    "school":             {"icon": "🏫", "color": "#a855f7", "label": "Schools"},
    "hospital":           {"icon": "🏥", "color": "#ec4899", "label": "Hospitals"},
    "traffic":            {"icon": "🚗", "color": "#3b82f6", "label": "Traffic Density"},
}

# ---------------------------------------------------------------- nav ----
NAV_ITEMS = [
    {"key": "executive",      "label": "Executive Dashboard",       "icon": "🏛️"},
    {"key": "overview",       "label": "Overview",                  "icon": "🏠"},
    {"key": "forecast",       "label": "AQI Forecast",               "icon": "📈"},
    {"key": "attribution",    "label": "Pollution Source Attribution", "icon": "🛰️"},
    {"key": "enforcement",    "label": "Enforcement Intelligence",   "icon": "🚨"},
    {"key": "intervention",   "label": "Intervention Simulator",     "icon": "🧪"},
    {"key": "ai_agents",      "label": "Multi-Agent AI Console",     "icon": "🤖"},
    {"key": "assistant",      "label": "AI Assistant",               "icon": "💬"},
    {"key": "advisory",       "label": "Citizen Health Advisory",    "icon": "🏥"},
    {"key": "geospatial",     "label": "Geospatial Intelligence",    "icon": "🗺️"},
    {"key": "multi_city",     "label": "Multi City Comparison",      "icon": "📊"},
    {"key": "settings",       "label": "Settings",                   "icon": "⚙️"},
]

# ---------------------------------------------------------- AQI scale ----
# Indian National AQI breakpoints -> (label, color, glow-color)
AQI_BANDS = [
    (0,   50,  "Good",         "#22c55e"),
    (51,  100, "Satisfactory", "#84cc16"),
    (101, 200, "Moderate",     "#facc15"),
    (201, 300, "Poor",         "#fb923c"),
    (301, 400, "Very Poor",    "#f87171"),
    (401, 10_000, "Severe",    "#c026d3"),
]

# ------------------------------------------------------- source colors ----
SOURCE_COLORS = {
    "Traffic":                  "#3b82f6",
    "Construction/Dust":        "#f59e0b",
    "Industrial":                "#ef4444",
    "Crop/Biomass Burning":      "#84cc16",
    "Secondary/Photochemical":  "#a855f7",
}

SOURCE_ICONS = {
    "Traffic":                  "🚗",
    "Construction/Dust":        "🏗️",
    "Industrial":                "🏭",
    "Crop/Biomass Burning":      "🔥",
    "Secondary/Photochemical":  "🌫️",
}

# Icons for the 5 Source Attribution Agent categories (Traffic / Industry /
# Dust / Biomass Burning / Construction) — distinct from SOURCE_ICONS above,
# which uses the underlying engine's original 5-category naming.
SOURCE_ICONS_5 = {
    "Traffic":          "🚗",
    "Industry":         "🏭",
    "Dust":             "🌪️",
    "Biomass Burning":  "🔥",
    "Construction":     "🏗️",
}

WARD_TYPE_ICONS = {
    "traffic_hub":   "🚦",
    "industrial":    "🏭",
    "residential":   "🏘️",
    "mixed":         "🏙️",
    "construction":  "🏗️",
    "green_belt":    "🌳",
}

# --------------------------------------------------------- brand colors ----
ACCENT_BLUE = "#3b82f6"
ACCENT_CYAN = "#22d3ee"
ACCENT_PURPLE = "#a855f7"
