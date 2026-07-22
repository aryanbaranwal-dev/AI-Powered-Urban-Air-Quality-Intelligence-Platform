"""
Everything visual that isn't a single component lives here:
- a light + dark color system (WCAG AA compliant) driven by st.session_state
- one big CSS block (glass cards / sidebar / buttons / forms / tables) that
  reads the active theme's CSS custom properties
- a shared Plotly template, rebuilt per-theme, so every chart matches
- small color helpers (AQI band, source color) used across sections

Theme switching model
----------------------
Streamlit re-runs the whole script on every interaction, so we don't need
any client-side JS to "switch" themes: `st.session_state["theme"]` holds
"dark" or "light", `inject_css()` renders a <style> block with that theme's
values baked in as CSS variables, and `register_plotly_theme()` rebuilds the
Plotly template the same way. Flipping the toggle just changes the session
value and reruns - every card, chart, badge and native widget re-renders
with the new palette because they all read the CSS vars / template below.
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from app.config import AQI_BANDS, SOURCE_COLORS, SOURCE_ICONS

PLOTLY_TEMPLATE_NAME = "aqi_theme"

# --------------------------------------------------------------------------
# Color system - values as specified: WCAG AA text contrast in both modes.
# --------------------------------------------------------------------------
THEMES = {
    "dark": {
        "bg0": "#0B1220",
        "bg1": "#080D17",
        "sidebar": "#0F172A",
        "card": "#111827",
        "card2": "#1E293B",
        "border": "#334155",
        "border_strong": "#475569",
        "primary": "#3B82F6",
        "secondary": "#06B6D4",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "text1": "#F8FAFC",
        "text2": "#CBD5E1",
        "text3": "#94A3B8",
        "hover": "#182338",
        "glass": "rgba(17,24,39,0.82)",
        "glass2": "rgba(30,41,59,0.82)",
        "shadow": "rgba(2,6,16,0.45)",
        "shadow_soft": "rgba(2,6,16,0.28)",
        "fill1": "rgba(248,250,252,0.035)",
        "fill2": "rgba(248,250,252,0.065)",
        "fill3": "rgba(248,250,252,0.11)",
        "scrollbar": "rgba(248,250,252,0.14)",
        "chart_paper": "#000000",
        "chart_grid": "rgba(148,163,184,0.14)",
        "chart_zeroline": "rgba(148,163,184,0.20)",
        "chart_axisline": "rgba(148,163,184,0.28)",
        "mapbox_style": "carto-darkmatter",
        "scheme": "dark",
    },
    "light": {
        "bg0": "#F3F6FB",
        "bg1": "#EAF0F8",
        "sidebar": "#FFFFFF",
        "card": "#FFFFFF",
        "card2": "#F8FAFC",
        "border": "#D6DEE8",
        "border_strong": "#94A3B8",
        "primary": "#2563EB",
        "secondary": "#0891B2",
        "success": "#16A34A",
        "warning": "#D97706",
        "danger": "#DC2626",
        "text1": "#0F172A",
        "text2": "#334155",
        "text3": "#64748B",
        "hover": "#F8FAFC",
        "glass": "rgba(255,255,255,0.88)",
        "glass2": "rgba(241,245,249,0.92)",
        "shadow": "rgba(15,23,42,0.12)",
        "shadow_soft": "rgba(15,23,42,0.07)",
        "fill1": "rgba(15,23,42,0.03)",
        "fill2": "rgba(15,23,42,0.055)",
        "fill3": "rgba(15,23,42,0.09)",
        "scrollbar": "rgba(15,23,42,0.16)",
        "chart_paper": "#FFFFFF",
        "chart_grid": "rgba(51,65,85,0.10)",
        "chart_zeroline": "rgba(51,65,85,0.16)",
        "chart_axisline": "rgba(51,65,85,0.22)",
        "mapbox_style": "carto-positron",
        "scheme": "light",
    },
}


def get_theme_name() -> str:
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    return st.session_state.theme


def get_theme() -> dict:
    """Return the active theme's color dict - the single source of truth
    every component/chart should pull from instead of hardcoding hex."""
    return THEMES[get_theme_name()]


def set_theme(name: str):
    if name in THEMES:
        st.session_state.theme = name


def toggle_theme():
    st.session_state.theme = "light" if get_theme_name() == "dark" else "dark"


def theme_toggle_button(key: str = "theme_toggle_btn", use_container_width: bool = True):
    """Small icon+label control that flips the theme and reruns. Safe to
    drop into the sidebar, navbar, or Settings page - all read the same
    session_state key so they always agree."""
    is_dark = get_theme_name() == "dark"
    label = "🌙  Dark mode" if is_dark else "☀️  Light mode"
    if st.button(label, key=key, use_container_width=use_container_width):
        toggle_theme()
        st.rerun()


# --------------------------------------------------------------------------
# AQI bands - brand-standard CPCB hues used for dots/badges/gauges in both
# themes (fine at AA on colored badge backgrounds); a darker AA-safe variant
# is provided for direct body text on a plain card background.
# --------------------------------------------------------------------------
_AQI_TEXT_DARK = ["#22c55e", "#a3e635", "#facc15", "#fb923c", "#f87171", "#e879f9"]
_AQI_TEXT_LIGHT = ["#15803d", "#4d7c0f", "#a16207", "#c2410c", "#b91c1c", "#86198f"]


def get_aqi_meta(aqi: float) -> dict:
    """Return label/color/text_color/glow for a given AQI value, Indian CPCB bands.

    `color` is the vivid brand hue (for dots, gauge fills, badge backgrounds).
    `text_color` is a theme-adjusted, AA-contrast-safe variant meant for
    plain text/numbers sitting directly on a card background.
    """
    if aqi is None:
        aqi = 0
    theme = get_theme()
    text_table = _AQI_TEXT_DARK if theme["scheme"] == "dark" else _AQI_TEXT_LIGHT
    for i, (lo, hi, label, color) in enumerate(AQI_BANDS):
        if lo <= aqi <= hi:
            return {"label": label, "color": color, "text_color": text_table[i], "band": (lo, hi)}
    lo, hi, label, color = AQI_BANDS[-1]
    return {"label": label, "color": color, "text_color": text_table[-1], "band": (lo, hi)}


def get_source_color(source: str) -> str:
    return SOURCE_COLORS.get(source, get_theme()["primary"])


def get_source_icon(source: str) -> str:
    return SOURCE_ICONS.get(source, "🌫️")


# --------------------------------------------------------------------------
# Status colors - AA-safe good/warn/bad text meant to sit directly on a
# card background (dots, badges with their own tinted background can keep
# using theme()['success'/'warning'/'danger'] directly; anywhere a color is
# used as *text on the plain card surface*, use this instead so light mode
# never ends up with a pale red/yellow on white).
# --------------------------------------------------------------------------
_STATUS_TEXT_DARK = {"good": "#22c55e", "warn": "#facc15", "bad": "#f87171"}
_STATUS_TEXT_LIGHT = {"good": "#15803d", "warn": "#a16207", "bad": "#b91c1c"}

_SEVERITY_TEXT_DARK = {
    "CRITICAL": "#e879f9", "SEVERE": "#f87171", "HIGH": "#fb923c",
    "MODERATE": "#facc15", "LOW": "#22c55e",
}
_SEVERITY_TEXT_LIGHT = {
    "CRITICAL": "#a21caf", "SEVERE": "#b91c1c", "HIGH": "#c2410c",
    "MODERATE": "#a16207", "LOW": "#15803d",
}


def get_status_text_color(kind: str) -> str:
    """kind: 'good' | 'warn' | 'bad'. Returns a theme-adjusted, AA-contrast-safe
    hex for plain text/labels/numbers sitting directly on a card background."""
    theme = get_theme()
    table = _STATUS_TEXT_DARK if theme["scheme"] == "dark" else _STATUS_TEXT_LIGHT
    return table.get(kind, theme["text2"])


def get_severity_text_color(level: str) -> str:
    """Map a severity label (CRITICAL/SEVERE/HIGH/MODERATE/LOW) to an
    AA-safe text color for the active theme - keeps all 5 tiers visually
    distinct instead of collapsing to a 3-color good/warn/bad scale."""
    theme = get_theme()
    table = _SEVERITY_TEXT_DARK if theme["scheme"] == "dark" else _SEVERITY_TEXT_LIGHT
    return table.get(str(level).upper(), theme["text2"])


# --------------------------------------------------------------------------
# Plotly - rebuilt every run against the active theme so every chart that
# calls apply_fig_theme() (i.e. all of them) adapts automatically: grid at
# low opacity, labels always readable, legend always visible.
# --------------------------------------------------------------------------
def register_plotly_theme():
    t = get_theme()
    template = go.layout.Template()
    template.layout = go.Layout(
        paper_bgcolor=t["chart_paper"],
        plot_bgcolor=t["chart_paper"],
        font=dict(family="Inter, -apple-system, sans-serif", color=t["text2"], size=13),
        colorway=[t["primary"], t["secondary"], "#a855f7", t["success"], t["warning"], t["danger"], "#84cc16"],
        xaxis=dict(
            gridcolor=t["chart_grid"], zerolinecolor=t["chart_zeroline"],
            linecolor=t["chart_axisline"], tickfont=dict(color=t["text3"]),
            title=dict(font=dict(color=t["text3"])),
        ),
        yaxis=dict(
            gridcolor=t["chart_grid"], zerolinecolor=t["chart_zeroline"],
            linecolor=t["chart_axisline"], tickfont=dict(color=t["text3"]),
            title=dict(font=dict(color=t["text3"])),
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=t["text1"]), itemwidth=30),
        hoverlabel=dict(
            bgcolor=t["card"], font=dict(color=t["text1"], family="Inter", size=12.5),
            bordercolor=t["border"], align="left",
        ),
        margin=dict(l=16, r=16, t=44, b=16),
        modebar=dict(bgcolor="rgba(0,0,0,0)", color=t["text3"], activecolor=t["primary"]),
    )
    pio.templates[PLOTLY_TEMPLATE_NAME] = template
    pio.templates.default = PLOTLY_TEMPLATE_NAME


def apply_fig_theme(fig: go.Figure, height: int = 400) -> go.Figure:
    """Apply the current template + force the legend to stay legible
    (never allowed to inherit a transparent/invisible font color)."""
    t = get_theme()
    fig.update_layout(
        template=PLOTLY_TEMPLATE_NAME,
        height=height,
        legend=dict(orientation="h", y=1.12, x=0, font=dict(color=t["text1"], size=12)),
    )
    return fig


def mapbox_style() -> str:
    return get_theme()["mapbox_style"]


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
def _css_vars(t: dict) -> str:
    return f"""
