import streamlit as st

from app.theme import get_theme


def _accent_hex():
    t = get_theme()
    return {
        "blue": t["primary"],
        "cyan": t["secondary"],
        "purple": "#a855f7",
        "green": t["success"],
        "amber": t["warning"],
        "red": t["danger"],
    }


def _sparkline_svg(values, color, width=76, height=28):
    """Tiny inline SVG trend line - no Plotly overhead for a decorative
    per-card mini-trend. Renders a smooth line + soft area fill under it,
    plus a highlighted dot on the last (most recent) point."""
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    pad = 3
    n = len(vals)
    step = (width - 2 * pad) / (n - 1)
    pts = [
        (pad + i * step, pad + (1 - (v - lo) / span) * (height - 2 * pad))
        for i, v in enumerate(vals)
    ]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pad:.1f},{height - pad:.1f} " + poly + f" {pts[-1][0]:.1f},{height - pad:.1f}"
    lx, ly = pts[-1]
    return f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="overflow:visible;">
      <polygon points="{area}" fill="{color}" opacity="0.14"></polygon>
      <polyline points="{poly}" fill="none" stroke="{color}" stroke-width="1.8"
                stroke-linecap="round" stroke-linejoin="round"></polyline>
      <circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.6" fill="{color}"></circle>
    </svg>
    """


def metric_card(label, value, icon="📊", delta=None, delta_positive_is_good=False,
                 accent="blue", sub=None, delay=0.0, value_color=None, progress_pct=None,
                 trend=None):
    """Render one animated glass metric card.

    delta: string like "+12" or "-3.4%"; colored green/red based on sign
           and `delta_positive_is_good`.
    progress_pct: optional 0-100 float. When set, renders a thin animated
           severity/progress bar under the value (e.g. AQI as % of the
           500-point scale, or a completion/success percentage).
    trend: optional list of recent numeric values (oldest -> newest).
           When set, renders a small inline sparkline in the card's top
           corner next to the icon, giving the number visible context
           without needing a full chart.
    """
    t = get_theme()
    accent_hex = _accent_hex()
    color = accent_hex.get(accent, accent_hex["blue"])
    delta_html = ""
    if delta is not None:
        is_pos = str(delta).strip().startswith("+")
        good = is_pos if delta_positive_is_good else not is_pos
        dcolor = t["success"] if good else t["danger"]
        arrow = "▲" if is_pos else "▼"
        delta_html = f'<div class="metric-delta" style="color:{dcolor};">{arrow} {delta}</div>'

    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    val_style = f"color:{value_color};" if value_color else ""

    progress_html = ""
    if progress_pct is not None:
        pct = max(0.0, min(100.0, progress_pct))
        bar_color = value_color or color
        progress_html = f"""
          <div class="progress-track">
            <div class="progress-fill" style="width:{pct:.0f}%; background:{bar_color};"></div>
          </div>
        """

    spark_html = ""
    if trend:
        svg = _sparkline_svg(trend, value_color or color)
        if svg:
            spark_html = f'<div class="metric-spark">{svg}</div>'

    html = f"""
        <div class="metric-card" style="animation-delay:{delay}s;">
          <div class="metric-top">
            <div class="metric-label">{label}</div>
            <div class="metric-icon" style="color:{color}; background:{color}1f; border-color:{color}40;">{icon}</div>
          </div>
          <div class="metric-value" style="{val_style}">{value}</div>
          {delta_html}
          {sub_html}
          {progress_html}
          {spark_html}
        </div>
        """
    # IMPORTANT: strip blank/whitespace-only lines (left behind whenever an
    # optional part like delta_html/progress_html is "") before rendering.
    # A whitespace-only line in the middle of this block breaks Streamlit's
    # markdown "continuous raw HTML" detection, and everything after it
    # falls back to normal Markdown parsing - where the still-indented
    # lines get rendered as a literal code block instead of HTML. See
    # metric_card.py bug (empty delta/progress -> visible "<div class=..."
    # text in a code box on cards that don't use every optional field).
    html = "\n".join(line for line in html.split("\n") if line.strip() != "")
    st.markdown(html, unsafe_allow_html=True)


def badge(label, color, dot=True, icon=None):
    dot_html = f'<span class="badge-dot" style="background:{color};"></span>' if dot else ""
    icon_html = f"{icon} " if icon else ""
    return (
        f'<span class="badge" style="background:{color}22; color:{color}; '
        f'border:1px solid {color}55;">{dot_html}{icon_html}{label}</span>'
    )


def section_title(text, icon="", trailing_html=None):
    """Card/chart header bar. `trailing_html` optionally renders
    right-aligned content (e.g. a live badge() or a current-value chip)
    so charts can carry their own compact header instead of a bare title."""
    trailing = f'<span class="section-title-trailing">{trailing_html}</span>' if trailing_html else ""
    st.markdown(
        f'<div class="section-title"><span class="bar"></span>{icon} {text}{trailing}</div>',
        unsafe_allow_html=True,
    )


def empty_state(message, icon="🗂️", sub=None):
    """Reusable placeholder for a card/table/chart with no data to show,
    instead of a bare line of caption text."""
    sub_html = f'<div class="empty-state-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="empty-state">
          <div class="empty-state-icon">{icon}</div>
          <div class="empty-state-msg">{message}</div>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
