import streamlit as st


def skeleton_kpi_row(n: int = 4):
    """Shimmering placeholder for a row of KPI cards, shown while data/models
    are loading on a cold start (see main.py)."""
    cols = st.columns(n)
    for c in cols:
        with c:
            st.markdown('<div class="skeleton skeleton-kpi"></div>', unsafe_allow_html=True)


def skeleton_chart(height: int = 320):
    st.markdown(f'<div class="skeleton skeleton-chart" style="height:{height}px;"></div>', unsafe_allow_html=True)


def skeleton_lines(n: int = 3, widths=None):
    widths = widths or [90, 75, 60]
    rows = "".join(
        f'<div class="skeleton skeleton-line" style="width:{widths[i % len(widths)]}%;"></div>'
        for i in range(n)
    )
    st.markdown(f'<div class="skeleton-wrap">{rows}</div>', unsafe_allow_html=True)


def skeleton_dashboard_preview():
    """Full-page placeholder used for the initial 'Booting AI intelligence
    layer…' load — two KPI rows plus a chart row, matching the real layout
    so the swap-in feels seamless rather than jarring."""
    skeleton_kpi_row(4)
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    skeleton_kpi_row(4)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.4, 1])
    with c1:
        skeleton_chart(300)
    with c2:
        skeleton_chart(300)