:root{{
  --bg-0:{t['bg0']};
  --bg-1:{t['bg1']};
  --sidebar-bg:{t['sidebar']};
  --card:{t['card']};
  --chart-bg:{t['chart_paper']};
  --card-2:{t['card2']};
  --glass:{t['glass']};
  --glass-2:{t['glass2']};
  --border:{t['border']};
  --border-strong:{t['border_strong']};
  --hover:{t['hover']};
  --text-1:{t['text1']};
  --text-2:{t['text2']};
  --text-3:{t['text3']};
  --primary:{t['primary']};
  --secondary:{t['secondary']};
  --success:{t['success']};
  --warning:{t['warning']};
  --danger:{t['danger']};
  --blue:{t['primary']};
  --cyan:{t['secondary']};
  --purple:#a855f7;
  --grad: linear-gradient(120deg, {t['primary']} 0%, {t['secondary']} 100%);
  --grad-soft: linear-gradient(135deg, {t['primary']}17 0%, {t['secondary']}12 100%);
  --grad-accent: linear-gradient(120deg, {t['secondary']} 0%, #a855f7 100%);
  --shadow:{t['shadow']};
  --shadow-soft:{t['shadow_soft']};
  --fill-1:{t['fill1']};
  --fill-2:{t['fill2']};
  --fill-3:{t['fill3']};
  --scrollbar:{t['scrollbar']};
  --focus-ring: 0 0 0 3px {t['primary']}55;

  /* Layered elevation - premium depth (ambient + direct shadow) */
  --elev-1: 0 1px 2px {t['shadow_soft']}, 0 4px 10px {t['shadow_soft']};
  --elev-2: 0 2px 4px {t['shadow_soft']}, 0 10px 24px {t['shadow']};
  --elev-3: 0 4px 10px {t['shadow']}, 0 20px 48px {t['shadow']};
  --elev-hover: 0 6px 14px {t['shadow']}, 0 26px 56px {t['primary']}26;

  /* 4px-based spacing scale - consistent rhythm across cards/sections */
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px;
  --space-5:20px; --space-6:24px; --space-7:32px; --space-8:40px;
  --radius-sm:10px; --radius-md:14px; --radius-lg:18px; --radius-xl:22px;

  --font-title:32px;
  --font-section:22px;
  --font-card-title:16px;
  --font-metric:36px;
  --font-body:15px;
}}
"""


def inject_css():
    t = get_theme()
    is_dark = t["scheme"] == "dark"

    # Page-level ambience: dark keeps soft glow blobs; light stays flat/clean
    # (matches the flat SaaS look of Grafana/Datadog/Fabric in day mode).
    if is_dark:
        app_bg = """
    radial-gradient(circle at 12% 8%, rgba(59,130,246,0.16) 0%, transparent 42%),
    radial-gradient(circle at 88% 6%, rgba(6,182,212,0.13) 0%, transparent 40%),
    radial-gradient(circle at 50% 100%, rgba(59,130,246,0.08) 0%, transparent 45%),
    linear-gradient(180deg, var(--bg-0) 0%, var(--bg-1) 100%)"""
    else:
        app_bg = """
    radial-gradient(circle at 12% 0%, rgba(37,99,235,0.05) 0%, transparent 40%),
    radial-gradient(circle at 90% 4%, rgba(8,145,178,0.05) 0%, transparent 38%),
    linear-gradient(180deg, var(--bg-0) 0%, var(--bg-1) 100%)"""

    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Manrope:wght@700;800&display=swap');
</style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<style>
{_css_vars(t)}

html, body, [class*="css"]{{ font-family:'Inter',sans-serif; font-size:var(--font-body); color:var(--text-2); }}

/* ---------- App background ---------- */
.stApp{{
  background: {app_bg};
  background-attachment: fixed;
  color: var(--text-1);
}}

/* Hide default streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"]{{ background:transparent; }}
header[data-testid="stHeader"]{{ box-shadow:none; }}
div[data-testid="stDecoration"]{{ display:none; }}
.block-container{{ padding-top:1.1rem; padding-bottom:2.5rem; max-width:1500px; }}

/* Default text color everywhere Streamlit renders markdown/body copy */
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span, .stCaption, p, label, span{{ color:var(--text-2); }}
h1, h2, h3, h4, h5, h6{{ color:var(--text-1) !important; }}
h1{{ font-size:var(--font-title) !important; font-weight:800 !important; }}
h2{{ font-size:var(--font-section) !important; font-weight:700 !important; }}
h3{{ font-size:18px !important; font-weight:700 !important; }}
a{{ color:var(--primary); }}

/* Focus visibility for accessibility (WCAG AA) */
button:focus-visible, [role="button"]:focus-visible, input:focus-visible,
[data-baseweb="select"]:focus-within, [tabindex]:focus-visible{{
  outline:none !important; box-shadow:var(--focus-ring) !important; border-radius:8px;
}}

/* Scrollbar */
::-webkit-scrollbar{{ width:10px; height:10px; }}
::-webkit-scrollbar-track{{ background:transparent; }}
::-webkit-scrollbar-thumb{{ background:var(--scrollbar); border-radius:8px; }}
::-webkit-scrollbar-thumb:hover{{ background:var(--border-strong); }}

/* ---------------------------- Sidebar ---------------------------- */
section[data-testid="stSidebar"]{{
  background: linear-gradient(180deg, var(--sidebar-bg) 0%, var(--bg-0) 100%);
  border-right:1px solid var(--border);
  box-shadow: 4px 0 24px var(--shadow-soft);
}}
section[data-testid="stSidebar"] *{{ color:var(--text-2); }}
section[data-testid="stSidebar"] .block-container{{ padding-top:1.4rem; }}

.brand-wrap{{ display:flex; align-items:center; gap:10px; padding:2px 4px 18px 4px; }}
.brand-badge{{
  width:40px;height:40px;border-radius:12px;
  background:var(--grad); display:flex;align-items:center;justify-content:center;
  font-size:20px; box-shadow:0 0 22px {t['primary']}55;
}}
.brand-title{{ font-weight:800; font-size:16px; color:var(--text-1); line-height:1.15; }}
.brand-sub{{ font-size:11px; color:var(--text-3); letter-spacing:.03em; }}

/* Sidebar nav buttons */
section[data-testid="stSidebar"] div[data-testid="stButton"] > button{{
  width:100%; text-align:left; justify-content:flex-start;
  background:transparent !important; border:1px solid transparent !important;
  color:var(--text-2) !important; font-weight:500; font-size:14px;
  padding:9px 12px; border-radius:10px; margin-bottom:3px;
  transition:all .18s ease; box-shadow:none !important;
}}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover{{
  background:var(--fill-2) !important; color:var(--text-1) !important;
  border:1px solid var(--border) !important; transform:translateX(2px);
}}
/* Active menu item: blue -> cyan gradient, always AA-readable text */
section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]{{
  background:var(--grad) !important;
  border:1px solid transparent !important;
  color:#ffffff !important; font-weight:700;
  box-shadow:0 4px 18px {t['primary']}40 !important;
}}
.sidebar-foot{{
  margin-top:10px; padding:12px 12px; border-radius:12px;
  background:var(--fill-1); border:1px solid var(--border);
  font-size:11.5px; color:var(--text-3); line-height:1.5;
}}
.sidebar-foot b{{ color:var(--text-1); }}

/* ---------------------------- Theme toggle ---------------------------- */
.theme-toggle-wrap div[data-testid="stButton"] > button{{
  background:var(--fill-1) !important; border:1px solid var(--border) !important;
  color:var(--text-1) !important; font-weight:600; border-radius:12px !important;
}}
.theme-toggle-wrap div[data-testid="stButton"] > button:hover{{
  background:var(--fill-2) !important; border-color:var(--border-strong) !important;
  transform:none !important;
}}

/* ---------------------------- Top navbar ---------------------------- */
.st-key-navbar_shell{{
  padding:12px 20px 4px 20px; margin-bottom:14px; border-radius:18px;
  background:var(--glass); border:1px solid var(--border);
  backdrop-filter:blur(18px); -webkit-backdrop-filter:blur(18px);
  box-shadow:0 8px 32px var(--shadow);
  position:sticky; top:0.4rem; z-index:999;
}}
.st-key-navbar_shell div[data-testid="stSelectbox"]{{ margin-top:2px; }}

/* Any keyed container ending in _card used as a content panel */
div[class*="st-key-"][class*="_card"]{{
  background:var(--glass); border:1px solid var(--border); border-radius:18px;
  padding:18px 20px 14px 20px; backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  box-shadow:0 6px 24px var(--shadow-soft); margin-bottom:16px;
  position:relative; overflow:hidden;
  transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
  animation: fadeInUp .5s ease both;
}}
div[class*="st-key-"][class*="_card"]:hover{{
  transform:translateY(-2px); border-color:var(--border-strong);
  box-shadow:0 14px 34px {t['primary']}22;
}}
.navbar-left{{ display:flex; align-items:center; gap:12px; }}
.navbar-logo{{
  width:44px;height:44px;border-radius:13px; background:var(--grad);
  display:flex;align-items:center;justify-content:center;font-size:22px;
  box-shadow:0 0 24px {t['primary']}55; flex-shrink:0;
}}
.navbar-title{{ font-weight:800; font-size:17px; color:var(--text-1); letter-spacing:-.01em; font-family:'Manrope','Inter',sans-serif; }}
.navbar-title .grad{{
  background:var(--grad); -webkit-background-clip:text; background-clip:text; color:transparent;
}}
.navbar-sub{{ font-size:12px; color:var(--text-3); margin-top:1px; }}
.navbar-pill{{
  display:flex; align-items:center; gap:8px; padding:8px 14px; border-radius:12px;
  background:var(--fill-1); border:1px solid var(--border); font-size:12.5px; color:var(--text-2);
}}
.navbar-pill b{{ color:var(--text-1); font-weight:600; }}
.live-dot{{
  width:7px;height:7px;border-radius:50%; background:var(--success); display:inline-block;
  box-shadow:0 0 8px var(--success); animation:pulse 1.8s infinite;
}}
@keyframes pulse{{ 0%{{opacity:1;}} 50%{{opacity:.35;}} 100%{{opacity:1;}} }}

/* ---------------------------- Forms: selects, sliders, radios, inputs ---------------------------- */
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stMultiSelect"] > div > div,
[data-baseweb="select"] > div{{
  background:var(--fill-1) !important; border:1px solid var(--border) !important;
  border-radius:12px !important; color:var(--text-1) !important;
}}
[data-baseweb="select"] *{{ color:var(--text-1) !important; }}
/* Dropdown popover (portal-rendered, not scoped to sidebar/card) */
[data-baseweb="popover"] [data-baseweb="menu"], [role="listbox"]{{
  background:var(--card) !important; border:1px solid var(--border) !important;
  box-shadow:0 12px 32px var(--shadow) !important;
}}
[role="option"]{{ color:var(--text-1) !important; }}
[role="option"]:hover, [aria-selected="true"][role="option"]{{ background:var(--fill-2) !important; }}

input, textarea{{
  background:var(--fill-1) !important; border:1px solid var(--border) !important;
  color:var(--text-1) !important; border-radius:10px !important;
}}
input::placeholder, textarea::placeholder{{ color:var(--text-3) !important; opacity:1; }}
div[data-testid="stNumberInput"] button{{ background:var(--fill-1) !important; color:var(--text-1) !important; }}

/* Sliders */
div[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"]{{
  background-color:var(--primary) !important; box-shadow:0 0 0 4px {t['primary']}25 !important;
}}
div[data-testid="stSlider"] [data-baseweb="slider"] > div > div{{ background:var(--primary) !important; }}
div[data-testid="stSlider"] [data-baseweb="slider"] > div{{ background:var(--fill-2) !important; }}
div[data-testid="stSlider"] [data-testid="stTickBar"]{{ color:var(--text-3) !important; }}
div[data-testid="stSlider"] label, div[data-testid="stSlider"] p{{ color:var(--text-2) !important; }}

/* Radio pills (language/channel pickers) + native radio dots */
div[role="radiogroup"] label{{
  background:var(--fill-1); border:1px solid var(--border); border-radius:10px;
  padding:6px 12px !important; margin-right:6px !important; color:var(--text-1) !important;
}}
div[role="radiogroup"] label:has(input:checked){{
  border-color:var(--primary); background:{t['primary']}18;
}}

/* Checkboxes / toggles */
div[data-testid="stCheckbox"] label p, div[data-testid="stToggle"] label p{{ color:var(--text-2) !important; }}
div[data-testid="stToggle"] [role="checkbox"][aria-checked="true"]{{ background:var(--primary) !important; }}

/* Labels & help/caption text everywhere */
.stCaption, [data-testid="stCaptionContainer"]{{ color:var(--text-3) !important; }}
div[data-testid="stWidgetLabel"] p{{ color:var(--text-2) !important; font-weight:600; font-size:13px; }}

/* ---------------------------- Glass cards ---------------------------- */
.glass-card{{
  background:var(--glass); border:1px solid var(--border); border-radius:18px;
  padding:20px 22px; backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  box-shadow:0 6px 24px var(--shadow-soft); position:relative; overflow:hidden;
  transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
  animation: fadeInUp .5s ease both;
}}
.glass-card:hover{{
  transform:translateY(-3px); border-color:var(--border-strong);
  box-shadow:0 14px 38px {t['primary']}22;
}}
.section-title{{
  font-size:var(--font-card-title); font-weight:700; color:var(--text-1); margin:2px 0 14px 2px;
  display:flex; align-items:center; gap:8px;
}}
.section-title .bar{{ width:4px; height:16px; border-radius:3px; background:var(--grad); display:inline-block;}}
.card-caption{{ font-size:12px; color:var(--text-3); margin-top:8px; line-height:1.5; }}
.small-caption{{ font-size:12px; color:var(--text-3); }}
.gradient-text{{ background:var(--grad); -webkit-background-clip:text; background-clip:text; color:transparent; font-weight:800; }}

/* ---------------------------- Metric cards ---------------------------- */
/* Gradient top-border accent strip - shared premium-card signature */
.metric-card::before, .glass-card::before,
div[class*="st-key-"][class*="_card"]::before{{
  content:""; position:absolute; top:0; left:0; right:0; height:3px;
  background:var(--grad); border-radius:18px 18px 0 0;
  opacity:.85; transition:opacity .25s ease;
}}
.metric-card:hover::before, .glass-card:hover::before,
div[class*="st-key-"][class*="_card"]:hover::before{{ opacity:1; }}

.metric-card{{
  background:var(--glass); border:1px solid var(--border); border-radius:18px;
  padding:18px 20px; position:relative; overflow:hidden;
  backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  box-shadow:0 6px 22px var(--shadow-soft);
  transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
  animation: fadeInUp .55s ease both;
  height:100%;
}}
.metric-card:hover{{ transform:translateY(-4px) scale(1.01); border-color:var(--border-strong); box-shadow:0 16px 40px {t['primary']}24; }}
.metric-card::after{{
  content:""; position:absolute; inset:0; opacity:0; transition:opacity .25s ease;
  background:radial-gradient(circle at 100% 0%, {t['primary']}22, transparent 60%);
}}
.metric-card:hover::after{{ opacity:1; }}
.metric-top{{ display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }}
.metric-icon{{
  width:38px;height:38px;border-radius:11px; display:flex;align-items:center;justify-content:center;
  font-size:18px; background:var(--fill-2); border:1px solid var(--border);
}}
.metric-label{{ font-size:12px; color:var(--text-2); font-weight:600; letter-spacing:.02em; text-transform:uppercase; }}
.metric-value{{ font-size:var(--font-metric); font-weight:800; color:var(--text-1); line-height:1.1; letter-spacing:-.02em; font-family:'Manrope','Inter',sans-serif; }}
.metric-delta{{ font-size:12px; font-weight:700; margin-top:6px; display:inline-flex; align-items:center; gap:4px; }}
.metric-sub{{ font-size:11.5px; color:var(--text-3); margin-top:4px; }}
.metric-spark{{ position:absolute; top:16px; right:18px; opacity:.9; pointer-events:none; }}

/* ---------------------------- Section title trailing slot + empty state ---------------------------- */
.section-title{{ position:relative; padding-right:2px; }}
.section-title-trailing{{ margin-left:auto; padding-left:10px; font-weight:500; font-size:12px; text-transform:none; letter-spacing:normal; }}
.empty-state{{
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  text-align:center; padding:34px 16px; color:var(--text-3);
}}
.empty-state-icon{{ font-size:26px; opacity:.55; margin-bottom:8px; }}
.empty-state-msg{{ font-size:13px; font-weight:600; color:var(--text-2); }}
.empty-state-sub{{ font-size:11.5px; color:var(--text-3); margin-top:3px; }}

/* ---------------------------- Executive hero banner ---------------------------- */
.exec-hero{{
  position:relative; overflow:hidden; border-radius:20px; padding:22px 26px;
  background:var(--glass); border:1px solid var(--border);
  backdrop-filter:blur(18px); -webkit-backdrop-filter:blur(18px);
  box-shadow:0 10px 30px var(--shadow); margin-bottom:14px;
  animation: fadeInUp .5s ease both;
}}
.exec-hero::before{{
  content:""; position:absolute; top:0; left:0; right:0; height:3px;
  background:linear-gradient(120deg, var(--hero-accent, var(--primary)) 0%, var(--secondary) 100%);
}}
.exec-hero-glow{{
  position:absolute; top:-40%; right:-8%; width:280px; height:280px; border-radius:50%;
  background:radial-gradient(circle, var(--hero-accent, var(--primary)) 0%, transparent 68%);
  opacity:.16; pointer-events:none;
}}
.exec-hero-row{{ position:relative; display:flex; align-items:center; justify-content:space-between; gap:20px; flex-wrap:wrap; }}
.exec-hero-eyebrow{{ font-size:11px; font-weight:700; letter-spacing:.08em; color:var(--text-3); margin-bottom:4px; }}
.exec-hero-title{{ font-size:24px; font-weight:800; color:var(--text-1); line-height:1.2; }}
.exec-hero-sub{{ font-size:12.5px; color:var(--text-3); margin-top:4px; }}
.exec-hero-readout{{ display:flex; align-items:center; gap:14px; }}
.exec-hero-aqi{{ font-size:44px; font-weight:800; font-family:'Manrope','Inter',sans-serif; line-height:1; letter-spacing:-.02em; }}
@media (max-width: 900px){{
  .exec-hero-title{{ font-size:19px; }}
  .exec-hero-aqi{{ font-size:32px; }}
}}

@keyframes fadeInUp{{
  from{{ opacity:0; transform:translateY(14px); }}
  to{{ opacity:1; transform:translateY(0); }}
}}

/* ---------------------------- Badges / pills ---------------------------- */
.badge{{
  display:inline-flex; align-items:center; gap:6px; padding:4px 11px; border-radius:999px;
  font-size:11.5px; font-weight:700; letter-spacing:.02em;
}}
.badge-dot{{ width:7px;height:7px;border-radius:50%; }}

/* ---------------------------- Alert / action rows ---------------------------- */
.alert-row{{
  display:flex; align-items:flex-start; gap:12px; padding:13px 14px; border-radius:14px;
  background:var(--fill-1); border:1px solid var(--border); margin-bottom:9px;
  transition: all .18s ease; animation: fadeInUp .5s ease both;
}}
.alert-row:hover{{ background:var(--fill-2); border-color:var(--border-strong); transform:translateX(2px); }}
.alert-icon{{ font-size:17px; margin-top:1px; }}
.alert-title{{ font-size:13.5px; font-weight:600; color:var(--text-1); }}
.alert-meta{{ font-size:11.5px; color:var(--text-3); margin-top:2px; }}

/* ---------------------------- Misc ---------------------------- */
hr{{ border-color:var(--border); }}

div[data-testid="stExpander"]{{
  background:var(--glass); border:1px solid var(--border); border-radius:14px; overflow:hidden;
}}
div[data-testid="stExpander"] summary{{ color:var(--text-1) !important; }}

/* ---------------------------- Tables ---------------------------- */
div[data-testid="stDataFrame"]{{
  border-radius:14px; overflow:hidden; border:1px solid var(--border);
  box-shadow:0 6px 18px var(--shadow-soft);
}}
/* Streamlit's dataframe grid reads these custom properties for its canvas
   theme (glide-data-grid) so header/cell colors follow our palette too. */
div[data-testid="stDataFrame"]{{
  --gdg-bg-cell: {t['card']};
  --gdg-bg-cell-medium: {t['card2']};
  --gdg-bg-header: {t['card2']};
  --gdg-bg-header-has-focus: {t['fill2']};
  --gdg-bg-header-hovered: {t['fill2']};
  --gdg-text-dark: {t['text1']};
  --gdg-text-medium: {t['text2']};
  --gdg-text-light: {t['text3']};
  --gdg-text-header: {t['text1']};
  --gdg-border-color: {t['border']};
  --gdg-accent-color: {t['primary']};
  --gdg-accent-light: {t['primary']}22;
}}
/* Real HTML tables (st.table / markdown tables) - alternating rows, sticky header */
table{{ border-collapse:separate !important; border-spacing:0; width:100%; }}
table thead th{{
  position:sticky; top:0; z-index:1; background:var(--card-2) !important; color:var(--text-1) !important;
  font-weight:700; font-size:12.5px; text-transform:uppercase; letter-spacing:.02em;
  padding:10px 12px !important; border-bottom:1px solid var(--border) !important;
}}
table tbody td{{ padding:9px 12px !important; color:var(--text-2) !important; border-bottom:1px solid var(--border) !important; font-size:13.5px; }}
table tbody tr:nth-child(even){{ background:var(--fill-1); }}
table tbody tr:hover{{ background:var(--fill-2); }}

/* ---------------------------- Buttons ---------------------------- */
div[data-testid="stButton"] > button{{
  border-radius:11px; border:1px solid var(--border); background:var(--fill-1); color:var(--text-1);
  font-weight:600; transition:all .18s ease;
}}
div[data-testid="stButton"] > button:hover{{
  border-color:var(--border-strong); background:var(--fill-2); transform:translateY(-1px);
  box-shadow:0 6px 16px var(--shadow-soft);
}}
div[data-testid="stButton"] > button:active{{ transform:translateY(0) scale(.97); transition:transform .08s ease; }}
/* Primary = blue, Secondary = grey (Streamlit's own type= values) */
div[data-testid="stButton"] > button[kind="primary"]{{
  background:var(--grad) !important; border:1px solid transparent !important; color:#ffffff !important;
  box-shadow:0 6px 18px {t['primary']}35 !important;
}}
div[data-testid="stButton"] > button[kind="primary"]:hover{{ filter:brightness(1.08); }}
div[data-testid="stButton"] > button[kind="secondary"]{{
  background:var(--fill-1) !important; border:1px solid var(--border) !important; color:var(--text-1) !important;
}}
/* Success / danger button variants - wrap a button in
   st.container(key="..._success") or ("..._danger") to opt in. */
div[class*="st-key-"][class*="_success"] div[data-testid="stButton"] > button{{
  background:{t['success']} !important; border:1px solid {t['success']} !important; color:#ffffff !important;
}}
div[class*="st-key-"][class*="_success"] div[data-testid="stButton"] > button:hover{{ filter:brightness(1.08); }}
div[class*="st-key-"][class*="_danger"] div[data-testid="stButton"] > button{{
  background:{t['danger']} !important; border:1px solid {t['danger']} !important; color:#ffffff !important;
}}
div[class*="st-key-"][class*="_danger"] div[data-testid="stButton"] > button:hover{{ filter:brightness(1.08); }}

/* Streamlit native alert boxes (st.success/info/warning/error) */
div[data-testid="stAlert"]{{ border-radius:12px !important; border:1px solid var(--border) !important; }}
div[data-testid="stAlertContentSuccess"], div[data-testid="stAlertContentSuccess"] p{{ color:{t['success']} !important; }}
div[data-testid="stAlertContentError"], div[data-testid="stAlertContentError"] p{{ color:{t['danger']} !important; }}
div[data-testid="stAlertContentWarning"], div[data-testid="stAlertContentWarning"] p{{ color:{t['warning']} !important; }}
div[data-testid="stAlertContentInfo"], div[data-testid="stAlertContentInfo"] p{{ color:{t['primary']} !important; }}

/* ---------------------------- Explainable AI cards ---------------------------- */
.xai-card{{
  background:var(--glass); border:1px solid var(--border); border-radius:18px;
  padding:20px 22px 18px 22px; backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  box-shadow:0 6px 24px var(--shadow-soft); animation: fadeInUp .55s ease both;
  height:100%;
}}
.xai-card-head{{ display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:14px; }}
.xai-card-label{{ font-size:11.5px; color:var(--text-2); font-weight:700; text-transform:uppercase; letter-spacing:.03em; }}
.xai-card-value{{ font-size:var(--font-metric); font-weight:800; line-height:1.1; letter-spacing:-.02em; margin-top:2px; font-family:'Manrope','Inter',sans-serif; }}
.xai-card-band{{ font-size:12px; font-weight:700; margin-top:2px; }}
.xai-conf-ring{{
  width:64px; height:64px; border-radius:50%; border:3px solid; display:flex; flex-direction:column;
  align-items:center; justify-content:center; flex-shrink:0; background:var(--fill-1);
}}
.xai-conf-pct{{ font-size:15px; font-weight:800; line-height:1; }}
.xai-conf-label{{ font-size:8.5px; color:var(--text-3); text-transform:uppercase; letter-spacing:.02em; margin-top:2px; }}
.xai-section-label{{
  font-size:11px; font-weight:700; color:var(--text-2); text-transform:uppercase; letter-spacing:.03em;
  margin:12px 0 6px 0;
}}
.xai-factors{{ display:flex; flex-direction:column; gap:5px; }}
.xai-factor-row{{
  display:flex; align-items:center; gap:8px; font-size:12.5px; color:var(--text-1);
  background:var(--fill-1); border:1px solid var(--border); border-radius:9px; padding:6px 10px;
}}
.xai-factor-dot{{ width:7px; height:7px; border-radius:50%; flex-shrink:0; }}
.xai-factor-name{{ flex:1; }}
.xai-factor-impact{{ font-weight:700; font-variant-numeric:tabular-nums; }}
.xai-reason-list{{ margin:0; padding-left:18px; font-size:12.5px; color:var(--text-2); line-height:1.65; }}
.xai-trend-row{{
  display:flex; align-items:center; justify-content:space-between; margin-top:12px;
  padding-top:10px; border-top:1px dashed var(--border); font-size:12.5px;
}}
.xai-trend-label{{ color:var(--text-3); font-weight:600; }}
.xai-trend-value{{ color:var(--text-1); font-weight:700; }}
.xai-intervention{{
  margin-top:12px; padding:11px 13px; border-radius:12px; font-size:12px; line-height:1.55;
  background:{t['success']}14; border:1px solid {t['success']}48; color:var(--text-1);
}}

/* ---------------------------- Agent JSON console cards ---------------------------- */
.agent-card{{
  background:var(--glass); border:1px solid var(--border); border-radius:18px;
  padding:16px 18px; backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  box-shadow:0 6px 22px var(--shadow-soft); animation: fadeInUp .5s ease both; height:100%;
}}
.agent-card-head{{ display:flex; align-items:center; gap:10px; margin-bottom:10px; }}
.agent-card-icon{{
  width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center;
  font-size:16px; background:var(--fill-2); border:1px solid var(--border); flex-shrink:0;
}}
.agent-card-title{{ font-size:13.5px; font-weight:700; color:var(--text-1); }}
.agent-card-sub{{ font-size:10.5px; color:var(--text-3); font-family:'JetBrains Mono',monospace; }}
.agent-status-ok{{
  margin-left:auto; font-size:10px; font-weight:700; padding:3px 9px; border-radius:999px;
  background:{t['success']}22; color:{t['success']}; border:1px solid {t['success']}4d;
}}
.agent-flow{{
  display:flex; align-items:center; gap:6px; flex-wrap:wrap; font-size:12px; color:var(--text-2);
  background:var(--fill-1); border:1px solid var(--border); border-radius:12px; padding:12px 14px;
}}
.agent-flow-node{{
  padding:5px 11px; border-radius:999px; background:{t['primary']}1f; border:1px solid {t['primary']}4d;
  color:var(--text-1); font-weight:600; white-space:nowrap;
}}
.agent-flow-arrow{{ color:var(--text-3); }}

/* =====================================================================
   PREMIUM UX PASS - sticky chrome, skeletons, progress bars, animated
   icons, smooth AQI color transitions, responsive layout, refined type.
   ===================================================================== */

section[data-testid="stSidebar"] > div{{
  position:sticky; top:0; height:100vh; overflow-y:auto;
}}

.block-container{{ padding-left:1.6rem; padding-right:1.6rem; }}
div[class*="st-key-"][class*="_card"]{{ margin-bottom:16px; }}

.metric-value, .metric-icon, .badge, .xai-card-value, .xai-conf-ring{{
  transition: color .45s ease, background-color .45s ease, border-color .45s ease, box-shadow .45s ease;
}}

.metric-icon{{ transition: transform .3s cubic-bezier(.34,1.56,.64,1), background-color .3s ease; }}
.metric-card:hover .metric-icon{{ transform: scale(1.14) rotate(-6deg); }}

@keyframes iconFloat{{
  0%,100%{{ transform:translateY(0); }}
  50%{{ transform:translateY(-3px); }}
}}
.brand-badge, .navbar-logo{{ animation: iconFloat 3.2s ease-in-out infinite; }}

@keyframes iconPulseAlert{{
  0%,100%{{ transform:scale(1); }}
  50%{{ transform:scale(1.18); }}
}}
.alert-icon{{ display:inline-block; }}
.alert-row:hover .alert-icon{{ animation: iconPulseAlert .6s ease-in-out; }}

/* Progress / severity bars */
.progress-track{{
  width:100%; height:6px; border-radius:999px; background:var(--fill-2);
  overflow:hidden; margin-top:10px; position:relative;
}}
.progress-fill{{
  height:100%; border-radius:999px; background:var(--grad);
  transition: width .8s cubic-bezier(.16,1,.3,1), background-color .5s ease;
  animation: fillIn .9s cubic-bezier(.16,1,.3,1) both;
}}
@keyframes fillIn{{ from{{ width:0 !important; }} }}
.progress-label{{ display:flex; justify-content:space-between; font-size:10.5px; color:var(--text-3); margin-top:5px; }}

/* Loading skeletons */
@keyframes shimmer{{
  0%{{ background-position:-400px 0; }}
  100%{{ background-position:400px 0; }}
}}
.skeleton{{
  border-radius:14px; background:linear-gradient(90deg, var(--fill-1) 25%, var(--fill-3) 37%, var(--fill-1) 63%);
  background-size:800px 100%; animation: shimmer 1.4s ease-in-out infinite;
  border:1px solid var(--border);
}}
.skeleton-kpi{{ height:118px; }}
.skeleton-chart{{ height:320px; }}
.skeleton-line{{ height:12px; border-radius:6px; margin-bottom:8px; }}
.skeleton-wrap{{ display:flex; flex-direction:column; gap:14px; }}

div[data-testid="stPlotlyChart"]{{ transition: filter .25s ease; border-radius:14px; overflow:hidden; background:var(--chart-bg); border:1px solid var(--border); }}
div[data-testid="stPlotlyChart"]:hover{{ filter:brightness(1.02); }}

.block-container{{ animation: fadeInUp .35s ease both; }}

@media (max-width: 1200px){{
  .block-container{{ max-width:100% !important; padding-left:1rem; padding-right:1rem; }}
  .metric-value{{ font-size:26px; }}
  .navbar-sub{{ display:none; }}
}}
@media (max-width: 900px){{
  .st-key-navbar_shell{{ position:static; }}
  .metric-card, .glass-card, .xai-card, .agent-card{{ padding:14px 16px; }}
  .metric-value{{ font-size:23px; }}
  .metric-icon{{ width:32px; height:32px; font-size:15px; }}
  .section-title{{ font-size:13.5px; }}
}}

/* =====================================================================
   FINAL PREMIUM POLISH — whitespace, layered elevation, gradients,
   equal-height grids, icon rhythm, chart proportions, micro-interactions.
   Additive layer only: nothing above is overridden in structure, only
   refined in spacing / depth / motion so business logic stays untouched.
   ===================================================================== */

/* -- Breathing room: consistent vertical rhythm between stacked blocks -- */
.block-container{{ padding-top:1.35rem; }}
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]{{
  margin-bottom:var(--space-5);
}}
div[data-testid="column"]{{ padding-left:var(--space-2); padding-right:var(--space-2); }}
div[data-testid="stHorizontalBlock"]{{ gap:var(--space-4); align-items:stretch; }}
h1, h2, h3{{ letter-spacing:-.015em; }}
h1{{ margin-bottom:var(--space-2) !important; }}
h2{{ margin-top:var(--space-7) !important; margin-bottom:var(--space-4) !important; }}

/* -- Equal-height card rows: every card in a Streamlit column row now -- */
/* -- stretches to match its tallest sibling instead of ragged bottoms -- */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{{
  display:flex; flex-direction:column;
}}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] > div{{
  flex:1; display:flex; flex-direction:column;
}}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] div[data-testid="stVerticalBlockBorderWrapper"]{{
  flex:1;
}}

/* -- Layered / richer shadow system replacing flat single-layer blur -- */
.metric-card, .glass-card, .xai-card, .agent-card, .exec-hero,
div[class*="st-key-"][class*="_card"]{{
  box-shadow:var(--elev-2) !important;
  padding:var(--space-5) var(--space-6) !important;
  border-radius:var(--radius-lg) !important;
}}
.metric-card:hover, .glass-card:hover, div[class*="st-key-"][class*="_card"]:hover{{
  box-shadow:var(--elev-hover) !important;
}}
.st-key-navbar_shell{{ box-shadow:var(--elev-2) !important; }}
div[data-testid="stDataFrame"], div[data-testid="stExpander"]{{ box-shadow:var(--elev-1) !important; }}

/* -- Icon rhythm: consistent circular/rounded icon chips everywhere -- */
.metric-icon{{
  width:40px; height:40px; border-radius:12px; font-size:18px;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,0.03);
}}
.agent-card-icon{{ width:36px; height:36px; border-radius:11px; }}
.brand-badge{{ box-shadow:0 0 0 1px rgba(255,255,255,0.06), 0 0 22px {t['primary']}55; }}
.exec-hero-eyebrow, .metric-label, .xai-card-label{{ letter-spacing:.045em; }}

/* -- Gradient refinement: subtle sheen on primary brand surfaces -- */
.navbar-logo, .brand-badge{{
  background:var(--grad); position:relative; overflow:hidden;
}}
.navbar-logo::after, .brand-badge::after{{
  content:""; position:absolute; inset:0;
  background:linear-gradient(135deg, rgba(255,255,255,0.28) 0%, transparent 55%);
}}
.gradient-text{{ background:linear-gradient(120deg, {t['primary']} 0%, {t['secondary']} 55%, #a855f7 100%); -webkit-background-clip:text; background-clip:text; }}

/* -- Buttons: gradient sheen + lift, consistent with card elevation -- */
div[data-testid="stButton"] > button{{ border-radius:var(--radius-sm); padding:9px 16px; }}
div[data-testid="stButton"] > button:hover{{ box-shadow:var(--elev-1); }}
div[data-testid="stButton"] > button[kind="primary"]{{ box-shadow:var(--elev-2) !important; }}
div[data-testid="stButton"] > button[kind="primary"]:hover{{ box-shadow:var(--elev-hover) !important; transform:translateY(-1px); }}

/* -- Chart canvas: matches card elevation + generous internal padding -- */
div[data-testid="stPlotlyChart"]{{
  border-radius:var(--radius-md) !important; box-shadow:var(--elev-1);
  padding:2px;
}}

/* -- Micro-interaction easing: consistent premium cubic-bezier curve -- */
.metric-card, .glass-card, div[class*="st-key-"][class*="_card"],
div[data-testid="stButton"] > button, .alert-row, table tbody tr{{
  transition-timing-function: cubic-bezier(.2,.8,.2,1) !important;
}}

/* -- Section title: slightly larger gap + refined accent bar -- */
.section-title{{ margin:var(--space-1) 0 var(--space-4) var(--space-1); gap:var(--space-2); }}
.section-title .bar{{ width:4px; height:17px; border-radius:4px; box-shadow:0 0 8px {t['primary']}55; }}

/* -- Badges: slightly larger touch target, consistent radius -- */
.badge{{ padding:5px 12px; border-radius:999px; font-weight:700; }}

/* -- Loading skeletons: match final card radius/elevation exactly -- */
.skeleton{{ border-radius:var(--radius-lg); box-shadow:var(--elev-1); }}

/* -- Floating AI Assistant FAB (bottom-right, always reachable) -- */
.st-key-floating_assistant_fab{{
  position:fixed !important; right:26px; bottom:26px; z-index:1000;
  width:auto; box-shadow:none !important;
}}
.st-key-floating_assistant_fab div[data-testid="stButton"] > button{{
  width:60px !important; height:60px !important; border-radius:50% !important;
  background:var(--grad) !important; border:1px solid rgba(255,255,255,0.18) !important;
  color:#fff !important; font-size:24px !important; padding:0 !important;
  box-shadow:0 10px 28px {t['primary']}55, 0 4px 12px var(--shadow) !important;
  display:flex; align-items:center; justify-content:center;
  transition: transform .25s cubic-bezier(.34,1.56,.64,1), box-shadow .25s ease !important;
  animation: fabPulse 3s ease-in-out infinite;
}}
.st-key-floating_assistant_fab div[data-testid="stButton"] > button:hover{{
  transform:scale(1.09) translateY(-2px) !important;
  box-shadow:0 16px 38px {t['primary']}70, 0 6px 16px var(--shadow) !important;
}}
@keyframes fabPulse{{
  0%,100%{{ box-shadow:0 10px 28px {t['primary']}55, 0 4px 12px var(--shadow), 0 0 0 0 {t['primary']}40; }}
  50%{{ box-shadow:0 10px 28px {t['primary']}55, 0 4px 12px var(--shadow), 0 0 0 10px {t['primary']}00; }}
}}
@media (max-width: 900px){{
  .st-key-floating_assistant_fab{{ right:16px; bottom:16px; }}
  .st-key-floating_assistant_fab div[data-testid="stButton"] > button{{ width:52px !important; height:52px !important; font-size:20px !important; }}
}}
</style>
        """,
        unsafe_allow_html=True,
    )
